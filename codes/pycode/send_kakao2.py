import requests
import json
import os
import time
from dotenv import load_dotenv

# 로컬 테스트 시 .env 파일을 읽어오기 위함 (GitHub Actions에서는 무시됨)
load_dotenv()

def get_new_access_token(api_key, refresh_token):
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": api_key,
        "refresh_token": refresh_token
    }
    response = requests.post(url, data=data)
    # 응답 결과 확인 로직 추가
    res_json = response.json()
    if "access_token" in res_json:
        return res_json.get("access_token")
    else:
        print(f"❌ 토큰 갱신 실패: {res_json}")
        return None

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
    # GitHub Secrets에 등록한 이름과 일치해야 함
    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    REFRESH_TOKEN = os.getenv('KAKAO_REFRESH_TOKEN')

    if not API_KEY or not REFRESH_TOKEN:
        print("❌ 환경 변수(Secrets)를 찾을 수 없습니다.")
    else:
        token = get_new_access_token(API_KEY, REFRESH_TOKEN)
        
        if token:
            # 스크립트 위치 기준 상위 폴더의 data.txt 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.abspath(os.path.join(current_dir, "..", "data.txt"))
            
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    full_content = f.read()
                
                # 메시지 분할 (안전하게 900자 단위)
                chunk_size = 900
                chunks = [full_content[i:i+chunk_size] for i in range(0, len(full_content), chunk_size)]
                
                print(f"총 {len(chunks)}개의 메시지 전송 시작...")
                for idx, chunk in enumerate(chunks):
                    if send_kakao_message(token, chunk):
                        print(f"[{idx+1}/{len(chunks)}] 전송 완료")
                    else:
                        print(f"[{idx+1}/{len(chunks)}] 전송 실패")
                    time.sleep(1.0) # 전송 안정성을 위해 간격 조정
                    
            except FileNotFoundError:
                print(f"❌ 파일을 찾을 수 없습니다: {data_path}")