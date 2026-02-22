import requests
import json
import os
import time
from dotenv import load_dotenv

# 1. .env 파일의 환경 변수 로드
load_dotenv()

def get_new_access_token(api_key, refresh_token):
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": api_key,
        "refresh_token": refresh_token
    }
    response = requests.post(url, data=data)
    return response.json().get("access_token")

def send_kakao_message(access_token, text_chunk):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": text_chunk,
            "link": {"web_url": "https://github.com"}
        })
    }
    res = requests.post(url, headers=headers, data=payload)
    return res.status_code == 200

if __name__ == "__main__":
    # 2. 로드된 환경 변수 사용 (Secrets 이름과 동일하게 설정)
    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    REFRESH_TOKEN = os.getenv('KAKAO_REFRESH_TOKEN')

    if not API_KEY or not REFRESH_TOKEN:
        print("❌ .env 파일에서 키를 찾을 수 없습니다.")
    else:
        token = get_new_access_token(API_KEY, REFRESH_TOKEN)
        
        if token:
            # 3. 상위 폴더의 data.txt 읽기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.abspath(os.path.join(current_dir, "..", "test_message.txt"))
            
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    full_content = f.read()
                
                # 4. 분할 전송 (약 400자 단위)
                chunk_size = 900
                chunks = [full_content[i:i+chunk_size] for i in range(0, len(full_content), chunk_size)]
                
                for idx, chunk in enumerate(chunks):
                    if send_kakao_message(token, chunk):
                        print(f"[{idx+1}/{len(chunks)}] 전송 완료")
                    time.sleep(0.5)
                    
            except FileNotFoundError:
                print(f"❌ 파일을 찾을 수 없습니다: {data_path}")