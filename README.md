# 🏗️ 아산 스마트시티 통합 WBS 대시보드

아산 컴팩트 스마트시티 조성사업의 **단위사업별 WBS**와 **사업관리 WBS**를 통합하여 **실시간 자동 동기화**하는 대시보드입니다.

[![Sync Status](https://github.com/LEESUNGHO-AI/Asan-Smartcity-WBS/actions/workflows/sync.yml/badge.svg)](https://github.com/LEESUNGHO-AI/Asan-Smartcity-WBS/actions/workflows/sync.yml)

---

## ⚡ 주요 특징

| 기능 | 설명 |
|------|------|
| 🔄 **15분 자동 동기화** | Notion 데이터 변경 시 15분 이내 자동 반영 |
| 📊 **스마트 업데이트** | 변경사항이 있을 때만 배포 (불필요한 배포 방지) |
| 🎯 **통합 대시보드** | 단위사업별 + 사업관리 WBS 한 화면에서 관리 |
| 📈 **실시간 KPI** | 진척률, 상태별 현황, 담당자별 업무 시각화 |

---

## 🚀 5분 완료 설정 가이드

### 📋 사전 준비

- [x] GitHub 계정
- [x] Notion 워크스페이스 접근 권한
- [x] 두 개의 WBS 데이터베이스 접근 권한

---

### 1단계: Notion 통합(Integration) 생성 (2분)

1. **[Notion Developers](https://developers.notion.com/)** 접속
2. **"New integration"** 클릭
3. 설정:
   - Name: `WBS Dashboard`
   - Associated workspace: 본인 워크스페이스 선택
   - Capabilities: **Read content** 체크
4. **"Submit"** 클릭
5. **"Internal Integration Secret"** 복사 (나중에 사용)

```
secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 2단계: Notion 데이터베이스 연결 (1분)

**두 개의 데이터베이스 모두** 통합을 연결해야 합니다:

#### 🎯 단위사업별 WBS 연결
1. [단위사업별 WBS](https://www.notion.so/2a250aa9577d80ca8bf2f2abfce71a59) 열기
2. 우측 상단 `...` 클릭
3. `연결 추가` 클릭
4. `WBS Dashboard` 선택

#### ✒️ 사업관리 WBS 연결
1. [사업관리 WBS](https://www.notion.so/21650aa9577d81e18ac1cedb07eea8bb) 열기
2. 우측 상단 `...` 클릭
3. `연결 추가` 클릭
4. `WBS Dashboard` 선택

---

### 3단계: GitHub 저장소 설정 (1분)

#### 방법 A: 기존 저장소 업데이트 (권장)

```bash
# 기존 저장소 클론
git clone https://github.com/LEESUNGHO-AI/Asan-Smartcity-WBS.git
cd Asan-Smartcity-WBS

# 새 파일 다운로드 및 압축 해제 후 복사
# (다운로드 받은 asan-wbs-integrated.zip 압축 해제)
cp -r [압축해제경로]/* .
cp -r [압축해제경로]/.github .

# 커밋 및 푸시
git add .
git commit -m "🚀 통합 WBS 대시보드 v2.0 업그레이드"
git push origin main
```

#### 방법 B: 새 저장소 생성

```bash
# 압축 해제 후 해당 폴더에서
cd asan-wbs-integrated

git init
git add .
git commit -m "🚀 통합 WBS 대시보드 초기 설정"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

---

### 4단계: GitHub Secrets 설정 (30초)

1. GitHub 저장소 → **Settings** 탭
2. 좌측 메뉴: **Secrets and variables** → **Actions**
3. **"New repository secret"** 클릭
4. 입력:
   - **Name**: `NOTION_API_KEY`
   - **Secret**: 1단계에서 복사한 API 키
5. **"Add secret"** 클릭

---

### 5단계: GitHub Pages 활성화 (30초)

1. GitHub 저장소 → **Settings** 탭
2. 좌측 메뉴: **Pages**
3. **Source**: `GitHub Actions` 선택
4. 저장 (자동)

---

### 6단계: 첫 동기화 실행 (자동)

1. GitHub 저장소 → **Actions** 탭
2. **"🔄 Auto Sync Notion WBS"** 클릭
3. **"Run workflow"** → **"Run workflow"** 클릭
4. 1-2분 후 완료!

**🎉 대시보드 URL:**
```
https://YOUR_USERNAME.github.io/YOUR_REPO/
```

---

## 📂 프로젝트 구조

```
📁 asan-wbs-integrated/
├── 📄 index.html              # 통합 대시보드 (탭 기반 UI)
├── 🐍 sync_notion.py          # 자동 동기화 스크립트
├── 🛠️ setup.sh                # 초기 설정 스크립트
├── 📁 data/
│   ├── 📊 wbs-data.json       # 동기화된 WBS 데이터
│   └── 🔒 .sync-hash          # 변경 감지용 해시
├── 📁 .github/
│   └── 📁 workflows/
│       └── ⚙️ sync.yml        # 15분 자동 동기화 워크플로우
└── 📖 README.md               # 이 문서
```

---

## ⚙️ 동기화 설정

### 자동 동기화 주기

| 기본값 | 설명 |
|--------|------|
| **15분** | `*/15 * * * *` - Notion 변경 후 최대 15분 내 반영 |

### 주기 변경 방법

`.github/workflows/sync.yml` 수정:

```yaml
schedule:
  # 15분마다 (기본값)
  - cron: '*/15 * * * *'
  
  # 30분마다
  # - cron: '*/30 * * * *'
  
  # 매시간
  # - cron: '0 * * * *'
  
  # 매일 오전 9시 (KST)
  # - cron: '0 0 * * *'
```

### 수동 동기화

1. GitHub → **Actions** 탭
2. **"🔄 Auto Sync Notion WBS"** 선택
3. **"Run workflow"** 클릭

---

## 📊 통합 데이터베이스

### 🎯 단위사업별 WBS
- **ID**: `2a250aa9577d80ca8bf2f2abfce71a59`
- **설명**: 16개 단위사업 기술 구축 업무
- **[Notion 열기](https://www.notion.so/2a250aa9577d80ca8bf2f2abfce71a59)**

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
- **ID**: `21650aa9577d81e18ac1cedb07eea8bb`
- **설명**: 사업 홍보, 보고, 감사, 현장점검 등 관리업무
- **[Notion 열기](https://www.notion.so/21650aa9577d81e18ac1cedb07eea8bb)**

**주요 관리 영역:**
- 정기/비정기 보고
- 사업 홍보 및 마케팅
- 국토부 현장점검
- 외부감사
- 기타사업

---

## 🔧 문제 해결

### ❌ "NOTION_API_KEY 환경변수가 설정되지 않았습니다"

**원인**: GitHub Secrets에 API 키가 없음

**해결**:
1. Settings → Secrets and variables → Actions
2. `NOTION_API_KEY` 시크릿 추가

---

### ❌ "데이터베이스를 찾을 수 없습니다"

**원인**: Notion 통합이 데이터베이스에 연결되지 않음

**해결**:
1. Notion에서 해당 데이터베이스 열기
2. 우측 상단 `...` → `연결 추가`
3. 생성한 통합 선택

---

### ❌ 동기화는 되지만 대시보드가 안 보임

**원인**: GitHub Pages 미활성화

**해결**:
1. Settings → Pages
2. Source: `GitHub Actions` 선택

---

### ❌ 변경사항이 반영되지 않음

**원인**: 캐시 또는 동기화 지연

**해결**:
1. 브라우저 캐시 삭제 (Ctrl+Shift+R)
2. Actions에서 수동 워크플로우 실행
3. 15분 대기 (다음 자동 동기화)

---

## 👥 담당자

| 이름 | 역할 | 연락처 |
|------|------|--------|
| 이성호 | 기술/인프라 | airlan506@icloud.com |
| 함정영 | 조달/입찰 | james943@naver.com |
| 임혁 | 계약/행정 | lhacc8856@gmail.com |
| 김주용 | PM | fbimpa@naver.com |

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript, Chart.js 4.x |
| **Backend** | Python 3.11, Notion API (2022-06-28) |
| **CI/CD** | GitHub Actions (15분 cron) |
| **Hosting** | GitHub Pages |

---

## 📞 문의

- **프로젝트 관리**: [프로젝트와 작업](https://www.notion.so/2aa50aa9577d80c4915ef7d62b966de4)
- **상위 프로젝트**: [아산시 강소형 스마트시티 구축사업](https://www.notion.so/21650aa9577d80dc8278e0187c54677f)

---

© 2024 제일엔지니어링. 아산 컴팩트 스마트시티 조성사업.
