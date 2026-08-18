---
name: change-drill
description: Execute a controlled change drill experiment in an isolated Git worktree with a real Claude Coding Agent
---

# Change Drill Skill

Execute a complete change drill: setup worktree → invoke Coding Agent → measure results.

**Scope: single agent only.** This command orchestrates one Coding Agent. Parallel mode
(`--parallel N`) creates N worktrees but its measurement and comparison phases are not reachable
from the CLI, so do not use it here. See `docs/PARALLEL_AGENT_POLICY.md`.

**Do not use `--phase full`.** It does not wait for the agent — it measures immediately after
creating the worktree and will always report an empty diff. Always use the two-phase flow below.

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
- **base_commit** — Line "Base commit: XXXXXXXX". This is a **truncated display value (8 chars)**.
  Obtain the **full SHA** for the measure phase by running `git rev-parse HEAD` in the target
  repository, since setup bases the worktree on `HEAD`. Do not pass the truncated value.
- **scenario_prompt** — Read the `prompt` field for this scenario ID from `src/scenarios.json`.
  The CLI does not emit it in single-agent mode.

Note: the setup phase performs **no confirmation prompt and no clean-working-tree check**. Before
running it, verify the target repo is clean yourself (`git status`), because a dirty tree makes
the base commit ambiguous.

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

Notes on what the harness does and does not capture:
- Whatever the agent runs in constraint 4 is **not recorded**. The measure phase re-runs its own
  single detected command and records only that result.
- Measurement uses `git diff <base_commit>`, which **excludes untracked files**. If the agent
  creates new files, instruct it to `git add` them, or they will not be counted.

## Phase 3: Measure & Report

Run measure phase to capture results:

```bash
cd /Users/byurin/codeStress
python3 -m src.cli --repo-path <repo-path> --scenario <scenario-id> \
  --phase measure \
  --worktree-path <worktree-path> \
  --base-commit <base-commit>
```

Pass the **full** base commit SHA to `--base-commit`.

Show user:
- Completion status (✓ Completed or ✗ Incomplete)
- Files changed, lines added (note: the CLI does not print lines deleted; read it from the JSON)
- Verification status (Build: ✓/✗, Tests: ✓/✗)
- Links to result files

**When reporting verification, state the caveat.** `Tests: ✓` is not an independent test result —
the harness runs one detected command and copies its outcome to both fields. Report it as
"verification command passed", not as "build and tests both passed".

Similarly, "Completed" means the verification command exited 0. It does **not** mean the requested
change was actually implemented. Confirm that separately by reading the diff.

## Post-execution Safety Check

Verify original repository was not modified:

```bash
cd <repo-path>
git status
```

Should show: "nothing to commit, working tree clean"

If clean, report: "✓ Original repository remains unmodified"

Also confirm no worktree leaked. The measure phase removes it, but if measurement was skipped or
failed, it persists:

```bash
cd <repo-path>
git worktree list
```

Any remaining `drill-*` entry should be removed with `git worktree remove --force <path>`.
