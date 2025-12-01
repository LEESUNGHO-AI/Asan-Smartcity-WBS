# 🏙️ 아산 스마트시티 WBS 통합 대시보드

아산 컴팩트 스마트시티 조성사업의 WBS(Work Breakdown Structure) 현황을 실시간으로 시각화하는 대시보드입니다.

## 🌟 주요 기능

- **실시간 동기화**: Notion 데이터베이스와 GitHub Actions를 통한 자동 동기화
- **통합 시각화**: 16개 단위사업별 진행현황, 진척률, 담당자별 업무 현황
- **다양한 차트**: 진행상태, 우선순위, 담당자, 진척률 등 다각도 분석
- **검색 및 필터**: 업무영역, 상태, 담당자별 필터링

## 📊 데이터 구조

### 단위사업 (16개 업무 영역)
- 디지털 OASIS SPOT 구축
- 스마트폴&디스플레이
- 무인매장
- 스마트 공공 WiFi
- AI시티관제 플랫폼 구축
- 정보관리 서비스(데이터허브)
- SDDC 기반 HW 인프라 구축
- 데이터 기반 AI 융복합 SW개발 플랫폼
- 모바일 전자시민증
- 수요응답형 모빌리티
- 메타버스 플랫폼
- 시설물위치기반서비스플랫폼
- 이노베이션 센터 인테리어 실시설계 및 시공
- 디지털 노마드 접수/운영/거래 관리 플랫폼 구축
- RFP 문서작성
- WBS

## 🚀 빠른 시작

### 1단계: GitHub 저장소 생성
```bash
git init
git add .
git commit -m "Initial commit: Asan Smart City WBS Dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/asan-wbs-dashboard.git
git push -u origin main
```

### 2단계: Notion API 키 설정

1. [Notion Developers](https://developers.notion.com/) 접속
2. 새 통합(Integration) 생성
3. WBS 데이터베이스에 통합 연결:
   - 데이터베이스 페이지 → 우측 상단 `...` → `연결 추가` → 생성한 통합 선택
4. Internal Integration Token 복사

### 3단계: GitHub Secrets 설정
- GitHub 저장소 → `Settings` → `Secrets and variables` → `Actions`
- `New repository secret` 클릭
- Name: `NOTION_API_KEY`
- Value: 노션 통합 API 키 입력

### 4단계: GitHub Pages 활성화
- `Settings` → `Pages`
- Source: `GitHub Actions` 선택

### 5단계: 워크플로우 실행
- `Actions` 탭 → `Sync Notion WBS Data` → `Run workflow`
- 이후 매일 오전 9시(KST) 자동 동기화

## 📁 프로젝트 구조

```
asan-wbs-dashboard/
├── index.html              # 메인 대시보드
├── sync_notion.py          # Notion 동기화 스크립트
├── data/
│   └── wbs-data.json       # 동기화된 WBS 데이터
├── .github/
│   └── workflows/
│       └── sync.yml        # GitHub Actions 워크플로우
└── README.md
```

## ⚙️ 설정 옵션

### 동기화 주기 변경
`.github/workflows/sync.yml`에서 cron 표현식 수정:
```yaml
schedule:
  - cron: '0 0 * * *'  # 매일 UTC 00:00 (KST 09:00)
```

### 수동 동기화
GitHub Actions → `Sync Notion WBS Data` → `Run workflow`

## 🔗 관련 링크

- **Notion 원본 데이터베이스**: [🎯 아산시 스마트시티 조성사업 단위사업별 WBS](https://www.notion.so/2a250aa9577d80ca8bf2f2abfce71a59)
- **프로젝트 관리 페이지**: [프로젝트와 작업](https://www.notion.so/2aa50aa9577d80c4915ef7d62b966de4)

## 🛠️ 기술 스택

- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Chart.js
- **Backend**: Python 3.11, Notion API
- **CI/CD**: GitHub Actions
- **Hosting**: GitHub Pages

## 📄 라이선스

© 2024 제일엔지니어링. All rights reserved.
