# M1 retained source-state and value hypotheses

**Tested bounded development-gap repair, 2026-11-04.** The original Grinstead–Snell
run 10/cut 4/task 27 retained 137 actual native groups but emitted zero records. State
inspection proposals displaced independently located values before occurrence
identity was assembled. This change preserves both observations and their exact
evidence; it does not establish extraction quality or production acceptance.

The assembler retains an unresolved inspection reading with its inspected-context
evidence and a typed value alternative with a separate literal or classification
cue evidence set. Valid primary raw proposal anchors can identify the occurrence
even when its inspected field remains unresolved. Invalid, missing, synthetic or
related-only primary proposals cannot borrow context evidence to establish an
occurrence. A conflicting state and an explicitly unresolved state receive
different diagnostics; raw state/value/confidence bytes remain in the actual
report and shared native-group dependencies.

For one actual native group, the assembler also retains at most one coherent whole
value reading. It selects only actually located literal values and classifications
with separately located cues. Other fields keep their actual inspected states:
missing output stays unresolved. Both readings share occurrence identity and
have distinct interpretation identities; both remain candidate. Structural native
supplements remain intact. Formula binding identity still requires a real symbol
and meaning proposal plus an exact primary first symbol use; ambiguity cannot
become a formula-only reading. No field Cartesian expansion, probability or
acceptance is introduced.

The interpretation recipe dependency is `source-reading-hypotheses-2`; branch
dependencies distinguish `inspection` from `native-group-value` while retaining
the same real native-group dependency. The existing auxiliary proposal schema
`source-role-inspection-1` remains unchanged. The integrated source operation and
policy fitting/calibration must use the new candidate universe before any
production qualification.

`replay_stored_groups.py` reads the exact named sealed raw task through ordinary
read credentials. It reconstructs the old context pieces, relationships,
retrieval receipts and policy from retained inputs, rather than applying current
source routing. Every retained decoder report must satisfy its exact source
context digest, consumed-text SHA, pack fingerprint and effective-profile bytes.
No fallback, annotation/model/PDF execution, database mutation or publication is
performed. The retained original envelope, task configuration, source frames and
pack declarations are in `replay-003/replay-inputs.json`, linked by digest from
`replay-003/replay.json`. The final replay also retains the exact executed
`record_assembly.py` bytes and digest.

The actual read-only replay command passed:

```bash
uv run python docs/design_review/evidence/2026-11-04_m1-capture-repair/replay_stored_groups.py \
  --run 10 --cut 4 --task 27 \
  --release release:e8b1dc426a02a024bf065ee29e5fa95c77a862efd0cbdfb38640a5ccf8cac938 \
  --out docs/design_review/evidence/2026-11-04_m1-capture-repair/replay-003
```

All 265 retained reports were rebound: 72 definition, 72 assertion, 72 measurement
and 49 formula-context reports. Their actual raw groups were 62 definition,
zero assertion, 13 measurement and 62 formula-context groups. Reassembly retained
50 definition candidate readings: 25 inspection and 25 value readings over 20
occurrence IDs. These are retained hypotheses, not 50 correct records.

Remaining diagnostics include 112 unlocated occurrences, 562 unresolved fields,
71 state/value conflicts, 31 unresolved value proposals, 69 unlocated value
proposals and 8 unsupported fields. Of the latter two categories, 66 lack an
independently located classification cue, one literal does not reconstruct,
two intersect synthetic text and 8 use unsupported alternate/recognized source
space. These observations do not establish the earliest causal stage of every
remaining gap. Other family capture and independent quality gains remain open.

`replay-001.log` retains the failed first replay: context/report reassembly
completed, but the evidence script passed records rather than `AssemblyResult`
objects to the reconciliation API. `replay-002` corrects that script call;
`replay-003` retains the same result with final executed assembler bytes. No
provider was rerun and no attempt changed the source/publication state.

Pure functional controls passed 34 tests with:

```bash
uv run pytest python/corpus-structure/tests/methods/test_record_assembly.py \
  python/corpus-structure/tests/methods/test_record_readings.py -q
```

The controls include exact separate alternative evidence, two whole readings
without Cartesian expansion, shared occurrence identity, raw confidence retention,
invalid/related primary refusal, cue-less classification, duplicate groups and
formula ambiguity/first-use identity. This is a focused result; native
integration and independent-reference quality qualification remain separate.

Scoped Pyrefly and Ruff passed for the changed production/test files; the replay
script passed scoped syntax/import lint. Root maintenance and assembled native
qualification remain with the coordinator.

## Rich-cell native assembly

**Tested bounded native-table repair, 2026-11-04.** Rich cells retain their actual
child literal pointers, for example `#/texts/…`, while occurrence identity retains
the separate native parent table/cell anchors. The assembler appends a cell suffix
only for an actual flat `#/tables/N` `cell_text` coordinate. It never invents
`#/texts/N/data/table_cells/M` or derives native cell existence from a child piece.

`native_table_cell_projection` in the existing source-preparation owner supplies
the canonical rich-cell projection. Assembly checks its complete ordered native
piece pointer/field/text signatures against the selected context. Rich-cell
summary text does not substitute for the child projection. Actual discontinuous
words remain a literal text sequence with separately addressed evidence; internal
synthetic separators never become source words. Missing, foreign, partial or
unsupported native projections leave the path unresolved.

An unresolved structural row/header field can retain a separately located actual
raw model proposal through the existing typed alternative and coherent value
branch. Present canonical structural values remain unchanged. Native table/cell
identity remains the same across both candidate readings, and unmarked first
data columns are not promoted to native row headers.

The actual retained source probe passed without annotation/model/PDF/provider
execution or publication:

```bash
uv run python docs/design_review/evidence/2026-11-04_m1-capture-repair/probe_rich_table_assembly.py \
  --out docs/design_review/evidence/2026-11-04_m1-capture-repair/rich-table-001
```

`rich-table-001/result.json` retains all selected contexts and candidate records;
`source-inputs.json` retains actual source/configuration and already stored
annotation inputs. Under preparation policy 3, all 182 eligible targets in 26
bounded contexts produced 182 native candidate occurrences. Complete declared
header paths were located for 156; no native row identities were declared, so
those remain unresolved. The 572 unresolved-field diagnostics are retained.
These are source-bound candidate assembly observations, not independently correct
record counts or a quality gate.

The final stored decoder replay is `replay-004`, preserving `replay-003`. Its
purpose remains exact old-report reassembly under the old context recipe, not
application of new table routing or a new model run. The final executed assembler
bytes and digest are retained alongside its result.
It retains the same 50 definition candidates across 20 occurrences, with 112
unlocated groups still visible. Additional actual proposals beside unresolved
structural fields are now retained: its unresolved-value-proposal count is 56 and
unlocated-value-proposal count is 70; the earlier replay's counts remain preserved.

The combined assembly/readings/source-preparation suite passed 56 tests. Added
controls cover authentic rich child pointers and native parent cell identity,
complete text sequences, missing/foreign/synthetic child replacement, and raw
alternatives beside unresolved structural fields without overriding present
native fields. Scoped typing/lint passed. The standalone
`test_record_alternative_publication_native.py` adds a candidate alternative
publication roundtrip using existing fixtures; native execution is `not_run`
pending the coordinator's successor deployment.
