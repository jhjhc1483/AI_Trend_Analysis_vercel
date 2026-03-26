import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from zoneinfo import ZoneInfo

# ================= 설정 부분 =================
sender_email = "dlsrhdwlsmdwjdcorrhk1@gmail.com"  # 보내는 사람
default_receiver = "jfchae1483@gmail.com" # 기본 받는 사람 (데이터 없을 시)

# GitHub Secrets에서 환경 변수로 전달된 값을 읽어옵니다.
app_password = os.environ.get("GMAIL_APP_PASSWORD")

# 파일 경로 설정
file_path = "codes/data.txt"
receiver_file_path = "codes/receiver_email.json"
# =============================================

def send_email():
    # 환경변수가 제대로 로드되었는지 확인
    if not app_password:
        print("오류: 환경 변수 'GMAIL_APP_PASSWORD'를 찾을 수 없습니다.")
        return

    # 수신자 목록 가져오기
    receivers = [default_receiver]
    if os.path.exists(receiver_file_path):
        try:
            with open(receiver_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    receivers = data
                    print(f"수신자 목록 로드 완료: {len(receivers)}명")
        except Exception as e:
            print(f"수신자 파일 읽기 오류: {e}. 기본 수신자를 사용합니다.")

    try:
        # 1. 파일 내용 읽기
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()

        # 2. 이메일 메시지 구성
        today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%y.%m.%d")
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(receivers)
        msg['Subject'] = f"{today} AI 일일 동향"

        # 파일 내용을 이메일 본문에 추가
        msg.attach(MIMEText(file_content, 'plain'))

        # 3. SMTP 서버 연결 및 이메일 전송
        print(f"SMTP 서버에 연결 중... (수신자: {msg['To']})")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # TLS 보안 연결 시작
        
        server.login(sender_email, app_password) # 로그인
        server.send_message(msg)                 # 메일 전송
        
        print("이메일 전송이 성공적으로 완료되었습니다!")

    except FileNotFoundError:
        print(f"오류: '{file_path}' 경로에서 파일을 찾을 수 없습니다.")
    except smtplib.SMTPAuthenticationError:
        print("오류: 이메일 로그인에 실패했습니다. 이메일 주소나 앱 비밀번호를 확인해 주세요.")
    except Exception as e:
        print(f"알 수 없는 오류가 발생했습니다: {e}")
    finally:
        # 서버 연결 종료
        try:
            server.quit()
        except:
            pass

if __name__ == "__main__":
    send_email()
