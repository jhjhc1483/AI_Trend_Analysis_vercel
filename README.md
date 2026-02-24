# 🤖 인공지능 동향 분석 사이트 (AI Trend Analyzer)

국방 및 인공지능(AI) 분야의 최신 기사와 간행물을 자동으로 수집하고, 인공지능(Gemini)을 활용하여 핵심 내용을 분석 및 브리핑하는 웹 서비스입니다. Vercel을 통해 배포되며, GitHub Actions를 통해 매일 데이터가 자동으로 업데이트됩니다.

---

## 🌟 주요 기능

- **📰 자동 뉴스 및 간행물 수집**: 국방부, 방사청, 과기정통부, AI Times 등 총 16개 이상의 주요 출처에서 매일 최신 데이터를 크롤링합니다.
- **🤖 AI 자동 선정 및 분류 (Beta)**: Google Gemini API를 사용하여 어제 발생한 뉴스 중 중요도가 높은 항목을 자동으로 선정하고 카테고리(국방, 육군, 민간, 기관, 해외)를 분류합니다.
- **🎙️ AI 오디오 브리핑 생성**: 선정된 뉴스 데이터를 바탕으로 AI가 요약 브리핑 대본을 작성하고 오디오 파일(`.mp3`)을 생성합니다.
- **⭐ 즐겨찾기 및 개인화**: 사용자가 직접 중요한 기사를 즐겨찾기에 추가하거나, AI의 분류 오류를 학습시키기 위한 데이터(Few-shot)를 추가할 수 있습니다.
- **📋 텍스트 추출**: 선정된 동향 데이터를 복사 가능한 텍스트 형식으로 즉시 추출하여 보고서나 메시지 공유에 활용할 수 있습니다.

---

## 🛠 기술 스택

### Frontend
- **HTML5 / CSS3**: 현대적이고 반응형인 대시보드 UI 구현.
- **JavaScript (Vanilla JS)**: 상태 관리 및 GitHub/Vercel API 연동.

### Backend & Deployment
- **Vercel**: 웹 호스팅 및 Serverless Functions(Node.js) 제공.
- **GitHub Actions**: 매일 정해진 시간에 파이썬 스크립트를 실행하여 데이터 최신화.

### AI & Automation
- **Python**: Selenium, BeautifulSoup4, Pandas를 활용한 웹 크롤링.
- **Google Gemini API**: 뉴스 선정, 분류 및 요약 브리핑 생성.
- **TTS (Text-to-Speech)**: AI 음성 브리핑 생성.

---

## 📂 프로젝트 구조

```text
.
├── api/                # Vercel Serverless Functions (Proxy, Auth)
├── codes/              # 뉴스/간행물 데이터 저장소 (.json)
│   ├── pycode/         # 크롤링 및 AI 분석 파이썬 스크립트
│   └── favorites/      # 즐겨찾기 및 AI 학습 데이터
├── public/             # 오디오 및 정적 자원
├── .github/workflows/  # 자동화 워크플로우 (Daily Updates, AI Task)
├── index.html          # 메인 대시보드 페이지
├── script.js           # 프론트엔드 핵심 로직
└── style.css           # 디자인 스타일시트
```

---

## 🚀 시작하기

### 환경 변수 설정
로컬 실행 또는 배포 시 다음 환경 변수가 필요합니다:
- `GEMINI_API_KEY`: Google Gemini API 키
- `GITHUB_TOKEN`: 데이터 자동 커밋 및 워크플로우 실행을 위한 권한
- `ADMIN_PASSWORD`: 대시보드 관리자 기능 접근을 위한 비밀번호

### 설치 및 실행
1. 저장소를 클론합니다.
   ```bash
   git clone https://github.com/jhjhc1483/AI_Trend_Analysis_vercel.git
   ```
2. 필요한 파이썬 패키지를 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```
3. Vercel CLI를 사용하여 배포하거나 로컬 서버를 실행합니다.

---

## 🗓 데이터 소스

### 뉴스 (News)
- 국가인공지능전략위원회, 국방부, 국방일보, 과기정통부, AI Times, 전자신문, 인공지능신문, 방위사업청

### 간행물 (Publication)
- NIA, IITP, STEPI, NIPA, KISDI, KISTI, KISA, TTA

---

## ⚖️ 저작권 및 라이선스
&copy; 2026 Maj.CJH. All rights reserved. 본 프로젝트는 개인적인 학습 및 정보 분석 목적으로 개발되었습니다.
