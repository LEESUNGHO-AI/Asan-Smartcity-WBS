#!/usr/bin/env python3
"""
sync_notion.py v4.3
====================================================
아산시 강소형 스마트시티 WBS 대시보드 데이터 생성기

[v4.2 → v4.3 변경사항]
- 총괄표 DB (ba6685cb0690464ea8da4d5cd04cc167) 추가 조회
- data/summary-data.json 생성 (종합현황 탭용)
- 총괄표 DB가 비어있으면 wbs-data.json 집계로 폴백

[GitHub Actions에서 실행]
NOTION_API_KEY 환경변수 필요
====================================================
"""

import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from collections import defaultdict

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
WBS_DB_ID      = "559654aed9404d9f88225ea0adc7d746"
SUMMARY_DB_ID  = "ba6685cb0690464ea8da4d5cd04cc167"
WBS_OUTPUT     = "data/wbs-data.json"
SUMMARY_OUTPUT = "data/summary-data.json"
KST            = timezone(timedelta(hours=9))

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

WBS_CAT_MAP = {
    "1":"사업총괄","2":"프로젝트 관리/거버넌스","3":"나라장터 발주 지원",
    "4":"서비스 구축","5":"통합시험/시범운영",
    "6":"준공/검수/이관","7":"준공/검수/이관","8":"준공/검수/이관",
    "9":"운영(3년)",
}

# ── API 공통 ──────────────────────────────────────────────────────
def notion_post(path, body, retry=3):
    url  = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode()
    for attempt in range(retry):
        try:
            req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            if e.code == 429:
                wait = 3 * (attempt + 1)
                print(f"  Rate limit → {wait}초 대기", flush=True)
                time.sleep(wait)
            elif attempt == retry - 1:
                print(f"  HTTPError {e.code}: {err[:200]}", flush=True)
                raise
            else:
                time.sleep(2)
        except Exception:
            if attempt == retry - 1: raise
            time.sleep(2)
    return {}

def fetch_all(db_id):
    results, cursor, page = [], None, 1
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        resp = notion_post(f"/databases/{db_id}/query", body)
        results.extend(resp.get("results", []))
        print(f"  {page}페이지 ({len(results)}건)", flush=True)
        if not resp.get("has_more"): break
        cursor = resp.get("next_cursor")
        page  += 1
        time.sleep(0.3)
    return results

# ── 값 추출 ──────────────────────────────────────────────────────
def txt(prop):
    arr = prop.get("rich_text") or prop.get("title") or []
    return "".join(b.get("plain_text","") for b in arr).strip()

def num(prop):
    return prop.get("number") or 0.0

def sel(prop):
    s = prop.get("select")
    return s["name"] if s else ""

def dt(prop):
    d = prop.get("date")
    return d["start"][:10] if d and d.get("start") else ""

def infer_level(wbs_id, lv):
    lv = str(lv or "").strip()
    if lv in ("1","2","3"): return lv
    if not wbs_id: return ""
    if wbs_id.startswith("◆"): return "1"
    dots = wbs_id.count(".")
    if dots == 0: return "1"
    if dots == 1: return "2"
    return "3"

def infer_cat(wbs_id):
    if not wbs_id: return ""
    if wbs_id.startswith("◆"): return "마일스톤"
    return WBS_CAT_MAP.get(wbs_id.split(".")[0], "")

def to_pct(v):
    """Notion 0~1 → 0~100"""
    if abs(v) <= 1: return round(v * 100, 1)
    return round(v, 1)

def status_from(actual, note):
    if actual >= 100 or "완료" in note: return "완료"
    if "지연" in note: return "지연"
    if actual > 0 or "진행" in note: return "진행중"
    return "대기"

def avg(lst):
    return round(sum(lst)/len(lst), 1) if lst else 0.0

# ================================================================
# 1. WBS 2026 DB → wbs-data.json
# ================================================================
def parse_wbs(pg):
    p      = pg["properties"]
    wbs_id = txt(p.get("작업명", {}))
    level  = infer_level(wbs_id, sel(p.get("Level", {})))
    cat    = sel(p.get("대분류", {})) or infer_cat(wbs_id)
    org    = sel(p.get("담당기관", {})) or "제일엔지니어링"

    plan   = to_pct(num(p.get("계획공정률",{})))
    actual = to_pct(num(p.get("실적공정률",{})))
    dev    = to_pct(num(p.get("진척차",{})))
    note   = txt(p.get("비고",{}))

    return {
        "id":           pg["id"],
        "name":         txt(p.get("Name",{})) or txt(p.get("중분류",{})),
        "wbsId":        wbs_id,
        "level":        level,
        "category":     cat,
        "subCategory":  txt(p.get("중분류",{})),
        "organization": org,
        "manager":      txt(p.get("담당R",{})),
        "collaborator": txt(p.get("협업C",{})),
        "approver":     txt(p.get("승인A",{})),
        "startDate":    dt(p.get("시작일",{})),
        "endDate":      dt(p.get("종료일",{})),
        "duration":     int(num(p.get("기간",{}))),
        "weight":       num(p.get("가중치",{})),
        "plannedRate":  plan,
        "actualRate":   actual,
        "deviation":    dev,
        "budget":       int(num(p.get("예산",{}))),
        "predecessor":  txt(p.get("선행작업",{})),
        "deliverable":  txt(p.get("산출물",{})),
        "evidence":     txt(p.get("근거자료",{})),
        "note":         note,
        "status":       status_from(actual, note),
    }

def wbs_summary(items):
    valid = [i for i in items if i["wbsId"] and i["level"]]
    total = len(valid)
    done  = sum(1 for i in valid if i["status"]=="완료")
    prog  = sum(1 for i in valid if i["status"]=="진행중")
    delay = sum(1 for i in valid if i["status"]=="지연")
    wait  = sum(1 for i in valid if i["status"]=="대기")
    plans   = [i["plannedRate"] for i in valid]
    actuals = [i["actualRate"]  for i in valid]

    def group(key_fn):
        d = defaultdict(lambda:{"total":0,"done":0,"inProg":0,"delayed":0,"waiting":0,"plans":[],"actuals":[]})
        for i in valid:
            k = key_fn(i)
            d[k]["total"]   += 1
            if i["status"]=="완료":   d[k]["done"]    += 1
            if i["status"]=="진행중": d[k]["inProg"]  += 1
            if i["status"]=="지연":   d[k]["delayed"] += 1
            if i["status"]=="대기":   d[k]["waiting"] += 1
            d[k]["plans"].append(i["plannedRate"])
            d[k]["actuals"].append(i["actualRate"])
        return {k:{
            "total":v["total"],"done":v["done"],"inProg":v["inProg"],
            "delayed":v["delayed"],"waiting":v["waiting"],
            "avgPlan":avg(v["plans"]),"avgActual":avg(v["actuals"])
        } for k,v in d.items()}

    return {
        "total":total,"done":done,"inProg":prog,"delayed":delay,"waiting":wait,
        "avgPlan":avg(plans),"avgActual":avg(actuals),
        "avgDev":round(avg(actuals)-avg(plans),1),
        "byCategory":group(lambda i:i["category"] or "기타"),
        "byOrg":group(lambda i:i["organization"] or "제일엔지니어링"),
    }

def gen_wbs():
    print("\n[1/2] WBS 2026 DB 조회", flush=True)
    pages = fetch_all(WBS_DB_ID)
    items = [parse_wbs(p) for p in pages]
    now   = datetime.now(KST)
    out   = {
        "meta":{"generatedAt":now.isoformat(),"generatedAtKst":now.strftime("%Y-%m-%d %H:%M KST"),
                "source":"Notion API v4.3","dbId":WBS_DB_ID,"totalRecords":len(items)},
        "summary":wbs_summary(items),
        "items":items,
    }
    os.makedirs("data", exist_ok=True)
    with open(WBS_OUTPUT,"w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)
    print(f"  ✅ {WBS_OUTPUT} ({len(items)}건)", flush=True)
    return out

# ================================================================
# 2. 총괄표 DB → summary-data.json
# ================================================================
def parse_summary(pg):
    p = pg["properties"]
    return {
        "id":          pg["id"],
        "name":        txt(p.get("구분",{})),
        "groupType":   sel(p.get("집계유형",{})),
        "total":       int(num(p.get("총작업수",{}))),
        "done":        int(num(p.get("완료",{}))),
        "inProg":      int(num(p.get("진행중",{}))),
        "delayed":     int(num(p.get("지연",{}))),
        "waiting":     int(num(p.get("대기",{}))),
        "plannedRate": to_pct(num(p.get("계획공정률",{}))),
        "actualRate":  to_pct(num(p.get("실적공정률",{}))),
        "deviation":   to_pct(num(p.get("진척차",{}))),
        "achieveRate": to_pct(num(p.get("달성률",{}))),
        "updatedAt":   dt(p.get("최종업데이트",{})),
        "note":        txt(p.get("비고",{})),
    }

def fallback_summary(wbs_items):
    """총괄표 DB 비어있을 때 WBS 집계로 대체"""
    valid = [i for i in wbs_items if i["wbsId"] and i["level"]]
    today = datetime.now(KST).strftime("%Y-%m-%d")
    by_cat = defaultdict(lambda:{"total":0,"done":0,"inProg":0,"delayed":0,"waiting":0,"plans":[],"actuals":[]})
    totals = {"total":0,"done":0,"inProg":0,"delayed":0,"waiting":0,"plans":[],"actuals":[]}

    for i in valid:
        c = i["category"] or "기타"
        for d in (by_cat[c], totals):
            d["total"]   += 1
            if i["status"]=="완료":   d["done"]    += 1
            if i["status"]=="진행중": d["inProg"]  += 1
            if i["status"]=="지연":   d["delayed"] += 1
            if i["status"]=="대기":   d["waiting"] += 1
            d["plans"].append(i["plannedRate"])
            d["actuals"].append(i["actualRate"])

    recs = []
    for cat, v in sorted(by_cat.items(), key=lambda x:-x[1]["total"]):
        n=v["total"]; pl=avg(v["plans"]); ac=avg(v["actuals"])
        recs.append({"id":f"fb-{cat}","name":cat,"groupType":"대분류별",
            "total":n,"done":v["done"],"inProg":v["inProg"],"delayed":v["delayed"],"waiting":v["waiting"],
            "plannedRate":pl,"actualRate":ac,"deviation":round(ac-pl,1),
            "achieveRate":round(v["done"]/n*100,1) if n else 0,"updatedAt":today,"note":""})

    n=totals["total"]; pl=avg(totals["plans"]); ac=avg(totals["actuals"])
    recs.append({"id":"fb-total","name":"📋 전체 종합","groupType":"전체",
        "total":n,"done":totals["done"],"inProg":totals["inProg"],"delayed":totals["delayed"],"waiting":totals["waiting"],
        "plannedRate":pl,"actualRate":ac,"deviation":round(ac-pl,1),
        "achieveRate":round(totals["done"]/n*100,1) if n else 0,"updatedAt":today,"note":"wbs 집계 폴백"})
    return recs

def gen_summary(wbs_items):
    print("\n[2/2] 총괄표 DB 조회", flush=True)
    pages = fetch_all(SUMMARY_DB_ID)
    now   = datetime.now(KST)

    if pages:
        records = [parse_summary(p) for p in pages]
        source  = "Notion 총괄표 DB"
    else:
        print("  ⚠️ 총괄표 DB 비어있음 → WBS 집계 폴백", flush=True)
        records = fallback_summary(wbs_items)
        source  = "WBS 집계 폴백"

    by_cat  = sorted([r for r in records if r["groupType"]=="대분류별"], key=lambda x:-x["total"])
    by_org  = sorted([r for r in records if r["groupType"]=="기관별"],   key=lambda x:-x["total"])
    total_r = next((r for r in records if r["groupType"]=="전체"), None)

    out = {
        "meta":{"generatedAt":now.isoformat(),"generatedAtKst":now.strftime("%Y-%m-%d %H:%M KST"),
                "source":source,"dbId":SUMMARY_DB_ID,"totalRecords":len(records)},
        "total":total_r,
        "byCategory":by_cat,
        "byOrg":by_org,
        "records":records,
    }
    with open(SUMMARY_OUTPUT,"w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)
    print(f"  ✅ {SUMMARY_OUTPUT} ({len(records)}건, {source})", flush=True)

# ================================================================
if __name__ == "__main__":
    if not NOTION_API_KEY:
        print("❌ NOTION_API_KEY 환경변수 없음", flush=True)
        sys.exit(1)

    print("="*50, flush=True)
    print(f"  아산시 WBS 데이터 생성 v4.3", flush=True)
    print(f"  {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}", flush=True)
    print("="*50, flush=True)

    t0 = time.time()
    wbs = gen_wbs()
    gen_summary(wbs["items"])
    print(f"\n✅ 완료 ({round(time.time()-t0,1)}초)", flush=True)
    print(f"  → {WBS_OUTPUT}", flush=True)
    print(f"  → {SUMMARY_OUTPUT}", flush=True)
