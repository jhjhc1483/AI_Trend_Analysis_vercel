import requests

# 본인의 정보로 수정하세요
rest_api_key = '여기에_REST_API_키_입력'
redirect_uri = 'https://localhost:3000' # 등록한 주소
authorize_code = '여기에_아까_복사한_인가_코드_입력'

url = "https://kauth.kakao.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": rest_api_key,
    "redirect_uri": redirect_uri,
    "code": authorize_code,
}

response = requests.post(url, data=data)
tokens = response.json()

if "access_token" in tokens:
    print("발급 성공!")
    print(f"Access Token: {tokens['access_token']}")
    print(f"Refresh Token: {tokens['refresh_token']}")
else:
    print(f"발급 실패: {tokens}")