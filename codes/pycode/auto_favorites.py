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

PUB_SITES = ['IITP', 'NIA', 'STEPI', 'NIPA', 'KISDI', 'KISTI', 'KISA', 'TTA']

def load_json_files():
    all_articles = []
    all_pubs = []
    
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
                    item_data = {
                        'title': item.get('기사명') or item.get('제목') or '제목 없음',
                        'link': item.get('링크') or item.get('link') or '#',
                        'date': date_str,
                        'site': site_name
                    }
                    if is_pub:
                        all_pubs.append(item_data)
                    else:
                        all_articles.append(item_data)
                        
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            
    return all_articles, all_pubs

def select_and_classify(items, item_type='ARTICLE'):
    if not items:
        return []

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')

    # 프롬프트 구성
    item_text = "\n".join([f"{i}. [{item['site']}] {item['title']} ({item['link']})" for i, item in enumerate(items)])

    if item_type == 'ARTICLE':
        system_instruction = """
당신은 대한민국 국방 및 AI 동향 분석 전문가입니다.
주어진 기사 목록 중에서 '국방 AI', '국방 기술', 'AI 최신 트렌드', '주요 기술 정책'과 관련된 중요 기사를 선정해주세요.
선정 기준:
1. 국방/군사 분야와 직접 관련된 AI/IT 기사 (최우선)
2. AI 기술의 획기적인 발전이나 주요 기업(Google, OpenAI 등)의 핵심 발표
3. 정부(과기정통부 등)의 주요 AI/SW 정책

각 선정된 기사에 대해 다음 카테고리 중 하나를 지정해야 합니다:
- 국방: 국방부, 방사청 등 직접적 국방 AI/IT 관련
- 육군: 육군 AI/IT 관련 특화 내용
- 민간: 일반 기업, 기술 트렌드, 해외 동향(중요도에 따라 10건 이하)
- 기관: 정부 기관, 공공 정책, 연구소
- 기타: 그 외

응답 형식은 반드시 유효한 JSON 배열이어야 합니다. 마크다운이나 코드 블록 없이 순수 JSON만 반환하세요.
형식:
[
  { "index": 0, "category": "국방" },
  ...
]
"""
        user_prompt = f"다음 기사 목록에서 중요 기사를 선정하고 카테고리를 분류해 주세요:\n\n{item_text}"
    else:
        # 간행물은 '간행물'로 통일
        system_instruction = """
당신은 AI 및 IT 기술 간행물 분석 전문가입니다.
주어진 간행물(보고서) 목록 중에서 국방 및 AI 기술 연구 개발에 도움이 될만한 핵심 간행물을 선정해주세요.
선정 기준:
1. 국방, 안보, 보안 관련 기술 보고서
2. 생성형 AI, LLM, 반도체 등 최신 핵심 기술 동향 보고서
3. 주요 정책 연구 보고서

선정된 항목의 카테고리는 모두 '간행물'로 지정해주세요.

응답 형식은 반드시 유효한 JSON 배열이어야 합니다. 마크다운이나 코드 블록 없이 순수 JSON만 반환하세요.
형식:
[
  { "index": 0, "category": "간행물" },
  ...
]
"""
        user_prompt = f"다음 간행물 목록에서 중요 항목을 선정해 주세요:\n\n{item_text}"

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
                if cat not in ["국방", "육군", "민간", "기관", "기타"]:
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
    
    articles, pubs = load_json_files()
    print(f"Found {len(articles)} articles and {len(pubs)} publications for {YESTERDAY}")
    
    # 1. 기사 처리
    fav_articles = select_and_classify(articles, 'ARTICLE')
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
