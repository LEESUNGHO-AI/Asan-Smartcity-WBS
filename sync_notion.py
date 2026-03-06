#!/usr/bin/env python3
"""
아산시 강소형 스마트시티 WBS 동기화 스크립트
Notion DB → data/wbs-data.json
"""

import os, json, re, sys
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.error

NOTION_TOKEN = os.environ.get("NOTION_API_KEY", "")
DB_ID = "559654aed9404d9f88225ea0adc7d746"
OUTPUT_PATH = "data/wbs-data.json"

VALID_ORG = {"제일엔지니어링","아산시","호서대","충남연구원","KAIST"}
VALID_CAT = {
    "사업총괄","프로젝트 관리/거버넌스","실시설계","나라장터 발주 지원",
    "서비스 구축","통합시험/시범운영","준공/검수/이관","운영(3년)","마일스톤"
}

def is_bad(v):
    s = str(v or "").strip()
    return bool(re.match(r"^\d{4}[^.]", s)) or "GMT" in s or "UTC" in s

def notion_req(method, path, body=None):
    url = f"https://api.notion.com/v1{path}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"❌ Notion API {e.code}: {e.read().decode()[:200]}")
        return None

def get_text(prop):
    if not prop: return ""
    t = prop.get("type","")
    if t == "title":     return "".join(x.get("plain_text","") for x in prop.get("title",[]))
    if t == "rich_text": return "".join(x.get("plain_text","") for x in prop.get("rich_text",[]))
    if t == "url":       return prop.get("url","") or ""
    return ""

def get_sel(prop):
    if not prop or prop.get("type") != "select": return ""
    return (prop.get("select") or {}).get("name","")

def get_num(prop):
    if not prop or prop.get("type") != "number": return None
    return prop.get("number")

def get_date(prop):
    if not prop or prop.get("type") != "date": return ""
    return ((prop.get("date") or {}).get("start","") or "")[:10]

def pct(v):
    if v is None: return None
    return round(v * 100, 1)

def parse_page(page):
    p = page.get("properties", {})
    task_id = get_text(p.get("작업명")) or get_text(p.get("Name"))
    if not task_id or is_bad(task_id): return None
    if task_id in {"작업패키지","범례","WBS ID"}: return None

    org_raw = get_sel(p.get("담당기관"))
    cat_raw = get_sel(p.get("대분류"))
    actual_v = get_num(p.get("실적공정률"))
    actual_pct = pct(actual_v)

    status = "대기"
    if actual_pct is not None:
        if actual_pct >= 100: status = "완료"
        elif actual_pct > 0:  status = "진행중"

    return {
        "id":           task_id,
        "name":         get_text(p.get("Name")) or task_id,
        "level":        get_sel(p.get("Level")),
        "category":     cat_raw if cat_raw in VALID_CAT else "",
        "subCategory":  "" if is_bad(get_text(p.get("중분류"))) else get_text(p.get("중분류")),
        "organization": org_raw if org_raw in VALID_ORG else "",
        "manager":      "" if is_bad(get_text(p.get("담당R"))) else get_text(p.get("담당R")),
        "collaborator": get_text(p.get("협업C")),
        "startDate":    get_date(p.get("시작일")),
        "endDate":      get_date(p.get("종료일")),
        "duration":     get_num(p.get("기간")),
        "weight":       get_num(p.get("가중치")),
        "plannedRate":  pct(get_num(p.get("계획공정률"))),
        "actualRate":   actual_pct,
        "progressRate": pct(get_num(p.get("진행률"))),
        "deviation":    pct(get_num(p.get("진척차"))),
        "budget":       get_num(p.get("예산")),
        "predecessor":  get_text(p.get("선행작업")),
        "deliverable":  get_text(p.get("산출물")),
        "evidence":     get_text(p.get("근거자료")),
        "note":         "" if is_bad(get_text(p.get("비고"))) else get_text(p.get("비고")),
        "status":       status,
    }

def main():
    if not NOTION_TOKEN:
        print("❌ NOTION_API_KEY 환경변수 없음")
        sys.exit(1)

    print(f"🔄 Notion DB 조회 시작 ({DB_ID})")

    # 전체 페이지 조회
    pages, cursor, pg = [], None, 1
    while True:
        print(f"  {pg}페이지 조회...", end=" ")
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        resp = notion_req("POST", f"/databases/{DB_ID}/query", body)
        if not resp: break
        batch = resp.get("results", [])
        pages.extend(batch)
        print(f"{len(batch)}건")
        if not resp.get("has_more"): break
        cursor = resp.get("next_cursor")
        pg += 1

    print(f"✅ 총 {len(pages)}건 조회")

    # 파싱 + 중복 제거
    seen, items = {}, []
    for page in pages:
        item = parse_page(page)
        if not item: continue
        if item["id"] in seen: continue
        seen[item["id"]] = True
        items.append(item)

    # 정렬
    items.sort(key=lambda x: x["id"])
    print(f"✅ 유효 항목: {len(items)}건")

    # 집계
    valid   = [i for i in items if i.get("actualRate") is not None]
    total   = len(items)
    done    = sum(1 for i in items if i["status"] == "완료")
    in_prog = sum(1 for i in items if i["status"] == "진행중")
    avg_plan   = round(sum(i["plannedRate"] or 0 for i in valid) / len(valid), 1) if valid else 0
    avg_actual = round(sum(i["actualRate"]  or 0 for i in valid) / len(valid), 1) if valid else 0
    avg_dev    = round(sum(i["deviation"]   or 0 for i in valid) / len(valid), 1) if valid else 0

    by_cat, by_org = {}, {}
    for i in items:
        if i["category"]:
            c = i["category"]
            if c not in by_cat: by_cat[c] = {"count":0,"planSum":0,"actualSum":0,"n":0}
            by_cat[c]["count"] += 1
            if i["plannedRate"] is not None:
                by_cat[c]["planSum"]   += i["plannedRate"]
                by_cat[c]["actualSum"] += i["actualRate"] or 0
                by_cat[c]["n"] += 1
        if i["organization"]:
            o = i["organization"]
            if o not in by_org: by_org[o] = {"count":0,"done":0,"inProg":0}
            by_org[o]["count"] += 1
            if i["status"] == "완료":   by_org[o]["done"]   += 1
            if i["status"] == "진행중": by_org[o]["inProg"] += 1

    for c in by_cat:
        n = by_cat[c]["n"]
        by_cat[c]["avgPlan"]   = round(by_cat[c]["planSum"]   / n, 1) if n else 0
        by_cat[c]["avgActual"] = round(by_cat[c]["actualSum"] / n, 1) if n else 0
        del by_cat[c]["planSum"], by_cat[c]["actualSum"], by_cat[c]["n"]

    now_kst = datetime.now(timezone(timedelta(hours=9)))
    output = {
        "meta": {
            "generatedAt":    datetime.utcnow().isoformat() + "Z",
            "generatedAtKst": now_kst.strftime("%Y-%m-%d %H:%M KST"),
            "source":         "Notion WBS 2026 DB",
            "dbId":           DB_ID,
            "totalRecords":   total,
        },
        "summary": {
            "total": total, "done": done, "inProg": in_prog,
            "avgPlan": avg_plan, "avgActual": avg_actual, "avgDev": avg_dev,
            "byCategory": by_cat, "byOrg": by_org,
        },
        "items": items,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"💾 저장: {OUTPUT_PATH} ({size:.1f} KB)")
    print(f"📊 전체:{total} | 완료:{done} | 진행:{in_prog} | 평균실적:{avg_actual}%")

if __name__ == "__main__":
    main()
