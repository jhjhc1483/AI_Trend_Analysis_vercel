"""출처 목록(config/sources.json)이 실제 파일·다른 목록과 맞는지 확인"""
from collections import Counter

import sources
from conftest import PYCODE, ROOT


def test_sources_are_unique_and_complete():
    items = sources.load_sources()
    assert items, "출처 목록이 비어 있습니다"
    for key in ("id", "file", "crawler"):
        duplicates = [v for v, n in Counter(s[key] for s in items).items() if n > 1]
        assert not duplicates, f"{key} 가 중복됨: {duplicates}"
    for s in items:
        assert s["type"] in (sources.ARTICLE, sources.PUBLICATION), s
        assert s["name"].strip() and s["full_name"].strip(), s
        assert not (s.get("daily_news") and s["type"] != sources.ARTICLE), f"간행물은 daily_news 가 될 수 없음: {s['id']}"


def test_every_source_has_crawler_and_data_file():
    for s in sources.load_sources():
        assert (PYCODE / s["crawler"]).is_file(), f"크롤러 파일 없음: {s['crawler']}"
        assert (ROOT / "codes" / s["file"]).is_file(), f"수집 데이터 파일 없음: codes/{s['file']}"


def test_report_names():
    by_id = {s["id"]: s for s in sources.load_sources()}
    assert sources.report_name(by_id["MND"]) == "국방부"
    assert sources.report_name(by_id["NIA"]) == "한국지능정보사회진흥원(NIA)"


def test_pipeline_modules_use_registry():
    import pipeline_report
    import run_crawlers

    assert [script for script, _ in run_crawlers.CRAWLER_SCRIPTS] == [s["crawler"] for s in sources.load_sources()]
    assert pipeline_report.DAILY_NEWS_SCRIPTS == {"mnd.py", "etnews.py", "aitimes.py", "AInews.py", "kookbang.py"}
