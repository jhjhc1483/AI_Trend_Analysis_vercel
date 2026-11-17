from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import urllib.parse

from crawler_common import save_results



# 1. 헤드리스 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless")  # 화면 안 띄우기
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# 2. 드라이버 실행
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

url = "https://www.tta.or.kr/tta/weeklyDataList?rep=1&key=310"
data = []
try:
    driver.get(url)
    
    # NextJS Hydration 및 데이터를 클라이언트에서 호출하는데 필요한 시간을 위해 5초 대기
    time.sleep(5) 
    label_element = driver.find_element(By.CSS_SELECTOR, "[class*='SubGnb_labelContainer__']")
    label_text = label_element.text.strip()
    
    items = driver.find_elements(By.CSS_SELECTOR, "tr[class*='Board_row__']")
    for item in items:
        try:
            # 1. 제목 추출 (Board_titleCell 클래스 포함 요소)
            title_el = item.find_element(By.CSS_SELECTOR, "td[class*='Board_titleCell__']")
            name = title_el.text.strip()
            category = label_text
            # 2. 등록일 추출
            # 같은 클래스가 여러 개이므로, 데이터 라벨이나 순서를 이용하는 게 정확합니다.
            date_temp = item.find_element(By.CSS_SELECTOR, "td[data-label='등록일']").text.strip()
            date = date_temp.split("-")
            years = date[0]
            month = date[1]
            day = date[2]
            # 3. 링크 추출
            link = ""
            try:
                # 1순위: 제목 td 안의 a 태그
                link_el = title_el.find_element(By.TAG_NAME, "a")
                link = link_el.get_attribute("href")
            except:
                try:
                    # 2순위: 행(tr) 전체에서 첫 번째 a 태그
                    link_el = item.find_element(By.TAG_NAME, "a")
                    link = link_el.get_attribute("href")
                except Exception as link_err:
                    # 3순위: 링크를 전혀 못 찾을 경우 고유 ID 생성 (중복 제거 방어용)
                    safe_name = urllib.parse.quote(name)
                    link = f"{url}&title={safe_name}"
            
            if name and years and month and day and link:
                # print(f"추출 성공: {name} | {link}") # 디버깅용
                data.append([name, category, link, years, month, day])
            
        except Exception as e:
            continue

finally:
    driver.quit()

print(f"\n총 {len(data)} 건 추출 완료")

df17 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
df17

# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/tta.json'
save_results(df17.to_dict('records'), full_path, "TTA")
