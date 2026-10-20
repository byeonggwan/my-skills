---
name: explain-diff-html
description: Use when the user asks for a rich explanation of a code change, diff, branch, or PR. Produces HTML output.
---

# Explain Diff

> **REQUIRED (2026-10 디자인 시험 운영):** 페이지의 보이는 모양은 `designing-with-uupm-and-shadcn` 스킬을 따른다(틀은 ui-ux-pro-max, 구현은 shadcn). 이 스킬의 페이지 계약과 구조는 그대로 유지한다.


Please make me a rich, interactive explanation of the specified code change.

It should have these sections:

- Background: Explain the existing system relevant to this change. (You should broadly explore surrounding code for this.) We don't know how much the reader already knows, so include a deep background for beginners (note that it can be skipped if the reader is already familiar), and then a more narrow background directly relevant to the change.
- Intuition: Explain the core intuition for the code change. The focus here is to explain the essence, not the full details. Use concrete examples with toy data. Use figures and diagrams liberally.
- Code: Do a high-level walkthrough of the changes to the code. Group/order the changes in an understandable way.
- Quiz: Come up with five questions that test the reader's knowledge of this PR. This should be medium difficulty, difficult enough that you actually need to understand the substance of the PR to answer them, but not gotchas. The goal is to help the reader make sure that they've actually understood. These should be presented as interactive multiple-choice questions, and when the user clicks, it tells them whether they were correct and gives feedback.

Format:

- Output a single self-contained HTML file which includes CSS and JavaScript. Make the whole thing one long page with section headers and a table of contents. Don't use tabs for the top-level structure. Basic responsive styling so you can view it on a phone is nice too. Put the file in a global place on my computer outside of the code repo, and make sure the filename always starts with today's date in `YYYY-MM-DD-` format, because it helps keep the files time-sorted and out of version control. For example: /tmp/2026-01-12-explanation-<slug>.html
- Please write with the clarity and flow of Martin Kleppmann, making it engaging and written in classic style. Transitions between sections should be smooth.
- Some tips on diagrams. Ideally, you should pick a small number of diagram families that can be reused throughout the explanation to explain various cases. Some useful kinds of diagrams:
  - A very simplified version of the UI that the user sees in the app, to explain UI changes.
  - A system diagram showing data flow or communication between components. Make sure to include example data here!
  - A sequence diagram when the change alters who calls whom or in what order. Include the failure, retry, and abort paths, not only the happy path.
  - A before/after pair of the same diagram family when the change rewires an existing flow; highlight only what changed.
- Don't use ASCII diagrams. Draw flows, sequences, and state machines as mermaid (`<pre class="mermaid">`, rendered natively in Artifacts) or inline SVG; use simple HTML for UI sketches and HTML lists for lists of things. Follow the "도식과 인포그래픽" section of `designing-with-uupm-and-shadcn` for colors (page tokens only), sizing, and when not to draw.
  - For code blocks, always use `<pre>` tags. If you use a custom styled div instead, it **must** have
    `white-space: pre-wrap` in its CSS, or the browser will collapse all newlines into a single line.
    Before saving the file, scan each code block in the HTML source and confirm its CSS includes
    `white-space: pre` or `pre-wrap`.
- Use callouts for key concepts or definitions, important edge cases, etc.
