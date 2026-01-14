from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json

# 1. WebDriver 옵션 설정
chrome_options = Options()

# 💡 헤드리스 모드 활성화
chrome_options.add_argument("--headless=new")
# 불필요한 에러 메시지 없애기
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
# 기타 헤드리스 환경 최적화 옵션
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
# # 창 크기 설정
chrome_options.add_argument("window-size=1920x1080") 

# 2. Service 객체 생성 및 WebDriver 초기화
service = Service(executable_path=ChromeDriverManager().install())

try:
    # 3. WebDriver 초기화
    browser = webdriver.Chrome(service=service, options=chrome_options)
    
    browser.get('https://www.aitimes.com/news/articleList.html?page=1&total=29543&sc_section_code=&sc_sub_section_code=&sc_serial_code=&sc_area=&sc_level=&sc_article_type=&sc_view_level=&sc_sdate=&sc_edate=&sc_serial_number=&sc_word=&sc_andor=&sc_word2=&box_idxno=&sc_multi_code=&sc_is_image=&sc_is_movie=&sc_user_name=&sc_order_by=E')
    browser.implicitly_wait(10) # 묵시적 대기 시간 설정
    more_button = browser.find_element(By.CSS_SELECTOR, '#section-list > button')
    
    more_button.click()
    more_button.click()
    more_button.click()
    more_button.click()

    items = browser.find_elements(By.CSS_SELECTOR, '.altlist-text-item')
    data = []
    
    print(f"총 {len(items)}개의 기사 항목을 찾았습니다. 상세 정보 수집을 시작합니다.")

    for item in items:
        try:
            name = item.find_element(By.CSS_SELECTOR, '.altlist-subject').text
            link_element = item.find_element(By.CSS_SELECTOR, '.altlist-subject > a')
            link = link_element.get_attribute('href')
            
            if not link:
                print(f"경고: 링크가 비어있는 항목을 건너뜁니다. (기사명: {name})")
                continue
        
            response = requests.get(link)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            date_text = soup.select_one(".breadcrumbs > li:nth-child(2)").text.strip()
            match = re.search(r'(\d{4})\.(\d{2})\.(\d{2})\s(\d{2}):(\d{2})', date_text)
            
            if match:
                years, month, day, hour, minute = match.groups()
            else:
                print(f"경고: 날짜/시간 형식을 찾을 수 없습니다. (링크: {link})")
                years, month, day, hour, minute = 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'

            data.append([name, link, years, month, day, hour, minute])
            
        except Exception as e:
            print(f"데이터 추출 중 오류 발생 (링크: {link if 'link' in locals() else 'N/A'}): {e}")
            continue

    browser.quit()

    df1 = pd.DataFrame(data, columns=['기사명','링크','년','월','일','시','분'])
    df1['기사명'] = df1['기사명'].fillna('')
    df1['기사명'] = df1['기사명'].str.replace('\\', '', regex=False)
    df1['기사명'] = df1['기사명'].str.replace('\'', '＇', regex=False)
    df1['기사명'] = df1['기사명'].str.replace('\"', '〃', regex=False)


    full_path = 'codes/aitimes.json' 
    new_data = df1.to_dict('records')

    existing_data_dict = {}
    total_existing = 0
    total_new = len(new_data)
    update_count = 0
    skip_count = 0

    # 1. 기존 JSON 파일 로드 및 딕셔너리로 변환 (link를 키로 사용)
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    existing_list = json.loads(content)
                    total_existing = len(existing_list)
               
                    for item in existing_list:
                        link = item.get('링크')
                        if link:
                            existing_data_dict[link] = item
                else:
                    print("기존 JSON 파일은 존재하지만 비어 있습니다.")
        except Exception as e:
            print(f"기존 JSON 파일 로드 중 오류 발생 ({e}). 새 데이터만 사용합니다.")
            existing_data_dict = {}

    # 2. 새 데이터를 순회하며 업데이트 또는 스킵 결정
    for item in new_data:
        link = item.get('링크')

        new_time_tuple = (item.get('년'), item.get('월'), item.get('일'), item.get('시'), item.get('분'))

        if link in existing_data_dict:

            existing_item = existing_data_dict[link]
            existing_time_tuple = (existing_item.get('년'), existing_item.get('월'), existing_item.get('일'), existing_item.get('시'), existing_item.get('분'))
            if new_time_tuple != existing_time_tuple:
                existing_data_dict[link] = item # 덮어쓰기
                update_count += 1
            else:
                skip_count += 1
        else:

            existing_data_dict[link] = item

    # 3. 딕셔너리 값을 리스트로 변환하여 최종 데이터 준비
    final_data = list(existing_data_dict.values())
            
    print(f"\n--- 데이터 저장 요약 ---")
    print(f"총 {total_existing}개의 기존 데이터와 {total_new}개의 새 데이터를 처리했습니다.")
    print(f" - **업데이트(시간 변경)**된 항목: {update_count}개")
    print(f" - **중복(링크+시간 동일)**되어 스킵된 항목: {skip_count}개")
    print(f" - **새로 추가**된 항목: {len(final_data) - total_existing + skip_count}개") # 새로 추가 = 최종 - 기존 + 스킵
    print(f"중복을 제거 및 업데이트한 후 최종 데이터는 총 {len(final_data)}개입니다.")

    # 4. 최종 데이터를 JSON 파일로 저장
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)

    print(f"최종 데이터가 '{full_path}'에 성공적으로 저장되었습니다.")

except Exception as e:
    print(f"크롤링/스크래핑 중 치명적인 오류 발생: {e}")
    if 'browser' in locals():
        browser.quit()
