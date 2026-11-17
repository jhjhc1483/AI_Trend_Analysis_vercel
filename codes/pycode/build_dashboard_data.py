"""
대시보드(index.html) 첫 화면용 '최근 N일' 데이터 파일을 만듭니다. → codes/dashboard/recent.json

전체 데이터(16개 파일, 약 12MB)를 매번 내려받지 않도록, 최근 RECENT_DAYS일 기사/간행물만
한 파일에 압축된 JSON으로 담습니다. 대시보드에서 검색하거나 '전체 기간 불러오기'를 누르면
그때 전체 파일을 받습니다. (script.js 의 loadRecentOrAllData / loadAllData)

크롤링(main.yml)이 끝날 때마다 실행됩니다.
"""
import json
import os
from datetime import timedelta

from pipeline_state import now_kst

RECENT_DAYS = 30
OUTPUT_PATH = os.path.join("codes", "dashboard", "recent.json")
# script.js 의 FILES_TO_LOAD 와 같은 파일 목록
SOURCE_FILES = [
    "aikorea.json", "aitimes.json", "etnews.json", "AInews.json", "mnd.json", "kookbang.json",
    "dapa.json", "msit.json", "iitp.json", "nia.json", "STEPI.json", "NIPA.json",
    "KISDI.json", "KISTI.json", "KISA.json", "tta.json",
]


def item_date(item):
    return f"{item.get('년', '')}{str(item.get('월', '')).zfill(2)}{str(item.get('일', '')).zfill(2)}"


def main():
    now = now_kst()
    cutoff = (now - timedelta(days=RECENT_DAYS)).strftime("%Y%m%d")
    files = {}
    total = 0
    for name in SOURCE_FILES:
        path = os.path.join("codes", name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"⚠️ {name} 읽기 실패 ({e}) - 빈 목록으로 둡니다.")
            data = []
        files[name] = [item for item in data if item_date(item) >= cutoff]
        total += len(files[name])

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    payload = {"generated_at": now.isoformat(timespec="seconds"), "days": RECENT_DAYS, "files": files}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ 대시보드용 최근 {RECENT_DAYS}일 데이터: {total}건, {os.path.getsize(OUTPUT_PATH) / 1e6:.2f}MB → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
