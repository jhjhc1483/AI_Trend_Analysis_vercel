"""
관리자 알림 메일 공용 모듈 (Gmail SMTP).

크롤링 경고(run_crawlers.py), 단계 실패/일일 요약(pipeline_report.py)에서 사용합니다.
GMAIL_APP_PASSWORD 환경변수(GitHub Secrets)가 필요합니다.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SENDER_EMAIL = "aiforarmy@gmail.com"   # 보내는 계정 (구독자 메일과 동일)
ADMIN_EMAIL = "jfchae1483@gmail.com"   # 관리자


def send_admin_mail(subject, html_body, plain_text=None):
    """관리자에게 HTML 메일을 보냅니다. 성공하면 True."""
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password:
        print("⚠️ 'GMAIL_APP_PASSWORD' 환경변수가 없어 관리자 메일을 보낼 수 없습니다.")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(plain_text or "HTML을 지원하는 메일 앱에서 확인해 주세요.", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    server = None
    try:
        print(f"📧 관리자에게 메일 발송 중: {subject}")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, app_password)
        server.send_message(msg)
        print("✅ 관리자 메일 발송 완료")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ 관리자 메일 발송 실패: SMTP 인증 오류 (Gmail 앱 비밀번호를 확인하세요)")
        return False
    except Exception as e:
        print(f"❌ 관리자 메일 발송 중 오류: {e}")
        return False
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass
