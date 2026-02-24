import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import json

# 환경 변수에서 API 키 불러오기
SCRAPER_API_KEY = os.environ.get('SCRAPER_API_KEY')
if not SCRAPER_API_KEY:
    raise ValueError("GitHub Secrets에 SCRAPER_API_KEY가 설정되지 않았습니다.")

SCRAPER_URL = 'http://api.scraperapi.com'
target_url = "https://www.dapa.go.kr/dapa/doc/selectDocList.do?menuSeq=3069&bbsSeq=326"

payload = {
    'api_key': SCRAPER_API_KEY,
    'url': target_url,
    'country_code': 'kr' # 한국 IP 지정
}

data = []

try:
    # 우회 서버로 요청 전송 (타임아웃 30초 설정)
    response = requests.get(SCRAPER_URL, params=payload, timeout=30)
    response.raise_for_status()
    
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    category = "방사청 보도자료"
    
    for a in range(1, 11):
        # 예외 처리를 추가하여 페이지 구조 변경 시 전체가 죽지 않도록 방어
        try:
            name_elem = soup.select_one(f".list-table > tbody > tr:nth-child({a}) > td > a > p")
            link_elem = soup.select_one(f".list-table > tbody > tr:nth-child({a}) > td > a ")
            date_elem = soup.select_one(f".list-table > tbody > tr:nth-child({a}) > td:nth-child(3)")
            
            if name_elem and link_elem and date_elem:
                name = name_elem.text.strip()
                link_temp = link_elem.attrs.get('onclick', '')
                code = link_temp.split("'")[1] if "'" in link_temp else ""
                
                link = f"https://www.dapa.go.kr/dapa/doc/selectDoc.do?docSeq={code}&menuSeq=3069&bbsSeq=326&currentPageNo=1&recordCountPerPage=10"
                
                date = date_elem.text.strip()
                date_temp_list = date.split('-')
                if len(date_temp_list) == 3:
                    years, month, day = date_temp_list
                    data.append([name, category, link, years, month, day])
        except AttributeError as e:
            print(f"{a}번째 항목 파싱 중 오류: {e}")
            continue

except requests.exceptions.RequestException as e:
    print(f"웹페이지 요청 중 오류 발생: {e}")

df9 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
os.makedirs('codes', exist_ok=True)
full_path = 'codes/dapa.json'
new_data = df9.to_dict('records')

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

# 4. 최종 데이터를 JSON 파일로 저장
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n최종 데이터가 '{full_path}'에 성공적으로 저장되었습니다.")
