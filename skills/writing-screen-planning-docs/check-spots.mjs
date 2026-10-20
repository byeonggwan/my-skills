#!/usr/bin/env node
// 화면기획서 HTML의 구조 일관성을 검사한다. 사용: node check-spots.mjs <file.html>
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const file = process.argv[2];
const pv = process.argv.indexOf('--preview');
const previewOut = pv > 0 ? process.argv[pv + 1] : null;
if (!file) { console.error('사용법: node check-spots.mjs <file.html>'); process.exit(2); }
const html = readFileSync(file, 'utf8');
const errors = [];
const warn = [];

// 1. 채우지 않은 자리표시자
const left = html.match(/\{\{[^}]*\}\}/g);
if (left) errors.push(`자리표시자 ${left.length}개가 남아 있음: ${[...new Set(left)].slice(0, 5).join(' ')}`);

// 1-1. 머리의 이슈 키는 Jira 이슈 링크
const eyebrow = (html.match(/<div class="eyebrow">([\s\S]*?)<\/div>/) || [])[1] || '';
if (/[A-Z][A-Z0-9]+-\d+/.test(eyebrow.replace(/<[^>]+>/g, '')) && !/<a href="https:\/\/[^"]+\/browse\/[A-Z][A-Z0-9]+-\d+"/.test(eyebrow)) errors.push('머리(eyebrow)의 이슈 키가 Jira 이슈 링크가 아님');

// 2. 화면 탭 ↔ 화면 섹션
const tabs = [...html.matchAll(/<button data-screen="([^"]+)"/g)].map(m => m[1]);
const pages = [...html.matchAll(/class="screen-page" data-screen="([^"]+)"/g)].map(m => m[1]);
for (const t of tabs) if (!pages.includes(t)) errors.push(`탭 ${t}에 대응하는 .screen-page 없음`);
for (const p of pages) if (!tabs.includes(p)) errors.push(`화면 ${p}에 대응하는 탭 버튼 없음`);
if (tabs.length === 0) errors.push('화면 탭이 없음');

// 3. 스크립트 상수 추출
const script = html.slice(html.lastIndexOf('<script>'));
function grab(name) {
  const start = script.indexOf(`const ${name} = `);
  if (start < 0) { errors.push(`const ${name} 을 찾지 못함`); return {}; }
  let i = script.indexOf('{', start), depth = 0, inStr = null;
  for (let j = i; j < script.length; j++) {
    const c = script[j];
    if (inStr) { if (c === '\\') j++; else if (c === inStr) inStr = null; continue; }
    if (c === '"' || c === "'" || c === '`') inStr = c;
    else if (c === '{') depth++;
    else if (c === '}' && --depth === 0) {
      try { return vm.runInNewContext(`(${script.slice(i, j + 1)})`); } catch (e) { errors.push(`${name} 파싱 실패: ${e.message}`); return {}; }
    }
  }
  errors.push(`const ${name} 의 중괄호가 닫히지 않음`); return {};
}
const SPOTS = grab('SPOTS');
const SCREEN_SPOTS = grab('SCREEN_SPOTS');
const NOW = grab('NOW');

// 4. 화면별 spot ↔ SPOTS ↔ SCREEN_SPOTS
const sections = [...html.matchAll(/<section class="screen-page" data-screen="([^"]+)"[\s\S]*?<\/section>/g)];
for (const sec of sections) {
  const id = sec[1];
  const body = sec[0];
  const inDom = [...body.matchAll(/data-spot="([^"]+)"/g)].map(m => m[1]);
  const listed = SCREEN_SPOTS[id] || [];
  for (const s of new Set(inDom)) {
    if (!SPOTS[s]) errors.push(`화면 ${id}: data-spot="${s}" 에 대한 SPOTS 항목 없음`);
    if (!listed.includes(s)) errors.push(`화면 ${id}: data-spot="${s}" 가 SCREEN_SPOTS.${id} 에 없음`);
  }
  for (const s of listed) if (!inDom.includes(s)) errors.push(`화면 ${id}: SCREEN_SPOTS 에 있는 ${s} 가 목업에 없음`);
  // 번호 연속성
  const ns = listed.map(s => SPOTS[s]?.n).filter(n => n != null).sort((a, b) => a - b);
  if (new Set(ns).size !== ns.length) errors.push(`화면 ${id}: 핀 번호가 중복됨 (${ns.join(',')})`);
  else if (ns.some((n, i) => n !== i + 1)) warn.push(`화면 ${id}: 핀 번호가 1부터 연속이 아님 (${ns.join(',')}) — 여러 화면이 spot 을 공유해 전역 번호를 쓴 경우면 정상`);
  // DOM 핀 텍스트와 n 일치
  for (const m of body.matchAll(/data-spot="([^"]+)"[^>]*>\s*<span class="pin">(\d+)<\/span>/g)) {
    if (SPOTS[m[1]] && SPOTS[m[1]].n !== Number(m[2])) errors.push(`화면 ${id}: ${m[1]} 핀 표기 ${m[2]} ≠ SPOTS.n ${SPOTS[m[1]].n}`);
  }
  // 토글 화면 검사
  const hasToggle = /class="view-toggle"/.test(body);
  if (hasToggle) {
    if (!/data-view="now"[\s\S]*?class="frame view" data-view="now"/.test(body) || !/class="frame view" data-view="next"/.test(body)) errors.push(`화면 ${id}: 토글이 있는데 now/next 프레임이 모두 있지 않음`);
    if (!NOW[id] || NOW[id].length === 0) errors.push(`화면 ${id}: 토글이 있는데 NOW.${id} 가 비어 있음`);
    const nowFrame = body.match(/class="frame view" data-view="now"[\s\S]*?class="frame view" data-view="next"/);
    if (nowFrame && /data-spot=/.test(nowFrame[0])) errors.push(`화면 ${id}: 현재 화면 프레임에 spot 이 있음 (현재 화면에는 변경 지점을 두지 않음)`);
    if (!/class="[^"]*keep/.test(body)) warn.push(`화면 ${id}: 변경 후 프레임에 "그대로"(.keep) 표지가 하나도 없음`);
  } else if (NOW[id]) {
    warn.push(`화면 ${id}: 토글이 없는데 NOW.${id} 가 있음 (쓰이지 않음)`);
  }
}
// 5. SPOTS 필수 필드
for (const [k, s] of Object.entries(SPOTS)) {
  for (const f of ['n', 'title', 'kind', 'what', 'why', 'data']) if (s[f] == null || s[f] === '') errors.push(`SPOTS.${k}.${f} 비어 있음`);
  if (!Object.values(SCREEN_SPOTS).some(a => a.includes(k))) errors.push(`SPOTS.${k} 가 어느 SCREEN_SPOTS 에도 없음`);
}
// 6. 기본 계약
if (!/<title>[^<]*화면기획서<\/title>/.test(html)) warn.push('<title> 이 "… 화면기획서" 형식이 아님');
if (!/prefers-color-scheme: dark/.test(html)) errors.push('다크 모드 토큰 없음');
for (const m of html.matchAll(/<script[^>]*src="([^"]+)"/g)) if (!/cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net\/npm\//.test(m[1])) errors.push(`허용되지 않은 외부 스크립트: ${m[1]}`);

if (previewOut) {
  const { writeFileSync } = await import('node:fs');
  writeFileSync(previewOut, '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:light}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#faf9f5;color:#141413}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>\n' + html + '\n</body></html>');
  console.log('미리보기: ' + previewOut);
}
for (const w of new Set(warn)) console.log('경고: ' + w);
for (const e of new Set(errors)) console.log('오류: ' + e);
console.log(`화면 ${pages.length}개 · 변경 지점 ${Object.keys(SPOTS).length}개 · 오류 ${errors.length} · 경고 ${warn.length}`);
process.exit(errors.length ? 1 : 0);
