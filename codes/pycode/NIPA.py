import requests
from bs4 import BeautifulSoup
import pandas as pd

from crawler_common import save_results
url = ["https://www.nipa.kr/home/2-7-1-1","https://www.nipa.kr/home/2-7-1-2"]
data = []
for i in range(0,2):
    a=0
    response = requests.get(url[i])
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    items=soup.select(".tl")
    for item in items:
        a = a+1
        name = item.select_one(".tl > a").text.strip()
        category = soup.select_one(".board_tab.cf > li > p > a").text
        link_temp = item.select_one(".tl > a").attrs['href']
        link = "https://www.nipa.kr"+ link_temp
        date_temp = soup.select_one(f".table.tb01 > tbody > tr:nth-child({a}) > td:nth-child(6)").text.strip()
        date_temp_list= date_temp.split('-')
        years = date_temp_list[0]
        month = date_temp_list[1]
        day = date_temp_list[2]
        data.append([name, category, link, years,month,day])
df7 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/NIPA.json'
save_results(df7.to_dict('records'), full_path, "NIPA")
