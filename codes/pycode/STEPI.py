import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json
url = ["https://www.stepi.re.kr/site/stepiko/ex/bbs/reportCateList.do?cateTypeCd=STEPI_REPORT","https://www.stepi.re.kr/site/stepiko/ex/bbs/reportCateList.do?cateTypeCd=A05"]

data = []
for i in range(0,2):
    response = requests.get(url[i])
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    items=soup.select(".boardList > li")
    for item in items:
        name_temp = item.select_one(".boardList > li > div.title > a >b")
        name_temp = str(name_temp)
        soup = BeautifulSoup(name_temp, "html.parser")
        name = soup.find('b').get_text()
        # name = str(match.group(1))
        pattern = r'<em>(.+?)</em>'
        category_temp = str(item.select_one(".boardList > li > div.title > a "))
        match = re.search(pattern, category_temp)
        category = match.group(1)
        date_temp = item.select_one(".info > span:nth-child(2)")
        #bbsFVo > ul > li:nth-child(1) > div.info > span:nth-child(2)
        date_temp = str(date_temp)
        pattern = r'<span>(.+?)</span>'
        match = re.search(pattern, date_temp)
        date_temp = match.group(1)
        date_temp_list = date_temp.split('-')
        years = date_temp_list[0]
        month = date_temp_list[1]
        day = date_temp_list[2]
        link_temp = str(item.select_one(".title > a").attrs['href'])
        pattern = r"reportView\((\d+),'([^']+)'\)"
        match = re.search(pattern, link_temp)
        value1 = match.group(1) # 첫 번째 괄호로 묶인 그룹 (93)
        value2 = match.group(2) # 두 번째 괄호로 묶인 그룹 (A0204)
        link = f"https://www.stepi.re.kr/site/stepiko/report/View.do?pageIndex=1&cateTypeCd=STEPI_REPORT&tgtTypeCd=ALL&searchType=&reIdx={value1}&cateCont={value2}&cbIdx=0&searchKey="
        data.append([name,category,link,years,month,day])
      
df6 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
full_path = 'codes/STEPI.json'
new_data = df6.to_dict('records') # 새 DataFrame을 리스트 오브 딕셔너리 형태로 변환

# ----------------- JSON 이어 붙이기 및 중복 제거 로직 시작 -----------------

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

# 2. 새 데이터와 기존 데이터를 합치기
combined_data = existing_data + new_data

# 3. 중복 제거 (가장 중요한 단계)
# '링크'를 기준으로 중복 제거를 위한 Set을 생성합니다.
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크') # '링크' 컬럼 값을 가져옵니다.
    
    # '링크'가 None이거나 비어있지 않고, 아직 처리하지 않은 링크인 경우에만 추가
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)
        
print(f"총 {len(existing_data)}개의 기존 데이터와 {len(new_data)}개의 새 데이터를 합쳤습니다.")
print(f"중복을 제거한 후 최종 데이터는 총 {len(final_data)}개입니다.")

# 4. 최종 데이터를 JSON 파일로 저장 (덮어쓰기)
# indent=4와 force_ascii=False 옵션을 유지하여 가독성 및 한글 보존
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"\n최종 데이터가 '{full_path}'에 성공적으로 저장되었습니다.")
