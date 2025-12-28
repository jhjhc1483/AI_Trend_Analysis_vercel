
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import json

url = "https://kookbang.dema.mil.kr/newsWeb/allToday.do"

response = requests.get(url)
html = response.text
soup = BeautifulSoup(html, 'html.parser')
data = []

# 모든 기사 li 기준으로 순회
for li in soup.select("li"):
    title_tag = li.select_one(".eps1")
    date_tag = li.select_one("span")
    link_tag = li.select_one("a")

    # 필수 요소가 없으면 건너뜀
    if not (title_tag and date_tag and link_tag):
        continue
    # 제목
    name = title_tag.get_text(strip=True)
    # 링크
    code = link_tag.get("href")
    link = str(f"https://kookbang.dema.mil.kr{code}")
    # 날짜 (예: 2025. 12. 18. 17:42)
    date_text = date_tag.get_text(strip=True)
    date = date_text.split(". ")
    year = date[0]
    month = date[1]
    day = date[2]
    time = date[3].split(":")
    hour = time[0]
    minute = time[1]

    data.append([name, link, year, month, day, hour, minute])

df13 = pd.DataFrame(data, columns=['제목','링크','년','월','일','시', '분'])
full_path = 'codes/kookbang.json'
# 폴더가 없으면 생성
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

# 새 데이터 합치기 및 중복 제거
new_data = df13.to_dict('records')
combined_data = existing_data + new_data

seen_titles = set()
final_data = []
for item in combined_data:
    link = item.get('제목')
    if link and link not in seen_titles:
        final_data.append(item)
        seen_titles.add(link)

# 최종 저장
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n작업 완료! 최종 데이터 수: {len(final_data)}개")