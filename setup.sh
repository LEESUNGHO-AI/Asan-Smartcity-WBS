#!/bin/bash
# ============================================================
# 🚀 아산 스마트시티 통합 WBS 대시보드 초기 설정 스크립트
# ============================================================
# 사용법: bash setup.sh
# ============================================================

set -e

echo "============================================================"
echo "🏗️ 아산 스마트시티 통합 WBS 대시보드 설정"
echo "============================================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 성공 메시지
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 함수: 경고 메시지
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 함수: 오류 메시지
error() {
    echo -e "${RED}❌ $1${NC}"
}

# 함수: 정보 메시지
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================
# 1. Git 확인
# ============================================================
echo "📋 1단계: 환경 확인"
echo "------------------------------------------------------------"

if ! command -v git &> /dev/null; then
    error "Git이 설치되어 있지 않습니다."
    echo "   설치 방법: https://git-scm.com/downloads"
    exit 1
fi
success "Git 설치됨: $(git --version)"

if ! command -v python3 &> /dev/null; then
    warning "Python3이 설치되어 있지 않습니다. (로컬 테스트 시 필요)"
else
    success "Python 설치됨: $(python3 --version)"
fi

echo ""

# ============================================================
# 2. 저장소 확인
# ============================================================
echo "📋 2단계: 저장소 확인"
echo "------------------------------------------------------------"

if [ ! -d ".git" ]; then
    warning "Git 저장소가 아닙니다. 초기화합니다..."
    git init
    success "Git 저장소 초기화 완료"
fi

# 원격 저장소 확인
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    warning "원격 저장소가 설정되지 않았습니다."
    echo ""
    read -p "GitHub 저장소 URL을 입력하세요 (예: https://github.com/username/repo.git): " REMOTE_URL
    if [ -n "$REMOTE_URL" ]; then
        git remote add origin "$REMOTE_URL"
        success "원격 저장소 설정 완료: $REMOTE_URL"
    fi
else
    success "원격 저장소: $REMOTE_URL"
fi

echo ""

# ============================================================
# 3. 필수 파일 확인
# ============================================================
echo "📋 3단계: 필수 파일 확인"
echo "------------------------------------------------------------"

REQUIRED_FILES=(
    "index.html"
    "sync_notion.py"
    ".github/workflows/sync.yml"
    "data/wbs-data.json"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "$file 존재"
    else
        MISSING_FILES+=("$file")
        error "$file 없음"
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    error "필수 파일이 누락되었습니다!"
    echo "   다운로드 받은 ZIP 파일의 내용을 이 디렉토리에 복사하세요."
    exit 1
fi

echo ""

# ============================================================
# 4. Notion API 키 테스트 (선택사항)
# ============================================================
echo "📋 4단계: Notion API 연결 테스트 (선택사항)"
echo "------------------------------------------------------------"

read -p "Notion API 키로 연결 테스트를 하시겠습니까? (y/n): " TEST_API
if [ "$TEST_API" = "y" ] || [ "$TEST_API" = "Y" ]; then
    read -sp "Notion API 키를 입력하세요: " NOTION_API_KEY
    echo ""
    
    if [ -n "$NOTION_API_KEY" ]; then
        echo "🔄 데이터베이스 연결 테스트 중..."
        
        # 단위사업별 WBS 테스트
        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $NOTION_API_KEY" \
            -H "Notion-Version: 2022-06-28" \
            "https://api.notion.com/v1/databases/2a250aa9577d80ca8bf2f2abfce71a59")
        
        if [ "$RESPONSE" = "200" ]; then
            success "🎯 단위사업별 WBS: 연결 성공"
        else
            error "🎯 단위사업별 WBS: 연결 실패 (HTTP $RESPONSE)"
            echo "   → Notion에서 데이터베이스에 통합(Integration)을 연결하세요"
        fi
        
        # 사업관리 WBS 테스트
        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $NOTION_API_KEY" \
            -H "Notion-Version: 2022-06-28" \
            "https://api.notion.com/v1/databases/21650aa9577d81e18ac1cedb07eea8bb")
        
        if [ "$RESPONSE" = "200" ]; then
            success "✒️ 사업관리 WBS: 연결 성공"
        else
            error "✒️ 사업관리 WBS: 연결 실패 (HTTP $RESPONSE)"
            echo "   → Notion에서 데이터베이스에 통합(Integration)을 연결하세요"
        fi
    fi
else
    info "API 테스트 건너뜀"
fi

echo ""

# ============================================================
# 5. 커밋 및 푸시
# ============================================================
echo "📋 5단계: Git 커밋 및 푸시"
echo "------------------------------------------------------------"

read -p "모든 파일을 커밋하고 푸시하시겠습니까? (y/n): " DO_PUSH
if [ "$DO_PUSH" = "y" ] || [ "$DO_PUSH" = "Y" ]; then
    git add .
    git commit -m "🚀 통합 WBS 대시보드 v2.0 설정" -m "- 단위사업별 WBS + 사업관리 WBS 통합" -m "- 15분마다 자동 동기화" || true
    
    # 브랜치 확인
    BRANCH=$(git branch --show-current)
    if [ -z "$BRANCH" ]; then
        git branch -M main
        BRANCH="main"
    fi
    
    git push -u origin "$BRANCH"
    success "푸시 완료!"
else
    info "푸시 건너뜀"
fi

echo ""

# ============================================================
# 6. 다음 단계 안내
# ============================================================
echo "============================================================"
echo "🎉 설정 완료!"
echo "============================================================"
echo ""
echo "📌 다음 단계를 완료하세요:"
echo ""
echo "1️⃣  GitHub Secrets 설정"
echo "   → 저장소 Settings → Secrets and variables → Actions"
echo "   → New repository secret"
echo "   → Name: NOTION_API_KEY"
echo "   → Value: 노션 통합 API 키"
echo ""
echo "2️⃣  GitHub Pages 활성화"
echo "   → 저장소 Settings → Pages"
echo "   → Source: GitHub Actions 선택"
echo ""
echo "3️⃣  Notion 통합 연결 (아직 안 했다면)"
echo "   → 🎯 단위사업별 WBS 열기 → ... → 연결 추가 → 통합 선택"
echo "   → ✒️ 사업관리 WBS 열기 → ... → 연결 추가 → 통합 선택"
echo ""
echo "4️⃣  워크플로우 수동 실행"
echo "   → 저장소 Actions 탭 → Auto Sync Notion WBS → Run workflow"
echo ""
echo "📊 대시보드 URL (배포 후):"
if [ -n "$REMOTE_URL" ]; then
    # GitHub URL에서 Pages URL 추출
    REPO_PATH=$(echo "$REMOTE_URL" | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com[:/]\(.*\)/\1/')
    USERNAME=$(echo "$REPO_PATH" | cut -d'/' -f1)
    REPONAME=$(echo "$REPO_PATH" | cut -d'/' -f2)
    echo "   https://${USERNAME}.github.io/${REPONAME}/"
fi
echo ""
echo "============================================================"
