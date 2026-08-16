# Clean Code Change Lab (codeStress)

AI-driven experimental measurement of codebase changeability through isolated parallel change drills.

## Parallel Agent Model

### Agent Configuration

- **Single Agent Mode:** 1 agent per experiment
- **Parallel Mode:** Up to 3 agents concurrently
- **Default:** 3 agents (when using parallel mode)
- **Maximum:** Never exceeds 3 agents

### Architecture

```
Scenario → Setup (N Worktrees) → Coding Agents (1-3 concurrent) → Measurement → Report
```

Each agent:
- Works in its own isolated Git worktree
- Receives identical task and scenario
- Operates independently (no cross-access)
- Produces separate evidence
- Measured independently

### Documentation

- **Planning:** [docs/code_stress.md](docs/code_stress.md)
- **User Scenarios:** [docs/code-stress-user-scenarios.md](docs/code-stress-user-scenarios.md)
- **System Design:** [docs/system_design.md](docs/system_design.md)
- **Implementation Details:** [IMPLEMENTATION.md](IMPLEMENTATION.md)
- **Parallel Execution Milestone:** [MILESTONE_PARALLEL_AGENTS.md](MILESTONE_PARALLEL_AGENTS.md)
- **Real Agent Integration:** [MILESTONE_REAL_AGENT_INTEGRATION.md](MILESTONE_REAL_AGENT_INTEGRATION.md)
