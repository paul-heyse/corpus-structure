---
name: handoff
description: Update STATUS.md from the actual tree after work changes the project state. Preserve concurrent work, distinguish decisions from verified implementation, and link to the single current owner of finding disposition.
---

# Handoff

Keep STATUS.md within 60 lines. It is a current checkpoint; the architectural collection owns architecture, ADRs own
rationale, the design principle audit owns baseline diagnosis, reviews own solution reasoning and dated evidence,
and the active plan owns scheduled findings' current status. Ordinary handoff does not refresh the
diagnostic audit; link to its owner only when the checkpoint depends on it.
The binding defines disposition transfer and closure. Link to that owner rather than maintaining
another mutable finding list. Replace the checkpoint rather than appending a session narrative;
keep a dated receipt only while it bounds a current claim, with its original date and scope.

## Gather

- `git log --oneline -10` and `git status --porcelain`: landed work and concurrent edits.
- Outcomes of checks actually run for this scope. Use the repository's acceptance timing. A
  handoff does not trigger `uv run ci check` or `uv run ci test`. Report omitted checks
  as `not_run` with the reason; never promote another session's receipt to a current result.
  Complete qualification accounts for the declared required functional/provider/nonfunctional
  union of explicitly scoped applicable native results (ADR-0001); preserve original failed or
  interrupted records, bounded scope and final-source/context applicability.
- Current ADR index and relevant decisions. `just turn-end` regenerates the index.
  Use `uv run ci adr lint` when a separate check is due. Inspect relevant revisit
  conditions; run commands only when due and within scope.
- Current plan disposition rows and review conclusions. Distinguish the bounded slice judgment,
  enclosing architectural status and remaining integrated acceptance.
  If a recommendation or completion audit was performed, use the integrated review or corrected
  owning plan for the current conclusion. Link the companion only when its net changes matter
  to the checkpoint; do not copy editorial dispositions into execution status. Handoff does not
  initiate either audit automatically.

## Write

1. **Increment and slice:** functional scope and process changes, committed or dirty.
2. **Last verified:** dated commands and `passed`/`failed`/`blocked`/`not_run`; name missing prerequisites.
   Write each command as an agent should run it: a recipe or bare command, without incidental
   environment prefixes such as `UV_OFFLINE=1` or `PYTEST_ADDOPTS=…`. Keep a prefix only when the
   command needs it, and say why; later agents copy receipts verbatim.
3. **Known failures, blocks and decisions:** do not drop an unresolved issue; link to its current
   disposition owner and summarize the consequence without replicating the full register.
4. **Next:** the next concrete action, responsible component and verification boundary.

Read shared files again before writing. Preserve changes made by other work, and do not claim
this session tested them. The tree establishes implemented state; a target remains labeled until
implemented and supported by the appropriate evidence.

For documentation work, record focused docs checks separately from product qualification and remote
CI. Link the current plan; navigation and search selection must not become another progress list.

When next work depends on selected library mechanisms, link the owning plan sections that retain
their concrete functionality, rationale and source references. Before retiring a plan, carry
enduring mechanism choices and material limitations into the established architectural owner.
Keep repository-specific adoption rationale there; reusable library overviews remain repo-agnostic.
