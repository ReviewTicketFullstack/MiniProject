---
name: change-drill
description: Execute a controlled change drill experiment in an isolated Git worktree with a real Claude Coding Agent
---

# Change Drill Skill

Execute a complete change drill: setup worktree → invoke Coding Agent → measure results.

## Pre-execution

Get repository path and scenario from user:

1. Ask: "Which repository should we experiment on?" (default: current directory)
2. Available scenarios:
   - `add-cancellation-reason` — Add optional field to Order domain entity
   - `rename-auth-service` — Refactor: rename a core service

## Phase 1: Setup

Run setup phase to create isolated worktree:

```bash
cd /Users/byurin/codeStress
python3 -m src.cli --repo-path <repo-path> --scenario <scenario-id> --phase setup
```

Extract from output:
- **worktree_path** — Line "Worktree ready at: /path/..."
- **base_commit** — First 7 chars from "Base commit: XXXXXXX"
- **scenario_prompt** — The scenario prompt from scenarios.json

Confirm with user: "Setup complete. Worktree ready. Invoking Coding Agent now..."

## Phase 2: Coding Agent (REAL CLAUDE AGENT)

Spawn a real Claude Coding Agent to implement the scenario:

**Agent Instructions:**

```
You are a Coding Agent for the codeStress change drill experiment.

Task: {{ scenario_prompt }}

Critical constraints:
1. Work ONLY in this directory: {{ worktree_path }}
2. Make ONLY the minimum necessary changes to complete the task
3. Do NOT modify files unrelated to the scenario
4. Run tests if present: npm test, python -m pytest, make test, etc.
5. Report completion when done, with a summary of changes made

Success means:
- Tests pass (if applicable)
- Build succeeds (if applicable)
- The requested change is complete and functional
```

Wait for the Agent to report completion.

## Phase 3: Measure & Report

Run measure phase to capture results:

```bash
cd /Users/byurin/codeStress
python3 -m src.cli --repo-path <repo-path> --scenario <scenario-id> \
  --phase measure \
  --worktree-path <worktree-path> \
  --base-commit <base-commit>
```

Show user:
- Completion status (✓ Completed or ✗ Incomplete)
- Files changed, lines added/deleted
- Verification status (Build: ✓/✗, Tests: ✓/✗)
- Links to result files

## Post-execution Safety Check

Verify original repository was not modified:

```bash
cd <repo-path>
git status
```

Should show: "nothing to commit, working tree clean"

If clean, report: "✓ Original repository remains unmodified"
