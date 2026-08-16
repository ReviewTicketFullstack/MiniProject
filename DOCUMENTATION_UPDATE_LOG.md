# Documentation Update Log: Parallel Agent Policy

**Date:** 2026-08-16
**Policy:** Maximum 3 parallel agents (1-3 agents configurable, 3 default)
**Scope:** All documentation consistency update
**Status:** Complete

---

## Summary

Updated all project documentation to establish and clarify the parallel agent execution policy. Changed the default understanding from undefined/flexible to explicit: **1-3 agents maximum, default 3 agents, hard limit of 3 agents.**

---

## Modified Documents

### 1. `/Users/byurin/codeStress/docs/code_stress.md`
**Product/Planning Document**

**Changes:**
- Added Section 19: "병렬 Agent 정책" (Parallel Agent Policy)
- Defined agent execution model: 1-3 agents with default of 3
- Added policy rationale and design constraints
- Established that 3+ agents are not supported
- Documented guarantee of original repository protection
- Specified that agents execute concurrently and produce independent measurements

**Why:**
- Initial planning document needed explicit agent count specification
- Provides foundation for all downstream design decisions
- Clear about constraints and guarantees

---

### 2. `/Users/byurin/codeStress/docs/system_design.md`
**System Architecture Document**

**Changes:**
- Converted from bare mermaid diagram to documented architecture
- Added "Parallel Agent Model" section with architecture diagram
- Added "Agent Execution Constraints" section
- Created table specifying min/default/max agent counts
- Documented isolation guarantees (per-agent worktree, no cross-access, original repo protection, independent verification)
- Added scaling notes clarifying 1-3 agent range and why beyond 3 is not supported
- Explained rationale for 3-agent design capacity

**Why:**
- System design should explicitly specify architectural constraints
- Prevents misunderstandings about scaling capabilities
- Clarifies isolation guarantees upfront
- Documents the 3-agent limit as a design choice, not an accident

---

### 3. `/Users/byurin/codeStress/MILESTONE_PARALLEL_AGENTS.md`
**Parallel Agents Milestone Document**

**Changes:**
- Updated "Scalability" section
- Removed vague "N agents concurrently (tested with 2)" language
- Explicitly stated: minimum 1, default 3, maximum 3
- Added note that beyond 3 requires architectural redesign
- Clarified "current test" (2 agents) is within design limits

**Why:**
- Milestone document was vague about actual limits
- Readers should understand this is not infinitely scalable
- Current test (2 agents) should be clearly within the designed range

---

### 4. `/Users/byurin/codeStress/README.md`
**Project Overview

**Changes:**
- Expanded minimal README to include project context
- Added "Parallel Agent Model" section
- Documented agent configuration (1 single, up to 3 parallel, default 3)
- Explained architecture at a high level
- Added documentation index (links to all key docs)
- Specified that maximum is "never exceeds 3 agents"

**Why:**
- README is the project entry point
- Should immediately communicate the agent model constraint
- Provides reader navigation to detailed documentation

---

### 5. `/Users/byurin/codeStress/IMPLEMENTATION.md`
**MVP Implementation Report**

**Changes:**
- Updated Phase 2 reference to explicitly mention "1-3 agents concurrently"

**Why:**
- Implementation document was vague about parallel capability
- Clarifies that parallel mode is specifically 1-3 agents

---

### 6. `/Users/byurin/codeStress/docs/PARALLEL_AGENT_POLICY.md` (NEW)
**Dedicated Policy Document**

**Content:**
- Comprehensive policy definition: 1-3 agents, default 3, hard limit 3
- Core principle statement
- Detailed rationale (resource efficiency, evidence quality, system constraints)
- Implementation details (CLI usage, worktree allocation, concurrent execution)
- Architectural guarantees (isolation, concurrency, evidence collection)
- Operational constraints (pre/during/post-execution)
- Failure handling procedures
- Future considerations for exceeding 3 agents
- Policy change procedure
- Design rationale appendix

**Why:**
- Needed dedicated document for policy clarity
- Establishes this as a deliberate, documented decision
- Provides reference for future development
- Explains rationale so others can judge tradeoffs
- Documents failure handling explicitly

---

## Search Results

### References Found and Addressed

| Search Term | Found | Status |
|---|---|---|
| "5.*agent" or "five.*agent" | 0 | N/A - No conflicting references existed |
| "parallel.*agent" | Multiple (already consistent) | Reviewed, no conflicts |
| Agent count specifications | Various (now consistent) | All updated to 1-3 range |

### Verification

✅ No remaining references to "5 agents"
✅ All agent count specifications now consistent (1-3, default 3)
✅ No conflicting architecture descriptions
✅ Policy enforcement clearly documented
✅ Rationale provided in dedicated policy document

---

## Impact Analysis

### What Changed

**Before:**
- Planning doc: Vague mention of "parallel execution"
- System design: Bare diagram without constraints
- Milestones: Mention "N agents" without upper bound
- README: Minimal, no agent model explanation

**After:**
- Planning doc: Explicit 1-3 agent policy in Korean
- System design: Detailed architecture with constraints table
- Milestones: Clear 1-3 agent specification
- README: Project overview includes agent model
- New: Dedicated 2400-word policy document

### What Did NOT Change

❌ Implementation code (not modified)
❌ Python harness (not modified)
❌ Claude Skill definitions (not modified)
❌ Existing test results (not modified)
❌ Architecture principles (clarified, not changed)

---

## Consistency Verification

**Cross-document consistency check:**

| Document | Agent Min | Agent Default | Agent Max |
|---|---|---|---|
| code_stress.md | 1 | 3 | 3 |
| system_design.md | 1 | 3 | 3 |
| PARALLEL_AGENTS.md | 1 | 3 | 3 |
| README.md | 1 | 3 | 3 |
| PARALLEL_AGENT_POLICY.md | 1 | 3 | 3 |
| IMPLEMENTATION.md | (implicit 1-3) | - | 3 |

✅ **All documents consistent**

---

## Next Steps (If Needed)

### To Enforce This Policy in Code

The CLI should validate:
```python
if args.parallel < 1 or args.parallel > 3:
    raise ValueError("--parallel must be 1-3 (current policy limits maximum to 3 agents)")
```

(This is already suggested as an enhancement in PARALLEL_AGENT_POLICY.md)

### To Modify Policy Future

If requirements change (e.g., need for 5 agents):

1. Update all 6 documents to reflect new limit
2. Document rationale for change in PARALLEL_AGENT_POLICY.md
3. Increment version number in policy document
4. Verify implementation code supports new limit
5. Test at new scale before deployment

---

## Sign-Off

**Documentation Update:** Complete
**Consistency:** Verified across all 6 modified/created documents
**Remaining Conflicts:** None found
**Implementation Code:** Not changed (as requested)
**Policy Enforcement:** Documented (implementation optional)

All project documentation now establishes a consistent, documented policy:

> **codeStress supports parallel execution of 1-3 Claude Coding Agents, with 3 agents as the default for parallel mode. No more than 3 agents may execute concurrently in a single change drill experiment.**
