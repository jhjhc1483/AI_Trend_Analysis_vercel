import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

from crawler_common import save_results
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
        pattern = r"reportView\d?\('?(\d+)'?,'([^']+)'\)"
        match = re.search(pattern, link_temp)
        value1 = match.group(1).strip("'") # 첫 번째 괄호로 묶인 그룹 (93)
        value2 = match.group(2) # 두 번째 괄호로 묶인 그룹 (A0204)
        link = f"https://www.stepi.re.kr/site/stepiko/report/View.do?pageIndex=1&cateTypeCd=STEPI_REPORT&tgtTypeCd=ALL&searchType=&reIdx={value1}&cateCont={value2}&cbIdx=0&searchKey="
        data.append([name,category,link,years,month,day])
      
df6 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/STEPI.json'
save_results(df6.to_dict('records'), full_path, "STEPI")
