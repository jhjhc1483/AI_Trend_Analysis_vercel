import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from zoneinfo import ZoneInfo  # Python 3.9 이상
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILES = [
    PROJECT_ROOT / "codes/favorites/favorite_articles.json",
    PROJECT_ROOT / "codes/favorites/favorite_publications.json",
]

OUTPUT_FILE = PROJECT_ROOT / "codes/data.txt"
JSON_OUTPUT_FILE = PROJECT_ROOT / "codes/data.json"

FIXED_CATEGORIES = ["국방", "육군", "민간", "기관", "해외", "기타"]
LAST_CATEGORY = "간행물"

# 대시보드에서 즐겨찾기를 고쳐 올리면 이 값들이 빠지므로, 그날 AI 원안(ai_pick)에서 같은 링크의 값을 채움
AI_FIELDS = ("site", "score", "reason", "keywords")


def report_date():
    """REPORT_DATE(YYYY-MM-DD) 환경변수가 있으면 그 날짜, 없으면 오늘(KST)."""
    env = os.environ.get("REPORT_DATE", "").strip()
    if env:
        return datetime.strptime(env, "%Y-%m-%d")
    return datetime.now(ZoneInfo("Asia/Seoul"))


def load_articles(files):
    articles = []
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                articles.extend(json.load(f))
        except FileNotFoundError:
            print(f"파일을 찾을 수 없습니다: {file_path}")
    return articles


def categorize_articles(articles):
    categorized = defaultdict(list)
    for item in articles:
        category = item.get("category", "기타")
        categorized[category].append(item)
    return categorized

def generate_report_text(categorized):
    # "%Y-%m-%d" 형식을 "%y.%m.%d" 형식으로 수정
    today = report_date().strftime("%y.%m.%d")
    # today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    lines = [f"📢{today} AI 일일 동향📢\n"]
    lines.append("📰 오늘의 기사")
#⌨️📰📚📖📒📔📃🗓️🔖💡📢🔊 ✨🎧🔎🌍⭐🌈🔥⚠️◾▪️◼️🔴

    # 1. 고정 카테고리
    for category in FIXED_CATEGORIES:
        if category in categorized:
            lines.append(f"[{category}]")
            for item in categorized[category]:
                lines.append(f"◾ {item['title']}")
                lines.append(f"{item['link']}")
                lines.append("")

    # 2. 그외 카테고리
    extra_categories = sorted(
        c for c in categorized
        if c not in FIXED_CATEGORIES and c != LAST_CATEGORY
    )

    for category in extra_categories:
        lines.append(f"[{category}]")
        for item in categorized[category]:
            lines.append(f"◾ {item['title']}")
            lines.append(f"{item['link']}")
            lines.append("")

    # 3. 간행물
    if LAST_CATEGORY in categorized:
        lines.append(f"📚 {LAST_CATEGORY}")
        for item in categorized[LAST_CATEGORY]:
            lines.append(f"◾ {item['title']}")
            lines.append(item["link"])
            lines.append("")
    lines.append("\n🎧오디오 듣기 https://ai-trend-analysis.vercel.app/public/bf.html")
    lines.append("(링크를 꾹 누른 후 '열기'를 누르면 백그라운드 재생이 가능합니다.(안드로이드 기준))")
    # lines.append("\n\n🤖AI Development Department🧑‍🤝‍🧑")
    
    if os.environ.get('AUTO_MODE') == 'true':
        lines.append("\n\n✅위 내용은 GEMINI에 의해 작성됨.")
        
    return "\n".join(lines).strip()


def main():
    articles = load_articles(FILES)
    categorized = categorize_articles(articles)
    report_text = generate_report_text(categorized)

    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(report_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    # JSON 저장 (누적)
    history_data = {}
    if JSON_OUTPUT_FILE.exists():
        try:
            with open(JSON_OUTPUT_FILE, "r", encoding="utf-8") as f:
                history_data = json.load(f)
            
            # 구버전 형식(단일 날짜)인 경우 마이그레이션
            if "date" in history_data and "categorized" in history_data:
                old_date = history_data["date"]
                old_cat = history_data["categorized"]
                history_data = { old_date: { "categorized": old_cat } }
        except json.JSONDecodeError as e:
            # 새로 만들면 지난 일일 동향·AI 원안 기록이 모두 사라지므로 덮어쓰지 않고 멈춤
            raise SystemExit(f"❌ data.json 파싱 실패 - 지난 기록을 지키기 위해 저장하지 않습니다: {e}")

    today_key = report_date().strftime("%y.%m.%d")
    # 그날 기록의 다른 값(ai_pick, ai_meta, briefing)은 그대로 두고 최종본(categorized)만 바꿈
    entry = history_data.get(today_key) or {}
    ai_by_link = {item["link"]: item for item in entry.get("ai_pick", []) if item.get("link")}
    for items in categorized.values():
        for item in items:
            ai_item = ai_by_link.get(item.get("link"))
            if not ai_item:
                continue
            for field in AI_FIELDS:
                if field not in item and field in ai_item:
                    item[field] = ai_item[field]
    entry["categorized"] = categorized
    if os.environ.get('AUTO_MODE') != 'true':
        # 대시보드에서 사람이 고쳐 저장한 시각 (없으면 AI 원안을 그대로 쓴 날)
        entry["edited_at"] = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    history_data[today_key] = entry

    with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
