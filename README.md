# 🏙️ 아산 스마트시티 WBS 통합 대시보드

아산 컴팩트 스마트시티 조성사업의 단위사업별 WBS(Work Breakdown Structure)를 실시간으로 모니터링하고 관리하는 통합 대시보드입니다.

## ✨ 주요 기능

- **📊 실시간 KPI 모니터링**: 전체 작업 현황, 진행률, 상태별 분포 한눈에 파악
- **🔄 Notion 자동 동기화**: GitHub Actions를 통한 일일 자동 데이터 동기화
- **📈 시각화 차트**: 상태별, 카테고리별, 담당자별, 단위사업별 분포 차트
- **🎯 단위사업별 현황**: 16개 단위사업의 진척 현황 카드 뷰
- **🔍 검색 및 필터링**: 작업 검색, 상태별 필터링 기능
- **📱 반응형 디자인**: 모바일, 태블릿, 데스크톱 모든 기기 지원

## 🚀 빠른 시작

### 1. GitHub 저장소 생성

```bash
# 저장소 클론 또는 새 저장소 생성
git clone https://github.com/YOUR_USERNAME/asan-wbs-dashboard.git
cd asan-wbs-dashboard
```

### 2. Notion API 키 설정

1. [Notion Developers](https://developers.notion.com/)에서 통합 생성
2. WBS 데이터베이스에 통합 연결
3. GitHub Secrets에 `NOTION_API_KEY` 추가

```
Settings → Secrets and variables → Actions → New repository secret
Name: NOTION_API_KEY
Value: your-notion-api-key
```

### 3. GitHub Pages 활성화

```
Settings → Pages → Source: Deploy from a branch → Branch: gh-pages
```

### 4. 첫 동기화 실행

```
Actions → Sync Notion WBS Data → Run workflow
```

## 📁 프로젝트 구조

```
asan-wbs-dashboard/
├── .github/
│   └── workflows/
│       └── sync.yml          # GitHub Actions 워크플로우
├── data/
│   └── wbs-data.json         # 동기화된 WBS 데이터
├── index.html                # 메인 대시보드
├── sync_notion.py            # Notion 동기화 스크립트
└── README.md
```

## 🔧 설정 옵션

### 동기화 주기 변경

`.github/workflows/sync.yml` 파일에서 cron 표현식 수정:

```yaml
schedule:
  # 매일 한국 시간 오전 9시 (UTC 00:00)
  - cron: '0 0 * * *'
  
  # 6시간마다 동기화 (더 자주)
  # - cron: '0 */6 * * *'
  
  # 매시간 동기화 (실시간에 가깝게)
  # - cron: '0 * * * *'
```

### 수동 동기화

GitHub Actions 페이지에서 "Run workflow" 버튼으로 수동 실행 가능

## 📊 데이터 구조

### Notion 데이터베이스 스키마

| 필드 | 타입 | 설명 |
|------|------|------|
| id | Title | 작업 ID (ASAN-XXXX) |
| name | Text | 작업명 |
| type | Select | 유형 (사업관리/요구분석/인프라설계/기타) |
| category | Select | 카테고리 |
| subcategory | Text | 단위사업명 |
| assignee | Text | 담당자 |
| deliverable | Text | 산출물 |
| status | Select | 상태 (진행중/대기/완료/지연) |
| progress | Number | 진척률 (%) |
| created_date | Date | 생성일 |

### 단위사업 목록 (16개)

1. 무인매장
2. 정보관리 시스템
3. SDDC 기반 HW 플랫폼 구축
4. 스마트폴 & 디스플레이
5. 스마트 주차
6. 스마트 교통
7. 공공 WiFi
8. 스마트 가로등
9. 도시통합관제센터
10. ESG 플랫폼
11. 디지털트윈
12. 공공데이터 개방 포털
13. 스마트 안전
14. 주민참여 플랫폼
15. 사업예산 실시설계
16. 프로젝트 상세 작업계획(WBS) 작성

## 🔗 관련 링크

- **Notion WBS Database**: [https://notion.so/2a250aa9577d80c6926df376223a3846](https://notion.so/2a250aa9577d80c6926df376223a3846)
- **GitHub Pages Dashboard**: `https://YOUR_USERNAME.github.io/asan-wbs-dashboard/`

## 🛠️ 기술 스택

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **차트**: Chart.js
- **백엔드**: Python 3.11
- **CI/CD**: GitHub Actions
- **호스팅**: GitHub Pages
- **데이터 소스**: Notion API

## 📝 라이선스

이 프로젝트는 제일엔지니어링 PMO 팀에서 관리합니다.

---

🏛️ **아산 컴팩트 스마트시티 조성사업** | 제일엔지니어링 PMO
