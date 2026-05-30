import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import re
import datetime

# 인공지능 신문 전체기사 3페이지까지 크롤링
data = []
# --- 크롤링 시작 ---
# 세션을 사용하여 쿠키와 상태를 유지 (페이지네이션 정상 작동을 위함)
session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.aitimes.kr/news/articleList.html?view_type=sm'
}
session.headers.update(headers)

for i in range(1, 4):
    # total 값을 현재 시점과 유사하게 24000 정도로 설정하여 호출 (서버 환경 대응)
    target_url = f"https://www.aitimes.kr/news/articleList.html?page={i}&total=24000&box_idxno=&view_type=sm"
    
    try:
        response = session.get(target_url, timeout=30)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 메인 뉴스 목록 영역만 정확히 타겟팅 (사이드바 중복 수집 방지)
        items = soup.select("#section-list li")
        
        if not items:
            print(f"[{i}페이지] 기사 목록을 찾을 수 없습니다. HTML 응답 일부: {response.text[:200]}")
            continue

        for item in items:
            try:
                name_tag = item.select_one(".titles a")
                if not name_tag: # 혹시 구조가 다를 경우를 위한 Fallback
                    name_tag = item.select_one("a")
                
                if not name_tag:
                    continue
                    
                name = name_tag.text.strip()
                code = name_tag.get('href', '')
                if not code.startswith('http'):
                    link = f"https://www.aitimes.kr{code}"
                else:
                    link = code
                
                # 날짜 추출 (HTML 주석에 숨겨져 있거나 구조가 깨진 경우 대비 정규식 사용)
                date_match = re.search(r'(\d{4}\.\d{2}\.\d{2}|\d{2}\.\d{2} \d{2}:\d{2})', str(item))
                
                years, month, day, hour, minute = "", "", "", "", ""
                
                if date_match:
                    raw_date = date_match.group(1)
                    if len(raw_date) == 10: # 2024.03.20
                        years, month, day = raw_date.split(".")
                    else: # 03.20 11:40
                        date_parts = raw_date.split(" ")
                        month, day = date_parts[0].split(".")
                        hour, minute = date_parts[1].split(":")
                        years = str(datetime.datetime.now().year)
                
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
        
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"[AInews] 완료: 신규 {len(new_data)}건 수집 | 기존 {len(existing_data)}건 병합 | 최종 {len(final_data)}건 저장 ({full_path})")
