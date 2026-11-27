"""
일일 파이프라인(크롤링 → AI 자동 선정 → 오디오 → 메일) 상태 요약과 관리자 알림.

평소에는 메일 발송이 끝난 뒤 관리자에게 하루 한 통 요약을 보내고,
어느 단계든 실패하면 그 자리에서 경고를 보냅니다. (워크플로우에서 호출)

  python codes/pycode/pipeline_report.py --summary
  python codes/pycode/pipeline_report.py --failed "AI 자동 선정" --run-url <Actions 실행 주소>

사이트 구조 변경 의심 감지(detect_suspicious)도 여기 있습니다. (run_crawlers.py 에서도 사용)
"""
import argparse
import html
import json
import os
import sys

from notify import send_admin_mail
from pipeline_state import read_state, report_date, today_key
from sources import daily_news_scripts

# 매일 새 기사가 올라오는 뉴스 소스: 며칠 연속 새 기사가 0건이면 의심 (config/sources.json 의 daily_news)
DAILY_NEWS_SCRIPTS = daily_news_scripts()
EMPTY_FETCH_DAYS = 2   # 사이트에서 한 건도 못 가져온 날이 이만큼 이어지면 경고 (구조 변경/차단 의심)
NO_NEW_DAYS = 4        # 뉴스 소스의 새 기사 0건이 이만큼 이어지면 경고 (주말+공휴일 고려)

FAVORITES_DIR = os.path.join("codes", "favorites")
ACTIONS_URL = "https://github.com/jhjhc1483/AI_Trend_Analysis_vercel/actions"


# ---------------- 사이트 구조 변경 의심 감지 ----------------

def _trailing_days(history, condition):
    count = 0
    for entry in reversed(history):
        if not condition(entry):
            break
        count += 1
    return count


def detect_suspicious(crawl_status):
    """crawl_status.json 의 소스별 최근 기록을 보고 의심스러운 소스 목록을 반환합니다."""
    warnings = []
    for script, history in (crawl_status.get("history") or {}).items():
        if not history:
            continue
        name = history[-1].get("name", script)
        empty = _trailing_days(history, lambda h: h.get("fetched", 0) == 0)
        if empty >= EMPTY_FETCH_DAYS:
            warnings.append({"script": script, "name": name,
                             "reason": f"{empty}일 연속 사이트에서 한 건도 가져오지 못함 (페이지 구조 변경 또는 차단 의심)"})
            continue
        if script in DAILY_NEWS_SCRIPTS:
            no_new = _trailing_days(history, lambda h: h.get("new", 0) == 0)
            if no_new >= NO_NEW_DAYS:
                warnings.append({"script": script, "name": name,
                                 "reason": f"{no_new}일 연속 새 기사 0건 (같은 페이지만 반복 수집 중인지 확인 필요)"})
    return warnings


# ---------------- 단계별 상태 ----------------

def _favorites_count(filename):
    try:
        with open(os.path.join(FAVORITES_DIR, filename), "r", encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return 0


def collect_status():
    today = today_key()
    crawl = read_state("crawl_status")
    results = crawl.get("results", {}) if crawl.get("date") == today else {}
    ok = sum(1 for r in results.values() if r.get("status") == "SUCCESS")
    new = sum(r.get("new_count", 0) for r in results.values())

    stages = []
    if results:
        stages.append(("크롤링", ok == len(results), f"{len(results)}개 중 {ok}개 성공, 새 기사 {new}건"))
    else:
        stages.append(("크롤링", None, "오늘 실행 기록 없음"))

    if report_date() == today:
        stages.append(("AI 자동 선정", True,
                       f"기사 {_favorites_count('favorite_articles.json')}건 · 간행물 {_favorites_count('favorite_publications.json')}건"))
    else:
        stages.append(("AI 자동 선정", False, f"오늘 일일 동향이 없음 (현재: {report_date() or '없음'})"))

    audio = read_state("audio")
    stages.append(("오디오", audio.get("date") == today,
                   f"생성 {audio.get('generated_at', '')[11:16]}" if audio.get("date") == today else "오늘 생성 기록 없음"))

    mail = read_state("mail")
    if mail.get("date") == today:
        detail = f"{mail.get('sent', 0)}명 발송" + (f", {mail['failed']}명 실패" if mail.get("failed") else "")
        stages.append(("구독자 메일", not mail.get("failed"), detail))
    else:
        stages.append(("구독자 메일", None, "아직 발송 안 함"))

    return {
        "date": today,
        "stages": stages,
        "crawl_results": results,
        "warnings": detect_suspicious(crawl),
    }


def _icon(ok):
    return "✅" if ok is True else "❌" if ok is False else "⏳"


def render_text(status):
    lines = [f"{_icon(ok)} {name}: {detail}" for name, ok, detail in status["stages"]]
    for w in status["warnings"]:
        lines.append(f"⚠️ {w['name']}: {w['reason']}")
    return "\n".join(lines)


def render_html(status, title, intro, color="#096dd9", extra_html=""):
    esc = html.escape
    stage_rows = "".join(
        f'<tr><td style="padding:8px 10px;">{_icon(ok)} {esc(name)}</td>'
        f'<td style="padding:8px 10px;color:#555;">{esc(detail)}</td></tr>'
        for name, ok, detail in status["stages"])
    warning_html = ""
    if status["warnings"]:
        items = "".join(f"<li><b>{esc(w['name'])}</b>: {esc(w['reason'])}</li>" for w in status["warnings"])
        warning_html = (f'<div style="background:#fff7e6;border-left:4px solid #fa8c16;padding:10px 14px;margin-top:16px;">'
                        f'<b>⚠️ 확인이 필요한 소스</b><ul style="margin:6px 0 0 18px;padding:0;">{items}</ul></div>')
    crawl_rows = "".join(
        f'<tr><td style="padding:4px 10px;">{esc(r.get("name", s))}</td>'
        f'<td style="padding:4px 10px;text-align:center;">{"✅" if r.get("status") == "SUCCESS" else "❌"}</td>'
        f'<td style="padding:4px 10px;text-align:right;">+{r.get("new_count", 0)}</td></tr>'
        for s, r in status["crawl_results"].items())
    crawl_html = ""
    if crawl_rows:
        crawl_html = ('<h4 style="margin:20px 0 6px;">소스별 수집</h4>'
                      '<table style="border-collapse:collapse;font-size:13px;width:100%;">'
                      '<tr style="color:#888;"><th style="text-align:left;padding:4px 10px;">소스</th>'
                      '<th style="padding:4px 10px;">상태</th><th style="text-align:right;padding:4px 10px;">새 기사</th></tr>'
                      f'{crawl_rows}</table>')
    return f"""<html><body style="font-family:-apple-system,'Malgun Gothic',sans-serif;color:#333;">
<div style="max-width:640px;margin:0 auto;border:1px solid #eee;border-radius:10px;overflow:hidden;">
  <div style="background:{color};color:#fff;padding:16px 20px;"><b style="font-size:17px;">{esc(title)}</b>
    <div style="font-size:13px;opacity:.9;margin-top:4px;">{esc(intro)}</div></div>
  <div style="padding:16px 20px;">
    <table style="border-collapse:collapse;font-size:14px;width:100%;">{stage_rows}</table>
    {extra_html}{warning_html}{crawl_html}
    <p style="font-size:12px;color:#999;margin-top:20px;">실행 기록: <a href="{ACTIONS_URL}">{ACTIONS_URL}</a></p>
  </div>
</div></body></html>"""


# ---------------- 알림 ----------------

def send_summary():
    status = collect_status()
    crawl = status["crawl_results"]
    ok = sum(1 for r in crawl.values() if r.get("status") == "SUCCESS")
    new = sum(r.get("new_count", 0) for r in crawl.values())
    mail = read_state("mail")
    has_issue = status["warnings"] or any(stage_ok is False for _, stage_ok, _ in status["stages"])
    subject = (f"{'⚠️' if has_issue else '📊'} [AI 동향] {status['date']} 일일 파이프라인 완료 "
               f"(크롤링 {ok}/{len(crawl)}, 새 기사 {new}건, 메일 {mail.get('sent', 0)}명)")
    body = render_html(status, "일일 파이프라인 완료", "오늘 브리핑 메일 발송까지 끝났습니다.",
                       color="#d48806" if has_issue else "#096dd9")
    return send_admin_mail(subject, body, render_text(status))


def send_failure(step, run_url=None):
    status = collect_status()
    link = f'<p style="margin-top:14px;">👉 <a href="{html.escape(run_url)}">실패한 실행 기록 보기</a></p>' if run_url else ""
    body = render_html(status, f"{step} 단계 실패", "아래 상태를 확인하고, 원인을 해결한 뒤 대시보드나 Actions에서 다시 실행하세요.",
                       color="#cf1322", extra_html=link)
    text = f"{step} 단계가 실패했습니다.\n{run_url or ACTIONS_URL}\n\n{render_text(status)}"
    return send_admin_mail(f"🚨 [AI 동향] {status['date']} {step} 단계 실패", body, text)


def main():
    parser = argparse.ArgumentParser(description="일일 파이프라인 상태 요약/실패 알림")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", action="store_true", help="관리자에게 오늘 요약 메일 발송")
    group.add_argument("--failed", metavar="STEP", help="해당 단계 실패 알림 발송")
    parser.add_argument("--run-url", help="실패한 Actions 실행 주소")
    parser.add_argument("--print", action="store_true", help="메일 대신 상태만 출력")
    args = parser.parse_args()

    if args.print:
        print(render_text(collect_status()))
        return 0
    sent = send_summary() if args.summary else send_failure(args.failed, args.run_url)
    return 0 if sent else 1


if __name__ == "__main__":
    sys.exit(main())
