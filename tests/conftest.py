"""
테스트 공통 설정.

파이프라인 스크립트는 저장소 루트에서 'python codes/pycode/<이름>.py' 로 실행되는 것을 전제로
상대 경로(codes/...)를 쓰므로, 테스트도 저장소 루트에서 codes/pycode 를 import 경로에 넣고 실행합니다.
네트워크·메일 발송은 하지 않습니다.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYCODE = ROOT / "codes" / "pycode"

if str(PYCODE) not in sys.path:
    sys.path.insert(0, str(PYCODE))
os.chdir(ROOT)

# 실수로라도 메일이 나가지 않도록
os.environ.pop("GMAIL_APP_PASSWORD", None)
