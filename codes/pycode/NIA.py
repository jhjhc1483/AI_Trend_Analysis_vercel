import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

from crawler_common import save_results
# =============================================================
# 셀 4: NIA 웹 크롤링 및 데이터 수집 로직
# =============================================================

# NIA 메인 페이지에 올라온 최신 5가지만 크롤링
response = requests.get("https://nia.or.kr/site/nia_kor/main.do;jsessionid=6EACE24EADAB8A749EFCC1293267C284.33f82d3a14ca06361270")
html = response.text
soup = BeautifulSoup(html, 'html.parser')

data = []
items=soup.select(".article.know")

for i in range(1, 6):
    try:
        selector_base = f".article.know > ul > li:nth-child({i}) > a"
        name = soup.select_one(selector_base).attrs['title']
        name = name.rstrip('}')
        category = soup.select_one(f"{selector_base} > span.category").text
        code0 = soup.select_one(selector_base).attrs['onclick']
        
        pattern = re.compile(r"'([^']*)'")
        raw_arguments = pattern.findall(code0)
        extracted_numbers = [arg for arg in raw_arguments if arg.isdigit()]
        
        code1 = extracted_numbers[0]
        code2 = extracted_numbers[1]
        code3 = extracted_numbers[2]
        link = f'https://nia.or.kr/site/nia_kor/ex/bbs/View.do?cbIdx={code1}&bcIdx={code2}&parentSeq={code3}'
        
        response = requests.get(link)
        html3 = response.text
        soup3 = BeautifulSoup(html3, 'html.parser')
        
        html_string = soup3.select_one(".src>em").text
        date_parts = html_string.split('.')
        year = date_parts[0]
        month = date_parts[1]
        day = date_parts[2]
        
        data.append([name, category, link, year, month, day])
        
    except AttributeError as e:
        print(f"항목 {i} 처리 중 셀렉터 오류 발생: {e}")
    except IndexError as e:
        print(f"항목 {i} 처리 중 인자 추출 오류 발생: {e}")
    except Exception as e:
        print(f"항목 {i} 처리 중 예상치 못한 오류 발생: {e}")


# =============================================================
# 셀 5: DataFrame 생성 및 출력
# =============================================================
df3 = pd.DataFrame(data, columns=['제목', '분류', '링크', '년', '월', '일'])


# =============================================================
# 셀 6: JSON 파일 이어 붙이기 및 저장 로직 (경로 수정됨)
# =============================================================

# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/nia.json'
save_results(df3.to_dict('records'), full_path, "NIA")
