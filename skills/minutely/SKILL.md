---
name: minutely
description: >-
  두 가지 작업. (A) Notion 'C조_한컴' 페이지의 변화를 감지해 "노션 변경 내용 정리 (Claude 전용)"
  페이지에 날짜별 로그로 정리. 트리거: "노션 정리", "노션 변경 정리", "변경점 정리해줘", "/minutely".
  (B) 회의 녹음 파일이나 텍스트 파일을 주면 전사·요약해 "회의록" DB에 새 회의록으로 작성.
  트리거: "이 녹음 회의록으로", "회의록 작성", "/minutely meeting <파일>". 두 경로 모두 초안을
  먼저 보여주고 사용자 승인 후에만 Notion에 씁니다.
---

# Minutely — 노션 변경 정리 & 회의록 작성

두 경로가 있습니다. 어느 쪽이든 **초안 승인 전에는 Notion에 절대 쓰지 마세요.**

- **경로 A** (인자 없음, "노션 정리"): C조_한컴 변화 → **"노션 변경 내용 정리 (Claude 전용)" 페이지**에 로그 추가.
- **경로 B** (`meeting <파일>`, 녹음/텍스트 파일): 파일 → 전사·요약 → **회의록 DB**에 새 회의록 작성.

## 사전 요구사항

- **Notion MCP 커넥터** 연결 필수. `notion-fetch id:"self"`로 확인, 미연결이면 안내 후 중단.
- 경로 B 음성만: `GEMINI_API_KEY` 또는 `OPENAI_API_KEY`(`.env`/환경변수) + `ffmpeg`. 둘 다 있으면 Gemini 우선.
  둘 다 없으면 로컬 Whisper(`pip install faster-whisper`, 계정·과금 불필요)로 자동 폴백 — 대신 느리고
  정확도가 클라우드보다 떨어짐. 텍스트 파일은 불필요.
- 스크립트: `$CLAUDE_PLUGIN_ROOT/skills/minutely/scripts/` (config.py에 아래 id 상수 동일).

## 고정 대상 (config.py와 동일)

- 감시 페이지 `C조_한컴`: `3aabdeac-d0b4-804d-a1c2-dfc339401282`
- **경로 A 출력**: "노션 변경 내용 정리 (Claude 전용)" 페이지 `3abbdeac-d0b4-802e-be23-f0a4c4f131e0`
- **경로 B 출력**: 회의록 DB `collection://c5bbdeac-d0b4-8333-bba6-07d1ccebfcfb`
  - 속성: `회의명`(title) · `날짜`(date) · `내용`(text, 간략 요약) · `상태`(select: 진행 예정/진행 중/완료)
  - 회의 전체 내용은 페이지 본문에 작성 (B2 참고)
- **소스 DB (변화 감시)** 5개: `ee9bdeac-d0b4-83f2-a974-079e24493877`, `949bdeac-d0b4-8273-a20e-07bd8585adad`,
  `533bdeac-d0b4-825b-b53a-87ceec15f904`, `2e1bdeac-d0b4-82a1-bdd8-87f9ca7d2a93`, `6f6bdeac-d0b4-82b8-97f9-87eb00fdd2c4`
- **diff 제외** (피드백 루프 방지): 회의록 `c5bb…`, 데일리 스크럼 `a79bdeac-d0b4-83b2-8ace-077993a8dd69`

---

## 경로 A — Notion 변화 → "노션 변경 내용 정리 (Claude 전용)" 페이지

### A1. 현재 상태 수집
1. **소스 DB 5개**: 각각 `notion-query-data-sources` (`SELECT * FROM "collection://…"`)로 행 수집.
   정규화해 `.minutely/current.json`에 저장 (형식은 아래). 출력/제외 DB는 넣지 않음.
2. **페이지 산문**: `notion-fetch`로 C조_한컴을 받습니다. 큰 페이지라 결과가 파일로 자동 저장되면,
   그 파일 내용을 `.minutely/page_new.txt`로 저장하세요(표·콜아웃 포함 원문 그대로).

`.minutely/current.json` 형식:
```json
{"page_id":"3aabdeac-d0b4-804d-a1c2-dfc339401282","captured_at":"<ISO>",
 "items":{"<행 id>":{"kind":"row","source":"<DB 이름>","title":"...","text":"..."}}}
```

### A2. diff (두 갈래)
```
python "$CLAUDE_PLUGIN_ROOT/skills/minutely/scripts/snapshot.py" diff --current .minutely/current.json
python "$CLAUDE_PLUGIN_ROOT/skills/minutely/scripts/pagediff.py" --old .minutely/page.txt --new .minutely/page_new.txt
```
- `snapshot.py` = DB 행의 added/modified/removed. `pagediff.py` = 산문의 `[+]/[-]` 구간.
- **최초 실행** (snapshot.py가 `baseline:true` 또는 pagediff가 `BASELINE_MISSING`): 아직 기준선이 없음.
  A6의 promote만 하고 "기준선을 만들었습니다. 다음 실행부터 변화를 정리합니다." 보고 후 종료.
- 둘 다 변화 없으면(`NO_PROSE_CHANGE` + diff 빈 배열) 보고 후 종료.

### A3. 요약
DB 변경 + 산문 변경을 사람이 읽을 요약으로 묶으세요. 표 태그 재정렬 같은 노이즈는 버리고,
의미 있는 결정·추가·미결정 사항만 남깁니다. (미결정/이슈는 눈에 띄게 표시.)

### A4. 초안 (한국어 존댓말)
Claude 전용 페이지에 추가할 **로그 블록**을 채팅에 먼저 보여주세요:
```
## YYYY-MM-DD HH:MM 변경 정리
· [소스/섹션] 무엇이 어떻게 바뀌었는지
· [미결정] 있으면 액션아이템으로
```

### A5. 확인 후 쓰기 (페이지에 이어붙이기)
- 승인 시에만 `notion-update-page`(`command: "insert_content"`, `position: {"type":"end"}`)로
  CHANGE_LOG 페이지(`3abbdeac-d0b4-802e-be23-f0a4c4f131e0`) **맨 끝에** 위 블록을 추가합니다.
  기존 로그는 보존됩니다(append). 새 페이지를 만들지 않습니다.
- 승인 안 하면 수정 반영해 다시 보여주세요.

### A6. 스냅샷 갱신 (쓰기 성공 후에만)
```
python "$CLAUDE_PLUGIN_ROOT/skills/minutely/scripts/snapshot.py" promote --current .minutely/current.json
```
그리고 `.minutely/page_new.txt`를 `.minutely/page.txt`로 옮깁니다(다음 실행의 산문 기준선).

---

## 경로 B — 회의 녹음/텍스트 파일 → 회의록 DB

`/minutely meeting <파일경로>` 또는 "이 파일 회의록으로 정리해줘".

### B1. 파일 → 텍스트
- 확장자가 오디오/영상(`.m4a .mp3 .wav .mp4 …`)이면:
  ```
  python "$CLAUDE_PLUGIN_ROOT/skills/minutely/scripts/transcribe.py" "<파일경로>"
  ```
  표준출력의 전사문을 사용. 키/ffmpeg 없으면 스크립트 안내 메시지를 사용자에게 전달 후 중단.
- 확장자가 텍스트(`.txt .md`)이면 파일을 그대로 읽습니다(전사 불필요).

### B1.5 참고 소스 보강
대상 날짜에 "일정" DB(`collection://949bdeac-d0b4-8273-a20e-07bd8585adad`, `구분: 회의록`인 행 —
오전/오후 회의록 등)나 "데일리 스크럼" DB(`collection://a79bdeac-d0b4-83b2-8ace-077993a8dd69`)에
같은 날짜 항목이 있으면 열어서 같이 참고합니다. "일정" 항목은 녹음 전사엔 없는 **담당자별 업무 계획**을
담고 있는 경우가 많음 — 있으면 회의록 불릿에 `**→ 이름 담당**` 형식으로 반영. 둘 다 없으면 생략.

### B2. 요약 → 회의록 양식
전사문/텍스트를 **회의록** 양식으로 정리하되, 아래 두 부분을 분리합니다:
- **본문**(`content`, 페이지 body): 안건·논의·결정·액션아이템 전체를 기존 회의록의 `·` 불릿 스타일로.
- `내용` **속성**(text): 본문을 1~3줄로 압축한 간략 요약.
그 외 `회의명` · `날짜`(파일/사용자 지정 또는 오늘) · `상태`.
초안 전에 회의록 DB 최신 몇 행을 읽어 문체를 맞추세요.

**화자명 교정**: 전사 결과에 다음 이름이 들리면 교정합니다 — "성훈"→"성원", "서원"→"성원", "도현"→"도연".
단 "정기준"(회의 진행/MC, "기준 님")은 별개 인물이니 성원으로 합치지 않습니다.

**서식**: 불릿은 `· **항목** : 설명`처럼 콜론 앞 항목명을 볼드 처리합니다. [미결정/액션아이템]은
일반 목록이 아니라 콜아웃으로 씁니다:
```
<callout icon="💡" color="red_bg">
	**[미결정/액션아이템]**
	· **항목** 설명
</callout>
```

**변경 이력**: 하루에 오전·오후 회의가 모두 있을 때, 오전 내용이 오후에 바뀌면 오후 섹션 해당 불릿에
`(오전: X → 변경: Y)`를 붙입니다. 바뀌지 않은 항목까지 표시하지 않습니다. 오전 섹션 자체는 건드리지 않습니다.

### B3. 확인 후 쓰기
- 쓰기 전 같은 날짜 행이 있는지 `notion-query-data-sources`로 확인.
  - **없으면**: `notion-create-pages`로 회의록 DB(`collection://c5bbdeac-d0b4-8333-bba6-07d1ccebfcfb`)에
    새 행 생성. `content`에 본문 전체, `properties.내용`에 간략 요약.
  - **같은 날짜 행이 이미 있으면**(하루 두 번째 녹음 등): 새 행을 만들지 않고, 기존 페이지 끝에
    `notion-update-page`(`insert_content`, `position: {"type":"end"}`)로 `---` 구분선 + 시간대
    구분한 새 섹션(예: `## 오후 회의 진행 (16:41~)`)을 이어붙입니다.
- 승인 안 하면 수정 반영해 다시 보여주세요.

---

## 원칙
- **승인 없이는 Notion에 쓰지 않는다.** 초안 → 확인 → 쓰기.
- 추정으로 지어내지 않는다. 모르면 비우거나 물어본다.
- 한국어 존댓말로 보고한다.
