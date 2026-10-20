#!/bin/bash
# UserPromptSubmit 훅: Jira 이슈 키와 짧은 한글 이름(예: "PROJ-581 컨텍스트 요약")을 세션 제목으로 한 번만 설정한다.
# 찾는 순서: 1) 사람이 쓴 프롬프트의 첫 이슈 키, 2) 없으면 작업 폴더 경로의 마지막 이슈 키.
# 프로젝트 키는 jira-project-keys.txt에 있는 실제 Jira 프로젝트만 인정한다(S1-10·SC-18 같은 계획·화면 번호 제외).
# 목록 파일이 없거나 비어 있으면 일반 키 패턴과 제외 접두어로만 검사한다.
input=$(cat)
# 이 훅은 모든 프롬프트를 막고 실행된다. jq는 이 VM에서 한 번 뜨는 데 약 24ms가 들어,
# 매번 지나가는 경로(마커 확인·고정 이름 확인)에서는 bash 정규식과 grep만 쓴다. jq는 이름을 정하는 첫 프롬프트에서만 쓴다.
sid_re='"session_id": *"([0-9A-Fa-f-]+)"'
[[ $input =~ $sid_re ]] || exit 0
sid=${BASH_REMATCH[1]}

# 지금 실행 중인 세션의 파일(~/.claude/sessions/<pid>.json) 내용. formerNames 안의 sessionId와 섞이지 않게 맨 앞 pid 다음 자리만 본다.
# 프로세스가 비정상 종료해 옛 파일이 남았을 수 있으므로 가장 최근 파일을 쓴다.
session_json() {
  local files
  files=$(grep -lE "^\{\"pid\":[0-9]+,\"sessionId\":\"$sid\"" "$HOME"/.claude/sessions/*.json 2>/dev/null) || return 0
  cat "$(ls -t $files | head -1)" 2>/dev/null
}

# 고정 이름(session-title-pins.tsv, "sessionId<TAB>이름"): 프로세스가 다시 떠서 이름이 풀려도 다음 프롬프트에서 되돌린다.
# 예: big-brother 조율 세션. Orca가 채팅 프로세스를 --resume으로 다시 띄우면 /rename 이름이 자동 이름으로 돌아간다.
pins_file="$(dirname "$0")/session-title-pins.tsv"
pinned=$(awk -F'\t' -v s="$sid" '$1 == s { print $2; exit }' "$pins_file" 2>/dev/null)
if [ -n "$pinned" ]; then
  # 세션 파일에서 맨 위 name은 바로 뒤에 nameSource가 온다(formerNames 항목은 뒤에 until이 온다).
  [[ $(session_json) == *"\"name\":\"$pinned\",\"nameSource\""* ]] && exit 0
  jq -nc --arg k "$pinned" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",sessionTitle:$k}}'
  exit 0
fi

marker="${XDG_RUNTIME_DIR:-/tmp}/.claude-jira-title-$sid"
[ -f "$marker" ] && exit 0
# 사용자가 /rename으로 붙인 이름은 덮어쓰지 않는다.
if [[ $(session_json) == *'"nameSource":"user"'* ]]; then
  touch "$marker" 2>/dev/null
  exit 0
fi

keys_file="$(dirname "$0")/jira-project-keys.txt"
prompt=$(printf '%s' "$input" | jq -r '.prompt // empty')
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')

# 백그라운드 작업 완료 알림·세션 간 메시지 등 하네스가 주입한 프롬프트는 사람이 쓴 것이 아니므로 보지 않는다.
case "${prompt#"${prompt%%[![:space:]]*}"}" in
  '<task-notification>'* | '<cross-session-message'* | '<system-reminder>'*) prompt='' ;;
esac

# 표준 입력의 후보 키 중 프로젝트 키가 인정되는 것만 순서대로 출력한다.
valid_keys() {
  local k
  while read -r k; do
    if grep -qv '^#' "$keys_file" 2>/dev/null; then
      grep -qxF "${k%-*}" "$keys_file" && echo "$k"
    else
      printf '%s\n' "$k" | grep -vE '^(UTF|GPT|SHA|MD|ISO|RFC|ES|HTTP|COVID|IPV|UUID|CSS|HTML|TLS|SSL|AES|RSA|X|CVE)-'
    fi
  done
}

# 키 규칙: 영대문자로 시작하는 2~10자 프로젝트 키 + '-' + 0으로 시작하지 않는 숫자.
# 프롬프트에서는 앞뒤가 식별자·경로·소수점(GPT-5.6)에 이어지면 제외한다.
key=$(printf '%s' "$prompt" \
  | grep -oP '(?<![A-Za-z0-9_/.\-])[A-Z][A-Z0-9]{1,9}-[1-9][0-9]{0,5}(?![A-Za-z0-9_\-]|\.[0-9])' \
  | valid_keys | head -1)

# 경로에서는 feature-PROJ-593처럼 앞에 '-'가 붙은 워크트리 이름도 인정하고, 가장 깊은 키를 쓴다.
if [ -z "$key" ] && [ -n "$cwd" ]; then
  key=$(printf '%s' "$cwd" \
    | grep -oP '(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,9}-[1-9][0-9]{0,5}(?![0-9])' \
    | valid_keys | tail -1)
fi
[ -n "$key" ] || exit 0

# 짧은 한글 이름: 1) 사람이 다듬은 jira-issue-labels.tsv, 2) 자동 조회 캐시, 3) Jira 읽기 토큰이 있으면 조회.
# 토큰 파일(~/.config/jira-session-title/auth, 한 줄 "email:api_token", 권한 600)이 없으면 키만 쓴다.
labels_file="$(dirname "$0")/jira-issue-labels.tsv"
cache_file="$(dirname "$0")/jira-issue-labels.cache.tsv"
lookup_label() {
  awk -F'\t' -v k="$1" '$1 == k { print $2; exit }' "$labels_file" "$cache_file" 2>/dev/null
}
label=$(lookup_label "$key")
auth_file="$HOME/.config/jira-session-title/auth"
site=${JIRA_SITE:-}   # 예: https://<사이트>.atlassian.net (settings.json env에 둔다)
if [ -z "$label" ] && [ -n "$site" ] && [ -r "$auth_file" ]; then
  summary=$(curl -s -m 2 -u "$(head -1 "$auth_file")" "$site/rest/api/3/issue/$key?fields=summary" 2>/dev/null \
    | jq -r '.fields.summary // empty' 2>/dev/null)
  if [ -n "$summary" ]; then
    # 앞의 [AI CHAT] 같은 말머리를 떼고 18자로 자른다.
    label=$(printf '%s' "$summary" | sed -E 's/^(\[[^]]*\][[:space:]]*)+//; s/[[:space:]]+/ /g; s/^ //; s/ $//')
    label=$(LC_ALL=C.UTF-8 python3 -c "import sys;s=sys.argv[1];print(s if len(s)<=18 else s[:18]+\"…\")" "$label")
    printf '%s\t%s\n' "$key" "$label" >> "$cache_file" 2>/dev/null
  fi
fi
title="$key${label:+ $label}"

touch "$marker" 2>/dev/null
jq -nc --arg k "$title" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",sessionTitle:$k}}'
