---
name: add-to-llm-wiki
description: Use when the user wants to save a local file or a conversation summary into their personal LLM wiki repository's staging/ folder (the staging area for the LLM wiki ingest workflow). Triggers include "위키에 추가/저장", "staging에 넣어", "llm-wiki에 보관", "이 파일 위키로". The GitHub repo (owner/name) comes from the LLM_WIKI_REPO environment variable; uses gh CLI Contents API. Not for editing wiki/ pages — that area is LLM-owned and has a separate ingest workflow.
---

# Add to LLM Wiki (staging/)

## Overview

환경변수 `LLM_WIKI_REPO`(예: `owner/llm-wiki`)가 가리키는 위키 저장소의 `staging/` 폴더에 파일이나 대화 내용을 마크다운으로 추가한다. `staging/`는 사람이 넣는 자료의 대기 영역이고, 이후 LLM의 위키 ingest 워크플로우의 입력이 된다.

**핵심 원칙: `staging/`만 다룬다.** `wiki/`는 절대 건드리지 않는다 — 그쪽은 LLM 위키 운영 영역.

## When to Use

- 로컬 파일(.md, 이미지)을 위키 저장소에 업로드할 때
- 현재 대화에서 가치 있는 내용을 위키 원본으로 보존하라고 요청받았을 때
- 사용자가 "staging에 저장", "위키에 넣어", "llm-wiki에 추가" 등을 말할 때

**사용하지 않는 경우:**
- `wiki/` 폴더 페이지 작성 → 이 스킬은 staging/ 전용
- `LLM_WIKI_REPO`가 아닌 다른 리포 → 이 스킬은 해당 리포 전용

## Repo Conventions

`staging/` (CLAUDE.md 기반):

위키 저장소의 CLAUDE.md가 기준이다. 아래와 다르면 CLAUDE.md를 따르고 이 스킬을 고친다(`gh api "repos/$LLM_WIKI_REPO/contents/CLAUDE.md" --jq .content | base64 -d`).

- **Flat 구조** — `staging/` 하위에 폴더를 만들지 않는다 (예외: `staging/assets/` 이미지)
- **파일명은 raw 컨벤션 그대로** (승격 시 `mv staging/<파일> raw/`로 그대로 옮겨지므로), 영어 kebab-case:

  | 입력 유형 | 파일명 |
  | --- | --- |
  | 업무 산출물 (보고서, 기술검토, 회고, 정리 문서) | `YYYY-MM-DD-<title>.md` |
  | 외부 조사물 (웹·논문 조사 노트) | `YYYY-MM-DD-<title>-research.md` |
  | 일기 | `YYYY-MM-DD.md` (날짜만) — **사람이 직접 쓰는 1차 기록 전용. LLM은 이 이름으로 만들지 않는다** |

- **이미지**: `staging/assets/{name}.{ext}`
- **본문 언어**: 한국어 + 영어 기술 용어 (CLAUDE.md 규칙 그대로)
- **첫 줄에 작성 주체와 근거 (필수)**:
  ```markdown
  > 작성: Claude (사용자 요청) · YYYY-MM-DD · <근거: 웹 조사 N건 / 코드베이스 분석 / 세션 기록 분석 등>
  > 사람이 직접 쓴 1차 기록이 아님.
  ```
  자동화가 만든 파일은 `(사용자 요청)` 대신 `(자동화: <자동화 이름>)`으로 쓴다. 외부 URL 출처는 이 아래 본문에 링크로 남긴다.

## Workflow

### 1. 사전 점검

```bash
gh auth status   # github.com 인증 + repo 권한 확인
test -n "$LLM_WIKI_REPO" || echo "LLM_WIKI_REPO가 비어 있음"   # 비어 있으면 사용자에게 저장소를 묻고 중단
```

인증 안 됨 → 사용자에게 `gh auth login` 안내하고 중단.

### 2. 입력 분기

| 입력 | 처리 |
| --- | --- |
| 로컬 파일 경로 | 파일을 그대로 읽어 base64 인코딩 |
| 대화 내용 정리 요청 | 핵심을 마크다운으로 작성 (한국어), 첫 줄 작성 주체·근거 표기 포함 |
| 이미지 파일 | `staging/assets/`로 라우팅 |

### 3. 파일명/경로 결정

- 텍스트: `staging/YYYY-MM-DD-<slug>.md` (오늘 날짜), 외부 조사물이면 `staging/YYYY-MM-DD-<slug>-research.md`
- 이미지: `staging/assets/<slug>.<ext>` (날짜 prefix 불요, 단 충돌 시 `<slug>-2.ext` 식으로 회피)
- `<slug>`: 영어 kebab-case, 내용을 한 줄로 요약

업로드 전에 사용자에게 결정한 파일명을 한 번 보여주고 확인받는다.

### 4. 푸시 (GitHub Contents API)

새 파일:

```bash
CONTENT_B64=$(printf '%s' "$MARKDOWN" | base64 -w0)
gh api -X PUT "repos/$LLM_WIKI_REPO/contents/staging/2026-05-08-<slug>.md" \
  -f message="add staging: <slug>" \
  -f content="$CONTENT_B64"
```

바이너리 (이미지):

```bash
gh api -X PUT "repos/$LLM_WIKI_REPO/contents/staging/assets/<name>.png" \
  -f message="add asset: <name>.png" \
  -f content="$(base64 -w0 < <local-image>)"
```

기존 파일 덮어쓰기: `sha` 필요.

```bash
SHA=$(gh api "repos/$LLM_WIKI_REPO/contents/staging/<path>" --jq .sha)
gh api -X PUT "repos/$LLM_WIKI_REPO/contents/staging/<path>" \
  -f message="update staging: <slug>" \
  -f content="$CONTENT_B64" \
  -f sha="$SHA"
```

> 충돌 회피: 같은 날짜·같은 slug가 이미 있으면 사용자에게 덮어쓸지 다른 slug로 갈지 묻는다. 임의로 덮어쓰지 않는다.

### 5. 보고

업로드 후 사용자에게:

- 생성된 경로 (예: `staging/2026-05-08-foo.md`)
- HTML URL: `https://github.com/$LLM_WIKI_REPO/blob/main/staging/...`
- 커밋 SHA (응답의 `commit.sha`)

이후 `wiki/` ingest는 이 스킬 범위 밖. 사용자가 별도로 요청한다.

## Common Mistakes

| 실수 | 올바른 처리 |
| --- | --- |
| `staging/` 하위에 카테고리 폴더 생성 | flat 구조 유지 (assets/만 예외) |
| 파일명에 한국어/공백 | 영어 kebab-case |
| 날짜 prefix 누락 | `YYYY-MM-DD-` 필수 |
| 본문도 영어로 번역 | 본문은 한국어 유지, 파일명만 영어 |
| 같은 경로에 파일 있는데 sha 없이 PUT | 422 에러 발생 — 먼저 GET으로 sha 조회 |
| `wiki/` 폴더 수정 시도 | 이 스킬은 `staging/` 전용. wiki는 별도 워크플로우 |
| 첫 줄을 `> 출처:`로 씀 | 위키 규칙은 `> 작성: Claude (...) · 날짜 · <근거>` + `> 사람이 직접 쓴 1차 기록이 아님.` 두 줄 |
| LLM 산출물을 `YYYY-MM-DD.md`(날짜만)로 저장 | 그 이름은 사람이 쓰는 일기 전용. 제목 slug를 붙인다 |
| 외부 조사물에 `-research` 접미사 누락 | ingest가 입력 유형을 파일명으로 판별하므로 반드시 붙인다 |
| 사용자 확인 없이 임의로 덮어쓰기 | 충돌 시 항상 사용자에게 물어본다 |

## Quick Reference

- **Repo**: 환경변수 `LLM_WIKI_REPO` (`~/.claude/settings.json`의 `env`에 둔다. 비공개 저장소 이름이라 스킬에 적지 않는다)
- **Default branch**: `main`
- **Allowed targets**: `staging/*.md`, `staging/assets/*`
- **Forbidden targets**: `raw/**`, `wiki/**`, `CLAUDE.md`, `.obsidian/**`
- **Auth**: `gh` CLI, `repo` scope 필요
