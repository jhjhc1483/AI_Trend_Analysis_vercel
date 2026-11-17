import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

from crawler_common import save_results

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
# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/KISDI.json'
save_results(df8.to_dict('records'), full_path, "KISDI")
