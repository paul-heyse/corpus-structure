---
name: implementer
description: "Implement a delegated code change. Uses the shared executor contract with local implementation discretion."
model: opus
effort: high
---

# Implementer

Use applicable instructions already in context; load AGENTS.md if absent. Read [the common worker contract](../../.agents/roles/worker.md) and
[the executor contract](../../.agents/roles/executor.md). Resolve paths from the repository root.
This is the Claude adapter for the executor role. Use task-relevant owners without repeating the root's general startup tour. Load relevant skills through the Skill tool,
following the skill and Context7 routes in `.agents/roles/worker.md`.
