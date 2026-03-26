"""
receiver_email.json에서 등록일로부터 1년(365일)이 지난 이메일을 자동 삭제하는 스크립트.
GitHub Actions(kakao_or_gmail_send.yml)에서 메일 발송 전에 실행됩니다.
"""
import json
import os
from datetime import datetime

# 파일 경로 설정
RECEIVER_FILE = "codes/receiver_email.json"

def cleanup_expired_emails():
    if not os.path.exists(RECEIVER_FILE):
        print("receiver_email.json 파일이 없습니다.")
        return

    try:
        with open(RECEIVER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("receiver_email.json 파싱 오류.")
        return

    # 구조 파싱 (리스트 또는 객체)
    email_list = data if isinstance(data, list) else data.get("emails", [])
    today = datetime.now()

    valid_emails = []
    removed_count = 0

    for item in email_list:
        # 문자열인 경우 객체로 변환
        if isinstance(item, str):
            item = {"email": item, "date": today.strftime("%Y-%m-%d")}

        email_addr = item.get("email", "")
        reg_date_str = item.get("date", "")

        if not email_addr:
            removed_count += 1
            continue

        # 날짜 체크
        if reg_date_str:
            try:
                reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
                diff_days = (today - reg_date).days
                if diff_days >= 365:
                    print(f"  ❌ 만료 삭제: {email_addr} (등록일: {reg_date_str}, {diff_days}일 경과)")
                    removed_count += 1
                    continue
            except ValueError:
                pass  # 날짜 형식 오류 시 유지

        valid_emails.append(item)

    # 변경사항이 있으면 파일 저장
    if removed_count > 0:
        with open(RECEIVER_FILE, "w", encoding="utf-8") as f:
            json.dump({"emails": valid_emails}, f, ensure_ascii=False, indent=2)
        print(f"✅ 만료 이메일 {removed_count}건 삭제 완료. 현재 {len(valid_emails)}명 유지.")
    else:
        print(f"✅ 만료된 이메일 없음. 현재 {len(email_list)}명 유지.")

if __name__ == "__main__":
    cleanup_expired_emails()
