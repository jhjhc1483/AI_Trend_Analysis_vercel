# 청크 안나눈 버전

import requests
import json
import os

def get_new_access_token(api_key, refresh_token):
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": api_key,
        "refresh_token": refresh_token
    }
    response = requests.post(url, data=data)
    return response.json().get("access_token")

def send_kakao_message(access_token):
    # 현재 스크립트 위치 기준으로 한 단계 위(..) 폴더의 data.txt를 찾습니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.abspath(os.path.join(current_dir, "..", "data.txt"))
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {data_path}")
        return

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": content,
            "link": {"web_url": "https://github.com"}
        })
    }
    
    res = requests.post(url, headers=headers, data=payload)
    if res.status_code == 200:
        print("🚀 메시지 전송 성공!")
    else:
        print(f"❌ 오류 발생: {res.text}")

if __name__ == "__main__":
    # GitHub Secrets에서 환경 변수로 가져옵니다.
    api_key = os.environ.get('KAKAO_REST_API_KEY')
    refresh_token = os.environ.get('KAKAO_REFRESH_TOKEN')

    token = get_new_access_token(api_key, refresh_token)
    if token:
        send_kakao_message(token)