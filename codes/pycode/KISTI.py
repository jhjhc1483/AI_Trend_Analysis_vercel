import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import itertools

# 환경 변수에서 API 키 불러오기 (로테이션 지원) - KISTI가 bot을 차단하므로 ScraperAPI 사용
API_KEYS = [
    os.environ.get('SCRAPER_API_KEY'),
    os.environ.get('SCRAPER_API_KEY_2')
]
# None이 아닌 키만 필터링
SCRAPER_KEYS = [k for k in API_KEYS if k]

# ScraperAPI가 없는 경우에는 직접 접속을 시도
USE_SCRAPER = bool(SCRAPER_KEYS)

if USE_SCRAPER:
    key_cycle = itertools.cycle(SCRAPER_KEYS)
    SCRAPER_URL = 'http://api.scraperapi.com'
    print(f"ScraperAPI 사용 (키 {len(SCRAPER_KEYS)}개)")
else:
    print("경고: ScraperAPI 키가 없어 직접 접속을 시도합니다. KISTI 서버가 차단할 수 있습니다.")

# 1. 세션 및 재시도(Retry) 설정
session = requests.Session()
retries = Retry(
    total=5,            
    backoff_factor=2,   
    status_forcelist=[403, 500, 502, 503, 504],
    raise_on_status=False
)
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

TIMEOUT_SEC = 30

# KISTI 보고서 카테고리 URL (2025년 사이트 개편 후)
# 기존 stdata, issuebrief 등은 없어지거나 변경됨
url = [
    "https://www.kisti.re.kr/post/policy-report",       # S&T Policy Report (구 stdata)
    "https://www.kisti.re.kr/post/data-insight",         # 데이터 인사이트
    "https://www.kisti.re.kr/post/asti-insight",         # ASTI 마켓 인사이트
    "https://www.kisti.re.kr/post/analysis-report",      # R&I Report (구 analysis-report)
]

data = []

for i in range(len(url)):
    print(f"--- {url[i]} 수집 중 ---")
    try:
        if USE_SCRAPER:
            # ScraperAPI를 통한 접속 (KISTI가 직접 접속 차단)
            payload = {
                'api_key': next(key_cycle),
                'url': url[i],
                'country_code': 'kr',
                'render': 'true'  # JavaScript 렌더링 활성화 (KISTI는 JS 기반 렌더링)
            }
            response = session.get(SCRAPER_URL, params=payload, timeout=60)
        else:
            # 직접 접속 시도
            response = session.get(url[i], headers=headers, timeout=TIMEOUT_SEC)
        
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 카테고리명 추출 시도 (여러 가지 선택자 시도)
        category = "알수없음"
        
        # 방법 1: 기존 선택자
        category_tag = soup.select_one(".tit_nav.tit_nav_bg04>h1")
        if category_tag:
            category = category_tag.text.strip()
        
        # 방법 2: 페이지 타이틀에서 추출
        if category == "알수없음":
            title_tag = soup.select_one("title")
            if title_tag:
                title_text = title_tag.text.strip()
                # "S&T DATA | 보고서 | ..." 같은 형태에서 첫 번째 부분 추출
                parts = [p.strip() for p in title_text.split('|')]
                if parts:
                    category = parts[0].strip()

        # 방법 3: URL 기반 카테고리 매핑 (fallback)
        if category == "알수없음" or not category:
            url_category_map = {
                "policy-report": "S&T Policy Report",
                "data-insight": "데이터 인사이트",
                "asti-insight": "ASTI 마켓 인사이트",
                "analysis-report": "R&I Report",
            }
            for key, val in url_category_map.items():
                if key in url[i]:
                    category = val
                    break

        # 게시글 목록 파싱 (여러 HTML 구조 시도)
        items = []
        
        # 방법 1: 기존 구조 (.text_wrap)
        items = soup.select(".text_wrap")
        
        # 방법 2: 새 구조 (리스트 형태)
        if not items:
            items = soup.select(".board_list li, .bbs_list li, .list_wrap li")
        
        # 방법 3: 테이블 형태
        if not items:
            items = soup.select("table.board_list tbody tr, .tbl_list tbody tr")
        
        # 방법 4: 카드/그리드 형태
        if not items:
            items = soup.select(".card_list .card_item, .post_list .post_item")

        # 방법 5: 일반적인 게시글 링크 패턴
        if not items:
            items = soup.select("a[href*='/post/']")
            # a 태그의 부모 요소를 items로 사용
            if items:
                items = [a.parent for a in items if a.parent and a.parent.name != 'nav']

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
        print(f"URL 접속 중 오류 발생 ({url[i]}): {e}")
        continue

# 2. 데이터프레임 생성 및 정제
df10 = pd.DataFrame(data, columns=['제목', '분류', '링크', '년', '월', '일'])
full_path = 'codes/KISTI.json'

os.makedirs(os.path.dirname(full_path), exist_ok=True)

new_data = df10.to_dict('records')

# 3. 기존 데이터 로드 및 중복 제거 (기존 로직 유지)
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

print(f"[KISTI] 완료: 신규 {len(new_data)}건 수집 | 기존 {len(existing_data)}건 병합 | 최종 {len(final_data)}건 저장 ({full_path})")