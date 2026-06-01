import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json
import time
import urllib.parse
import base64

import itertools

# 환경 변수에서 API 키 불러오기 (로테이션 지원)
API_KEYS = [
    os.environ.get('SCRAPER_API_KEY'),
    os.environ.get('SCRAPER_API_KEY_2')
]
# None이 아닌 키만 필터링
SCRAPER_KEYS = [k for k in API_KEYS if k]

if not SCRAPER_KEYS:
    raise ValueError("GitHub Secrets 또는 .env에 SCRAPER_API_KEY가 설정되지 않았습니다.")

# API 키 순환을 위한 이터레이터 생성
key_cycle = itertools.cycle(SCRAPER_KEYS)

SCRAPER_URL = 'http://api.scraperapi.com'

# 1. 재시도 로직을 포함한 세션 설정
def get_safe_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1, 
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_safe_session()

# 우회 시 API 서버 자체의 헤더를 사용하는 것이 유리하므로 기존 headers는 제거하거나 기본값 사용
TIMEOUT_SEC = 30 # 우회 API를 거치므로 타임아웃을 넉넉히 설정
data = []

# ===== 새로운 국방부 홈페이지 구조 (2025년 리뉴얼) =====
# 국방뉴스 카테고리별 URL 매핑
# 159: 국방부, 160: 육군, 161: 해군/해병대, 162: 공군, 167: 보도자료
news_pages = [
    {"url": "https://www.mnd.go.kr/mnd/159/subview.do", "category": "국방부"},
    {"url": "https://www.mnd.go.kr/mnd/160/subview.do", "category": "육군"},
    {"url": "https://www.mnd.go.kr/mnd/161/subview.do", "category": "해군"},
    {"url": "https://www.mnd.go.kr/mnd/162/subview.do", "category": "공군"},
    {"url": "https://www.mnd.go.kr/mnd/167/subview.do", "category": "국방부 보도자료"},
]

for page_info in news_pages:
    target_url = page_info["url"]
    category = page_info["category"]

    payload = {
        'api_key': next(key_cycle),
        'url': target_url,
        'country_code': 'kr'  # 한국 IP 지정
    }

    try:
        print(f"--- {category} 수집 중 ({target_url}) ---")
        # 타겟 URL 대신 ScraperAPI 서버로 요청
        response = session.get(SCRAPER_URL, params=payload, timeout=TIMEOUT_SEC)
        response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 새 BBS 구조: .thumnailWrap.webzine > ul > li 형태
        items = soup.select(".thumnailWrap.webzine li")
        
        if not items:
            # 대체 시도: 일반 게시판 목록 형태 (.board-list 또는 .board-table 내부의 테이블)
            items = soup.select(".board-list tbody tr, .board-table tbody tr")

        print(f"  발견된 게시글 수: {len(items)}")

        for item in items:
            try:
                # 웹진(카드) 형태 파싱
                anchor = item.select_one("a[href*='artclView']")
                if not anchor:
                    anchor = item.select_one("a[href*='/bbs/']")
                if not anchor:
                    # 테이블 형태의 게시판에서 링크 찾기
                    anchor = item.select_one("td.title a, td a.title")
                if not anchor:
                    continue

                # 제목 추출
                title_tag = anchor.select_one(".title span span")
                if not title_tag:
                    title_tag = anchor.select_one(".title span")
                if not title_tag:
                    title_tag = anchor.select_one("strong.title")
                if not title_tag:
                    title_tag = anchor
                name = title_tag.text.strip()
                # "새글" 태그 제거
                name = re.sub(r'\s*새글\s*$', '', name).strip()

                if not name:
                    continue

                # 링크 추출
                href = anchor.get('href', '')
                if href.startswith('/'):
                    # 모바일에서 보기 편한 서브뷰 링크 형태로 변환
                    category_id = target_url.split('/')[-2] # 예: 159, 160 등
                    # subview.do는 페이지 파라미터가 없으면 본문을 불러오지 못하는 문제가 있으므로 추가
                    href_with_query = f"{href}?page=1&"
                    encoded_href = urllib.parse.quote(href_with_query, safe='')
                    full_string = f"fnct1|@@|{encoded_href}"
                    enc = base64.b64encode(full_string.encode('utf-8')).decode('utf-8')
                    link = f'https://www.mnd.go.kr/mnd/{category_id}/subview.do?enc={enc}'
                elif href.startswith('http'):
                    link = href
                else:
                    continue

                # 날짜 추출 (등록일 : YYYY.MM.DD 형태)
                date_text = ""
                detail_items = item.select(".detail li")
                for detail_li in detail_items:
                    strong = detail_li.select_one("strong")
                    if strong and "등록일" in strong.text:
                        date_text = detail_li.text.replace(strong.text, "").strip()
                        break

                # 테이블 형태에서 날짜 찾기
                if not date_text:
                    # 모든 td를 가져와서 텍스트 중 YYYY.MM.DD 형태가 있는지 찾음
                    all_tds = item.select("td")
                    for td in all_tds:
                        date_match = re.search(r'(202\d[.\-/]\d{2}[.\-/]\d{2})', td.text)
                        if date_match:
                            date_text = date_match.group(1)
                            break

                if date_text:
                    # YYYY.MM.DD 또는 YYYY-MM-DD 형태 파싱
                    date_parts = re.split(r'[.\-/]', date_text)
                    date_parts = [d.strip() for d in date_parts if d.strip()]
                    if len(date_parts) >= 3:
                        years = date_parts[0]
                        month = date_parts[1]
                        day = date_parts[2]
                        data.append([name, category, link, years, month, day, "", ""])
                    else:
                        data.append([name, category, link, "", "", "", "", ""])
                else:
                    data.append([name, category, link, "", "", "", "", ""])

            except Exception as e:
                print(f"  항목 파싱 중 오류: {e}")
                continue

        time.sleep(2)
    except Exception as e:
        print(f"국방뉴스({category}) 크롤링 중 오류: {e}")

df5 = pd.DataFrame(data, columns=['기사명','분류','링크','년','월','일','시','분'])
os.makedirs('codes', exist_ok=True)
full_path = 'codes/mnd.json'
new_data = df5.to_dict('records')

existing_data = []
if os.path.exists(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                existing_data = json.loads(content)
    except Exception as e:
        print(f"기존 파일 로드 실패: {e}")

combined_data = existing_data + new_data
seen_links = set()
final_data = []

for item in combined_data:
    link = item.get('링크')
    if link and link not in seen_links:
        final_data.append(item)
        seen_links.add(link)

with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"[국방부] 완료: 신규 {len(new_data)}건 수집 | 기존 {len(existing_data)}건 병합 | 최종 {len(final_data)}건 저장 ({full_path})")
