import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import re

# 1. 환경 변수에서 API 키 불러오기
SCRAPER_API_KEY = os.environ.get('SCRAPER_API_KEY')
if not SCRAPER_API_KEY:
    raise ValueError("GitHub Secrets에 SCRAPER_API_KEY가 설정되지 않았습니다.")

SCRAPER_URL = 'http://api.scraperapi.com'

# 인공지능 신문 전체기사 3페이지까지 크롤링
data = []
for i in range(1, 4):
    target_url = f"https://www.aitimes.kr/news/articleList.html?page={i}&total=22766&box_idxno=&view_type=sm"
    
    # 2. ScraperAPI 파라미터 설정
    payload = {
        'api_key': SCRAPER_API_KEY,
        'url': target_url,
        'country_code': 'kr' 
    }
    
    try:
        # 3. 우회 서버로 요청
        response = requests.get(SCRAPER_URL, params=payload, timeout=30)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select(".view-cont")
        
        # [안전장치] 만약 기사 목록이 비어있다면 응답받은 HTML의 앞부분을 출력하여 확인
        if not items:
            print(f"[{i}페이지] 기사 목록을 찾을 수 없습니다. 차단 여부 확인을 위한 HTML 응답:")
            print(html[:500])
            continue

        for item in items:
            try:
                name = item.select_one(".titles").text.strip()
                code = item.select_one(".titles > a").attrs['href']
                link = f"https://www.aitimes.kr{code}"
                
                pattern = r'<em>(.+?)</em>'
                date_temp = str(item.select_one(".byline > em:nth-child(3)"))
                match = re.search(pattern, date_temp)
                
                # 변수 초기화
                years, month, day, hour, minute = "", "", "", "", ""
                
                if match:
                    date_all = match.group(1)
                    date = date_all.split(" ")
                    if len(date) >= 2:
                        temp = str(date[0]).split(".")
                        if len(temp) == 3:
                            years = temp[0]
                            month = temp[1]
                            day = temp[2]
                        time_temp = str(date[1]).split(":")
                        if len(time_temp) >= 2:
                            hour = time_temp[0]
                            minute = time_temp[1]
                
                data.append([name, link, years, month, day, hour, minute])
            except Exception as e:
                print(f"개별 기사 파싱 중 오류: {e}")
                
    except requests.exceptions.RequestException as e:
        print(f"{i}페이지 요청 중 오류 발생: {e}")

# 4. 데이터 전처리 및 DataFrame 생성 (기존 로직 유지)
df12 = pd.DataFrame(data, columns=['기사명','링크','년','월','일','시','분'])
df12['기사명'] = df12['기사명'].fillna('')
df12['기사명'] = df12['기사명'].str.replace('\\', '', regex=False)
df12['기사명'] = df12['기사명'].str.replace('\'', '＇', regex=False)
df12['기사명'] = df12['기사명'].str.replace('\"', '〃', regex=False)
new_data = df12.to_dict('records')

os.makedirs('codes', exist_ok=True)
full_path = 'codes/AInews.json'

# ----------------- JSON 이어 붙이기 및 중복 제거 로직 -----------------

existing_data = []

if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
            else:
                print("기존 JSON 파일은 존재하지만 비어 있습니다. 새 데이터만 저장합니다.")
    except Exception as e:
        print(f"기존 JSON 파일 로드 중 오류 발생 ({e}). 새 데이터만 저장합니다.")
        existing_data = []

combined_data = existing_data + new_data

seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크') 
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)
        
print(f"총 {len(existing_data)}개의 기존 데이터와 {len(new_data)}개의 새 데이터를 합쳤습니다.")
print(f"중복을 제거한 후 최종 데이터는 총 {len(final_data)}개입니다.")

with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n최종 데이터가 '{full_path}'에 성공적으로 저장되었습니다.")
