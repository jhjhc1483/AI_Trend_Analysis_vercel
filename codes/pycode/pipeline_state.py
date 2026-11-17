"""
일일 파이프라인(크롤링 → AI 자동 선정 → 오디오 → 메일) 상태 기록 공용 모듈.

GitHub 예약 실행은 몇 시간씩 밀리고 하루에 여러 번 겹쳐 돌기도 하므로,
자동 실행(PIPELINE_AUTO=true)일 때는 AI 선정·오디오·메일이 하루에 한 번씩만 실행되도록
아래 상태 파일을 보고 이미 한 일은 건너뜁니다. (대시보드 버튼 등 수동 실행은 항상 실행)

상태 파일은 쓰는 워크플로우별로 나눠서 동시에 커밋해도 충돌하지 않게 합니다.
  codes/state/crawl_status.json  ← run_crawlers.py         오늘 소스별 수집 결과 (2회차 재시도용)
  codes/state/audio.json         ← gen_audio.py            오디오를 만든 data.txt의 해시
  codes/state/mail.json          ← gmail_send_visualizer.py 마지막 발송 날짜
AI 자동 선정은 별도 상태 파일 없이 data.txt 첫 줄의 날짜로 판단합니다.

경로는 다른 스크립트와 마찬가지로 저장소 루트에서 실행하는 것을 기준으로 합니다.
"""
import hashlib
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

STATE_DIR = os.path.join("codes", "state")
REPORT_PATH = os.path.join("codes", "data.txt")
# json_to_txt.py 가 만드는 data.txt 첫 줄 형식: "📢26.11.17 AI 일일 동향📢"
REPORT_HEADER_REGEX = re.compile(r"📢(\d{2}\.\d{2}\.\d{2}) AI 일일 동향📢")


def now_kst():
    return datetime.now(ZoneInfo("Asia/Seoul"))


def today_key():
    """data.txt / data.json 에서 쓰는 날짜 키 (예: 26.11.17)"""
    return now_kst().strftime("%y.%m.%d")


def is_auto_run():
    """앞 단계 완료로 자동 실행된 경우 True (워크플로우에서 PIPELINE_AUTO=true 로 전달)"""
    return os.environ.get("PIPELINE_AUTO", "").strip().lower() == "true"


def report_date(path=REPORT_PATH):
    """data.txt 첫 줄의 날짜 키를 반환합니다. 파일이 없거나 형식이 다르면 None."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        found = REPORT_HEADER_REGEX.search(f.read())
    return found.group(1) if found else None


def file_sha256(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_state(name):
    path = os.path.join(STATE_DIR, f"{name}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def set_output(name, value):
    """GitHub Actions 다음 단계에서 steps.<id>.outputs.<name> 으로 읽을 수 있게 값을 남깁니다."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def write_state(name, data):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
