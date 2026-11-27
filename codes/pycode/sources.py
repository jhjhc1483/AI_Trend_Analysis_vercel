"""
수집 출처 목록 (config/sources.json) 읽기.

크롤러 실행(run_crawlers.py), AI 자동 선정(auto_favorites.py), 대시보드용 데이터(build_dashboard_data.py),
구조 변경 감지(pipeline_report.py)와 대시보드(script.js)가 모두 같은 파일을 씁니다.
출처를 추가하거나 이름을 바꿀 때는 config/sources.json 만 고치면 됩니다.
"""
import json
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCES_PATH = PROJECT_ROOT / "config" / "sources.json"

ARTICLE = "article"
PUBLICATION = "publication"


@lru_cache(maxsize=1)
def load_sources():
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return tuple(json.load(f)["sources"])


def report_name(source):
    """크롤링 리포트·상태 기록에 쓰는 이름 (예: '국방부', '한국지능정보사회진흥원(NIA)')"""
    if source["type"] == PUBLICATION:
        return f"{source['full_name']}({source['name']})"
    return source["full_name"]


def crawler_scripts():
    """[(크롤러 파일명, 리포트 이름)] — run_crawlers.py 실행 순서"""
    return [(s["crawler"], report_name(s)) for s in load_sources()]


def data_files():
    """codes/ 아래 출처별 수집 데이터 파일명 목록"""
    return [s["file"] for s in load_sources()]


def daily_news_scripts():
    """매일 새 기사가 올라오는 뉴스 출처의 크롤러 파일명 (며칠 연속 0건이면 경고)"""
    return {s["crawler"] for s in load_sources() if s.get("daily_news")}


def by_file():
    """수집 데이터 파일명 → 출처 정보"""
    return {s["file"]: s for s in load_sources()}
