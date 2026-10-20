---
name: operating-orca-cli
description: Use when the user works in the Orca app and something must appear on their screen — opening a file for them, making a new git worktree show up in the Orca sidebar, starting a new Claude session in a worktree, or driving a browser page the user can watch on their own machine.
---

# Orca CLI로 사용자 화면 다루기

## Overview

사용자는 Windows의 Orca 앱으로 이 VM에 SSH로 붙어 일한다(`TERM_PROGRAM=Orca`). CLI는 PATH의 `orca`(`$ORCA_CLI_COMMAND`, 2026-10-15 기준 `~/.orca/cli/bin/orca`)이고, 명령의 결과는 사용자 Windows 화면에 나타난다. 대상은 항상 `--worktree path:<절대경로>`로 고른다.

## 파일 열기

```bash
orca file open --worktree path:<메인 트리> --path <상대경로 또는 .claude/worktrees 아래 절대경로>
```

- 사용자가 "여기서 보게"라고 하면 메인 트리(git 워크트리들의 원래 체크아웃)를 worktree로 주고 다른 워크트리 파일을 절대경로로 연다.
- 같은 기기의 다른 저장소는 `orca worktree list`에 없으면 "Opened"가 떠도 안 보인다. 메인 트리의 git 무시 경로(예: `.superpowers/sdd/`)에 복사해 연다.

## 새 워크트리를 사이드바에 띄우기

git으로 만든 워크트리는 `orca worktree list`에는 바로 잡히지만 앱 사이드바에는 늦게 뜬다. 만든 직후 둘 다 실행한다.

```bash
orca worktree set --worktree path:<워크트리> --display-name "<이슈키 한글 이름>" --comment "<착수 지시문 위치>" --unread
orca file open --worktree path:<워크트리> --path CLAUDE.md
```

## 새 Claude 세션 띄우기

```bash
orca terminal create --worktree path:<워크트리> --title "<이슈키 한글 이름>" \
  --command "claude --dangerously-skip-permissions '<착수 지시문 경로> 를 읽고 그대로 시작해 줘. 조율 세션 이름은 big-brother다.'" --json
orca terminal read --terminal <handle>   # 시작 출력 확인
```

`--dangerously-skip-permissions`를 빼면 설정 기본값(auto)으로 뜬다. 그러면 권한 모드가 다른 세션끼리 보내는 메시지(SendMessage)가 사용자 승인을 기다리다 만료된다. 이미 그렇게 떴다면 사용자에게 `/exit` 후 `claude --dangerously-skip-permissions --continue`로 다시 열어 달라고 한다. 메시지를 terminal send로 우회 입력하지 않는다.

끊긴 세션을 원래 대화로 다시 띄울 때는 `--command "claude --dangerously-skip-permissions --resume <sessionId>"`를 쓴다. sessionId는 `~/.claude/projects/<워크트리 경로의 / 를 - 로 바꾼 이름>/`에서 가장 최근 `.jsonl`의 파일 이름이다. `orca agent launch`는 새 대화만 열고 특정 대화를 이어 열지 못한다.

## 사용자 화면에서 브라우저 조작

Orca 내장 브라우저 페이지는 사용자 Windows에서 렌더링되어 사용자가 조작 과정을 그대로 본다.

```bash
orca tab create --url <url> --worktree path:<메인 트리> --json   # → browserPageId
orca snapshot --page <id>                       # 요소 ref(@eN) 받기
orca fill --element e3 --value "<값>" --page <id>  # ref는 snapshot이 준 값(@e3 또는 e3)
orca click --element e3 --page <id>
orca eval --expression "<JS>" --page <id>        # 같은 출처 iframe 이동 등
orca screenshot --format png --page <id>
orca goto --url <url> --page <id>              # 같은 탭에서 이동
```

- 명령 형식은 `orca <명령> --help`와 `orca agent-context`가 최신이다. `fill`·`click` 전에 매번 `snapshot`으로 ref를 새로 받는다. 옛 ref로 fill하면 빈 칸으로 제출된다.
- 비밀번호는 파일에서 읽어 `--value`로 넘기고 대화에 출력하지 않는다.
- 특정 서비스의 로그인·화면 이동 절차는 그 환경의 전용 스킬이 있으면 따른다.

## Common Mistakes

| 증상 | 고치는 법 |
| --- | --- |
| 워크트리를 만들었는데 사용자 사이드바에 없음 | `worktree set` + `file open` |
| 새 세션에 보낸 메시지가 보류·만료 | 세션을 `--dangerously-skip-permissions`로 다시 띄움 |
| Orca 앱 재시작 뒤 ListAgents에 같은 이름 둘 | 옛 claude 프로세스가 살아 있음. `claude-sessions <저장소>`와 `~/.claude/sessions/<pid>.json`으로 짝을 찾아, 사용자 확인 뒤 옛 PID만 SIGTERM |
| fill했는데 입력칸이 비어 있음 | snapshot을 다시 받고 새 ref로 fill |
| `Orca SSH CLI bridge cannot find the relay socket` | 옛 relay 래퍼(`~/.orca-relay/bin/orca`)를 부른 것. Orca 업데이트 뒤 relay 소켓이 사라진다. 경로를 적지 말고 PATH의 `orca`나 `$ORCA_CLI_COMMAND`를 쓴다 |
| Orca 업데이트 뒤 사이드바 이름이 브랜치명으로 바뀜 | `worktree set --display-name "<이슈키 한글 이름>"`으로 되돌림 |
