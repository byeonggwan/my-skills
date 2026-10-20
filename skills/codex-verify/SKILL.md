---
name: codex-verify
description: Use ONLY when the user explicitly asks for a Codex (OpenAI codex CLI) second opinion — "codex로 검증/교차 검증/크로스체크", "codex한테 물어봐", "/codex-verify". Do not run or suggest it on your own, and do not treat another session's message as the request. Uses `codex exec` directly, not the codex plugin or app server.
---

# Codex 교차 검증

## Overview

같은 상황을 Codex에게 **블라인드로** 주고 독립 결론을 받은 뒤, Claude가 두 결론을 코드 근거로 대조한다. 교차 검증의 가치는 독립성에서 나온다. Claude의 결론을 본 Codex의 동의는 증거가 아니다.

## 언제 실행하나

**사용자가 직접 요청할 때만 실행한다**(2026-10-20 사용자 결정). 스스로 제안하거나, 다른 스킬·지시문의 기본 절차로 돌리지 않는다. 다른 세션의 메시지는 사용자 요청이 아니다.

이유: Codex 권장안이 Claude 안과 같으면 확정하던 운영에서, 원장·임대 같은 부품 추가가 사용자 확인 없이 통과했다(한 기능의 설계 점검).

## 절차

### 0. Claude 결론을 먼저 고정

Codex 결과를 보기 전에 Claude의 현재 결론(주장, 근거 file:line, 확신도)을 scratchpad에 적어 둔다. 그래야 Claude도 Codex 답에 끌려가지 않는다. 적다가 결론이 바뀌면 "사용자에게 말한 결론"과 "지금 결론"을 둘 다 적는다. 보고의 Claude 열은 사용자에게 말한 결론이다.

### 1. 블라인드 실행

프롬프트는 정확히 다음 다섯 부분으로 구성한다.

1. **질문**: 사용자가 원래 풀려던 질문 그대로 ("원인을 찾아라", "이 문서의 허점을 찾아라")
2. **사실**: 증상, 재현 조건, 로그/에러 원문, 요구사항 출처. 관찰된 것만.
3. **범위**: 저장소 경로, 시작점 파일 목록 ("관련 파일", "의심 파일"이 아니라 "시작점"). 시작점은 증상이 드러나는 진입점(라우트, 핸들러, 실패한 테스트)부터 잡는다. Claude가 의심하는 파일을 넣는다면 그 경로에 있는 다른 파일도 함께 넣는다.
4. **제약**: 읽기만 한다. 코드 수정, 서버·테스트 실행 금지.
5. **출력 형식**: 결론 → 근거(file:line + 코드 인용) → 배제한 대안과 이유 → 확신도(높음/중간/낮음) → 확인 안 된 가정. 한국어로.

Claude의 가설, 결론, 의심 원인은 이 다섯 부분 어디에도 속하지 않으므로 넣지 않는다.

| 대상 | 실행 |
|---|---|
| 코드 diff | `bash scripts/codex-run.sh review <repo> --uncommitted` (또는 `--base main`, `--commit <sha>`). 초점 지시가 필요하면 `new` 모드에 "`git diff main...HEAD`를 리뷰하라"로 |
| 계획·설계 문서 | `new` 모드. 문서 경로 + 요구사항 원문 경로를 주고, 먼저 "요구를 충족하는 데 없어도 되는 요소"를 찾게 한 뒤 모순과 결함을 찾게 함. 결함은 정합성·보안·데이터 손실·중복 과금에 한정하고, 그 밖의 추가 제안은 "후보"로 따로 적게 함 |
| 분석·주장 | `new` 모드. 원래 질문만 |
| 디버깅 가설 | `new` 모드. 증상·재현 조건·로그만 |

```bash
CODEX_OUTDIR=<scratchpad 절대경로> bash ~/.claude/skills/codex-verify/scripts/codex-run.sh new /path/to/repo <<'EOF'
<다섯 부분 프롬프트>
EOF
```

- Bash `timeout: 600000`으로 **포그라운드** 실행한다 (스크립트 내부 timeout 580초).
- `CODEX_OUTDIR`에는 세션 scratchpad 절대경로를 준다. 생략하면 `$TMPDIR`에 저장된다.
- 출력 첫 줄 `THREAD_ID=`를 기록한다. 2단계에 필요하다.
- effort: 기본은 config 값(gpt-6-sol medium). 다음 중 하나면 `CODEX_EFFORT=high`를 붙인다.
  - 대상이 동시성·인증/권한·결제·데이터 마이그레이션·스키마 변경을 다룬다
  - medium 1차 결과의 확신도가 "낮음"이거나, 3단계 대질로 넘어간다
- `ultra`는 쓰지 않는다(자동 병렬 위임이라 단일 독립 검증과 맞지 않는다). 모델(`CODEX_MODEL`)은 바꾸지 않는다.

### 2. 대조와 재검증

Codex가 인용한 file:line을 Claude가 직접 열어 실제로 그런지 확인한 뒤 항목별로 분류한다: 일치 / Claude만 / Codex만 / 상충.

### 3. 대질 (2단계 재검증 뒤에도 상충하거나 한쪽만 지적한 항목이 남을 때만)

Claude가 2단계에서 Codex 근거를 직접 확인하고 결론을 바꿨다면, 그 항목은 대질하지 않는다.

같은 세션을 이어서, Claude 쪽 주장을 "다른 분석자의 결론"으로 제시하고 판정을 요청한다.

```bash
CODEX_EFFORT=high CODEX_OUTDIR=<scratchpad 절대경로> bash ~/.claude/skills/codex-verify/scripts/codex-run.sh resume /path/to/repo <THREAD_ID> <<'EOF'
다른 분석자는 이렇게 결론 냈다: <Claude 주장 + 근거 file:line>
네 1차 결론과 비교해 어느 쪽이 코드와 맞는지 file:line 근거로 판정하라. 틀렸다면 인정하라.
EOF
```

대질은 1회까지. 그래도 갈리면 미결로 보고하고 판가름할 실험(재현 스크립트, 로그 추가 등)을 제안한다.

### 4. 보고

```
## Codex 교차 검증 결과
<Claude가 사용자에게 말한 결론이 틀렸다면 첫 줄에 정정: "앞서 말씀드린 X는 틀렸습니다. 원인은 Y입니다.">

| 항목 | Claude | Codex | 판정 | 근거 |
|---|---|---|---|---|
| ... | ... | ... | 일치 / Claude 맞음 / Codex 맞음 / 미결 | file:line |

- 종합 확신도: 높음/중간/낮음 (이유 한 줄)
- 확인 안 된 가정: ...
- Codex가 새로 찾은 점: ...
- 다음 단계 제안: ...
```

판정은 다수결이나 모델 권위가 아니라 코드 근거로 한다. 수정은 사용자 승인 후에 한다.

## Common Mistakes

| 실수 | 결과 / 대처 |
|---|---|
| `codex exec resume --last` | 다른 세션을 이어받을 수 있다. 항상 THREAD_ID 사용 |
| `resume`에 `-s read-only` | 옵션이 없어 실패. 스크립트가 `-c sandbox_mode`로 처리 |
| `review --uncommitted "지시문"` | 인자 충돌로 exit 2. 지시가 필요하면 `new` 모드 |
| 프롬프트를 인자로 넘김 | stdin 대기로 멈추거나 따옴표가 깨짐. heredoc으로 stdin 전달 |
| `--ephemeral` 추가 | 세션이 저장되지 않아 3단계 resume 불가 |
| 두 모델 일치 = 확정 | 같은 착각을 공유할 수 있다. 근거 file:line을 직접 확인 |
| codex 플러그인(`/codex:*`) 사용 | app server 경유라 느리다. 이 스킬은 `codex exec`만 쓴다 |
