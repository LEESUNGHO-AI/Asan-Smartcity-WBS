#!/usr/bin/env python3
"""
아산 스마트시티 통합 WBS 동기화 스크립트
- 단위사업별 WBS + 사업관리 WBS 통합 동기화
- GitHub Actions에서 실행
"""

import os
import json
import requests
from datetime import datetime
from collections import defaultdict

# Notion API 설정
NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
NOTION_VERSION = '2022-06-28'

# 데이터베이스 설정
DATABASES = {
    'unit_project': {
        'id': '2a250aa9577d80ca8bf2f2abfce71a59',
        'name': '단위사업별 WBS',
        'description': '16개 단위사업 기술 구축 업무',
        'icon': '🎯'
    },
    'management': {
        'id': '21650aa9577d81e18ac1cedb07eea8bb',
        'name': '사업관리 WBS',
        'description': '사업 홍보, 보고, 감사, 현장점검 등 관리업무',
        'icon': '✒️'
    }
}

# 담당자 매핑
USER_MAP = {
    '1e3d872b-594c-8148-a561-0002b1fa89c4': '함정영',
    '1e3d872b-594c-8117-a95f-000282af6efc': '임혁',
    '1e3d872b-594c-8122-83ec-0002eed70be7': '김주용',
    '1b5d872b-594c-81e7-b2e0-00029fc040fd': '이성호',
    '1f3d872b-594c-812f-b210-00025dddebd2': '이성호',
}

# 진행현황 그룹 분류
STATUS_GROUPS = {
    'to_do': ['진행 전', '대기', '시작 전'],
    'in_progress': ['진행 중', '업무협의', '계약진행중', '자료 작성', '자료 대응', 
                   '용역발주', '계약', '구축', '테스트중', '대금 집행'],
    'complete': ['완료', '계약완료', '작성완료', '품의완료', '작업완료', '종료', '중단']
}

HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Content-Type': 'application/json',
    'Notion-Version': NOTION_VERSION
}


def get_status_group(status):
    """진행현황을 그룹으로 분류"""
    if not status:
        return 'to_do'
    for group, statuses in STATUS_GROUPS.items():
        if status in statuses:
            return group
    return 'in_progress'


def extract_property_value(prop):
    """Notion 속성에서 값 추출"""
    if not prop:
        return None
    
    prop_type = prop.get('type')
    
    if prop_type == 'title':
        title_arr = prop.get('title', [])
        return ''.join([t.get('plain_text', '') for t in title_arr]) if title_arr else None
    
    elif prop_type == 'rich_text':
        text_arr = prop.get('rich_text', [])
        return ''.join([t.get('plain_text', '') for t in text_arr]) if text_arr else None
    
    elif prop_type == 'select':
        select = prop.get('select')
        return select.get('name') if select else None
    
    elif prop_type == 'multi_select':
        items = prop.get('multi_select', [])
        return [item.get('name') for item in items] if items else []
    
    elif prop_type == 'status':
        status = prop.get('status')
        return status.get('name') if status else None
    
    elif prop_type == 'number':
        return prop.get('number')
    
    elif prop_type == 'checkbox':
        return prop.get('checkbox', False)
    
    elif prop_type == 'date':
        date = prop.get('date')
        if date:
            return {
                'start': date.get('start'),
                'end': date.get('end')
            }
        return None
    
    elif prop_type == 'people':
        people = prop.get('people', [])
        return [USER_MAP.get(p.get('id'), p.get('name', '미지정')) for p in people]
    
    elif prop_type == 'url':
        return prop.get('url')
    
    elif prop_type == 'formula':
        formula = prop.get('formula', {})
        formula_type = formula.get('type')
        if formula_type == 'number':
            return formula.get('number')
        elif formula_type == 'string':
            return formula.get('string')
        elif formula_type == 'boolean':
            return formula.get('boolean')
        return None
    
    return None


def query_database(database_id):
    """Notion 데이터베이스 조회 (페이지네이션 처리)"""
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    all_results = []
    has_more = True
    next_cursor = None
    
    while has_more:
        payload = {'page_size': 100}
        if next_cursor:
            payload['start_cursor'] = next_cursor
        
        response = requests.post(url, headers=HEADERS, json=payload)
        
        if response.status_code != 200:
            print(f"Error querying database {database_id}: {response.status_code}")
            print(response.text)
            break
        
        data = response.json()
        all_results.extend(data.get('results', []))
        has_more = data.get('has_more', False)
        next_cursor = data.get('next_cursor')
    
    return all_results


def process_page(page, wbs_type):
    """Notion 페이지 데이터 처리"""
    props = page.get('properties', {})
    page_id = page.get('id', '').replace('-', '')
    
    # 공통 속성 추출
    title = extract_property_value(props.get('업무 항목'))
    area = extract_property_value(props.get('\b업무 영역'))
    status = extract_property_value(props.get('\b진행현황'))
    simple_status = extract_property_value(props.get('상태'))
    priority = extract_property_value(props.get('우선순위'))
    assignees = extract_property_value(props.get('담당자')) or []
    phase = extract_property_value(props.get('사업단계'))
    detail_status = extract_property_value(props.get('세분화상태'))
    risk_level = extract_property_value(props.get('리스크레벨'))
    description = extract_property_value(props.get('설명'))
    slack_url = extract_property_value(props.get('SLACK'))
    
    # 날짜
    start_date = extract_property_value(props.get('시작일'))
    due_date = extract_property_value(props.get('마감일'))
    expected_completion = extract_property_value(props.get('예상완료'))
    actual_completion = extract_property_value(props.get('실제완료'))
    
    # 진척률 계산
    real_progress = extract_property_value(props.get('실진행률'))
    auto_progress = extract_property_value(props.get('자동진행률'))
    
    progress = 0
    if real_progress is not None:
        progress = real_progress * 100 if real_progress <= 1 else real_progress
    elif auto_progress is not None:
        progress = auto_progress * 100 if auto_progress <= 1 else auto_progress
    
    # 예산집행률
    budget_rate = extract_property_value(props.get('예산집행률'))
    if budget_rate is not None and budget_rate <= 1:
        budget_rate = budget_rate * 100
    
    # 사업관리 WBS 전용 속성
    function_type = extract_property_value(props.get('기능 유형')) if wbs_type == 'management' else None
    
    # 상태 그룹 결정
    effective_status = status or simple_status or '대기'
    status_group = get_status_group(effective_status)
    
    return {
        'id': page_id,
        'url': f"https://www.notion.so/{page_id}",
        'wbs_type': wbs_type,
        'title': title or '제목 없음',
        'area': area,
        'status': effective_status,
        'status_group': status_group,
        'priority': priority,
        'assignees': assignees,
        'phase': phase,
        'detail_status': detail_status,
        'risk_level': risk_level,
        'progress': round(progress, 1),
        'budget_rate': round(budget_rate, 1) if budget_rate else None,
        'description': description,
        'slack_url': slack_url,
        'function_type': function_type,
        'dates': {
            'start': start_date.get('start') if start_date else None,
            'due': due_date.get('start') if due_date else None,
            'expected': expected_completion.get('start') if expected_completion else None,
            'actual': actual_completion.get('start') if actual_completion else None
        }
    }


def calculate_statistics(items, wbs_type=None):
    """통계 계산"""
    if wbs_type:
        filtered = [i for i in items if i['wbs_type'] == wbs_type]
    else:
        filtered = items
    
    total = len(filtered)
    if total == 0:
        return {
            'total': 0,
            'to_do': 0,
            'in_progress': 0,
            'complete': 0,
            'average_progress': 0,
            'by_area': {},
            'by_status': {},
            'by_priority': {},
            'by_assignee': {},
            'by_phase': {}
        }
    
    # 상태별 집계
    to_do = sum(1 for i in filtered if i['status_group'] == 'to_do')
    in_progress = sum(1 for i in filtered if i['status_group'] == 'in_progress')
    complete = sum(1 for i in filtered if i['status_group'] == 'complete')
    
    # 평균 진척률
    avg_progress = sum(i['progress'] for i in filtered) / total
    
    # 업무영역별
    by_area = defaultdict(lambda: {'count': 0, 'progress': 0, 'to_do': 0, 'in_progress': 0, 'complete': 0})
    for item in filtered:
        area = item['area'] or '미분류'
        by_area[area]['count'] += 1
        by_area[area]['progress'] += item['progress']
        by_area[area][item['status_group']] += 1
    
    for area in by_area:
        if by_area[area]['count'] > 0:
            by_area[area]['progress'] = round(by_area[area]['progress'] / by_area[area]['count'], 1)
    
    # 상태별
    by_status = defaultdict(int)
    for item in filtered:
        by_status[item['status']] += 1
    
    # 우선순위별
    by_priority = defaultdict(int)
    for item in filtered:
        priority = item['priority'] or '미지정'
        by_priority[priority] += 1
    
    # 담당자별
    by_assignee = defaultdict(int)
    for item in filtered:
        if item['assignees']:
            for assignee in item['assignees']:
                by_assignee[assignee] += 1
        else:
            by_assignee['미배정'] += 1
    
    # 사업단계별
    by_phase = defaultdict(int)
    for item in filtered:
        phase = item['phase'] or '미지정'
        by_phase[phase] += 1
    
    return {
        'total': total,
        'to_do': to_do,
        'in_progress': in_progress,
        'complete': complete,
        'average_progress': round(avg_progress, 1),
        'by_area': dict(by_area),
        'by_status': dict(by_status),
        'by_priority': dict(by_priority),
        'by_assignee': dict(by_assignee),
        'by_phase': dict(by_phase)
    }


def main():
    if not NOTION_API_KEY:
        print("Error: NOTION_API_KEY environment variable not set")
        return
    
    print("=" * 60)
    print("아산 스마트시티 통합 WBS 동기화 시작")
    print("=" * 60)
    
    all_items = []
    db_stats = {}
    
    for wbs_type, db_config in DATABASES.items():
        print(f"\n{db_config['icon']} {db_config['name']} 동기화 중...")
        
        pages = query_database(db_config['id'])
        print(f"  - 조회된 페이지: {len(pages)}개")
        
        items = [process_page(page, wbs_type) for page in pages]
        all_items.extend(items)
        
        # 개별 통계
        db_stats[wbs_type] = calculate_statistics(items, wbs_type)
        print(f"  - 대기: {db_stats[wbs_type]['to_do']}개")
        print(f"  - 진행중: {db_stats[wbs_type]['in_progress']}개")
        print(f"  - 완료: {db_stats[wbs_type]['complete']}개")
        print(f"  - 평균 진척률: {db_stats[wbs_type]['average_progress']}%")
    
    # 통합 통계
    print("\n📊 통합 통계 계산 중...")
    combined_stats = calculate_statistics(all_items)
    
    # 데이터 구조화
    output_data = {
        'metadata': {
            'synced_at': datetime.utcnow().isoformat() + 'Z',
            'total_items': len(all_items),
            'databases': {
                wbs_type: {
                    'id': db_config['id'],
                    'name': db_config['name'],
                    'description': db_config['description'],
                    'icon': db_config['icon'],
                    'url': f"https://www.notion.so/{db_config['id'].replace('-', '')}"
                }
                for wbs_type, db_config in DATABASES.items()
            }
        },
        'statistics': {
            'combined': combined_stats,
            'unit_project': db_stats.get('unit_project', {}),
            'management': db_stats.get('management', {})
        },
        'items': {
            'all': all_items,
            'unit_project': [i for i in all_items if i['wbs_type'] == 'unit_project'],
            'management': [i for i in all_items if i['wbs_type'] == 'management']
        }
    }
    
    # JSON 저장
    output_path = 'data/wbs-data.json'
    os.makedirs('data', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 동기화 완료!")
    print(f"  - 총 항목: {len(all_items)}개")
    print(f"  - 단위사업별 WBS: {len(output_data['items']['unit_project'])}개")
    print(f"  - 사업관리 WBS: {len(output_data['items']['management'])}개")
    print(f"  - 저장 위치: {output_path}")


if __name__ == '__main__':
    main()
