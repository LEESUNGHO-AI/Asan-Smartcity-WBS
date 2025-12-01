#!/usr/bin/env python3
"""
아산 스마트시티 WBS 노션 데이터 동기화 스크립트
Notion API를 통해 WBS 데이터베이스를 조회하고 JSON으로 저장합니다.
"""

import os
import json
import requests
from datetime import datetime
from collections import defaultdict

# 노션 설정
NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
DATABASE_ID = '2a250aa9577d80ca8bf2f2abfce71a59'
NOTION_API_URL = 'https://api.notion.com/v1'
NOTION_VERSION = '2022-06-28'

# 담당자 매핑 (Notion User ID -> 이름)
USER_MAP = {
    '1e3d872b-594c-8148-a561-0002b1fa89c4': '함정영',
    '1e3d872b-594c-8117-a95f-000282af6efc': '임혁',
    '1e3d872b-594c-8122-83ec-0002eed70be7': '김주용',
    '1b5d872b-594c-81e7-b2e0-00029fc040fd': '이성호',
    '1f3d872b-594c-812f-b210-00025dddebd2': '이성호',
    '1e3d872b-594c-8108-8452-0002fffe796d': '함정영',
}

# 업무 영역 목록 (16개 단위사업)
BUSINESS_AREAS = [
    'RFP 문석작성', 'WBS', '디지털 OASIS SPOT 구축', '모바일 전자시민증',
    '수요응답형 모빌리티', '스마트폴&디스플레이', '무인매장', '스마트 공공 WiFi',
    '디지털 노마드 접수/운영/거래 관리 플랫폼 구축', 'AI시티관제 플랫폼 구축',
    '정보관리 서비스(데이터허브)', '이노베이션 센터 인테리어 실시설계 및 시공',
    '데이터 기반 AI 융복합 SW개발 플랫폼', 'SDDC 기반 HW 인프라 구축',
    '메타버스 플랫폼', '시설물위치기반서비스플랫폼'
]

# 진행현황 그룹 분류
STATUS_GROUPS = {
    'to_do': ['진행 전', '대기'],
    'in_progress': ['진행 중', '업무협의', '계약진행중', '자료 작성', '자료 대응', 
                    '용역발주', '계약', '구축', '대금 집행', '테스트중'],
    'complete': ['완료', '계약완료', '작성완료', '품의완료', '작업완료', '종료', '중단']
}

def get_headers():
    return {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json'
    }

def query_database(start_cursor=None):
    url = f'{NOTION_API_URL}/databases/{DATABASE_ID}/query'
    payload = {'page_size': 100}
    if start_cursor:
        payload['start_cursor'] = start_cursor
    response = requests.post(url, headers=get_headers(), json=payload)
    response.raise_for_status()
    return response.json()

def get_all_pages():
    all_pages = []
    has_more = True
    start_cursor = None
    while has_more:
        result = query_database(start_cursor)
        all_pages.extend(result.get('results', []))
        has_more = result.get('has_more', False)
        start_cursor = result.get('next_cursor')
        print(f"조회된 항목 수: {len(all_pages)}")
    return all_pages

def extract_property_value(prop):
    if not prop:
        return None
    prop_type = prop.get('type')
    
    if prop_type == 'title':
        titles = prop.get('title', [])
        return ''.join([t.get('plain_text', '') for t in titles]) if titles else None
    elif prop_type == 'rich_text':
        texts = prop.get('rich_text', [])
        return ''.join([t.get('plain_text', '') for t in texts]) if texts else None
    elif prop_type == 'select':
        select = prop.get('select')
        return select.get('name') if select else None
    elif prop_type == 'multi_select':
        return [opt.get('name') for opt in prop.get('multi_select', [])]
    elif prop_type == 'status':
        status = prop.get('status')
        return status.get('name') if status else None
    elif prop_type == 'number':
        return prop.get('number')
    elif prop_type == 'checkbox':
        return prop.get('checkbox', False)
    elif prop_type == 'date':
        date_obj = prop.get('date')
        return {'start': date_obj.get('start'), 'end': date_obj.get('end')} if date_obj else None
    elif prop_type == 'people':
        return [USER_MAP.get(p.get('id'), p.get('name', '미지정')) for p in prop.get('people', [])]
    elif prop_type == 'url':
        return prop.get('url')
    elif prop_type == 'formula':
        formula = prop.get('formula', {})
        ft = formula.get('type')
        return formula.get(ft) if ft in ['number', 'string', 'boolean'] else None
    return None

def parse_page(page):
    props = page.get('properties', {})
    assignees = extract_property_value(props.get('담당자')) or []
    real_progress = extract_property_value(props.get('실진행률'))
    auto_progress = extract_property_value(props.get('자동진행률'))
    progress = real_progress if real_progress is not None else (auto_progress or 0)
    if isinstance(progress, (int, float)) and 0 < progress <= 1:
        progress = progress * 100
    
    return {
        'id': page.get('id', ''),
        'url': page.get('url', ''),
        'title': extract_property_value(props.get('업무 항목')) or '제목 없음',
        'business_area': extract_property_value(props.get('\b업무 영역')),
        'status': extract_property_value(props.get('상태')),
        'progress_status': extract_property_value(props.get('\b진행현황')),
        'priority': extract_property_value(props.get('우선순위')),
        'business_phase': extract_property_value(props.get('사업단계')),
        'detail_status': extract_property_value(props.get('세분화상태')),
        'risk_level': extract_property_value(props.get('리스크레벨')),
        'assignees': assignees,
        'description': extract_property_value(props.get('설명')) or '',
        'start_date': extract_property_value(props.get('시작일')),
        'due_date': extract_property_value(props.get('마감일')),
        'progress': round(progress, 1) if progress else 0,
        'budget_rate': extract_property_value(props.get('예산집행률')),
        'slack_url': extract_property_value(props.get('SLACK')) or '',
        'last_edited': page.get('last_edited_time', ''),
    }

def classify_status_group(status):
    for group, statuses in STATUS_GROUPS.items():
        if status in statuses:
            return group
    return 'to_do'

def calculate_statistics(items):
    stats = {
        'total_items': len(items),
        'by_business_area': defaultdict(lambda: {'count': 0, 'progress_sum': 0, 'to_do': 0, 'in_progress': 0, 'complete': 0}),
        'by_status': defaultdict(int),
        'by_progress_status': defaultdict(int),
        'by_priority': defaultdict(int),
        'by_business_phase': defaultdict(int),
        'by_detail_status': defaultdict(int),
        'by_risk_level': defaultdict(int),
        'by_assignee': defaultdict(int),
        'status_groups': {'to_do': 0, 'in_progress': 0, 'complete': 0},
        'overall_progress': 0,
    }
    
    total_progress, progress_count = 0, 0
    
    for item in items:
        area = item.get('business_area') or '미지정'
        stats['by_business_area'][area]['count'] += 1
        if item.get('progress'):
            stats['by_business_area'][area]['progress_sum'] += item['progress']
        
        stats['by_status'][item.get('status') or '미지정'] += 1
        
        ps = item.get('progress_status') or '미지정'
        stats['by_progress_status'][ps] += 1
        sg = classify_status_group(ps)
        stats['status_groups'][sg] += 1
        stats['by_business_area'][area][sg] += 1
        
        stats['by_priority'][item.get('priority') or '미지정'] += 1
        stats['by_business_phase'][item.get('business_phase') or '미지정'] += 1
        stats['by_detail_status'][item.get('detail_status') or '미지정'] += 1
        
        if item.get('risk_level'):
            stats['by_risk_level'][item['risk_level']] += 1
        
        assignees = item.get('assignees', [])
        if assignees:
            for a in assignees:
                stats['by_assignee'][a] += 1
        else:
            stats['by_assignee']['미배정'] += 1
        
        if item.get('progress'):
            total_progress += item['progress']
            progress_count += 1
    
    stats['overall_progress'] = round(total_progress / progress_count, 1) if progress_count > 0 else 0
    
    for area, data in stats['by_business_area'].items():
        data['avg_progress'] = round(data['progress_sum'] / data['count'], 1) if data['count'] > 0 else 0
    
    for key in ['by_business_area', 'by_status', 'by_progress_status', 'by_priority', 
                'by_business_phase', 'by_detail_status', 'by_risk_level', 'by_assignee']:
        stats[key] = dict(stats[key])
    
    return stats

def main():
    if not NOTION_API_KEY:
        print("오류: NOTION_API_KEY 환경변수가 설정되지 않았습니다.")
        return
    
    print("=== 아산 스마트시티 WBS 데이터 동기화 시작 ===")
    pages = get_all_pages()
    items = [parse_page(page) for page in pages]
    statistics = calculate_statistics(items)
    
    grouped = defaultdict(list)
    for item in items:
        grouped[item.get('business_area') or '미지정'].append(item)
    
    result = {
        'metadata': {
            'database_id': DATABASE_ID,
            'database_url': f'https://www.notion.so/{DATABASE_ID.replace("-", "")}',
            'synced_at': datetime.now().isoformat(),
            'total_items': len(items),
            'business_areas': BUSINESS_AREAS
        },
        'statistics': statistics,
        'grouped_by_business_area': dict(grouped),
        'items': items
    }
    
    os.makedirs('data', exist_ok=True)
    with open('data/wbs-data.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 동기화 완료: {len(items)}개 항목 ===")
    print(f"평균 진척률: {statistics['overall_progress']}%")

if __name__ == '__main__':
    main()
