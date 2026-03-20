import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import re
import datetime

# 인공지능 신문 전체기사 3페이지까지 크롤링
data = []
for i in range(1, 4):
    target_url = f"https://www.aitimes.kr/news/articleList.html?page={i}&total=22766&box_idxno=&view_type=sm"
    
    try:
        # 일반 서버로 직접 요청 (Scraper 미사용)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(target_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 새로운 HTML 구조에 맞춰 리스트 아이템 선택 (기존 view-cont 대비 강건하게)
        items = soup.select(".type2 li, .type1 li, .list-block li, #section-list li, .view-cont")
        
        # [안전장치] 만약 기사 목록이 비어있다면 응답받은 HTML의 앞부분을 출력하여 확인
        if not items:
            print(f"[{i}페이지] 기사 목록을 찾을 수 없습니다. 차단 여부 확인을 위한 HTML 응답:")
            print(html[:500])
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
        
print(f"총 {len(existing_data)}개의 기존 데이터와 {len(new_data)}개의 새 데이터를 합쳤습니다.")
print(f"중복을 제거한 후 최종 데이터는 총 {len(final_data)}개입니다.")

with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n최종 데이터가 '{full_path}'에 성공적으로 저장되었습니다.")
