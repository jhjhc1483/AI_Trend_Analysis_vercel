import requests
import pandas as pd
import time
import os
import json
import re  # 정규표현식 모듈

# 1. 헤더 설정
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
            # 1. 기사명 처리
            raw_title = post.get('title', '').strip()
            
            # [강력해진 정규표현식 적용]
            # \s* : 괄호 앞 공백 제거
            # \(       : 여는 소괄호
            # [\'‘’]   : 직선 따옴표(') 뿐만 아니라 둥근 따옴표(‘ ’)도 모두 포함
            # \d{2}    : 연도 숫자 2자리 (예: 25)
            # [\.\d]+  : 점(.)과 숫자가 섞여 있는 날짜 부분
            # \.?      : 맨 끝에 점이 있어도 되고 없어도 됨 (예: 23.)
            # \)       : 닫는 소괄호
            name = re.sub(r"\s*\([\'‘’]\d{2}[\.\d]+\.?\)", "", raw_title).strip()
            
            # 2. 분류
            category = category_name
            
            # 3. 링크 생성
            num = post.get('num')
            link = f"{base_detail_url}?menu_cd={code}&num={num}"
            
            # 4. 날짜 분리
            date_str = post.get('write_dt', '')
            if date_str and '-' in date_str:
                date_parts = date_str.split('-')
                years = date_parts[0]
                month = date_parts[1]
                day = date_parts[2]
            else:
                years, month, day = "", "", ""
            
            data.append([name, category, link, years, month, day, "", ""])
            
        time.sleep(0.5) 
        
    except Exception as e:
        print(f"Error on {category_name}: {e}")

df17 = pd.DataFrame(data, columns=['기사명','분류','링크','년','월','일','시','분'])
full_path = 'codes/aikorea.json'

# 폴더 생성
os.makedirs(os.path.dirname(full_path), exist_ok=True)

new_data = df17.to_dict('records')
existing_data = []

# 기존 데이터 로드
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
    except Exception as e:
        print(f"기존 JSON 로드 에러: {e}")
        existing_data = []

# 데이터 병합 및 중복 제거
combined_data = existing_data + new_data
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크') 
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)

print(f"총 {len(final_data)}개의 데이터가 준비되었습니다.")

# 저장
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"저장 완료: {full_path}")