# 깃허브 링크

## 저장소

- 프롬프트 분석 시스템: (아직 원격 저장소를 만들지 않았다. 아래 절차로 만든 뒤
  이 줄을 실제 주소로 바꾼다.)

## 원격 저장소 만드는 절차

로컬 저장소는 `C:/dev/weekly_project`이다. 아래 순서로 초기화하고 올린다.

```bash
cd /c/dev/weekly_project && git init && git add . && git commit -m "feat: 클로드 코드 프롬프트 분석 시스템"
```

```bash
cd /c/dev/weekly_project && gh repo create weekly_project --public --source=. --push
```

## 올리기 전에 확인할 것

이 저장소에는 분석 결과가 함께 들어간다. `out/` 아래 파일에는 실제 프롬프트
원문이 인용되어 있으므로 공개 전에 다음을 확인한다.

| 확인 항목 | 방법 |
| --- | --- |
| 비밀값 노출 | 리포트 말미의 마스킹 규칙 목록을 확인한다 |
| 원문 인용 | `out/report.md`의 2부 사례를 눈으로 훑는다 |
| 점수 원본 | `out/scores.json`에는 원문이 들어가지 않지만 파일이 크므로 제외를 고려한다 |

공개하지 않을 파일은 `.gitignore`에 넣는다. 기본 제공되는 `.gitignore`는
`out/scores.json`과 채점 캐시를 제외하고 있다.

## 관련 저장소

- 분석 대상 프로젝트: ReviewTicketFullstack (팀 모노레포)
