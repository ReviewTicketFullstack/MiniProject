# prompt-audit

클로드 코드가 남긴 세션 기록을 읽어, 프롬프트 품질과 그 프롬프트가 실제로
만들어 낸 결과 품질을 함께 채점하고 리포트를 만든다.

문장이 잘 다듬어져 있다고 좋은 프롬프트는 아니다. 모델이 엉뚱한 파일을 고치거나,
열 턴을 더 쓰거나, 결국 사용자가 중간에 끊었다면 그 프롬프트는 실패한 것이다.
그래서 이 도구는 입력 축과 결과 축을 따로 재고 둘을 교차해서 본다.

## 빠른 실행

```bash
cd /c/dev/weekly_project && PYTHONPATH=src python -m promptaudit
```

옵션 없이 실행하면 컴퓨터에 남아 있는 대화 기록을 전부 훑어 분석할 수 있는
대상을 목록으로 보여 주고, 무엇을 분석할지 물어본다. 무엇이 있는지만 보려면
`--list`, 묻지 않고 바로 돌리려면 `--project 이름`을 붙인다.

결과물은 `out/` 아래에 생긴다. 최종 리포트를 다른 자리에도 만들고 싶으면
`--html "C:/보고서/report.html"` 처럼 자리를 지정한다. 폴더만 주면 그 안에
`report.html` 로 만든다.

| 파일 | 내용 |
| --- | --- |
| `report.html` | 네 개 장으로 나뉜 리포트. 위쪽 버튼으로 장을 옮겨 다닌다 |
| `report.md` | 같은 내용의 마크다운 |
| `charts/*.png` | 차트 9종, 발표 슬라이드용 |
| `scores.json` | 프롬프트별 점수와 채점 기준 원본 |
| `judge_queue.json` | 아직 채점하지 않은 프롬프트 대기열 |

## 채점을 얹으려면

`out/judge_queue.json`을 클로드 코드에게 읽히고, 각 프롬프트를 두 번 채점하게
한다. 먼저 문장만 보고(blind), 그다음 실제로 벌어진 일까지 보고(aware) 매긴다.
결과를 `out/judge_results.json`에 쓰고 같은 명령을 다시 돌리면 리포트에
반영된다. 자세한 절차는 `.claude/skills/prompt-audit/SKILL.md`에 있다.

## 테스트

```bash
cd /c/dev/weekly_project && PYTHONPATH=src python tests/test_core.py
```

## 문서

| 문서 | 내용 |
| --- | --- |
| [기획서](docs/기획서.md) | 배경, 문제 정의, 두 축 설계, 한계 |
| [유저 시나리오](docs/유저시나리오.md) | 사용 흐름 세 가지와 예외 처리 |
| [시스템 설계도](docs/시스템설계도.md) | 파이프라인, 데이터 모델, 점수 계산식 |
| [깃허브 링크](docs/github.md) | 저장소 주소와 공개 전 확인 사항 |

## 요구 환경

파이썬 3.11 이상, matplotlib. 한글 차트를 위해 Malgun Gothic 같은 한글 폰트가
설치되어 있어야 한다. 트랜스크립트는 UTF-8이므로 PowerShell `Get-Content`로
직접 열면 한글이 깨진다. 파싱은 반드시 이 패키지를 통한다.
