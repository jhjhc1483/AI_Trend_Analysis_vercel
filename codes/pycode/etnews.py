import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import re
import time
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 1. 세션 및 재시도 설정 (SSL 오류 및 연결 끊김 방지)
session = Session()
retries = Retry(
    total=5,              
    backoff_factor=1,      
    status_forcelist=[403, 404, 500, 502, 503, 504]
)
session.mount("https://", HTTPAdapter(max_retries=retries))

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

data = []

for i in range(1, 6):
    print(f"--- 현재 {i}페이지 크롤링 중 ---")
    search_url = f"https://search.etnews.com/etnews/search.html?category=CATEGORY1&kwd=%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5&pageNum={i}&pageSize=20&reSrchFlag=false&sort=1&startDate=&endDate=&detailSearch=true"
    
    try:
        response = session.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        items = soup.select(".news_list li")
        for item in items:
            try:
                title_tag = item.select_one(".text > strong > a")
                if not title_tag: continue              
                name = title_tag.text.strip()

                numbers = re.sub(r'[^\d]', '', title_tag.attrs['href'])
                link = f"https://www.etnews.com/{numbers}"
                
                res_detail = session.get(link, headers=headers, timeout=15)
                res_detail.raise_for_status()
                soup_detail = BeautifulSoup(res_detail.text, 'html.parser')
                
                time_tag = soup_detail.select_one("time")
                if time_tag:
                    time_text = time_tag.text.replace("발행일 : ", "").strip()
                    parts = time_text.split(' ')
                    date_part = parts[0] # 2025-12-19
                    time_part = parts[1] # 10:30
                    
                    y, m, d = date_part.split('-')
                    hr, mn = time_part.split(':')
                    
                    data.append([name, link, y, m, d, hr, mn])

                time.sleep(0.3)
                
            except Exception as e:
                print(f"상세 페이지 파싱 중 오류 발생 ({link}): {e}")
                continue

    except Exception as e:
        print(f"{i}페이지 목록을 가져오는 중 오류 발생: {e}")

# 2. 데이터프레임 생성 및 정제
df2 = pd.DataFrame(data, columns=['기사명', '링크', '년', '월', '일', '시', '분'])
df2['기사명'] = df2['기사명'].fillna('').str.replace(r'\\', '', regex=True)
df2['기사명'] = df2['기사명'].str.replace('\'', '＇', regex=False).str.replace('\"', '〃', regex=False)

# 3. JSON 저장 및 중복 제거 로직
full_path = 'codes/etnews.json'
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

new_data = df2.to_dict('records')
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

print(f"\n작업 완료! 최종 데이터 수: {len(final_data)}개")