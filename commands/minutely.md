---
description: Notion 'C조_한컴' 변화를 'Claude 전용' 페이지에 정리 / 회의 파일은 회의록으로 (meeting <파일>)
argument-hint: "[meeting <녹음또는텍스트파일>]"
---

`minutely` 스킬로 정리하세요.

인자: `$ARGUMENTS`

- 인자가 `meeting`으로 시작하면 → **경로 B**: 뒤의 파일(녹음/영상 또는 `.txt`/`.md`)을 전사·요약해
  **회의록 DB에 새 회의록**으로 작성.
- 인자가 없으면 → **경로 A**: C조_한컴 변화(소스 DB + 페이지 산문)를 감지해
  **"노션 변경 내용 정리 (Claude 전용)" 페이지에 날짜별 로그**로 추가.

두 경로 모두 **초안을 먼저 보여주고, 승인받은 뒤에만** Notion에 씁니다. 자세한 절차는 `minutely` 스킬(SKILL.md).
