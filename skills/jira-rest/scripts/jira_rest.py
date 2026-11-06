#!/usr/bin/env python3
"""Jira Cloud REST 도우미. 표준 라이브러리만 쓴다.

설정
  사이트  : 환경 변수 JIRA_SITE(예: https://<site>.atlassian.net), 없으면 <스킬>/local/site 파일 한 줄
  인증    : JIRA_AUTH_FILE(기본 ~/.config/jira-session-title/auth), 내용은 "email:api_token" 한 줄.
            읽기만 한다. 이 파일을 고치거나 다른 곳에 복사하지 않는다.

라이브러리로 쓸 때
  import sys; sys.path.insert(0, "<스킬>/scripts"); from jira_rest import *
  status, data = req("GET", "/rest/api/3/issue/KEY-1")   # 언제나 (status, data) tuple
  data = call("GET", "/rest/api/3/issue/KEY-1")          # 2xx가 아니면 JiraError

명령줄은 `python3 jira_rest.py -h`.
"""
import argparse
import base64
import json
import mimetypes
import os
import struct
import sys
import urllib.error
import urllib.request
import uuid

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_FILE = os.path.expanduser(os.environ.get("JIRA_AUTH_FILE", "~/.config/jira-session-title/auth"))
MAX_IMG_WIDTH = 1400


class JiraError(Exception):
    def __init__(self, method, path, status, data):
        super().__init__(f"{method} {path} -> {status}: {str(data)[:500]}")
        self.status, self.data = status, data


def _site():
    site = os.environ.get("JIRA_SITE", "").strip()
    if not site:
        p = os.path.join(SKILL_DIR, "local", "site")
        if os.path.exists(p):
            site = open(p).read().strip()
    if not site:
        sys.exit("JIRA_SITE 환경 변수나 <스킬>/local/site 파일에 사이트 주소를 넣는다")
    return site.rstrip("/")


def _auth_header():
    email, token = open(AUTH_FILE).read().strip().split(":", 1)
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def req(method, path, body=None, headers=None, raw=None):
    """(status, data)를 돌려준다. data는 JSON이면 dict/list, 아니면 앞부분 문자열, 본문이 없으면 None.

    HTTP 오류도 예외 없이 (코드, 응답 본문)으로 돌려준다. 결과를 바로 ["fields"]로 쓰지 말고
    status, data = req(...) 로 풀거나 call()을 쓴다.
    """
    h = {"Authorization": _auth_header(), "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    if raw is not None:
        data = raw
    if headers:
        h.update(headers)
    url = path if path.startswith("http") else _site() + path
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r) as resp:
            text = resp.read().decode()
            status = resp.status
    except urllib.error.HTTPError as e:
        text, status = e.read().decode(errors="replace"), e.code
    try:
        return status, (json.loads(text) if text else None)
    except ValueError:
        return status, text[:2000]


def unwrap(result):
    """req()의 tuple이든 이미 푼 data든 data만 돌려준다(옛 스크립트 호환)."""
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], int):
        return result[1]
    return result


def call(method, path, body=None, **kw):
    status, data = req(method, path, body, **kw)
    if status >= 300:
        raise JiraError(method, path, status, data)
    return data


# ---------- 검색·조회 ----------

def search(jql, fields=("summary", "status"), limit=100):
    """POST /rest/api/3/search/jql. 옛 GET /search는 막혔다. nextPageToken으로 limit까지 모은다."""
    out, token = [], None
    while len(out) < limit:
        body = {"jql": jql, "fields": list(fields), "maxResults": min(100, limit - len(out))}
        if token:
            body["nextPageToken"] = token
        data = call("POST", "/rest/api/3/search/jql", body)
        out += data.get("issues", [])
        token = data.get("nextPageToken")
        if not token or data.get("isLast"):
            break
    return out


def issue(key, fields="summary,status,fixVersions,issuetype,parent"):
    return call("GET", f"/rest/api/3/issue/{key}?fields={fields}")


# ---------- 상태 전환 ----------

def transitions(key):
    return call("GET", f"/rest/api/3/issue/{key}/transitions")["transitions"]


def transition(key, target):
    """target은 전환 id, 전환 이름, 도착 상태 이름 중 하나. 이미 그 상태면 아무것도 하지 않는다."""
    cur = issue(key, "status")["fields"]["status"]["name"]
    if cur == target:
        return f"{key}: 이미 {cur}"
    ts = transitions(key)
    m = [t for t in ts if target in (t["id"], t["name"], t["to"]["name"])]
    if not m:
        raise SystemExit(f"{key}: '{target}' 전환 없음. 가능: " +
                         ", ".join(f'{t["id"]}={t["name"]}->{t["to"]["name"]}' for t in ts))
    call("POST", f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": m[0]["id"]}})
    return f'{key}: {cur} -> {m[0]["to"]["name"]} (id {m[0]["id"]})'


# ---------- 댓글(wiki 마크업, API v2) ----------

def add_comment(key, body):
    return call("POST", f"/rest/api/2/issue/{key}/comment", {"body": body})


def get_comment(key, cid):
    return call("GET", f"/rest/api/2/issue/{key}/comment/{cid}")


def edit_comment(key, cid, body, backup_dir="."):
    """기존 본문을 backup_dir/bak_<cid>.txt에 남기고 바꾼다."""
    old = get_comment(key, cid)["body"]
    with open(os.path.join(backup_dir, f"bak_{cid}.txt"), "w") as f:
        f.write(old)
    return call("PUT", f"/rest/api/2/issue/{key}/comment/{cid}", {"body": body})


def rendered_img_count(key, cid):
    d = call("GET", f"/rest/api/2/issue/{key}/comment/{cid}?expand=renderedBody")
    return d["renderedBody"].count("<img")


# ---------- 첨부와 이미지 마크업 ----------

def image_size(path):
    """PNG/JPEG/GIF 크기를 파일 머리에서 읽는다. 모르면 None."""
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", head[6:10])
        if head[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                b = f.read(1)
                while b and b != b"\xff":
                    b = f.read(1)
                while b == b"\xff":
                    b = f.read(1)
                if not b:
                    return None
                marker = b[0]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    continue
                seg = struct.unpack(">H", f.read(2))[0]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">xHH", f.read(5))
                    return w, h
                f.seek(seg - 2, 1)
    return None


def image_markup(path, max_width=MAX_IMG_WIDTH, caption=True):
    """`*이름*\\n!파일|width=W,height=H!`. 크기를 붙여야 댓글에서 원본 크기로 넘치지 않는다."""
    name = os.path.basename(path)
    size = image_size(path)
    attrs = ""
    if size:
        w, h = size
        if w > max_width:
            w, h = max_width, h * max_width // w
        attrs = f"|width={w},height={h}"
    line = f"!{name}{attrs}!"
    return f"*{name.rsplit('.', 1)[0]}*\n{line}" if caption else line


def attachments(key):
    return {a["filename"] for a in issue(key, "attachment")["fields"]["attachment"]}


def upload(key, path, skip_existing=True):
    """multipart 업로드. 같은 파일명이 이미 있으면 건너뛴다(중복 첨부 방지)."""
    name = os.path.basename(path)
    if skip_existing and name in attachments(key):
        return None
    b = uuid.uuid4().hex
    ct = mimetypes.guess_type(name)[0] or "application/octet-stream"
    body = (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
            f"Content-Type: {ct}\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    return call("POST", f"/rest/api/3/issue/{key}/attachments", raw=body,
                headers={"X-Atlassian-Token": "no-check", "Content-Type": f"multipart/form-data; boundary={b}"})


def attach_images(key, paths, heading=None, text=None, comment_id=None, max_width=MAX_IMG_WIDTH):
    """이미지를 올리고 댓글에 넣는다. comment_id가 있으면 그 댓글 끝에 붙이고(원문 백업), 없으면 새 댓글."""
    for p in paths:
        upload(key, p)
    parts = ([f"h3. {heading}"] if heading else []) + [image_markup(p, max_width) for p in paths]
    section = "\n".join(parts) + "\n"
    if comment_id:
        old = get_comment(key, comment_id)["body"]
        if f"!{os.path.basename(paths[0])}" in old:
            return comment_id, "already"
        edit_comment(key, comment_id, old.rstrip() + "\n\n" + section)
        cid = comment_id
    else:
        cid = add_comment(key, ((text.rstrip() + "\n\n") if text else "") + section)["id"]
    return cid, rendered_img_count(key, cid)


# ---------- 버전 ----------

def project_versions(project):
    return call("GET", f"/rest/api/3/project/{project}/versions")


def ensure_version(project, name, description=None):
    """있으면 그 버전, 없으면 만든다. (version, created)"""
    for v in project_versions(project):
        if v["name"] == name:
            return v, False
    pid = int(call("GET", f"/rest/api/3/project/{project}")["id"])
    body = {"name": name, "projectId": pid}
    if description:
        body["description"] = description
    return call("POST", "/rest/api/3/version", body), True


def add_fix_version(key, name):
    """기존 fixVersions는 두고 하나를 더한다. fields로 넣으면 기존 값이 지워진다."""
    return req("PUT", f"/rest/api/3/issue/{key}", {"update": {"fixVersions": [{"add": {"name": name}}]}})[0]


def release_version(version_id, date, description=None):
    body = {"released": True, "releaseDate": date}
    if description:
        body["description"] = description
    return call("PUT", f"/rest/api/3/version/{version_id}", body)


# ---------- 명령줄 ----------

def _main():
    ap = argparse.ArgumentParser(description="Jira REST 도우미")
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("jql"); s.add_argument("--fields", default="summary,status"); s.add_argument("--limit", type=int, default=50)
    s = sp.add_parser("issue"); s.add_argument("keys", nargs="+"); s.add_argument("--fields", default="summary,status,fixVersions,issuetype,parent")
    s = sp.add_parser("transitions"); s.add_argument("key")
    s = sp.add_parser("transition", help="전환 id·전환 이름·도착 상태 이름"); s.add_argument("target"); s.add_argument("keys", nargs="+")
    s = sp.add_parser("comment"); s.add_argument("key"); s.add_argument("--file", help="wiki 마크업 본문 파일(없으면 stdin)")
    s = sp.add_parser("comments"); s.add_argument("key")
    s = sp.add_parser("attach", help="이미지 업로드 + width/height를 붙인 댓글")
    s.add_argument("key"); s.add_argument("files", nargs="+"); s.add_argument("--heading"); s.add_argument("--text-file")
    s.add_argument("--comment-id", help="이 댓글 끝에 붙인다"); s.add_argument("--max-width", type=int, default=MAX_IMG_WIDTH)
    s.add_argument("--dry-run", action="store_true", help="마크업만 출력")
    s = sp.add_parser("version", help="버전을 만들거나 찾고 이슈에 연결"); s.add_argument("project"); s.add_argument("name")
    s.add_argument("--description"); s.add_argument("--issues", nargs="*", default=[])
    s = sp.add_parser("release", help="버전을 릴리스로 표시"); s.add_argument("version_id"); s.add_argument("date"); s.add_argument("--description")
    s = sp.add_parser("raw", help="임의 요청"); s.add_argument("method"); s.add_argument("path"); s.add_argument("--json")
    a = ap.parse_args()

    if a.cmd == "search":
        for i in search(a.jql, a.fields.split(","), a.limit):
            f = i["fields"]
            print(i["key"], (f.get("status") or {}).get("name", ""), (f.get("summary") or "")[:80], sep="\t")
    elif a.cmd == "issue":
        for k in a.keys:
            print(json.dumps(issue(k, a.fields)["fields"], ensure_ascii=False)[:3000])
    elif a.cmd == "transitions":
        for t in transitions(a.key):
            print(t["id"], t["name"], "->", t["to"]["name"], sep="\t")
    elif a.cmd == "transition":
        for k in a.keys:
            print(transition(k, a.target))
    elif a.cmd == "comment":
        body = open(a.file).read() if a.file else sys.stdin.read()
        print(add_comment(a.key, body)["id"])
    elif a.cmd == "comments":
        for c in call("GET", f"/rest/api/2/issue/{a.key}/comment?maxResults=100")["comments"]:
            print(c["id"], c["author"]["displayName"], c["created"][:16], repr(c["body"][:80]), sep="\t")
    elif a.cmd == "attach":
        if a.dry_run:
            print("\n".join(image_markup(p, a.max_width) for p in a.files))
            return
        text = open(a.text_file).read() if a.text_file else None
        cid, n = attach_images(a.key, a.files, a.heading, text, a.comment_id, a.max_width)
        print(f"comment {cid}, rendered img: {n}")
    elif a.cmd == "version":
        v, created = ensure_version(a.project, a.name, a.description)
        print("created" if created else "exists", v["id"], v["name"], "released" if v.get("released") else "")
        for k in a.issues:
            print(k, add_fix_version(k, a.name))
    elif a.cmd == "release":
        v = release_version(a.version_id, a.date, a.description)
        print(v["id"], v["name"], v.get("released"), v.get("releaseDate"))
    elif a.cmd == "raw":
        status, data = req(a.method, a.path, json.loads(a.json) if a.json else None)
        print(status)
        print(json.dumps(data, ensure_ascii=False, indent=1)[:5000] if not isinstance(data, str) else data)


if __name__ == "__main__":
    _main()
