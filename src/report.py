"""Report generation from experiment evidence."""

from pathlib import Path
from typing import Optional
from .measurement import ExperimentEvidence


def generate_markdown_report(evidence: ExperimentEvidence, diff_text: str = "") -> str:
    """
    Generate a human-readable Markdown report from experiment evidence.

    Args:
        evidence: Complete experiment evidence
        diff_text: Raw unified diff (optional, for embedding)

    Returns:
        Markdown formatted report
    """
    lines = []

    lines.append(f"# Change Drill: {evidence.scenario_name}")
    lines.append("")

    lines.append("## Result")
    lines.append("")
    status = "✓ Completed" if evidence.completed else "✗ Incomplete"
    lines.append(f"**Status:** {status}")
    lines.append(f"**Timestamp:** {evidence.timestamp}")
    lines.append(f"**Base Commit:** `{evidence.base_commit[:8]}`")
    lines.append("")

    lines.append("## Change Cost")
    lines.append("")
    cost = evidence.change_cost
    lines.append(f"- Files changed: **{cost.total_files_changed}**")
    lines.append(f"- Lines added: {cost.total_lines_added}")
    lines.append(f"- Lines deleted: {cost.total_lines_deleted}")
    lines.append(f"- Test files affected: {cost.test_files_changed}")
    lines.append("")

    if cost.files_changed_list:
        lines.append("### Files Changed")
        lines.append("")
        for f in cost.files_changed_list:
            test_marker = " (test)" if f.is_test_file else ""
            lines.append(f"- `{f.path}`{test_marker}")
        lines.append("")

    lines.append("## Verification")
    lines.append("")
    verification = evidence.verification
    build_status = "✓ Passed" if verification.build_success else "✗ Failed"
    test_status = "✓ Passed" if verification.test_success else "✗ Failed"

    lines.append(f"- Build: {build_status} ({verification.build_command})")
    lines.append(f"- Tests: {test_status}")
    lines.append("")

    if not verification.build_success and verification.build_output:
        lines.append("### Build Output")
        lines.append("")
        lines.append("```")
        lines.append(verification.build_output[:500])
        if len(verification.build_output) > 500:
            lines.append("... (truncated)")
        lines.append("```")
        lines.append("")

    if evidence.notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(evidence.notes)
        lines.append("")

    if diff_text:
        lines.append("## Raw Diff")
        lines.append("")
        lines.append("```diff")
        lines.append(diff_text[:1000])
        if len(diff_text) > 1000:
            lines.append("... (truncated, see full diff in .diff file)")
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def save_experiment_results(
    evidence: ExperimentEvidence,
    diff_text: str,
    results_dir: Path,
) -> tuple[Path, Path, Path]:
    """
    Save experiment evidence to disk.

    Args:
        evidence: Experiment evidence object
        diff_text: Raw unified diff
        results_dir: Directory to save results in

    Returns:
        Tuple of (json_path, md_path, diff_path)
    """
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = evidence.timestamp.replace(":", "-").replace(".", "-")
    base = f"{evidence.scenario_id}_{timestamp}"

    json_path = results_dir / f"{base}.json"
    md_path = results_dir / f"{base}.md"
    diff_path = results_dir / f"{base}.diff"

    json_path.write_text(evidence.to_json())

    markdown = generate_markdown_report(evidence, diff_text)
    md_path.write_text(markdown)

    diff_path.write_text(diff_text)

    return json_path, md_path, diff_path
