# gen_audio.py
import os
import asyncio
import google.generativeai as genai
from openai import OpenAI # OpenAI 라이브러리 추가

# 1. 환경 변수 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# 2. 클라이언트 설정
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

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

        response = gemini_model.generate_content(prompt)
        script = response.text
        
        # 기본 전처리
        script = script.replace("*", "").replace("#", "").replace("-", "")
        print(f">>> 생성된 대본:\n{script[:100]}...")

        # 5. OpenAI TTS 생성
        # 모델: tts-1 (빠름, 일반용) / tts-1-hd (고음질)
        # 목소리: alloy, echo, fable, onyx, nova, shimmer 중 택1
        # nova: 차분한 여성 톤 (뉴스에 적합) / onyx: 신뢰감 있는 남성 톤
        print(">>> OpenAI TTS로 오디오 생성 중...")
        
        output_file = "public/audio.mp3"
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova", 
            input=script
        )

        # 파일 저장
        response.stream_to_file(output_file)
        print(">>> 오디오 파일 생성 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())