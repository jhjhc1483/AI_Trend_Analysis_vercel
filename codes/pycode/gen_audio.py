# gen_audio.py
import os
import asyncio
import google.generativeai as genai
import edge_tts # Edge-TTS 라이브러리

# 1. 환경 변수 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3-flash-preview")

async def main():
    try:
        # 3. 데이터 읽기
        data_path = "codes/data.txt"
        if not os.path.exists(data_path):
            print("데이터 파일이 없습니다.")
            return

        with open(data_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        
        if not raw_text.strip():
            print("데이터 내용이 비어있습니다.")
            return

        print(">>> Gemini에게 브리핑 대본 작성을 요청합니다...")
        
        # 4. Gemini 프롬프트
        prompt = f"""
        너는 인공지능 동향을 매일 아침 전해주는 전문 뉴스 캐스터야.
        아래 [데이터]를 바탕으로 3분 내외의 라디오 뉴스 브리핑 대본을 작성해줘.
        
        [작성 조건]
        1. 인사말: "안녕하십니까, 00년00월00일 오늘의 AI 동향 브리핑입니다."로 시작할 것.
        2. 내용 구성: 가장 중요한 이슈를 정해진 시간 안에 브리핑 할 수 있게 갯수를 선정해서 자연스럽게 연결해줘.
        3. 어조: 아나운서처럼 명확하고 친절한 구어체("~습니다", "~입니다").
        4. 주의사항: 특수문자(*, #, - 등)나 이모지를 절대 넣지 마. 오직 읽을 수 있는 한글 텍스트만 작성해.
        5. 기관에 대한 발음을 정확히 해. "NIA"는 "니아", "NIPA"는 "나이파", "STEPI"는 "과학기술정책연구원", "KISTI"는 "키스티", "KISA"는 "키사", "IITP"는 "아이아이티피"로 읽어.
        6. 마무리: "이상으로 오늘의 브리핑을 마칩니다. 감사합니다."로 끝낼 것.

        [데이터]
        {raw_text}
        """

        response = model.generate_content(prompt)
        script = response.text
        
        script = script.replace("*", "").replace("#", "").replace("-", "").replace('"', "")
        print(f">>> 생성된 대본:\n{script[:100]}...")

        # 5. Edge-TTS 생성
        print(">>> Edge-TTS(ko-KR-SunHiNeural)로 변환 시작...")
        
        voice = "ko-KR-SunHiNeural"
        output_file = "public/audio.mp3"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        communicate = edge_tts.Communicate(script, voice, rate="+0%")
        await communicate.save(output_file)
        
        print(f">>> 오디오 파일 생성 완료! ({output_file})")

        # 6. 카카오톡 공유용 브리핑 텍스트 생성 (추가됨)
        print(">>> Gemini에게 카카오톡 공유용 브리핑 텍스트를 요청합니다...")
        import json
        from datetime import datetime

        today_str = datetime.now().strftime("%Y.%m.%d")
        
        briefing_prompt = f"""
        너는 IT/AI 트렌드를 사람들에게 전달하는 뉴스 큐레이터야.
        아래 [데이터]를 바탕으로, 오늘 가장 중요한 핵심 기사 3개만 골라서 아래의 [출력 양식]에 맞춰 작성해줘.
        
        [출력 양식]
        - [기사 요약 1 (간결하게 한 줄로)]
        - [기사 요약 2 (간결하게 한 줄로)]
        - [기사 요약 3 (간결하게 한 줄로)]
        
        [주의사항]
        - [출력 양식] 텍스트 구조를 그대로 유지해.
        - 제목이나 부연설명 없이 오직 '- '로 시작하는 리스트 3줄만 출력해.

        [데이터]
        {raw_text}
        """

        briefing_response = model.generate_content(briefing_prompt)
        briefing_text = briefing_response.text.strip()
        
        # 결과를 JSON으로 저장 (visualizer_brief.html에서 읽어서 쓰기 위함)
        briefing_data = {
            "date": today_str,
            "text": briefing_text
        }
        
        briefing_file = "public/briefing.json"
        with open(briefing_file, "w", encoding="utf-8") as bf:
            json.dump(briefing_data, bf, ensure_ascii=False, indent=2)
            
        print(">>> 카톡 공유용 브리핑 JSON 생성 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    # 윈도우 환경에서 발생할 수 있는 asyncio 에러 방지
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())