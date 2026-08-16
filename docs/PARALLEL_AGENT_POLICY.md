# Parallel Agent Execution Policy

**Last Updated:** 2026-08-16
**Version:** 1.0
**Status:** Active

---

## Policy Statement

### Agent Execution Model

codeStress supports **parallel execution of up to 3 independent Claude Coding Agents** for conducting concurrent change drill experiments on the same scenario.

### Limits

| Parameter | Value |
|-----------|-------|
| Minimum Agents | 1 (single-agent mode) |
| Default Agents | 3 (parallel mode) |
| Maximum Agents | 3 (hard limit) |
| Agents Beyond 3 | Not supported |

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
# Single-agent (default for MVP)
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 1

# Dual-agent
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 2

# Tri-agent (maximum, default for parallel mode)
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 3

# Error: Not allowed
python3 -m src.cli --repo-path <repo> --scenario <id> --parallel 4
# → Error: --parallel must be 1-3
```

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
- Cleaned up after measurement phase

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

---

## Architectural Guarantees

### Isolation

- ✅ **No Interference:** Agents cannot access other agents' worktrees
- ✅ **Independent State:** Each agent's code changes isolated in its worktree
- ✅ **Clean Original:** Original repository never modified by any agent
- ✅ **Verified Cleanup:** All worktrees cleaned after completion

### Concurrency

- ✅ **True Parallelism:** Agents run concurrently, not sequentially
- ✅ **Independent Measurement:** Each agent's results measured independently
- ✅ **No Blocking:** No agent waits for another
- ✅ **Notification-Based:** System notifies when each agent completes

### Evidence Collection

- ✅ **Per-Agent Tracking:** Separate JSON/Markdown/diff for each agent
- ✅ **Independent Verification:** Each agent's tests run independently
- ✅ **Combined Reporting:** Results merged for comparative analysis
- ✅ **Full Preservation:** No evidence lost during concurrent execution

---

## Operational Constraints

### Pre-Execution Checks

Before launching N agents:
1. Validate target repository is clean
2. Verify N ≤ 3
3. Ensure sufficient disk space (N worktrees + results)
4. Confirm scenario is well-defined

### During Execution

1. All N agents must receive identical scenario
2. Agents execute concurrently (not sequentially)
3. Each agent has exclusive worktree
4. No stopping or pausing agents mid-execution

### Post-Execution

1. All worktrees cleaned up automatically
2. Evidence preserved for each agent
3. Comparison report generated
4. Original repository verified unchanged

---

## Failure Handling

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

| Aspect | Specification |
|--------|---|
| Minimum agents | 1 |
| Default agents | 3 |
| Maximum agents | 3 |
| Execution | Concurrent (not sequential) |
| Isolation | Per-worktree (complete) |
| Original repo protection | Guaranteed |
| Failure handling | Explicit, non-hiding |
| Policy enforcement | Hard limit in CLI |

**This policy is effective immediately and applies to all parallel execution modes in codeStress.**
