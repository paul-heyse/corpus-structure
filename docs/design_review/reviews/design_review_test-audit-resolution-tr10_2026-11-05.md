# TR-10 — Assembled test-audit resolution target review

**Decision: Accept the assembled design and bounded corrections. Full-series qualification remains open.**
Independent delegated design reviewer,2026-11-05; design tier, target purpose, combined full-standard/library focus.
Intended publication: `docs/design_review/reviews/design_review_test-audit-resolution-tr10_2026-11-05.md`.

## 1. Scope, baseline and evidence boundary

Subject: the resolution coordinator and all four companions, their assembled implementation and affected consumers.
Consume TR-00 at `ea4d410f`, test-audit publication `1e42a6e5`, and audited source
`bc2208f9d6a12d3ad9cf71575fa1c6df388d885b`. Standard: core3.3, heuristics1.0, test-assessment1.2,
applicable CI1.4 and repository binding. Functional grounding: DESIGN §1.1, D3 native deployment,
D7 independent evaluation and D9 tests. This is the scheduled assembled review, not another broad audit.

Inspected HEAD after root final formatting: `f45d88d79fb9bb5a305a13dd2c48bdf2042de965`, plus the identified
dirty scenario/assertion/native correction. SHA256 of the scoped `git diff --binary <audited-source> -- <paths>`:
`cab2a33e0e97c2341ebe325ed315f65e8cd919b78302c0f702a6d9a420c1cc09`.
Paths: `python/corpus-structure/tests`, `python/corpus-structure/src`, `python/corpus-structure/semantic_alembic`,
`scripts/native_test_support.py`, `scripts/qualification_plugin.py`, `scripts/test_receipts.py`,
`tests/conftest.py`, `tests/scripts/test_native_auth.py`, `tests/scripts/test_test_receipts.py`,
`tests/test_native_region_render.py`. New untracked migration products are separately identified:

| Product under semantic_alembic/versions | SHA256 |
|---|---|
| `0152_local_semantic_rowtype.py` | `dc9886a5ea7c6923d71840fefae96d77e61e4fac3eb269a332ad624d12435637` |
| `semantic_test_rowtype_20261105_native.json` | `d3c41cdd666d7a4cb596c000ac1dadf7f4f9228c68f017ad2c34b18d0cf1d6a0` |
| `semantic_test_rowtype_20261105_admission.sql` | `e59205baa3299bde97605dc1b501a10404014e0ced28fd704e805b2ae90e6345` |
| `semantic_test_rowtype_20261105_upgrade.txt` | `c008175eb501a1036aeb48e4cb70c9b5e767d5637ffaa3fede75d19b33d960f5` |

Method: independent source/contract and installed-library inspection, current caller searches, static
source reconciliation, and inspection of producer logs/receipts. This reviewer ran no product tests,
database operations or probes and edited no repository file. Unrelated production-review/STATUS changes
were excluded and preserved. Publishing the same inspected bytes changes Git identity without changing
this assessment. Subsequent semantic changes need affected review/evidence reassessment.

## 2. Responsibilities, dependencies and semantic ownership

| Owner | Contract and direction |
|---|---|
| `native_record_fixtures` | Pure preparation returns original bundle/dependencies/profile/prepared release. Native construction consumes these and explicit options; owns real publication/task effects. |
| `reference_scenarios` | Independently authored source readings, frames, origins and labels; consumes scenario references, never producer candidates for expected meaning. |
| `domain_scenarios` | Shared kernel-model/batch construction with explicit release identity; preparation occurs at a fixture/caller, not import. |
| Math fixtures/support/transport | Explicit retained/read/extract/scope products, session dependency reuse, spawned execution and faithful library-value transport. |
| Native support/plugin | Resource ownership and actual acquisitions / live observation-consumer lifetime, respectively. |
| Classifier | Identity completeness, node applicability and owned-process settlement; no invented deployment evidence. |
| Native semantic validator | Exact cut/grade/source/witness authority; representation correction preserves this responsibility. |

The model distinguishes construction from expected answer, retained data from process-owned preparation,
requested stage from completed work, acquisition identity from optional deployment metadata, and Python
refusal from native enforcement. These distinctions govern operations, not merely output labels.

Applicable CI fact/fidelity assessment: source/record/evidence relations retain original pins and member
identity; absent/empty/partial reports remain distinct. Independently authored reference values stay
outside producer inputs. Actual acquisition facts come from connections; unavailable revision/policy
observations remain unavailable. No code-graph or new analytic capability is claimed.

Decisive locations: test `semantic/native_record_fixtures.py:183/252/263/653`,
`semantic/reference_scenarios.py:206/297`, `math_support.py:199`, `math_worker_transport.py:26`,
`semantic/test_local_semantic_admission_native.py:445`; root `scripts/native_test_support.py:668/677`,
`scripts/qualification_plugin.py:20`, `scripts/test_receipts.py:427/588`; production
`semantic/sql/record_publication.sql:1047` and `semantic/execution_admission.py:204`.
Package-relative paths are under `python/corpus-structure/tests` or `src/corpus_structure` as appropriate.

## 3. Contracts and discriminating assurance

The ten judged-semantic mutations establish a valid SERIALIZABLE workspace before their expected-error
region. An unchanged sibling passes through the same staging/publication operation and is rolled back;
then a single-fault input reaches native publication. Exact FK identities or primary diagnostics identify
source/cut, witness/applicability and statement failures. The no-data refusal also identifies the native
validation function through diagnostic context. Post-failure state checks protect atomicity. The direct
writer status-update42501 control remains separate; writer grants were not widened.

Private custody tests refresh ordinary derived identities when changing source meaning; deliberate
identity-corruption cases remain. Actual privilege controls observe principal/login and SQLSTATE42501.
PDF late-append and missing-validation cases establish lifecycle premises and use current-shaped bodies.
Decomposed/integrated cases distinguish Python preparation from native record-shape/task-fence checks.
Local append cases omit unrelated record-report transport so an earlier record-append guard cannot
satisfy the local-assertion claim.

The composed journey asserts exact independent support/evidence/report identities, multiplicity, locators
and custody, retaining the Alice fact assertion. Immutable input addresses supply identity binding, not
expected consolidator semantics. Native score controls vary center and scale separately and include a
noncancelling combined case. LinkML exit/report checks and asymmetric source-authored PDF pixels
separate the previously confounding outcomes. Independent reference meaning and frozen bytes remain.

## 4. Composition and execution fit

Focused pure placement assertions require preparation alone. Readings activate no extraction/scopes;
extraction activates no scope/NLP; scopes consume earlier products. Whole-group selection parses each
fixed population once. Parent views reuse content/readings instead of retaining complete deserialized
copies per tier. Frozen historical macros and independent source answers remain distinct from current
production configuration. Real scope resolution runs in worker main threads, preserving parser signals.

The runner retains bounded outstanding submission, page identity, spawn, submission-to-result deadlines
and pool settlement on BaseException. Direct whole-page jobs retain one whole-job deadline; separately
requested stages have separate active-job deadlines. The lightweight transport initializer avoids
unrelated grammar/NLP startup in short lifecycle controls without increasing their deadlines.

Inactive native observation returns before observation-only acquisition, cursor work, hashing, cache
mutation and rollback. Required authentication, policy replay, cloning and cleanup continue. Capture
precedes its owned clone preparation and outlives teardown. Existing engines consult current consumer
availability; late capture cannot reconstruct unobserved history. Rust and Python share cleanup
predicates. Zero Rust selection remains no functional coverage.

These routes credibly fit focused/full test selection, retained corpus populations, concurrent native
ownership and failure/retry. This is qualitative structural assessment, not measured speed/capacity.

## 5. Original change and failure scenarios

| Scenario | Assembled assessment |
|---|---|
| New source/reference/policy family | Explicit transforms, method descriptors, reading functions, origins and labels replace private-host interception; expected source meaning retains its own owner. |
| Helper/import refactor or collection only | Caller searches found no remaining migrated private-host imports/global specialization; fresh-interpreter sentinel covers import passivity. |
| Select one/all math tiers | Explicit dependency products minimize demand while sharing parsing; token positions must survive transport for semantic equivalence. |
| Substitute worker mechanism | Stdlib and Loky can implement the complete contract; their real differences are assessed below. |
| Worker exception/exit/timeout/interruption | Page diagnostics and actual child settlement remain independently exercised. |
| Activate/close recorder, or start late | Live consumer controls optional work; acquired identity and unavailable optional evidence remain distinct. |
| Commit/rollback/clone disposal | Each selectable lifecycle control owns its positive premise/observation, including exceptional rollback and committed cross-session visibility. |
| Recreate temporary staging on one backend | Stable scalar/JSON/durable-row transport removes the ephemeral-type dependency; final18-case native selection passed. |

## 6. Independent correctness and fidelity gates

| Gate | Verdict and own evidence |
|---|---|
| G1 Authority | pass: original inputs, independent readings and production guards retain separate owners. |
| G2 Fidelity | pass: corrected transport preserves all token positions, relation endpoints, source meanings and absence distinctions. |
| G3 Validity | pass: valid siblings and single-fault cases identify intended native guards rather than setup refusal. |
| G4 Hidden behavior | pass: explicit preparation, live-sink observation and declared work-time multiprocessing reduction. |
| G5 Consistency/recovery | pass: stable native representation, repeated same-session rollback/recreation control, and owned native/worker cleanup. |
| G6 Transformation/reuse | pass: full-position math transport and stable native row representation preserve required behavior across reuse. |
| G7 Truthful claims | pass: identity completeness is narrower than deployment reproducibility; focused results and empty Rust selection remain scoped. |
| G8 Library leverage | pass: established fixture/executor/database/renderer/CLI mechanisms with bounded adapters. |
| CI-G1 Fidelity | pass: source/derived/private/accepted and unavailable/absent remain distinguishable. |
| CI-G2 Evidence closure | pass: exact source/member/custody binding; unbound historical receipts cannot satisfy current required native identity. |
| CI-G3 Evaluation integrity | pass: expected readings and references remain outside producer candidate derivation. |

## 7. Findings and disposition

Current status belongs in the resolution coordinator, not this report.

| ID | Diagnosis, correction and closure evidence |
|---|---|
| TR10-F01; DTA-018 / TR-02 | Staged Lark1.3.1 Token pickle dropped terminal end positions, changing relations/T2 reopening despite equal values/mentions. DP-07/08/15/23, G2/G6. Corrected by a narrow native multiprocessing reducer and lightweight initializer. Explicit eight-field nested/bidirectional checks, independent terminal bounds, direct/staged Normal data and original corpus/scope answers passed in the28-case selection. |
| TR10-F02; DTA-001 / TR-03 | Combined native selection produced XX000 for a missing type OID instead of the intended refusal. Source transports a temporary composite into a cached PL/pgSQL record field across recreated staging; this is the identified structural cause, with the baseline-pass limit below. DP-08/09/19/23, G5/G6. Scalar staged columns, JSON projection and conversion into the durable publication row type remove that dependency. Exact typed joins, every left-side staged row, multiplicity and canonical identity checks remain. Migration152 plus descriptor pin are implemented; final18-case native selection passed, including repeated same-session valid/rollback/recreate/refusal loops. |

No additional material architectural finding was established in the inspected assembled scope. These
focused closures do not discharge the remaining required functional/provider/nonfunctional union.

## 8. Library fit and enabling mechanisms

Context7 and exact installed sources settled consequential transport and plan-cache details. Lark's
Token constructor accepts all eight fields; installed1.3.1 `__reduce__` preserves only five. Token/tree
equality does not establish positional fidelity. `Lark.save/load` serializes compiled parsers, not the
finished token data needed here. The selected reducer reuses Token construction without reparsing.

CPython3.14.10 `multiprocessing.reduction.register` extends ForkingPickler. Parent registration and the
worker initializer cover both directions. It is process-wide/idempotent and leaves ordinary pickle
unchanged. The fixed lossless representation carries no scenario/source/reference state. No competing
reducer was found in the searched repository scope. Its process-wide effect is explicit, not claimed
as executor-local isolation.

Loky is a complete credible alternative. Installed Joblib1.6.0's ProcessPoolExecutor accepts
`job_reducers/result_reducers`, an explicit spawn context, and `shutdown(wait=True,kill_workers=True)`;
its custom picklers scope reduction per executor and shutdown kills its worker tree. Narrower dispatch
is a real benefit. It also selects an additional executor/serialization provider, direct dependency
ownership and a different shutdown/configuration route. Stdlib is acceptable here because one fixed
lossless representation applies coherently to all multiprocessing Token transfers, with no required
competing policy. Revisit for competing policies or required executor-local isolation. Restoring private
dispatch state temporarily would introduce races. No claim is made that Loky lacks this capability.

Pytest dependency/finalizer lifetimes, SQLAlchemy physical-connect events, PgAdmin ownership and Psycopg
diagnostics fit the remaining responsibilities. pgTAP/isolationtester do not replace these Python and
actual-purpose integration claims. PDFium/Pillow provide the real pixel oracle; LinkML provides the
structured process/report contract. No new generic scenario/worker/observation framework is needed.

PostgreSQL18 plan caching requires record-field types to remain stable across calls. The correction
uses scalar staged columns and JSON before filling the durable publication row type. Added scope fields
`release_id/realization_id` are excluded from content equality because r/z and the existing run/cut
checks own scope. Dynamic EXECUTE, reconnecting or cache flushing would manage the incidental temporary
type with repeated work. The append-only migration follows existing prospective authoring/admission.

Primary references: [Token](https://lark-parser.readthedocs.io/en/latest/classes.html#token),
[Python3.14 executors](https://docs.python.org/3.14/library/concurrent.futures.html#processpoolexecutor),
[Loky API](https://loky.readthedocs.io/en/stable/API.html),
[PostgreSQL18 plan caching](https://www.postgresql.org/docs/18/plpgsql-implementation.html#PLPGSQL-PLAN-CACHING).
Repository orientation: parsing/lark.md §6.2/6.3/10.3 and the Python concurrency overview §4.4/11.2.
Later-version Python features are not attributed to installed3.14.10.

## 9. Alternatives and tradeoffs

Explicit ordinary builders replace cross-host interception without introducing a scenario registry.
Independent tier rebuilding repeats parsing; lazy mutable scope properties hide effects. Session
fixture edges preserve demand and reuse. Reparsing or a second serialized tree protocol would repeat
work or add another representation contract; the native Token reducer fills the actual library gap.
Loky remains a valid scoped-policy alternative with the complete tradeoffs above.

Native validation continues to own exact semantic authority. A stable row representation resolves its
physical lifetime problem without changing grading/admission meaning or weakening grants. Frozen
historical configuration, independent source expectations, actual commits and real cleanup remain
preservation constraints on these simplifications.

## 10. Verification, preservation and limits

**Interface-checked,2026-11-05:** source/caller review and final AST reconciliation. Three intentionally
replaced order-dependent db-fixture names were removed. The integrated PDF control was renamed to
`test_integrated_preparation_and_native_task_fences_are_explicit`, retaining/clarifying its assertions.
Other existing authored test functions remain. Frozen references, old migrations, cold compiler, real
SDK stdio and production serializer controls remain; source retention is not fresh runtime qualification.
No manifests/locks, .cargo configuration or frozen reference bytes changed in the scoped diff.

**Interface-checked,2026-11-05:** wrapper hashes match all three new migration products; the frozen
validator statement exactly matches authoring SQL. The two native transitions are the validator and
its derived execution descriptor; no ordinary DDL and no old migration edits. The descriptor trust pin
changes with its generated descriptor. Final source formatting of previously focused math/native
infrastructure was re-read and is semantically unchanged.

**Focused passed,2026-11-05; producer results inspected:**

- Native lifecycle39: `uv run python scripts/test_receipts.py run --out-dir build/test-receipts/tr-native-lifecycle-final-focused --python-only -- python/corpus-structure/tests/test_db_fixtures.py python/corpus-structure/tests/semantic/test_native_fixtures.py -q`.
- Classifier/observer24: `uv run python scripts/test_receipts.py run --out-dir build/test-receipts/tr-native-receipt-classifier-final-focused --python-only -- tests/scripts/test_test_receipts.py -k 'rust or native_observation' -q`.
- Math28: `uv run python scripts/test_receipts.py run --python-only --out-dir build/test-receipts/tr02-math-lightweight-adapter-final -- python/corpus-structure/tests/math/test_workers.py python/corpus-structure/tests/math/test_spans.py python/corpus-structure/tests/math/test_scope.py python/corpus-structure/tests/math/test_property.py::test_corpus_layer_on_the_spike_pages`. Reporting/owned-group cleanup complete.
- Native15218: `uv run pytest python/corpus-structure/tests/semantic/test_local_semantic_admission_native.py::test_native_rejects_forged_judged_semantic_rows python/corpus-structure/tests/semantic/test_local_semantic_admission_native.py::test_writer_cannot_prepare_consolidation_by_direct_run_status_update python/corpus-structure/tests/semantic/test_local_admission_native.py::test_native_local_witness_refusals_rollback_receipt_and_all_rows > build/test-receipts/tr03-native-rowtype-final.log 2>&1`. Ten judged-semantic mutations, one direct writer status-update42501 control, seven local-witness mutations. Valid siblings are internal, not another separately counted node. The unit case repeats eight same-session valid/rollback/recreate/refusal loops with forced generic planning.
- TR-05 actual CLI/render/artifact results remain at their original source conditions in the coordinator; actual artifact receipt: `qualification/tr05-region-artifact-20261105`.

**Important limit:** original combined default-plan `tr03-04-focused.log` produced18 passed/1 failed
with XX000 in the unit case. Isolated OLD151 command
`uv run pytest 'python/corpus-structure/tests/semantic/test_local_semantic_admission_native.py::test_native_rejects_forged_judged_semantic_rows[unit-judged_source0-private_source0]' > build/test-receipts/tr03-semantic-cache-repeat-reproduction.log 2>&1`
passed its eight-loop forced-generic control. It did not deterministically reproduce the baseline failure.
Attribution follows the observed error, source structure and PostgreSQL record-field caching contract;
no deterministic failing reproducer is claimed. Revision152 removes that structural dependency and its
full18-case focused selection passed. Initial math failures, heavy-initializer deadline failure, native
diagnostic mismatches and the XX000 failure remain retained, not relabelled as passes.

**not_run by this reviewer:** product/provider/native tests, database/probes, just test-all/hygiene and
integrated qualification. Required-union accounting, migration/head applicability across the complete
consumer set, actual opt-in auth crash controls, provider/prerequisite outcomes, and truthful empty Rust
selection remain with the coordinator. No numerical performance improvement is claimed. Focused results
above are not an all-green broad qualification recipe or full-series completion.

## 11. Authority changes and dispositions

No rule impact, §B change or new architectural authority is recommended. The corrections preserve
existing source, admission, privilege and frozen-history contracts. Descriptor-pin/migration changes
carry the implementation repair through the existing owner, not weaker admission. DTA/TR10 finding
disposition and complete acceptance remain in the resolution coordinator. Production scientific quality,
provider/adoption campaigns and unsupported historical Notice/T3-D1 meanings are outside this engagement.

## 12. Architectural judgment and decision

| Judgment | Verdict and scope |
|---|---|
| A1 Localize change | satisfied: explicit preparation/reference/lifecycle owners and bounded native correction. |
| A2 Encode domain meaning | satisfied: source, stage, evidence, identity and lifecycle distinctions govern supported behavior. |
| A3 Extend through composition | satisfied: ordinary functions/fixtures and established worker/native primitives suffice. |
| A4 Execution fit | satisfied: demand-shaped reuse, lightweight startup, inactive guards and stable native representation avoid unnecessary work while retaining assurance. |

**Accept** the assembled test architecture and bounded native correction for these change/failure
scenarios. TR10-F01/F02 have coherent implemented corrections and focused evidence for the diagnosed
failure mechanisms, with the baseline reproduction limit above. No material architectural finding
remains open in this review. This enables final required-union qualification; it does not establish
complete runtime acceptance, measured performance or enclosing production/scientific architecture.
The coordinator owns final source applicability, remaining outcomes, hygiene and the completion decision.
