# gen_audio.py
import os
import asyncio
from google import genai
from google.genai import types
import edge_tts # Edge-TTS 라이브러리

# 1. 환경 변수 설정
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.env"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Gemini 설정
client = genai.Client(api_key=GEMINI_API_KEY)

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

        # 기준 날짜: REPORT_DATE(YYYY-MM-DD)가 있으면 그 날짜(과거 날짜는 브리핑 텍스트만 생성), 없으면 오늘
        import json
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
        report_env = os.environ.get("REPORT_DATE", "").strip()
        today_date = datetime.strptime(report_env, "%Y-%m-%d") if report_env else now_kst
        today_key = today_date.strftime("%y.%m.%d")  # data.json 키 형식 (예: 24.03.26)
        is_today = today_key == now_kst.strftime("%y.%m.%d")

        # 빈 데이터나 지난 날짜 데이터로 엉뚱한 브리핑을 만들지 않도록 확인
        if f"📢{today_key} AI 일일 동향📢" not in raw_text:
            raise RuntimeError(f"data.txt가 {today_key} 날짜 데이터가 아닙니다. 즐겨찾기 생성 단계가 성공했는지 확인하세요.")
        if "◾" not in raw_text:
            raise RuntimeError(f"data.txt에 {today_key} 기사가 하나도 없습니다. 즐겨찾기 생성 단계가 성공했는지 확인하세요.")

        # URL 제거 (토큰 수 낭비 방지)
        import re
        text_without_urls = re.sub(r'http[s]?://\S+', '', raw_text)

        max_retries = 5
        if is_today:
            await make_audio(text_without_urls, max_retries)
        else:
            print(f">>> {today_key}는 지난 날짜라 오디오는 건너뛰고 브리핑 텍스트만 생성합니다.")

        # 6. 카카오톡 공유용 브리핑 텍스트 생성 (추가됨)
        print(">>> Gemini에게 카카오톡 공유용 브리핑 텍스트를 요청합니다...")

        briefing_prompt = f"""
        너는 IT/AI 트렌드를 사람들에게 전달하는 뉴스 큐레이터야.
        아래 [데이터]를 바탕으로, 오늘 가장 육군 간부들이 관심 갖을만한 AI 관련 주요 핵심 기사 3개만 골라서 아래의 [출력 양식]에 맞춰 작성해줘.

        [출력 양식]
        - [기사 요약 1 (간결하게 한 줄로)]
        - [기사 요약 2 (간결하게 한 줄로)]
        - [기사 요약 3 (간결하게 한 줄로)]

        [주의사항]
        - [출력 양식] 텍스트 구조를 그대로 유지해.
        - 제목이나 부연설명 없이 오직 '- '로 시작하는 리스트 3줄만 출력해.
        - 팩트 왜곡 주의: 기고문, 제안, 의견, 아이디어 단계의 기사를 "도입합니다", "공급됩니다"처럼 이미 확정된 기정사실로 요약하면 절대 안 돼. 사실 관계를 명확히 파악하여 "~제안했습니다", "~주장했습니다", "~필요성이 제기되었습니다"처럼 원문의 문맥에 맞게 정확히 표현해.

        [데이터]
        {text_without_urls}
        """

        for attempt in range(max_retries):
            try:
                briefing_response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=briefing_prompt
                )
                briefing_text = briefing_response.text.strip()
                break
            except Exception as e:
                error_msg = str(e)
                if ("429" in error_msg or "503" in error_msg) and attempt < max_retries - 1:
                    print(f"API Error (429/503). 60초 대기 후 재시도합니다... ({attempt+1}/{max_retries})")
                    await asyncio.sleep(60)
                else:
                    raise e

        print(">>> 카톡 공유용 브리핑 JSON 텍스트 생성 완료!")

        # 7. data.json에 브리핑 내용 누적 저장
        data_json_path = "codes/data.json"
        if os.path.exists(data_json_path):
            try:
                with open(data_json_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except json.JSONDecodeError:
                history_data = {}
        else:
            history_data = {}

        if today_key in history_data:
            history_data[today_key]["briefing"] = briefing_text
        else:
            history_data[today_key] = {"briefing": briefing_text}

        with open(data_json_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        print(">>> data.json에 브리핑 내용 누적 저장 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)


async def make_audio(text_without_urls, max_retries):
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
        6. 팩트 왜곡 주의: 기고문, 제안, 의견, 아이디어 단계의 기사를 "도입합니다", "확정되었습니다"처럼 기정사실로 요약하면 절대 안 돼. 사실 관계를 명확히 파악하여 "~제안했습니다", "~주장했습니다" 등 원문의 문맥에 맞게 정확히 전달해.
        7. 마무리: "이상으로 오늘의 브리핑을 마칩니다. 감사합니다."로 끝낼 것.

        [데이터]
        {text_without_urls}
        """

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=prompt
                )
                script = response.text
                break
            except Exception as e:
                error_msg = str(e)
                if ("429" in error_msg or "503" in error_msg) and attempt < max_retries - 1:
                    print(f"API Error (429/503). 60초 대기 후 재시도합니다... ({attempt+1}/{max_retries})")
                    await asyncio.sleep(60)
                else:
                    raise e
        
        script = script.replace("*", "").replace("#", "").replace("-", "").replace('"', "")
        print(f">>> 생성된 대본:\n{script[:100]}...")

        # 5. Edge-TTS 생성
        print(">>> Edge-TTS(ko-KR-InJoonNeural)로 변환 시작...")
        
        voice = "ko-KR-InJoonNeural"
        output_file = "public/audio.mp3"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 임시 파일에 먼저 저장 → 변환 도중 실패해도 기존 audio.mp3가 0바이트로 망가지지 않음
        tmp_file = output_file + ".tmp"
        try:
            communicate = edge_tts.Communicate(script, voice, rate="+0%")
            await communicate.save(tmp_file)
            os.replace(tmp_file, output_file)
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

        print(f">>> 오디오 파일 생성 완료! ({output_file})")


if __name__ == "__main__":
    # 윈도우 환경에서 발생할 수 있는 asyncio 에러 방지
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
