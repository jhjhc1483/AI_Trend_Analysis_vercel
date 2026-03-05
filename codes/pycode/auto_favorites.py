import os
import json
import glob
from datetime import datetime, timedelta, timezone
import google.generativeai as genai


KST = timezone(timedelta(hours=9))
YESTERDAY = (datetime.now(KST) - timedelta(days=1)).strftime('%Y%m%d')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # codes/pycode
BASE_DIR = os.path.dirname(PROJECT_ROOT) # codes
FILES_PATTERN = os.path.join(BASE_DIR, "*.json")
FAV_ARTICLES_PATH = os.path.join(BASE_DIR, "favorites", "favorite_articles.json")
FAV_PUBS_PATH = os.path.join(BASE_DIR, "favorites", "favorite_publications.json")
FEWSHOT_EXAMPLES_PATH = os.path.join(BASE_DIR, "favorites", "fewshot_examples.json")
EXCLUDED_ARTICLES_PATH = os.path.join(BASE_DIR, "favorites", "excluded_articles.json")


PUB_SITES = ['IITP', 'NIA', 'STEPI', 'NIPA', 'KISDI', 'KISTI', 'KISA', 'TTA']

def load_json_files():
    all_articles = []
    all_pubs = []

    # 일일동향 제외 블랙리스트 로드
    excluded_links = set()
    excluded_data_full = []  # 이유 포함 전체 데이터
    if os.path.exists(EXCLUDED_ARTICLES_PATH):
        try:
            with open(EXCLUDED_ARTICLES_PATH, 'r', encoding='utf-8') as f:
                excluded_data_full = json.load(f)
            excluded_links = {item.get('link', '') for item in excluded_data_full if item.get('link')}
            print(f"Loaded {len(excluded_links)} excluded articles.")
        except Exception as e:
            print(f"Error loading excluded_articles.json: {e}")

    for filepath in glob.glob(FILES_PATTERN):
        filename = os.path.basename(filepath)
        if filename == "update_time.json": continue
        
        site_name = os.path.splitext(filename)[0].upper()
        if site_name == "KOOKBANG": site_name = "kookbang"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            is_pub = site_name in PUB_SITES
            
            for item in data:
                year = str(item.get('년', ''))
                month = str(item.get('월', '')).zfill(2)
                day = str(item.get('일', '')).zfill(2)
                date_str = f"{year}{month}{day}"
                
                # 어제 날짜만
                if date_str == YESTERDAY:
                    link = item.get('링크') or item.get('link') or '#'

                    # 제외 블랙리스트 필터링
                    if link in excluded_links:
                        print(f"[EXCLUDED] {item.get('기사명') or item.get('제목', '')[:40]}")
                        continue

                    item_data = {
                        'title': item.get('기사명') or item.get('제목') or '제목 없음',
                        'link': link,
                        'date': date_str,
                        'site': site_name
                    }
                    if is_pub:
                        all_pubs.append(item_data)
                    else:
                        all_articles.append(item_data)
                        
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            
    return all_articles, all_pubs, excluded_data_full

def select_and_classify(items, item_type='ARTICLE', excluded_reasons=None):
    if not items:
        return []

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # 프롬프트 구성
    item_text = "\n".join([f"{i}. [{item['site']}] {item['title']} ({item['link']})" for i, item in enumerate(items)])

    if item_type == 'ARTICLE':
        system_instruction = """
You are an expert in analyzing South Korean defense and AI trends.
From the given list of articles, you must select important articles related to 'Defense AI' and 'Latest AI Trends'.

[CRITICAL FILTERING RULE - MUST OBEY]
1. You MUST COMPLETELY IGNORE general military, defense, or army news that lacks a clear AI, or software component. 
(e.g., DO NOT select articles about conventional weapons, troop movements, military exercises, personnel appointments, or diplomatic defense talks unless AI is the main topic).

2. [DEDUPLICATION RULE] 
If multiple articles cover the same event or subject (even from different sites), select only the ONE most representative article.
EXCEPTION: This deduplication rule DOES NOT apply to 'Defense' (국방) and 'Army' (육군) categories. For these, you may select multiple related articles if they provide valuable context.

Selection Criteria:
1. Defense/Military AI (Highest Priority): Technologies like AI drones, AI defense centers, military cloud, etc.
2. Groundbreaking advancements in AI technology or key announcements from major companies (e.g., Naver, LG, Google, OpenAI).
3. Major AI policies of the government (e.g., Presidential Committee on AI, MSIT).

For each selected article, you must assign one of the following categories:
- 국방 (Defense): MUST contain BOTH [Defense context] AND [AI context]. (e.g., "Defense AI Center", "AI targeting"). Strictly exclude non-AI defense news.
- 육군 (Army): MUST contain BOTH [Army context] AND [AI context]. (e.g., "Army AI dronebot"). Strictly exclude non-AI army news.
- 민간 (Private Sector): General companies, tech trends, international trends (Limit to 5-7 most important articles).
- 기관 (Institution): Presidential Committee on AI, MSIT, other government agencies, public policies, research institutes (Limit to 5-7 most important articles).
- 해외 (Overseas): AI-related trends in foreign countries, companies, and technologies (Limit to 5-7 most important articles).
- 기타 (Other): Anything else.

The response format must be a valid JSON array. Return only pure JSON without markdown or code blocks.
Format:
[
  { "index": 0, "category": "국방" },
  ...
]
"""
# - 국방 (Defense): Only AI/IT-related articles within defense-related news.
# - 육군 (Army): Only AI/IT-related articles within Army-related news.
        
        # Few-shot 예제 동적 로드
        fewshot_text = ""
        try:
            if os.path.exists(FEWSHOT_EXAMPLES_PATH):
                with open(FEWSHOT_EXAMPLES_PATH, 'r', encoding='utf-8') as f:
                    examples = json.load(f)
                if examples:
                    fewshot_text = "\n\n[Classification Learning Examples (Few-Shot)]\nThe following are examples of articles and categories manually classified by the user. Prioritize learning these criteria and assign the same category when classifying articles with similar titles or sites:\n"
                    for ex in examples:
                        reason = ex.get('reason', '').strip()
                        reason_str = f" (Reason: {reason})" if reason else ""
                        fewshot_text += f"- [{ex.get('site', 'Unknown')}] {ex.get('title', 'No Title')} -> Category: {ex.get('category', '기타')}{reason_str}\n"
        except Exception as e:
            print(f"Error loading fewshot examples: {e}")

        system_instruction += fewshot_text

        # 제외 기사 이유 프롬프트 추가
        if excluded_reasons:
            reasons_with_text = [ex for ex in excluded_reasons if ex.get('reason', '').strip()]
            if reasons_with_text:
                system_instruction += "\n\n[Exclusion Rules (User-defined)]\nThe following articles have been permanently excluded from the daily briefing by the user. Learn the pattern of these titles and reasons, and NEVER select similar articles:\n"
                for ex in reasons_with_text:
                    system_instruction += f"- [{ex.get('site', 'Unknown')}] {ex.get('title', '')} (Reason: {ex.get('reason', '')})\n"

        user_prompt = f"Select important articles from the following list and classify their categories:\n\n{item_text}"
    else:
        # 간행물은 '간행물'로 통일
        system_instruction = """
You are an expert analyzing AI and IT technology publications.
From the given list of publications (reports), please select key publications that would be helpful for defense and AI technology research and development.
Selection Criteria:
1. Science and technology reports related to defense and security.
2. Reports on the latest core technology trends such as AI, LLM, semiconductors, etc.
3. Major science and technology policy research reports.

Categorize all selected items as '간행물'.

The response format must be a valid JSON array. Return only pure JSON without markdown or code blocks.
Format:
[
  { "index": 0, "category": "간행물" },
  ...
]
"""
        user_prompt = f"Please select important items from the following publication list:\n\n{item_text}"

    try:
        response = model.generate_content(system_instruction + "\n\n" + user_prompt, generation_config={"response_mime_type": "application/json"})
        text = response.text.replace("```json", "").replace("```", "").strip()
        selected_indices = json.loads(text)
        
        results = []
        for selection in selected_indices:
            idx = selection.get('index')
            # 간행물은 강제로 '간행물', 기사는 LLM 분류 따름
            if item_type == 'PUBLICATION':
                cat = '간행물'
            else:
                cat = selection.get('category', '기타')
                if cat not in ["국방", "육군", "민간", "기관", "해외", "기타"]:
                    cat = "기타"
            
            if idx is not None and 0 <= idx < len(items):
                original = items[idx]
            results.append({
                    'title': original['title'],
                    'link': original['link'],
                'category': cat
            })
        return results

    except Exception as e:
        print(f"Error during LLM processing ({item_type}): {e}")
        return [] # 오류 발생 시 빈 리스트 (또는 전체 반환? 안전하게 빈 리스트 권장)

def main():
    print(f"Start Job. Target Date (Yesterday): {YESTERDAY}")
    
    articles, pubs, excluded_data = load_json_files()
    print(f"Found {len(articles)} articles and {len(pubs)} publications for {YESTERDAY}")
    
    # 1. 기사 처리
    fav_articles = select_and_classify(articles, 'ARTICLE', excluded_reasons=excluded_data)
    print(f"Selected {len(fav_articles)} articles")
    
    # 2. 간행물 처리
    fav_pubs = select_and_classify(pubs, 'PUBLICATION')
    print(f"Selected {len(fav_pubs)} publications")
    
    # 3. 저장 (덮어쓰기 - 매일 새로운 리스트 생성)
    os.makedirs(os.path.dirname(FAV_ARTICLES_PATH), exist_ok=True)
    
    with open(FAV_ARTICLES_PATH, 'w', encoding='utf-8') as f:
        json.dump(fav_articles, f, ensure_ascii=False, indent=2)
        
    with open(FAV_PUBS_PATH, 'w', encoding='utf-8') as f:
        json.dump(fav_pubs, f, ensure_ascii=False, indent=2)

    print("Done. Files overwritten.")

if __name__ == "__main__":
    main()
