# Boundaries and composition

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline and limits](README.md#baseline)). Source paths omit
`python/corpus-structure/src/corpus_structure/`; `sql/` means `semantic/sql/`.

<a id="da-079"></a>

## DA-079 — The process execution host refuses a second concurrent run with an unclassified error

**FP-05, FP-07; DP-20; H21, H25.**

`ProcessExecutionHost.run` takes its run lock without blocking and raises
`RuntimeError("process execution host already has an active run")` when it is held
(`orchestrate/execution_host.py:89–92`). The MCP server installs one host for its lifetime
(`intervene/runtime_engines.py:16–31`). `render_source_region` reaches `host.run` through
`execute_native_intent` (`semantic/data_operation_service.py:237`), and its refusal wrapper
converts only `ValueError`, `KeyError` and `OSError` (`intervene/native_render_tools.py:91–92`).

**Consequence.** If two agent renders overlap, the second fails with a generic tool error. It
neither waits nor receives a typed refusal that says "busy, retry".

**Contrary evidence.** ADR-0125 deliberately allows one active run per host, and one run serves
all of its claims concurrently. Provider residency itself now waits on a condition rather than
refusing (`methods/native_host.py:842–863`), which corrects the earlier ready-execution
observation about non-blocking provider borrowing.

**Limit.** Overlap is likely, not observed: the installed MCP framework runs synchronous tools
in worker threads by default (installed source read 2026-11-17), and ADR-0125 itself
anticipates concurrent MCP calls sharing one budget and states that it trades away concurrent
entry-point execution. Concurrency at the transport level was not checked.

<a id="da-080"></a>

## DA-080 — Superseded machinery remains in the production tree, kept alive only by tests or by nothing

**Delta, 2026-11-17, source `1afa63f88`.** Partly corrected: `native_finalization.sql` was deleted (`708c119a6`); the other thirteen unreferenced SQL files remain. `semantic/target_installation.py:209, 215` still dispatches on the name `scientific_layout.sql` after that file was converted ([delta](README.md#delta-1afa63f88)).

**FP-01, FP-03; DP-01, DP-16; H27.** This is the production home for a cause that also shows
in the test account ([DTA-035](../test-audit/retirement-transfer.md#dta-035)).

Four groups were found with no current production consumer:

- **Native SQL files.** Fourteen files under `semantic/sql/` (about 1,980 lines) are named by no
  loader in `src`, `scripts`, `tests`, `domains` or the migration trees: `characterization`,
  `current_operation_guards`, `definition_declaration`, `exclusions`, `fact`,
  `native_finalization`, `record_policy`, `record_references`, `selection`,
  `source_anchor_coordinates`, `source_record_coordinates`, `source_record_report`,
  `split_decisions`, `validation`. Every loader names a literal file; the one directory walk is
  the change explanation. `validation.sql` defines `data.validate_state`, which the loaded
  `source_record_graph.sql:3` also defines. They still enter the model-change source fence and
  the SQL change explanation (`schema/model_change.py:643–647`; `schema/model_explanation.py:423–455`),
  so editing them invalidates previews and nothing else. `record_references.sql:623–625` still
  reads `ops.task_dependency`.
- **Evaluation modules.** `evaluate/equivalence.py`, `affine.py`, `artifact_pilot.py`,
  `sampling.py`, `split_decisions.py` and `split.py` (about 1,190 lines with `sets.py`) are
  imported only by tests or by each other; `sets.py` is imported by nothing.
- **Rendition keying and translation.** No production caller constructs `KeyContext`
  (`core/keys.py:928–960`) or imports `core/translations.py` and `core/candidates.py`; the
  rendition-index branch of `semantic/proposals.py:286–300` is unreachable from its one caller
  (`:614`). Six test files and about 3,300 test lines exercise this half.
- **Earlier pack loader.** `schema/pack.py` and `schema/lookup.py` have no production importer
  outside `schema/` (see [DA-072](semantic-model-and-authority.md#da-072)).

**Consequence.** These read as current authority. Passing tests over them look like assurance
for paths that do not run, they are paid for in every run, and they stand in the way of the
removal that the project's design-stage rule asks for.

**Limits.** "No consumer" is by search over the named trees; a loader that builds file names
dynamically was searched for and not found, and dynamic imports were not excluded. Parts of
`core/keys.py` and `core/locators.py` are live. Whether the rendition half is meant to return
(archive reading, prompts) is an owner question.

## Prior identities on this page

<a id="da-018"></a>
<a id="da-019"></a>
<a id="da-020"></a>
<a id="da-045"></a>
<a id="da-047"></a>
<a id="da-052"></a>
<a id="da-059"></a>
<a id="da-060"></a>

Earlier text is in Git at `fbd3f2a98`.

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-018 | Not re-examined | Historical correction |
| DA-019 | Not re-examined | Test-sweep leasing is covered by the [test account](../test-audit/README.md) |
| DA-020 | Not re-examined | Cited `domain_operations.py` and `orchestrate/commands.py` are gone |
| DA-045 | Not re-examined | — |
| DA-047 | No longer applicable | `orchestrate/commands.py` is gone |
| DA-052 | Not re-examined | — |
| DA-059 | Not re-examined | Last evidence 2026-11-10 |
| DA-060 | Not re-examined | Last evidence 2026-11-10 |
