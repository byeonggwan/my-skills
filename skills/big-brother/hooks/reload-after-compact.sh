#!/usr/bin/env bash
# SessionStart(matcher: compact) 훅.
# 압축된 세션이 big-brother 스킬을 쓰던 조율 세션이면, 스킬을 다시 불러오라는 안내를 모델 맥락에 넣는다.
# 압축 뒤 안내문은 "이미 부른 스킬을 다시 실행하지 말라"고 하고 스킬 본문은 잘려 남지 않아서,
# 그대로 두면 조율 규칙 없이 일을 이어 간다.
# 다른 세션에서는 아무것도 출력하지 않는다.
set -u

input=$(cat)
IFS=$'\t' read -r source transcript < <(printf '%s' "$input" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d.get("source", ""), d.get("transcript_path", ""), sep="\t")
' 2>/dev/null) || exit 0

[ "$source" = "compact" ] || exit 0
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0

# Skill 도구 호출 또는 /big-brother 슬래시 명령이 기록에 있어야 조율 세션으로 본다.
grep -qF -e '"name":"Skill","input":{"skill":"big-brother"' -e '<command-name>/big-brother</command-name>' "$transcript" || exit 0

python3 -c '
import json
msg = (
    "이 세션은 big-brother 조율 세션이다. 대화가 방금 압축됐다. "
    "다른 일을 하기 전에 Skill 도구로 big-brother 스킬을 지금 다시 불러온다. "
    "압축 뒤 안내의 \"이미 부른 스킬을 다시 실행하지 말라\"는 이 스킬에는 적용하지 않는다"
    "(스킬 본문이 압축 요약에 남지 않기 때문이다). "
    "불러온 뒤 스킬의 \"압축 직후 점검\" 절을 따른다."
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}, ensure_ascii=False))
'
