"""
구독자 목록(codes/receiver_email.json) 읽기/쓰기 공용 모듈.

저장소가 공개되어 있으므로 목록은 암호화해서 저장합니다.
암호화 형식은 api/subscribe.js 와 반드시 같아야 합니다.
  {"v": 1, "enc": "aes-256-gcm", "iv": "<base64 12바이트>", "data": "<base64 암호문+인증태그 16바이트>"}
  키 = SHA-256(SUBSCRIBER_ENCRYPTION_KEY 앞뒤 공백 제거)
  복호화한 내용 = {"emails": [{"email": "...", "date": "YYYY-MM-DD"}, ...]}

SUBSCRIBER_ENCRYPTION_KEY 가 설정되지 않은 동안에는 기존 평문 형식으로 읽고 씁니다.
키가 설정되면 다음 저장 때(매일 cleanup_expired_emails.py 실행 시) 자동으로 암호화됩니다.
"""
import base64
import hashlib
import json
import os
import re
from datetime import datetime

RECEIVER_FILE = "codes/receiver_email.json"
KEY_ENV = "SUBSCRIBER_ENCRYPTION_KEY"
MIN_KEY_LENGTH = 32
ENC_ALG = "aes-256-gcm"
IV_BYTES = 12
EXPIRE_DAYS = 365
# api/subscribe.js 와 같은 규칙
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class SubscriberFileError(Exception):
    """구독자 파일을 안전하게 읽거나 쓸 수 없을 때 (키 없음/불일치 등)."""


def _get_key():
    passphrase = os.environ.get(KEY_ENV, "").strip()
    if not passphrase:
        return None
    if len(passphrase) < MIN_KEY_LENGTH:
        raise SubscriberFileError(f"{KEY_ENV}는 {MIN_KEY_LENGTH}자 이상이어야 합니다.")
    return hashlib.sha256(passphrase.encode("utf-8")).digest()


def encryption_enabled():
    return _get_key() is not None


def _encrypt(plaintext, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    iv = os.urandom(IV_BYTES)
    data = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)  # 암호문 + 인증태그
    return {
        "v": 1,
        "enc": ENC_ALG,
        "iv": base64.b64encode(iv).decode("ascii"),
        "data": base64.b64encode(data).decode("ascii"),
    }


def _decrypt(doc, key):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        iv = base64.b64decode(doc["iv"])
        data = base64.b64decode(doc["data"])
        return AESGCM(key).decrypt(iv, data, None).decode("utf-8")
    except (InvalidTag, KeyError, ValueError) as e:
        raise SubscriberFileError(
            f"구독자 목록을 복호화하지 못했습니다. Vercel과 GitHub Secrets의 {KEY_ENV} 값이 같은지 확인하세요."
        ) from e


def load_subscribers(path=RECEIVER_FILE):
    """
    구독자 목록을 정리 전 상태 그대로 반환합니다.
    반환: (원본 항목 리스트, 파일이 암호화되어 있었는지 여부)
    """
    if not os.path.exists(path):
        return [], False

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if not text.strip():
        return [], False
    doc = json.loads(text)

    encrypted = isinstance(doc, dict) and doc.get("enc") == ENC_ALG
    if encrypted:
        key = _get_key()
        if key is None:
            raise SubscriberFileError(f"암호화된 구독자 목록을 읽으려면 {KEY_ENV}가 필요합니다.")
        doc = json.loads(_decrypt(doc, key))

    raw = doc if isinstance(doc, list) else doc.get("emails", [])
    return raw, encrypted


def save_subscribers(subscribers, path=RECEIVER_FILE):
    """구독자 목록을 저장합니다. 키가 있으면 암호화, 없으면 기존 평문 형식."""
    payload = {"emails": subscribers}
    key = _get_key()
    doc = _encrypt(json.dumps(payload, ensure_ascii=False), key) if key else payload

    # 저장 도중 실패해도 기존 파일이 깨지지 않도록 임시 파일에 쓴 뒤 교체
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, path)


def clean_subscribers(raw, today=None):
    """
    옛 형식(문자열) 변환, 잘못된 주소·만료(등록 후 365일)된 구독 제거.
    반환: (유효한 구독자 리스트, 제거된 건수)
    """
    today = today or datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    valid = []
    removed = 0

    for item in raw:
        entry = {"email": item, "date": today_str} if isinstance(item, str) else item
        if not isinstance(entry, dict) or not isinstance(entry.get("email"), str):
            removed += 1
            continue

        email = "".join(c for c in entry["email"] if ord(c) >= 32 and ord(c) != 127).strip()
        if not EMAIL_REGEX.match(email):
            removed += 1
            continue

        date_str = entry.get("date") or today_str
        try:
            if (today - datetime.strptime(date_str, "%Y-%m-%d")).days >= EXPIRE_DAYS:
                removed += 1
                continue
        except ValueError:
            pass  # 날짜 형식이 잘못된 경우 일단 유지

        valid.append({"email": email, "date": date_str})

    return valid, removed


def mask_email(email):
    """공개 저장소의 Actions 로그에 주소가 남지 않도록 가립니다. 예: ab***@gmail.com"""
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"
