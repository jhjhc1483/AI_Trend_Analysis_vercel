"""크롤링 실행기·구조 변경 감지·일일 동향 텍스트·AI 선정 후보 (네트워크·AI 호출 없음)"""
import json

import pytest

import pipeline_report
import pipeline_state
import run_crawlers


# ---------------- run_crawlers ----------------

def test_mask_secrets_hides_unknown_keys():
    text = "GET http://api.scraperapi.com?api_key=abcdef123456&url=x"
    assert "abcdef123456" not in run_crawlers.mask_secrets(text)
    assert "api_key=***" in run_crawlers.mask_secrets(text)


def test_retry_failed_selects_only_failed_sources(monkeypatch):
    first, second = run_crawlers.CRAWLER_SCRIPTS[0][0], run_crawlers.CRAWLER_SCRIPTS[1][0]
    status = {"date": pipeline_state.today_key(), "results": {first: {"status": "SUCCESS"}, second: {"status": "FAILED"}}}
    monkeypatch.setattr(run_crawlers, "read_state", lambda name: status)
    targets = [script for script, _ in run_crawlers.select_targets(retry_failed=True)]
    assert first not in targets and second in targets
    assert len(targets) == len(run_crawlers.CRAWLER_SCRIPTS) - 1


def test_retry_failed_without_todays_record_runs_everything(monkeypatch):
    monkeypatch.setattr(run_crawlers, "read_state", lambda name: {"date": "00.01.01", "results": {}})
    assert run_crawlers.select_targets(retry_failed=True) == run_crawlers.CRAWLER_SCRIPTS


# ---------------- pipeline_report.detect_suspicious ----------------

def history(*entries):
    return [{"date": f"26.11.{10 + i:02d}", "name": "국방부", **e} for i, e in enumerate(entries)]


def test_detects_empty_fetch_streak():
    warnings = pipeline_report.detect_suspicious({"history": {"KISA.py": history({"fetched": 5, "new": 1}, {"fetched": 0, "new": 0}, {"fetched": 0, "new": 0})}})
    assert [w["script"] for w in warnings] == ["KISA.py"]


def test_detects_no_new_articles_only_for_daily_news():
    stale = history(*[{"fetched": 20, "new": 0}] * pipeline_report.NO_NEW_DAYS)
    warnings = pipeline_report.detect_suspicious({"history": {"mnd.py": stale, "KISA.py": stale}})
    assert [w["script"] for w in warnings] == ["mnd.py"], "간행물은 새 글이 없는 날이 많으므로 경고하지 않음"


# ---------------- json_to_txt ----------------

@pytest.fixture
def json_to_txt(monkeypatch, tmp_path):
    import json_to_txt as module
    monkeypatch.setenv("REPORT_DATE", "2026-11-28")
    monkeypatch.delenv("AUTO_MODE", raising=False)
    monkeypatch.setattr(module, "OUTPUT_FILE", tmp_path / "data.txt")
    monkeypatch.setattr(module, "JSON_OUTPUT_FILE", tmp_path / "data.json")
    articles, pubs = tmp_path / "a.json", tmp_path / "p.json"
    monkeypatch.setattr(module, "FILES", [articles, pubs])
    articles.write_text(json.dumps([
        {"title": "민간 기사", "link": "https://x/1", "category": "민간"},
        {"title": "국방 기사", "link": "https://x/2", "category": "국방"},
    ], ensure_ascii=False), encoding="utf-8")
    pubs.write_text(json.dumps([{"title": "보고서", "link": "https://x/3", "category": "간행물"}], ensure_ascii=False), encoding="utf-8")
    return module, tmp_path


def test_report_text_format(json_to_txt):
    module, tmp = json_to_txt
    module.main()
    text = (tmp / "data.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "📢26.11.28 AI 일일 동향📢"
    assert pipeline_state.REPORT_HEADER_REGEX.search(text).group(1) == "26.11.28", "오디오·AI 선정 단계가 읽는 머리말 형식"
    assert text.index("[국방]") < text.index("[민간]") < text.index("📚 간행물"), "고정 분류 순서, 간행물은 마지막"
    assert "◾ 국방 기사\nhttps://x/2" in text


def test_report_history_keeps_ai_fields(json_to_txt):
    module, tmp = json_to_txt
    (tmp / "data.json").write_text(json.dumps({"26.11.28": {
        "ai_pick": [{"title": "국방 기사", "link": "https://x/2", "site": "MND", "score": 5, "reason": "중요", "keywords": ["AI"]}],
        "briefing": "- 요약",
    }}, ensure_ascii=False), encoding="utf-8")
    module.main()
    day = json.loads((tmp / "data.json").read_text(encoding="utf-8"))["26.11.28"]
    item = day["categorized"]["국방"][0]
    assert (item["score"], item["site"], item["reason"]) == (5, "MND", "중요"), "사람이 고친 목록에도 AI 점수·이유를 다시 채움"
    assert day["briefing"] == "- 요약" and "ai_pick" in day, "그날 기록의 다른 값은 유지"
    assert "edited_at" in day, "대시보드(수동) 저장은 수정 시각을 남김"


def test_report_refuses_to_overwrite_broken_history(json_to_txt):
    module, tmp = json_to_txt
    (tmp / "data.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(SystemExit):
        module.main()
    assert (tmp / "data.json").read_text(encoding="utf-8") == "{broken"


# ---------------- auto_favorites: 후보 고르기 (AI 호출 없음) ----------------

def test_candidates_prefer_mnd_and_skip_excluded(monkeypatch, tmp_path):
    pytest.importorskip("google.genai")
    import auto_favorites

    day = {"년": "2026", "월": "11", "일": "27"}
    (tmp_path / "mnd.json").write_text(json.dumps([{"기사명": "같은 제목!", "링크": "https://mnd/1", **day}], ensure_ascii=False), encoding="utf-8")
    (tmp_path / "kookbang.json").write_text(json.dumps([
        {"기사명": "같은 제목", "링크": "https://kookbang/1", **day},
        {"기사명": "제외할 기사", "링크": "https://kookbang/2", **day},
        {"기사명": "다른 날 기사", "링크": "https://kookbang/3", "년": "2026", "월": "11", "일": "26"},
    ], ensure_ascii=False), encoding="utf-8")
    (tmp_path / "nia.json").write_text(json.dumps([{"제목": "보고서", "link": "https://nia/1", **day}], ensure_ascii=False), encoding="utf-8")
    excluded = tmp_path / "excluded.json"
    excluded.write_text(json.dumps([{"link": "https://kookbang/2"}]), encoding="utf-8")

    monkeypatch.setattr(auto_favorites, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(auto_favorites, "EXCLUDED_ARTICLES_PATH", str(excluded))
    monkeypatch.setattr(auto_favorites, "YESTERDAY", "20261127")

    articles, pubs, _, skipped = auto_favorites.load_json_files()
    assert [(a["site"], a["link"]) for a in articles] == [("MND", "https://mnd/1")], "같은 제목은 국방부 것을 남김"
    assert [(p["site"], p["title"]) for p in pubs] == [("NIA", "보고서")]
    assert skipped == {"excluded": 1, "duplicate": 1}


# ---------------- 메일·공유 텍스트의 사이트 주소 ----------------

def test_links_use_short_addresses_defined_in_vercel_json(monkeypatch, json_to_txt):
    """메일·일일 동향 텍스트에 넣는 주소가 vercel.json 에 연결된 주소인지 (파일 이름 주소를 쓰면 이동 한 번을 더 거침)"""
    import gmail_send_visualizer as gsv
    from conftest import ROOT

    rewrites = {r["source"] for r in json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["rewrites"]}
    monkeypatch.setenv("SUBSCRIBER_ENCRYPTION_KEY", "test-key-for-ci-only-0123456789abcdef")
    links = gsv.subscription_links("user@example.com")
    paths = [gsv.VISUALIZER_URL, links["unsubscribe_page"], links["renew_page"]]

    module, tmp = json_to_txt
    module.main()
    listen = [line.split()[-1] for line in (tmp / "data.txt").read_text(encoding="utf-8").splitlines() if "오디오 듣기" in line]
    assert listen, "일일 동향 텍스트에 오디오 링크가 없습니다"

    for url in paths + listen:
        path = url.replace(gsv.SITE_URL, "").split("?")[0]
        assert path in rewrites, f"{url} 의 경로 {path} 가 vercel.json 에 없습니다"
