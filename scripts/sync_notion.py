#!/usr/bin/env python3
"""
아산시 강소형 스마트시티 WBS 2026 Notion 동기화 스크립트
GitHub Actions에서 매일 자동 실행되어 Notion 데이터를 가져옵니다.
"""

import os
import json
import requests
from datetime import datetime
from collections import defaultdict

# Notion API 설정
NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
DATABASE_ID = '0ed4b202-7037-400e-96f3-9e3455ba63cd'  # WBS 2026 Database

HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28'
}

def query_notion_database(database_id, start_cursor=None):
    """Notion 데이터베이스 쿼리"""
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    
    payload = {
        'page_size': 100
    }
    if start_cursor:
        payload['start_cursor'] = start_cursor
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def get_all_pages(database_id):
    """모든 페이지 가져오기 (페이지네이션 처리)"""
    all_pages = []
    start_cursor = None
    
    while True:
        result = query_notion_database(database_id, start_cursor)
        if not result:
            break
        
        all_pages.extend(result.get('results', []))
        
        if result.get('has_more'):
            start_cursor = result.get('next_cursor')
        else:
            break
    
    return all_pages

def extract_property(page, prop_name, prop_type):
    """페이지에서 속성 값 추출"""
    props = page.get('properties', {})
    prop = props.get(prop_name, {})
    
    if prop_type == 'title':
        title_list = prop.get('title', [])
        return title_list[0].get('text', {}).get('content', '') if title_list else ''
    
    elif prop_type == 'text' or prop_type == 'rich_text':
        text_list = prop.get('rich_text', [])
        return text_list[0].get('text', {}).get('content', '') if text_list else ''
    
    elif prop_type == 'number':
        return prop.get('number')
    
    elif prop_type == 'select':
        select_val = prop.get('select')
        return select_val.get('name') if select_val else None
    
    elif prop_type == 'date':
        date_val = prop.get('date')
        return date_val.get('start') if date_val else None
    
    return None

def parse_page(page):
    """Notion 페이지를 WBS 아이템으로 변환"""
    page_id = page.get('id', '')
    url = page.get('url', '')
    
    # 속성 추출
    name = extract_property(page, 'Name', 'title')
    wbs_code = extract_property(page, '작업명', 'text')
    level = extract_property(page, 'Level', 'select')
    category = extract_property(page, '대분류', 'select')
    sub_category = extract_property(page, '중분류', 'text')
    org = extract_property(page, '담당기관', 'select')
    manager = extract_property(page, '담당R', 'text')
    
    planned_progress = extract_property(page, '계획공정률', 'number')
    actual_progress = extract_property(page, '실적공정률', 'number')
    gap = extract_property(page, '진척차', 'number')
    weight = extract_property(page, '가중치', 'number')
    
    start_date = extract_property(page, '시작일', 'date')
    end_date = extract_property(page, '종료일', 'date')
    
    # 진행 상태 결정
    progress = (actual_progress or 0) * 100 if actual_progress is not None else 0
    
    if progress >= 100:
        status = 'complete'
        status_text = '완료'
    elif progress > 0:
        status = 'in_progress'
        status_text = '진행중'
    else:
        status = 'to_do'
        status_text = '대기'
    
    # 우선순위 결정 (가중치 기반)
    if weight and weight >= 15:
        priority = 'P0'
    elif weight and weight >= 10:
        priority = 'P1'
    elif weight and weight >= 5:
        priority = 'P2'
    else:
        priority = 'P3'
    
    # WBS 타입 결정 (대분류 기반)
    if category in ['프로젝트 관리/거버넌스', '마일스톤']:
        wbs_type = 'management'
    else:
        wbs_type = 'unit_project'
    
    return {
        'id': page_id,
        'url': url,
        'title': name,
        'wbs_code': wbs_code,
        'level': level,
        'area': category or '',
        'sub_area': sub_category or '',
        'org': org or '',
        'assignee': manager or '',
        'status': status,
        'status_text': status_text,
        'priority': priority,
        'progress': round(progress, 1),
        'planned_progress': round((planned_progress or 0) * 100, 1) if planned_progress else 0,
        'gap': round((gap or 0) * 100, 1) if gap else 0,
        'weight': weight or 0,
        'start_date': start_date,
        'end_date': end_date,
        'wbs_type': wbs_type
    }

def calculate_statistics(items, wbs_type_filter=None):
    """통계 계산"""
    if wbs_type_filter:
        items = [i for i in items if i['wbs_type'] == wbs_type_filter]
    
    total = len(items)
    if total == 0:
        return {
            'total': 0,
            'to_do': 0,
            'in_progress': 0,
            'complete': 0,
            'average_progress': 0,
            'by_area': {},
            'by_assignee': {}
        }
    
    to_do = sum(1 for i in items if i['status'] == 'to_do')
    in_progress = sum(1 for i in items if i['status'] == 'in_progress')
    complete = sum(1 for i in items if i['status'] == 'complete')
    
    # 가중평균 진척률 계산
    weighted_items = [i for i in items if i['weight'] > 0]
    if weighted_items:
        total_weight = sum(i['weight'] for i in weighted_items)
        weighted_progress = sum(i['weight'] * i['progress'] for i in weighted_items) / total_weight
    else:
        weighted_progress = sum(i['progress'] for i in items) / total if items else 0
    
    # 영역별 통계
    by_area = defaultdict(lambda: {'count': 0, 'progress': 0, 'complete': 0, 'total_progress': 0})
    for item in items:
        area = item['area'] or '미분류'
        by_area[area]['count'] += 1
        by_area[area]['total_progress'] += item['progress']
        if item['status'] == 'complete':
            by_area[area]['complete'] += 1
    
    for area in by_area:
        by_area[area]['progress'] = round(by_area[area]['total_progress'] / by_area[area]['count'], 1)
        del by_area[area]['total_progress']
    
    # 담당자별 통계
    by_assignee = defaultdict(int)
    for item in items:
        assignee = item['assignee'] or '미지정'
        by_assignee[assignee] += 1
    
    return {
        'total': total,
        'to_do': to_do,
        'in_progress': in_progress,
        'complete': complete,
        'average_progress': round(weighted_progress, 1),
        'by_area': dict(by_area),
        'by_assignee': dict(by_assignee)
    }

def main():
    """메인 실행 함수"""
    print(f"[{datetime.now()}] Notion 동기화 시작...")
    
    if not NOTION_API_KEY:
        print("Error: NOTION_API_KEY 환경 변수가 설정되지 않았습니다.")
        return
    
    # 데이터 가져오기
    print("Notion 데이터베이스 쿼리 중...")
    pages = get_all_pages(DATABASE_ID)
    print(f"총 {len(pages)}개의 페이지를 가져왔습니다.")
    
    # 아이템 파싱
    items = [parse_page(page) for page in pages]
    
    # 정렬 (WBS 코드 기준)
    def sort_key(item):
        code = item['wbs_code'] or 'zzz'
        # 숫자와 문자 분리하여 정렬
        parts = []
        current = ''
        for char in code:
            if char.isdigit() or char == '.':
                current += char
            else:
                if current:
                    parts.append(current)
                    current = ''
                parts.append(char)
        if current:
            parts.append(current)
        
        # 숫자는 숫자로, 문자는 문자로 정렬
        result = []
        for part in parts:
            try:
                if '.' in part:
                    for p in part.split('.'):
                        result.append((0, int(p) if p else 999))
                else:
                    result.append((0, int(part)))
            except ValueError:
                result.append((1, part))
        return result
    
    items.sort(key=sort_key)
    
    # 통계 계산
    combined_stats = calculate_statistics(items)
    unit_stats = calculate_statistics(items, 'unit_project')
    mgmt_stats = calculate_statistics(items, 'management')
    
    # 결과 데이터 구성
    result = {
        'metadata': {
            'synced_at': datetime.now().isoformat(),
            'database_id': DATABASE_ID,
            'total_items': len(items)
        },
        'statistics': {
            'combined': combined_stats,
            'unit_project': unit_stats,
            'management': mgmt_stats
        },
        'items': {
            'all': items,
            'unit_project': [i for i in items if i['wbs_type'] == 'unit_project'],
            'management': [i for i in items if i['wbs_type'] == 'management']
        }
    }
    
    # JSON 파일로 저장
    output_path = 'data/wbs-data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"데이터가 {output_path}에 저장되었습니다.")
    print(f"- 전체: {combined_stats['total']}개 (진척률: {combined_stats['average_progress']}%)")
    print(f"- 단위사업: {unit_stats['total']}개 (진척률: {unit_stats['average_progress']}%)")
    print(f"- 사업관리: {mgmt_stats['total']}개 (진척률: {mgmt_stats['average_progress']}%)")
    print(f"[{datetime.now()}] 동기화 완료!")

if __name__ == '__main__':
    main()
