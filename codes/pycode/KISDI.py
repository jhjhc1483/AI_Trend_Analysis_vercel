import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json

url = ["https://www.kisdi.re.kr/report/list.do?key=m2101113024153&arrMasterId=3934560","https://www.kisdi.re.kr/report/list.do?key=m2101113024770&arrMasterId=3934580","https://www.kisdi.re.kr/report/list.do?key=m2101113024973&arrMasterId=3934581","https://www.kisdi.re.kr/report/list.do?key=m2104225467881&arrMasterId=3934586","https://www.kisdi.re.kr/report/list.do?key=m2101113025536&arrMasterId=3934550","https://www.kisdi.re.kr/report/list.do?key=m2102058837181&arrMasterId=4334696","https://www.kisdi.re.kr/report/list.do?key=m2101113025790&arrMasterId=4333447","https://www.kisdi.re.kr/report/list.do?key=m2101113025377&arrMasterId=4333446"]
data = []
for i in range(0,8):
    response = requests.get(url[i])
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    pattern = r'<h3>(.+?)</h3>'
    category_temp = str(soup.select(".fs_sub_visual > div > h3"))
    match = re.search(pattern, category_temp)
    category = match.group(1)
    items=soup.select(".board_list > ul > li")
    a=1
    for item in items:
        name = item.select_one(".board_list > ul > li > a > strong").text
        link_temp = item.select_one(".board_list > ul > li > a").attrs['onclick']
        numbers = re.findall(r"'\d+'", link_temp)
        clean_numbers = [n.replace("'", "") for n in numbers]
        link = f"https://www.kisdi.re.kr/report/view.do?key=m2101113024153&masterId={clean_numbers[0]}&arrMasterId={clean_numbers[0]}&artId={clean_numbers[1]}"

        date_temp = soup.select_one(f".board_list > ul > li:nth-child({a}) > a > ul > li:nth-child(2)").text
        date = date_temp.replace("발행일", "").strip()
        date_temp_list = date.split('-')
        years = date_temp_list[0]
        month = date_temp_list[1]
        day = date_temp_list[2]
        a = a+1
    
        data.append([name, category, link, years,month,day])

        
df8 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
full_path = 'codes/KISDI.json'
new_data = df8.to_dict('records')

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

# 3. 중복 제거 (가장 중요한 단계)
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
