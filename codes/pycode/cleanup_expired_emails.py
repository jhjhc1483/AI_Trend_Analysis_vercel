"""
receiver_email.json에서 등록일로부터 1년(365일)이 지난 이메일을 자동 삭제하는 스크립트.
GitHub Actions(kakao_or_gmail_send.yml)에서 메일 발송 전에 실행됩니다.

SUBSCRIBER_ENCRYPTION_KEY가 설정되어 있고 파일이 아직 평문이면, 이때 암호화된 형식으로 바꿔 저장합니다.
키가 없거나 맞지 않으면 파일을 건드리지 않고 실패(exit 1)하여 워크플로우 실패 알림이 가도록 합니다.
"""
import sys

from subscribers import (
    SubscriberFileError,
    clean_subscribers,
    encryption_enabled,
    load_subscribers,
    mask_email,
    save_subscribers,
)


def cleanup_expired_emails():
    raw, was_encrypted = load_subscribers()
    if not raw and not was_encrypted:
        print("구독자 목록이 비어 있거나 파일이 없습니다.")
        return

    valid, removed = clean_subscribers(raw)
    removed_emails = {item if isinstance(item, str) else item.get("email") for item in raw} - {v["email"] for v in valid}
    for email in removed_emails:
        if isinstance(email, str):
            print(f"  ❌ 만료/형식 오류 삭제: {mask_email(email)}")

    needs_encryption = encryption_enabled() and not was_encrypted
    if removed or needs_encryption:
        save_subscribers(valid)
        if needs_encryption:
            print("🔒 구독자 목록을 암호화된 형식으로 변환했습니다.")
        print(f"✅ 정리 완료: {removed}건 삭제, 현재 {len(valid)}명 유지.")
    else:
        print(f"✅ 만료된 이메일 없음. 현재 {len(valid)}명 유지.")

    if not encryption_enabled():
        print("⚠️ SUBSCRIBER_ENCRYPTION_KEY가 설정되지 않아 구독자 목록이 평문으로 저장되어 있습니다.")


if __name__ == "__main__":
    try:
        cleanup_expired_emails()
    except SubscriberFileError as e:
        print(f"❌ {e}")
        sys.exit(1)
