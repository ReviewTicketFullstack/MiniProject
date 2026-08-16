---
name: change-drill
description: Execute a controlled change drill experiment in an isolated Git worktree
---

# Change Drill Skill

Execute a change scenario experiment to measure code modification impact.

This skill orchestrates a complete change drill in three phases:
1. **Setup** — Create isolated worktree
2. **Code** — Launch Claude Coding Agent to implement scenario
3. **Measure** — Run verification and generate report

## Instructions

When invoked, follow these steps:

1. **Get repository path from user**
   - Ask which repository to run the experiment against
   - If unclear, default to current directory
   
2. **Load scenario**
   - Ask user to select or specify scenario
   - Available scenarios: `add-cancellation-reason`, `rename-auth-service`

3. **Setup phase: Create isolated worktree**
   - Run: `cd /Users/byurin/codeStress && python3 -m src.cli --repo-path <repo-path> --scenario <scenario-id> --phase setup`
   - Watch the output and extract:
     - `worktree_path`: Line like "Worktree ready at: /path/..."
     - `base_commit`: Line like "Base commit: XXXXXXX"
   - Show user that setup is complete

4. **Invoke Coding Agent to implement scenario**
   - Use the Agent tool to spawn a new Claude coding agent
   - Tell the agent:
     - The target directory is the worktree (use worktree_path)
     - The task is from the selected scenario prompt
     - The agent should modify code files in that directory
     - The agent should make all necessary changes to complete the scenario
   - Wait for the agent to finish and signal completion

5. **Measure phase: Capture results**
   - Run: `cd /Users/byurin/codeStress && python3 -m src.cli --repo-path <repo-path> --scenario <scenario-id> --phase measure --worktree-path <worktree-path> --base-commit <base-commit>`
   - Monitor the output for measurements and report

6. **Display results to user**
   - Extract and show:
     - Completion status (✓ or ✗)
     - Files changed, lines added/deleted
     - Build and test status
     - Paths to result files
   - Offer to show the generated report details

## Key Design Points

- **Isolation**: Worktree is separate from original repository
- **Simplicity**: One coding agent, sequential execution
- **Observability**: All output is captured and shown to user
- **Reusability**: Each phase can run independently
