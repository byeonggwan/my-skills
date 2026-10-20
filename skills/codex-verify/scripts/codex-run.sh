#!/usr/bin/env bash
# Codex를 read-only로 비대화형 실행하고 thread_id와 최종 답변을 출력한다.
#
#   bash codex-run.sh new    <workdir>              < prompt.md
#   bash codex-run.sh resume <workdir> <thread_id>  < prompt.md
#   bash codex-run.sh review <workdir> --uncommitted | --base <branch> | --commit <sha>
#
# 출력: 첫 줄 THREAD_ID=<id>, 이어서 RESULT_FILE=<path>, 그 뒤 Codex 최종 답변 본문.
# 환경변수: CODEX_OUTDIR(결과 저장 상위 디렉터리, 기본 $TMPDIR), CODEX_TIMEOUT(초, 기본 580),
#           CODEX_MODEL(예: gpt-6-astra), CODEX_EFFORT(예: high). 미지정 시 config 기본값
set -uo pipefail

mode="${1:?mode: new|resume|review}"
workdir="${2:?workdir}"
shift 2

mkdir -p "${CODEX_OUTDIR:-${TMPDIR:-/tmp}}"
outdir="$(mktemp -d "${CODEX_OUTDIR:-${TMPDIR:-/tmp}}/codex-verify.XXXXXX")"
events="$outdir/events.jsonl"
result="$outdir/result.md"
errlog="$outdir/stderr.log"

common=(--skip-git-repo-check --json -o "$result")
[[ -n "${CODEX_MODEL:-}" ]] && common+=(-m "$CODEX_MODEL")
[[ -n "${CODEX_EFFORT:-}" ]] && common+=(-c "model_reasoning_effort=\"$CODEX_EFFORT\"")

cd "$workdir" || { echo "workdir not found: $workdir" >&2; exit 2; }

case "$mode" in
  new)
    # 프롬프트는 stdin(-)으로 받는다. 인자로 넘기면 셸 이스케이프가 깨지기 쉽다.
    timeout "${CODEX_TIMEOUT:-580}" codex exec -s read-only "${common[@]}" - >"$events" 2>"$errlog"
    ;;
  resume)
    tid="${1:?thread_id}"
    # resume은 -s를 받지 않으므로 config로 샌드박스를 고정한다.
    timeout "${CODEX_TIMEOUT:-580}" codex exec resume -c 'sandbox_mode="read-only"' "${common[@]}" "$tid" - >"$events" 2>"$errlog"
    ;;
  review)
    # review 대상 플래그(--uncommitted 등)와 커스텀 프롬프트는 함께 쓸 수 없다.
    timeout "${CODEX_TIMEOUT:-580}" codex exec review -c 'sandbox_mode="read-only"' "${common[@]}" "$@" </dev/null >"$events" 2>"$errlog"
    ;;
  *)
    echo "unknown mode: $mode" >&2; exit 2 ;;
esac
status=$?

tid_out="$(jq -r 'select(.type=="thread.started") | .thread_id' "$events" 2>/dev/null | head -1)"
echo "THREAD_ID=${tid_out:-unknown}"
echo "RESULT_FILE=$result"

if [[ $status -eq 124 ]]; then
  echo "ERROR: codex timed out after ${CODEX_TIMEOUT:-580}s" >&2
fi
if [[ $status -ne 0 || ! -s "$result" ]]; then
  echo "ERROR: codex exit=$status. stderr tail:" >&2
  tail -20 "$errlog" >&2
  exit "${status/#0/1}"
fi
echo "---"
cat "$result"
