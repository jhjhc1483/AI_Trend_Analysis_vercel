import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json
import time

# 1. 재시도 로직을 포함한 세션 설정
def get_safe_session():
    session = requests.Session()
    # 연결 실패나 500번대 에러 발생 시 최대 3번까지 재시도
    retry_strategy = Retry(
        total=3,
        backoff_factor=1, # 실패 시 1초, 2초, 4초 간격으로 대기 후 시도
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_safe_session()

# 2. 브라우저 헤더 설정
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

# 타임아웃을 20초로 조금 더 늘림
TIMEOUT_SEC = 20
data = []

for i in range(3, 8):    
    if i > 6:
        url = "https://www.mnd.go.kr/user/newsInUserRecord.action?siteId=mnd&handle=I_669&id=mnd_020500000000"
        try:
            # session.get 사용
            response = session.get(url, headers=headers, timeout=TIMEOUT_SEC)
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
            
            # 페이지 간 간격
            time.sleep(1)
        except Exception as e:
            print(f"보도자료 크롤링 중 오류: {e}")

    else:
        for p in range(1, 3):
            url = f"https://www.mnd.go.kr/cop/kookbang/kookbangIlboList.do?siteId=mnd&pageIndex={p}&findType=&findWord=&categoryCode=dema000{i}&boardSeq=&startDate=&endDate=&id=mnd_020101000000"
            try:
                # session.get 사용
                response = session.get(url, headers=headers, timeout=TIMEOUT_SEC)
                response.raise_for_status()
                
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                items = soup.select(".post")
                
                categories = {3: "국방부", 4: "육군", 5: "해군", 6: "공군"}
                category = categories.get(i, "기타")

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
                
                # ⭐ 중요: 요청 간 휴식 시간을 2초로 늘려 서버 차단 방지
                time.sleep(2)
            except Exception as e:
                print(f"국방일보({category}, {p}페이지) 크롤링 중 오류: {e}")

# --- 이후 JSON 저장 로직 (동일) ---
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
