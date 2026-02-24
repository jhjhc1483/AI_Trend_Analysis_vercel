import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json
import time

# 환경 변수에서 API 키 불러오기
SCRAPER_API_KEY = os.environ.get('SCRAPER_API_KEY')
if not SCRAPER_API_KEY:
    raise ValueError("GitHub Secrets에 SCRAPER_API_KEY가 설정되지 않았습니다.")

SCRAPER_URL = 'http://api.scraperapi.com'

# 1. 재시도 로직을 포함한 세션 설정
def get_safe_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1, 
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_safe_session()

# 우회 시 API 서버 자체의 헤더를 사용하는 것이 유리하므로 기존 headers는 제거하거나 기본값 사용
TIMEOUT_SEC = 30 # 우회 API를 거치므로 타임아웃을 넉넉히 설정
data = []

for i in range(3, 8):    
    if i > 6:
        target_url = "https://www.mnd.go.kr/user/newsInUserRecord.action?siteId=mnd&handle=I_669&id=mnd_020500000000"
        
        payload = {
            'api_key': SCRAPER_API_KEY,
            'url': target_url,
            'country_code': 'kr' # 한국 IP 지정
        }
        
        try:
            # 타겟 URL 대신 ScraperAPI 서버로 요청
            response = session.get(SCRAPER_URL, params=payload, timeout=TIMEOUT_SEC)
            response.raise_for_status()
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select(".post")
            category = "국방부 보도자료"
            
            for item in items:
                name = item.select_one(".post > div").text.strip()
                code_temp = item.select_one(".title > a").attrs['href']
                pattern = r"_(.*?)&"
                code_list = re.findall(pattern, code_temp)
                
                if len(code_list) > 1:
                    link = f'https://www.mnd.go.kr/user/newsInUserRecord.action?siteId=mnd&page=1&newsId=I_669&newsSeq=I_{code_list[1]}&command=view&id=mnd_020500000000&findStartDate=&findEndDate=&findType=title&findWord=&findOrganSeq='
                    date = item.select_one(".post_info > dl").select_one('dd').text.strip()
                    years, month, day = date.split('-')
                    data.append([name, category, link, years, month, day, "", ""])
            time.sleep(1)
        except Exception as e:
            print(f"보도자료 크롤링 중 오류: {e}")

    else:
        categories = {3: "국방부", 4: "육군", 5: "해군", 6: "공군"}
        category = categories.get(i, "기타")

        for p in range(1, 3):
            target_url = f"https://www.mnd.go.kr/cop/kookbang/kookbangIlboList.do?siteId=mnd&pageIndex={p}&findType=&findWord=&categoryCode=dema000{i}&boardSeq=&startDate=&endDate=&id=mnd_020101000000"
            
            payload = {
                'api_key': SCRAPER_API_KEY,
                'url': target_url,
                'country_code': 'kr'
            }

            try:
                # 타겟 URL 대신 ScraperAPI 서버로 요청
                response = session.get(SCRAPER_URL, params=payload, timeout=TIMEOUT_SEC)
                response.raise_for_status()
                
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                items = soup.select(".post")

                for item in items:
                    name = item.select_one(".post > div").text.strip()
                    code_temp = item.select_one(".title > a").attrs['href']
                    pattern = r"'(.*?)'"
                    code_list = re.findall(pattern, code_temp)
                    
                    if len(code_list) > 1:
                        link = f'https://www.mnd.go.kr/cop/kookbang/kookbangIlboView.do?siteId=mnd&pageIndex=1&findType=&findWord=&categoryCode={code_list[0]}&boardSeq={code_list[1]}&startDate=&endDate=&id=mnd_020101000000'
                        date = item.select_one(".post_info > dl").select_one('dd').text.strip()
                        years, month, day = date.split('.')
                        data.append([name, category, link, years, month, day, "", ""])
                time.sleep(2)
            except Exception as e:
                print(f"국방일보({category}, {p}페이지) 크롤링 중 오류: {e}")

df5 = pd.DataFrame(data, columns=['기사명','분류','링크','년','월','일','시','분'])
os.makedirs('codes', exist_ok=True)
full_path = 'codes/mnd.json'
new_data = df5.to_dict('records')

existing_data = []
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
    except Exception as e:
        print(f"기존 파일 로드 실패: {e}")

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

print(f"성공: 기존 {len(existing_data)}개 + 신규 {len(new_data)}개 -> 합계(중복제거 후) {len(final_data)}개 저장 완료.")
