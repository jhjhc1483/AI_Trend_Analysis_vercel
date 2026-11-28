"""
구독자 목록 암호화·해지 링크 토큰이 파이썬(메일 발송)과 서버 API(api/subscribe.js)에서 같은지 확인.
둘이 어긋나면 메일 속 해지 링크가 '링크가 올바르지 않습니다'가 되거나, 구독 신청이 목록을 깨뜨립니다.
"""
import json
import shutil
import subprocess
from datetime import datetime

import pytest

from conftest import ROOT

pytest.importorskip("cryptography")
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node 가 없음")

KEY = "test-key-for-ci-only-0123456789abcdef"


def run_node(script, env):
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        cwd=ROOT, env={"PATH": "/usr/bin:/bin:/usr/local/bin", **env},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def subscribers(monkeypatch):
    monkeypatch.setenv("SUBSCRIBER_ENCRYPTION_KEY", KEY)
    import subscribers as module
    return module


def test_tokens_match(subscribers):
    js = run_node("""
        import { makeToken } from './api/subscribe.js';
        console.log(JSON.stringify({ u: makeToken('unsubscribe', 'user@example.com'), r: makeToken('renew', 'user@example.com') }));
    """, {"SUBSCRIBER_ENCRYPTION_KEY": KEY})
    assert js["u"] == subscribers.make_token("unsubscribe", " User@Example.com ")
    assert js["r"] == subscribers.make_token("renew", "user@example.com")


def test_python_encrypts_js_decrypts(subscribers):
    payload = json.dumps({"emails": [{"email": "a@b.co", "date": "2026-01-01"}]})
    doc = subscribers._encrypt(payload, subscribers._get_key())
    js = run_node(f"""
        import {{ decrypt, getKey }} from './api/subscribe.js';
        console.log(decrypt({json.dumps(doc)}, getKey()));
    """, {"SUBSCRIBER_ENCRYPTION_KEY": KEY})
    assert js == json.loads(payload)


def test_js_encrypts_python_decrypts(subscribers):
    doc = run_node("""
        import { encrypt, getKey } from './api/subscribe.js';
        console.log(JSON.stringify(encrypt(JSON.stringify({ emails: [{ email: 'x@y.kr', date: '2026-02-02' }] }), getKey())));
    """, {"SUBSCRIBER_ENCRYPTION_KEY": KEY})
    assert json.loads(subscribers._decrypt(doc, subscribers._get_key())) == {"emails": [{"email": "x@y.kr", "date": "2026-02-02"}]}


def test_cleanup_rules_match(subscribers):
    raw = ["old@format.com", {"email": "ok@test.com", "date": "2026-06-01"}, {"email": "expired@test.com", "date": "2025-01-01"},
           {"email": "bad address", "date": "2026-06-01"}, {"email": " ctrl\u0007@test.com ", "date": "2026-06-01"}]
    py, _ = subscribers.clean_subscribers(raw, today=datetime(2026, 11, 28))
    js = run_node(f"""
        import {{ cleanSubscribers }} from './api/subscribe.js';
        console.log(JSON.stringify(cleanSubscribers({json.dumps(raw)}, '2026-11-28')));
    """, {})
    assert js == py
