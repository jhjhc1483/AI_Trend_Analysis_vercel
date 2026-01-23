import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import json
import os
import re

data = []
for i in range(1,4):
    response = requests.get(f"https://www.aitimes.kr/news/articleList.html?page={i}&total=22766&box_idxno=&view_type=sm")
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    items=soup.select(".view-cont")
    for item in items:
        name = item.select_one(".titles").text
        code = item.select_one(".titles > a").attrs['href']
        link = f"https://www.aitimes.kr{code}"
        pattern = r'<em>(.+?)</em>'
        date_temp= str(item.select_one(".byline > em:nth-child(3)"))
        match = re.search(pattern, date_temp)
        if match:
            date_all = match.group(1)
            date = date_all.split(" ")
            temp = str(date[0]).split(".")
            years = temp[0]
            month = temp[1]
            day = temp[2]
            temp = str(date[1]).split(":")
            hour = temp[0]
            minute = temp[1]
        
        data.append([name, link, years, month, day, hour, minute])

df12 = pd.DataFrame(data, columns=['기사명','링크','년','월','일','시','분'])
df12['기사명'] = df12['기사명'].fillna('')
df12['기사명'] = df12['기사명'].str.replace('\\', '', regex=False)
df12['기사명'] = df12['기사명'].str.replace('\'', '＇', regex=False)
df12['기사명'] = df12['기사명'].str.replace('\"', '〃', regex=False)
new_data = df12.to_dict('records')
full_path = 'codes/AInews.json'


existing_data = []

# 1. 기존 JSON 파일 로드
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            # 파일이 비어있지 않은지 확인 후 로드
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

# indent=4와 force_ascii=False 옵션을 유지하여 가독성 및 한글 보존
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n최종 데이터가 '{full_path}'에 성공적으로 저장되었습니다.")
