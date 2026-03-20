import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import json

# 환경 변수에서 API 키 불러오기 (로테이션 지원)
API_KEYS = [
    os.environ.get('SCRAPER_API_KEY'),
    os.environ.get('SCRAPER_API_KEY_2')
]
# None이 아닌 키만 필터링
SCRAPER_KEYS = [k for k in API_KEYS if k]

if not SCRAPER_KEYS:
    raise ValueError("GitHub Secrets 또는 .env에 SCRAPER_API_KEY가 설정되지 않았습니다.")

# 현재 사용할 API 키 인덱스
current_key_idx = 0

SCRAPER_URL = 'http://api.scraperapi.com'
target_url = "https://kookbang.dema.mil.kr/newsWeb/allToday.do"

# 2. ScraperAPI 파라미터 설정 (한국 IP 우회)
payload = {
    'url': target_url,
    'country_code': 'kr' 
}

data = []

while current_key_idx < len(SCRAPER_KEYS):
    payload['api_key'] = SCRAPER_KEYS[current_key_idx]
    try:
        # 3. 우회 서버로 요청 전송 (타임아웃 30초)
        response = requests.get(SCRAPER_URL, params=payload, timeout=30)
        if response.status_code == 403:
            print(f"API 키 ({current_key_idx+1}번째) 크레딧 부족(403). 다음 API 키를 시도합니다.")
            current_key_idx += 1
            continue
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
                
                # 날짜 파싱 로직 안전장치 추가
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
        break
    except requests.exceptions.RequestException as e:
        print(f"웹페이지 우회 요청 중 오류 발생: {e}")
        break

# 4. 데이터 저장 로직 (기존과 동일)
df13 = pd.DataFrame(data, columns=['제목','링크','년','월','일','시', '분'])
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
    # 기존 코드에서 item.get('제목')을 link라는 변수로 받았던 것을 직관적으로 수정
    title = item.get('제목')
    if title and title not in seen_titles:
        final_data.append(item)
        seen_titles.add(title)

with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n작업 완료! 최종 데이터 수: {len(final_data)}개")
