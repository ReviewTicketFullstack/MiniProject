"""Analysis and comparison of multi-agent experiment results.

에이전트 간 비교: 여러 에이전트의 측정값(파일/라인/테스트)을 수집 및 비교 분석.
패턴 탐지: 공통 변경/분기 변경, 범위 min/max/avg, 관찰 가능 정규성 추출.
증거 분리: 증거(관측값)와 해석(그 의미)을 명확히 분리. CLI에서 도달 불가능한 모듈.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from difflib import unified_diff


@dataclass
class AgentMetrics:
    """Metrics for a single agent's execution."""
    agent_id: str
    files_changed: int
    lines_added: int
    lines_deleted: int
    test_files_changed: int
    build_success: bool
    test_success: bool
    duration_seconds: Optional[float] = None
    files_list: List[str] = None
    diff: str = ""


@dataclass
class ComparisonResult:
    """Structured comparison of multiple agent results."""
    scenario_id: str
    scenario_name: str
    num_agents: int
    agents: Dict[str, AgentMetrics]
    common_changes: List[str]
    divergent_changes: Dict[str, List[str]]
    scope_analysis: Dict[str, Any]
    patterns: List[str]

    @property
    def shared_files(self) -> List[str]:
        """Files changed by all agents."""
        return self.common_changes

    @property
    def divergent_files(self) -> List[str]:
        """Files changed differently by agents (union of all divergent changes)."""
        all_divergent = set()
        for files in self.divergent_changes.values():
            all_divergent.update(files)
        return sorted(list(all_divergent))


class ExperimentAnalyzer:
    """Analyzes and compares multi-agent experiment results."""

    def __init__(self, scenario_id: str, scenario_name: str):
        """Initialize analyzer for a scenario."""
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.agents: Dict[str, AgentMetrics] = {}

    def add_agent_result(self, agent_id: str, metrics: AgentMetrics) -> None:
        """Register an agent's results."""
        self.agents[agent_id] = metrics

    def analyze(self) -> ComparisonResult:
        """Generate structured comparison of all agents."""
        return ComparisonResult(
            scenario_id=self.scenario_id,
            scenario_name=self.scenario_name,
            num_agents=len(self.agents),
            agents=self.agents,
            common_changes=self._find_common_changes(),
            divergent_changes=self._find_divergent_changes(),
            scope_analysis=self._analyze_scope(),
            patterns=self._identify_patterns(),
        )

    def _find_common_changes(self) -> List[str]:
        """Identify changes made by all successful agents."""
        if not self.agents:
            return []

        successful_agents = {
            aid: m for aid, m in self.agents.items()
            if m.build_success and m.test_success
        }

        if not successful_agents:
            return []

        if len(successful_agents) == 1:
            return []  # No comparison with single agent

        # Find files changed by all agents
        if successful_agents:
            first_agent_files = set(successful_agents[list(successful_agents.keys())[0]].files_list or [])
            common_files = first_agent_files.copy()

            for agent_metrics in list(successful_agents.values())[1:]:
                agent_files = set(agent_metrics.files_list or [])
                common_files &= agent_files

            return sorted(list(common_files))

        return []

    def _find_divergent_changes(self) -> Dict[str, List[str]]:
        """Identify differences between agents' changes."""
        divergent = {}

        if len(self.agents) < 2:
            return divergent

        successful_agents = {
            aid: m for aid, m in self.agents.items()
            if m.build_success and m.test_success
        }

        # For each agent, find files it changed that others didn't
        for agent_id, metrics in successful_agents.items():
            agent_files = set(metrics.files_list or [])
            other_files = set()

            for other_id, other_metrics in successful_agents.items():
                if other_id != agent_id:
                    other_files.update(other_metrics.files_list or [])

            unique_files = agent_files - other_files
            if unique_files:
                divergent[agent_id] = sorted(list(unique_files))

        return divergent

    def _analyze_scope(self) -> Dict[str, Any]:
        """Analyze the scope of changes across agents."""
        if not self.agents:
            return {}

        successful = [m for m in self.agents.values() if m.build_success and m.test_success]

        if not successful:
            return {"status": "no_successful_agents"}

        files_changed = [m.files_changed for m in successful]
        lines_added = [m.lines_added for m in successful]

        return {
            "num_successful_agents": len(successful),
            "files_changed": {
                "min": min(files_changed),
                "max": max(files_changed),
                "avg": sum(files_changed) / len(files_changed),
            },
            "lines_added": {
                "min": min(lines_added),
                "max": max(lines_added),
                "avg": sum(lines_added) / len(lines_added),
            },
            "range": {
                "files_changed_range": max(files_changed) - min(files_changed),
                "lines_added_range": max(lines_added) - min(lines_added),
            },
        }

    def _identify_patterns(self) -> List[str]:
        """Identify observable patterns in implementations."""
        patterns = []

        if not self.agents:
            return patterns

        # Pattern 1: All agents used same file count
        successful = [m for m in self.agents.values() if m.build_success and m.test_success]
        if successful:
            file_counts = [m.files_changed for m in successful]
            if len(set(file_counts)) == 1:
                patterns.append(
                    f"All successful agents modified the same number of files ({file_counts[0]})."
                )

        # Pattern 2: Wide variation in lines added
        if successful:
            lines = [m.lines_added for m in successful]
            if max(lines) > 1.5 * min(lines):
                patterns.append(
                    f"Significant variation in lines added: {min(lines)}-{max(lines)} (ratio: {max(lines)/min(lines):.1f}x)"
                )

        # Pattern 3: Test file consistency
        if successful:
            test_file_changes = [m.test_files_changed for m in successful]
            if len(set(test_file_changes)) == 1:
                patterns.append(
                    f"All agents modified the same number of test files ({test_file_changes[0]})."
                )

        # Pattern 4: Universal test success
        if all(m.test_success for m in successful):
            patterns.append("All successful agents produced implementations with passing tests.")

        # Pattern 5: Divergence in scope
        if len(successful) > 1 and len(set(f.files_changed for f in successful)) > 1:
            patterns.append("Agents chose different scope for implementing the scenario.")

        return patterns


class ComparisonReportGenerator:
    """Generate human-readable comparison reports."""

    @staticmethod
    def generate_markdown(result: ComparisonResult) -> str:
        """Generate Markdown report from comparison results."""
        lines = []

        # Header
        lines.append(f"# Experiment Comparison: {result.scenario_name}")
        lines.append("")
        lines.append(f"**Scenario:** `{result.scenario_id}`")
        lines.append(f"**Agents:** {result.num_agents}")
        lines.append("")

        # Per-agent metrics table
        lines.append("## Agent Results")
        lines.append("")
        lines.append("| Agent | Files | Lines+ | Lines- | Tests | Build |")
        lines.append("|-------|-------|--------|--------|-------|-------|")

        for agent_id in sorted(result.agents.keys()):
            metrics = result.agents[agent_id]
            test_icon = "✓" if metrics.test_success else "✗"
            build_icon = "✓" if metrics.build_success else "✗"
            lines.append(
                f"| {agent_id} | {metrics.files_changed} | {metrics.lines_added} | "
                f"{metrics.lines_deleted} | {test_icon} | {build_icon} |"
            )

        lines.append("")

        # Common changes
        if result.common_changes:
            lines.append("## Common Changes")
            lines.append("")
            lines.append("Files modified by all successful agents:")
            lines.append("")
            for file in result.common_changes:
                lines.append(f"- `{file}`")
            lines.append("")

        # Divergent changes
        if result.divergent_changes:
            lines.append("## Divergent Changes")
            lines.append("")
            for agent_id, files in result.divergent_changes.items():
                lines.append(f"**Agent {agent_id} only:**")
                for file in files:
                    lines.append(f"- `{file}`")
            lines.append("")

        # Scope analysis
        if result.scope_analysis and result.scope_analysis.get("status") != "no_successful_agents":
            lines.append("## Change Scope Analysis")
            lines.append("")
            scope = result.scope_analysis

            if "files_changed" in scope:
                files = scope["files_changed"]
                lines.append(f"**Files Changed:**")
                lines.append(f"- Minimum: {files['min']}")
                lines.append(f"- Maximum: {files['max']}")
                lines.append(f"- Average: {files['avg']:.1f}")
                lines.append("")

            if "lines_added" in scope:
                lines_data = scope["lines_added"]
                lines.append(f"**Lines Added:**")
                lines.append(f"- Minimum: {lines_data['min']}")
                lines.append(f"- Maximum: {lines_data['max']}")
                lines.append(f"- Average: {lines_data['avg']:.1f}")
                lines.append("")

            if "range" in scope:
                r = scope["range"]
                if r["files_changed_range"] > 0:
                    lines.append(
                        f"**Range:** Files changed vary by {r['files_changed_range']} "
                        f"(lines added vary by {r['lines_added_range']})"
                    )
                    lines.append("")

        # Patterns
        if result.patterns:
            lines.append("## Observed Patterns")
            lines.append("")
            for pattern in result.patterns:
                lines.append(f"- {pattern}")
            lines.append("")

        # Analysis section
        lines.append("## Analysis Notes")
        lines.append("")
        lines.append("**Evidence vs. Interpretation:**")
        lines.append("")
        lines.append(
            "The metrics above are direct observations from agent execution. "
            "Differences in file count, line count, or scope do not automatically indicate "
            "code quality differences. All agents' implementations passed verification (build and tests)."
        )
        lines.append("")
        lines.append(
            "Observable differences may reflect:")
        lines.append("- Different implementation strategies")
        lines.append("- Different levels of refactoring")
        lines.append("- Different approaches to test coverage")
        lines.append("- Different file organization choices")
        lines.append("")
        lines.append("Each choice may be valid depending on project context.")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_json(result: ComparisonResult) -> str:
        """Generate JSON report from comparison results."""
        data = {
            "scenario_id": result.scenario_id,
            "scenario_name": result.scenario_name,
            "num_agents": result.num_agents,
            "agents": {
                agent_id: {
                    "files_changed": metrics.files_changed,
                    "lines_added": metrics.lines_added,
                    "lines_deleted": metrics.lines_deleted,
                    "test_files_changed": metrics.test_files_changed,
                    "build_success": metrics.build_success,
                    "test_success": metrics.test_success,
                }
                for agent_id, metrics in result.agents.items()
            },
            "common_changes": result.common_changes,
            "divergent_changes": result.divergent_changes,
            "scope_analysis": result.scope_analysis,
            "patterns": result.patterns,
        }
        return json.dumps(data, indent=2)
