# 깃허브 링크

## 저장소

- 프롬프트 분석 시스템: https://github.com/ReviewTicketFullstack/MiniProject/tree/mini_05

## 저장소 구조

팀 저장소 `MiniProject`에 주차별 브랜치로 올린다. 각 주차 브랜치는 서로
히스토리를 공유하지 않는 독립 브랜치이고, 그 주차 과제가 저장소 루트에
그대로 들어간다. 이 과제는 `mini_05` 브랜치다.

로컬 작업 폴더는 `C:/dev/weekly_project`이다. 다른 곳에서 내려받으려면
아래를 쓴다.

```bash
git clone -b mini_05 https://github.com/ReviewTicketFullstack/MiniProject.git
```

## 올리기 전에 확인할 것

이 저장소는 공개(public) 상태다. `out/` 아래 파일에는 실제 프롬프트 원문이
인용되어 있어서 지금은 통째로 올리지 않았다. 결과물을 함께 올릴 일이 생기면
공개 전에 다음을 확인한다.

| 확인 항목 | 방법 |
| --- | --- |
| 비밀값 노출 | 리포트 말미의 마스킹 규칙 목록을 확인한다 |
| 원문 인용 | `out/report.md`의 2부 사례를 눈으로 훑는다 |
| 점수 원본 | `out/scores.json`에는 원문이 들어가지 않지만 파일이 크므로 제외를 고려한다 |

공개하지 않을 파일은 `.gitignore`에 넣는다. 현재 `.gitignore`는 `out/`과
`Output/` 폴더를 통째로 제외하고 있다.

## 관련 저장소

- 분석 대상 프로젝트: ReviewTicketFullstack (팀 모노레포)
