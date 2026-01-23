import requests
import pandas as pd
import time
import os
import json
import re  # 정규표현식 모듈 추가

# 1. 헤더 설정 (차단 회피용)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://aikorea.go.kr/'
}

# 2. 메뉴 코드와 분류명 매핑
menu_map = {
    "000010": "공지사항",
    "000011": "정책자료",
    "000012": "보도자료"
}

# 3. 데이터 수집 설정
base_ajax_url = "https://aikorea.go.kr/web/board/ajax/list.do"
base_detail_url = "https://aikorea.go.kr/web/board/brdDetail.do"

data = []

for code, category_name in menu_map.items():
    print(f"'{category_name}'({code}) 수집 중...")
    
    params = {
        'menu_cd': code,
        'currentPage': '1',  # 1페이지만 수집
        'searchData': 'contdata',
        'searchText': ''
    }
    
    try:
        response = requests.get(base_ajax_url, headers=headers, params=params)
        response.raise_for_status()
        
        # JSON 데이터 파싱
        json_data = response.json()
        posts = json_data.get('brdList', [])
        
        for post in posts:
            # 1. 기사명 (괄호 제거 로직 추가)
            raw_title = post.get('title', '').strip()
            
            # 정규표현식 설명:
            # ^ : 문자열의 시작
            # [\(\[] : '(' 또는 '[' 문자로 시작하고
            # .*? : 그 안에 어떤 내용이든 최소한으로 포함하며
            # [\)\]] : ')' 또는 ']' 문자로 끝나는 패턴
            # 이 패턴을 빈 문자열('')로 치환 후 양쪽 공백 제거(.strip())
            name = re.sub(r'^[\(\[].*?[\)\]]', '', raw_title).strip()
            
            # 2. 분류 (매핑된 이름 사용)
            category = category_name
            
            # 3. 링크 생성
            num = post.get('num')
            link = f"{base_detail_url}?menu_cd={code}&num={num}"
            
            # 4. 날짜 분리 (YYYY-MM-DD 형식이라고 가정)
            date_str = post.get('write_dt', '') # 예: "2026-01-09"
            if date_str and '-' in date_str:
                date_parts = date_str.split('-')
                years = date_parts[0]
                month = date_parts[1]
                day = date_parts[2]
            else:
                years, month, day = "", "", ""
            
            data.append([name, category, link, years, month, day, "", ""])
            
        time.sleep(0.5) # 서버 부하 방지
        
    except Exception as e:
        print(f"Error on {category_name}: {e}")

df17 = pd.DataFrame(data, columns=['기사명','분류','링크','년','월','일','시','분'])
full_path = 'codes/aikorea.json'

# 디렉토리가 없으면 생성 (에러 방지용)
os.makedirs(os.path.dirname(full_path), exist_ok=True)

new_data = df17.to_dict('records')

existing_data = []

# 1. 기존 JSON 파일 로드
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

# 2. 새 데이터와 기존 데이터를 합치기
combined_data = existing_data + new_data

# 3. 중복 제거
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