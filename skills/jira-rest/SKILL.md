---
name: jira-rest
description: Use when a Jira Cloud task needs the REST API directly — attaching screenshots to an issue comment, editing an existing comment, creating or linking a fix version, releasing a version, bulk status transitions, or JQL searches — especially when the Atlassian MCP tools cannot do it (no attachment upload, no version API) or the old GET /rest/api/3/search returns 410.
---

# Jira REST 도우미

`scripts/jira_rest.py` 하나로 Jira Cloud REST를 부릅니다. 세션마다 scratchpad에 `j.py`를 새로 짜지 않고 이 스크립트를 명령줄이나 라이브러리로 씁니다.

## 설정

| 항목 | 어디서 읽나 |
| --- | --- |
| 사이트 주소 | 환경 변수 `JIRA_SITE`(예: `https://<site>.atlassian.net`). 없으면 `<스킬>/local/site` 파일 한 줄. `local/`은 저장소에서 추적하지 않습니다 |
| 인증 | `JIRA_AUTH_FILE`, 기본 `~/.config/jira-session-title/auth`. 내용은 `email:api_token` 한 줄 |

**인증 파일은 읽기만 합니다.** 고치거나 다른 곳(scratchpad, `local/`, 메모리)에 복사하지 않습니다. 사이트 주소·이슈 키·버전 id 같은 환경 값은 이 스킬 파일에 적지 않습니다.

## 명령줄

`J=~/.claude/skills/jira-rest/scripts/jira_rest.py`로 두고, 백업 파일이 생기므로 scratchpad에서 실행합니다.

| 할 일 | 명령 |
| --- | --- |
| JQL 검색 | `python3 $J search 'project=KEY AND fixVersion="1.2.3"' --fields summary,status --limit 200` |
| 이슈 필드 보기 | `python3 $J issue KEY-1 KEY-2 --fields summary,status,fixVersions` |
| 가능한 전환 보기 | `python3 $J transitions KEY-1` — 열은 `id 전환이름 -> 도착상태` |
| 상태 전환(여러 건) | `python3 $J transition 완료 KEY-1 KEY-2` — 전환 id, 전환 이름, 도착 상태 이름 모두 받습니다. 이미 그 상태면 건너뜁니다. 같은 이름의 전환이 둘 이상이면(예: 서로 다른 "백로그") 첫 번째를 고르므로 id로 넘깁니다 |
| 댓글 달기(wiki 마크업) | `python3 $J comment KEY-1 --file body.txt` 또는 stdin |
| 댓글 목록 | `python3 $J comments KEY-1` |
| 스크린샷 붙이기(새 댓글) | `python3 $J attach KEY-1 a.png b.jpg --heading '화면 기록' --text-file body.txt` |
| 기존 댓글 끝에 스크린샷 | `python3 $J attach KEY-1 a.png --comment-id 12345` — 원문을 `bak_12345.txt`로 남기고 붙입니다. 이미 붙어 있으면 `already` |
| 마크업만 미리 보기 | `python3 $J attach KEY-1 a.png --dry-run` — 넘긴 파일만 대상입니다. `dir/*`처럼 넘기면 텍스트 파일까지 들어가니 이미지만 고릅니다 |
| 버전 만들기·연결 | `python3 $J version KEY 1.2.3 --description '...' --issues KEY-1 KEY-2` — `--description`·`--issues`는 생략할 수 있습니다. 있으면 그대로 쓰고, 이슈의 기존 fixVersions는 지우지 않고 더합니다 |
| 버전 릴리스 표시 | `python3 $J release <version_id> 2026-11-05 --description '...'` |
| 그 밖의 요청 | `python3 $J raw GET /rest/agile/1.0/board/<id>/configuration` |

`attach`는 끝에 `rendered img: N`을 찍습니다. 붙인 이미지 수와 다르면 렌더링이 깨진 것이니 댓글을 열어 확인합니다.

## 라이브러리로 쓸 때

여러 이슈를 한 번에 처리하는 일회성 스크립트는 이 모듈을 불러 씁니다.

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/jira-rest/scripts"))
from jira_rest import req, call, unwrap, JiraError, search, transition, attach_images, ensure_version, add_fix_version

status, data = req("GET", "/rest/api/3/issue/KEY-1?fields=status")   # req(method, path, body=None, headers=None, raw=None)
if status == 404: print("없음", data)                                # 오류 때 data는 Jira 오류 JSON(dict)이나 본문 문자열
data = call("PUT", "/rest/api/3/issue/KEY-1", {"fields": {"labels": ["보류"]}})  # 2xx가 아니면 JiraError(.status, .data)

for i in search('project=KEY AND status="(5-3)테스트 완료"', ["summary"]):
    print(transition(i["key"], "완료"))
v, created = ensure_version("KEY", "1.2.4", "수정 버전")
```

## 지키는 형태

| 규칙 | 이유 |
| --- | --- |
| `req()`는 **언제나 `(status, data)` tuple**을 돌려줍니다. `status, data = req(...)`로 풀거나 2xx만 받으면 `call()`을 씁니다. 옛 스크립트처럼 결과를 dict로 쓴 코드는 `unwrap(req(...))`로 감쌉니다 | `req(...)["fields"]`는 `TypeError: tuple indices`로 죽고, HTTP 오류도 예외 없이 돌아오므로 status를 안 보면 실패를 놓칩니다. 네트워크 오류(접속 실패)만 예외로 올라옵니다 |
| 검색은 `POST /rest/api/3/search/jql`, 다음 쪽은 `nextPageToken` | 옛 `GET /rest/api/3/search`는 막혔고, 새 API는 `total`·`startAt`이 없습니다 |
| 댓글 본문은 API v2(`/rest/api/2/.../comment`)에 wiki 마크업으로 보냅니다 | v3는 ADF JSON만 받습니다 |
| 이미지 마크업에는 `width=W,height=H` 속성을 붙이고 폭은 1400 이하로 줄입니다(`image_markup`이 `!a.png` 뒤에 붙임) | 크기 없이 `!a.png!`만 쓰면 댓글에서 원본 크기로 펼쳐져 화면을 넘칩니다 |
| 첨부는 같은 파일명이 이미 있으면 다시 올리지 않습니다 | 다시 돌릴 때 같은 그림이 여러 장 쌓입니다 |
| fixVersion은 `update.fixVersions.add`로 더합니다(`add_fix_version`) | `fields.fixVersions`로 넣으면 기존 버전이 지워집니다 |
| 기존 댓글을 바꿀 때는 원문을 먼저 파일로 남깁니다(`edit_comment`) | Jira에는 댓글 이력이 없어 잘못 덮으면 되살릴 수 없습니다 |

## 흔한 실수

| 실수 | 바로잡기 |
| --- | --- |
| 스크립트 안에 사이트 주소·토큰을 적음 | `JIRA_SITE`와 인증 파일에서 읽음 |
| 인증 파일을 scratchpad에 복사해 씀 | 경로만 넘김(`JIRA_AUTH_FILE`) |
| 전환 id를 기억으로 씀 | `transitions`로 보거나 도착 상태 이름으로 넘김. 프로젝트마다 id가 다릅니다 |
| 버전 이름으로 새 버전을 또 만듦 | `ensure_version`/`version` 명령은 있으면 그 버전을 씁니다 |
