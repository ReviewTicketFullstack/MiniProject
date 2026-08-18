---
name: change-drill
description: Execute a controlled parallel change drill experiment with natural-language input
---

# Change Drill Skill

Execute a complete change drill with natural-language input: natural language → temporary scenario → 2-agent parallel experiment → measurement → analysis → report.

**This skill now uses 2-agent parallel execution.** Natural language input is interpreted and structured into a temporary Scenario, then passed to the existing parallel infrastructure.

## Pre-execution

Get repository path and change description from user:

1. Ask: "Which repository should we experiment on?" (default: current directory)
2. Ask: "What change would you like to test? (Describe in natural language)"

Example user response:
```
"Add order cancellation to the order history. Only paid orders should be cancellable. 
Add a cancel button to each order, validate payment status, and update the order state."
```

## Claude: Generate Temporary Scenario

Parse the user's natural language request and generate a structured temporary Scenario dict **in memory**:

```python
scenario = {
    "id": "temp-" + (epoch timestamp or random UUID),
    "name": (short title from user request, max 60 chars),
    "description": (user's request summarized, max 200 chars),
    "objective": (what the change accomplishes, max 150 chars),
    "prompt": (detailed implementation prompt derived from user request)
}
```

**The prompt should be actionable and specific.** Example:
```
"The Order entity needs cancellation support. Implement:
1. Add a 'cancelReason' optional field to the Order model
2. Add a 'cancel()' method that validates order state (only 'paid' orders are cancellable)
3. Expose cancellation through the API (POST /orders/{id}/cancel)
4. Display a cancel button in the order history UI (only for cancellable orders)
5. Update and run tests

Follow existing patterns for similar operations. Keep changes minimal and focused."
```

## Show Generated Scenario to User

Display the generated Scenario for verification:

```
GENERATED SCENARIO
==================
ID:          temp-1726234567890
Name:        Order Cancellation
Description: Add cancellation support to the order history page
Objective:   Implement order cancellation with payment state validation
Prompt:      [full prompt as above]

Does this match your intent? (yes/no)
```

Wait for user confirmation. If "no", offer to regenerate with clarification.

## Phase 1: Setup (2 Agents)

Once confirmed, run setup phase to create isolated worktrees for 2 agents:

```bash
cd /Users/byurin/codeStress
python3 -m src.cli --repo-path <repo-path> \
  --scenario-json '<scenario-json>' \
  --parallel 2 \
  --phase setup
```

Extract from output:
- **base_commit** — Line "Base commit: XXXXXXXX..." (use full SHA for measure phase)
- **agents** — Map of agent IDs to worktree paths. Output includes:
  ```
  Agent A: /path/to/worktree-0
  Agent B: /path/to/worktree-1
  ```

Confirm with user: "Setup complete. 2 isolated worktrees created. Invoking Coding Agents now..."

## Phase 2: Coding Agents (REAL CLAUDE AGENTS)

Spawn **exactly 2** independent Claude Coding Agents in parallel. Each agent receives:

**Agent Instructions (identical for both A and B):**

```
You are a Coding Agent for the codeStress change drill experiment.

Task: {{ scenario.prompt }}

Critical constraints:
1. Work ONLY in this directory: {{ agent_worktree_path }}
2. Make ONLY the minimum necessary changes to complete the task
3. Do NOT modify files unrelated to the requested change
4. Run tests if present: npm test, python -m pytest, make test, etc.
5. Report completion when done, with a summary of changes made

Success means:
- Tests pass (if applicable)
- Build succeeds (if applicable)
- The requested change is complete and functional
```

**Key points:**
- Both agents receive the SAME scenario and instructions
- Each works in its own isolated worktree
- They run in parallel (not sequentially)
- Do NOT wait for either agent to complete before moving to measurement

Wait for both agents to report completion. The measurement phase will analyze their independent implementations.

**Note on verification:** Whatever agents run in constraint 4 is not recorded. The measure phase re-runs its own detected build/test command and records only that result. If new files are created, instruct agents to `git add` them, or they will not be counted.

## Phase 3: Measure & Report (All 2 Agents)

Run measure phase to capture and compare results from both agents:

```bash
cd /Users/byurin/codeStress
python3 -m src.cli --repo-path <repo-path> \
  --scenario-json '<scenario-json>' \
  --parallel 2 \
  --phase measure \
  --worktree-path <agent_A_worktree> \
  --base-commit <base-commit>
```

**Note:** For parallel mode, pass the first agent's worktree path; the CLI discovers the others.

Show user:
- **For each agent (A, B):**
  - Completion status (✓ Completed or ✗ Incomplete)
  - Files changed, lines added/deleted
  - Verification status (Build: ✓/✗, Tests: ✓/✗)
  - Code diff (preview or link)

- **Comparison analysis:**
  - Files changed: which files did each agent modify? (overlap, divergence)
  - Diff size: which agent's solution was larger/smaller?
  - Verification: did both pass tests? Did one fail?
  - Code quality: any obvious differences in approach?

- **Links to result files:**
  - Agent A results JSON/Markdown/Diff
  - Agent B results JSON/Markdown/Diff
  - Comparison report JSON/Markdown

**Verification caveat:** "Build/Tests" results are from a single detected command, not independent verification. Report as "verification command passed", not "build and tests both passed".

## Post-execution Safety Check

Verify original repository was not modified:

```bash
cd <repo-path>
git status
```

Should show: "nothing to commit, working tree clean"

If clean, report: "✓ Original repository remains unmodified"

Confirm no worktrees leaked:

```bash
cd <repo-path>
git worktree list
```

Any remaining `temp-*` or `<scenario-id>-*` entries should be removed with `git worktree remove --force <path>`.

## Natural Language Input is Primary

The natural-language request is now the ONLY way to run change-drill. Predefined scenarios in `scenarios.json` are retained for internal/backward compatibility but are not presented to users.

The temporary Scenario is generated on-the-fly, never persisted to `scenarios.json`, and cleaned up after measurement.
