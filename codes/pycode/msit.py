from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import pandas as pd
import os
import json
from datetime import datetime

# 1. 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless=new") # 최신 헤드리스 모드 사용 권장
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080") 
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
chrome_options.add_argument("--disable-blink-features=AutomationControlled") # 자동화 제어 흔적 제거
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--allow-running-insecure-content')
chrome_options.add_argument('--lang=ko_KR') # 한국어 설정

service = Service(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

data = []

try:
    for i in range(1, 4):
        url = f"https://www.msit.go.kr/bbs/list.do?sCode=user&mId=307&mPid=208&pageIndex={i}&bbsSeqNo=94"
        print(f"페이지 접속 시도: {url}")
        driver.get(url)
        
        # 페이지 로딩 대기 (GitHub Actions는 느릴 수 있으므로 넉넉하게)
        driver.implicitly_wait(15) 
        time.sleep(2) 

        items = driver.find_elements(By.CSS_SELECTOR, ".board_list .toggle:not(.thead)")
        
        if not items:
            print(f"!!! {i} 페이지에서 게시글을 찾지 못했습니다.")
            print(f"현재 페이지 제목: {driver.title}")
            print("페이지 소스 일부(500자):")
            print(driver.page_source[:500])
            continue

        for item in items:
            try:
                title_el = item.find_element(By.CSS_SELECTOR, "p.title")
                name = title_el.text.strip()
                category = "과기정통부 보도자료"
                date_el = item.find_element(By.CSS_SELECTOR, ".date")
                date_text = date_el.text.strip()
                years, month, day = "", "", ""
                
                try:
                    dt = datetime.strptime(date_text, "%b %d, %Y")
                    years = str(dt.year)
                    month = f"{dt.month:02d}"
                    day = f"{dt.day:02d}"
                except ValueError:
                    date_parts = re.findall(r'\d+', date_text)
                    if len(date_parts) >= 3:
                        years = date_parts[0]
                        month = date_parts[1]
                        day = date_parts[2]
                    else:
                        print(f"날짜 형식 인식 불가: {date_text}")
                        continue
                link_element = item.find_element(By.TAG_NAME, "a")
                onclick_text = link_element.get_attribute("onclick")
                
                code_match = re.search(r'\d+', onclick_text)
                if code_match:
                    code = code_match.group()
                    link = f"https://www.msit.go.kr/bbs/view.do?sCode=user&mId=307&mPid=208&pageIndex=1&bbsSeqNo=94&nttSeqNo={code}&searchOpt=ALL&searchTxt="
                    
                    data.append([name, category, link, years, month, day])
                    print(f"추출 성공: {name} ({years}-{month}-{day})")
                else:
                    print(f"링크 코드 추출 실패: {name}")
            except Exception as e:
                print(f"항목 파싱 중 에러: {e}")
                continue
except Exception as e:
    print(f"전체 프로세스 에러: {e}")

finally:
    driver.quit()


print(f"\n총 {len(data)} 건 추출 완료")

df15 = pd.DataFrame(data, columns=['기사명','분류', '링크','년','월','일'])
full_path = 'codes/msit.json'

os.makedirs(os.path.dirname(full_path), exist_ok=True)

new_data = df15.to_dict('records')

existing_data = []
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
    except Exception as e:
        print(f"JSON 로드 실패: {e}")

combined_data = existing_data + new_data
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크')
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)

with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"저장 완료. 총 {len(final_data)}개")
