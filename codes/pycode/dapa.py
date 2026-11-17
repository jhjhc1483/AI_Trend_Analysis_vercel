import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

from crawler_common import fetch_page, save_results

target_url = "https://www.dapa.go.kr/dapa/doc/selectDocList.do?menuSeq=3069&bbsSeq=326"

data = []

try:
    # ScraperAPI(한국 IP)로 요청, 키가 없으면 직접 요청 (타임아웃 30초)
    response = fetch_page(target_url, timeout=30)
    response.raise_for_status()
    
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    category = "방사청 보도자료"
    
    for a in range(1, 11):
        # 예외 처리를 추가하여 페이지 구조 변경 시 전체가 죽지 않도록 방어
        try:
            name_elem = soup.select_one(f".list-table > tbody > tr:nth-child({a}) > td > a > p")
            link_elem = soup.select_one(f".list-table > tbody > tr:nth-child({a}) > td > a ")
            date_elem = soup.select_one(f".list-table > tbody > tr:nth-child({a}) > td:nth-child(3)")
            
            if name_elem and link_elem and date_elem:
                name = name_elem.text.strip()
                link_temp = link_elem.attrs.get('onclick', '')
                code = link_temp.split("'")[1] if "'" in link_temp else ""
                
                link = f"https://www.dapa.go.kr/dapa/doc/selectDoc.do?docSeq={code}&menuSeq=3069&bbsSeq=326&currentPageNo=1&recordCountPerPage=10"
                
                date = date_elem.text.strip()
                date_temp_list = date.split('-')
                if len(date_temp_list) == 3:
                    years, month, day = date_temp_list
                    data.append([name, category, link, years, month, day])
        except AttributeError as e:
            print(f"{a}번째 항목 파싱 중 오류: {e}")
            continue

except requests.exceptions.RequestException as e:
    print(f"웹페이지 요청 중 오류 발생: {e}")

df9 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
os.makedirs('codes', exist_ok=True)
# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/dapa.json'
save_results(df9.to_dict('records'), full_path, "방사청")
