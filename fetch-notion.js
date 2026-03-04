/**
 * fetch-notion.js
 * Notion WBS DB → data/wbs.json 변환 스크립트
 * GitHub Actions에서 실행
 */

const { Client } = require('@notionhq/client');
const fs = require('fs');
const path = require('path');

const notion = new Client({ auth: process.env.NOTION_TOKEN });
const DB_ID = process.env.NOTION_DB_ID;

// ── 속성 파서 ─────────────────────────────────────────────
function parseProps(page) {
  const p = page.properties;

  const getText = (prop) => {
    if (!prop) return '';
    if (prop.type === 'title') return prop.title?.map(t => t.plain_text).join('') || '';
    if (prop.type === 'rich_text') return prop.rich_text?.map(t => t.plain_text).join('') || '';
    if (prop.type === 'url') return prop.url || '';
    return '';
  };

  const getSelect = (prop) => {
    if (!prop || prop.type !== 'select') return '';
    return prop.select?.name || '';
  };

  const getNumber = (prop) => {
    if (!prop || prop.type !== 'number') return null;
    return prop.number;
  };

  const getDate = (prop) => {
    if (!prop || prop.type !== 'date') return '';
    return prop.date?.start || '';
  };

  // 날짜 문자열 오염 여부 검사
  const isDateContaminated = (val) => {
    return /^\d{4}/.test(val) || val.includes('GMT') || val.includes('UTC');
  };

  const cleanText = (val) => {
    if (!val) return '';
    if (isDateContaminated(val)) return '';
    return val;
  };

  const taskId = getText(p['작업명']);
  const name   = getText(p['Name']);
  const level  = getSelect(p['Level']);
  const org    = getSelect(p['담당기관']);
  const cat    = getSelect(p['대분류']);
  const sub    = getText(p['중분류']);
  const mgrRaw = getText(p['담당R']);
  const collab = cleanText(getText(p['협업C']));
  const sd     = getDate(p['시작일']);
  const ed     = getDate(p['종료일']);
  const dur    = getNumber(p['기간']);
  const wt     = getNumber(p['가중치']);
  const plan   = getNumber(p['계획공정률']);
  const actual = getNumber(p['실적공정률']);
  const prog   = getNumber(p['진행률']);
  const dev    = getNumber(p['진척차']);
  const budget = getNumber(p['예산']);
  const pred   = getText(p['선행작업']);
  const deliv  = getText(p['산출물']);
  const evid   = getText(p['근거자료']);
  const appr   = getText(p['승인A']);
  const note   = cleanText(getText(p['비고']));
  const url    = getText(p['userDefined:URL']);

  // 쓰레기 데이터 필터링
  const isJunk = (id) => {
    if (!id) return true;
    if (['작업패키지','범례','WBS ID'].includes(id)) return true;
    if (isDateContaminated(id)) return true;
    return false;
  };

  if (isJunk(taskId) && isJunk(name)) return null;

  // 진행 상태 계산
  let status = '대기';
  const actualVal = actual !== null ? actual : 0;
  const planVal   = plan !== null ? plan : 0;
  if (actualVal >= 1.0) status = '완료';
  else if (actualVal > 0) status = '진행중';

  // 유효한 담당기관만 허용
  const VALID_ORGS = ['제일엔지니어링','아산시','호서대','충남연구원','KAIST'];
  const validOrg = VALID_ORGS.includes(org) ? org : '';

  // 유효한 대분류만 허용
  const VALID_CATS = [
    '사업총괄','프로젝트 관리/거버넌스','실시설계','나라장터 발주 지원',
    '서비스 구축','통합시험/시범운영','준공/검수/이관','운영(3년)','마일스톤'
  ];
  const validCat = VALID_CATS.includes(cat) ? cat : '';

  return {
    id:           taskId || name,
    name:         name || taskId,
    level:        level || '',
    category:     validCat,
    subCategory:  sub,
    organization: validOrg,
    manager:      cleanText(mgrRaw),
    collaborator: collab,
    startDate:    sd,
    endDate:      ed,
    duration:     dur,
    weight:       wt,
    plannedRate:  plan !== null ? Math.round(plan * 100) : null,
    actualRate:   actual !== null ? Math.round(actual * 100) : null,
    progressRate: prog !== null ? Math.round(prog * 100) : null,
    deviation:    dev !== null ? parseFloat((dev * 100).toFixed(1)) : null,
    budget:       budget,
    predecessor:  pred,
    deliverable:  deliv,
    evidence:     evid,
    approver:     appr,
    note:         note,
    url:          url,
    status:       status,
    notionPageId: page.id,
  };
}

// ── 전체 페이지 조회 ──────────────────────────────────────
async function fetchAllPages() {
  const results = [];
  let cursor = undefined;
  let page = 1;

  do {
    console.log(`  페이지 ${page} 조회 중...`);
    const resp = await notion.databases.query({
      database_id: DB_ID,
      page_size: 100,
      start_cursor: cursor,
    });

    results.push(...resp.results);
    cursor = resp.has_more ? resp.next_cursor : undefined;
    page++;
    
    if (cursor) await new Promise(r => setTimeout(r, 300));
  } while (cursor);

  return results;
}

// ── 집계 계산 ─────────────────────────────────────────────
function calcSummary(items) {
  const valid = items.filter(i => i.level && i.actualRate !== null);
  
  const total = items.length;
  const done  = items.filter(i => i.status === '완료').length;
  const inProg = items.filter(i => i.status === '진행중').length;
  const avgPlan   = valid.length ? Math.round(valid.reduce((s,i) => s + (i.plannedRate||0), 0) / valid.length) : 0;
  const avgActual = valid.length ? Math.round(valid.reduce((s,i) => s + (i.actualRate||0), 0) / valid.length) : 0;
  const avgDev    = valid.length ? parseFloat((valid.reduce((s,i) => s + (i.deviation||0), 0) / valid.length).toFixed(1)) : 0;

  // 대분류별 집계
  const byCategory = {};
  items.forEach(i => {
    if (!i.category) return;
    if (!byCategory[i.category]) byCategory[i.category] = { count:0, totalPlan:0, totalActual:0, items:0 };
    const b = byCategory[i.category];
    b.count++;
    if (i.plannedRate !== null) { b.totalPlan += i.plannedRate; b.items++; }
    if (i.actualRate !== null) b.totalActual += i.actualRate;
  });
  Object.values(byCategory).forEach(b => {
    b.avgPlan   = b.items ? Math.round(b.totalPlan / b.items) : 0;
    b.avgActual = b.items ? Math.round(b.totalActual / b.items) : 0;
    delete b.totalPlan; delete b.totalActual; delete b.items;
  });

  // 담당기관별 집계
  const byOrg = {};
  items.forEach(i => {
    if (!i.organization) return;
    if (!byOrg[i.organization]) byOrg[i.organization] = { count:0, done:0, inProg:0 };
    byOrg[i.organization].count++;
    if (i.status === '완료') byOrg[i.organization].done++;
    if (i.status === '진행중') byOrg[i.organization].inProg++;
  });

  return { total, done, inProg, avgPlan, avgActual, avgDev, byCategory, byOrg };
}

// ── 메인 ─────────────────────────────────────────────────
async function main() {
  console.log('🚀 Notion WBS 데이터 추출 시작');
  console.log(`   DB ID: ${DB_ID}`);

  if (!process.env.NOTION_TOKEN) throw new Error('NOTION_TOKEN 환경변수 없음');
  if (!DB_ID) throw new Error('NOTION_DB_ID 환경변수 없음');

  const pages  = await fetchAllPages();
  console.log(`✅ 총 ${pages.length}개 페이지 조회`);

  const parsed = pages.map(parseProps).filter(Boolean);
  console.log(`✅ 유효 레코드: ${parsed.length}개 (무효 ${pages.length - parsed.length}개 제거)`);

  // 중복 제거 (작업명 기준, 나중 것 우선)
  const deduped = {};
  parsed.forEach(item => {
    const key = item.id;
    if (!deduped[key] || deduped[key].notionPageId < item.notionPageId) {
      deduped[key] = item;
    }
  });
  const items = Object.values(deduped).sort((a,b) => a.id.localeCompare(b.id, undefined, {numeric:true}));
  console.log(`✅ 중복 제거 후: ${items.length}개`);

  const summary = calcSummary(items);
  console.log(`📊 요약: 전체 ${summary.total} | 완료 ${summary.done} | 진행중 ${summary.inProg} | 평균실적 ${summary.avgActual}%`);

  const output = {
    meta: {
      generatedAt:  new Date().toISOString(),
      generatedAtKst: new Date(Date.now() + 9*3600*1000).toISOString().replace('T',' ').slice(0,19) + ' KST',
      source:       'Notion DB - 아산시 강소형 스마트시티 WBS 2026',
      dbId:         DB_ID,
      totalRecords: items.length,
    },
    summary,
    items,
  };

  // data 디렉토리 생성
  const dir = path.join(process.cwd(), 'data');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const outPath = path.join(dir, 'wbs.json');
  fs.writeFileSync(outPath, JSON.stringify(output, null, 2), 'utf8');
  console.log(`💾 저장 완료: ${outPath} (${(fs.statSync(outPath).size / 1024).toFixed(1)} KB)`);
}

main().catch(err => {
  console.error('❌ 오류:', err.message);
  process.exit(1);
});
