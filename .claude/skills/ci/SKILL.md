---
name: ci
description: Use the installed corpus-structure ci command for routine repository, test, database, model, corpus, and evidence work. Load when choosing an operational route or diagnosing a ci failure encountered during assigned work.
---

# Operate corpus-structure with ci

Prefer `uv run ci` for functionality it already provides. Run it from the prepared checkout.
Use [AGENTS.md](../../../AGENTS.md#commands) for operating rules and
[ADR-0069](../../../docs/adr/0069-cli-operations-custody.md) for the ownership and effect
boundaries. Here `ci` is the installed project CLI. Hosted CI is a separate verification context.

## Choose the route

- Use `uv run ci --help` or the relevant subcommand's `--help` when you need syntax. Use
  `uv run ci docs commands --stdout` to read the full current reference directly. Use
  `uv run ci docs commands --json` when a managed reference is needed.
- Use `uv run ci context show --json` to inspect resolved settings and their origins when the
  checkout, profile, or environment is in doubt. Use `uv run ci doctor` for tool prerequisites.
  Use `uv run ci setup` to synchronize an already prepared checkout when needed. For
  database work, `ci db status` observes the acquired target and role.
- Use `uv run ci check` for applicable repository checks at the declared boundary. Use
  `uv run ci check --view steps --json` for ordered, structured outcomes. Select
  `--only types`, `--only lint`, `--only docs`, `--only deps`, `--only rules` or
  `--only adr` when you need one check. The rules selector runs the scan. Use
  `uv run ci docs check` for publication and `uv run ci format` for intentional formatting.
- Use the command's defaults when they select the intended scope. Supply the identifiers,
  target, or effect options that change the operation's meaning. For automation, use
  `--json` where supported and capture stdout separately from diagnostics on stderr.
  Retain the exit status and managed result ID. Exit 74 means stdout closed before a
  report could be delivered. An already-known operation failure keeps its own exit status.

Read only the reference needed for the task.

- [Testing and managed results](references/testing-and-results.md) covers targeted and
  full selections, exact retry, coverage, recovery, delivery, holds and expiry.
- [Database and model changes](references/database-and-model.md) covers development
  maintenance, preview and apply, native authoring, deployment, activation and selection.
- [Corpus and review work](references/corpus-and-review.md) covers source preparation,
  retained runs, fitting applicability, review export and detached verification.

Repository recipes stay owned by `just`. Use direct tooling for initial bootstrap, documented
recovery, root `just turn-end`, workflows whose owners still expose only a direct route, and
ordinary source editing, inspection and Git work.

## Own a defect when the work exposes it

Use the CLI for the work at hand. Verification follows the assigned scope and the changed
behavior. Loading this skill does not initiate a CLI audit or a test sweep.

1. Check the installed syntax, resolved context, actual result and owning contract. A
   usage error, a valid refusal, a missing prerequisite and a product test failure each have
   their own remedy. An adapter that drops scope, calls the wrong owner, mishandles custody
   or reports the wrong outcome is a CLI defect.
2. Treat a CLI defect encountered in assigned work as part of the active plan. Preserve the
   failure or result ID. Fix the smallest responsible layer, whether that is the adapter, its
   recipe, or the owning operation. If the defect crosses your assigned write boundary, send
   the exact command, expected behavior and evidence to the coordinator for repair.
3. Use a bounded fallback when needed to diagnose or unblock authorized work. Record what it
   established. Verify the repair through the installed command and directly affected
   consumers, then continue the plan. Keep any unresolved obligation with the owning plan.

For example, an assertion failure inside the selected pytest node goes to the product or
test owner. A keyword-only selection that also starts the exclusive fault lane is a CLI defect.

Existing authority governs effects during repair, including deployment, activation, selection
and recovery. An unrelated feature request follows its own planning route.
