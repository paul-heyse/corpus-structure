---
id: ADR-0001
title: Keep a light, single-operator process and a current documentation working set
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§2]
evidence: Implemented
revisit: Current readers need retired documents, supersession chains or amendment logs to interpret a contract, or a process mechanism exists without a consumer, or agents repeatedly skip `just turn-end`.
---

## Context

corpus-structure is a personal project with one operator, generated from project-template. The
template carries the process that library-context settled on after a predecessor repository
accumulated dozens of ADRs and reviews within days and agents rebuilt project history before they
could act (library-context ADR-0026, ADR-0042). The process has to stay cheap under frequent
change while keeping decisions, evidence and current state findable.

## Options

1. **No recorded process**: least overhead, but decisions and their reasons are lost between
   sessions and agents reconstruct them from code.
2. **Keep everything and label it**: no loss, but the reading context grows without bound and
   contradictions accumulate between current and historical material.
3. **A current working set with Git for recovery** (chosen): each kind of fact has one current
   owner; retired material leaves the tree and is recovered from Git on demand.

End-of-turn hooks were tried and removed: a fixer agent edited other sessions' in-progress code,
and a report-only background job needed a script, a lock and operator plumbing to run a few
recipes that agents can run themselves. Agents run named bundles instead (chosen), and own
`just hygiene` at scope end.

## Decision

- **Ownership.** Architecture pages (DESIGN plus `docs/design/sections/`) own current contracts
  and accepted or proposed targets; current ADRs own reasons and meaningful alternatives; the
  active plan owns execution and the current disposition of scheduled findings; STATUS owns the
  checkpoint; `AGENTS.md` owns agent instructions.
- **Retirement.** A plan, review, evidence folder or ADR without a current consumer is deleted
  once its surviving obligations have a current owner. There is no archive, stub or register.
  Accepted records change only through replacement, apart from status metadata and dated
  factual amendments. ADR ids are allocated above every number in Git history.
- **Development loop.** Work on `main` in the current tree; use a worktree only when truly
  parallel agents must edit production code concurrently. Compile checks and targeted tests are the loop;
  `just check` and `just test-all` (functional tests only) run once all functional scope is
  implemented, not per slice or commit. There are no hooks. The root agent runs `just turn-end`
  (generators, formatting with safe auto-fixes) at the end of a turn that changed files, and
  `just ready` after an environment change. Every
  non-functional check (`just hygiene`: type errors, lint, policy) runs once at scope end beside
  `just test-all`, and the agent fixes what fails. Outcomes use `passed`/`failed`/`blocked`/`not_run` with their commands.
- **Proportion.** Before adding a hook, gate, register or document type, name its consumer.

## Consequences

Current reading is bounded by owners and live records; a replaced decision's surviving reason
must be written where readers look. Recovering an earlier rationale takes a deliberate Git
command. ADR creation needs non-shallow history; lint does not. The tooling is **Tested** by
`tests/scripts/test_adr.py`; the reading-cost benefit remains **Proposed**.
