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

chrome_options = Options()
chrome_options.add_argument("--headless")  # 화면 안 띄우기
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")


service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

url = ["https://www.kisa.or.kr/201","https://www.kisa.or.kr/20207","https://www.kisa.or.kr/20305"]
data = []
try:
    for i in range(0, 3):
        driver.get(url[i])

        time.sleep(2) 
        category_temp = driver.find_element(By.CSS_SELECTOR, ".h2_type_1").text.strip()
        items = driver.find_elements(By.CSS_SELECTOR, "table.tbl_board tbody tr")
        for item in items:
            try:
                # 1. 제목 추출
                title_el = item.find_element(By.CSS_SELECTOR, "td.sbj.txtL a")
                name = title_el.text.strip()
                category = category_temp
                date = item.find_element(By.CSS_SELECTOR, "td.date").text.strip()
                date_temp = date.split("-")
                years = date_temp[0]
                month = date_temp[1]
                day = date_temp[2]
                link_element = item.find_element(By.CSS_SELECTOR, 'td.sbj.txtL a')
                link = link_element.get_attribute('href')
                if name and years and month and day and link:
                    data.append([name,category, link, years, month, day])

            except Exception as e:
                continue

finally:
    driver.quit() 

print(f"\n총 {len(data)} 건 추출 완료")

df16 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
full_path = 'codes/KISA.json'
new_data = df16.to_dict('records') 

existing_data = []

# 1. 기존 JSON 파일 로드
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            # 파일이 비어있지 않은지 확인 후 로드
            content = f.read()
            if content:
                existing_data = json.loads(content)
            else:
                print("기존 JSON 파일은 존재하지만 비어 있습니다. 새 데이터만 저장합니다.")
    except Exception as e:
        print(f"기존 JSON 파일 로드 중 오류 발생 ({e}). 새 데이터만 저장합니다.")
        existing_data = []

# 2. 새 데이터와 기존 데이터를 합치기
combined_data = existing_data + new_data

# 3. 중복 제거 (가장 중요한 단계)
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크') 
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)
        
print(f"총 {len(existing_data)}개의 기존 데이터와 {len(new_data)}개의 새 데이터를 합쳤습니다.")
print(f"중복을 제거한 후 최종 데이터는 총 {len(final_data)}개입니다.")

# 4. 최종 데이터를 JSON 파일로 저장 (덮어쓰기)
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n최종 데이터가 '{full_path}'에 성공적으로 저장되었습니다.")
