# codeStress (Clean Code Change Lab)

가상의 변경 요청을 AI Agent에게 시켜보고, 그 과정에서 발생하는 **변경 비용**을 측정하는 도구.

## 배경

"이 코드가 Clean한가?"는 정적 규칙으로 판단하기 어렵다.
대신 **"이 코드는 실제로 변경하기 쉬운가?"**를 직접 실험한다.

작은 요구사항 하나가 몇 개의 파일·계층에 영향을 주는지는 작업을 시작해야 알 수 있다.
이 하나의 가상 변경 실험을 **Change Drill**이라 부른다.

## 두 가지 모드

| 모드 | 하는 일 | 저장소 변경 |
|---|---|---|
| **예측 (Prediction)** | Agent 2개가 코드를 읽고 변경 비용을 *추정* | 없음 (읽기 전용) |
| **구현 (Implementation)** | Agent가 격리된 Worktree에서 실제로 *구현* | Worktree 내부만 |

## 예측 모드 워크플로우

```text
자연어 요청
  → 임시 시나리오 생성
  → 저장소 검증          (--predict)
  → 읽기 전용 Agent 2개 실행
  → 각자 예측 JSON 저장
  → CLI가 리포트 렌더링   (--predict-report)
  → git status 확인
```

```bash
# 1. 검증
python3 -m src.cli --repo-path <repo> --scenario-json '<json>' --predict --parallel 2

# 2. Agent 2개가 results/agent_{A,B}/prediction_<id>.json 작성

# 3. 리포트 출력
python3 -m src.cli --predict-report --results-dir results \
  --scenario-id <id> --scenario-name "<name>"
```

**리포트 형식의 단일 진실 공급원은 `src/prediction_report.py`다.**
Claude는 오케스트레이션만 하고, 비교 결과를 직접 작성하지 않는다.

출력 섹션(고정 순서): 헤더 → SCENARIO → KEY METRICS → ESTIMATE COMPARISON →
CONSENSUS → DIFFERENCE → 추정치 고지.

모든 수치는 정적 분석 기반 **추정치**이며 실측값이 아니다.

## 구현 모드 워크플로우

```text
시나리오 선택 → Worktree 생성 → Agent 구현 → 빌드 검증 → 비용 측정 → 리포트
```

```bash
python3 -m src.cli --repo-path <repo> --scenario <id> --phase setup
# (Agent 작업)
python3 -m src.cli --repo-path <repo> --scenario <id> --phase measure \
  --worktree-path <path> --base-commit <sha>
```

`--phase full`은 Agent를 기다리지 않으므로 빈 diff를 측정한다. 실제 실험에는 쓰지 않는다.

## 핵심 원칙

- **harness는 Agent를 호출하지 않는다.** Agent 실행은 `/change-drill` 프롬프트를 읽은
  어시스턴트가 담당하고, Python은 검증·측정·리포트만 맡는다.
- **원본 저장소는 수정되지 않는다.** 예측 모드는 읽기만, 구현 모드는 Worktree만 건드린다.
- **JSON은 증거, 터미널 리포트는 Python이 생성한다.**
