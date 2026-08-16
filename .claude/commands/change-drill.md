---
name: change-drill
description: Execute a controlled change drill experiment in an isolated Git worktree
---

# Change Drill Skill

Execute a change scenario experiment to measure code modification impact.

## Instructions

When invoked, follow these steps:

1. **Get repository path from user**
   - Ask which repository to run the experiment against
   - Default to current working directory if user doesn't specify
   
2. **Invoke the experiment orchestrator**
   - Run: `cd /Users/byurin/codeStress && python3 -m src.cli --repo-path <repo-path>`
   - The CLI will interactively present available scenarios and guide the experiment
   - Answer any prompts the CLI shows

3. **Monitor execution**
   - Watch for the experiment progress (worktree creation, changes, verification)
   - If the CLI asks for confirmation, relay to user

4. **Report results**
   - Show the experiment summary printed by the harness
   - Point user to generated files in `results/` directory (JSON, Markdown, diff)
   - Highlight key findings: files changed, build/test status, completion

## Example Invocation

```
/change-drill
→ User provides: /path/to/target-repo
→ User selects: rename-auth-service
→ Harness creates worktree, captures changes, runs verification
→ Display results with links to generated reports
```
