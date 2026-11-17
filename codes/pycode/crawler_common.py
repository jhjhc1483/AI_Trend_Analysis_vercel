"""
크롤러 공통 함수.

- save_results: 새로 수집한 항목을 기존 JSON과 합쳐 중복을 제거하고 저장합니다. (16개 크롤러 공통)
- fetch_page:   ScraperAPI 키가 있으면 한국 IP 우회로, 없으면 브라우저 헤더로 직접 요청합니다.
                (봇 접속을 막는 국방부·방위사업청·국방일보·KISTI에서 사용)

크롤러는 저장소 루트에서 'python codes/pycode/<이름>.py' 로 실행합니다.
run_crawlers.py 는 save_results 가 출력하는 '신규 N건', '최종 N건' 문구를 읽어 리포트를 만듭니다.
"""
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

SCRAPER_URL = "http://api.scraperapi.com"

# ScraperAPI 키가 없을 때 직접 요청에 쓰는 브라우저 헤더
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}


def fetch_page(url, *, session=None, timeout=30, render=False, headers=None, direct_timeout=None):
    """
    페이지를 가져옵니다.
    - SCRAPER_API_KEY 가 있으면 ScraperAPI(한국 IP)를 거쳐 요청 (render=True면 JavaScript 렌더링)
    - 없으면 직접 요청 (사이트가 차단할 수 있음)
    session 을 넘기면 그 세션의 재시도 설정을 그대로 사용합니다.
    """
    http = session or requests
    api_key = os.environ.get("SCRAPER_API_KEY", "").strip()
    if api_key:
        params = {"api_key": api_key, "url": url, "country_code": "kr"}
        if render:
            params["render"] = "true"
        return http.get(SCRAPER_URL, params=params, timeout=timeout)
    return http.get(url, headers=headers or BROWSER_HEADERS, timeout=direct_timeout or timeout)


def _load_existing(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            print("기존 JSON 파일이 비어 있습니다. 새 데이터만 저장합니다.")
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"기존 JSON 파일 로드 중 오류 발생 ({e}). 새 데이터만 저장합니다.")
        return []


def save_results(rows, path, label, key="링크", update_if=None):
    """
    rows(이번에 수집한 항목 리스트)를 path 의 기존 데이터와 합쳐 저장합니다.
    - key(기본: '링크') 값이 같은 항목은 먼저 있던 것(기존 데이터)을 남깁니다.
      단, update_if(기존 항목, 새 항목)가 True를 돌려주면 그 자리에서 새 항목으로 바꿉니다.
    - key 값이 비어 있는 항목은 저장하지 않습니다.
    반환: 실제로 새로 추가된 건수
    """
    existing = _load_existing(path)

    position = {}  # key 값 → final 안의 위치
    final = []
    for item in existing:
        value = item.get(key)
        if value and value not in position:
            position[value] = len(final)
            final.append(item)
    kept_existing = len(final)

    updated = 0
    for item in rows:
        value = item.get(key)
        if not value:
            continue
        if value in position:
            if update_if and update_if(final[position[value]], item):
                final[position[value]] = item
                updated += 1
            continue
        position[value] = len(final)
        final.append(item)
    new_count = len(final) - kept_existing

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=4, ensure_ascii=False)

    # run_crawlers.py 가 '신규 N건' / '최종 N건' 을 읽습니다. (형식 변경 시 함께 수정)
    updated_note = f" (내용이 바뀐 {updated}건 갱신)" if update_if else ""
    print(f"[{label}] 완료: 신규 {new_count}건 수집 (이번에 가져온 {len(rows)}건) | "
          f"기존 {len(existing)}건 병합{updated_note} | 최종 {len(final)}건 저장 ({path})")
    return new_count
