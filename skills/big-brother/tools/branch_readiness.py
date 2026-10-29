#!/usr/bin/env python3
"""merge_readiness.py 결과를 브랜치 단위로 묶고, 이슈 상태로 "지금 main에 머지할 수준인가"를 판정한다.

충돌이 아니라 기능·테스트 관점의 판정이다. 브랜치에 걸린 이슈(머지 점검 대상 + 브랜치 이슈의 하위 이슈)의 상태를
--status-groups로 받은 묶음에 넣어 아래 순서로 정한다.
  main에 있음 → 개발 중(dev 묶음이 하나라도 있음) → 머지 가능(모두 tested) → 테스트 중(tested·testing이 일부) → 테스트 전

입력
  --merge     merge_readiness.py 출력 JSON
  --branch-issues  브랜치 이름의 이슈 정보 [{key, summary, type?, description?}] (description은 마크다운, 목표 절을 뽑는다)
  --related   하위 이슈 [{key, summary, status, parent}]
  --status-groups  {"dev": [...], "deployed": [...], "testing": [...], "tested": [...], "done": [...], "planned": [...], "ignore": [...]}
                   done은 끝난 일(완료 등)이라 '모두 끝남'에는 세지만 '테스트 중' 근거로는 쓰지 않는다.
  --epic-types     에픽으로 볼 이슈 유형 이름(쉼표 구분). 에픽 자신의 상태는 판정에 넣지 않는다.
"""
import argparse
import json
import re


def goal_of(desc):
    if not desc:
        return ''
    m = re.search(r'^#+\s*(목표|목적|Goal)\s*$(.*?)(?=^#+\s|\Z)', desc, flags=re.M | re.S)
    body = m.group(2) if m else desc
    for line in body.splitlines():
        t = re.sub(r'^\s*([*\-]|\d+\.)\s*', '', line).strip()
        t = re.sub(r'<[^>]+>', '', t).replace('**', '').strip()
        if t:
            return t[:160]
    return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--merge', required=True)
    ap.add_argument('--branch-issues', required=True)
    ap.add_argument('--related', default='')
    ap.add_argument('--status-groups', required=True, help='JSON 문자열 또는 파일 경로')
    ap.add_argument('--epic-types', default='')
    ap.add_argument('--branch-prefix', default='feature/')
    ap.add_argument('--out', default='-')
    a = ap.parse_args()

    sg = a.status_groups
    groups = json.loads(open(sg).read() if not sg.lstrip().startswith('{') else sg)
    group_of = {s: g for g, ss in groups.items() for s in ss}
    epic_types = set(x.strip() for x in a.epic_types.split(',') if x.strip())
    merge = json.load(open(a.merge))
    binfo = {i['key']: i for i in json.load(open(a.branch_issues))}
    related = json.load(open(a.related)) if a.related else []

    branches = {}
    for r in merge:
        b = r['branch'] or ''
        name = b or f"(브랜치 없음) {r['key']}"
        g = branches.setdefault(name, {'branch': name, 'gitVerdict': r['verdict'], 'pr': r.get('pr', ''),
                                       'migrations': r.get('migrations', 0), 'issues': {}, 'checkedAt': r.get('checkedAt', '')})
        g['issues'][r['key']] = {'summary': r.get('summary', ''), 'status': r.get('status', '')}

    # 자기 브랜치가 없는 상위 이슈는 하위 이슈가 가장 많이 든 브랜치에 넣는다
    parent_of = {c['key']: c.get('parent') for c in related}
    for name in [n for n in branches if n.startswith('(브랜치 없음) ')]:
        key = name.split(' ')[-1]
        hits = {n: sum(1 for k in g['issues'] if parent_of.get(k) == key) for n, g in branches.items() if n != name}
        best = max(hits, key=hits.get) if hits else None
        if best and hits[best]:
            branches[best]['issues'].update(branches.pop(name)['issues'])

    rows = []
    for name, g in branches.items():
        bkey = name[len(a.branch_prefix):] if name.startswith(a.branch_prefix) else name.split(' ')[-1]
        info = binfo.get(bkey, {})
        issues = dict(g['issues'])
        planned = []
        for c in related:
            if c.get('parent') != bkey or c['key'] in issues:
                continue
            grp = group_of.get(c['status'])
            if grp == 'planned':
                planned.append(c['key'])
            elif grp and grp != 'ignore':
                issues[c['key']] = {'summary': c['summary'], 'status': c['status']}
        if info.get('type') in epic_types:
            issues.pop(bkey, None)
        counts = {}
        dev = []
        for k, v in issues.items():
            grp = group_of.get(v['status'], 'other')
            counts[grp] = counts.get(grp, 0) + 1
            if grp == 'dev':
                dev.append(k)
        total = sum(counts.values())
        tested = counts.get('tested', 0)
        finished = tested + counts.get('done', 0)
        if g['gitVerdict'] == 'main에 있음':
            level, detail = 'main에 있음', ''
        elif dev:
            level, detail = '개발 중', f"개발 중 {len(dev)}건: {', '.join(sorted(dev))}"
        elif total and finished == total:
            level, detail = '머지 가능', f'{total}건 모두 테스트 완료 또는 완료'
        elif tested or counts.get('testing'):
            level, detail = '테스트 중', f"테스트 완료 {tested}/{total - counts.get('done', 0)}" + (f", 테스트 중 {counts['testing']}" if counts.get('testing') else '')
        else:
            dep = counts.get('deployed', 0)
            level, detail = '테스트 전', (f'{dep}건 통합개발서버 배포됨, ' if dep else '') + '테스트 기록 없음'
        if planned:
            detail += ('; ' if detail else '') + f"계획만 있는 하위 {len(planned)}건 제외({', '.join(sorted(planned))})"
        rows.append({
            'branch': name, 'issueKey': bkey, 'title': info.get('summary') or next(iter(g['issues'].values()))['summary'],
            'goal': goal_of(info.get('description', '')), 'issues': ', '.join(sorted(issues)), 'issueCount': total,
            'level': level, 'levelDetail': detail, 'pr': g['pr'], 'migrations': g['migrations'], 'checkedAt': g['checkedAt'],
        })
    order = {'머지 가능': 0, '테스트 중': 1, '테스트 전': 2, '개발 중': 3, 'main에 있음': 4}
    rows.sort(key=lambda r: (order.get(r['level'], 5), r['branch']))
    text = json.dumps(rows, ensure_ascii=False, indent=1)
    if a.out == '-':
        print(text)
    else:
        open(a.out, 'w').write(text + '\n')


if __name__ == '__main__':
    main()
