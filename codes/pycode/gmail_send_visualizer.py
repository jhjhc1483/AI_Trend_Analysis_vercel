import smtplib
import os
import json
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv(override=True)

# ================= 설정 부분 =================
sender_email = "aiforarmy@gmail.com"  # 보내는 사람
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
                valid_receivers_all = [] # 저장을 위한 전체 유효 목록
                email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
                
                was_modified = False
                for item in email_list:
                    email_addr = ""
                    reg_date_str = ""
                    
                    if isinstance(item, dict):
                        email_addr = item.get("email", "")
                        reg_date_str = item.get("date", "")
                    elif isinstance(item, str):
                        email_addr = item
                        was_modified = True # 문자열은 나중에 객체로 변환되어 저장됨
                    
                    if not email_addr: 
                        was_modified = True
                        continue
                    
                    # 제어 문자 제거 및 공백 제거
                    clean_email = "".join(c for c in email_addr if ord(c) >= 32).strip()
                    
                    if email_regex.match(clean_email):
                        # 날짜 체크 (있을 경우에만)
                        if reg_date_str:
                            try:
                                reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
                                if (today - reg_date).days >= 365:
                                    was_modified = True # 만료된 항목 발견
                                    continue # 만료됨
                            except:
                                pass # 날짜 형식이 잘못된 경우 일단 포함
                        
                        # 유효한 항목 추가 (객체 형태 유지)
                        valid_receivers_all.append({"email": clean_email, "date": reg_date_str or today.strftime("%Y-%m-%d")})
                    else:
                        was_modified = True # 유효하지 않은 메일 제거됨

                # 6. 변경사항이 있으면 파일에 다시 저장 (영구 삭제)
                if was_modified:
                    try:
                        with open(receiver_file_path, "w", encoding="utf-8") as f:
                            json.dump({"emails": valid_receivers_all}, f, ensure_ascii=False, indent=2)
                        print(f"수신자 목록 정리 완료: {len(valid_receivers_all)}명 유지")
                    except Exception as e:
                        print(f"수신자 목록 파일 저장 중 오류: {e}")

                # 7. 실제 발송을 위한 이메일 주소만 추출 (최대 100명)
                receivers = [item["email"] for item in valid_receivers_all[:100]]
                
                if receivers:
                    print(f"수신자 목록 검증 및 만료 체크 완료: {len(receivers)}명")
                else:
                    print("경고: 유효한 수신자가 없습니다. 기본 수신자를 사용합니다.")
                    receivers = [default_receiver]
        except Exception as e:
            print(f"수신자 파일 읽기 오류: {e}. 기본 수신자를 사용합니다.")

    try:
        # 1. 정보 및 데이터 준비
        url = "https://ai-trend-analysis.vercel.app/visualizer.html"
        
        # KST 시간으로 오늘 날짜 가져오기
        now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
        date_str = now_kst.strftime("%Y년 %m월 %d일")
        subject = f"{date_str} AI 동향 브리핑"
        
        # 2. 데이터 파일 읽기
        report_text = "일일 동향 데이터를 읽을 수 없습니다."
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                report_text = f.read()

        # Plain text body (기본 요약)
        text_body = f"오늘의 AI 동향 브리핑이 도착했습니다.\n아래 링크에서 확인하실 수 있습니다.\n\n{url}"
        
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
            </div>
        </body>
        </html>
        """

        # 3. SMTP 서버 연결
        print("SMTP 서버에 연결 중...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # TLS 보안 연결 시작
        
        server.login(sender_email, app_password) # 로그인

        # 4. 각 수신자별로 개별 메일 생성 및 전송
        print(f"총 {len(receivers)}명의 수신자에게 메일을 발송합니다...")
        for receiver in receivers:
            msg = MIMEMultipart('mixed')
            msg['From'] = sender_email
            msg['To'] = receiver
            msg['Subject'] = subject

            # Alternative 파트로 HTML 카드와 기본 텍스트 요약 묶기
            msg_alt = MIMEMultipart('alternative')
            msg_alt.attach(MIMEText(text_body, 'plain'))
            msg_alt.attach(MIMEText(html_body, 'html'))
            msg.attach(msg_alt)

            # HTML '밖'에 data.txt 원본 내용을 평문으로 추가
            msg.attach(MIMEText(f"\n----------------\n[상세 내용]\n{report_text}", 'plain'))

            server.send_message(msg)                 # 개별 메일 전송
            print(f" -> 발송 완료: {receiver}")
        
        print("모든 이메일 전송이 성공적으로 완료되었습니다!")

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
