#!/usr/bin/env python3
"""이슈별 기능 브랜치가 기준 브랜치(main)에 머지될 수 있는 상태인지 실제 머지 없이 확인한다.

입력: 이슈 목록 JSON [{"key", "summary"?, "status"?, "parent"?}, ...] (조율 세션이 이슈 트래커에서 뽑아 넘긴다)
출력: 이슈마다 한 줄인 JSON 배열(현황판 데이터 파일로 그대로 올린다)

브랜치 찾는 순서: <prefix><key> → 원격 브랜치 중 커밋 메시지가 "<key> "로 시작하는 커밋을 가진 것 → 상위 이슈 브랜치.
충돌은 `git merge-tree --write-tree`(git 2.38 이상)로 작업 트리를 건드리지 않고 계산한다. 테스트는 돌리지 않는다.

Bitbucket PR 상태를 함께 보려면 --bitbucket <workspace>/<repo>와 환경 변수 BITBUCKET_USER(Atlassian 계정 이메일)·BITBUCKET_TOKEN을 준다.
"""
import argparse
import base64
import datetime
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request


def git(repo, *args, check=True):
    p = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p


def remote_branches(repo, remote):
    out = git(repo, 'for-each-ref', '--format=%(refname:strip=3)', f'refs/remotes/{remote}/').stdout.split()
    return set(b for b in out if b != 'HEAD')


def branches_with_key_commits(repo, remote, base, key):
    """기준 브랜치에 없는 커밋 중 메시지가 '<key> '로 시작하는 커밋을 가진 원격 브랜치."""
    p = git(repo, 'log', f'--remotes={remote}/*', '--not', f'{remote}/{base}', '--format=%H %s', check=False)
    shas = [l.split(' ', 1)[0] for l in p.stdout.splitlines() if l.split(' ', 1)[-1].startswith(key + ' ')]
    found = []
    for sha in shas[:3]:
        for b in git(repo, 'branch', '-r', '--contains', sha, '--format=%(refname:strip=3)', check=False).stdout.split():
            if b != 'HEAD' and b not in found:
                found.append(b)
    return found


def key_in_base(repo, remote, base, key):
    p = git(repo, 'log', f'{remote}/{base}', '--format=%s', '--fixed-strings', f'--grep={key} ', '-n', '1', check=False)
    return bool(p.stdout.strip())


def pr_status(bb, branch):
    if not bb:
        return ''
    user, token = os.environ.get('BITBUCKET_USER'), os.environ.get('BITBUCKET_TOKEN')
    if not user or not token:
        return ''
    q = urllib.parse.quote(f'source.branch.name="{branch}"')
    url = (f'https://api.bitbucket.org/2.0/repositories/{bb}/pullrequests'
           f'?q={q}&state=OPEN&state=MERGED&state=DECLINED&sort=-updated_on&pagelen=1')
    req = urllib.request.Request(url, headers={'Authorization': 'Basic ' + base64.b64encode(f'{user}:{token}'.encode()).decode()})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            vals = json.load(r).get('values', [])
    except Exception as e:  # PR 조회 실패는 머지 판정을 막지 않는다
        return f'조회 실패({type(e).__name__})'
    if not vals:
        return '없음'
    v = vals[0]
    label = {'OPEN': '열림', 'MERGED': '머지됨', 'DECLINED': '거절됨'}.get(v['state'], v['state'])
    return f"#{v['id']} {label}"


def check(repo, remote, base, prefix, item, branches, bb, generated, migrations_dir):
    key = item['key']
    row = {'key': key, 'summary': item.get('summary', ''), 'status': item.get('status', ''),
           'branch': '', 'via': '', 'verdict': '', 'ahead': None, 'behind': None,
           'conflicts': 0, 'conflictFiles': '', 'generatedOnly': False, 'migrations': 0, 'pr': ''}
    candidates = []
    if prefix + key in branches:
        candidates.append((prefix + key, '자기 브랜치'))
    for b in branches_with_key_commits(repo, remote, base, key):
        candidates.append((b, '커밋이 든 브랜치'))
    parent = item.get('parent')
    if parent and prefix + parent in branches:
        candidates.append((prefix + parent, f'상위 {parent} 브랜치'))
    elif parent:
        for b in branches_with_key_commits(repo, remote, base, parent)[:1]:
            candidates.append((b, f'상위 {parent} 커밋이 든 브랜치'))
    if not candidates:
        row['verdict'] = 'main에 있음' if key_in_base(repo, remote, base, key) else '브랜치 못 찾음'
        return row
    branch, via = candidates[0]
    ref = f'{remote}/{branch}'
    row.update(branch=branch, via=via, pr=pr_status(bb, branch))
    behind, ahead = git(repo, 'rev-list', '--left-right', '--count', f'{remote}/{base}...{ref}').stdout.split()
    row.update(ahead=int(ahead), behind=int(behind))
    if row['ahead'] == 0:
        row['verdict'] = 'main에 있음'
        return row
    changed = git(repo, 'diff', '--name-only', f'{remote}/{base}...{ref}').stdout.split()
    row['migrations'] = sum(1 for f in changed if migrations_dir and f.startswith(migrations_dir.rstrip('/') + '/'))
    p = git(repo, 'merge-tree', '--write-tree', '--name-only', '--no-messages', f'{remote}/{base}', ref, check=False)
    if p.returncode == 0:
        row['verdict'] = '충돌 없음'
        return row
    if p.returncode != 1:
        row['verdict'] = '확인 실패'
        row['conflictFiles'] = p.stderr.strip()[:300]
        return row
    files = [l for l in p.stdout.splitlines()[1:] if l.strip()]
    row['conflicts'] = len(files)
    row['conflictFiles'] = ', '.join(files)
    row['generatedOnly'] = all(f in generated for f in files)
    row['verdict'] = '생성 파일만 충돌' if row['generatedOnly'] else f'충돌 {len(files)}개'
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--remote', default='origin')
    ap.add_argument('--base', default='main')
    ap.add_argument('--branch-prefix', default='feature/')
    ap.add_argument('--issues', required=True, help='이슈 목록 JSON 파일')
    ap.add_argument('--bitbucket', default='', help='<workspace>/<repo>')
    ap.add_argument('--generated', default='', help='다시 만들면 되는 생성 파일 경로(쉼표 구분)')
    ap.add_argument('--migrations-dir', default='')
    ap.add_argument('--no-fetch', action='store_true')
    ap.add_argument('--out', default='-')
    a = ap.parse_args()

    if not a.no_fetch:
        git(a.repo, 'fetch', '-q', '--prune', a.remote)
    branches = remote_branches(a.repo, a.remote)
    generated = set(x.strip() for x in a.generated.split(',') if x.strip())
    items = json.load(open(a.issues))
    now = datetime.datetime.now().astimezone().isoformat(timespec='minutes')
    rows = []
    for it in items:
        r = check(a.repo, a.remote, a.base, a.branch_prefix, it, branches, a.bitbucket, generated, a.migrations_dir)
        r['checkedAt'] = now
        rows.append(r)
    text = json.dumps(rows, ensure_ascii=False, indent=1)
    if a.out == '-':
        print(text)
    else:
        open(a.out, 'w').write(text + '\n')
        counts = {}
        for r in rows:
            v = '충돌 있음' if r['conflicts'] and not r['generatedOnly'] else r['verdict']
            counts[v] = counts.get(v, 0) + 1
        print(f'{len(rows)}건: ' + ', '.join(f'{k} {v}' for k, v in counts.items()), file=sys.stderr)


if __name__ == '__main__':
    main()
