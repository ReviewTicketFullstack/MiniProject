# Parallel Agent Execution Policy

**Last Updated:** 2026-08-16
**Version:** 1.1
**Status:** Active (policy) / Partially implemented (enforcement)

---

## ⚠️ Implementation Status

This document states **policy**. Much of it is not yet enforced or reachable in code. Read this
table before relying on any guarantee below.

| Policy item | Implemented? |
|---|---|
| Create 1–3 isolated worktrees | ✅ Yes |
| CLI default agent count | ⚠️ Defaults to **1**, not 3 |
| Hard limit of 3 agents | ❌ **Not enforced** — no range validation on `--parallel` |
| Concurrent agent execution | ⚠️ Performed by the assistant, not the harness |
| Per-agent measurement | ❌ Unreachable from the CLI |
| Comparison report generation | ❌ Unreachable from the CLI |
| Automatic worktree cleanup (parallel) | ❌ Does not occur |
| Pre-execution checks | ❌ None implemented |
| Per-agent failure isolation | ❌ Not implemented |

**Root cause for the unreachable items:** `--phase measure --parallel N` constructs a fresh
`ParallelDrill` whose worktree map is empty, then calls `measure_all()`, which guards on exactly
that condition. It always exits with:

```
Error: Harness not properly initialized. Call setup_worktrees() first.
```

No state is persisted between the setup process and the measure process.

---

## Policy Statement

### Agent Execution Model

codeStress supports **parallel execution of up to 3 independent Claude Coding Agents** for conducting concurrent change drill experiments on the same scenario.

### Limits

| Parameter | Value | Enforced in code? |
|-----------|-------|---|
| Minimum Agents | 1 (single-agent mode) | — |
| CLI Default | 1 | ✅ `--parallel` defaults to `1` |
| Recommended for parallel mode | 3 | ❌ Convention only |
| Maximum Agents | 3 (policy limit) | ❌ **Not enforced** |
| Agents Beyond 3 | Not supported | ❌ Accepted by the CLI anyway |

### Core Principle

**No more than 3 agents may execute concurrently in a single change drill experiment.**

---

## Why This Limit?

### Resource Efficiency

- **Concurrent Execution:** 3 agents running simultaneously maintain wall-clock time efficiency
- **Worktree Overhead:** Each agent requires an isolated Git worktree; 3 is a reasonable balance
- **Verification Load:** Sequential verification after agent completion remains manageable

### Evidence Quality

- **Biased Sampling Avoidance:** 3 independent runs capture implementation variation
- **Statistical Sufficiency:** Enough diversity to observe natural implementation choices
- **Not Exhaustive:** Beyond 3, diminishing returns without corresponding benefit

### System Constraints

- **Claude Code Runtime:** Tested stable with 2 agents; designed for up to 3
- **Resource Consumption:** Parallel I/O, file system load reasonable with 3 agents
- **Isolation Complexity:** Worktree management scales reliably to 3; beyond requires different architecture

---

## Implementation Details

### User Configuration

```bash
# Single-agent (CLI default — --parallel may be omitted)
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 1

# Dual-agent
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 2

# Tri-agent (policy maximum)
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 3

# Violates policy, but IS NOT REJECTED by the CLI today.
# No range validation exists; this creates 4 worktrees.
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 4
```

To make the limit real, the CLI would need a guard such as:

```python
if not 1 <= args.parallel <= 3:
    raise ValueError("--parallel must be 1-3")
```

This guard is **not present** in `src/cli.py`.

### Worktree Allocation

```
Worktree A ← Agent A
Worktree B ← Agent B
Worktree C ← Agent C
(Worktrees D+ not created)
```

Each worktree:
- Isolated Git repository state
- Independent filesystem
- No cross-access between agents
- ❌ **Not** cleaned up in parallel mode — the measurement phase that performs cleanup is
  unreachable, so worktrees persist under `<repo>/.git/worktrees/` and must be removed manually:
  ```bash
  git worktree remove --force <path>
  ```

### Concurrent Execution

```
T=0s:   Launch Agent A (background)
T+0.1s: Launch Agent B (background)
T+0.2s: Launch Agent C (background)
        All three execute concurrently
T+~60s: Agent A completes (notification)
T+~61s: Agent B completes (notification)
T+~62s: Agent C completes (notification)
        → Proceed to measurement phase
```

All agents start at nearly identical times; no artificial sequencing.

**Important:** this launch sequence is executed by the **Claude assistant** following the
`/change-drill` prompt, not by the harness. The harness creates worktrees and returns; it has no
knowledge of, control over, or record of any agent. Concurrency is therefore an orchestration
property of the prompt, not a guarantee the harness can enforce.

---

## Architectural Guarantees

### Isolation

- ✅ **No Interference:** Each agent gets a separate worktree directory
- ✅ **Independent State:** Each agent's code changes isolated in its worktree
- ✅ **Clean Original:** Original repository never modified (detached checkouts)
- ❌ **Verified Cleanup:** Not performed in parallel mode — see Worktree Allocation above

Note: scoping an agent to its worktree relies on the agent honoring the path constraint given in
its prompt. There is no filesystem-level sandbox preventing an agent from writing elsewhere.

### Concurrency

- ⚠️ **True Parallelism:** Depends on the assistant backgrounding each agent; not harness-enforced
- ❌ **Independent Measurement:** Parallel measurement is unreachable from the CLI
- ✅ **No Blocking:** No agent waits for another
- ⚠️ **Notification-Based:** Completion notification is a property of the assistant's task runner

### Evidence Collection

- ❌ **Per-Agent Tracking:** `results/agent_<ID>/` is never written — the code path is unreachable
- ❌ **Independent Verification:** Not reached in parallel mode. Even in single-agent mode, tests
  are not verified independently of the build (`test_success` mirrors `build_success`)
- ❌ **Combined Reporting:** `results/comparison/` is never written
- ⚠️ **Full Preservation:** Evidence must currently be collected by invoking single-agent
  `--phase measure` manually, once per worktree

---

## Operational Constraints

### Pre-Execution Checks

> **Status: none of these are implemented.** The only validation performed is that the target path
> exists and contains a `.git` entry (`Worktree.validate_repo()`). The checks below are the
> intended policy and must currently be performed by the operator.

Before launching N agents:
1. Validate target repository is clean — ❌ not checked; a dirty working tree makes the base
   commit ambiguous but does not stop execution
2. Verify N ≤ 3 — ❌ not checked
3. Ensure sufficient disk space (N worktrees + results) — ❌ not checked
4. Confirm scenario is well-defined — ❌ not checked

### During Execution

1. All N agents must receive identical scenario
2. Agents execute concurrently (not sequentially)
3. Each agent has exclusive worktree
4. No stopping or pausing agents mid-execution

### Post-Execution

> **Status: items 1–3 do not occur in parallel mode.**

1. All worktrees cleaned up automatically — ❌ manual cleanup required
2. Evidence preserved for each agent — ⚠️ requires manual per-worktree measure invocations
3. Comparison report generated — ❌ code path unreachable
4. Original repository verified unchanged — ✅ verifiable via `git status` in the target repo

---

## Failure Handling

> **Status: not implemented.** The section below describes intended behavior.
> Today, `measure_all()` wraps all agents in a single `try` block and returns one error for the
> whole run if any agent's measurement raises. There is no per-agent failure isolation and no
> partial comparison report.

### Single Agent Failure

If 1 of 3 agents fails:
- Continue with other agents' results
- Record failure explicitly
- Preserve evidence from successful agents
- Generate partial comparison report

**Example:**
```
Agent A: Completed (3 files, 35 lines)
Agent B: Completed (3 files, 36 lines)
Agent C: Failed (build error) → Evidence preserved
Result: Report with A and B, notation of C failure
```

### Multiple Agent Failure

If 2+ agents fail:
- Preserve evidence from any successful agents
- Record all failures explicitly
- Do not stop the experiment
- Generate report with available evidence

### No Partial Success Hiding

Never convert failed results to "passed". Always:
- Record actual status (completed/failed)
- Preserve error messages
- Include in final report with explicit notation

---

## Future Considerations

### Exceeding 3 Agents

If future requirements demand more than 3 concurrent agents:

**Required Changes:**
1. Redesign worktree management
2. Assess Claude Code runtime capacity
3. Verify resource consumption remains acceptable
4. Document new constraints and guarantees
5. Test isolation at new scale

**Not Recommended Without Evidence**
- No current requirement for 4+ agents
- Architecture untested beyond 3
- Requires deliberate design decisions

---

## Policy Change Procedure

To modify this policy:

1. **Document Rationale:** Why is the change necessary?
2. **Test Thoroughly:** Verify at new scale (if increasing)
3. **Update All Documentation:** Reflect new limits everywhere
4. **Version This Document:** Increment version number
5. **Announce Change:** Notify team of new constraints

---

## Appendix: Design Rationale

### Why Not More Agents?

**5 Agents (Example)**
- Worktree management complexity increases quadratically
- Concurrent verification load on target repository (if applicable)
- Results harder to interpret (too much variance)
- Diminishing return on evidence quality vs. resource cost

**Why 3 Specifically?**
- Small prime number (good for statistical sampling)
- Tested and working (2 verified, 3 designed)
- Provides diversity without excess
- Reasonable resource consumption
- Scalable in future if needed

### Why Not 1?

Single-agent mode (1 agent) still supported because:
- Some experiments require sequential runs
- Lower resource overhead
- Simpler orchestration
- Some scenarios may need repeated single runs

---

## Summary

| Aspect | Specification | Implemented |
|--------|---|---|
| Minimum agents | 1 | ✅ |
| CLI default agents | 1 | ✅ |
| Recommended parallel count | 3 | ❌ convention only |
| Maximum agents | 3 | ❌ not enforced |
| Execution | Concurrent (not sequential) | ⚠️ assistant-driven |
| Isolation | Per-worktree | ✅ |
| Original repo protection | Guaranteed | ✅ |
| Failure handling | Explicit, non-hiding | ❌ |
| Policy enforcement | Hard limit in CLI | ❌ **no validation exists** |

**This policy states intent. Where the "Implemented" column shows ❌, the policy is currently
maintained by operator discipline rather than by code.**

## Gap Closure Backlog

To bring the implementation in line with this policy:

1. Add `1 <= --parallel <= 3` validation to `src/cli.py`
2. Persist `ParallelDrill` state (worktree paths + base commit) between the setup and measure
   processes so `measure_all()` becomes reachable
3. Wrap per-agent measurement in individual `try` blocks for failure isolation
4. Add a clean-working-tree precondition check
5. Ensure worktree cleanup runs even when measurement is never invoked
