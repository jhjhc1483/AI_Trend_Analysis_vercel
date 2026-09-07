import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import json

# 국방일보 전체기사 URL
target_url = "https://kookbang.dema.mil.kr/newsWeb/allToday.do"

# 브라우저 User-Agent 및 헤더 설정 (ScraperAPI 대신 직접 요청)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive'
}

data = []

try:
    # 직접 웹페이지 요청 (타임아웃 30초)
    response = requests.get(target_url, headers=headers, timeout=30)
    response.raise_for_status()
    
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    
    for li in soup.select("li"):
        title_tag = li.select_one(".eps1")
        date_tag = li.select_one("span")
        link_tag = li.select_one("a")

        if not (title_tag and date_tag and link_tag):
            continue
            
        try:
            name = title_tag.get_text(strip=True)
            code = link_tag.get("href")
            link = f"https://kookbang.dema.mil.kr{code}"
            
            # 날짜 파싱 로직 안전장치 추가 (예: "2026. 03. 20. 17:25")
            date_text = date_tag.get_text(strip=True)
            date = date_text.split(". ")
            if len(date) >= 4:
                year = date[0]
                month = date[1]
                day = date[2]
                time = date[3].split(":")
                if len(time) == 2:
                    hour = time[0]
                    minute = time[1]
                    data.append([name, link, year, month, day, hour, minute])
        except Exception as e:
            print(f"항목 파싱 중 오류 발생: {e}")
            continue

except requests.exceptions.RequestException as e:
    print(f"웹페이지 직접 요청 중 오류 발생: {e}")

# 데이터 저장 로직 (기존 kookbang.py와 동일)
df13 = pd.DataFrame(data, columns=['제목', '링크', '년', '월', '일', '시', '분'])
full_path = 'codes/kookbang.json'
os.makedirs(os.path.dirname(full_path), exist_ok=True)

existing_data = []
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
    except Exception as e:
        print(f"기존 파일 로드 실패: {e}")

new_data = df13.to_dict('records')
combined_data = existing_data + new_data

seen_titles = set()
final_data = []
for item in combined_data:
    title = item.get('제목')
    if title and title not in seen_titles:
        final_data.append(item)
        seen_titles.add(title)

with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"[국방일보(직접 요청)] 완료: 신규 {len(new_data)}건 수집 | 기존 {len(existing_data)}건 병합 | 최종 {len(final_data)}건 저장 ({full_path})")
