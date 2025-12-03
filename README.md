# 🏗️ 아산 스마트시티 통합 WBS 대시보드

아산 컴팩트 스마트시티 조성사업의 **단위사업별 WBS**와 **사업관리 WBS**를 통합하여 실시간으로 시각화하는 대시보드입니다.

## 📊 주요 기능

### 🔄 실시간 동기화
- Notion 데이터베이스와 GitHub Actions를 통한 자동 동기화
- 매일 KST 09:00, 14:00, 18:00 자동 업데이트
- 수동 동기화 지원

### 📈 통합 대시보드
- **통합 현황**: 두 WBS의 전체 진행 상황 한눈에 파악
- **단위사업별 WBS**: 16개 단위사업 기술 구축 업무 상세 현황
- **사업관리 WBS**: 사업 홍보, 보고, 감사, 현장점검 등 관리업무 현황

### 📉 시각화 차트
- WBS별 진척률 비교 차트
- 담당자별 통합 업무 현황
- 진행현황 분포 (대기/진행중/완료)
- 업무영역별 진척률

### 🔍 검색 및 필터
- WBS 유형별 필터 (전체/단위사업/사업관리)
- 상태별 필터 (대기/진행중/완료)
- 키워드 검색

---

## 📁 통합 데이터베이스

### 🎯 단위사업별 WBS
- **데이터베이스 ID**: `2a250aa9577d80ca8bf2f2abfce71a59`
- **설명**: 16개 단위사업 기술 구축 업무
- **Notion 링크**: [단위사업별 WBS 열기](https://www.notion.so/2a250aa9577d80ca8bf2f2abfce71a59)

**16개 단위사업:**
1. 디지털 OASIS SPOT 구축
2. 모바일 전자시민증
3. 수요응답형 모빌리티
4. 스마트폴&디스플레이
5. 무인매장
6. 스마트 공공 WiFi
7. 디지털 노마드 접수/운영/거래 관리 플랫폼 구축
8. AI시티관제 플랫폼 구축
9. 정보관리 서비스(데이터허브)
10. 이노베이션 센터 인테리어 실시설계 및 시공
11. 데이터 기반 AI 융복합 SW개발 플랫폼
12. SDDC 기반 HW 인프라 구축
13. 메타버스 플랫폼
14. 시설물위치기반서비스플랫폼
15. RFP 문서작성
16. WBS

### ✒️ 사업관리 WBS
- **데이터베이스 ID**: `21650aa9577d81e18ac1cedb07eea8bb`
- **설명**: 사업 홍보, 보고, 감사, 현장점검 등 관리업무
- **Notion 링크**: [사업관리 WBS 열기](https://www.notion.so/21650aa9577d81e18ac1cedb07eea8bb)

**주요 관리 영역:**
- 정기/비정기 보고
- 사업 홍보 및 마케팅
- 국토부 현장점검
- 외부감사
- 기타사업

---

## 🚀 배포 가이드

### 1. GitHub 저장소 설정

```bash
git clone https://github.com/LEESUNGHO-AI/Asan-Smartcity-WBS.git
cd Asan-Smartcity-WBS

# 기존 파일 백업 후 새 파일로 교체
# 또는 새 저장소에 푸시
git init
git add .
git commit -m "🚀 통합 WBS 대시보드 v2.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/asan-wbs-integrated.git
git push -u origin main
```

### 2. Notion API 설정

1. [Notion Developers](https://developers.notion.com/) 접속
2. 새 통합(Integration) 생성
3. Internal Integration Token 복사
4. **두 개의 데이터베이스 모두** 통합 연결:
   - 🎯 단위사업별 WBS → 우측 상단 `...` → `연결 추가` → 생성한 통합 선택
   - ✒️ 사업관리 WBS → 우측 상단 `...` → `연결 추가` → 생성한 통합 선택

### 3. GitHub Secrets 설정

1. GitHub 저장소 → `Settings` → `Secrets and variables` → `Actions`
2. `New repository secret` 클릭
3. Name: `NOTION_API_KEY`
4. Value: 노션 통합 API 키 입력

### 4. GitHub Pages 활성화

1. `Settings` → `Pages`
2. Source: `GitHub Actions` 선택

### 5. 워크플로우 실행

1. `Actions` 탭 → `Sync Integrated WBS Data`
2. `Run workflow` 클릭
3. 이후 자동 동기화:
   - 매일 KST 09:00, 14:00, 18:00

---

## 📂 프로젝트 구조

```
asan-wbs-integrated/
├── index.html                    # 통합 대시보드 메인 페이지
├── sync_notion.py                # Notion 동기화 스크립트
├── data/
│   └── wbs-data.json            # 동기화된 통합 WBS 데이터
├── .github/
│   └── workflows/
│       └── sync.yml             # GitHub Actions 워크플로우
└── README.md                     # 프로젝트 설명서
```

---

## ⚙️ 동기화 주기 변경

`.github/workflows/sync.yml`에서 cron 표현식 수정:

```yaml
schedule:
  # 현재: 매일 KST 09:00, 14:00, 18:00
  - cron: '0 0,5,9 * * *'
  
  # 예시: 매시간 동기화
  # - cron: '0 * * * *'
  
  # 예시: 평일 매 2시간마다
  # - cron: '0 */2 * * 1-5'
```

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript, Chart.js 4.x |
| **Backend** | Python 3.11, Notion API (2022-06-28) |
| **CI/CD** | GitHub Actions |
| **Hosting** | GitHub Pages |

---

## 📋 데이터 구조

### JSON 스키마 (data/wbs-data.json)

```json
{
  "metadata": {
    "synced_at": "ISO-8601 동기화 시간",
    "total_items": "총 항목 수",
    "databases": {
      "unit_project": { "id", "name", "description", "icon", "url" },
      "management": { "id", "name", "description", "icon", "url" }
    }
  },
  "statistics": {
    "combined": { /* 통합 통계 */ },
    "unit_project": { /* 단위사업별 통계 */ },
    "management": { /* 사업관리 통계 */ }
  },
  "items": {
    "all": [ /* 전체 항목 */ ],
    "unit_project": [ /* 단위사업별 항목 */ ],
    "management": [ /* 사업관리 항목 */ ]
  }
}
```

### 항목 속성

| 속성 | 설명 |
|------|------|
| `wbs_type` | WBS 유형 (unit_project / management) |
| `title` | 업무 항목명 |
| `area` | 업무 영역 |
| `status` | 진행현황 |
| `status_group` | 상태 그룹 (to_do / in_progress / complete) |
| `priority` | 우선순위 (P0~P3) |
| `assignees` | 담당자 목록 |
| `progress` | 진척률 (%) |
| `phase` | 사업단계 |
| `dates` | 시작일, 마감일, 예상완료, 실제완료 |

---

## 👥 담당자

| 이름 | 역할 |
|------|------|
| 이성호 | 기술/인프라 |
| 함정영 | 조달/입찰 |
| 임혁 | 계약/행정 |
| 김주용 | PM |

---

## 📞 문의

- **Notion 프로젝트 관리**: [프로젝트와 작업](https://www.notion.so/2aa50aa9577d80c4915ef7d62b966de4)
- **상위 프로젝트**: [아산시 강소형 스마트시티 구축사업 프로젝트 관리](https://www.notion.so/21650aa9577d80dc8278e0187c54677f)

---

© 2024 제일엔지니어링. 아산 컴팩트 스마트시티 조성사업.
