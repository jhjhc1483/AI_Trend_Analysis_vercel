import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ================= 설정 부분 =================
# GitHub Secrets에서 환경 변수로 전달된 값을 읽어옵니다.
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

# 파일 경로 설정
file_path = "codes/data.txt"
receiver_file_path = "codes/receiver_telegram.json"
# =============================================

def send_telegram_message():
    # 환경변수가 제대로 로드되었는지 확인
    if not bot_token:
        print("오류: 환경 변수 'TELEGRAM_BOT_TOKEN'를 찾을 수 없습니다.")
        return

    # 수신자 목록 가져오기
    receivers = []
    if os.path.exists(receiver_file_path):
        try:
            with open(receiver_file_path, "r", encoding="utf-8") as f:
                receivers = json.load(f)
                if not isinstance(receivers, list):
                    receivers = []
        except Exception as e:
            print(f"수신자 파일 읽기 오류: {e}")
            return

    if not receivers:
        print("알림: 등록된 텔레그램 수신자가 없습니다.")
        return

    # 1. 파일 내용 읽기
    if not os.path.exists(file_path):
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        
        if not file_content.strip():
            print("알림: 발송할 내용이 비어 있습니다.")
            return

        # 2. 메시지 구성
        today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%y.%m.%d")
        header = f"📢 {today} AI 일일 동향\n\n"
        full_message = header + file_content

        # 3. 텔레그램 API 호출
        print(f"텔레그램 메시지 발송 시작... (수신자: {len(receivers)}명)")
        
        # 텔레그램 메시지 길이 제한(4096자) 처리 (필요시 분할 발송)
        def split_message(text, limit=4000):
            return [text[i:i+limit] for i in range(0, len(text), limit)]

        message_chunks = split_message(full_message)

        for chat_id in receivers:
            try:
                for chunk in message_chunks:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "HTML" # HTML 태그를 사용할 수 있도록 설정 (기본은 Markdown이 아님)
                    }
                    # parse_mode를 HTML로 설정하면 일부 특수문자(<, >, &) 처리가 필요할 수 있으나, 
                    # data.txt 내용이 일반 텍스트라면 'plain' 느낌으로 보내기 위해 필터링하거나 생략 가능.
                    # 여기서는 안전하게 parse_mode를 제거하거나 plain으로 처리.
                    payload.pop("parse_mode") 
                    
                    response = requests.post(url, data=payload)
                    if response.ok:
                        print(f"성공: {chat_id}")
                    else:
                        print(f"실패 ({chat_id}): {response.status_code} - {response.text}")
            except Exception as e:
                print(f"오류 ({chat_id}): {e}")

        print("텔레그램 발송 프로세스 완료!")

    except Exception as e:
        print(f"알 수 없는 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    send_telegram_message()
