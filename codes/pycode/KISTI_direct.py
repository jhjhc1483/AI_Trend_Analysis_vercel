import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 1. 세션 및 재시도(Retry) 설정
def get_safe_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_safe_session()

# 브라우저 User-Agent 및 헤더 설정 (ScraperAPI 대신 직접 요청)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

TIMEOUT_SEC = 25

# KISTI 보고서 카테고리 URL
url = [
    "https://www.kisti.re.kr/post/policy-report",       # S&T Policy Report
    "https://www.kisti.re.kr/post/data-insight",         # 데이터 인사이트
    "https://www.kisti.re.kr/post/asti-insight",         # ASTI 마켓 인사이트
    "https://www.kisti.re.kr/post/analysis-report",      # R&I Report
]

data = []

for target_url in url:
    print(f"--- {target_url} 수집 중 ---")
    try:
        response = session.get(target_url, headers=headers, timeout=TIMEOUT_SEC)
        response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 카테고리명 추출 시도
        category = "알수없음"

        category_tag = soup.select_one(".tit_nav.tit_nav_bg04>h1")
        if category_tag:
            category = category_tag.text.strip()

        if category == "알수없음":
            title_tag = soup.select_one("title")
            if title_tag:
                title_text = title_tag.text.strip()
                parts = [p.strip() for p in title_text.split('|')]
                if parts:
                    category = parts[0].strip()

        if category == "알수없음" or not category:
            url_category_map = {
                "policy-report": "S&T Policy Report",
                "data-insight": "데이터 인사이트",
                "asti-insight": "ASTI 마켓 인사이트",
                "analysis-report": "R&I Report",
            }
            for key, val in url_category_map.items():
                if key in target_url:
                    category = val
                    break

        # 게시글 목록 파싱 (구조별 fallback 지원)
        items = soup.select(".text_wrap")

        if not items:
            items = soup.select(".board_list li, .bbs_list li, .list_wrap li")

        if not items:
            items = soup.select("table.board_list tbody tr, .tbl_list tbody tr")

        if not items:
            items = soup.select(".card_list .card_item, .post_list .post_item")

        print(f"  카테고리: {category}, 발견된 항목 수: {len(items)}")

        for item in items:
            try:
                anchor = item.select_one("a")
                if not anchor:
                    if item.name == 'a':
                        anchor = item
                    else:
                        continue

                code = anchor.attrs.get('href', '')
                if not code or code.startswith('javascript:'):
                    continue

                link = code if "https://" in code else f"https://www.kisti.re.kr{code}"

                # URL에서 jsessionid 및 쿼리 파라미터(?t= 등) 제거하여 중복 방지
                if ';jsessionid=' in link:
                    link = link.split(';jsessionid=')[0]
                if '?' in link:
                    link = link.split('?')[0]

                # 네비게이션/메뉴 링크 필터링
                if any(skip in link for skip in ['/intro/', '/notifications/', '/mspt/', '/government/', '/promote/', '/research/', '/pageView/', '#']):
                    continue

                name = anchor.text.strip()
                if not name or len(name) < 3:
                    continue

                # 날짜 추출
                date_tag = item.select_one(".date, .txt_date, .info_date, time")
                years = ""
                month = ""
                day = ""

                if date_tag:
                    date_text = date_tag.text.strip()
                    date_temp = re.split(r'[.\-/]', date_text)
                    date_temp = [d.strip() for d in date_temp if d.strip()]

                    if len(date_temp) >= 3:
                        years = date_temp[0]
                        month = date_temp[1]
                        day = date_temp[2]

                data.append([name, category, link, years, month, day])
            except Exception as e:
                print(f"  항목 파싱 중 오류: {e}")
                continue

        time.sleep(1)

    except Exception as e:
        print(f"URL 접속 중 오류 발생 ({target_url}): {e}")
        continue

# 2. 데이터프레임 생성 및 정제
df10 = pd.DataFrame(data, columns=['제목', '분류', '링크', '년', '월', '일'])
full_path = 'codes/KISTI.json'
os.makedirs(os.path.dirname(full_path), exist_ok=True)

new_data = df10.to_dict('records')

# 3. 기존 데이터 로드 및 중복 제거
existing_data = []
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
    except Exception as e:
        print(f"기존 JSON 로드 오류: {e}")

combined_data = existing_data + new_data
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크')
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)

# 4. 파일 저장
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"[KISTI(직접 요청)] 완료: 신규 {len(new_data)}건 수집 | 기존 {len(existing_data)}건 병합 | 최종 {len(final_data)}건 저장 ({full_path})")
