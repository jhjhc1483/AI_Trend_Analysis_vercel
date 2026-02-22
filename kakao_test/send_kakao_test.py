import requests
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ==========================================
# 1. 환경 변수에서 정보 로드
# ==========================================
REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")
# ==========================================

def get_new_access_token():
    """Refresh Token으로 새로운 Access Token을 받아옵니다."""
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_API_KEY,
        "refresh_token": REFRESH_TOKEN
    }
    response = requests.post(url, data=data)
    tokens = response.json()
    
    if "access_token" in tokens:
        print("✅ Access Token 갱신 성공!")
        return tokens["access_token"]
    else:
        print(f"❌ 토큰 갱신 실패: {tokens}")
        return None

def send_message(access_token):
    """test_message.txt의 내용을 나에게 보내기 API로 전송합니다."""
    # txt 파일 읽기
    try:
        with open('test_message.txt', 'r', encoding='utf-8') as f:
            msg_content = f.read()
    except FileNotFoundError:
        print("❌ test_message.txt 파일을 찾을 수 없습니다.")
        return

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": msg_content,
            "link": {
                "web_url": "https://developers.kakao.com",
                "mobile_web_url": "https://developers.kakao.com"
            },
            "button_title": "내용 확인"
        })
    }

    res = requests.post(url, headers=headers, data=payload)
    
    if res.status_code == 200:
        print("🚀 카톡 메시지 전송 성공!")
    else:
        print(f"❌ 전송 실패: {res.status_code}")
        print(res.text)

# 실행부
if __name__ == "__main__":
    new_token = get_new_access_token()
    if new_token:
        send_message(new_token)