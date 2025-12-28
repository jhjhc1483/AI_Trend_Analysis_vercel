from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options  # 옵션 설정을 위해 추가
from bs4 import BeautifulSoup
import warnings
import pandas as pd
from urllib3.exceptions import InsecureRequestWarning
import os
import json
import numpy as np

# iitp 파싱할 사이트 주소들을 2d array로 생성
url_list = [
    'https://www.iitp.kr/web/lay1/program/S1T14C61/itfind/list.do?cpage=1&rows=10&searchTarget=all',
    'https://www.iitp.kr/web/lay1/program/S1T14C61/itfind',
    'https://www.iitp.kr/web/lay1/program/S1T62C65/itfind/list.do?cpage=1&rows=10&searchTarget=all',
    'https://www.iitp.kr/web/lay1/program/S1T62C65/itfind',
    'https://www.iitp.kr/web/lay1/program/S1T62C66/itfind/list.do?cpage=1&rows=10&searchTarget=all',
    'https://www.iitp.kr/web/lay1/program/S1T62C66/itfind',
    'https://www.iitp.kr/web/lay1/program/S1T62C67/itfind/list.do?cpage=1&rows=10&searchTarget=all',
    'https://www.iitp.kr/web/lay1/program/S1T62C67/itfind',
    'https://www.iitp.kr/web/lay1/program/S1T62C68/itfind/list.do?cpage=1&rows=10&searchTarget=all',
    'https://www.iitp.kr/web/lay1/program/S1T62C68/itfind',
    'https://www.iitp.kr/web/lay1/program/S1T62C69/itfind/list.do?cpage=1&rows=10&searchTarget=all',
    'https://www.iitp.kr/web/lay1/program/S1T62C69/itfind',
    'https://www.iitp.kr/web/lay1/program/S1T62C226/itfind/list.do?cpage=1&rows=10&searchTarget=all',
    'https://www.iitp.kr/web/lay1/program/S1T62C226/itfind',
    'https://www.iitp.kr/web/lay1/bbs/S1T62C70/A/21/list.do?cpage=1&sort=latest&rows=10',
    'https://www.iitp.kr/web/lay1/bbs/S1T62C70/A/21',
    'https://www.iitp.kr/web/lay1/bbs/S1T14C63/A/22/list.do?cpage=1&sort=latest&rows=10',
    'https://www.iitp.kr/web/lay1/bbs/S1T14C63/A/22'
]

# 1. 1차원 배열 생성
array_1d = np.array(url_list)
# 2. 2차원 배열로 변형 (reshape) (9행 2열)
array_2d = array_1d.reshape(9, 2)
# print(array_2d[8,0])

# requests 라이브러리 경고 숨김 
warnings.filterwarnings('ignore', category=InsecureRequestWarning) 

data = []

# --- Headless 옵션 설정 ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # 창 띄우지 않음
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
# 봇 탐지 방지를 위한 User-Agent 설정 (일반 브라우저처럼 보이게 함)
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

for i in range(0, 9):
    # 접속할 URL
    url = array_2d[i, 0]
    
    # CSS 선택자 설정
    if i < 7:
        # 일반 게시판
        LIST_ITEM_SELECTOR = "#itfindList > div.board_list_area > ul > li"
    else:
        # 공지사항 등 다른 게시판
        LIST_ITEM_SELECTOR = "#bbs_a_list > div.board_list_area > ul > li"
    
    MAIN_TITLE_SELECTOR = "#v_sub_tit h2" 
    
    driver = None 

    try:
        print(f"[{i+1}/9] 웹 브라우저(Headless)를 열고 페이지 로드 중... : {url}")
        
        # 옵션을 적용하여 드라이버 실행
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # 명시적 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, LIST_ITEM_SELECTOR))
        )

        # HTML 가져오기
        html_after_js = driver.page_source
        soup = BeautifulSoup(html_after_js, 'html.parser')

        # 메인 카테고리 제목 추출
        category_element = soup.select_one(MAIN_TITLE_SELECTOR)
        category_text = category_element.text.strip() if category_element else "카테고리 없음"
        print(f"   ✅ 메인 카테고리: {category_text}")

        # 목록 항목 추출
        item_list = soup.select(LIST_ITEM_SELECTOR)
        print(f"   ✅ 항목 수: {len(item_list)}개")

        # 기본 URL (상대 경로 해결용)
        base_url = array_2d[i, 1]
        
        for item in item_list:
            # 제목 및 링크 추출
            title_link_tag = item.select_one("div.tit_area > a")
            title = title_link_tag.text.strip() if title_link_tag else "제목 없음"
            link = title_link_tag.get('href') if title_link_tag else ""
            
            if link.startswith('.'):
                absolute_link = base_url + link[1:]
            else:
                absolute_link = link

            # 발행일 추출
            date_element = item.select_one(".info_list_area li:nth-child(2) .txt")
            if date_element:
                date_raw = date_element.text.replace("발행일:", "").strip()
                date_parts = date_raw.split('-')
                
                # 날짜 형식이 올바른지 확인 (YYYY-MM-DD)
                if len(date_parts) == 3:
                    year = date_parts[0]
                    month = date_parts[1]
                    day = date_parts[2]
                else:
                    year, month, day = "", "", ""
            else:
                year, month, day = "", "", ""

            # 링크가 존재하는 경우에만 추가
            if absolute_link:
                data.append([title, category_text, absolute_link, year, month, day])
                
    except Exception as e:
        print(f"   ❌ 에러 발생: {e}")
        
    finally:
        if driver:
            driver.quit()

# --- 데이터 저장 로직 ---
df11 = pd.DataFrame(data, columns=['제목', '분류', '링크', '년', '월', '일'])
# print(df4.head())

full_path = 'codes/iitp.json'

# 디렉토리가 없으면 생성
os.makedirs(os.path.dirname(full_path), exist_ok=True)

new_data = df11.to_dict('records') 

existing_data = []

# 1. 기존 JSON 파일 로드
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
            else:
                print("기존 JSON 파일이 비어 있습니다.")
    except Exception as e:
        print(f"기존 JSON 로드 오류 ({e}). 새 데이터만 저장합니다.")
        existing_data = []

# 2. 합치기
combined_data = existing_data + new_data

# 3. 중복 제거
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크')
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)

print("-" * 50)
print(f"기존 데이터: {len(existing_data)}개")
print(f"신규 데이터: {len(new_data)}개")
print(f"중복 제거 후 최종: {len(final_data)}개")

# 4. 저장
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"최종 데이터가 '{full_path}'에 저장되었습니다.")