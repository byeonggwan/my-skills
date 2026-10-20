// 테크 스펙 HTML(Artifact 조각)의 계약을 검사한다. 사용: node check-techspec.mjs <file.html> [--preview <out.html>]
import { readFileSync, writeFileSync } from 'node:fs';

const file = process.argv[2];
const pv = process.argv.indexOf('--preview');
const previewOut = pv > 0 ? process.argv[pv + 1] : null;
if (!file) { console.error('사용법: node check-techspec.mjs <file.html> [--preview <out.html>]'); process.exit(2); }
const html = readFileSync(file, 'utf8');
const errors = [];
const warn = [];
const flows = [...html.matchAll(/<script type="text\/plain" class="flow-src">([\s\S]*?)<\/script>/g)].map(m => m[1]);
const body = html.replace(/<!--[\s\S]*?-->/g, '').replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style>[\s\S]*?<\/style>/g, '');
const text = (s) => s.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&[a-z]+;/g, ' ').replace(/\s+/g, ' ').trim();
const num = (s) => (s == null ? null : Number(s));
const sectionOf = (id) => { const m = body.match(new RegExp(`<section[^>]*id="${id}"[\\s\\S]*?</section>`)); return m ? m[0] : ''; };

// 1. 자리표시자, 안내 주석, 조각 형식
const left = body.match(/\{\{[^}]*\}\}/g) || [];
const leftFlow = flows.join('\n').match(/\{\{[^}]*\}\}/g) || [];
if (left.length + leftFlow.length) errors.push(`자리표시자 ${left.length + leftFlow.length}개가 남아 있음: ${[...new Set([...left, ...leftFlow])].slice(0, 4).join(' ')}`);
if (/<!--\s*안내:/.test(html)) errors.push('"안내:" 주석이 남아 있음 (발행 전에 지운다)');
if (/<!doctype|<html[\s>]|<head[\s>]|<body[\s>]/i.test(html)) errors.push('doctype/html/head/body가 있음. Artifact 조각으로 쓴다(발행할 때 감싼다)');
const title = (html.match(/<title>([^<]*)<\/title>/) || [])[1];
if (!title || !title.trim()) errors.push('<title>이 없음');
if (!/url\("fonts\/PretendardVariable\.woff2"\)/.test(html)) errors.push('Pretendard 경로가 fonts/PretendardVariable.woff2가 아님');

// 1-1. 맨 위 이슈 키는 Jira 이슈 링크
const keyM = body.match(/<span class="issue-key">\(<a href="https:\/\/[^"]+\/browse\/([A-Z][A-Z0-9]+-\d+|\{\{[^}]+\}\})"[^>]*>([^<]+)</);
if (!keyM) errors.push('제목의 이슈 키가 Jira 이슈 링크(<span class="issue-key">(<a href=".../browse/키">키</a>)</span>)가 아님');
else if (keyM[1] !== keyM[2].trim()) errors.push(`제목의 이슈 키 링크(${keyM[1]})와 글자(${keyM[2].trim()})가 다름`);

// 2. 외부 스크립트: 버전을 고정한 mermaid 하나만
const imports = [...html.matchAll(/import\(['"]([^'"]+)['"]\)|<script[^>]+src="([^"]+)"/g)].map(m => m[1] || m[2]);
for (const u of imports) {
  if (!/^https:\/\/cdn\.jsdelivr\.net\/npm\/mermaid@\d+\.\d+\.\d+\//.test(u)) errors.push(`허용하지 않는 외부 스크립트: ${u}`);
}
if (!imports.length) errors.push('mermaid 불러오기가 없음(템플릿 스크립트를 지웠는지 확인)');

// 3. 절 순서와 목차
const ORDER = ['background', 'goals', 'design', 'alternatives', 'risks', 'questions', 'rollout', 'tests', 'qa'];
const secIds = [...body.matchAll(/<section class="sec" id="([^"]+)"/g)].map(m => m[1]);
if (secIds.join() !== ORDER.join()) errors.push(`절 순서가 다름: ${secIds.join(' → ')} (기대 ${ORDER.join(' → ')})`);
const navIds = [...(body.match(/<nav class="rail-nav"[\s\S]*?<\/nav>/) || [''])[0].matchAll(/href="#([^"]+)"/g)].map(m => m[1]);
if (navIds.join() !== ORDER.join()) errors.push('왼쪽 목차의 링크 순서가 절 순서와 다름');
const navCount = (id) => num(((body.match(new RegExp(`<a href="#${id}">[^\\n]*?<span class="nav-count">(\\d+)</span>`)) || [])[1]));
if ((body.match(/aria-current="step"/g) || []).length !== 1) errors.push('문서 상태 단계에 aria-current="step"이 정확히 하나여야 함');

// 4. 링크 대상
const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
for (const m of body.matchAll(/href="#([^"]+)"/g)) if (!ids.has(m[1])) errors.push(`링크 대상 없음: #${m[1]}`);
for (const m of body.matchAll(/href="(https?:[^"]+)"/g)) {
  const trackerHosts = (process.env.TECHSPEC_TRACKER_HOSTS || '').split(',').map((h) => h.trim()).filter(Boolean);
  const isTracker = /^https:\/\/[a-z0-9-]+\.atlassian\.net\//.test(m[1]) || trackerHosts.some((h) => m[1].startsWith(`https://${h}/`));
  if (!/^https:\/\/claude\.ai\/(code\/)?artifact\//.test(m[1]) && !isTracker) warn.push(`외부 링크는 화면기획서·이슈 트래커만 둔다: ${m[1]}`);
}

// 5. 설계: 흐름도
const design = sectionOf('design');
if (!/class="flow-src"/.test(html) || !flows.length) errors.push('설계 절에 흐름도(flow-src)가 없음');
const figs = (design.match(/<figure class="flow"/g) || []).length;
if (figs !== flows.length) errors.push(`figure.flow ${figs}개와 flow-src ${flows.length}개가 다름`);
for (const [i, f] of flows.entries()) {
  if (/classDef|linkStyle/.test(f)) warn.push(`흐름도 ${i + 1}: classDef·linkStyle 대신 :::색 클래스와 %% group, 화살표 모양을 쓴다`);
  if (/hsl\(/.test(f)) errors.push(`흐름도 ${i + 1}: hsl() 색은 Mermaid에서 깨진다`);
  if (/^\s*stateDiagram/.test(f) && !/%%\s*paint\s/.test(f)) warn.push(`상태도 ${i + 1}: %% paint 줄이 없어 상태 색이 칠해지지 않음`);
  if (/^\s*(flowchart|graph)/.test(f) && !/==>/.test(f)) warn.push(`흐름도 ${i + 1}: 정상 경로(==>)가 없음`);
}

// 6. 열린 질문: 묶음·번호·건수
const qs = sectionOf('questions');
const qItems = [...qs.matchAll(/<li id="(Q\d+)" class="check-row([^"]*)">([\s\S]*?)<\/details><\/li>/g)];
qItems.forEach((m, i) => { if (m[1] !== `Q${i + 1}`) errors.push(`질문 번호가 순서대로가 아님: ${m[1]} (기대 Q${i + 1})`); });
const groups = { review: 0, impl: 0, next: 0 };
for (const g of Object.keys(groups)) {
  const gm = qs.match(new RegExp(`<div class="qgroup[^"]*" id="q-${g}">([\\s\\S]*?)</ol>`));
  if (!gm) continue;
  const items = [...gm[1].matchAll(/<li id="Q\d+"/g)].length;
  groups[g] = items;
  const shown = num((gm[1].match(/<span class="qg-count">(\d+)<\/span>/) || [])[1]);
  if (shown !== items) errors.push(`q-${g} 묶음 건수 ${shown}와 실제 ${items}가 다름`);
  if (!items) errors.push(`q-${g} 묶음이 비어 있음(비면 묶음째 지운다)`);
  const band = num((body.match(new RegExp(`class="k-${g}"[^>]*>[\\s\\S]*?<b>(\\d+)</b>`)) || [])[1]);
  if (band !== items) errors.push(`상태 띠의 ${g} 건수 ${band ?? '없음'}와 실제 ${items}가 다름`);
  const rail = num((body.match(new RegExp(`<nav class="phase-index"[\\s\\S]*?href="#q-${g}"><span>[^<]*</span><strong>(\\d+)</strong>`)) || [])[1]);
  if (rail !== items) errors.push(`왼쪽 질문 시점의 ${g} 건수 ${rail ?? '없음'}와 실제 ${items}가 다름`);
}
for (const g of Object.keys(groups)) if (!groups[g] && new RegExp(`class="k-${g}"|href="#q-${g}"`).test(body)) errors.push(`q-${g} 묶음이 없는데 띠나 목차에 칩이 남아 있음`);
if (navCount('questions') !== qItems.length) errors.push(`목차의 열린 질문 수 ${navCount('questions')}와 실제 ${qItems.length}가 다름`);
const qN = num((qs.match(/<span class="n">(\d+)건/) || [])[1]);
if (qN !== qItems.length) errors.push(`열린 질문 제목 옆 건수 ${qN}와 실제 ${qItems.length}가 다름`);
for (const m of qItems) {
  const t = text((m[3].match(/<h3 class="c-title">([\s\S]*?)<\/h3>/) || ['', ''])[1]);
  if (!t.endsWith('?')) errors.push(`${m[1]} 제목이 질문(?)으로 끝나지 않음: ${t.slice(0, 30)}`);
  if (t.length > 70) warn.push(`${m[1]} 제목이 70자를 넘음(${t.length}자)`);
  if (!/class="chip who"/.test(m[3])) errors.push(`${m[1]}에 답할 사람 칩(chip who)이 없음`);
  if (!/class="rec-dt"/.test(m[3])) errors.push(`${m[1]}에 추천이 없음`);
}
const reviewBlock = (qs.match(/id="q-review">([\s\S]*?)<\/ol>/) || ['', ''])[1];
for (const m of reviewBlock.matchAll(/<li id="(Q\d+)"[\s\S]*?<\/details><\/li>/g)) {
  if (!/class="opts-q"/.test(m[0])) errors.push(`${m[1]}: 검토 중 질문에 선택지가 없음`);
  if (!/class="if-dt"/.test(m[0])) errors.push(`${m[1]}: 검토 중 질문에 "틀리면"이 없음`);
  if ((m[0].match(/class="rec-tag"/g) || []).length !== 1) errors.push(`${m[1]}: 추천 표시(rec-tag)가 정확히 하나여야 함`);
}

// 7. 상태 띠 단어와 질문의 일치
const stateCls = (body.match(/<div class="state([^"]*)" role="status">/) || [])[1];
const word = text((body.match(/<span class="word">([\s\S]*?)<\/span>/) || ['', ''])[1]);
if (stateCls == null) errors.push('상태 띠(div.state)가 없음');
else if (groups.review > 0) { if (word !== '검토 후 개발' || stateCls.trim()) errors.push(`검토 중 질문이 있으면 class="state" + "검토 후 개발"이어야 함 (지금 "${word}")`); }
else if (/hold/.test(stateCls)) { if (word !== '보류') errors.push(`class="state hold"면 단어는 "보류" (지금 "${word}")`); }
else if (word !== '개발 가능' || !/\bgo\b/.test(stateCls)) errors.push(`검토 중 질문이 없으면 class="state go" + "개발 가능"이어야 함 (지금 "${word}")`);

// 8. 위험: 번호·필드·격자
const rs = sectionOf('risks');
const rItems = [...rs.matchAll(/<li id="(R\d+)" class="check-row (sev-[hml])">([\s\S]*?)<\/details><\/li>/g)];
rItems.forEach((m, i) => { if (m[1] !== `R${i + 1}`) errors.push(`위험 번호가 순서대로가 아님: ${m[1]}`); });
for (const m of rItems) {
  if ((m[3].match(/class="chip lv-[hml]"/g) || []).length !== 2) errors.push(`${m[1]}: 영향·가능성 칩이 두 개여야 함`);
  const dts = [...m[3].matchAll(/<dt>([^<]+)<\/dt>/g)].map(x => x[1]);
  if (dts.join() !== '영향,대응,감지') errors.push(`${m[1]}: 영향·대응·감지 세 줄이어야 함 (지금 ${dts.join('·')})`);
  const dots = (rs.match(new RegExp(`<a class="dot" href="#${m[1]}">`, 'g')) || []).length;
  if (dots !== 1) errors.push(`${m[1]}: 격자에 점이 ${dots}개 (정확히 하나)`);
  const cell = (rs.match(new RegExp(`<div class="cell ([hml])"[^>]*>(?:(?!</div>).)*href="#${m[1]}"`, 's')) || [])[1];
  if (cell && `sev-${cell}` !== m[2]) warn.push(`${m[1]}: 행 색(${m[2]})과 격자 칸 색(${cell})이 다름`);
}
const rBand = num((body.match(/class="k-risk"[^>]*>[\s\S]*?<b>(\d+)<\/b>/) || [])[1]);
if ((rBand ?? 0) !== rItems.length) errors.push(`상태 띠의 위험 건수 ${rBand ?? '없음'}와 실제 ${rItems.length}가 다름`);
if (navCount('risks') !== rItems.length) errors.push(`목차의 위험 수 ${navCount('risks')}와 실제 ${rItems.length}가 다름`);
if (num((rs.match(/<span class="n">(\d+)건/) || [])[1]) !== rItems.length) errors.push('위험 제목 옆 건수가 실제와 다름');

// 9. 대안
const al = sectionOf('alternatives');
const alts = [...al.matchAll(/<article class="alt">([\s\S]*?)<\/article>/g)];
alts.forEach((m, i) => { if ((m[1].match(/class="opt pick"/g) || []).length !== 1) errors.push(`대안 ${i + 1}: 채택(opt pick)이 정확히 하나여야 함`); });
if (navCount('alternatives') !== alts.length) errors.push(`목차의 대안 수 ${navCount('alternatives')}와 실제 ${alts.length}가 다름`);
if (num((al.match(/<span class="n">결정 (\d+)건/) || [])[1]) !== alts.length) errors.push('대안 제목 옆 "결정 N건"이 실제와 다름');

// 10. 출시 계획: 선행 작업 건수
const pre = (sectionOf('rollout').match(/<li class="stage pre"/g) || []).length;
const dBand = num((body.match(/class="k-dep"[^>]*>[\s\S]*?<b>(\d+)<\/b>/) || [])[1]);
if ((dBand ?? 0) !== pre) errors.push(`상태 띠의 선행 작업 ${dBand ?? '없음'}와 출시 계획의 stage pre ${pre}개가 다름`);

// 11. 테스트와 Q&A 건수
const tests = (sectionOf('tests').match(/<li><span class="tbox"/g) || []).length;
if (num((sectionOf('tests').match(/<span class="n">검증할 동작 (\d+)건/) || [])[1]) !== tests) errors.push('테스트 제목 옆 건수가 실제와 다름');
const qa = (sectionOf('qa').match(/<li><details>/g) || []).length;
if (navCount('qa') !== qa) errors.push(`목차의 Q&A 수 ${navCount('qa')}와 실제 ${qa}가 다름`);
if (num((sectionOf('qa').match(/<span class="n">(\d+)건/) || [])[1]) !== qa) errors.push('Q&A 제목 옆 건수가 실제와 다름');

// 12. 설계와 상관없는 메타
const plain = text(body);
for (const [re, why] of [[/Codex|세션안|AI 리뷰|리뷰 \d+회|검토 \d+회/, '작성 과정(누가 리뷰했는지)'], [/docs\/superpowers|\.md\b|커밋 [0-9a-f]{7}|\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b/, '원본 경로·커밋'], [/결정 대기함/, '결정 대기함 링크']]) {
  const m = plain.match(re); if (m) errors.push(`${why}가 본문에 있음: "${m[0]}"`);
}

if (previewOut) {
  writeFileSync(previewOut, '<!doctype html><html lang="ko"><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">\n' + html.replace(/(<\/style>)/, '$1\n</head><body>') + '\n</body></html>');
  console.log('미리보기: ' + previewOut);
}
for (const w of new Set(warn)) console.log('경고: ' + w);
for (const e of new Set(errors)) console.log('오류: ' + e);
console.log(`질문 ${qItems.length}건(검토 ${groups.review} · 구현 ${groups.impl} · 다음 ${groups.next}) · 위험 ${rItems.length} · 대안 ${alts.length} · 오류 ${errors.length} · 경고 ${warn.length}`);
process.exit(errors.length ? 1 : 0);
