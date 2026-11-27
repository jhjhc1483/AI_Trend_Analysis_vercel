# 🤖 인공지능 동향 분석 사이트 (AI Trend Analyzer)

국방 및 인공지능(AI) 분야의 최신 기사와 간행물을 자동으로 수집하고, 인공지능(Gemini)을 활용하여 핵심 내용을 분석 및 브리핑하는 웹 서비스입니다. Vercel을 통해 배포되며, GitHub Actions를 통해 매일 데이터가 자동으로 업데이트됩니다.

---

## 🌟 주요 기능

- **📰 자동 뉴스 및 간행물 수집**: 국방부, 방사청, 과기정통부, AI Times 등 16개 출처에서 매일 최신 데이터를 크롤링합니다.
- **🤖 AI 자동 선정 및 분류**: Google Gemini API로 어제 기사 중 중요한 항목을 골라 카테고리(국방, 육군, 민간, 기관, 해외)를 분류합니다.
  - 여러 출처에 같은 제목으로 올라온 기사(예: 국방부가 다시 게시한 국방일보 기사)는 하나만 남깁니다. (국방부 쪽 우선)
  - 최근 3일 브리핑과 같은 사건은 새로운 진전이 있을 때만 다시 고릅니다.
- **🎙️ AI 오디오 브리핑 생성**: 선정된 뉴스로 브리핑 대본을 쓰고 오디오(`.mp3`)를 만듭니다.
- **📧 이메일 구독 서비스**: `subscribe.html`에서 구독하면 매일 브리핑 메일을 받습니다. 구독은 1년간 유지되며, 만료 2주 전부터 메일에 '1년 연장하기' 안내가 붙습니다. 메일마다 본인 전용 '구독 해지' 링크가 있습니다.
  - ⏸️ **현재 신규 구독 신청은 일시 중단** 상태입니다. 기존 구독자의 메일 발송·해지·연장은 그대로 동작합니다. (다시 여는 방법은 아래 '자주 쓰는 설정 변경' 참고)
- **🖥️ 대시보드**: 첫 화면은 최근 30일 데이터만 빠르게 불러오고, 검색하거나 '전체 기간 불러오기'를 누르면 전체 데이터를 받습니다. 다크 모드·모바일 메뉴 지원.
  - **⚙️ 오늘 자동 처리 현황**: 기사 수집 → AI 선정 → 오디오 → 메일 단계별 최근 실행 결과. 관리자가 실행한 작업은 끝나면 알림이 뜹니다.
- **⭐ 오늘 일일 동향**: AI가 고른 목록(`codes/favorites/favorite_*.json`)이 ★로 표시됩니다. ☆/★로 넣고 빼거나 분류 배지를 눌러 바꾼 뒤 **💾 일일 동향 저장**(관리자)을 누르면 약 1분 뒤 텍스트에 반영됩니다.
  - 저장 전 변경은 그 브라우저에만 임시로 남고, 새 AI 선정이 나오면 새 목록으로 바뀝니다.
  - 관리자 모드에서는 AI 분류 학습 데이터(🧠 Few-shot)·일일 동향 제외(🚫) 목록을 고칠 수 있습니다.
- **📋 일일 동향 복사**: 오늘 일일 동향 텍스트(`codes/data.txt`)를 바로 복사해 공유합니다.
- **📊 데이터 시각화 / 📅 지난 일일 동향**: `visualizer.html`에서 통계·추이를 보고, 날짜를 골라 지난 동향을 봅니다.

---

## 🛠 기술 스택

- **Frontend**: HTML5 / CSS3 / Vanilla JavaScript
- **Backend & Deployment**: Vercel (정적 호스팅 + Serverless Functions), GitHub Actions (자동화)
- **AI & Automation**: Python (requests, BeautifulSoup4, Selenium, pandas), Google Gemini API, Edge-TTS

---

## 📂 프로젝트 구조

```text
.
├── config/sources.json         # ★ 수집 출처 목록 (크롤러·AI 선정·대시보드가 모두 이 파일을 씀)
├── api/                        # Vercel Serverless Functions
│   ├── auth.js                 #   관리자 비밀번호 확인
│   ├── github.js               #   대시보드 → GitHub API 프록시 (허용 목록에 있는 요청만 통과, 삭제 불가)
│   ├── cron-crawl.js           #   매일 크롤링 시작 신호 (Vercel Cron이 호출 → main.yml 실행)
│   └── subscribe.js            #   구독 신청/해지/연장 (구독자 목록 암호화 저장)
├── codes/
│   ├── *.json                  # 출처별 수집 데이터
│   ├── data.txt / data.json    # 오늘 일일 동향 텍스트 / 날짜별 일일 동향 기록
│   ├── receiver_email.json     # 구독자 목록 (암호화됨)
│   ├── favorites/              # 즐겨찾기, AI 학습 데이터(Few-shot), 일일동향 제외 목록
│   ├── dashboard/recent.json   # 대시보드 첫 화면용 최근 30일 데이터 (크롤링 때 생성)
│   ├── state/                  # 파이프라인 상태 기록 (아래 '일일 자동 파이프라인' 참고)
│   └── pycode/
│       ├── run_crawlers.py     #   크롤러 16개 실행 + 결과 리포트
│       ├── sources.py          #   출처 목록(config/sources.json) 읽기
│       ├── crawler_common.py   #   크롤러 공통 함수 (저장, ScraperAPI 요청)
│       ├── <출처>.py            #   출처별 크롤러 (사이트별 파싱만 담당)
│       ├── auto_favorites.py   #   AI 자동 선정 (Gemini)
│       ├── json_to_txt.py      #   즐겨찾기 → 일일 동향 텍스트(data.txt/data.json)
│       ├── gen_audio.py        #   브리핑 대본 + 오디오 생성
│       ├── gmail_send_visualizer.py  # 구독자 메일 발송
│       ├── cleanup_expired_emails.py # 만료 구독자 정리 (+ 암호화 변환)
│       ├── build_dashboard_data.py   # 대시보드용 최근 30일 데이터 생성
│       ├── subscribers.py      #   구독자 목록 읽기/쓰기·암호화·링크 토큰
│       ├── pipeline_state.py   #   파이프라인 상태 파일 읽기/쓰기
│       ├── pipeline_report.py  #   단계별 상태 요약, 사이트 구조 변경 감지, 관리자 알림
│       └── notify.py           #   관리자 알림 메일 발송
├── public/                     # 오늘 브리핑 오디오(audio.mp3), 오디오 재생 페이지(bf.html), 공유 썸네일
├── scripts/vercel-ignore-build.sh  # 사이트와 무관한 커밋은 Vercel 배포를 건너뜀 (vercel.json ignoreCommand)
├── tests/                      # 테스트 (CI에서 실행, 네트워크·AI·메일 호출 없음)
├── .github/workflows/          # 자동화 워크플로우 + ci.yml(코드 검사)
├── index.html / script.js / style.css   # 메인 대시보드
├── subscribe.html              # 구독 신청/해지 (메일 속 해지·연장 링크도 처리)
└── visualizer.html / visualizer_brief.html  # 시각화 / 브리핑 페이지
```

---

## 🔄 일일 자동 파이프라인

```text
크롤링(main.yml) → AI 자동 선정(auto_favorites.yml) → 오디오(audio_gen.yml) → 구독자 메일(kakao_or_gmail_send.yml)
```

- 앞 단계가 끝나면 다음 단계가 자동으로 이어서 실행됩니다. 메일은 오디오 생성이 끝나는 즉시 발송됩니다.
- 매일 시작 신호는 **Claude 예약 작업**이 보냅니다. (매일 **04:03 KST**)
  - 저장소 밖(claude.ai 계정의 예약 작업)에 설정되어 있습니다. 예약 작업 이름은 'AI 동향 매일 크롤링 시작 (04:03 KST)'입니다.
  - 매일 **05:13 KST**에 예약 작업 'AI 동향 파이프라인 점검·복구 (05:13 KST)'가 크롤링 → AI 자동 선정 → 오디오 → 메일 중 실패한 단계를 찾아 그 단계만 한 번 다시 실행합니다. (진행 중이거나 메일까지 성공했으면 아무것도 안 함)
  - 전용 세션이 오늘 `main.yml` 실행이 이미 있는지 확인한 뒤, 없을 때만 `main.yml`을 실행합니다(round 1).
  - 자정 전으로 옮기면 안 됩니다. AI 자동 선정이 KST 기준 '어제' 날짜 기사를 고르기 때문입니다.
- 대안(현재 꺼져 있음): **Vercel Cron**도 쓸 수 있습니다. (`vercel.json`의 `crons` → `api/cron-crawl.js`, KST 00시대)
  - Vercel 환경변수 `CRON_SECRET`을 등록하면 동작합니다. 등록하지 않으면 모든 호출을 거부합니다.
  - 둘 다 켜져 있어도 Claude 예약 작업은 그날 이미 실행된 크롤링이 있으면 새로 실행하지 않습니다.
- `main.yml`의 GitHub 예약(00:06, 00:37 KST)은 **예비용**입니다. GitHub 예약은 몇 시간씩 밀리거나 건너뛰는 일이 있어 시작 신호로 쓰지 않습니다.
  - 예약으로 실행되면 항상 '오늘 실패한 출처만 재시도' 모드라, 그날 이미 수집했으면 거의 할 일 없이 끝납니다.
  - Vercel Cron이 실패해 그날 아무것도 안 돌았으면 전체 수집을 대신합니다.
  - **2회차**는 1회차에서 실패한 출처만 다시 수집합니다. 모두 성공했으면 건너뜁니다.
- 크롤링이 하루에 여러 번 끝나도 **AI 선정·오디오·메일은 하루 한 번씩만** 실행됩니다. 대시보드 버튼으로 직접 실행하면 항상 실행됩니다.
- 각 단계는 결과를 main에 커밋하고, 사이트(Vercel)는 그 커밋으로 다시 배포됩니다. 사이트에 보이지 않는 파일(`codes/state/`, 구독자 목록, 파이썬 코드, 워크플로우, 문서)만 바뀐 커밋은 배포하지 않습니다. (`scripts/vercel-ignore-build.sh`)
- 메일은 GitHub Actions의 오디오 생성이 끝날 때만 이어서 발송됩니다 (별도 예약 없음). 로컬에서 실행해 푸시한 경우에는 메일이 자동으로 나가지 않으니 Actions에서 `KakaoTalk or Gmail Auto Send`를 mode `send`로 실행하세요.

**상태 기록 (`codes/state/`)**

| 파일 | 내용 |
|---|---|
| `crawl_status.json` | 오늘 출처별 수집 결과, 최근 14일 이력 (사이트 구조 변경 감지용) |
| `crawl_log.json` | 날짜별·출처별 수집 결과 **영구 누적** (성공 여부, 가져온/신규 건수, 시도 횟수). '기사가 없던 날'과 '수집에 실패한 날'을 구분하는 근거 |
| `audio.json` | 오디오를 만든 일일 동향의 해시 |
| `mail.json` | 마지막 발송 날짜와 인원 |

**날짜별 일일 동향 기록 (`codes/data.json`)**

날짜 키(예: `26.11.18`)마다 아래 값이 쌓입니다. 나중에 분석·출품에 쓸 수 있도록 AI 원안과 사람이 고친 최종본을 따로 남깁니다.

| 키 | 내용 |
|---|---|
| `categorized` | **최종본** (메일·대시보드에 나간 목록). 대시보드에서 고쳐 저장해도 AI가 매긴 점수·이유·키워드는 같은 링크에서 다시 채워짐 |
| `ai_pick` | **AI 원안**. AI 자동 선정이 처음 고른 목록 그대로 (출처, 분류, 점수, 선정 이유, 키워드) |
| `ai_meta` | 그날 선정 조건: 모델, 프롬프트 버전(문구 해시), few-shot·제외 규칙 수, 후보·제외·선정 건수 |
| `edited_at` | 대시보드에서 사람이 고쳐 저장한 시각 (없으면 AI 원안을 그대로 쓴 날) |
| `briefing` | 오디오 브리핑 대본 |

**관리자 알림**
- 평소에는 메일 발송이 끝난 뒤 **하루 한 통 요약**(단계별 상태 + 출처별 새 기사 수)을 받습니다.
- 다음 경우에는 그때그때 알림이 옵니다.
  - 크롤링 실패
  - 출처가 2일 연속 0건 (구조 변경 의심)
  - 뉴스 출처의 새 기사가 4일 연속 0건
  - AI 선정 또는 오디오 단계 실패
  - 메일 발송 시점에 데이터가 준비되지 않음

**자주 쓰는 수동 실행** (GitHub → Actions → 워크플로우 선택 → Run workflow)
- 오늘 크롤링부터 전체 다시 돌리기: `Run Python Scripts Daily` (이어서 AI 선정 → 오디오 → 메일이 자동 진행)
- 메일 보내기: `KakaoTalk or Gmail Auto Send` → mode `send` (로컬 실행 후 등 체인이 메일까지 안 간 날) / 이미 보낸 날 다시 보내기는 `resend`
- 메일 없이 구독자 목록만 정리·암호화: 같은 워크플로우 → mode `cleanup_only`
- 오늘 상태 확인(로컬): `python codes/pycode/pipeline_report.py --summary --print`

**자주 쓰는 설정 변경**
- 신규 구독 신청 다시 열기: 아래 세 곳을 함께 바꿉니다.
  - `api/subscribe.js`의 `SUBSCRIBE_OPEN`을 `true`로
  - `subscribe.html`의 `SUBSCRIBE_OPEN`을 `true`로
  - `index.html`의 구독 버튼(`subscribeRedirectBtn`)에서 `hidden` 제거
- 출처 추가: `codes/pycode/<이름>.py` 크롤러를 만들고(`crawler_common.save_results`로 `codes/<파일>.json`에 저장) `config/sources.json`에 한 줄 추가합니다. 크롤링·AI 선정·대시보드 메뉴에 모두 반영됩니다.
- 크롤링 시작 시각: claude.ai의 예약 작업 'AI 동향 매일 크롤링 시작 (04:03 KST)'에서 변경. (대안인 Vercel Cron은 `vercel.json`의 `crons`, 예비용 GitHub 예약은 `.github/workflows/main.yml`의 `cron`. 둘 다 UTC 기준, KST = UTC + 9시간)

---

## 🔐 환경 변수 / 비밀값

| 이름 | Vercel 환경변수 | GitHub Secrets | 용도 |
|---|:---:|:---:|---|
| `GITHUB_TOKEN` | ✅ | (자동) | 대시보드·구독 API가 저장소 파일을 읽고 쓰기 |
| `ADMIN_PASSWORD` | ✅ | | 대시보드 관리자 기능 |
| `CRON_SECRET` | ✅ (선택) | | Vercel Cron으로 크롤링을 시작할 때만 필요 (`api/cron-crawl.js` 인증). 16자 이상 임의 문자열 |
| `SUBSCRIBER_ENCRYPTION_KEY` | ✅ | ✅ | 구독자 목록 암호화 + 메일 속 해지/연장 링크 서명 (**두 곳에 같은 값**, 32자 이상) |
| `GEMINI_API_KEY` | | ✅ | AI 자동 선정·브리핑 |
| `GMAIL_APP_PASSWORD` | | ✅ | 구독자 메일·관리자 알림 발송 (Gmail 앱 비밀번호) |
| `SCRAPER_API_KEY`, `_2`, `_3` | | ✅ | 봇 차단 사이트(국방부·방사청·국방일보·KISTI) 우회 |

저장소가 공개되어 있으므로 구독자 목록(`codes/receiver_email.json`)은 암호화해서 보관합니다.

---

## 🚀 로컬 실행

1. 저장소를 클론합니다.
2. 파이썬 패키지를 설치합니다: `pip install -r requirements.txt`
3. 필요한 값을 `.env`에 넣습니다. (위 표 참고)
4. 저장소 루트에서 실행합니다. 예: `python codes/pycode/run_crawlers.py --no-mail`

> 로컬에서 크롤링·AI 선정·오디오를 실행해 푸시하면 구독자 메일은 자동으로 나가지 않습니다. 메일은 GitHub Actions의 오디오 단계가 끝날 때만 이어서 발송되므로, 푸시 후 Actions에서 `KakaoTalk or Gmail Auto Send`를 mode `send`로 실행하세요.

### 테스트 · CI

- 코드 수정은 브랜치에서 하고 PR로 병합합니다. PR과 브랜치 push 때 `.github/workflows/ci.yml`이 테스트와 문법 검사를 실행합니다. (main의 데이터 커밋에는 실행하지 않음)
- 로컬 실행:
  - 파이썬: `python -m pytest -q tests`
  - 자바스크립트: `node --test "tests/js/*.test.mjs"`
- 파이썬 패키지 버전은 `requirements.txt`에 고정되어 있고, 데이터 워크플로우도 `pip install -c requirements.txt ...`로 같은 버전을 씁니다. Dependabot이 한 달에 한 번 버전 올리기 PR을 만듭니다. CI가 통과하면 병합하세요.

---

## 🗓 데이터 소스

### 뉴스 (News)
- 국가인공지능전략위원회, 국방부, 국방일보, 과기정통부, AI Times, 전자신문, 인공지능신문, 방위사업청

### 간행물 (Publication)
- NIA, IITP, STEPI, NIPA, KISDI, KISTI, KISA, TTA

---

## ⚖️ 저작권 및 라이선스
&copy; 2026 Maj.CJH. All rights reserved. 본 프로젝트는 개인적인 학습 및 정보 분석 목적으로 개발되었습니다.
