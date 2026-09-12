import os
import sys
import time
import subprocess
import re
import argparse
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Windows 터미널(cp949) 이모지 출력 인코딩 방어
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv(override=False)
ORIGINAL_SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")

# ================= 설정 부분 =================
SENDER_EMAIL = "aiforarmy@gmail.com"
ADMIN_RECEIVER = "jfchae1483@gmail.com"

# 크롤링 대상 스크립트 목록 (파일명, 소스 표시명)
CRAWLER_SCRIPTS = [
    ("mnd.py", "국방부"),
    ("etnews.py", "전자신문"),
    ("aitimes.py", "AI타임스"),
    ("NIA.py", "한국지능정보사회진흥원(NIA)"),
    ("STEPI.py", "과학기술정책연구원(STEPI)"),
    ("NIPA.py", "정보통신산업진흥원(NIPA)"),
    ("KISDI.py", "정보통신정책연구원(KISDI)"),
    ("dapa.py", "방위사업청"),
    ("KISTI.py", "한국과학기술정보연구원(KISTI)"),
    ("iitp.py", "정보통신기획평가원(IITP)"),
    ("AInews.py", "인공지능신문"),
    ("kookbang.py", "국방일보"),
    ("msit.py", "과학기술정보통신부"),
    ("KISA.py", "한국인터넷진흥원(KISA)"),
    ("tta.py", "한국정보통신기술협회(TTA)"),
    ("aikorea.py", "한국인공지능협회"),
]

TIMEOUT_PER_SCRIPT = 300  # 스크립트당 최대 5분 타임아웃
# =============================================


def get_current_kst():
    """현재 한국 시간(KST) 반환"""
    try:
        return datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        return datetime.now()


def check_scraper_api_credits(api_key):
    """
    ScraperAPI 계정의 잔여 크레딧 및 상태를 조회합니다.
    (Account 조회 API는 크레딧이 전혀 차감되지 않는 무료 API입니다 - 0 credit consumption)
    성공 시 잔여 크레딧(int), 실패 시 -1 반환
    """
    if not api_key:
        return -1
    try:
        url = f"https://api.scraperapi.com/account?api_key={api_key.strip()}"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            return data.get("creditsLeft", 0)
        return -1
    except Exception:
        return -1


def resolve_best_scraper_api_key():
    """
    현재 설정된 키와 후보 키(1번, 2번, 3번, 여분 키)의 잔여 크레딧을 점검하여,
    크레딧이 남아있는 최적의 키를 반환합니다.
    크레딧이 0이거나 오류인 경우 자동으로 살아있는 키로 Fallback합니다.
    """
    current_key = os.environ.get("SCRAPER_API_KEY", "")
    current_name = os.environ.get("SCRAPER_KEY_NAME", "배정된 키")

    # .env 파일 직접 파싱 (환경 변수 덮어쓰기 방지)
    env_vals = {}
    try:
        from dotenv import dotenv_values
        env_vals = dotenv_values()
    except Exception:
        pass

    # 후보 키 수집 (GitHub Actions secrets 또는 .env 파일)
    candidates = [
        ("1번 키", os.environ.get("KEY_1") or env_vals.get("SCRAPER_API_KEY") or os.environ.get("SCRAPER_API_KEY_1")),
        ("2번 키", os.environ.get("KEY_2") or env_vals.get("SCRAPER_API_KEY_2") or os.environ.get("SCRAPER_API_KEY_2")),
        ("3번 키", os.environ.get("KEY_3") or env_vals.get("SCRAPER_API_KEY_3") or os.environ.get("SCRAPER_API_KEY_3")),
        ("여분 키", env_vals.get("SCRAPER_API_KEY_Spare") or os.environ.get("SCRAPER_API_KEY_Spare")),
    ]

    valid_candidates = []
    seen = set()
    for name, k in candidates:
        if k and k.strip() and k.strip() not in seen:
            seen.add(k.strip())
            valid_candidates.append((name, k.strip()))

    if not valid_candidates:
        return current_key, current_name

    # 현재 키의 매핑 명칭 보정
    for name, k in valid_candidates:
        if k == current_key:
            current_name = name
            break

    # 1. 현재 배정된 키의 잔여 크레딧 체크
    current_credits = check_scraper_api_credits(current_key) if current_key else -1
    if current_credits > 0:
        return current_key, f"{current_name} (잔여: {current_credits:,}개)"

    print(f"\n⚠️ [ScraperAPI 감지] {current_name}의 잔여 크레딧이 0개이거나 조회 불가(상태: {current_credits}).")
    print("🔍 사용 가능한 대체 ScraperAPI 키 크레딧 점검 중 (계정 조회는 크레딧을 소모하지 않습니다)...")

    # 2. 후보 키들 중 크레딧이 가장 많이 남은 키 탐색
    best_key = None
    best_name = None
    max_credits = -1

    for name, k in valid_candidates:
        credits = check_scraper_api_credits(k)
        if credits >= 0:
            print(f" - {name}: {credits:,}개 잔여")
        else:
            print(f" - {name}: 조회 실패/비활성")

        if credits > max_credits:
            max_credits = credits
            best_key = k
            best_name = name

    if best_key and max_credits > 0:
        print(f"🔄 [스마트 폴백 적용] 잔여 크레딧이 가장 많은 '{best_name}'(잔여: {max_credits:,}개)로 자동 전환합니다!")
        os.environ["SCRAPER_API_KEY"] = best_key
        return best_key, f"{best_name} (자동 폴백, 잔여: {max_credits:,}개)"

    print("⚠️ 모든 Scraper API 키의 크레딧이 소진되었거나 조회할 수 없습니다. 기존 키로 계속 진행합니다.")
    return current_key, f"{current_name} (크레딧 부족 주의)"


def run_single_crawler(script_name, display_name):
    """
    개별 크롤러 스크립트를 실행하고 결과를 집계합니다.
    오류가 발생해도 다음 스크립트 실행에 영향을 주지 않도록 격리합니다.
    """
    script_path = os.path.join("codes", "pycode", script_name)
    if not os.path.exists(script_path):
        return {
            "name": display_name,
            "script": script_name,
            "status": "FAILED",
            "elapsed": 0,
            "new_count": 0,
            "total_count": 0,
            "error_summary": f"파일을 찾을 수 없음: {script_path}",
            "logs": ""
        }

    print(f"\n[{display_name} ({script_name})] 크롤링 시작...")
    start_time = time.time()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if "SCRAPER_API_KEY" in os.environ:
        env["SCRAPER_API_KEY"] = os.environ["SCRAPER_API_KEY"]

    output_lines = []
    return_code = 0
    error_summary = ""

    try:
        proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            encoding="utf-8",
            errors="replace"
        )

        try:
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                output_lines.append(line)
            proc.wait(timeout=TIMEOUT_PER_SCRIPT)
            return_code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            return_code = -1
            error_summary = f"타임아웃 초과 ({TIMEOUT_PER_SCRIPT}초)"
            print(f"❌ {display_name} 실행 중 타임아웃 발생 (강제 종료)")

    except Exception as e:
        return_code = 1
        error_summary = f"프로세스 실행 예외: {str(e)}"
        print(f"❌ {display_name} 실행 예외: {e}")

    elapsed_time = round(time.time() - start_time, 2)
    full_output = "".join(output_lines)

    # 신규 건수 및 전체 건수 정규식 파싱
    # 예: 신규 15건 수집 | 기존 100건 병합 | 최종 115건 저장
    new_count = 0
    total_count = 0

    new_match = re.search(r'신규\s*(\d+)\s*건', full_output)
    if new_match:
        new_count = int(new_match.group(1))

    total_match = re.search(r'최종\s*(\d+)\s*건', full_output)
    if total_match:
        total_count = int(total_match.group(1))

    # 치명적 오류 감지 (403 Forbidden, Timeout, 전체 프로세스 에러 등)
    critical_error_keywords = [
        "403 Client Error",
        "Forbidden for url",
        "Read timed out",
        "Connection timed out",
        "전체 프로세스 에러",
        "크롤링 중 오류",
        "웹페이지 요청 중 오류 발생",
        "웹페이지 우회 요청 중 오류 발생",
        "Traceback (most recent call last):",
        "HTTPConnectionPool",
    ]
    detected_errors = []
    for line in output_lines:
        if any(kw in line for kw in critical_error_keywords):
            detected_errors.append(line.strip())

    # [핵심] 종료 코드가 0이더라도, 치명적 오류가 출력되고 신규 수집이 0건이면 명백한 실패로 판정!
    if return_code != 0:
        is_success = False
    elif detected_errors and new_count == 0:
        is_success = False
        if not error_summary:
            error_summary = " | ".join(detected_errors[-2:])
    else:
        is_success = True

    # 비정상 종료 시 에러 요약 추출 보완
    if not is_success and not error_summary:
        error_candidates = []
        for line in output_lines:
            if any(kw in line for kw in ["Error", "Exception", "Traceback", "Failed", "실패", "오류"]):
                error_candidates.append(line.strip())

        if error_candidates:
            error_summary = " | ".join(error_candidates[-3:])
        elif output_lines:
            error_summary = " | ".join([l.strip() for l in output_lines[-3:] if l.strip()])
        else:
            error_summary = f"비정상 종료 (종료 코드: {return_code})"

    if is_success:
        print(f"✅ [{display_name}] 성공 (신규: {new_count}건, 소요: {elapsed_time}초)")
    else:
        print(f"❌ [{display_name}] 실패 (코드: {return_code}, 원인: {error_summary})")

    return {
        "name": display_name,
        "script": script_name,
        "status": "SUCCESS" if is_success else "FAILED",
        "elapsed": elapsed_time,
        "new_count": new_count,
        "total_count": total_count,
        "error_summary": error_summary,
        "logs": full_output[-2000:] if len(full_output) > 2000 else full_output
    }


def generate_email_html(results, total_elapsed, scraper_key_name, kst_now_str):
    """경고 알림용 프리미엄 HTML 이메일 본문 생성"""
    failed_items = [r for r in results if r["status"] == "FAILED"]
    success_items = [r for r in results if r["status"] == "SUCCESS"]
    total_new = sum(r["new_count"] for r in results)

    failed_count = len(failed_items)
    success_count = len(success_items)
    total_count = len(results)

    # 실패한 항목 상세 블록
    failed_details_html = ""
    if failed_items:
        failed_cards = ""
        for item in failed_items:
            # 에러 요약 및 로그 발췌
            escaped_error = item["error_summary"].replace("<", "&lt;").replace(">", "&gt;")
            failed_cards += f"""
            <div style="background-color: #fff1f0; border-left: 4px solid #ff4d4f; border-radius: 6px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #cf1322; font-size: 15px;">❌ {item['name']} <span style="font-size: 12px; color: #8c8c8c; font-weight: normal;">({item['script']})</span></strong>
                    <span style="font-size: 12px; color: #8c8c8c;">소요 시간: {item['elapsed']}초</span>
                </div>
                <div style="background-color: #ffffff; border: 1px solid #ffccc7; border-radius: 4px; padding: 8px 12px; font-family: Consolas, monospace; font-size: 13px; color: #a8071a; word-break: break-all;">
                    {escaped_error}
                </div>
            </div>
            """

        failed_details_html = f"""
        <div style="margin-top: 24px;">
            <h3 style="color: #cf1322; font-size: 16px; margin-bottom: 12px; display: flex; align-items: center;">
                🚨 오류 발생 소스 상세 내역 ({failed_count}개)
            </h3>
            {failed_cards}
        </div>
        """

    # 전체 소스 실행 현황 테이블 행 생성
    table_rows = ""
    for r in results:
        is_ok = (r["status"] == "SUCCESS")
        status_badge = '<span style="background-color: #e6f7ff; color: #1890ff; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">✅ 성공</span>' if is_ok else '<span style="background-color: #fff1f0; color: #ff4d4f; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">❌ 실패</span>'
        new_text = f"<b>+{r['new_count']}건</b>" if r['new_count'] > 0 else f"{r['new_count']}건"
        note_text = f"{r['elapsed']}초" if is_ok else f'<span style="color: #cf1322;">오류 발생</span>'

        table_rows += f"""
        <tr style="border-bottom: 1px solid #f0f0f0;">
            <td style="padding: 10px 12px; font-weight: 500; color: #262626;">{r['name']}</td>
            <td style="padding: 10px 12px; text-align: center;">{status_badge}</td>
            <td style="padding: 10px 12px; text-align: center; color: #52c41a;">{new_text}</td>
            <td style="padding: 10px 12px; text-align: center; color: #8c8c8c; font-size: 13px;">{note_text}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f5f5; color: #333333;">
        <div style="max-width: 680px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.06);">
            
            <!-- 헤더 배너 -->
            <div style="background: linear-gradient(135deg, #cf1322 0%, #fa541c 100%); padding: 24px 28px; color: #ffffff;">
                <h1 style="margin: 0 0 8px 0; font-size: 20px; font-weight: 700; letter-spacing: -0.5px;">
                    ⚠️ AI 트렌드 크롤링 오류 경고 리포트
                </h1>
                <p style="margin: 0; font-size: 14px; opacity: 0.9;">
                    일부 사이트 수집 중 오류가 발생했습니다. (정상 수집된 데이터는 안전하게 보존 및 반영되었습니다)
                </p>
            </div>

            <div style="padding: 24px 28px;">
                <!-- 핵심 요약 메타 카드 -->
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; background-color: #fafafa; border: 1px solid #f0f0f0; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <div>
                        <span style="font-size: 12px; color: #8c8c8c; display: block;">📅 실행 일시 (KST)</span>
                        <strong style="font-size: 14px; color: #262626;">{kst_now_str}</strong>
                    </div>
                    <div>
                        <span style="font-size: 12px; color: #8c8c8c; display: block;">🔑 사용된 Scraper API 키</span>
                        <strong style="font-size: 14px; color: #1890ff;">{scraper_key_name}</strong>
                    </div>
                    <div>
                        <span style="font-size: 12px; color: #8c8c8c; display: block;">📊 수집 결과 요약</span>
                        <strong style="font-size: 14px; color: #262626;">성공 {success_count} / <span style="color: #cf1322;">실패 {failed_count}</span> (총 {total_count}개)</strong>
                    </div>
                    <div>
                        <span style="font-size: 12px; color: #8c8c8c; display: block;">⏱️ 총 소요 시간 / 신규 기사</span>
                        <strong style="font-size: 14px; color: #52c41a;">+{total_new}건 수집 <span style="font-size: 12px; color: #8c8c8c; font-weight: normal;">({total_elapsed}초)</span></strong>
                    </div>
                </div>

                <!-- 실패 상세 내역 -->
                {failed_details_html}

                <!-- 전체 소스 실행 현황 테이블 -->
                <div style="margin-top: 24px;">
                    <h3 style="color: #262626; font-size: 15px; margin-bottom: 12px;">
                        📋 전체 소스별 수집 상태 현황
                    </h3>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background-color: #fafafa; border-bottom: 2px solid #f0f0f0; color: #8c8c8c; font-size: 12px;">
                                <th style="padding: 10px 12px; text-align: left;">소스명</th>
                                <th style="padding: 10px 12px; text-align: center; width: 80px;">상태</th>
                                <th style="padding: 10px 12px; text-align: center; width: 90px;">신규 수집</th>
                                <th style="padding: 10px 12px; text-align: center; width: 90px;">소요 시간</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>

                <!-- 안내 푸터 -->
                <div style="margin-top: 30px; padding-top: 16px; border-top: 1px solid #f0f0f0; font-size: 12px; color: #8c8c8c; text-align: center; line-height: 1.6;">
                    본 메일은 GitHub Actions <code>Run Python Scripts Daily</code> 워크플로우에서 크롤링 오류 감지 시 자동으로 발송되는 관리자 전용 알림입니다.<br>
                    수신자: {ADMIN_RECEIVER} | 발신자: {SENDER_EMAIL}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_alert_email(subject, html_body):
    """Gmail SMTP를 통해 경고 메일 발송"""
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password:
        print("\n⚠️ 경고: 'GMAIL_APP_PASSWORD' 환경변수가 설정되지 않아 이메일을 발송할 수 없습니다.")
        return False

    print(f"\n📧 관리자({ADMIN_RECEIVER})에게 경고 이메일 발송 중...")

    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = ADMIN_RECEIVER
    msg["Subject"] = subject

    # 평문 대체 텍스트
    plain_text = "AI 트렌드 크롤링 워크플로우에서 일부 오류가 발생했습니다. HTML 지원 메일 클라이언트에서 확인해 주세요."
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    server = None
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, app_password)
        server.send_message(msg)
        print("✅ 경고 이메일이 성공적으로 발송되었습니다!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ 이메일 발송 실패: SMTP 인증 오류 (Gmail 앱 비밀번호를 확인하세요)")
        return False
    except Exception as e:
        print(f"❌ 이메일 발송 중 오류 발생: {e}")
        return False
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="크롤러 통합 스마트 러너 및 에러 알림 시스템")
    parser.add_argument("--force-mail", action="store_true", help="오류 여부와 무관하게 항상 리포트 메일 발송")
    parser.add_argument("--test-mail", action="store_true", help="테스트용 가상 실패 데이터를 생성하여 메일 발송 테스트")
    args = parser.parse_args()

    kst_now = get_current_kst()
    kst_now_str = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    # ScraperAPI 키 사전 점검 및 스마트 폴백 수행
    _, scraper_key_name = resolve_best_scraper_api_key()

    print("=" * 60)
    print(f"🚀 AI Trend 크롤링 통합 스마트 러너 시작")
    print(f"🕒 실행 시각(KST): {kst_now_str}")
    print(f"🔑 적용된 Scraper API 키: {scraper_key_name}")
    print(f"📋 총 대상 크롤러 수: {len(CRAWLER_SCRIPTS)}개")
    print("=" * 60)

    # 테스트 메일 모드
    if args.test_mail:
        print("\n🧪 [--test-mail] 모드 실행: 가상의 테스트 데이터를 생성하여 메일 발송을 테스트합니다.")
        dummy_results = [
            {"name": "전자신문", "script": "etnews.py", "status": "SUCCESS", "elapsed": 4.5, "new_count": 12, "total_count": 2380, "error_summary": "", "logs": ""},
            {"name": "국방부", "script": "mnd.py", "status": "FAILED", "elapsed": 30.2, "new_count": 0, "total_count": 711, "error_summary": "ScraperAPI 500: Internal Server Error (서버 응답 오류)", "logs": ""},
            {"name": "AI타임스", "script": "aitimes.py", "status": "SUCCESS", "elapsed": 5.1, "new_count": 8, "total_count": 1060, "error_summary": "", "logs": ""},
            {"name": "방위사업청", "script": "dapa.py", "status": "FAILED", "elapsed": 12.0, "new_count": 0, "total_count": 45, "error_summary": "ConnectionTimeout: HTTPSConnectionPool timed out", "logs": ""},
        ]
        html_body = generate_email_html(dummy_results, 51.8, scraper_key_name, kst_now_str)
        subject = f"[AI 트렌드 크롤링 경고 (테스트)] ⚠️ 2개 소스 수집 실패 (국방부, 방위사업청)"
        send_alert_email(subject, html_body)
        return

    total_start = time.time()
    results = []

    # 16개 크롤러 순차 실행 (오류 격리)
    for script_name, display_name in CRAWLER_SCRIPTS:
        res = run_single_crawler(script_name, display_name)
        results.append(res)

    total_elapsed = round(time.time() - total_start, 2)
    failed_items = [r for r in results if r["status"] == "FAILED"]
    success_items = [r for r in results if r["status"] == "SUCCESS"]
    total_new = sum(r["new_count"] for r in results)

    print("\n" + "=" * 60)
    print("📊 [크롤링 전체 결과 요약]")
    print(f" - 총 소요 시간: {total_elapsed}초")
    print(f" - 성공: {len(success_items)}개 / 실패: {len(failed_items)}개 (총 {len(results)}개)")
    print(f" - 신규 수집된 총 기사 수: {total_new}건")
    if failed_items:
        print(f" - ❌ 실패 목록: {', '.join(f['name'] for f in failed_items)}")
    else:
        print(" - ✅ 16개 소스 모두 정상 수집 완료!")
    print("=" * 60)

    # 옵션 B 로직: 실패가 발생했거나, --force-mail 인자가 있는 경우에만 메일 발송
    should_send_mail = (len(failed_items) > 0) or args.force_mail

    if should_send_mail:
        if len(failed_items) > 0:
            failed_names_str = ", ".join(f["name"] for f in failed_items[:3])
            if len(failed_items) > 3:
                failed_names_str += f" 외 {len(failed_items)-3}곳"
            subject = f"[AI 트렌드 크롤링 경고] ⚠️ {len(failed_items)}개 소스 수집 실패 ({failed_names_str})"
        else:
            subject = f"[AI 트렌드 크롤링 보고] ✅ {len(results)}개 소스 전체 정상 수집 완료 (+{total_new}건)"

        html_body = generate_email_html(results, total_elapsed, scraper_key_name, kst_now_str)
        send_alert_email(subject, html_body)
    else:
        print("\n✨ [옵션 B 적용] 모든 크롤러가 정상 완료되어 경고 이메일을 발송하지 않습니다. (정상 상태 유지)")


if __name__ == "__main__":
    main()
