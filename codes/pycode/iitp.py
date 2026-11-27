"""
정보통신기획평가원(IITP) 크롤러

2026-11-27부터 IITP 서버가 해외(클라우드) IP의 접속을 응답 없이 끊어서
GitHub Actions(미국 서버)에서 Selenium으로 직접 열면 목록이 비어 있게 되었습니다.
그래서 국방부·방위사업청·KISTI처럼 ScraperAPI(한국 IP)를 거쳐 가져옵니다.
(ScraperAPI 키가 없으면 직접 접속 → 국내 PC에서 실행할 때는 그대로 동작)

- 먼저 JavaScript 렌더링 없이 가져오고(1크레딧), 목록이 비어 있을 때만 렌더링으로 한 번 더 시도(10크레딧)
- 한 건도 못 가져오면 '크롤링 중 오류'를 출력 → run_crawlers.py 가 실패로 판정해 2회차에 다시 시도하고 바로 알림
"""
import os
import re
import sys
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from crawler_common import BROWSER_HEADERS, fetch_page, save_results

# Windows 터미널(cp949) 출력 인코딩 방어
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# (목록 URL, 사이트에서 제목을 못 읽었을 때 쓸 분류명)
PAGES = [
    ("https://www.iitp.kr/web/lay1/program/S1T14C61/itfind/list.do?cpage=1&rows=10&searchTarget=all", "정부 정책자료"),
    ("https://www.iitp.kr/web/lay1/program/S1T62C65/itfind/list.do?cpage=1&rows=10&searchTarget=all", "AI · ICT Brief"),
    ("https://www.iitp.kr/web/lay1/program/S1T62C66/itfind/list.do?cpage=1&rows=10&searchTarget=all", "주간기술동향"),
    ("https://www.iitp.kr/web/lay1/program/S1T62C67/itfind/list.do?cpage=1&rows=10&searchTarget=all", "IITP 디지털 아웃룩"),
    ("https://www.iitp.kr/web/lay1/program/S1T62C68/itfind/list.do?cpage=1&rows=10&searchTarget=all", "ICT SPOT Issue"),
    ("https://www.iitp.kr/web/lay1/program/S1T62C69/itfind/list.do?cpage=1&rows=10&searchTarget=all", "ICT 10대 이슈"),
    ("https://www.iitp.kr/web/lay1/program/S1T62C226/itfind/list.do?cpage=1&rows=10&searchTarget=all", "IITP 디지털 통상 브리프"),
    ("https://www.iitp.kr/web/lay1/bbs/S1T62C70/A/21/list.do?cpage=1&sort=latest&rows=10", "정보통신산업진흥 연차보고서"),
    ("https://www.iitp.kr/web/lay1/bbs/S1T14C63/A/22/list.do?cpage=1&sort=latest&rows=10", "공개자료실"),
]

ITFIND_ITEM_SELECTOR = "#itfindList > div.board_list_area > ul > li"  # 보고서 목록 (program/.../itfind)
BBS_ITEM_SELECTOR = "#bbs_a_list > div.board_list_area > ul > li"      # 게시판 목록 (bbs/...)
LOOSE_ITEM_SELECTOR = "div.board_list_area > ul > li"                  # 바깥 id가 바뀌었을 때 대비
MAIN_TITLE_SELECTOR = "#v_sub_tit h2"
DATE_RE = re.compile(r"(\d{4})[-.](\d{1,2})[-.](\d{1,2})")

TIMEOUT_SEC = 60          # ScraperAPI 권장 대기 시간
DIRECT_TIMEOUT_SEC = 20   # 키 없이 직접 접속할 때
TIME_BUDGET_SEC = 220     # run_crawlers.py 의 스크립트당 제한(300초) 안에 저장까지 끝내기 위한 여유

HAS_SCRAPER_KEY = bool(os.environ.get("SCRAPER_API_KEY", "").strip())
if not HAS_SCRAPER_KEY:
    print("경고: ScraperAPI 키가 없어 직접 접속합니다. 해외 IP(GitHub Actions 등)에서는 IITP가 연결을 끊습니다.")

session = requests.Session()
_retry = Retry(total=1, backoff_factor=1, status_forcelist=[500, 502, 503, 504], raise_on_status=False)
session.mount("https://", HTTPAdapter(max_retries=_retry))
session.mount("http://", HTTPAdapter(max_retries=_retry))


def find_items(soup, list_url):
    primary = BBS_ITEM_SELECTOR if "/bbs/" in list_url else ITFIND_ITEM_SELECTOR
    return soup.select(primary) or soup.select(LOOSE_ITEM_SELECTOR)


def describe_page(response, soup):
    """목록을 못 찾았을 때 무엇을 받았는지 로그에 남김 (차단 페이지인지, 구조가 바뀐 건지 구분용)"""
    title = soup.title.get_text(strip=True) if soup.title else "(title 없음)"
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:150]
    return f"HTTP {response.status_code}, HTML {len(response.content):,}바이트, title='{title}', 본문 앞부분='{text}'"


def load_page(list_url, render):
    response = fetch_page(list_url, session=session, timeout=TIMEOUT_SEC, render=render,
                          headers=BROWSER_HEADERS, direct_timeout=DIRECT_TIMEOUT_SEC)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")  # 인코딩은 meta charset으로 자동 판별
    return response, soup


def parse_item(item, list_url, category):
    title_link_tag = item.select_one("div.tit_area > a") or item.select_one(".tit_area a, a[href*='view.do']")
    if not title_link_tag:
        return None
    href = (title_link_tag.get("href") or "").strip()
    if not href or href.startswith(("javascript:", "#")):
        return None
    title = title_link_tag.get_text(strip=True) or "제목 없음"
    link = urljoin(list_url, href)  # './view.do?...' → '.../itfind/view.do?...' (기존 저장 형식과 동일)

    year = month = day = ""
    date_element = item.select_one(".info_list_area li:nth-child(2) .txt")
    date_text = date_element.get_text(strip=True).replace("발행일:", "").strip() if date_element else ""
    parts = date_text.split("-")
    if len(parts) == 3:
        year, month, day = parts
    else:
        match = DATE_RE.search(item.get_text(" ", strip=True))
        if match:
            year, month, day = match.group(1), match.group(2).zfill(2), match.group(3).zfill(2)

    return [title, category, link, year, month, day]


data = []
failed_pages = 0
use_render = False      # 렌더링 없이는 목록이 안 나오는 사이트로 확인되면 이후 페이지도 렌더링
render_useless = False  # 렌더링해도 목록이 안 나왔으면 크레딧 낭비를 막기 위해 다시 시도하지 않음
start = time.time()

for index, (list_url, fallback_category) in enumerate(PAGES, start=1):
    if time.time() - start > TIME_BUDGET_SEC:
        print(f"[{index}/{len(PAGES)}] 시간 제한({TIME_BUDGET_SEC}초)에 가까워 남은 페이지는 건너뜁니다.")
        failed_pages += len(PAGES) - index + 1
        break

    print(f"[{index}/{len(PAGES)}] 페이지 로드 중... : {list_url}")
    try:
        response, soup = load_page(list_url, render=use_render)
        items = find_items(soup, list_url)

        if not items and HAS_SCRAPER_KEY and not use_render and not render_useless:
            print(f"   [!] 목록이 비어 있음 ({describe_page(response, soup)}) → JavaScript 렌더링으로 다시 시도")
            response, soup = load_page(list_url, render=True)
            items = find_items(soup, list_url)
            if items:
                use_render = True
            else:
                render_useless = True

        if not items:
            failed_pages += 1
            print(f"   [X] 크롤링 중 오류: 목록을 찾지 못함 ({describe_page(response, soup)})")
            continue

        category_element = soup.select_one(MAIN_TITLE_SELECTOR)
        category = category_element.get_text(strip=True) if category_element else fallback_category
        rows = [row for row in (parse_item(item, list_url, category) for item in items) if row]
        data.extend(rows)
        print(f"   [O] 분류: {category} | 항목 {len(rows)}개")

    except Exception as e:
        failed_pages += 1
        print(f"   [X] 크롤링 중 오류: {type(e).__name__}: {e}")

if failed_pages:
    print(f"⚠️ {len(PAGES)}개 페이지 중 {failed_pages}개 실패")

df11 = pd.DataFrame(data, columns=['제목', '분류', '링크', '년', '월', '일'])
df11['제목'] = df11['제목'].fillna('').str.replace(r'\\', '', regex=True)
df11['제목'] = df11['제목'].str.replace('\'', '＇', regex=False).str.replace('\"', '〃', regex=False)

# 기존 데이터와 합쳐 중복 제거 후 저장 (crawler_common.save_results)
full_path = 'codes/iitp.json'
save_results(df11.to_dict('records'), full_path, "IITP")
