"""
GitHub Actions 워크플로우 설정 검사.

- 매일 시작 순서: 1순위 Claude 예약 작업(04:03 KST 시작, 05:13 KST 점검·복구),
  2순위 GitHub 예약(main.yml schedule). GitHub 예약이 Claude 작업보다 먼저 돌면
  Claude 작업이 '이미 실행됨'으로 건너뛰어 순서가 뒤집히므로 그 뒤 시각인지 확인합니다.
- 단계 연결(workflow_run)은 앞 워크플로우의 이름(name:)으로 이어지므로, 이름을 바꾸면 끊깁니다.
"""
import re

from conftest import ROOT

WORKFLOWS = ROOT / ".github" / "workflows"
CLAUDE_LAST_KST_MINUTE = 5 * 60 + 13   # 05:13 KST 점검·복구


def read(name):
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def schedule_crons(text):
    return re.findall(r"^\s*-\s*cron:\s*'([^']+)'", text, flags=re.M)


def kst_minutes(cron):
    minute, hour, *rest = cron.split()
    assert rest == ["*", "*", "*"], f"매일 실행 예약만 지원: {cron}"
    return ((int(hour) + 9) % 24) * 60 + int(minute)


def test_github_backup_schedule_runs_after_claude_tasks():
    crons = schedule_crons(read("main.yml"))
    assert crons, "main.yml 에 예비 예약(schedule)이 없습니다"
    for cron in crons:
        minutes = kst_minutes(cron)
        assert minutes > CLAUDE_LAST_KST_MINUTE, (
            f"GitHub 예약 '{cron}' = KST {minutes // 60:02d}:{minutes % 60:02d} — "
            "Claude 예약 작업(04:03 시작, 05:13 점검)보다 먼저 돌면 순서가 뒤집힙니다")


def test_round_two_cron_string_matches_schedule():
    text = read("main.yml")
    referenced = re.search(r'if \[ "\$CRON" = "([^"]+)" \]; then ROUND=2', text)
    assert referenced, "예약 회차를 판단하는 부분을 찾지 못했습니다"
    assert referenced.group(1) in schedule_crons(text), "ROUND=2 로 판단하는 cron 문자열이 schedule 목록과 다릅니다"


def test_pipeline_chain_names_match():
    names = {path.name: re.search(r"^name:\s*(.+)$", path.read_text(encoding="utf-8"), flags=re.M).group(1).strip()
             for path in WORKFLOWS.glob("*.yml")}
    chain = [("auto_favorites.yml", "main.yml"), ("audio_gen.yml", "auto_favorites.yml"), ("kakao_or_gmail_send.yml", "audio_gen.yml")]
    for follower, leader in chain:
        triggers = re.search(r"workflow_run:\s*\n\s*workflows:\s*\[([^\]]+)\]", read(follower))
        assert triggers, f"{follower} 에 workflow_run 연결이 없습니다"
        listed = [name.strip().strip('"\'') for name in triggers.group(1).split(",")]
        assert names[leader] in listed, f"{follower} 가 기다리는 이름 {listed} ≠ {leader} 의 name '{names[leader]}'"
