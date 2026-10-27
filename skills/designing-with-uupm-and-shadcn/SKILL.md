---
name: designing-with-uupm-and-shadcn
description: Use when making or changing any UI — an Artifact page (decision board, explainer, report, dashboard), a 화면기획서 mockup, or a product screen in a project with components.json. Trial design workflow started 2026-10-08.
---

# 틀은 ui-ux-pro-max, 구현은 shadcn (시험 운영)

2026-10-08 사용자 지시로 시험 운영합니다. 앞으로 만드는 모든 Artifact, 관련 스킬, 화면기획서, 실제 제품 화면에 적용합니다. 아직 CLAUDE.md에는 넣지 않습니다. 결과가 좋다고 판단되면 사용자가 CLAUDE.md로 옮깁니다.

**REQUIRED:** `ui-ux-pro-max` 스킬과 `shadcn` 스킬을 함께 로드합니다. 둘 다 `~/.claude/skills`에 설치되어 있습니다.

## 순서

1. **틀 잡기 (ui-ux-pro-max).** 아래 표에서 대상별로 허용된 범위만 씁니다. 검색 스크립트는 `python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<검색어>" ...` 형식으로 실행합니다. 검색어에 비공개 데이터(고객명, 키, 사내 URL)를 넣지 않습니다.
2. **구현 (shadcn).** 컴포넌트 구성과 스타일 규칙을 따릅니다. 시맨틱 토큰을 쓰고, 색 값을 직접 쓰지 않습니다. 간격은 `space-*` 대신 `gap-*`를 쓰고, 정사각형은 `size-*`로 지정합니다. Card는 Header/Title/Description/Content/Footer를 모두 갖춰 구성합니다. 상태 표시는 Badge로 합니다.
3. **납품 전 점검.** `ui-ux-pro-max/references/pro-rules.md`의 체크리스트를 확인합니다. 대비 4.5:1, 키보드 포커스, 아이콘에 이모지 금지, 좁은 화면에서 가로 스크롤 없음이 기준입니다.
4. **보고.** 사용자에게 한 줄로 알립니다. ui-ux-pro-max에서 무엇을 가져왔는지, 그리고 검색 결과가 없어 기본값으로 대신한 항목이 있는지를 적습니다.

## 대상별 범위

| 대상 | ui-ux-pro-max | shadcn |
| --- | --- | --- |
| Artifact (제품과 무관한 페이지: 결정 대기함, 설명, 보고서, 현황판) | 전부 씁니다. `--design-system`으로 스타일, 색, 효과를 정합니다. 본문 글꼴은 아래 "글꼴: Pretendard 고정"을 따르고, 검색 결과의 글꼴 짝은 쓰지 않습니다. | 빌드 단계가 없습니다. 그래서 shadcn 토큰 구조(`--background`, `--foreground`, `--muted`… HSL 변수)와 Tailwind CDN `cdn.tailwindcss.com/3.4.17`으로 컴포넌트 모양과 styling 규칙을 옮깁니다. 색 값은 ui-ux-pro-max 결과를 토큰에 넣습니다. |
| 화면기획서 목업 | `--domain ux`, `--stack shadcn`, 체크리스트만 씁니다. `--design-system`으로 색과 글꼴을 바꾸지 **않습니다**. 목업은 실제 제품과 같아 보여야 하기 때문입니다. | 제품의 실제 토큰(`client/src/index.css`, `tailwind.config.js`)과 설치된 컴포넌트(`client/src/components/ui`) 모양을 그대로 옮깁니다. |
| 실제 제품 (`components.json`이 있는 프로젝트) | 화면기획서와 같습니다. `--persist`는 쓰지 않습니다. 쓰면 저장소에 `design-system/`이 생깁니다. | shadcn 스킬 규칙을 따르되, 프로젝트 관례(CLAUDE.md, 기존 컴포넌트, i18n)와 충돌하면 **기존 관례가 우선**입니다. 새 컴포넌트를 `npx shadcn@latest add`로 추가하는 일은 제품 변경이므로 계획서에 적은 뒤에 진행합니다. 프리셋 `apply`, `init`, `--overwrite`는 사용자 승인 없이 쓰지 않습니다. |

## 글꼴: Pretendard 고정

2026-10-13 사용자 지시로, 이 스킬이 다루는 모든 페이지(Artifact, 화면기획서, 결정 대기함)의 본문 글꼴을 **Pretendard Variable**로 고정합니다. 제품 화면도 Pretendard를 쓰는 프로젝트라면 목업과 제품의 글꼴이 같아집니다. `--design-system`이 다른 글꼴을 권해도 본문 글꼴은 바꾸지 않습니다. 코드용 고정폭 글꼴만 Google Fonts(IBM Plex Mono 등)를 써도 됩니다.

Pretendard는 Google Fonts에 없고, Artifact는 외부 스타일시트를 Google Fonts에서만 허용합니다. 그래서 글꼴 파일을 페이지와 함께 발행합니다.

1. 글꼴 파일: `~/.claude/skills/designing-with-uupm-and-shadcn/fonts/PretendardVariable.woff2` (npm `pretendard@1.3.9`, OFL-1.1, 약 2MB, 라이선스는 같은 폴더의 `LICENSE.txt`).
2. 페이지 `<style>` 맨 위에 넣습니다.
   ```css
   @font-face { font-family: "Pretendard Variable"; font-weight: 45 920; font-style: normal; font-display: swap;
     src: url("fonts/PretendardVariable.woff2") format("woff2-variations"), url("fonts/PretendardVariable.woff2") format("woff2"); }
   /* 본문 글꼴 토큰 */
   --sans: "Pretendard Variable", Pretendard, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
   ```
3. 발행할 때 `files`의 소스는 작업 디렉터리나 scratchpad 아래에 있어야 하므로, 글꼴을 페이지 옆 `fonts/`로 복사한 뒤 넘깁니다.
   ```
   cp ~/.claude/skills/designing-with-uupm-and-shadcn/fonts/PretendardVariable.woff2 <페이지 폴더>/fonts/
   Artifact publish: file_path=<페이지>, files={"fonts/PretendardVariable.woff2": "<페이지 폴더>/fonts/PretendardVariable.woff2"}, ...
   ```
   같은 Artifact를 다시 발행할 때는 `files`를 빼도 이미 올린 글꼴이 유지됩니다. 다른 Artifact에 이미 올라간 글꼴을 복사하려면 `files`에 `{"artifact": "<그 URL>", "path": "fonts/PretendardVariable.woff2"}`를 넘깁니다.
4. 로컬 미리보기도 페이지 옆에 `fonts/`가 있어야 같은 글꼴로 보입니다. snap Chromium은 `/tmp`를 못 읽으므로 `python3 -m http.server`로 띄워서 엽니다.

## 한국어 줄바꿈

브라우저는 기본값에서 한글을 글자 단위로 끊어서, "통과했습니" / "다"처럼 낱말 중간에서 줄이 바뀝니다. 모든 페이지의 `body`에 아래 두 줄을 넣습니다.

```css
body { word-break: keep-all; overflow-wrap: anywhere; }  /* 한글은 어절 단위로, 긴 URL·코드만 강제로 끊음 */
p, li { text-wrap: pretty; }                            /* 마지막 줄에 한 어절만 남는 것을 줄임 */
```

글 폭을 `ch`로 정하지 않습니다. `ch`는 숫자 0의 폭이라 한글은 그 두 배쯤 차지해서, `max-width: 68ch`면 카드 폭의 절반쯤에서 줄이 바뀝니다. 읽기 폭은 `em`(본문 18px 기준 `40em` 안팎)이나 px로 정합니다.

## 도식과 인포그래픽

내용에 아래 구조가 있으면 글 대신 도식 하나로 보여 줍니다. 구조가 없으면 그리지 않습니다. 꾸밈용 일러스트, 아이콘 나열, 의미 없는 배경 그래픽은 넣지 않습니다.

| 내용의 구조 | 도식 |
| --- | --- |
| 누가 누구를 호출하거나 데이터가 어디로 가는지 | 흐름도: 상자와 화살표. 화살표에 실제 예시 값을 적습니다 |
| 시간 순서, 요청과 응답 왕복 | 시퀀스도. 실패, 재시도, 중단 흐름도 함께 그립니다 |
| 상태가 바뀌는 기능 | 상태 전이도. 전이 조건을 화살표에 적습니다 |
| 변경 전과 후 | 같은 모양의 도식 두 개를 나란히(좁은 화면에서는 위아래로) 두고 바뀐 곳만 강조합니다 |
| 수치 비교, 비율, 추이 | 막대, 선, 점 차트. 축 하나에 한 단위만 두고, 실제 비율대로 그리고, 값 라벨을 붙입니다 |

그리는 방법은 아래와 같습니다.
- 흐름도, 시퀀스도, 상태 전이도는 Artifact가 기본으로 렌더링하는 mermaid(`<pre class="mermaid">`)를 먼저 씁니다. 모양을 세밀하게 맞춰야 하면 인라인 SVG로 그립니다. 단, 기본 렌더는 도식을 폭에 맞춰 줄여서 큰 도식의 글자가 작아집니다. 큰 흐름도는 `writing-tech-specs` 템플릿의 렌더러(원래 크기, 자기 상자 스크롤, 크게 보기)를 가져다 씁니다. 테크 스펙은 항상 그 렌더러를 씁니다.
- 차트는 인라인 SVG로 그리거나, 허용 CDN의 차트 라이브러리를 버전을 고정해 씁니다. `ui-ux-pro-max --domain chart`로 차트 종류를 고릅니다.
- SVG의 색은 페이지 토큰(`hsl(var(--foreground))`처럼)으로만 지정해서 다크 모드에서도 보이게 합니다. 모든 도형에 fill을 명시하고, 바깥 라벨이 잘리지 않도록 viewBox에 여백을 둡니다.
- 도식 안 글자도 14px 이상으로 둡니다. 도식 바로 아래에 한두 문장으로 무엇을 보여 주는지 적습니다.
- 좁은 화면에서 도식이 넘치면 자기 `overflow-x: auto` 컨테이너 안에서만 스크롤되게 합니다.

## 기존 규칙과의 관계

- 사용자의 말과 프로젝트 규칙이 이 스킬보다 우선합니다.
- 설명형 페이지의 가독성 기준(본문 18px, 한 열로 쌓기)과 각 스킬의 페이지 계약(결정 대기함의 한 화면 하나, 화면기획서의 마커 구조)은 그대로 유지합니다. 이 스킬은 그 구조 위에 보이는 모양만 바꿉니다.
- Artifact 발행 규칙(CDN 허용 목록, 다크 모드 토큰 세 블록, 16px 거터)은 그대로 지킵니다.

## 흔한 실수

| 실수 | 바로잡기 |
| --- | --- |
| 제품 화면이나 화면기획서에서 `--design-system`의 색과 글꼴을 적용함 | 제품 토큰을 고정하고 ux, stack, 체크리스트만 씁니다 |
| shadcn 스킬이 권하는 새 컴포넌트(Field, Empty, Spinner, sonner 등)를 제품에 바로 추가함 | 설치된 컴포넌트를 먼저 확인하고, 추가는 계획서에 적은 뒤에 합니다 |
| 본문 글꼴을 Google Fonts나 jsDelivr CSS 링크로 불러옴 | Pretendard woff2를 `files`로 함께 발행하고 `@font-face`로 읽습니다 |
| 발행할 때 `files`에 글꼴을 빠뜨림 | 첫 발행에는 반드시 넘깁니다. 빠지면 기본 글꼴로 조용히 바뀝니다 |
| `word-break: keep-all` 없이 발행하거나 글 폭을 `ch`로 정함 | 낱말 중간에서 줄이 바뀌고 문단이 카드 폭보다 일찍 끊긴다는 지적(2026-10-27 Terra 점검 페이지). "한국어 줄바꿈" 절을 따릅니다 |
| `npx shadcn@latest info`를 저장소 루트에서 실행함 | `components.json`이 있는 디렉터리(이 저장소는 `client/`)에서 실행합니다 |
