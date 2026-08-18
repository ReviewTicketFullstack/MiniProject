---
name: change-drill
description: Predict implementation approach and cost for a proposed change (read-only analysis)
---

# Change Drill: Prediction Mode

Predict how a proposed change would be implemented without actually implementing it.

**Workflow:** Natural language → Read-only analysis → 2-agent predictions → Terminal UI report

## Pre-execution: Collect User Input

Do NOT show a numbered menu. Do NOT assume any scenario.

1. Ask: "Which repository should we predict for?" (default: current directory)
   - Accept any git repository path

2. Ask: "What change would you like to predict? (Describe in natural language)"
   - Wait for the user's natural-language request
   - Accept any description of a feature, refactoring, or fix
   - Do NOT suggest predefined scenarios

## Claude: Parse User Input and Generate Scenario

Based on the user's natural-language response, generate a temporary Scenario dict **in memory**:

```python
scenario = {
    "id": "temp-" + generate_timestamp_or_uuid(),
    "name": (concise title from user's request, max 60 chars),
    "description": (user's request summarized, max 200 chars),
    "prompt": (actionable analysis prompt for agents)
}
```

**Rules:**

- Use ONLY the user's actual request as the source
- Never use example text from the documentation
- The prompt must guide agents to analyze the codebase

## Show Generated Scenario for Confirmation

Display the temporary Scenario you just generated:

```
PREDICTION SCENARIO FROM YOUR REQUEST
====================================
Name:        [Generated title]
Description: [Summary of request]

Analysis prompt:
[Full prompt for agents]

Proceed with prediction? (yes/no)
```

**If user confirms "yes":**

- Proceed to Phase 1: Validate Repository

**If user says "no":**

- Ask: "What would you like to clarify or change?"
- Go back and regenerate scenario
- Show revised Scenario for confirmation

## Phase 1: Validate Repository

Validate that the target repository exists and is readable (no modifications will be made):

```bash
cd /Users/byurin/codeStress
python3 -m src.cli --repo-path <repo-path> \
  --scenario-json '<scenario-json>' \
  --predict \
  --parallel 2
```

**Output should show:**

```
PREDICTION MODE
==================================================
Scenario: [name]
Agents: 2 (read-only analysis)
==================================================

Repository validated. Ready for prediction agents.
(Agents will analyze code without modifying anything)
```

Confirm with user: "Repository ready. Invoking prediction agents now..."

## Phase 2: Prediction Agents

Spawn exactly 2 independent Claude Coding Agents in parallel.

Both agents must:

- Work in read-only mode
- Never edit, create, delete, or write files in the target repository
- Analyze the requested change
- Return their prediction as structured JSON
- Save their prediction to:
  - results/agent_A/<scenario-id>\_prediction.json
  - results/agent_B/<scenario-id>\_prediction.json

Wait until BOTH agents have completed and their prediction JSON files exist.

Do NOT display the final result yet.

## Phase 3: Collect and Display Predictions

After BOTH agents have completed, run the CLI again to collect their results and display the comparison:

````bash
cd /Users/byurin/codeStress

python3 -m src.cli \
  --repo-path <repo-path> \
  --scenario-json '<scenario-json>' \
  --parallel 2 \
  --predict

## Phase 3: Aggregate and Display Results

Collect predictions from both agents and display in Terminal UI:

```bash
# (Skill handles this internally)
# Aggregate the two JSON predictions
# Build comparison analysis
# Display terminal UI with:
#  - Scenario name
#  - Agent A predictions
#  - Agent B predictions
#  - Comparison (consensus/divergence)
````

The Terminal UI will show:

```
CODESTRESS
CHANGE DRILL PREDICTION

Scenario
  [User's change request]

Agent A
  Estimated tokens
  Estimated files
  Estimated LOC
  Complexity
  Implementation approach
  ... observations

Agent B
  Estimated tokens
  Estimated files
  Estimated LOC
  Complexity
  Implementation approach
  ... observations

COMPARISON
  Estimated change scope
  Common points
  Divergent points
  Structural observations

KEY: All values are ESTIMATES based on static code analysis.
These predictions are not guarantees of actual implementation cost.
```

Result files saved for evidence:

- `results/agent_A/prediction_{scenario_id}.json` — Structured predictions
- `results/agent_B/prediction_{scenario_id}.json` — Structured predictions

## Post-execution Safety Check

Verify original repository was not modified:

```bash
cd <repo-path>
git status
```

Should show: "nothing to commit, working tree clean"

If clean, confirm: "✓ Original repository remains unmodified"

## Key Differences from Implementation Mode

| Aspect         | Implementation                | Prediction                      |
| -------------- | ----------------------------- | ------------------------------- |
| Worktrees      | Creates 2 isolated worktrees  | No worktrees                    |
| File changes   | Agents implement changes      | Agents analyze only (read-only) |
| Build/Tests    | Runs verification             | No build/test execution         |
| Git operations | Uses git diff to measure      | No git operations               |
| Evidence       | JSON + diff files             | JSON predictions only           |
| Output         | Terminal UI + JSON            | Terminal UI + JSON predictions  |
| Time           | Minutes (with implementation) | Seconds (analysis only)         |

## What This Mode Tells You

Predictions from this mode help you:

- Estimate implementation cost before starting
- Understand different implementation approaches
- Identify potential coupling/dependency issues
- Assess changeability impact
- Make decisions about whether to implement

Predictions are NOT:

- Guarantees of actual implementation
- Exhaustive file lists
- Precise LOC counts
- Final technical decisions

Use predictions to inform decisions; validate with actual implementation if needed.
