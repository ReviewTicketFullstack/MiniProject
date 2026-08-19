# 병렬 Agent 실행 정책

**최종 수정:** 2026-08-19

## 요약

| 항목 | 값 | 코드로 강제? |
|---|---|---|
| 최소 Agent | 1 | — |
| CLI 기본값 | 1 (`--parallel`) | ✅ |
| 예측 모드 | **정확히 2개** | ⚠️ 스킬 규약 |
| 구현 모드 권장 | 3개 | ❌ 관례 |
| 최대 Agent | 3개 | ❌ **미강제** — `--parallel` 범위 검증 없음 |

`--parallel 4` 이상도 CLI가 그대로 수용하며 그만큼 worktree를 만든다.

## 왜 상한이 3인가

- **자원**: worktree마다 체크아웃 사본이 필요하다. 3개가 실행 시간과 자원의 균형점.
- **증거 품질**: 독립 실행 3회면 구현 방식의 편차를 관찰하기에 충분하다. 그 이상은 수익 체감.
- **격리 복잡도**: worktree 관리가 3개까지는 안정적으로 확장된다.

## 모드별 실행 모델

### 예측 모드 — Agent 2개, 읽기 전용

Worktree를 만들지 않는다. 두 Agent가 **동일한 프롬프트**로 독립 분석하고,
각자 `results/agent_{A,B}/prediction_<id>.json`에 예측을 기록한다.

두 예측의 차이가 곧 신호다. 수치가 수렴하면 추정 신뢰도가 높고,
벌어지면 그 변경에 대해 코드베이스의 해석 여지가 크다는 뜻이다.

Agent는 대상 저장소의 파일을 **생성·수정·삭제·이름변경할 수 없다.**

### 구현 모드 — Agent N개, 격리된 Worktree

각 Agent는 `git worktree add --detach`로 만든 자기 디렉터리에서만 작업한다.

| 보장 | 상태 |
|---|---|
| Agent별 독립 Worktree | ✅ |
| 원본 저장소 미변경 | ✅ (worktree 메타데이터만 `.git/worktrees/`에 기록) |
| 쓰기 범위 제한 | ⚠️ 프롬프트 지시일 뿐, 파일시스템 샌드박스는 없음 |
| Agent별 개별 측정 | ✅ (`discover_worktrees()`로 measure 단계 복구) |
| Agent 간 비교 분석 | ✅ (`analysis.py`) |

## 실행 절차

**예측 모드**

```bash
python3 -m src.cli --repo-path <repo> --scenario-json '<json>' --predict --parallel 2
# Agent A, B 실행 → 각자 JSON 저장
python3 -m src.cli --predict-report --results-dir results \
  --scenario-id <id> --scenario-name "<name>"
```

**구현 모드**

```bash
python3 -m src.cli --repo-path <repo> --scenario <id> --phase setup --parallel 3
# Agent 3개가 각 worktree에서 구현
python3 -m src.cli --repo-path <repo> --scenario <id> --phase measure --parallel 3 \
  --worktree-path <path> --base-commit <sha>
```

## 미구현

- `--parallel` 값 범위 검증 (3 초과 차단)
- Agent별 실패 격리 — 하나가 실패하면 그대로 전파된다
- 사전 점검 (working tree clean 여부, 빌드 명령 존재 여부)
- 여러 시나리오 동시 실행 — `--parallel N`은 **하나의 시나리오**에 N개 Agent를 배정한다
