import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from zoneinfo import ZoneInfo  # Python 3.9 이상

# 현재 파일: codes/pycode/report.py
# 프로젝트 루트로 이동
PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILES = [
    PROJECT_ROOT / "codes/favorites/favorite_articles.json",
    PROJECT_ROOT / "codes/favorites/favorite_publications.json",
]

OUTPUT_FILE = PROJECT_ROOT / "codes/data.txt"

FIXED_CATEGORIES = ["국방", "육군", "민간", "기관", "기타"]
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
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    lines = [f"[{today} AI 일일 동향 보고]\n"]

    # 1. 고정 카테고리
    for category in FIXED_CATEGORIES:
        if category in categorized:
            lines.append(f"[{category}]")
            for item in categorized[category]:
                lines.append(f"▲ {item['title']}")
                lines.append(item["link"])
                lines.append("")

    # 2. 그외 카테고리 (실제 카테고리명)
    extra_categories = sorted(
        c for c in categorized
        if c not in FIXED_CATEGORIES and c != LAST_CATEGORY
    )

    for category in extra_categories:
        lines.append(f"[{category}]")
        for item in categorized[category]:
            lines.append(f"▲ {item['title']}")
            lines.append(item["link"])
            lines.append("")

    # 3. 간행물
    if LAST_CATEGORY in categorized:
        lines.append(f"[{LAST_CATEGORY}]")
        for item in categorized[LAST_CATEGORY]:
            lines.append(f"▲ {item['title']}")
            lines.append(item["link"])
            lines.append("")

    lines.append("")
    lines.append("by. AI Development Department")
    return "\n".join(lines).strip()


def main():
    articles = load_articles(FILES)
    categorized = categorize_articles(articles)
    report_text = generate_report_text(categorized)

    print(report_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)


if __name__ == "__main__":
    main()
