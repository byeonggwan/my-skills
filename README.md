# Claude Code 사용자 설정

`~/.claude`에서 직접 관리하는 사용자 범위 스킬·에이전트·훅이다. `~/.claude`에는 인증 파일·대화 기록·메모리가 함께 있으므로, `.gitignore`의 허용 목록에 적은 경로만 추적한다.

## 구성

| 경로 | 내용 |
| --- | --- |
| `skills/` | 범용 스킬. 환경 전용 파일은 각 스킬의 `local/`에 두며 이 저장소에 넣지 않는다 |
| `agents/` | 사용자 정의 서브에이전트 |
| `hooks/jira-session-title.sh` | Jira 이슈 키로 세션 제목을 붙이는 UserPromptSubmit 훅 |
| `tools/pre-commit` | 금지어 검사 훅. `ln -s ../../tools/pre-commit .git/hooks/pre-commit` |
| `settings.env.example.json` | settings.json에 넣을 환경변수 예시 |

## 설치

```bash
git clone <이 저장소> ~/.claude-config && cp -rn ~/.claude-config/. ~/.claude/   # 또는 ~/.claude에서 직접 clone 후 기존 파일과 병합
ln -s ../../tools/pre-commit ~/.claude/.git/hooks/pre-commit
```

## 환경변수

`~/.claude/settings.json`의 `env`에 둔다. 이 파일은 저장소에 넣지 않는다. 형식은 `settings.env.example.json`을 참고해 `env` 블록을 settings.json에 합친다. 빈 값은 쓰지 않는 변수이므로 지워도 된다.

`.env` 파일을 따로 두지 않는 이유: Claude Code는 `~/.claude/.env`를 읽지 않는다. settings.json의 `env`는 Claude Code가 모든 명령과 훅에 자동으로 넣어 주므로, 스킬과 훅이 값을 읽으려고 파일을 따로 불러올 필요가 없다.

| 변수 | 쓰는 곳 | 예 |
| --- | --- | --- |
| `LLM_WIKI_REPO` | add-to-llm-wiki | `owner/llm-wiki` |
| `JIRA_SITE` | hooks/jira-session-title.sh(이슈 제목 조회, 없으면 조회 생략) | `https://example.atlassian.net` |
| `TECHSPEC_TRACKER_HOSTS` | writing-tech-specs 검사기(Atlassian 외 이슈 트래커 허용, 선택) | `jira.example.com` |
| `CLAUDE_CONFIG_DENYLIST` | tools/pre-commit(선택, 기본 `~/.config/claude-config/denylist`) | |

## 환경마다 따로 두는 것(이 저장소 밖)

- 프로젝트 부록: 이슈 트래커 주소, 배포 절차, 조율 규칙. 각 프로젝트의 `CLAUDE.md`나 프로젝트 메모리에 둔다(big-brother, writing-tech-specs, writing-screen-planning-docs가 읽는다).
- `skills/<스킬>/local/`: 제품별 부품 목록 등(예: writing-screen-planning-docs의 `local/<저장소 이름>.md`).
- 환경 전용 스킬: 특정 서비스의 로그인·화면 확인 절차처럼 한 환경에서만 쓰는 스킬.
- 훅 데이터: `hooks/jira-issue-labels.tsv`(이슈 이름표), `hooks/jira-project-keys.txt`(인정할 프로젝트 키), `hooks/session-title-pins.tsv`.

## 외부 스킬(추적하지 않음)

다음 스킬은 원본에서 받아 설치한다. 로컬 변경은 각 폴더의 기록을 따른다.

| 스킬 | 원본 |
| --- | --- |
| ui-ux-pro-max | github.com/nextlevelbuilder/ui-ux-pro-max-skill (`.claude/skills/ui-ux-pro-max`, 설치 커밋은 폴더의 LOCAL-CHANGES.md) |
| shadcn | github.com/shadcn-ui/ui (설치 시점·커밋은 폴더의 LOCAL-CHANGES.md) |

designing-with-uupm-and-shadcn은 위 두 스킬이 설치되어 있어야 한다. 포함된 Pretendard 글꼴은 OFL-1.1(`fonts/LICENSE.txt`)이다.
