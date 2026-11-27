"""crawler_common.save_results: 기존 데이터와 합치기·중복 제거, run_crawlers 가 읽는 출력 형식"""
import json
import re

from crawler_common import save_results


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_merges_and_deduplicates_by_link(tmp_path, capsys):
    path = tmp_path / "site.json"
    path.write_text(json.dumps([{"링크": "a", "기사명": "old A"}, {"링크": "b", "기사명": "B"}], ensure_ascii=False), encoding="utf-8")

    new = save_results([{"링크": "a", "기사명": "new A"}, {"링크": "c", "기사명": "C"}, {"링크": "", "기사명": "no link"}],
                       str(path), "테스트")

    assert new == 1
    assert [item["링크"] for item in read(path)] == ["a", "b", "c"]
    assert read(path)[0]["기사명"] == "old A", "같은 링크는 먼저 있던 항목을 남김"


def test_update_if_replaces_in_place(tmp_path):
    path = tmp_path / "site.json"
    path.write_text(json.dumps([{"링크": "a", "v": 1}, {"링크": "b", "v": 1}]), encoding="utf-8")
    save_results([{"링크": "a", "v": 2}], str(path), "테스트", update_if=lambda old, new: new["v"] > old["v"])
    assert read(path) == [{"링크": "a", "v": 2}, {"링크": "b", "v": 1}]


def test_broken_existing_file_does_not_crash(tmp_path):
    path = tmp_path / "site.json"
    path.write_text("{not json", encoding="utf-8")
    assert save_results([{"링크": "a"}], str(path), "테스트") == 1


def test_output_line_matches_run_crawlers_parser(tmp_path, capsys):
    """run_crawlers.run_single_crawler 는 이 출력에서 '신규/가져온/최종 N건'을 정규식으로 읽음 (형식이 바뀌면 리포트가 0건으로 나옴)"""
    path = tmp_path / "site.json"
    path.write_text(json.dumps([{"링크": "x"}]), encoding="utf-8")
    save_results([{"링크": "x"}, {"링크": "y"}, {"링크": "z"}], str(path), "테스트")
    out = capsys.readouterr().out

    assert int(re.search(r"신규\s*(\d+)\s*건", out).group(1)) == 2
    assert int(re.search(r"가져온\s*(\d+)\s*건", out).group(1)) == 3
    assert int(re.search(r"최종\s*(\d+)\s*건", out).group(1)) == 3
