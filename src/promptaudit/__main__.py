"""명령줄 진입점.

아무 옵션 없이 실행하면 컴퓨터에 남아 있는 대화 기록을 먼저 전부 훑어, 분석할
수 있는 대상을 목록으로 보여 주고 무엇을 분석할지 물어본다. 다른 사람이 이
프로그램을 받아 써도 자기 프로젝트를 바로 고를 수 있게 하기 위해서다.

  python -m promptaudit                     대상을 물어본 뒤 분석한다
  python -m promptaudit --project mycloset  물어보지 않고 바로 분석한다
  python -m promptaudit --list              어떤 기록이 있는지만 보여 준다
  python -m promptaudit --html D:/보고서    최종 리포트 html을 그 자리에 만든다
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import charts, discover, pipeline, report, rubric
from .selector import PROJECTS, filter_from_candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promptaudit",
        description="클로드 코드 대화 기록으로 프롬프트를 평가한다",
    )
    parser.add_argument("--project", default=None,
                        help="분석할 대상 이름. 생략하면 목록에서 고르게 한다")
    parser.add_argument("--list", action="store_true",
                        help="분석할 수 있는 대상만 보여 주고 끝낸다")
    parser.add_argument("--out", default="out", type=Path)
    parser.add_argument("--html", default=None, type=Path,
                        help="최종 리포트 html을 따로 둘 자리. 폴더를 주면 그 안에 report.html 로 만든다")
    parser.add_argument("--projects-dir", default=None, type=Path,
                        help="대화 기록 폴더. 기본은 사용자 홈의 .claude/projects")
    parser.add_argument("--sample", default=180, type=int, help="채점 표본 크기")
    parser.add_argument("--no-llm", action="store_true",
                        help="채점 결과를 반영하지 않고 규칙 지표만으로 리포트를 만든다")
    parser.add_argument("--queue-only", action="store_true",
                        help="채점 대기열만 만들고 리포트는 만들지 않는다")
    return parser


def deliver_html(source: Path, target: Path) -> Path:
    """다 만든 리포트 html을 사용자가 지정한 자리에 만들어 준다.

    그림이 html 안에 통째로 박혀 있어 파일 하나만 있으면 어디서든 그대로 열린다.
    폴더를 주면 그 안에 report.html 이라는 이름으로 만들고, 파일 이름까지 주면
    그 이름을 그대로 쓴다.
    """
    destination = Path(str(target)).expanduser()
    if destination.suffix.lower() not in (".html", ".htm"):
        destination = destination / "report.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def pick_target(args):
    """무엇을 분석할지 정한다. 필요하면 사용자에게 물어본다."""
    print("대화 기록을 훑는 중입니다. 기록이 많으면 조금 걸립니다.")
    candidates = discover.merge_similar(discover.scan(args.projects_dir))
    if not candidates:
        print("분석할 만한 대화 기록을 찾지 못했습니다.", file=sys.stderr)
        return None

    if args.list:
        print(discover.format_table(candidates))
        return None

    if args.project:
        key = args.project.lower()
        if key in PROJECTS:
            return key
        for candidate in candidates:
            if key in (candidate.label.lower(), candidate.key):
                return filter_from_candidate(candidate)
        for candidate in candidates:
            if key in candidate.label.lower():
                return filter_from_candidate(candidate)
        print("'" + args.project + "'와 맞는 대상을 찾지 못했습니다. 아래에서 골라 주세요.")

    chosen = discover.choose(candidates)
    if chosen is None:
        print("선택이 취소되었습니다.")
        return None
    print("'" + chosen.label + "'을 분석하겠습니다.")
    return filter_from_candidate(chosen)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    target = pick_target(args)
    if target is None:
        return 0 if args.list else 1

    print()
    print("[1/4] 대상 세션을 고르고 지표를 계산합니다.")
    analysis = pipeline.run(target, args.projects_dir)
    if not analysis.rows:
        print("고른 대상에서 사람이 입력한 프롬프트를 찾지 못했습니다.", file=sys.stderr)
        return 1
    print("      세션 " + str(analysis.session_count) + "개에서 프롬프트 " +
          format(analysis.prompt_count, ",") + "개를 찾았습니다.")

    cache_path = out_dir / "judge_cache.json"
    results_path = out_dir / "judge_results.json"
    queue_path = out_dir / "judge_queue.json"

    print("[2/4] 자세히 채점할 표본을 고릅니다.")
    sample = rubric.select_sample(analysis, size=args.sample)
    cache = rubric.load_results(cache_path)
    fresh = rubric.load_results(results_path)
    if fresh:
        cache = rubric.merge_cache(cache_path, fresh)
    todo = rubric.pending(sample, cache)
    if todo:
        rubric.write_queue(todo, queue_path)
        print("      아직 채점하지 않은 " + str(len(todo)) + "개를 " +
              str(queue_path) + " 에 적어 두었습니다.")
    else:
        print("      새로 채점할 프롬프트가 없습니다.")

    if args.queue_only:
        return 0

    # 표본이 바뀌어도 이미 채점해 둔 것은 모두 살려 쓴다.
    known = {rubric.prompt_key(row.prompt.text) for row in analysis.rows}
    judged = None if args.no_llm else {k: v for k, v in cache.items() if k in known}
    if judged:
        print("      이미 채점된 " + str(len(judged)) + "개를 리포트에 반영합니다.")

    print("[3/4] 그림을 그립니다.")
    chart_files = charts.build_all(analysis, out_dir / "charts", judged)

    print("[4/4] 리포트를 씁니다.")
    paths = report.write_all(analysis, chart_files, out_dir, judged)
    if args.html is not None:
        paths["html"] = deliver_html(paths["html"], args.html)
    print()
    print("다 끝났습니다. 아래 파일을 열어 보시면 됩니다.")
    for name, path in paths.items():
        print("      " + name + ": " + str(path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
