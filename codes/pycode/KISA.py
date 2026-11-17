from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd

from crawler_common import save_results

chrome_options = Options()
chrome_options.add_argument("--headless")  # 화면 안 띄우기
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")


service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

url = ["https://www.kisa.or.kr/201","https://www.kisa.or.kr/20207","https://www.kisa.or.kr/20305"]
data = []
try:
    for i in range(0, 3):
        driver.get(url[i])

        time.sleep(2) 
        category_temp = driver.find_element(By.CSS_SELECTOR, ".h2_type_1").text.strip()
        items = driver.find_elements(By.CSS_SELECTOR, "table.tbl_board tbody tr")
        for item in items:
            try:
                # 1. 제목 추출
                title_el = item.find_element(By.CSS_SELECTOR, "td.sbj.txtL a")
                name = title_el.text.strip()
                category = category_temp
                date = item.find_element(By.CSS_SELECTOR, "td.date").text.strip()
                date_temp = date.split("-")
                years = date_temp[0]
                month = date_temp[1]
                day = date_temp[2]
                link_element = item.find_element(By.CSS_SELECTOR, 'td.sbj.txtL a')
                link = link_element.get_attribute('href')
                if name and years and month and day and link:
                    data.append([name,category, link, years, month, day])

            except Exception as e:
                continue

finally:
    driver.quit() 

print(f"\n총 {len(data)} 건 추출 완료")

df16 = pd.DataFrame(data, columns=['제목','분류','링크','년','월','일'])
# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/KISA.json'
save_results(df16.to_dict('records'), full_path, "KISA")
