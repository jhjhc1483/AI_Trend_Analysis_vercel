#!/usr/bin/env bash
# Vercel 'Ignored Build Step' (vercel.json 의 ignoreCommand 가 실행)
#   exit 0 → 이번 배포를 건너뜀
#   exit 1 → 배포 진행
#
# 사이트(정적 파일 + api/)가 읽지 않는 파일만 바뀐 커밋이면 배포하지 않습니다.
#   예) 메일 발송 기록 커밋(codes/state/mail.json, codes/receiver_email.json),
#       파이썬 코드·워크플로우·문서·테스트만 바꾼 커밋
# 기사 데이터·일일 동향·오디오처럼 사이트에 보이는 파일이 바뀌면 지금처럼 배포됩니다.
#
# 비교 기준은 '마지막으로 성공한 배포의 커밋'(VERCEL_GIT_PREVIOUS_SHA)입니다.
# 그 커밋을 찾을 수 없거나 비교 중 오류가 나면 항상 배포합니다. (안전한 쪽으로)

# 사이트와 무관한 경로 (여기에 없는 경로가 하나라도 바뀌면 배포)
IGNORED_PATHS=(
  ':(exclude)codes/state'
  ':(exclude)codes/pycode'
  ':(exclude)codes/receiver_email.json'
  ':(exclude).github'
  ':(exclude)tests'
  ':(exclude)scripts'
  ':(exclude).vscode'
  ':(exclude)*.md'
  ':(exclude)requirements*.txt'
)

BASE="${VERCEL_GIT_PREVIOUS_SHA:-}"
if [ -z "$BASE" ]; then
  echo "이전 배포 기록이 없어 배포합니다."
  exit 1
fi
if ! git cat-file -e "${BASE}^{commit}" 2>/dev/null; then
  echo "이전 배포 커밋(${BASE})을 찾을 수 없어 배포합니다."
  exit 1
fi

git diff --quiet "$BASE" HEAD -- . "${IGNORED_PATHS[@]}"
status=$?

if [ "$status" -eq 0 ]; then
  echo "사이트에 영향을 주는 변경이 없어 배포를 건너뜁니다. (${BASE:0:7}..HEAD)"
  git diff --name-only "$BASE" HEAD | sed 's/^/  - /'
  exit 0
fi

echo "사이트 파일이 바뀌어 배포합니다."
git diff --name-only "$BASE" HEAD -- . "${IGNORED_PATHS[@]}" 2>/dev/null | head -20 | sed 's/^/  + /'
exit 1
