"""Prediction-only mode for change drill: analyze without implementing.

Agents analyze the codebase and predict implementation approach, scope, and cost
without modifying any files or creating worktrees.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional


@dataclass
class AgentPrediction:
    """Prediction from a single agent about a proposed change."""
    agent_id: str
    scenario_name: str
    timestamp: str

    # Predictions (all labeled as estimates)
    estimated_files_changed: int
    estimated_lines_added: int
    estimated_lines_deleted: int
    estimated_tokens: int

    # Qualitative analysis
    implementation_approach: str
    likely_files: List[str]
    complexity_level: str  # low / medium / high
    coupling_observations: str
    duplication_observations: str
    responsibility_observations: str
    changeability_observations: str

    # Raw analysis (for evidence)
    analysis_notes: str

    def to_json(self) -> str:
        """Serialize to JSON for evidence storage."""
        return json.dumps({
            "agent_id": self.agent_id,
            "scenario_name": self.scenario_name,
            "timestamp": self.timestamp,
            "estimated_files_changed": self.estimated_files_changed,
            "estimated_lines_added": self.estimated_lines_added,
            "estimated_lines_deleted": self.estimated_lines_deleted,
            "estimated_tokens": self.estimated_tokens,
            "implementation_approach": self.implementation_approach,
            "likely_files": self.likely_files,
            "complexity_level": self.complexity_level,
            "coupling_observations": self.coupling_observations,
            "duplication_observations": self.duplication_observations,
            "responsibility_observations": self.responsibility_observations,
            "changeability_observations": self.changeability_observations,
            "analysis_notes": self.analysis_notes,
        }, indent=2)


@dataclass
class PredictionComparison:
    """Comparison of predictions from multiple agents."""
    scenario_id: str
    scenario_name: str
    num_agents: int
    agents: Dict[str, AgentPrediction]

    # Comparison analysis
    scope_consensus: str  # Do agents agree on file count?
    approach_similarities: List[str]  # Common points in approaches
    approach_differences: List[str]  # Divergent points
    structural_observations: str  # Overall structural insights


class PredictionOrchestrator:
    """Orchestrates read-only prediction of changes across multiple agents."""

    def __init__(
        self,
        repo_path: str,
        scenario_id: str,
        scenario_name: str,
        scenario_prompt: str,
        num_agents: int = 2,
        results_dir: str = "results",
    ):
        """Initialize prediction orchestrator (no worktrees needed)."""
        self.repo_path = Path(repo_path).resolve()
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.scenario_prompt = scenario_prompt
        self.num_agents = num_agents
        self.results_dir = Path(results_dir).resolve()
        self.predictions: Dict[str, AgentPrediction] = {}

    def validate_repo(self) -> bool:
        """Verify the repository exists and is readable."""
        if not self.repo_path.exists():
            print(f"✗ Repository not found: {self.repo_path}")
            return False

        if not (self.repo_path / ".git").exists():
            print(f"✗ Not a Git repository: {self.repo_path}")
            return False

        print(f"✓ Repository validated: {self.repo_path}")
        return True

    def record_prediction(self, agent_id: str, prediction: AgentPrediction) -> None:
        """Record an agent's prediction."""
        self.predictions[agent_id] = prediction
        print(f"✓ Agent {agent_id} prediction recorded")

    def save_predictions(self) -> Dict[str, Path]:
        """Save prediction evidence to disk."""
        saved_files = {}

        from datetime import datetime
        timestamp = datetime.now().isoformat()

        for agent_id, prediction in self.predictions.items():
            results_dir = self.results_dir / f"agent_{agent_id}"
            results_dir.mkdir(parents=True, exist_ok=True)

            file_timestamp = timestamp.replace(":", "-").replace(".", "-")
            base = f"{self.scenario_id}_{file_timestamp}"

            json_path = results_dir / f"{base}_prediction.json"
            json_path.write_text(prediction.to_json())

            saved_files[agent_id] = json_path
            print(f"  Agent {agent_id}: {json_path.parent.name}/")

        return saved_files

    def analyze_predictions(self) -> PredictionComparison:
        """Build comparison from multiple agent predictions."""
        if len(self.predictions) < 2:
            # Single agent prediction
            single_pred = list(self.predictions.values())[0]
            return PredictionComparison(
                scenario_id=self.scenario_id,
                scenario_name=self.scenario_name,
                num_agents=len(self.predictions),
                agents=self.predictions,
                scope_consensus="N/A - single agent",
                approach_similarities=[single_pred.implementation_approach],
                approach_differences=[],
                structural_observations=single_pred.coupling_observations,
            )

        # Multiple agents - compare
        preds_list = list(self.predictions.values())

        # Check scope consensus
        file_counts = [p.estimated_files_changed for p in preds_list]
        min_files = min(file_counts)
        max_files = max(file_counts)

        if min_files == max_files:
            scope_consensus = f"Strong consensus: {min_files} files"
        elif max_files - min_files <= 2:
            scope_consensus = f"Modest variance: {min_files}-{max_files} files"
        else:
            scope_consensus = f"Wide variance: {min_files}-{max_files} files"

        # Extract approach similarities and differences
        approaches = [p.implementation_approach for p in preds_list]
        similarities = self._find_common_themes(approaches)
        differences = self._find_divergent_points(approaches)

        # Structural observations
        couplings = [p.coupling_observations for p in preds_list]
        structural = self._summarize_observations(couplings)

        return PredictionComparison(
            scenario_id=self.scenario_id,
            scenario_name=self.scenario_name,
            num_agents=len(self.predictions),
            agents=self.predictions,
            scope_consensus=scope_consensus,
            approach_similarities=similarities,
            approach_differences=differences,
            structural_observations=structural,
        )

    @staticmethod
    def _find_common_themes(approaches: List[str]) -> List[str]:
        """Extract common themes from agent approaches."""
        if not approaches:
            return []

        # Simple heuristic: look for common words/phrases
        common = []
        if len(set(approaches)) == 1:
            common.append("Agents agree on approach")
        elif all("API" in a for a in approaches):
            common.append("Both consider API changes")
        elif all("UI" in a for a in approaches):
            common.append("Both consider UI changes")

        return common if common else ["Multiple perspectives"]

    @staticmethod
    def _find_divergent_points(approaches: List[str]) -> List[str]:
        """Extract divergent points from agent approaches."""
        if len(set(approaches)) == 1:
            return []

        return ["Agents propose different implementation paths"]

    @staticmethod
    def _summarize_observations(observations: List[str]) -> str:
        """Summarize structural observations."""
        if not observations:
            return "No structural observations recorded"

        return " ".join(observations[:1])  # Use first observation as summary
