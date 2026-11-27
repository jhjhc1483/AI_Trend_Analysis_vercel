"""
정보통신기획평가원(IITP) 크롤러

[구조 점검 및 동작 원리]
- IITP 목록 페이지(list.do)는 서버 렌더링 HTML이 아니라 Vue.js 클라이언트 렌더링(CSR) 페이지입니다.
- 단순 GET(render=False)으로 list.do HTML을 가져오면 `#itfindList > div.board_list_area > ul > li` 안에
  `<li v-if="list.length === 0">`, `<li v-for="(item, idx) in list">` 같은 빈 Vue 템플릿 `<li>`가 들어 있고,
  `#v_sub_tit h2`에도 `{{sub_tit}}` 템플릿 문자열만 들어 있습니다.
- 따라서:
  1) 1차(기본, 페이지당 1크레딧): Vue.js가 실제로 데이터를 받아오는 백엔드 API
     - 보고서(itfind): POST https://www.iitp.kr/program-svc/api/itfind/list.do (XML 응답)
     - 게시판(bbs):    POST https://www.iitp.kr/board-svc/api/bbs/A/list.do (JSON 응답)
     를 호출해 9개 페이지(총 91건)를 빠르게 가져옵니다. (ScraperAPI 키가 있으면 한국 IP 경유, 없으면 직접 호출)
  2) 2차(폴백, 페이지당 10크레딧): 만약 백엔드 API 구조가 바뀌어 실패하면 ScraperAPI JavaScript 렌더링(render=True)으로
     실제 렌더링된 DOM을 가져와 CSS Selector로 파싱합니다. (미렌더링 Vue 템플릿 `<li>`는 자동 제외)
"""
import html
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from crawler_common import BROWSER_HEADERS, SCRAPER_URL, fetch_page, save_results

# Windows 터미널(cp949) 출력 인코딩 방어
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# (목록 URL, 분류명)
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

# itfind 메뉴별 (api_cat, api_list_url) 매핑 (/program-svc/api/itfind/itfindInfo.do 응답값)
ITFIND_API_MAP = {
    "61": ("K_STAT_01", "statisticsList.do"),
    "65": ("B_ITA_16", "periodicalList.do"),
    "66": ("B_ITA_01", "weeklyIctTrendList.do"),
    "67": ("B_ITA_36", "periodicalList.do"),
    "68": ("B_ITA_17", "periodicalList.do"),
    "69": ("B_ITA_02", "periodicalList.do"),
    "226": ("B_ITA_37", "periodicalList.do"),
}

ITFIND_INFO_API_URL = "https://www.iitp.kr/program-svc/api/itfind/itfindInfo.do"
ITFIND_LIST_API_URL = "https://www.iitp.kr/program-svc/api/itfind/list.do"
BBS_LIST_API_URL = "https://www.iitp.kr/board-svc/api/bbs/A/list.do"

ITFIND_ITEM_SELECTOR = "#itfindList > div.board_list_area > ul > li"  # 보고서 목록 (program/.../itfind)
BBS_ITEM_SELECTOR = "#bbs_a_list > div.board_list_area > ul > li"      # 게시판 목록 (bbs/...)
LOOSE_ITEM_SELECTOR = "div.board_list_area > ul > li"                  # 바깥 id가 바뀌었을 때 대비
MAIN_TITLE_SELECTOR = "#v_sub_tit h2"
DATE_RE = re.compile(r"(\d{4})[-.](\d{1,2})[-.](\d{1,2})")
MENU_SEQ_RE = re.compile(r"S\d+T\d+C(\d+)")

TIMEOUT_SEC = 60          # ScraperAPI 권장 대기 시간
DIRECT_TIMEOUT_SEC = 20   # 키 없이 직접 접속할 때
TIME_BUDGET_SEC = 220     # run_crawlers.py 의 스크립트당 제한(300초) 안에 저장까지 끝내기 위한 여유

HAS_SCRAPER_KEY = bool(os.environ.get("SCRAPER_API_KEY", "").strip())
if not HAS_SCRAPER_KEY:
    print("경고: ScraperAPI 키가 없어 직접 접속합니다. 해외 IP(GitHub Actions 등)에서는 IITP가 연결을 끊을 수 있습니다.")

session = requests.Session()
_retry = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504], raise_on_status=False)
session.mount("https://", HTTPAdapter(max_retries=_retry))
session.mount("http://", HTTPAdapter(max_retries=_retry))


def post_api(api_url, payload, referer=None):
    """
    IITP 백엔드 JSON API에 POST 요청을 보냅니다.
    - SCRAPER_API_KEY가 있으면 ScraperAPI(한국 IP, render=False, 1크레딧)를 경유
    - 없으면 직접 POST 요청
    """
    headers = {
        **BROWSER_HEADERS,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
    }
    if referer:
        headers["Referer"] = referer

    api_key = os.environ.get("SCRAPER_API_KEY", "").strip()
    if api_key:
        params = {"api_key": api_key, "url": api_url, "country_code": "kr"}
        return session.post(SCRAPER_URL, params=params, json=payload, headers=headers, timeout=TIMEOUT_SEC)
    return session.post(api_url, json=payload, headers=headers, timeout=DIRECT_TIMEOUT_SEC)


def split_date(date_str):
    if not date_str:
        return "", "", ""
    match = DATE_RE.search(str(date_str).strip())
    if match:
        return match.group(1), match.group(2).zfill(2), match.group(3).zfill(2)
    return "", "", ""


def clean_html_text(raw_text):
    """HTML 엔티티(&amp;, &#039; 등) 및 태그가 섞인 제목을 순수 텍스트로 정리"""
    if not raw_text:
        return ""
    unescaped = html.unescape(str(raw_text))
    if "<" in unescaped and ">" in unescaped:
        unescaped = BeautifulSoup(unescaped, "html.parser").get_text(" ", strip=True)
    return unescaped.strip()


def fetch_via_backend_api(list_url, category):
    """
    Vue.js가 호출하는 IITP 백엔드 API에서 직접 게시글 목록을 가져옵니다.
    성공 시 [[제목, 분류, 링크, 년, 월, 일], ...] 리스트 반환.
    """
    m = MENU_SEQ_RE.search(list_url)
    if not m:
        return []
    cms_menu_seq = m.group(1)

    if "/itfind/" in list_url:
        if cms_menu_seq in ITFIND_API_MAP:
            api_cat, api_list_url = ITFIND_API_MAP[cms_menu_seq]
        else:
            r_info = post_api(ITFIND_INFO_API_URL, {"cms_menu_seq": cms_menu_seq}, referer=list_url)
            r_info.raise_for_status()
            itfind_info = (r_info.json().get("itfindInfo") or {})
            api_cat = itfind_info.get("api_cat")
            api_list_url = itfind_info.get("api_list_url")
            if not api_cat or not api_list_url:
                return []

        payload = {
            "pageIndex": 0,
            "pageSize": 10,
            "searchText": "",
            "searchTarget": "all",
            "searClassCode": api_cat,
            "url": api_list_url,
        }
        res = post_api(ITFIND_LIST_API_URL, payload, referer=list_url)
        res.raise_for_status()
        xmldata = res.json().get("xmldata") or ""
        if not xmldata.strip():
            return []

        root = ET.fromstring(xmldata)
        rows = []
        for row_el in root.findall(".//row"):
            seq = (row_el.findtext("identifier") or "").strip()
            title = clean_html_text(row_el.findtext("title") or "") or "제목 없음"
            date_str = (row_el.findtext("issued") or row_el.findtext("created") or "").strip()
            if not seq:
                continue
            link = urljoin(list_url, f"./view.do?seq={seq}&cpage=1&rows=10&searchTarget=all")
            year, month, day = split_date(date_str)
            rows.append([title, category, link, year, month, day])
        return rows

    # 게시판(/bbs/) 목록 API 호출
    payload = {
        "cms_menu_seq": cms_menu_seq,
        "cpage": 1,
        "rows": 10,
        "keyword": "",
        "condition": "",
        "sort": "latest",
    }
    res = post_api(BBS_LIST_API_URL, payload, referer=list_url)
    res.raise_for_status()
    bjson = res.json()
    if bjson.get("result") != "SUCCESS":
        return []

    items = (bjson.get("notice_list") or []) + (bjson.get("list") or [])
    rows = []
    for item in items:
        article_seq = str(item.get("article_seq") or "").strip()
        if not article_seq:
            continue
        title = clean_html_text(item.get("title") or "") or "제목 없음"
        link = urljoin(list_url, f"./view.do?article_seq={article_seq}&sort=latest&cpage=1&rows=10")
        year, month, day = split_date(item.get("reg_dt") or "")
        rows.append([title, category, link, year, month, day])
    return rows


def is_vue_template_item(item):
    """렌더링되지 않은 Vue.js 템플릿 <li> 태그(v-for, v-if, {{...}})인지 판별"""
    if item.has_attr("v-for") or item.has_attr("v-if"):
        return True
    text = item.get_text(" ", strip=True)
    if "{{item." in text or "decodeHtmlEntities(" in text:
        return True
    return False


def find_items(soup, list_url):
    primary = BBS_ITEM_SELECTOR if "/bbs/" in list_url else ITFIND_ITEM_SELECTOR
    raw_items = soup.select(primary) or soup.select(LOOSE_ITEM_SELECTOR)
    return [item for item in raw_items if not is_vue_template_item(item)]


def describe_page(response, soup):
    """목록을 못 찾았을 때 무엇을 받았는지 로그에 남김 (차단 페이지인지, 구조가 바뀐 건지 구분용)"""
    title = soup.title.get_text(strip=True) if soup.title else "(title 없음)"
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:150]
    return f"HTTP {response.status_code}, HTML {len(response.content):,}바이트, title='{title}', 본문 앞부분='{text}'"


def load_page(list_url, render):
    response = fetch_page(list_url, session=session, timeout=TIMEOUT_SEC, render=render,
                          headers=BROWSER_HEADERS, direct_timeout=DIRECT_TIMEOUT_SEC)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    return response, soup


def parse_item(item, list_url, category):
    title_link_tag = item.select_one("div.tit_area > a") or item.select_one(".tit_area a, a[href*='view.do']")
    if not title_link_tag:
        return None
    href = (title_link_tag.get("href") or "").strip()
    if not href or href.startswith(("javascript:", "#")) or "{{" in href:
        return None
    title = title_link_tag.get_text(strip=True) or "제목 없음"
    if "{{" in title:
        return None
    link = urljoin(list_url, href)

    year = month = day = ""
    date_element = item.select_one(".info_list_area li:nth-child(2) .txt")
    date_text = date_element.get_text(strip=True).replace("발행일:", "").strip() if date_element else ""
    year, month, day = split_date(date_text)
    if not year:
        year, month, day = split_date(item.get_text(" ", strip=True))

    return [title, category, link, year, month, day]


data = []
failed_pages = 0
start = time.time()

for index, (list_url, fallback_category) in enumerate(PAGES, start=1):
    if time.time() - start > TIME_BUDGET_SEC:
        print(f"[{index}/{len(PAGES)}] 시간 제한({TIME_BUDGET_SEC}초)에 가까워 남은 페이지는 건너뜁니다.")
        failed_pages += len(PAGES) - index + 1
        break

    print(f"[{index}/{len(PAGES)}] 페이지 로드 중... : {list_url}")
    try:
        # 1차: Vue 백엔드 데이터 API 직접 호출 (페이지당 1크레딧, 초고속)
        rows = []
        try:
            rows = fetch_via_backend_api(list_url, fallback_category)
        except Exception as api_err:
            print(f"   [!] 백엔드 API 요청 실패 ({type(api_err).__name__}: {api_err}) → HTML 렌더링 폴백 시도")

        # 2차 폴백: 백엔드 API에서 항목을 못 가져왔을 때만 ScraperAPI JS 렌더링(render=True) 시도
        if not rows and HAS_SCRAPER_KEY:
            print("   [!] JavaScript 렌더링(render=True)으로 HTML 파싱 재시도")
            response, soup = load_page(list_url, render=True)
            items = find_items(soup, list_url)
            category_element = soup.select_one(MAIN_TITLE_SELECTOR)
            cat_text = category_element.get_text(strip=True) if category_element else ""
            category = cat_text if (cat_text and "{{" not in cat_text) else fallback_category
            rows = [row for row in (parse_item(item, list_url, category) for item in items) if row]
            if not rows:
                failed_pages += 1
                print(f"   [X] 크롤링 중 오류: 목록을 찾지 못함 ({describe_page(response, soup)})")
                continue

        if not rows:
            failed_pages += 1
            print(f"   [X] 크롤링 중 오류: {fallback_category} 목록이 비어 있음")
            continue

        data.extend(rows)
        print(f"   [O] 분류: {rows[0][1]} | 항목 {len(rows)}개")

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
