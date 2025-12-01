#!/usr/bin/env python3
"""
아산 스마트시티 WBS 데이터 동기화 스크립트
Notion 데이터베이스에서 WBS 데이터를 가져와 JSON 파일로 저장합니다.
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Any

# Notion API 설정
NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
DATABASE_ID = "2a250aa9577d80c6926df376223a3846"
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}

def query_database(database_id: str, start_cursor: str = None) -> Dict[str, Any]:
    """노션 데이터베이스 쿼리"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    payload = {
        "page_size": 100
    }
    
    if start_cursor:
        payload["start_cursor"] = start_cursor
    
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()

def extract_property_value(prop: Dict[str, Any]) -> Any:
    """노션 속성에서 값 추출"""
    prop_type = prop.get("type")
    
    if prop_type == "title":
        titles = prop.get("title", [])
        return "".join([t.get("plain_text", "") for t in titles])
    
    elif prop_type == "rich_text":
        texts = prop.get("rich_text", [])
        return "".join([t.get("plain_text", "") for t in texts])
    
    elif prop_type == "select":
        select = prop.get("select")
        return select.get("name", "") if select else ""
    
    elif prop_type == "number":
        return prop.get("number", 0) or 0
    
    elif prop_type == "date":
        date = prop.get("date")
        return date.get("start", "") if date else ""
    
    elif prop_type == "checkbox":
        return prop.get("checkbox", False)
    
    elif prop_type == "multi_select":
        options = prop.get("multi_select", [])
        return [opt.get("name", "") for opt in options]
    
    return None

def parse_page(page: Dict[str, Any]) -> Dict[str, Any]:
    """페이지 데이터 파싱"""
    properties = page.get("properties", {})
    
    return {
        "id": extract_property_value(properties.get("id", {})),
        "name": extract_property_value(properties.get("name", {})),
        "type": extract_property_value(properties.get("type", {})),
        "category": extract_property_value(properties.get("category", {})),
        "subcategory": extract_property_value(properties.get("subcategory", {})),
        "assignee": extract_property_value(properties.get("assignee", {})),
        "deliverable": extract_property_value(properties.get("deliverable", {})),
        "status": extract_property_value(properties.get("status", {})),
        "progress": extract_property_value(properties.get("progress", {})),
        "created_date": extract_property_value(properties.get("created_date", {})),
        "notion_url": page.get("url", ""),
        "last_edited": page.get("last_edited_time", "")
    }

def fetch_all_wbs_data() -> List[Dict[str, Any]]:
    """모든 WBS 데이터 가져오기"""
    all_items = []
    has_more = True
    start_cursor = None
    
    print("📥 노션에서 WBS 데이터를 가져오는 중...")
    
    while has_more:
        result = query_database(DATABASE_ID, start_cursor)
        pages = result.get("results", [])
        
        for page in pages:
            item = parse_page(page)
            all_items.append(item)
        
        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")
        
        print(f"  ✓ {len(all_items)}개 항목 로드됨...")
    
    return all_items

def calculate_statistics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """통계 계산"""
    total = len(items)
    
    # 상태별 통계
    status_counts = {}
    for item in items:
        status = item.get("status", "미지정")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # 카테고리별 통계
    category_counts = {}
    for item in items:
        category = item.get("category", "미지정")
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # 단위사업(서브카테고리)별 통계
    subcategory_counts = {}
    for item in items:
        subcategory = item.get("subcategory", "미지정")
        if subcategory:
            subcategory_counts[subcategory] = subcategory_counts.get(subcategory, 0) + 1
    
    # 담당자별 통계
    assignee_counts = {}
    for item in items:
        assignee = item.get("assignee", "미지정")
        if assignee:
            assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    # 유형별 통계
    type_counts = {}
    for item in items:
        work_type = item.get("type", "미지정")
        type_counts[work_type] = type_counts.get(work_type, 0) + 1
    
    # 전체 진척률 계산
    total_progress = sum(item.get("progress", 0) or 0 for item in items)
    avg_progress = round(total_progress / total, 1) if total > 0 else 0
    
    # 서브카테고리별 진척률
    subcategory_progress = {}
    for item in items:
        subcategory = item.get("subcategory", "미지정")
        if subcategory:
            if subcategory not in subcategory_progress:
                subcategory_progress[subcategory] = {"total": 0, "count": 0}
            subcategory_progress[subcategory]["total"] += item.get("progress", 0) or 0
            subcategory_progress[subcategory]["count"] += 1
    
    for sub, data in subcategory_progress.items():
        data["average"] = round(data["total"] / data["count"], 1) if data["count"] > 0 else 0
    
    return {
        "total_items": total,
        "average_progress": avg_progress,
        "status": status_counts,
        "category": category_counts,
        "subcategory": subcategory_counts,
        "assignee": assignee_counts,
        "type": type_counts,
        "subcategory_progress": subcategory_progress
    }

def group_by_subcategory(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """서브카테고리(단위사업)별로 그룹핑"""
    grouped = {}
    for item in items:
        subcategory = item.get("subcategory", "기타")
        if subcategory not in grouped:
            grouped[subcategory] = []
        grouped[subcategory].append(item)
    return grouped

def main():
    """메인 실행 함수"""
    if not NOTION_API_KEY:
        print("❌ NOTION_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   export NOTION_API_KEY='your-api-key' 로 설정해주세요.")
        return
    
    try:
        # 데이터 가져오기
        items = fetch_all_wbs_data()
        
        # 통계 계산
        stats = calculate_statistics(items)
        
        # 단위사업별 그룹핑
        grouped = group_by_subcategory(items)
        
        # 결과 데이터 구성
        result = {
            "metadata": {
                "database_id": DATABASE_ID,
                "synced_at": datetime.now().isoformat(),
                "total_items": len(items),
                "notion_database_url": f"https://notion.so/{DATABASE_ID}"
            },
            "statistics": stats,
            "grouped_by_unit_project": grouped,
            "items": items
        }
        
        # JSON 파일로 저장
        output_path = "data/wbs-data.json"
        os.makedirs("data", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 동기화 완료!")
        print(f"   총 {len(items)}개 항목이 {output_path}에 저장되었습니다.")
        print(f"\n📊 통계 요약:")
        print(f"   - 평균 진척률: {stats['average_progress']}%")
        print(f"   - 상태별: {stats['status']}")
        print(f"   - 단위사업 수: {len(stats['subcategory'])}개")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API 요청 오류: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
