# 변경 이력 (Claude Code)

## 2026-07-29 10:19  ·  파일 1개 · 편집 1건 · +68 / -0

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| build_pdf.py | 1 | +68 | -0 | 신규/덮어씀 |

**[1] build_pdf.py · 신규/덮어씀  (+68/-0)**
```diff
+ #!/usr/bin/env python3
+ """팀원_가이드.md → HTML(mermaid) → (Chrome headless) → PDF."""
+ import html
+ import re
+ import sys
+ from pathlib import Path
+ import markdown
+ 
+ … 외 60줄
```

---

## 2026-07-29 10:12  ·  파일 2개 · 편집 4건 · +99 / -28

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| minutely_diagrams_preview.md | 1 | +71 | -0 | 신규/덮어씀 |
| 팀원_가이드.md | 3 | +28 | -28 | 수정 |

**[1] minutely_diagrams_preview.md · 신규/덮어씀  (+71/-0)**
```diff
+ # Minutely 다이어그램 미리보기
+ 
+ 팀원 가이드(`docs/팀원_가이드.md`)에 들어간 mermaid 다이어그램 3개를 렌더한 모습입니다.
+ 
+ ---
+ 
+ ## 1. 구조 한눈에
+ 
+ … 외 63줄
```
**[2] 팀원_가이드.md · 수정  (+13/-13)**
```diff
-     U[사용자: /minutely 또는 '노션 정리'] --> C[커맨드 minutely.md]
-     C --> S[스킬 SKILL.md<br/>= 순서가 적힌 지시서]
-     S -->|Notion 읽기·쓰기| T1
-     subgraph SCRIPTS[스크립트 skills/minutely/scripts]
-       A1[snapshot.py<br/>표 변화 비교]
-       A2[pagediff.py<br/>글 변화 비교]
-       A3[transcribe.py<br/>녹음 받아쓰기]
-       A4[config.py<br/>주소·열쇠 보관]
- … 외 5줄
+     U["사용자: /minutely 또는 노션 정리"] --> C["커맨드 minutely.md"]
+     C --> S["스킬 SKILL.md<br/>순서가 적힌 지시서"]
+     S -->|"Notion 읽기·쓰기"| T1
+     subgraph SCRIPTS["스크립트 · scripts/"]
+       A1["snapshot.py<br/>표 변화 비교"]
+       A2["pagediff.py<br/>글 변화 비교"]
+       A3["transcribe.py<br/>녹음 받아쓰기"]
+       A4["config.py<br/>주소·열쇠 보관"]
+ … 외 5줄
```
**[3] 팀원_가이드.md · 수정  (+8/-8)**
```diff
-     A[1.모으기<br/>Notion→임시파일] --> B[2.비교<br/>snapshot.py·pagediff.py]
-     B --> C{바뀐 게<br/>있나?}
-     C -->|없음/첫실행| Z[기준선만 저장하고 끝]
-     C -->|있음| D[3.요약]
-     D --> E[4.초안 보여주기]
-     E --> F{사람이 OK?}
-     F -->|예| G[5.페이지에 덧붙이기<br/>notion-update-page]
-     G --> H[6.기준선 갱신]
+     A["1. 모으기<br/>Notion→임시파일"] --> B["2. 비교<br/>snapshot.py·pagediff.py"]
+     B --> C{"바뀐 게 있나?"}
+     C -->|"없음/첫실행"| Z["기준선만 저장하고 끝"]
+     C -->|있음| D["3. 요약"]
+     D --> E["4. 초안 보여주기"]
+     E --> F{"사람이 OK?"}
+     F -->|예| G["5. 페이지에 덧붙이기<br/>notion-update-page"]
+     G --> H["6. 기준선 갱신"]
```
**[4] 팀원_가이드.md · 수정  (+7/-7)**
```diff
-     A[회의 파일] --> B{녹음이야<br/>텍스트야?}
-     B -->|녹음/영상| C[transcribe.py<br/>받아쓰기]
-     B -->|.txt/.md| D[그냥 읽기]
-     C --> E[회의록 모양 요약]
-     E --> F[초안 보여주기]
-     F --> G{OK?}
-     G -->|예| H[회의록에 새 줄<br/>notion-create-pages]
+     A["회의 파일"] --> B{"녹음이야 텍스트야?"}
+     B -->|"녹음/영상"| C["transcribe.py<br/>받아쓰기"]
+     B -->|".txt/.md"| D["그냥 읽기"]
+     C --> E["회의록 모양 요약"]
+     E --> F["초안 보여주기"]
+     F --> G{"OK?"}
+     G -->|예| H["회의록에 새 줄<br/>notion-create-pages"]
```

---

## 2026-07-29 10:05  ·  파일 3개 · 편집 4건 · +234 / -4

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| lovely-foraging-goblet.md | 1 | +52 | -0 | 신규/덮어씀 |
| 팀원_가이드.md | 2 | +181 | -4 | 신규/덮어씀, 수정 |
| README.md | 1 | +1 | -0 | 추가 |

**[1] lovely-foraging-goblet.md · 신규/덮어씀  (+52/-0)**
```diff
+ # 팀원용 입문 가이드 문서 작성 (docs/팀원_가이드.md)
+ 
+ ## Context
+ 
+ 사용자가 팀원(입문자)에게 minutely 플러그인을 설명할 **쉬운 가이드**를 원함. 기존 문서는
+ 기획서(설계 근거)·설치가이드(사용법)·스킬_상세(기술 상세)로 이미 있으나, **Claude Code 플러그인을
+ 처음 보는 사람**이 "이 스크립트는 ~하는 애구나, 스킬이 이렇게 동작하는구나"를 스스로 이해·확인할 수
+ 있는 **입문자 눈높이 종합 가이드**가 없음.
+ … 외 44줄
```
**[2] 팀원_가이드.md · 신규/덮어씀  (+177/-0)**
```diff
+ # Minutely 팀원 가이드 (입문자용)
+ 
+ Claude Code 플러그인을 처음 보는 팀원도 "아, 이건 이렇게 돌아가는구나"를 알 수 있게 쉽게 정리했습니다.
+ 어려운 말엔 항상 괄호로 비유를 붙였습니다.
+ 
+ ---
+ 
+ ## 1. 이 플러그인 뭐예요?
+ … 외 169줄
```
**[3] README.md · 추가  (+1/-0)**
```diff
+ - [팀원 가이드 (입문자용)](docs/팀원_가이드.md) — 개념부터 쉽게, 다이어그램 포함. **여기부터 읽으세요**
```
**[4] 팀원_가이드.md · 수정  (+4/-4)**
```diff
-     S -->|계산 시킴| SC[스크립트 4개]
-     S -->|Notion 읽기·쓰기| M[(Notion MCP 커넥터)]
-     subgraph SC[스크립트 skills/minutely/scripts]
-     subgraph M[Notion 도구]
+     S -->|계산 시킴| A1
+     S -->|Notion 읽기·쓰기| T1
+     subgraph SCRIPTS[스크립트 skills/minutely/scripts]
+     subgraph NOTION[Notion MCP 도구]
```

---

## 2026-07-28 15:08  ·  파일 2개 · 편집 2건 · +184 / -0

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| 기획서.md | 1 | +76 | -0 | 신규/덮어씀 |
| 설치_및_적용방법.md | 1 | +108 | -0 | 신규/덮어씀 |

**[1] 기획서.md · 신규/덮어씀  (+76/-0)**
```diff
+ # Minutely 기획서
+ 
+ ## 1. 배경 · 목적
+ 
+ C조_한컴 프로젝트의 기획·자료는 Notion **C조_한컴** 페이지에서 관리된다. 팀원이 페이지를
+ 계속 수정하는데, **무엇이 바뀌었는지**를 사람이 매번 눈으로 훑어 옮기는 일이 번거롭다.
+ 또 회의 내용을 회의록으로 옮기는 것도 수작업이다.
+ 
+ … 외 68줄
```
**[2] 설치_및_적용방법.md · 신규/덮어씀  (+108/-0)**
```diff
+ # Minutely 설치 및 적용 방법
+ 
+ ## 1. 사전 요구사항
+ 
+ - **Notion MCP 커넥터 연결** (필수) — 경로 A/B 모두 Notion 읽기·쓰기에 필요.
+ - **Python 3** — diff/전사 스크립트 실행 (외부 패키지 불필요, 표준 라이브러리만).
+ - **경로 B 음성만**: `OPENAI_API_KEY` + `ffmpeg`. (텍스트 파일 입력은 둘 다 불필요.)
+ 
+ … 외 100줄
```

---

## 2026-07-28 14:42  ·  파일 5개 · 편집 5건 · +273 / -2

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| config.py | 1 | +8 | -2 | 수정 |
| pagediff.py | 1 | +65 | -0 | 신규/덮어씀 |
| SKILL.md | 1 | +114 | -0 | 신규/덮어씀 |
| minutely.md | 1 | +16 | -0 | 신규/덮어씀 |
| README.md | 1 | +70 | -0 | 신규/덮어씀 |

**[1] config.py · 수정  (+8/-2)**
```diff
- # 출력 DB (여기에 새 행 생성) — collection id
- OUTPUT_COLLECTIONS = {
+ # 경로 A: 노션 변화 정리 로그를 쌓는 페이지 (회의록 아님)
+ CHANGE_LOG_PAGE_ID = "3abbdeac-d0b4-802e-be23-f0a4c4f131e0"  # 노션 변경 내용 정리 (Claude 전용)
+ 
+ # 경로 B: 회의 녹음/텍스트를 정리해 새 행을 만드는 회의록 DB
+ MEETING_MINUTES_COLLECTION = "c5bbdeac-d0b4-8333-bba6-07d1ccebfcfb"  # 회의록 (1)
+ 
+ # diff에서 제외할 출력/자동생성 DB (피드백 루프 방지) — collection id
+ EXCLUDED_COLLECTIONS = {
```
**[2] pagediff.py · 신규/덮어씀  (+65/-0)**
```diff
+ #!/usr/bin/env python3
+ """페이지 산문 dump 두 개(이전/현재)를 비교해 바뀐 구간을 뽑는다.
+ 
+ C조_한컴 페이지는 표·콜아웃이 많은 큰 문서라 소스 DB row 스냅샷만으로는 산문 변화를
+ 못 잡는다. 이 스크립트는 이전 dump와 현재 dump를 difflib로 비교해 insert/replace/delete
+ 구간을 사람이 읽을 만하게 출력한다. Claude가 그 결과를 요약한다. 표준 라이브러리만.
+ """
+ from __future__ import annotations
+ … 외 57줄
```
**[3] SKILL.md · 신규/덮어씀  (+114/-0)**
```diff
+ ---
+ name: minutely
+ description: >-
+   두 가지 작업. (A) Notion 'C조_한컴' 페이지의 변화를 감지해 "노션 변경 내용 정리 (Claude 전용)"
+   페이지에 날짜별 로그로 정리. 트리거: "노션 정리", "노션 변경 정리", "변경점 정리해줘", "/minutely".
+   (B) 회의 녹음 파일이나 텍스트 파일을 주면 전사·요약해 "회의록" DB에 새 회의록으로 작성.
+   트리거: "이 녹음 회의록으로", "회의록 작성", "/minutely meeting <파일>". 두 경로 모두 초안을
+   먼저 보여주고 사용자 승인 후에만 Notion에 씁니다.
+ … 외 106줄
```
**[4] minutely.md · 신규/덮어씀  (+16/-0)**
```diff
+ ---
+ description: Notion 'C조_한컴' 변화를 'Claude 전용' 페이지에 정리 / 회의 파일은 회의록으로 (meeting <파일>)
+ argument-hint: "[meeting <녹음또는텍스트파일>]"
+ ---
+ 
+ `minutely` 스킬로 정리하세요.
+ 
+ 인자: `$ARGUMENTS`
+ … 외 8줄
```
**[5] README.md · 신규/덮어씀  (+70/-0)**
```diff
+ # Minutely — 노션 변경 정리 & 회의록 작성 플러그인
+ 
+ C조_한컴 프로젝트를 위한 Claude Code 플러그인. 두 가지를 합니다.
+ 
+ - **경로 A — 노션 변경 정리**: `C조_한컴` 페이지(소스 DB 5개 + 페이지 산문)의 변화를 로컬 스냅샷과
+   비교해 바뀐 부분만 뽑아, **"노션 변경 내용 정리 (Claude 전용)"** 페이지에 날짜별 로그로 정리합니다.
+ - **경로 B — 회의록 작성**: 회의 **녹음/영상 파일**이나 **텍스트 파일**을 주면 전사·요약해
+   **회의록 DB**에 새 회의록으로 작성합니다.
+ … 외 62줄
```

---

## 2026-07-28 14:03  ·  파일 1개 · 편집 2건 · +18 / -7

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| SKILL.md | 2 | +18 | -7 | 수정 |

**[1] SKILL.md · 수정  (+4/-1)**
```diff
- > ⚠️ **피드백 루프 방지**: 출력 DB(회의록·데일리)는 C조_한컴 하위지만 **감시 대상에서 제외**합니다.
+ > ⚠️ **피드백 루프 방지**: 출력 DB(회의록·데일리)는 C조_한컴 하위지만 **diff 대상에서 제외**합니다.
+ >
+ > **단, "diff 제외"와 "읽지 않음"은 다릅니다.** 회의록/데일리 DB는 diff엔 안 넣지만, 초안을 만들기 전
+ > **맥락·양식 참고와 중복 방지를 위해 읽습니다** (기존 문체·불릿 스타일을 따라가고, 같은 날 회의록에 이어쓰기 위함).
```
**[2] SKILL.md · 수정  (+14/-6)**
```diff
- 대상 DB 스키마에 맞춰 채팅에 **초안을 먼저** 보여주세요.
- - 회의록: `회의명`(예: "YYYY-MM-DD 노션 변경 정리"), `날짜`(오늘), `내용`(변경 요약 — 무엇이 왜 바뀌었는지 불릿), `상태`
- ### A5. 확인 후 쓰기
- - 사용자가 승인하면 그때만 `notion-create-pages`로 해당 data source(`collection://...`)에 새 행을 만듭니다.
- - **중복 방지**: 쓰기 전에 `notion-query-data-sources`로 같은 날짜/제목 행이 이미 있는지 확인하세요.
- - 승인 안 하면 쓰지 말고 수정 요청을 반영해 초안을 다시 보여주세요.
+ ### A3.5. 기존 회의록 읽기 (양식·톤 참고)
+ 초안 전에 `notion-query-data-sources`로 회의록 DB(`collection://c5bbdeac-d0b4-8333-bba6-07d1ccebfcfb`)의
+ **최신 행 몇 개**를 읽으세요. 기존 `내용`의 불릿 스타일(예: `·`로 시작하는 짧은 결정 나열)을 그대로 따라갑니다.
+ 대상 DB 스키마에 맞춰 채팅에 **초안을 먼저** 보여주세요. 기존 회의록 문체를 따릅니다.
+ - 회의록: `회의명`·`날짜`·`내용`(변경 요약 — 기존 불릿 스타일로) ·`상태`
+ 
+ ### A5. 확인 후 쓰기 — **같은 날 회의록엔 이어쓰기**
+ 회의록은 **새 행을 남발하지 말고 기존 것에 이어씁니다**. 순서:
+ … 외 6줄
```

---

## 2026-07-28 11:47  ·  파일 1개 · 편집 1건 · +47 / -0

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| current.json | 1 | +47 | -0 | 신규/덮어씀 |

**[1] current.json · 신규/덮어씀  (+47/-0)**
```diff
+ {
+   "page_id": "3aabdeac-d0b4-804d-a1c2-dfc339401282",
+   "captured_at": "2026-07-28",
+   "items": {
+     "571bdeac-d0b4-83bb-a6af-01df4b96985a": {
+       "kind": "row", "source": "프로젝트안내", "title": "최종 발표",
+       "text": "발표날짜 2026-09-08 | 온·오프라인, 시연+발표 10분·Q&A 10분 | 제출: 코드 산출물(GitHub), 시연 영상, 최종 보고서, 발표 PPT(PDF), 팀원 소개"
+     },
+ … 외 39줄
```

---

## 2026-07-28 11:35  ·  파일 1개 · 편집 1건 · +19 / -0

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| marketplace.json | 1 | +19 | -0 | 신규/덮어씀 |

**[1] marketplace.json · 신규/덮어씀  (+19/-0)**
```diff
+ {
+   "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
+   "name": "minutely",
+   "metadata": {
+     "description": "Notion C조_한컴 변화를 회의록/데일리 스크럼 양식으로 자동 정리하는 플러그인."
+   },
+   "owner": {
+     "name": "jkjun"
+ … 외 11줄
```

---

## 2026-07-28 10:48  ·  파일 10개 · 편집 10건 · +834 / -0

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| lovely-foraging-goblet.md | 1 | +120 | -0 | 신규/덮어씀 |
| plugin.json | 1 | +12 | -0 | 신규/덮어씀 |
| minutely.md | 1 | +15 | -0 | 신규/덮어씀 |
| SKILL.md | 1 | +125 | -0 | 신규/덮어씀 |
| .gitignore | 1 | +10 | -0 | 신규/덮어씀 |
| README.md | 1 | +47 | -0 | 신규/덮어씀 |
| snapshot.py | 1 | +120 | -0 | 신규/덮어씀 |
| test_snapshot.py | 1 | +87 | -0 | 신규/덮어씀 |
| config.py | 1 | +63 | -0 | 신규/덮어씀 |
| transcribe.py | 1 | +235 | -0 | 신규/덮어씀 |

**[1] lovely-foraging-goblet.md · 신규/덮어씀  (+120/-0)**
```diff
+ # Minutely — Notion 회의록 자동 정리 플러그인
+ 
+ ## Context (왜 만드나)
+ 
+ C조_한컴 프로젝트의 기획·자료는 Notion에서 관리된다. 팀원이 Notion "C조_한컴" 페이지를
+ 계속 고치는데, **무엇이 바뀌었는지**를 사람이 매번 눈으로 훑어 회의록에 옮기는 게 번거롭다.
+ 
+ 목표: Claude Code 플러그인 `minutely`를 만들어 (1) "C조_한컴" 페이지 전체의 **변화**를
+ … 외 112줄
```
**[2] plugin.json · 신규/덮어씀  (+12/-0)**
```diff
+ {
+   "name": "minutely",
+   "version": "0.1.0",
+   "displayName": "Minutely — 노션 회의록 자동 정리",
+   "description": "Notion 'C조_한컴' 페이지 전체의 변화를 로컬 스냅샷 diff로 감지하고, 회의록·데일리 스크럼 DB 양식 중 알맞은 곳에 초안을 만들어 확인 후 기록합니다. 회의 음성 녹음도 Whisper API로 전사·요약합니다.",
+   "author": {
+     "name": "jkjun"
+   },
+ … 외 4줄
```
**[3] minutely.md · 신규/덮어씀  (+15/-0)**
```diff
+ ---
+ description: Notion 'C조_한컴' 변화를 감지해 회의록/데일리 스크럼 양식으로 정리 (음성: /minutely audio <파일>)
+ argument-hint: "[audio <녹음파일경로>]"
+ ---
+ 
+ `minutely` 스킬을 사용해 회의록을 정리하세요.
+ 
+ 인자: `$ARGUMENTS`
+ … 외 7줄
```
**[4] SKILL.md · 신규/덮어씀  (+125/-0)**
```diff
+ ---
+ name: minutely
+ description: >-
+   Notion 'C조_한컴' 프로젝트 페이지의 변화를 감지해 회의록/데일리 스크럼 DB 양식으로
+   정리하거나, 회의 음성 녹음을 전사해 회의록으로 요약할 때 사용합니다.
+   트리거: "노션 정리", "회의록 정리", "노션 변경 정리해줘", "회의록 만들어줘",
+   "회의 녹음 정리", "/minutely", "minutely". 로컬 스냅샷 diff로 이전 대비 바뀐 부분만
+   뽑아 상황별(회의록/데일리 스크럼/아카이빙)로 분류하고, 초안을 먼저 보여준 뒤 사용자
+ … 외 117줄
```
**[5] .gitignore · 신규/덮어씀  (+10/-0)**
```diff
+ # Minutely 런타임 상태 (스냅샷·전사 임시파일) — 커밋하지 않음
+ .minutely/
+ 
+ # 로컬 시크릿
+ .env
+ 
+ # Python
+ __pycache__/
+ … 외 2줄
```
**[6] README.md · 신규/덮어씀  (+47/-0)**
```diff
+ # Minutely — 노션 회의록 자동 정리 플러그인
+ 
+ Notion **C조_한컴** 프로젝트 페이지의 변화를 자동으로 감지해, 이미 있는 **회의록 / 데일리 스크럼**
+ DB 양식 중 알맞은 곳에 초안을 만들어 준 뒤 **확인을 받고** 기록합니다. 회의 **음성 녹음**도
+ Whisper API로 전사해 회의록으로 요약합니다.
+ 
+ ## 동작 방식
+ 
+ … 외 39줄
```
**[7] snapshot.py · 신규/덮어씀  (+120/-0)**
```diff
+ #!/usr/bin/env python3
+ """Minutely 스냅샷 diff 코어.
+ 
+ C조_한컴 페이지를 정규화한 JSON을 직전 스냅샷과 비교해 added/modified/removed를 뽑는다.
+ Notion 접근은 스킬(Claude + MCP)이 담당하고, 이 스크립트는 순수 비교만 한다 — 표준 라이브러리만.
+ 
+ 정규화 입력 형태 (current.json):
+ {
+ … 외 112줄
```
**[8] test_snapshot.py · 신규/덮어씀  (+87/-0)**
```diff
+ #!/usr/bin/env python3
+ """snapshot.py diff 코어 유닛테스트. pytest 없이 `python test_snapshot.py`로 실행 가능."""
+ import json
+ import sys
+ import tempfile
+ import unittest
+ from pathlib import Path
+ 
+ … 외 79줄
```
**[9] config.py · 신규/덮어씀  (+63/-0)**
```diff
+ #!/usr/bin/env python3
+ """Minutely 공용 설정 — Notion 대상 id 상수 + OPENAI_API_KEY 로드."""
+ from __future__ import annotations
+ 
+ import os
+ from pathlib import Path
+ 
+ # --- Notion 대상 (SKILL.md와 동일하게 유지) ---
+ … 외 55줄
```
**[10] transcribe.py · 신규/덮어씀  (+235/-0)**
```diff
+ #!/usr/bin/env python3
+ """회의 음성 녹음 → OpenAI Whisper 전사. 표준 라이브러리만 사용.
+ 
+ 흐름: ffmpeg로 mono 16kHz mp3 추출 → (25MB 초과 시 시간 균등 분할) → OpenAI Whisper API
+ 업로드 → 세그먼트 텍스트를 이어붙여 표준출력으로 반환. 실패는 SystemExit 메시지로 안내.
+ 
+ watch 플러그인의 whisper.py를 OpenAI 전용으로 슬림화해 적응.
+ """
+ … 외 227줄
```

---

## 2026-07-28 10:36  ·  파일 1개 · 편집 1건 · +110 / -0

| 파일 | 편집수 | +added | -removed | 태그 |
|------|-------:|-------:|---------:|------|
| lovely-foraging-goblet.md | 1 | +110 | -0 | 신규/덮어씀 |

**[1] lovely-foraging-goblet.md · 신규/덮어씀  (+110/-0)**
```diff
+ # Minutely — Notion 회의록 자동 정리 플러그인
+ 
+ ## Context (왜 만드나)
+ 
+ C조_한컴 프로젝트의 기획·자료는 Notion에서 관리된다. 팀원이 Notion "C조_한컴" 페이지를
+ 계속 고치는데, **무엇이 바뀌었는지**를 사람이 매번 눈으로 훑어 회의록에 옮기는 게 번거롭다.
+ 
+ 목표: Claude Code 플러그인 `minutely`를 만들어 (1) Notion "C조_한컴" 페이지 전체의 **변화**를
+ … 외 102줄
```

---











