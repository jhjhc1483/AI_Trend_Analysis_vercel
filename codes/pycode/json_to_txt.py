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
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%y.%m.%d")
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
        except json.JSONDecodeError:
            print("기존 JSON 파일 파싱 실패. 새로 생성합니다.")

    today_key = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%y.%m.%d")
    history_data[today_key] = {
        "categorized": categorized
    }

    with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
