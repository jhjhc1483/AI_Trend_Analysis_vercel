import requests
from bs4 import BeautifulSoup
import pandas as pd

from crawler_common import fetch_page, save_results

target_url = "https://kookbang.dema.mil.kr/newsWeb/allToday.do"

data = []

try:
    # ScraperAPI(한국 IP)로 요청, 키가 없으면 직접 요청 (타임아웃 30초)
    response = fetch_page(target_url, timeout=30)
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

except requests.exceptions.RequestException as e:
    print(f"웹페이지 우회 요청 중 오류 발생: {e}")

# 4. 데이터 저장 로직 (기존과 동일)
df13 = pd.DataFrame(data, columns=['제목','링크','년','월','일','시', '분'])
# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/kookbang.json'
# 국방일보는 같은 기사가 다른 링크로 올라오는 경우가 있어 제목 기준으로 중복 제거
save_results(df13.to_dict('records'), full_path, "국방일보", key="제목")
