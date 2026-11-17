"""
매일 아침 구독자에게 AI 동향 브리핑 메일을 보냅니다. (kakao_or_gmail_send.yml)

보내기 전에 codes/data.txt가 '오늘 날짜의 동향'인지 확인합니다.
앞 단계(크롤링 → AI 자동 선정)가 실패하거나 늦어져 어제 내용이 남아 있으면
구독자에게는 보내지 않고 관리자에게만 경고 메일을 보낸 뒤 실패(exit 1)로 끝냅니다.
데이터가 준비되면 GitHub Actions에서 이 워크플로우를 수동 실행(mode: send)하면 됩니다.

오디오 생성이 끝나면 자동으로 실행되고, 체인이 끊긴 경우를 대비해 예약 실행도 한 번 더 있습니다.
같은 날 여러 번 실행돼도 구독자에게는 하루 한 번만 보냅니다. (codes/state/mail.json에 기록)
다시 보내야 하면 MAIL_MODE=resend (워크플로우 mode: resend)로 실행하세요.
"""
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

from pipeline_state import REPORT_HEADER_REGEX, now_kst, read_state, write_state
from subscribers import clean_subscribers, load_subscribers, mask_email, save_subscribers

load_dotenv(override=True)

# ================= 설정 부분 =================
sender_email = "aiforarmy@gmail.com"      # 보내는 사람
default_receiver = "jfchae1483@gmail.com"  # 관리자: 구독자가 없을 때 기본 수신자 + 경고 메일 수신자

# GitHub Secrets에서 환경 변수로 전달된 값을 읽어옵니다.
app_password = os.environ.get("GMAIL_APP_PASSWORD")

# 파일 경로 설정
file_path = "codes/data.txt"
receiver_file_path = "codes/receiver_email.json"
MAX_RECIPIENTS = 100  # api/subscribe.js 의 구독자 상한과 같게 유지

VISUALIZER_URL = "https://ai-trend-analysis.vercel.app/visualizer.html"
WORKFLOW_URL = "https://github.com/jhjhc1483/AI_Trend_Analysis_vercel/actions/workflows/kakao_or_gmail_send.yml"
# =============================================


def check_report(report_text, today_key):
    """오늘 보내도 되는 동향이면 None, 아니면 보내면 안 되는 이유를 반환합니다."""
    if report_text is None:
        return f"'{file_path}' 파일이 없습니다."
    found = REPORT_HEADER_REGEX.search(report_text)
    if not found or found.group(1) != today_key:
        current = found.group(1) if found else "날짜 정보 없음"
        return f"data.txt가 오늘({today_key}) 동향이 아닙니다. (현재 파일: {current})"
    if "◾" not in report_text:
        return f"오늘({today_key}) 동향에 선정된 기사가 하나도 없습니다."
    return None


def load_receivers():
    """구독자 목록을 읽어 발송 대상 주소 리스트를 반환합니다. (암호화/평문 모두 subscribers.py에서 처리)"""
    receivers = [default_receiver]
    try:
        raw, _ = load_subscribers(receiver_file_path)
        valid, removed = clean_subscribers(raw)
        if removed:
            save_subscribers(valid, receiver_file_path)
            print(f"수신자 목록 정리 완료: {removed}건 삭제, {len(valid)}명 유지")

        if valid:
            receivers = [item["email"] for item in valid[:MAX_RECIPIENTS]]
            print(f"수신자 목록 검증 및 만료 체크 완료: {len(receivers)}명")
        else:
            print("경고: 유효한 수신자가 없습니다. 기본 수신자를 사용합니다.")
    except Exception as e:
        print(f"수신자 파일 읽기 오류: {e}. 기본 수신자를 사용합니다.")
    return receivers


def build_briefing_message(receiver, subject, report_text):
    text_body = f"오늘의 AI 동향 브리핑이 도착했습니다.\n아래 링크에서 확인하실 수 있습니다.\n\n{VISUALIZER_URL}"
    html_body = f"""
        <html>
        <body style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 15px; padding: 30px; background-color: #ffffff;">
                <h2 style="color: #2c5234; border-bottom: 2px solid #2c5234; padding-bottom: 10px;">오늘의 AI 동향 브리핑이 도착했어요! 📰</h2>
                <p style="font-size: 1.1em;">오늘의 AI 주요 소식과 동향을 아래 시각화 페이지에서 쉽고 간편하게 확인해 보세요.</p>
                <div style="text-align: center; margin: 40px 0;">
                    <a href="{VISUALIZER_URL}" style="background-color: #2c5234; color: white; padding: 15px 30px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 1.1em; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">동향 브리핑 확인하기</a>
                </div>
                <p style="color: #666; font-size: 0.9em;">링크가 클릭되지 않는다면 아래 주소를 복사해 브라우저에 붙여넣어 주세요:<br>
                <a href="{VISUALIZER_URL}" style="color: #3498db;">{VISUALIZER_URL}</a></p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            </div>
        </body>
        </html>
        """

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
    return msg


def build_alert_message(reason, today_key):
    body = (
        f"오늘({today_key}) 구독자 메일 발송을 중단했습니다.\n\n"
        f"■ 이유\n{reason}\n\n"
        "■ 확인할 것\n"
        "앞 단계 워크플로우(Run Python Scripts Daily → Auto Favorites Generation)가 "
        "성공했는지 GitHub Actions에서 확인하세요.\n\n"
        "■ 다시 보내는 방법\n"
        "데이터가 준비되면 아래 페이지에서 'Run workflow'를 눌러 mode를 send로 실행하세요.\n"
        f"{WORKFLOW_URL}\n"
    )
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = sender_email
    msg['To'] = default_receiver
    msg['Subject'] = f"[AI 동향 메일 발송 중단] {today_key} 데이터가 준비되지 않았습니다"
    return msg


def send_messages(messages):
    """[(수신자, 메시지)]를 발송하고 실패 건수를 반환합니다. 한 명이 실패해도 나머지는 계속 보냅니다."""
    print("SMTP 서버에 연결 중...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    try:
        server.starttls()  # TLS 보안 연결 시작
        server.login(sender_email, app_password)

        print(f"총 {len(messages)}명의 수신자에게 메일을 발송합니다...")
        failed = 0
        for receiver, msg in messages:
            try:
                server.send_message(msg)
                print(f" -> 발송 완료: {mask_email(receiver)}")  # 공개 로그에 주소를 남기지 않음
            except Exception as e:
                failed += 1
                print(f" -> 발송 실패: {mask_email(receiver)} ({type(e).__name__})")
        return failed
    finally:
        try:
            server.quit()
        except Exception:
            pass


def main():
    if not app_password:
        print("오류: 환경 변수 'GMAIL_APP_PASSWORD'를 찾을 수 없습니다.")
        return 1

    now = now_kst()
    today_key = now.strftime("%y.%m.%d")

    # 하루 한 번만 발송 (자동 체인 + 예약 안전장치가 겹쳐도 중복 발송하지 않음)
    resend = os.environ.get("MAIL_MODE", "send").strip().lower() == "resend"
    if not resend and read_state("mail").get("date") == today_key:
        print(f"⏭️ 오늘({today_key}) 메일은 이미 발송했습니다. 건너뜁니다. (다시 보내려면 mode: resend)")
        return 0

    report_text = None
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            report_text = f.read()

    try:
        problem = check_report(report_text, today_key)
        if problem:
            print(f"⚠️ 구독자 발송 중단: {problem}")
            send_messages([(default_receiver, build_alert_message(problem, today_key))])
            print("관리자에게 경고 메일을 보냈습니다.")
            return 1

        receivers = load_receivers()
        subject = f"{now.strftime('%Y년 %m월 %d일')} AI 동향 브리핑"
        failed = send_messages([(r, build_briefing_message(r, subject, report_text)) for r in receivers])

        # 한 명에게라도 보냈으면 '오늘 발송함'으로 기록 (재실행 시 받은 사람에게 중복 발송 방지)
        if failed < len(receivers):
            write_state("mail", {
                "date": today_key,
                "sent_at": now.isoformat(timespec="seconds"),
                "sent": len(receivers) - failed,
                "failed": failed,
            })
        if failed:
            print(f"❌ {len(receivers)}명 중 {failed}명에게 발송하지 못했습니다.")
            return 1
        print("모든 이메일 전송이 성공적으로 완료되었습니다!")
        return 0

    except smtplib.SMTPAuthenticationError:
        print("오류: 이메일 로그인에 실패했습니다. 이메일 주소나 앱 비밀번호를 확인해 주세요.")
        return 1
    except Exception as e:
        print(f"알 수 없는 오류가 발생했습니다: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
