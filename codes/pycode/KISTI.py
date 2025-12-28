import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 1. 세션 및 재시도(Retry) 설정
session = requests.Session()
retries = Retry(
    total=5,               # 최대 5번까지 재시도
    backoff_factor=1,      # 재시도 간격 (1초, 2초, 4초...)
    status_forcelist=[403, 500, 502, 503, 504], # 해당 에러 발생 시 재시도
    raise_on_status=False
)
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))

# 공통 헤더 (서버 차단 방지용)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

url = [
    "https://www.kisti.re.kr/post/stdata?t=1766153331929",
    "https://www.kisti.re.kr/post/issuebrief?t=1766153335872",
    "https://www.kisti.re.kr/post/data-insight?t=1766153370270",
    "https://www.kisti.re.kr/post/asti-insight?t=1766153386897",
    "https://www.kisti.re.kr/post/analysis-report?t=1766153395670"
]

data = []

for i in range(len(url)):
    print(f"--- {url[i]} 수집 중 ---")
    try:
        # headers와 timeout을 추가하고 session.get 사용
        response = session.get(url[i], headers=headers, timeout=30)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 카테고리 추출 시 예외 처리
        category_tag = soup.select_one(".tit_nav.tit_nav_bg04>h1")
        category = category_tag.text.strip() if category_tag else "알수없음"

        items = soup.select(".text_wrap")
        for item in items:
            try:
                anchor = item.select_one("a")
                if not anchor: continue
                
                code = anchor.attrs['href']
                link = code if "https://" in code else f"https://www.kisti.re.kr{code}"
                
                # 정규식 대신 .text를 사용하는 것이 안전하고 빠릅니다
                name = anchor.text.strip()
                
                date_tag = item.select_one(".date")
                if date_tag:
                    date_text = date_tag.text.strip()
                    date_temp = date_text.split('.')
                    # '2023.12.19.' 형태 대비 빈값 제거
                    date_temp = [d.strip() for d in date_temp if d.strip()]
                    
                    years = date_temp[0]
                    month = date_temp[1]
                    day = date_temp[2]

                    data.append([name, category, link, years, month, day])
            except Exception as e:
                print(f"항목 파싱 중 오류: {e}")
                continue
        
        # 페이지 간 짧은 휴식 (서버 부하 방지)
        time.sleep(0.5)

    except Exception as e:
        print(f"URL 접속 중 오류 발생 ({url[i]}): {e}")
        continue

# 2. 데이터프레임 생성 및 정제
df10 = pd.DataFrame(data, columns=['제목', '분류', '링크', '년', '월', '일'])
full_path = 'codes/KISTI.json'

# 폴더 자동 생성
os.makedirs(os.path.dirname(full_path), exist_ok=True)

new_data = df10.to_dict('records')

# 3. 기존 데이터 로드 및 중복 제거 (기존 로직 유지)
existing_data = []
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
    except Exception as e:
        print(f"기존 JSON 로드 오류: {e}")

combined_data = existing_data + new_data
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크')
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)

# 4. 파일 저장
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n총 {len(existing_data)}개의 기존 데이터와 {len(new_data)}개의 새 데이터를 합쳤습니다.")
print(f"중복 제거 후 최종 데이터: {len(final_data)}개 저장 완료.")