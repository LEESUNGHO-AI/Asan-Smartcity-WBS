# 아산시 강소형 스마트시티 WBS 2026 대시보드

Notion 데이터베이스와 자동 동기화되는 WBS 대시보드입니다.

## 📋 주요 기능

- **Notion 자동 동기화**: 매일 오전 6시 (KST) GitHub Actions를 통해 자동 동기화
- **3개의 탭 구성**: 통합 현황, 단위사업별 WBS, 사업관리 WBS
- **실시간 필터링**: WBS 코드, 상태, Level별 검색 및 필터
- **시각화 차트**: 진척률, 담당기관별 업무 현황 등

## 🚀 설정 방법

### 1. GitHub Repository 설정

1. 이 폴더의 모든 파일을 GitHub Repository에 업로드합니다.
   ```
   ├── index.html
   ├── data/
   │   └── wbs-data.json
   ├── scripts/
   │   └── sync_notion.py
   └── .github/
       └── workflows/
           └── sync-notion.yml
   ```

2. **GitHub Pages 활성화**:
   - Repository > Settings > Pages
   - Source: `Deploy from a branch`
   - Branch: `main` / `/ (root)`
   - Save

### 2. Notion Integration 설정

1. [Notion Integrations](https://www.notion.so/my-integrations) 접속

2. **새 Integration 생성**:
   - Name: `WBS Dashboard Sync`
   - Associated workspace: 작업공간 선택
   - Capabilities: `Read content` 체크

3. **Integration Token 복사**:
   - Internal Integration Token 복사 (secret_xxx... 형식)

4. **데이터베이스 연결**:
   - Notion에서 WBS 2026 데이터베이스 열기
   - 우측 상단 `...` > `Connections` > `WBS Dashboard Sync` 추가

### 3. GitHub Secrets 설정

1. Repository > Settings > Secrets and variables > Actions

2. **New repository secret** 클릭:
   - Name: `NOTION_API_KEY`
   - Value: 복사한 Integration Token 붙여넣기

### 4. 수동 동기화 테스트

1. Repository > Actions > `Sync Notion WBS Data`
2. `Run workflow` 클릭
3. 실행 완료 후 `data/wbs-data.json` 파일 업데이트 확인

## 📁 파일 구조

```
asan-wbs-dashboard/
├── index.html              # 대시보드 메인 페이지
├── data/
│   └── wbs-data.json       # WBS 데이터 (자동 생성)
├── scripts/
│   └── sync_notion.py      # Notion 동기화 스크립트
├── .github/
│   └── workflows/
│       └── sync-notion.yml # GitHub Actions 워크플로우
└── README.md               # 이 파일
```

## ⏰ 자동 동기화 스케줄

- **매일 오전 6시 (KST)** 자동 실행
- 수동 실행: Actions > `Run workflow`
- `scripts/sync_notion.py` 또는 `.github/workflows/sync-notion.yml` 변경 시 자동 실행

## 🔧 커스터마이징

### 데이터베이스 ID 변경

`scripts/sync_notion.py` 파일에서:
```python
DATABASE_ID = '0ed4b202-7037-400e-96f3-9e3455ba63cd'  # 새 데이터베이스 ID로 변경
```

### 동기화 시간 변경

`.github/workflows/sync-notion.yml` 파일에서:
```yaml
schedule:
  - cron: '0 21 * * *'  # UTC 21:00 = KST 06:00
  # 예: '0 0 * * *'   = KST 09:00
  # 예: '0 9 * * *'   = KST 18:00
```

## 📊 Notion 데이터베이스 스키마

| 속성명 | 타입 | 설명 |
|--------|------|------|
| Name | Title | 작업 이름 (예: [1.1] 킥오프/착수회의) |
| 작업명 | Text | WBS 코드 (예: 1.1) |
| Level | Select | 작업 수준 (1, 2, 3) |
| 대분류 | Select | 대분류 카테고리 |
| 중분류 | Text | 중분류 상세 |
| 담당기관 | Select | 담당 기관 |
| 담당R | Text | 담당자 |
| 계획공정률 | Number | 계획 진척률 (0~1) |
| 실적공정률 | Number | 실적 진척률 (0~1) |
| 진척차 | Number | 차이 (실적-계획) |
| 가중치 | Number | 작업 가중치 |
| 시작일 | Date | 시작 날짜 |
| 종료일 | Date | 종료 날짜 |

## 🔗 관련 링크

- **Notion WBS 2026**: https://www.notion.so/559654aed9404d9f88225ea0adc7d746
- **GitHub Pages**: https://leesungho-ai.github.io/Asan-Smartcity-WBS/

## 📝 라이선스

© 2025 제일엔지니어링. 아산시 강소형 스마트시티 조성사업
