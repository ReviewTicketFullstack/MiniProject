# Minutely — 노션 변경 정리 & 회의록 작성 플러그인

C조_한컴 프로젝트를 위한 Claude Code 플러그인. 두 가지를 합니다.

- **경로 A — 노션 변경 정리**: `C조_한컴` 페이지(소스 DB 5개 + 페이지 산문)의 변화를 로컬 스냅샷과
  비교해 바뀐 부분만 뽑아, **"노션 변경 내용 정리 (Claude 전용)"** 페이지에 날짜별 로그로 정리합니다.
- **경로 B — 회의록 작성**: 회의 **녹음/영상 파일**이나 **텍스트 파일**을 주면 전사·요약해
  **회의록 DB**에 새 회의록으로 작성합니다.

두 경로 모두 **초안을 먼저 보여주고, 사용자가 승인해야만** Notion에 씁니다.

## 사용법

```
/minutely                         # 경로 A: 노션 변화 → 'Claude 전용' 페이지에 정리
/minutely meeting <녹음/영상파일>   # 경로 B: 전사 → 회의록 작성
/minutely meeting <파일.txt>       # 경로 B: 텍스트 파일 → 회의록 작성
```

자연어로도 됩니다: "노션 정리", "노션 변경 정리해줘" (경로 A) / "이 녹음 회의록으로", "회의록 작성" (경로 B).

## 동작 원리

**경로 A**
1. 소스 DB 5개는 `notion-query-data-sources`로, 페이지 산문은 `notion-fetch`로 수집.
2. `snapshot.py`(DB 행) + `pagediff.py`(산문)로 이전 스냅샷과 비교 → added/modified/removed.
3. 의미 있는 변경만 요약해 로그 블록 초안 생성 → 승인 시 Claude 전용 페이지 끝에 append.
4. 스냅샷 갱신.

> 회의록·데일리 스크럼 DB는 감시 대상 하위에 있지만 **diff에서 제외**합니다 — 자동 생성물이
> 다음 실행에서 "변화"로 잡히는 피드백 루프를 막기 위함입니다.

**경로 B**
1. 오디오/영상이면 `transcribe.py`(ffmpeg → OpenAI Whisper)로 전사, 텍스트 파일이면 그대로 읽기.
2. 회의록 양식(회의명·날짜·내용·상태)으로 요약 → 승인 시 회의록 DB에 새 행 생성.

## 사전 준비

- **Notion MCP 커넥터** 연결 (필수).
- 경로 B 음성만: `OPENAI_API_KEY`(`.env` 또는 환경변수) + `ffmpeg`. 텍스트 파일은 불필요.

## 상태 파일 (git 제외)

- `.minutely/snapshot.json` — 마지막으로 본 소스 DB 정규화 콘텐츠.
- `.minutely/page.txt` — 마지막으로 본 페이지 산문 dump.
- `.minutely/current.json`, `.minutely/page_new.txt` — 이번 실행 수집분.

## 문서

- [팀원 가이드 (입문자용)](docs/팀원_가이드.md) — 개념부터 쉽게, 다이어그램 포함. **여기부터 읽으세요**
- [기획서](docs/기획서.md) — 배경·설계 결정·아키텍처·한계
- [설치 및 적용 방법](docs/설치_및_적용방법.md) — 설치·환경설정·사용법·문제 해결
- [스킬·스크립트 상세](docs/스킬_상세.md) — 스킬의 전체 절차 지휘 방식과 스크립트별 역할

## 설치 (로컬)

```
claude plugin marketplace add "<이 repo 경로>"
claude plugin install minutely@minutely
```
설치 후 세션 재시작하면 `/minutely`와 자연어 트리거가 활성화됩니다.

## 구조

```
.claude-plugin/plugin.json      매니페스트
.claude-plugin/marketplace.json 로컬 설치용 마켓플레이스
commands/minutely.md            /minutely 커맨드
skills/minutely/SKILL.md        전체 절차
skills/minutely/scripts/
  snapshot.py                   소스 DB 행 스냅샷·diff
  pagediff.py                   페이지 산문 dump 비교
  transcribe.py                 오디오 → Whisper 전사
  config.py                     Notion id 상수 + OPENAI_API_KEY 로드
  tests/test_snapshot.py        diff 유닛테스트
```
