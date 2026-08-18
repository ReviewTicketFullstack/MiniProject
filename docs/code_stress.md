# Clean Code Change Lab (code_stress)

AI Agent를 활용해 코드베이스의 변경 가능성과 유지보수성을 실제 변경 실험으로 측정하는 자동화 도구

## 1. 배경

Clean Code를 정적인 규칙으로 판단하는 방식에 대한 의문에서 출발한다. 함수가 짧은지, 중복이 없는지, SOLID 원칙을 지키는지 확인하는 것만으로 실제 유지보수성이 좋은지 판단하기 어렵다. 따라서 “이 코드가 Clean한가?”가 아니라 “이 코드는 실제로 변경하기 쉬운가?”를 직접 실험한다.

## 2. 문제 정의

코드베이스의 변경 비용을 개발자가 사전에 객관적으로 파악하기 어렵다는 것이다. 작은 요구사항 하나가 몇 개의 파일과 계층에 영향을 주는지, 예상치 못한 변경 범위가 발생하는지는 실제 작업을 시작해야 알 수 있다.

## 3. 목표

가상의 변경 요청을 AI Agent에게 실제로 수행하게 하고, 그 과정에서 발생하는 변경 범위와 비용을 측정하여 코드베이스의 변화에 대한 취약 지점을 발견하는 것이다.

## 8. 핵심 개념

가상의 변경 요청을 실제로 수행해보고, 그 과정에서 발생하는 변경 비용을 측정하는 한다. 예를 들어 아래와 같은 과제를 가정한다.

- “Order에 새로운 필드를 추가하라”
- “인증 방식을 변경하라”
- “모든 에러 메시지를 존댓말로 변경하라”

위와 같은 과제를 AI Agent에게 전달한다.
Agent는 실제 개발자처럼 코드를 수정하고, 시스템은 이 과정에서 변경된 파일 수, 수정 범위, 관련 계층, 테스트 결과 등을 기록한다. 이러한 하나의 가상 변경 실험을 'Change Drill' 이라고 정의한다. 이를 여러 시나리오에 반복 적용하여 코드베이스가 어떤 종류의 변화에 강하고 약한지를 실험적으로 확인한다.

## 10. 메인 워크플로우

### 목표 워크플로우 (설계)

변경 시나리오 선택 → 독립 Worktree 생성 → AI Agent 변경 수행 → 빌드·테스트 검증 → 변경 비용 측정 → 결과 분석 및 리포트 생성

### 현재 구현된 워크플로우

위 단계는 하나의 프로그램이 아니라 **두 주체로 나뉘어** 수행된다.

| 단계 | 수행 주체 | 구현 위치 |
|---|---|---|
| 시나리오 선택 | Python harness | `src/cli.py` (카탈로그 ID 기반) |
| Worktree 생성 | Python harness | `src/worktree.py` |
| **AI Agent 변경 수행** | **Claude 어시스턴트 (harness 아님)** | `.claude/commands/change-drill.md` 프롬프트 |
| 빌드·테스트 검증 | Python harness | `src/measurement.py` |
| 변경 비용 측정 | Python harness | `src/measurement.py` |
| 리포트 생성 | Python harness | `src/report.py` |

주의할 점:

- **harness는 Coding Agent를 호출하지 않는다.** Agent 실행은 `/change-drill` 프롬프트를 읽은 어시스턴트가 수행하며, harness는 그 존재를 인지하지 못한다. 따라서 harness 단독 실행(`--phase full`)은 Agent를 기다리지 않고 즉시 측정하므로 빈 diff를 측정한다.
- **빌드와 테스트는 별도로 검증되지 않는다.** 탐지된 명령 하나만 실행하며, 테스트 성공 여부는 빌드 성공 여부를 그대로 복사한 값이다(`test_success = build_success`).
- 실제 실행은 `--phase setup` → (Agent 작업) → `--phase measure` 2단계로 나눠 호출한다.

## 18. MVP 범위

Claude Hook, Skill, Sub-agent, Parallel Execution을 활용해 몇 가지 대표적인 변경 시나리오를 실행한다. 파일 변경 수·변경 범위·성공 여부·테스트 결과 등을 수집하여 “어떤 변경에 이 코드베이스가 강하고 약한가”를 보여주는 것까지 구현한다.

## 19. 병렬 Agent 정책

### Agent 실행 모델

- **CLI 기본값**: 1개 Agent (`--parallel` 기본값은 `1`)
- **병렬 모드 권장값**: 3개 Agent
- **권장 상한**: 3개 Agent
- **제약**: 병렬로 3개를 초과하는 Agent는 실행하지 않는다

> **구현 현황**: 이 상한은 **코드로 강제되지 않는 운영 관례**다. `--parallel`에는 범위 검증이 없어 `--parallel 4` 이상도 그대로 수용되어 worktree가 그 수만큼 생성된다.

### 병렬 실행의 이점

각 Agent는 독립적인 Worktree에서 동시 실행되므로:
- 실험의 독립성 보장 (Agent 간 간섭 없음)
- 비결정성 측정 가능 (여러 실행 비교)
- 벽시계 시간 효율 (순차 실행 대비 N배 빠름)

### 설계 제약

- Agent 간 워크트리 격리 필수
- 원본 저장소는 수정되지 않음
- 각 Agent의 결과는 독립적으로 측정됨
- 3개 초과 병렬 실행 금지

### 병렬 모드 구현 현황 (중요)

병렬 실행은 **setup 단계까지만 동작한다.**

| 단계 | 상태 |
|---|---|
| N개 Worktree 생성 (`setup_worktrees()`) | ✅ 동작 |
| Agent 동시 실행 | ⚠️ harness 밖(어시스턴트)에서 수행 |
| 병렬 측정 (`measure_all()`) | ❌ CLI에서 도달 불가 |
| 에이전트 간 비교 분석 (`analysis.py`) | ❌ CLI에서 도달 불가 |
| Worktree 정리 | ❌ 자동 정리되지 않음 (수동 필요) |

원인: `--phase measure --parallel N`은 worktree 목록이 비어 있는 새 `ParallelDrill` 객체를 만든 뒤 `measure_all()`을 호출하므로 항상 다음 에러로 종료된다.

```
Error: Harness not properly initialized. Call setup_worktrees() first.
```

setup 프로세스와 measure 프로세스 사이에 상태를 넘기는 영속화 계층이 없다. 병렬 실험 결과는 현재 worktree별로 단일 에이전트 measure를 수동 호출해 수집해야 한다.

### 다중 시나리오 병렬 실행

`--parallel N`은 **동일한 하나의 시나리오**에 N개 Agent를 배정한다(비결정성 측정용). 서로 다른 시나리오를 동시에 돌리는 기능(유저 시나리오 S2)은 구현되어 있지 않다.
