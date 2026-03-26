import smtplib
import os
import json
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from zoneinfo import ZoneInfo

# ================= 설정 부분 =================
sender_email = "jfchae1483@gmail.com"  # 보내는 사람
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
                
                # ✅ 새 구조(객체)와 구 구조(리스트) 모두 대응
                email_list = data if isinstance(data, list) else data.get("emails", [])
                
                # ✅ 개별 만료 체크 (365일)
                today = datetime.now()
                valid_receivers = []
                email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
                
                for item in email_list:
                    email_addr = ""
                    reg_date_str = ""
                    
                    if isinstance(item, dict):
                        email_addr = item.get("email", "")
                        reg_date_str = item.get("date", "")
                    elif isinstance(item, str):
                        email_addr = item
                    
                    if not email_addr: continue
                    
                    # 제어 문자 제거 및 공백 제거
                    clean_email = "".join(c for c in email_addr if ord(c) >= 32).strip()
                    
                    if email_regex.match(clean_email):
                        # 날짜 체크 (있을 경우에만)
                        if reg_date_str:
                            try:
                                reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
                                if (today - reg_date).days >= 365:
                                    continue # 만료됨
                            except:
                                pass # 날짜 형식이 잘못된 경우 일단 포함
                        
                        valid_receivers.append(clean_email)
                        if len(valid_receivers) >= 100:
                            break
                
                if valid_receivers:
                    receivers = valid_receivers
                    print(f"수신자 목록 검증 및 만료 체크 완료: {len(receivers)}명")
                else:
                    print("경고: 유효한 수신자가 없습니다. 기본 수신자를 사용합니다.")
        except Exception as e:
            print(f"수신자 파일 읽기 오류: {e}. 기본 수신자를 사용합니다.")

    try:
        # 1. 이메일 메시지 구성
        url = "https://ai-trend-analysis.vercel.app/visualizer.html"
        subject = "오늘의 AI 동향 브리핑이 도착했어요!"
        
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = ", ".join(receivers)
        msg['Subject'] = subject

        # 2. 데이터 파일 읽기
        report_text = "일일 동향 데이터를 읽을 수 없습니다."
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                report_text = f.read()

        # Plain text body
        text_body = f"오늘의 AI 동향 브리핑이 도착했습니다.\n아래 링크에서 확인하실 수 있습니다.\n\n{url}\n\n---\n오늘의 동향 내용:\n{report_text}"
        
        # HTML body with brand styling
        html_body = f"""
        <html>
        <body style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 15px; padding: 30px; background-color: #ffffff;">
                <h2 style="color: #2c5234; border-bottom: 2px solid #2c5234; padding-bottom: 10px;">오늘의 AI 동향 브리핑이 도착했어요! 📰</h2>
                <p style="font-size: 1.1em;">오늘의 AI 주요 소식과 동향을 아래 시각화 페이지에서 쉽고 간편하게 확인해 보세요.</p>
                <div style="text-align: center; margin: 40px 0;">
                    <a href="{url}" style="background-color: #2c5234; color: white; padding: 15px 30px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 1.1em; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">동향 브리핑 확인하기</a>
                </div>
                <p style="color: #666; font-size: 0.9em;">링크가 클릭되지 않는다면 아래 주소를 복사해 브라우저에 붙여넣어 주세요:<br>
                <a href="{url}" style="color: #3498db;">{url}</a></p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 10px; font-size: 0.9em;">
                    <h3 style="margin-top: 0; color: #2c5234;">오늘의 동향 리포트 (텍스트)</h3>
                    <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit;">{report_text}</pre>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 0.85em; text-align: center;">&copy; Maj.Cjh. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

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
