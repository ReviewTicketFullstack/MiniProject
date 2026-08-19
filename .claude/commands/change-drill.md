---
name: change-drill
description: Predict implementation approach and cost for a proposed change (read-only analysis)
---

# Change Drill: Prediction Mode

Predict the implementation cost and approach for a proposed change without modifying
the analysed repository.

```text
user request
  → generate temporary scenario
  → validate repository        (--predict)
  → run exactly 2 read-only prediction agents
  → wait until both prediction JSON files exist
  → exit the Claude prediction phase
  → run the Python CLI         (--predict-report)
  → the CLI renders the final terminal report
  → verify git status
```

**The Python CLI owns the final report.** Claude orchestrates the run and invokes the
report command — nothing more.

## 1. Collect input

Ask, in order:

1. "Which repository should we predict for?" — default to the current directory.
2. "What change would you like to predict? (Describe it in natural language)"

Do not offer predefined scenarios.

## 2. Build the scenario

Derive a temporary scenario from the user's request only:

```python
scenario = {
    "id": "temp-" + timestamp_or_uuid,   # also used as the evidence filename
    "name": "concise title, max 60 chars",
    "description": "summary, max 200 chars",
    "prompt": "actionable codebase analysis prompt",
}
```

Show it, ask for confirmation, and regenerate from the user's clarification if rejected.

## 3. Validate the repository

```bash
python3 -m src.cli \
  --repo-path <repo-path> \
  --scenario-json '<scenario-json>' \
  --predict \
  --parallel 2
```

This validates the repo and writes the run state. It creates no worktrees, runs no
agents, and prints no report.

## 4. Run the two prediction agents

Launch exactly 2 independent agents in parallel. Both receive the same
`scenario.prompt`. Each agent must:

- read the repository only — never create, modify, delete, or rename any file in it;
- write its prediction to `<results-dir>/agent_<A|B>/prediction_<scenario_id>.json`.

Required JSON fields (the evidence schema — unchanged):

```json
{
  "agent_id": "A",
  "scenario_name": "...",
  "timestamp": "...",
  "estimated_tokens": 0,
  "estimated_files_changed": 0,
  "estimated_lines_added": 0,
  "estimated_lines_deleted": 0,
  "complexity_level": "low | medium | high",
  "implementation_approach": "...",
  "likely_files": ["..."],
  "coupling_observations": "...",
  "duplication_observations": "...",
  "responsibility_observations": "...",
  "changeability_observations": "..."
}
```

Wait until both files exist, then end the prediction phase. Do not comment on, compare,
or summarise the predictions.

## 5. Render the report

```bash
python3 -m src.cli \
  --predict-report \
  --results-dir <results-dir> \
  --scenario-id <scenario-id> \
  --scenario-name "<scenario name>"
```

This reads the saved JSON, aggregates it, and prints the report to stdout. It runs no
agents, creates no worktrees, and touches no repository. A non-zero exit code means the
evidence is missing or malformed — report the CLI's error rather than filling the gap.

Show the CLI output as-is.

## 6. Safety check

```bash
cd <repo-path> && git status --short
```

Report immediately any change that was not present before the run.

## Rules

Claude must **not**:

- write the prediction comparison itself, in any form;
- design, restate, reformat, or "improve" the terminal report;
- add commentary, recommendations, or a summary alongside the CLI output;
- modify `src/cli.py` or `src/prediction_report.py` during a prediction run;
- create worktrees, implement the change, run builds or tests, or modify the target repo.

The JSON files are the evidence. `src/prediction_report.py` is the single source of
truth for the report layout: fixed sections, same order, every run. All numbers are
estimates from static analysis, never measurements.
