#!/usr/bin/env python3
"""
sync_notion.py  v4.0  (2026-03-10)
아산시 강소형 스마트시티 WBS - Notion DB -> data/wbs-data.json

수정 내역:
 - Name 필드([X.Y.Z] 패턴)에서 WBS ID 추출 (작업명 필드 빈값 대응)
 - WBS ID -> 대분류 자동 추론 (Notion 빈값 완전 대응)
 - byCategory / byOrg 정상 집계
 - 표준 라이브러리만 사용 (pip install 불필요)
"""

import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from collections import defaultdict

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
DATABASE_ID    = "559654aed9404d9f88225ea0adc7d746"
API_VER        = "2022-06-28"
OUTPUT         = "data/wbs-data.json"
MAX_RETRY      = 3
KST            = timezone(timedelta(hours=9))

VALID_CATS = {
    "사업총괄","프로젝트 관리/거버넌스","실시설계",
    "나라장터 발주 지원","서비스 구축","통합시험/시범운영",
    "준공/검수/이관","운영(3년)","마일스톤",
}

WBS_CAT = {
    "1":"사업총괄","2":"프로젝트 관리/거버넌스","3":"나라장터 발주 지원",
    "4":"서비스 구축","5":"통합시험/시범운영","6":"준공/검수/이관",
    "7":"준공/검수/이관","8":"준공/검수/이관","9":"운영(3년)",
}

_NAME_RE = re.compile(r"^\[(.+?)\]")


def infer_category(wbs_id, notion_val):
    if notion_val and notion_val in VALID_CATS:
        return notion_val
    if not wbs_id:
        return ""
    s = str(wbs_id).strip()
    if s.startswith("◆"):
        return "마일스톤"
    return WBS_CAT.get(s.split(".")[0], "")


def api_call(path, method="GET", body=None, attempt=0):
    url = "https://api.notion.com/v1/" + path
    hdr = {
        "Authorization": "Bearer " + NOTION_API_KEY,
        "Notion-Version": API_VER,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers=hdr, method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        if e.code == 429 and attempt < MAX_RETRY:
            wait = (attempt+1)*5
            print("  Rate limit -> " + str(wait) + "s 대기...")
            time.sleep(wait)
            return api_call(path, method, body, attempt+1)
        raise RuntimeError("Notion API " + str(e.code) + ": " + msg[:200])
    except OSError as e:
        if attempt < MAX_RETRY:
            wait = (attempt+1)*3
            print("  네트워크 오류 -> " + str(wait) + "s 후 재시도: " + str(e))
            time.sleep(wait)
            return api_call(path, method, body, attempt+1)
        raise


def fetch_db():
    pages, cursor, pg = [], None, 0
    while True:
        pg += 1
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        res = api_call("databases/" + DATABASE_ID + "/query", "POST", payload)
        batch = res.get("results", [])
        pages.extend(batch)
        print("  page " + str(pg) + ": " + str(len(batch)) + "건 (합계 " + str(len(pages)) + "건)")
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
        time.sleep(0.35)
    return pages


def txt(pr, key):
    p = pr.get(key, {})
    t = p.get("type", "")
    if t in ("rich_text", "title"):
        return "".join(x.get("plain_text","") for x in p.get(t, []))
    return ""

def sel(pr, key):
    s = pr.get(key, {}).get("select")
    return s.get("name","") if s else ""

def num(pr, key, default=0):
    v = pr.get(key, {}).get("number")
    return v if v is not None else default

def dt(pr, key):
    d = pr.get(key, {}).get("date")
    return str(d["start"])[:10] if d and d.get("start") else ""

def pct(v):
    if v is None:
        return 0.0
    return round(v*100, 1) if abs(v) <= 1.5 else round(float(v), 1)


def parse(page):
    pr = page["properties"]
    name_full = txt(pr, "Name")
    m = _NAME_RE.match(name_full)
    wbs_id = m.group(1) if m else txt(pr, "작업명")
    category = infer_category(wbs_id, sel(pr, "대분류"))

    plan_pct   = pct(num(pr, "계획공정률", 0))
    actual_pct = pct(num(pr, "실적공정률", 0))
    dev_pct    = round(actual_pct - plan_pct, 1)

    note = txt(pr, "비고")
    if "완료" in note or actual_pct >= 100:
        status = "완료"
    elif "지연" in note:
        status = "지연"
    elif "진행" in note or actual_pct > 0:
        status = "진행중"
    else:
        status = "대기"

    return {
        "id": page["id"], "name": name_full, "wbsId": wbs_id,
        "level": sel(pr,"Level"), "category": category,
        "subCategory": txt(pr,"중분류"), "organization": sel(pr,"담당기관"),
        "manager": txt(pr,"담당R"), "collaborator": txt(pr,"협업C"),
        "approver": txt(pr,"승인A"),
        "startDate": dt(pr,"시작일"), "endDate": dt(pr,"종료일"),
        "duration": num(pr,"기간",0), "weight": num(pr,"가중치",0),
        "plannedRate": plan_pct, "actualRate": actual_pct,
        "deviation": dev_pct,
        "budget": num(pr,"예산",0), "predecessor": txt(pr,"선행작업"),
        "deliverable": txt(pr,"산출물"), "evidence": txt(pr,"근거자료"),
        "note": note, "status": status,
    }


def summarize(items):
    valid = [
        x for x in items
        if x["level"] in ("1","2","3") and x["wbsId"]
        and x["name"] not in ("범례","")
    ]
    total   = len(valid)
    done    = sum(1 for x in valid if x["status"]=="완료")
    in_prog = sum(1 for x in valid if x["status"]=="진행중")
    delayed = sum(1 for x in valid if x["status"]=="지연")
    waiting = sum(1 for x in valid if x["status"]=="대기")
    avg_plan   = round(sum(x["plannedRate"]  for x in valid)/total, 1) if total else 0
    avg_actual = round(sum(x["actualRate"]   for x in valid)/total, 1) if total else 0

    by_cat = defaultdict(lambda: {"total":0,"done":0,"inProg":0,"delayed":0,
                                   "avgPlan":0,"avgActual":0,"_ps":0,"_as":0})
    by_org = defaultdict(lambda: {"total":0,"done":0,"inProg":0,"delayed":0})

    for x in valid:
        cat = x["category"] or "기타"
        org = x["organization"] or "미지정"
        bc = by_cat[cat]
        bc["total"]+=1; bc["_ps"]+=x["plannedRate"]; bc["_as"]+=x["actualRate"]
        if x["status"]=="완료":   bc["done"]+=1
        if x["status"]=="진행중": bc["inProg"]+=1
        if x["status"]=="지연":   bc["delayed"]+=1
        bo = by_org[org]
        bo["total"]+=1
        if x["status"]=="완료":   bo["done"]+=1
        if x["status"]=="진행중": bo["inProg"]+=1
        if x["status"]=="지연":   bo["delayed"]+=1

    cat_result = {}
    for cat, bc in by_cat.items():
        n = bc["total"]
        cat_result[cat] = {
            "total":bc["total"],"done":bc["done"],"inProg":bc["inProg"],"delayed":bc["delayed"],
            "avgPlan":round(bc["_ps"]/n,1) if n else 0,
            "avgActual":round(bc["_as"]/n,1) if n else 0,
        }

    return {
        "total":total,"done":done,"inProg":in_prog,"delayed":delayed,"waiting":waiting,
        "avgPlan":avg_plan,"avgActual":avg_actual,"avgDev":round(avg_actual-avg_plan,1),
        "byCategory":cat_result,"byOrg":dict(by_org),
    }


def main():
    now = datetime.now(KST)
    print("\n" + "="*55)
    print(" WBS Notion Sync v4.0  " + now.strftime("%Y-%m-%d %H:%M KST"))
    print("="*55)

    if not NOTION_API_KEY:
        print("ERROR: NOTION_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print("\nNotion DB 조회 중...")
    pages = fetch_db()
    print("Notion 응답: " + str(len(pages)) + "건\n")

    items, skip = [], 0
    for pg in pages:
        try:
            items.append(parse(pg))
        except Exception as e:
            skip += 1
            print("  파싱 실패 [" + pg.get("id","")[:8] + "]: " + str(e))
    print("파싱 완료: " + str(len(items)) + "건  (실패 " + str(skip) + "건)")

    summary = summarize(items)
    s = summary
    print("\n집계 결과:")
    print("  전체 " + str(s["total"]) + "건 | 완료 " + str(s["done"]) + "건 | 진행중 " + str(s["inProg"]) + "건 | 지연 " + str(s["delayed"]) + "건")
    print("  평균 실적: " + str(s["avgActual"]) + "% / 계획: " + str(s["avgPlan"]) + "%")
    print("\n  대분류별:")
    for cat, v in sorted(s["byCategory"].items(), key=lambda x: -x[1]["total"]):
        print("    " + cat.ljust(25) + str(v["total"]).rjust(3) + "건  실적 " + str(v["avgActual"]) + "%")
    print("\n  담당기관별:")
    for org, v in sorted(s["byOrg"].items(), key=lambda x: -x[1]["total"]):
        print("    " + org.ljust(20) + str(v["total"]).rjust(3) + "건")

    os.makedirs("data", exist_ok=True)
    output = {
        "meta": {
            "generatedAt":    now.isoformat(),
            "generatedAtKst": now.strftime("%Y-%m-%d %H:%M KST"),
            "source":         "Notion API v4.0",
            "dbId":           DATABASE_ID,
            "totalRecords":   len(items),
        },
        "summary": summary,
        "items":   items,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    kb = os.path.getsize(OUTPUT) / 1024
    print("\n" + OUTPUT + " 저장 완료  (" + str(round(kb,1)) + " KB)")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
