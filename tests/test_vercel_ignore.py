"""scripts/vercel-ignore-build.sh: 사이트와 무관한 변경만 있으면 배포를 건너뛰는지 (exit 0 = 건너뜀, 1 = 배포)"""
import shutil
import subprocess

import pytest

from conftest import ROOT

SCRIPT = ROOT / "scripts" / "vercel-ignore-build.sh"
pytestmark = pytest.mark.skipif(shutil.which("git") is None or shutil.which("bash") is None, reason="git/bash 필요")


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                   env={"PATH": "/usr/bin:/bin:/usr/local/bin", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(repo)})


def commit(repo, files):
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def ignore_exit(repo, previous_sha):
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
    if previous_sha:
        env["VERCEL_GIT_PREVIOUS_SHA"] = previous_sha
    return subprocess.run(["bash", str(SCRIPT)], cwd=repo, env=env, capture_output=True, text=True).returncode


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    base = commit(tmp_path, {"index.html": "v1", "codes/mnd.json": "[]", "codes/state/mail.json": "{}"})
    return tmp_path, base


@pytest.mark.parametrize("files, expected", [
    ({"codes/state/mail.json": '{"sent": 1}', "codes/receiver_email.json": "{}"}, 0),   # 메일 발송 기록
    ({"codes/pycode/mnd.py": "print()", "README.md": "doc", ".github/workflows/x.yml": "on: push"}, 0),
    ({"codes/mnd.json": "[1]"}, 1),        # 수집 데이터
    ({"public/audio.mp3": "mp3"}, 1),      # 오디오
    ({"index.html": "v2"}, 1),             # 사이트 코드
    ({"codes/state/audio.json": "{}", "codes/data.txt": "today"}, 1),
])
def test_decides_by_changed_paths(repo, files, expected):
    path, base = repo
    commit(path, files)
    assert ignore_exit(path, base) == expected


def test_compares_against_last_deployment_not_just_parent(repo):
    path, base = repo
    commit(path, {"codes/mnd.json": "[1]"})        # 배포되지 않은 데이터 변경 (한 번에 여러 커밋 push)
    commit(path, {"codes/state/mail.json": '{"sent": 2}'})  # 마지막 커밋은 기록만
    assert ignore_exit(path, base) == 1


def test_builds_when_previous_deployment_unknown(repo):
    path, _ = repo
    assert ignore_exit(path, None) == 1
    assert ignore_exit(path, "0" * 40) == 1
