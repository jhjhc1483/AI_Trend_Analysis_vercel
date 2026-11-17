from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

from crawler_common import save_results

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


    # 기존 데이터와 합쳐 저장 (crawler_common.save_results)
    # AI타임스는 이미 있는 기사라도 시간이 바뀌었으면(수정된 기사) 새 정보로 갱신
    full_path = 'codes/aitimes.json'
    time_of = lambda item: tuple(item.get(k) for k in ('년', '월', '일', '시', '분'))
    save_results(df1.to_dict('records'), full_path, "aitimes",
                 update_if=lambda old, new: time_of(old) != time_of(new))

except Exception as e:
    print(f"크롤링/스크래핑 중 치명적인 오류 발생: {e}")
    if 'browser' in locals():
        browser.quit()
