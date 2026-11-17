# 🤖 인공지능 동향 분석 사이트 (AI Trend Analyzer)

국방 및 인공지능(AI) 분야의 최신 기사와 간행물을 자동으로 수집하고, 인공지능(Gemini)을 활용하여 핵심 내용을 분석 및 브리핑하는 웹 서비스입니다. Vercel을 통해 배포되며, GitHub Actions를 통해 매일 데이터가 자동으로 업데이트됩니다.

---

## 🌟 주요 기능

- **📰 자동 뉴스 및 간행물 수집**: 국방부, 방사청, 과기정통부, AI Times 등 16개 출처에서 매일 최신 데이터를 크롤링합니다.
- **🤖 AI 자동 선정 및 분류**: Google Gemini API로 어제 기사 중 중요한 항목을 골라 카테고리(국방, 육군, 민간, 기관, 해외)를 분류합니다. 최근 3일 브리핑과 같은 사건은 새로운 진전이 있을 때만 다시 고릅니다.
- **🎙️ AI 오디오 브리핑 생성**: 선정된 뉴스로 브리핑 대본을 쓰고 오디오(`.mp3`)를 만듭니다.
- **📧 이메일 구독 서비스**: `subscribe.html`에서 구독하면 매일 브리핑 메일을 받습니다. 구독은 1년간 유지되며, 만료 2주 전부터 메일에 '1년 연장하기' 안내가 붙습니다. 메일마다 본인 전용 '구독 해지' 링크가 있습니다.
- **📅 지난 일일 동향 조회**: `visualizer.html`에서 날짜를 골라 지난 날의 동향을 볼 수 있습니다.
- **⭐ 즐겨찾기 및 개인화**: 중요한 기사를 즐겨찾기하거나, AI 분류 학습 데이터(Few-shot)·일일동향 제외 목록을 추가할 수 있습니다.
- **📋 텍스트 추출 및 공유**: 선정된 동향을 복사 가능한 텍스트로 바로 추출합니다.
- **📊 데이터 시각화**: `visualizer.html`에서 통계와 추이를 확인합니다.

---

## 🛠 기술 스택

- **Frontend**: HTML5 / CSS3 / Vanilla JavaScript
- **Backend & Deployment**: Vercel (정적 호스팅 + Serverless Functions), GitHub Actions (자동화)
- **AI & Automation**: Python (requests, BeautifulSoup4, Selenium, pandas), Google Gemini API, Edge-TTS

---

## 📂 프로젝트 구조

```text
.
├── api/                        # Vercel Serverless Functions
│   ├── auth.js                 #   관리자 비밀번호 확인
│   ├── github.js               #   대시보드 → GitHub API 프록시 (허용 목록에 있는 요청만 통과)
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
├── public/                     # 오디오(audio.mp3 / audio.json), 오디오 재생 페이지(bf.html)
├── .github/workflows/          # 자동화 워크플로우
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
- 크롤링 예약(01:07, 01:37 KST)은 GitHub 사정으로 실제로는 몇 시간 늦게 시작되는 경우가 많습니다.
  - **2회차**는 1회차에서 실패한 출처만 다시 수집합니다. 모두 성공했으면 건너뜁니다.
- 크롤링이 하루에 여러 번 끝나도 **AI 선정·오디오·메일은 하루 한 번씩만** 실행됩니다. 대시보드 버튼으로 직접 실행하면 항상 실행됩니다.
- 메일 워크플로우에는 **안전장치 예약(12:23 KST)**이 있습니다. 이미 보냈으면 건너뛰고, 오늘 동향이 준비되지 않았으면 관리자에게 경고합니다.

**상태 기록 (`codes/state/`)**

| 파일 | 내용 |
|---|---|
| `crawl_status.json` | 오늘 출처별 수집 결과, 최근 14일 이력 (사이트 구조 변경 감지용) |
| `audio.json` | 오디오를 만든 일일 동향의 해시 |
| `mail.json` | 마지막 발송 날짜와 인원 |

**관리자 알림**
- 평소에는 메일 발송이 끝난 뒤 **하루 한 통 요약**(단계별 상태 + 출처별 새 기사 수)을 받습니다.
- 다음 경우에는 그때그때 알림이 옵니다.
  - 크롤링 실패
  - 출처가 2일 연속 0건 (구조 변경 의심)
  - 뉴스 출처의 새 기사가 4일 연속 0건
  - AI 선정 또는 오디오 단계 실패
  - 메일 발송 시점에 데이터가 준비되지 않음

**자주 쓰는 수동 실행** (GitHub → Actions → 워크플로우 선택 → Run workflow)
- 메일 다시 보내기: `KakaoTalk or Gmail Auto Send` → mode `resend` (오늘 아직 안 보냈으면 `send`)
- 메일 없이 구독자 목록만 정리·암호화: 같은 워크플로우 → mode `cleanup_only`
- 오늘 상태 확인(로컬): `python codes/pycode/pipeline_report.py --summary --print`

---

## 🔐 환경 변수 / 비밀값

| 이름 | Vercel 환경변수 | GitHub Secrets | 용도 |
|---|:---:|:---:|---|
| `GITHUB_TOKEN` | ✅ | (자동) | 대시보드·구독 API가 저장소 파일을 읽고 쓰기 |
| `ADMIN_PASSWORD` | ✅ | | 대시보드 관리자 기능 |
| `SUBSCRIBER_ENCRYPTION_KEY` | ✅ | ✅ | 구독자 목록 암호화 + 메일 속 해지/연장 링크 서명 (**두 곳에 같은 값**, 32자 이상) |
| `GEMINI_API_KEY` | | ✅ | AI 자동 선정·브리핑 |
| `GMAIL_APP_PASSWORD` | | ✅ | 구독자 메일·관리자 알림 발송 (Gmail 앱 비밀번호) |
| `SCRAPER_API_KEY`, `_2`, `_3` | | ✅ | 봇 차단 사이트(국방부·방사청·국방일보·KISTI) 우회 |
| `BLOB_READ_WRITE_TOKEN` | | ✅ (선택) | 있으면 오디오를 Vercel Blob에 저장해 git 저장소 용량이 늘지 않음 (없으면 기존처럼 git에 커밋) |

저장소가 공개되어 있으므로 구독자 목록(`codes/receiver_email.json`)은 암호화해서 보관합니다.

---

## 🚀 로컬 실행

1. 저장소를 클론합니다.
2. 파이썬 패키지를 설치합니다: `pip install -r requirements.txt`
3. 필요한 값을 `.env`에 넣습니다. (위 표 참고)
4. 저장소 루트에서 실행합니다. 예: `python codes/pycode/run_crawlers.py --no-mail`

---

## 🗓 데이터 소스

### 뉴스 (News)
- 국가인공지능전략위원회, 국방부, 국방일보, 과기정통부, AI Times, 전자신문, 인공지능신문, 방위사업청

### 간행물 (Publication)
- NIA, IITP, STEPI, NIPA, KISDI, KISTI, KISA, TTA

---

## ⚖️ 저작권 및 라이선스
&copy; 2026 Maj.CJH. All rights reserved. 본 프로젝트는 개인적인 학습 및 정보 분석 목적으로 개발되었습니다.
