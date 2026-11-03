# Private family assembly component

**Tested · 2026-11-03 · bounded candidate shape/location integration.** Implementation baseline
`8ea35f88`, isolated `codex/m1-assembly`. The M1 coordinator owns package completion and the
required qualification union. This evidence supplies no accepted-release, native persistence,
publication, reading-accuracy or all-family retained-source claim.

`methods/record_packs.py` derives literal/classified native fields, released classification value
kinds and closed choices from the prepared family declarations. The caller supplies its explicit
natural grouping anchor and extraction descriptions. Native locations and transformed values
do not become decoder string fields. All extracted fields use `optional_one`; missing decoder
output remains unresolved, with a reason.

`methods/record_assembly.py` provides the shared released-field builder:

- `assemble_records(prepared, context, pack, report, *, contract, anchor_role, policy_version,
  occurrence_roles=None, supplements=None)` consumes a genuine native report. Supplements map
  temporary group indices to explicit `NativeRecordGroup` inputs; occurrence identity comes from
  source anchors rather than those indices.
- `assemble_native_records(prepared, context, *, contract, occurrence_roles, policy_version,
  groups)` consumes genuine structural groups without fabricating inference.
- `native_table_groups` reads retained native cell structures and exact source-piece locations
  under explicitly supplied full row/header paths and declared note/unit/caption inheritance.
  Blank native text, missing cells and a literal dash remain distinct. Missing/ambiguous paths
  remain unresolved; there is no proximity-based note attachment or header retrieval.
- `native_formula_group` consumes the existing `FormulaOccurrence` and explicitly located
  declaration roles/scope. It accepts original formula text reconstructing the same pinned
  canonical source view. Recognized LaTeX/parser offsets and equal symbol spellings do not
  establish source evidence or declaration identity.
- `reconcile_record_candidates` reduces equal source readings across windows and unions all
  computation dependencies. Distinct positions and qualification alternatives survive. Callers
  retain the original results and raw reports; repeats are not independent votes.

Every output remains `candidate`. Family roles, kinds, meaning-changing standing and occurrence
recipe are taken from the release; the existing binder validates the result. Explicit inspected
scope/reason is required for a supplied nonpresent state. Classified enum offsets cannot become
literal evidence; independently reconstructing cues require an explicit association reason.
Original strings/decimals remain exact. The result retains raw reports, structural inputs,
unlocated diagnostics and role/group dependencies, including rejected alternatives.

## Actual source and CPU attempt

The helper reads MAIN's frozen `2026-11-03_m1-gliner-runtime/mapped-context-00001.json` and
`attempt-00005.json` without database access, reconstructs the exact source context subclass,
prepares the actual current statistics family declarations, generates a definition pack, and
runs the acquired CPU worker. `#/groups/4265` supplies explicit native section scope.

| Attempt | Outcome | Meaning |
| --- | --- | --- |
| `attempt-00001.json` | failed | Frozen primary was a `NativeProposalFrame`; initial helper attempted `NativeFrameSource` rehydration. No inference ran. Retained unchanged. |
| `attempt-00002.json` | passed | Three distinct-position definition candidates passed released shape and coordinate binding; actual worker joined. Source, helper and implementation hashes are recorded. |

The three actual candidates all associate `normal distribution` with defining text `central
limit theorem` and alias `theGaussian distribution`. These strings reproduce the source
projection, but the association does not establish a faithful definition reading. The released
`definition_relation=definition` classification has unavailable cue evidence. These actual
limitations are retained in the raw report/candidates; passing here means shape and location
binding only.

Run from MAIN, selecting a new positive attempt number and this checkout on `PYTHONPATH`:

```sh
PYTHONPATH=/home/paul/.cache/corpus-structure-m1-assembly/python/corpus-structure/src uv run python /home/paul/.cache/corpus-structure-m1-assembly/docs/design_review/evidence/2026-11-03_m1-family-assembly/check_cpu_assembly.py --main-root /home/paul/corpus-structure --attempt 3
```

## Focused checks and remaining scope

**passed · 2026-11-03:** 80 focused tests across `methods/test_record_assembly.py` (16 independent
family/control tests), `methods/test_gliner.py` and `semantic/test_record_contracts.py`, using
MAIN's `uv` environment and the isolated source tree on `PYTHONPATH`. These include all five
families, modal/condition evidence, exact mean versus dispersion roles for two groups, repeated
positions/windows, discontinuous/nested evidence, table full headers/notes/blank/zero/dash/missing
cells, scoped formula declarations, unmappable spans and field-state controls.

```sh
PYTHONPATH=/home/paul/.cache/corpus-structure-m1-assembly/python/corpus-structure/src uv run pytest /home/paul/.cache/corpus-structure-m1-assembly/python/corpus-structure/tests/methods/test_record_assembly.py /home/paul/.cache/corpus-structure-m1-assembly/python/corpus-structure/tests/methods/test_gliner.py /home/paul/.cache/corpus-structure-m1-assembly/python/corpus-structure/tests/semantic/test_record_contracts.py -q
```

**passed · 2026-11-03:** scoped `uv run ruff check` and `uv run pyrefly check` on the two owned
production files and owned test file. Pyrefly used
`--site-package-path /home/paul/corpus-structure/.venv/lib/python3.14/site-packages` because the
isolated checkout has no environment. No dependency installation or database write occurred.

**not_run:** retained-source extraction for the other four families, production pipeline routing,
persisted admission/accepted release, all-family source-reading evaluation, final qualification.
Related/cross-view and alternate/recognized evidence remain explicitly unsupported by the
private-100 custody contract. Upstream table path selection/note applicability and declaration
scope remain explicit inputs; no generic matching, solver, store or cache was added. Broader
set-based selection belongs to the existing analytical-scope owner; these adapters compose small
already selected native groups and perform keyed reconciliation only.

The coordinator copies and finalizes these receipts. Existing inherited LFS-pointer changes in
the isolated checkout were not altered.

## Integrated-tree check

**passed · 2026-11-03:** root copied the two reviewed producer modules and16 tests to MAIN,
then ran the same80 focused tests with MAIN imports. No source/model/database mutation occurred
during this check. This does not expand the actual CPU attempt's shape/location claim.

```sh
uv run pytest python/corpus-structure/tests/methods/test_record_assembly.py python/corpus-structure/tests/methods/test_gliner.py python/corpus-structure/tests/semantic/test_record_contracts.py -q
```
