# 청크 나눈 버전

import requests
import json

import os
import time

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
    """실제 메시지를 보내는 단위 함수"""
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
    api_key = os.environ.get('KAKAO_REST_API_KEY')
    refresh_token = os.environ.get('KAKAO_REFRESH_TOKEN')

    # 1. 토큰 갱신
    token = get_new_access_token(api_key, refresh_token)
    
    if token:
        # 2. 파일 읽기 (상위 폴더 data.txt)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.abspath(os.path.join(current_dir, "..", "data.txt"))
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
            
            # 3. 텍스트 분할 (안전하게 400자 단위로 설정)
            chunk_size = 900 
            chunks = [full_content[i:i+chunk_size] for i in range(0, len(full_content), chunk_size)]
            
            print(f"총 {len(chunks)}개의 메시지로 분할하여 전송합니다.")

            # 4. 루프를 돌며 순차 전송
            for idx, chunk in enumerate(chunks):
                success = send_kakao_message(token, chunk)
                if success:
                    print(f"[{idx+1}/{len(chunks)}] 전송 성공")
                else:
                    print(f"[{idx+1}/{len(chunks)}] 전송 실패")
                
                # 메시지 순서가 뒤바뀌지 않도록 아주 잠깐 대기 (0.5초)
                time.sleep(0.5)

        except FileNotFoundError:
            print("❌ data.txt 파일을 찾을 수 없습니다.")