# gen_audio.py
import os
import asyncio
import google.generativeai as genai
import edge_tts

# 1. 환경 변수 설정 (GitHub Secrets에서 가져옴)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash") # 속도가 빠른 Flash 모델 사용

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
        
        # 4. Gemini 프롬프트 작성 (뉴스 캐스터 페르소나)
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
        
        # 불필요한 마크다운 기호 제거 (TTS 오류 방지)
        script = script.replace("*", "").replace("#", "").replace("-", "")
        print(f">>> 생성된 대본:\n{script[:100]}...") # 로그 확인용

        # 5. TTS 변환 (Edge TTS - 무료, 고품질)
        # 목소리 옵션: ko-KR-SunHiNeural (여성), ko-KR-InJoonNeural (남성)
        VOICE = "ko-KR-SunHiNeural" 
        output_file = "public/audio.mp3"
        
        print(f">>> 오디오 변환 시작 (Voice: {VOICE})...")
        communicate = edge_tts.Communicate(script, VOICE)
        await communicate.save(output_file)
        print(">>> 오디오 파일 생성 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
