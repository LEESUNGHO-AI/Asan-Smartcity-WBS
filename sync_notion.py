#!/usr/bin/env python3
"""
sync_notion.py — 아산시 강소형 스마트시티 WBS 2026
Notion DB → data/wbs-data.json 동기화 스크립트

Notion DB ID : 559654aed9404d9f88225ea0adc7d746
출력 경로    : data/wbs-data.json
사용 라이브러리: 표준 라이브러리만 (urllib, json, os, datetime)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# ── 설정 ─────────────────────────────────────────────────────────────────────
NOTION_DB_ID  = "559654aed9404d9f88225ea0adc7d746"
OUTPUT_PATH   = "data/wbs-data.json"
NOTION_VER    = "2022-06-28"
PAGE_SIZE     = 100          # Notion API 최대값
MAX_RETRIES   = 3
RETRY_DELAY   = 3            # seconds

KST = timezone(timedelta(hours=9))

# ── Notion API 헬퍼 ───────────────────────────────────────────────────────────
def get_api_key() -> str:
    key = os.environ.get("NOTION_API_KEY", "").strip()
    if not key:
        print("❌ NOTION_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    return key


def notion_request(method: str, path: str, body: dict | None = None) -> dict:
    """Notion API 요청 (재시도 포함)"""
    api_key = get_api_key()
    url = f"https://api.notion.com/v1{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VER,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            if e.code == 429:          # rate limit
                wait = RETRY_DELAY * attempt
                print(f"⚠️  Rate limit — {wait}초 대기 후 재시도 ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
            elif e.code >= 500:
                print(f"⚠️  서버 오류 {e.code} — 재시도 ({attempt}/{MAX_RETRIES}): {body_text[:200]}")
                time.sleep(RETRY_DELAY)
            else:
                print(f"❌ HTTP {e.code}: {body_text[:500]}", file=sys.stderr)
                raise
        except Exception as e:
            print(f"⚠️  요청 오류 — 재시도 ({attempt}/{MAX_RETRIES}): {e}")
            time.sleep(RETRY_DELAY)

    raise RuntimeError(f"Notion API 요청 실패 (최대 재시도 초과): {path}")


# ── Notion 페이지 전체 조회 ────────────────────────────────────────────────────
def fetch_all_pages() -> list[dict]:
    """DB의 모든 페이지를 페이지네이션으로 수집"""
    pages = []
    cursor = None

    while True:
        body: dict = {"page_size": PAGE_SIZE}
        if cursor:
            body["start_cursor"] = cursor

        result = notion_request("POST", f"/databases/{NOTION_DB_ID}/query", body)
        pages.extend(result.get("results", []))

        if result.get("has_more") and result.get("next_cursor"):
            cursor = result["next_cursor"]
            time.sleep(0.3)   # 요청 간격
        else:
            break

    return pages


# ── 속성값 추출 헬퍼 ──────────────────────────────────────────────────────────
def prop(page: dict, name: str) -> dict:
    return page.get("properties", {}).get(name, {})


def get_title(page: dict) -> str:
    t = prop(page, "Name").get("title", [])
    return "".join(r.get("plain_text", "") for r in t).strip()


def get_text(page: dict, name: str) -> str:
    rich = prop(page, name).get("rich_text", [])
    return "".join(r.get("plain_text", "") for r in rich).strip()


def get_select(page: dict, name: str) -> str:
    s = prop(page, name).get("select")
    return s["name"] if s else ""


def get_number(page: dict, name: str) -> float | None:
    v = prop(page, name).get("number")
    return v  # None 유지


def get_date_start(page: dict, name: str) -> str:
    d = prop(page, name).get("date")
    return d["start"] if d else ""


# ── 공정률 변환 ───────────────────────────────────────────────────────────────
def pct_to_display(value: float | None) -> float | None:
    """Notion percent 필드(0.0~1.0) → 표시용 %(0~100)"""
    if value is None:
        return None
    # 이미 0~1 범위면 ×100, 이미 0~100이면 그대로
    if 0.0 <= value <= 1.0:
        return round(value * 100, 1)
    return round(value, 1)


# ── 페이지 → 아이템 변환 ──────────────────────────────────────────────────────
def page_to_item(page: dict) -> dict:
    name_full = get_title(page)

    # WBS ID 추출 — "[1.2] 작업명" 패턴에서 "1.2" 추출
    wbs_id = ""
    task_name = name_full
    if name_full.startswith("[") and "]" in name_full:
        bracket_end = name_full.index("]")
        wbs_id = name_full[1:bracket_end].strip()
        task_name = name_full[bracket_end + 1:].strip()

    # 공정률 (Notion에서 0.0~1.0 또는 0~100 혼재 가능)
    planned_raw  = get_number(page, "계획공정률")
    actual_raw   = get_number(page, "실적공정률")
    progress_raw = get_number(page, "진행률")
    deviation_raw= get_number(page, "진척차")

    planned  = pct_to_display(planned_raw)
    actual   = pct_to_display(actual_raw)
    progress = pct_to_display(progress_raw)
    deviation= pct_to_display(deviation_raw)

    # 상태 결정
    status = get_select(page, "상태") if get_select(page, "상태") else _infer_status(actual, planned)

    return {
        "id":           wbs_id or get_text(page, "작업명") or name_full,
        "name":         name_full,
        "level":        get_select(page, "Level"),
        "category":     get_select(page, "대분류"),
        "subCategory":  get_text(page, "중분류"),
        "organization": get_select(page, "담당기관"),
        "manager":      get_text(page, "담당R"),
        "collaborator": get_text(page, "협업C"),
        "startDate":    get_date_start(page, "시작일"),
        "endDate":      get_date_start(page, "종료일"),
        "duration":     get_number(page, "기간"),
        "weight":       get_number(page, "가중치"),
        "plannedRate":  planned,
        "actualRate":   actual,
        "progressRate": progress,
        "deviation":    deviation,
        "budget":       get_number(page, "예산"),
        "predecessor":  get_text(page, "선행작업"),
        "deliverable":  get_text(page, "산출물"),
        "evidence":     get_text(page, "근거자료"),
        "note":         get_text(page, "비고"),
        "status":       status,
    }


def _infer_status(actual: float | None, planned: float | None) -> str:
    """공정률 기반 상태 추론"""
    if actual is None:
        return "대기"
    if actual >= 100:
        return "완료"
    if actual > 0:
        if planned is not None and (planned - actual) >= 5:
            return "지연"
        return "진행중"
    return "대기"


# ── 유효 카테고리 판별 ─────────────────────────────────────────────────────────
VALID_CATEGORIES = {
    "사업총괄", "프로젝트 관리/거버넌스", "실시설계",
    "나라장터 발주 지원", "서비스 구축", "통합시험/시범운영",
    "준공/검수/이관", "운영(3년)", "마일스톤"
}

def is_valid_category(cat: str) -> bool:
    return cat in VALID_CATEGORIES


# ── 집계 계산 ──────────────────────────────────────────────────────────────────
def compute_summary(items: list[dict]) -> dict:
    valid = [i for i in items if i["actualRate"] is not None]
    total  = len(items)
    done   = sum(1 for i in items if (i["actualRate"] or 0) >= 100)
    in_prog= sum(1 for i in items if 0 < (i["actualRate"] or 0) < 100)

    avg_actual = round(sum(i["actualRate"] for i in valid) / len(valid), 1) if valid else 0
    avg_plan   = round(sum(i["plannedRate"] for i in valid if i["plannedRate"] is not None) /
                       max(1, sum(1 for i in valid if i["plannedRate"] is not None)), 1)
    avg_dev    = round(sum(i["deviation"]   for i in valid if i["deviation"]   is not None) /
                       max(1, sum(1 for i in valid if i["deviation"]   is not None)), 1)

    # 대분류별 집계 (유효 카테고리만)
    by_cat: dict[str, dict] = {}
    for i in items:
        cat = i["category"]
        if not is_valid_category(cat):
            continue
        if cat not in by_cat:
            by_cat[cat] = {"total": 0, "done": 0, "avgActual": 0, "_sum": 0, "_n": 0}
        by_cat[cat]["total"] += 1
        if (i["actualRate"] or 0) >= 100:
            by_cat[cat]["done"] += 1
        if i["actualRate"] is not None:
            by_cat[cat]["_sum"] += i["actualRate"]
            by_cat[cat]["_n"]   += 1
    for cat in by_cat:
        n = by_cat[cat]["_n"]
        by_cat[cat]["avgActual"] = round(by_cat[cat]["_sum"] / n, 1) if n else 0
        del by_cat[cat]["_sum"]
        del by_cat[cat]["_n"]

    # 기관별 집계
    by_org: dict[str, dict] = {}
    VALID_ORGS = {"제일엔지니어링", "아산시", "호서대", "충남연구원", "KAIST"}
    for i in items:
        org = i["organization"]
        if org not in VALID_ORGS:
            continue
        if org not in by_org:
            by_org[org] = {"total": 0, "done": 0}
        by_org[org]["total"] += 1
        if (i["actualRate"] or 0) >= 100:
            by_org[org]["done"] += 1

    return {
        "total":     total,
        "done":      done,
        "inProg":    in_prog,
        "avgPlan":   avg_plan,
        "avgActual": avg_actual,
        "avgDev":    avg_dev,
        "byCategory": by_cat,
        "byOrg":      by_org,
    }


# ── 오염 항목 필터 ─────────────────────────────────────────────────────────────
def is_garbage_item(item: dict) -> bool:
    """실제 WBS 항목이 아닌 오염 레코드 제거"""
    name = item["name"]
    # WBS ID 패턴 없이 너무 긴 제목이거나 숫자만인 경우
    if not name:
        return True
    if not name.startswith("["):
        # "노션 실시간 분석..." 같은 시스템 레코드
        if any(k in name for k in ["노션", "Claude", "대시보드", "수정", "분석"]):
            return True
    return False


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc.astimezone(KST)
    kst_str = now_kst.strftime("%Y-%m-%d %H:%M KST")

    print(f"🔄 Notion DB 동기화 시작 — {kst_str}")
    print(f"   DB ID: {NOTION_DB_ID}")

    # 1) 전체 페이지 조회
    print("📥 Notion 페이지 조회 중...")
    pages = fetch_all_pages()
    print(f"   총 {len(pages)}건 조회됨")

    # 2) 변환
    items = []
    for p in pages:
        try:
            item = page_to_item(p)
            if not is_garbage_item(item):
                items.append(item)
        except Exception as e:
            print(f"⚠️  변환 오류 (page {p.get('id', '?')}): {e}")

    print(f"   유효 항목: {len(items)}건")

    # 3) 집계
    summary = compute_summary(items)
    print(f"   완료: {summary['done']}건 | 진행중: {summary['inProg']}건")
    print(f"   평균 실적공정률: {summary['avgActual']}% | 계획: {summary['avgPlan']}%")

    # 4) 출력
    output = {
        "meta": {
            "generatedAt":    now_utc.isoformat(),
            "generatedAtKst": kst_str,
            "source":         "Notion WBS 2026 DB",
            "dbId":           NOTION_DB_ID,
            "totalRecords":   len(items),
        },
        "summary": summary,
        "items":   items,
    }

    # data/ 디렉토리 생성
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"✅ 저장 완료: {OUTPUT_PATH} ({size_kb:.1f} KB)")
    print(f"   총 항목: {len(items)}건 | 생성 시각: {kst_str}")


if __name__ == "__main__":
    main()
