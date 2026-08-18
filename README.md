# Clean Code Change Lab (codeStress)

AI-driven experimental measurement of codebase changeability through isolated change drills.

codeStress asks "is this code actually easy to change?" by having a real Claude Coding Agent
perform a controlled change in an isolated Git worktree, then measuring what the change cost.
It is **not** a code review tool and produces no quality score.

## How it works

`/change-drill` is a **prompt file**, not a single program. It directs the Claude assistant to
drive a Python harness in two phases, with the Coding Agent running in between:

```
harness --phase setup     →  creates isolated worktree, prints path + base commit
   ↓
Coding Agent (spawned by the assistant, scoped to that worktree)
   ↓
harness --phase measure   →  diff, verify, report, clean up worktree
```

**The harness does not invoke the Coding Agent.** Agent orchestration lives entirely in the
assistant following [.claude/commands/change-drill.md](.claude/commands/change-drill.md).
`--phase full` exists but does not wait for an agent, so it always measures an empty diff.

## Current status

| Capability | Status |
|---|---|
| Single-agent drill (setup → agent → measure) | 🟢 Working |
| Worktree isolation and cleanup | 🟢 Working (single-agent path) |
| Change measurement (files, lines, test files) | 🟢 Working |
| Markdown / JSON / diff reports | 🟢 Working |
| Parallel worktree creation | 🟢 Working |
| Parallel measurement and comparison | 🔴 Unreachable from CLI |
| Independent test verification | 🔴 Not implemented — see below |
| Cross-run comparison, hooks, propagation analysis | 🔴 Not implemented |

### Two limitations worth knowing up front

1. **Build and tests are not separately verified.** One detected command is run, and
   `test_success` is a copy of `build_success`. A report showing `Tests: ✓` tells you nothing
   beyond `Build: ✓`.
2. **Untracked files are invisible to measurement.** Measurement uses `git diff <base_commit>`,
   so files an agent newly creates are not counted unless staged.

## Agent model

- **Single Agent Mode:** 1 agent per experiment — this is the CLI default and the only fully
  working path
- **Parallel Mode:** up to 3 agents on the *same* scenario, for measuring implementation
  non-determinism
- **Policy maximum:** 3 agents — **not enforced in code**; `--parallel 4` is accepted today
- **Not supported:** running *different* scenarios concurrently

Each agent works in its own isolated worktree, receives the identical task, and operates
independently. In parallel mode, measurement and cleanup currently require manual per-worktree
invocation.

## Usage

```bash
# Phase 1 — create the worktree
python3 -m src.cli --repo-path /path/to/repo --scenario add-cancellation-reason --phase setup

# (Coding Agent makes changes in the printed worktree path)

# Phase 2 — measure, report, clean up
python3 -m src.cli --repo-path /path/to/repo --scenario add-cancellation-reason \
  --phase measure --worktree-path <path> --base-commit <full-sha>
```

Results are written to `results/<scenario_id>_<timestamp>.{json,md,diff}`.

## Documentation

- **Planning:** [docs/code_stress.md](docs/code_stress.md)
- **User Scenarios:** [docs/code-stress-user-scenarios.md](docs/code-stress-user-scenarios.md) —
  product spec with per-scenario implementation status
- **System Design:** [docs/system_design.md](docs/system_design.md) — architecture as implemented
- **Parallel Agent Policy:** [docs/PARALLEL_AGENT_POLICY.md](docs/PARALLEL_AGENT_POLICY.md)
- **Implementation Details:** [IMPLEMENTATION.md](IMPLEMENTATION.md)
- **Milestones:** [MILESTONE_PARALLEL_AGENTS.md](MILESTONE_PARALLEL_AGENTS.md),
  [MILESTONE_REAL_AGENT_INTEGRATION.md](MILESTONE_REAL_AGENT_INTEGRATION.md),
  [MILESTONE_RESULT_ANALYSIS.md](MILESTONE_RESULT_ANALYSIS.md)
