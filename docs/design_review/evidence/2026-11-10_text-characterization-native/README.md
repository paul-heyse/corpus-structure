# TC02 native characterization foundation

**Stopped at operator request; acceptance incomplete · 2026-11-10.** Implements the protected persistence/publication portion of
[TC02](../../../../docs/plans/text-characterization/model-and-retention.md#TC-02).
The coordinator owns combined acceptance. This record does not establish TC03 inference,
linguistic support calibration, release activation or run selection.
The [coordinator's bulk continuation](../../../plans/text-characterization_2026-11-10.md#stopped-checkpoint-and-bulk-continuation)
owns next work; the final stopped checkpoint below supersedes earlier pending-attempt wording.

The baseline development database is `corpus_structure_dev`, PostgreSQL18/corpus port5434,
exact native predecessor `semantic_dmc_completion_repairs`. `change.yaml` owns the requested
forward revision `semantic_tc02_foundation`; deployment and release admission are permitted,
activation and selection are outside this work.

## Realization

One canonical release-typed payload owns each immutable layer/view product. Independent physical
relations index occurrences and real extents, annotations, memberships, attributed roles, term
edges, analytical choice members and family coverage. Protected task completion fences the run,
attempt and holder, binds method/release/runtime/configuration/input and exact source closure,
and derives all indexed rows atomically. Valid reports can retain failed sibling families;
a failed analysis cannot create a layer seal. A real `text.compose_view` task can publish a
source-only view. Exact kind-qualified product pins do not require run completion.

Public reader functions authenticate the runtime purpose and exact source closure, optionally
check the requesting run's project, and expose indexed keyset pages before hydration. Payloads
and response bytes have explicit bounds. Stored physical tables have no direct runtime-reader
SELECT grants. Publication creates private analysis products, never knowledge admission.

Trusted physical imports now contribute explicitly marked stored relations; imported payload
classes remain values. The legacy relational compiler revision stays unchanged because its
legacy target has not changed. The trusted physical closure and model-change source fingerprint
bind the semantic-target change.

## Verification and retained managed operations

Every ID below remains in managed custody. Failed records are preserved, not replaced. Holds
were set with `uv run ci results hold ID --json` while this evidence is a consumer.

| Outcome | Command / managed ID | Scope or reason |
| --- | --- | --- |
| passed | `uv run ci db status --maintenance --json` | Verified2026-11-10: expected dedicated development target and predecessor |
| passed | `uv run ci test -- python/corpus-structure/tests/semantic/test_characterization_physical.py` · `8950c4c78d8e435eb441fbc43f262f48` | Imported physical projection and membership index |
| passed | `uv run ci test -- python/corpus-structure/tests/semantic/test_characterization_physical.py python/corpus-structure/tests/semantic/test_operation_call_generation.py` · `1eaa818d4ff446b0b3156be4b1f39925` |29 focused checks at that source |
| passed | `uv run ci test -- python/corpus-structure/tests/semantic/test_characterization_completion.py python/corpus-structure/tests/semantic/test_characterization_physical.py python/corpus-structure/tests/semantic/test_operation_call_generation.py` · `b604fed5ccdd40a2993b9113466c2cc1` |37 focused checks; terminal-product channel refusal, physical closure and generated calls |
| failed | `uv run ci test -- python/corpus-structure/tests/semantic/test_characterization_native.py` · `987ee95646444e649b2d1143339cfb2c` | Setup used the unregistered old native head, which correctly refused the new execution operation; no native product assertions ran |
| failed | `ci model change preview change.yaml --json` · `ab7bf8307277439ba1c0b33813add793` | Duplicate generated YAML anchor; corrected |
| failed | same preview route · `74367be6f90b458b89040ef95595aea7` | Missing approved implementation binding; corrected |
| failed | same preview route · `5e5351d6c6f345d1a7fa69024db78d0e` | Missing finite supported effect profile; corrected |
| failed | same preview route · `0076bc1792ed4bb9aae5ae7ccefd18d0` | Global legacy compiler revision bump was inappropriate; kept legacy compiler version4 |
| failed | `ci model change candidate f1636e99f8fd4d6989eef474d1ccf138 --json` · `e2f6ed9954714113a06b13efc77c7139` | Rollback-only native authoring completed; candidate publication refused an overlong revision ID; corrected to `semantic_tc02_foundation` |
| failed | `ci model change candidate 7c78c7982ec841e9a9f843edf6e7ff9a --json` · `f57f3416239c4ec19dcbf58ce86d4d56` | Exact preview correctly refused generated calls changed after preview |
| failed | `ci model change candidate 19bae5ad5af444ab90be7cecb2cc2e37 --json` · `7938dc34c8a44faaadcaf7a327b4abc1` | Prepared release changed while concurrent final corrections landed; refused before database effects |

The last identity diagnosis called the owning `_prepare_release` with both explicit trusted
physical closure and its default acquisition in one process: both yielded
`release:3ffc15eda73bf450f7884c8860a1b43f3c38649773862b48c0b7764348db92e0`, with equal
manifest and artifact digests (observed2026-11-10). This was an acquisition diagnostic, not a
native deployment or qualification result.

Native tests require the registered frozen migration head. Final migration authoring,
registration/deployment and the final native result are pending below. The root owns full
functional/repository qualification after source maintenance.

Additional retained attempt `288459acc6784d6d813777b53f97a5f1` failed in test setup because
an existing test helper invoked a nested Alembic `ModifyTableOps` container as a leaf. The local
recursive test candidate adapter subsequently traversed operation containers. That attempt
`7a46990cf95c437f872807cde0207510` was independently refused during setup because temporary
deployment differed from frozen migration admission. Both adapters were removed; the tests
require the authoritative registered migration. Neither attempt modified the development
database, and both failed attempts are held unchanged.

## First registered forward deployment

`ci model change preview change.yaml --json` passed as
`641d1e6be39f4d98bb525bb8d962c614`; its prepared release is
`release:802cb26342921d5b799d8e032fe5746d175ab4ef8a40c4d13272cb84a34e407a`.
Candidate `0a18054ef8c3410f8227db17429b0d70` passed rollback-only authoring with23 native and36
ordinary operations. Its summary and complete operations were read through
`ci model change inspect-candidate`. Registration passed as
`42217a89c488423291f52c8fcba819ba`, writing the four frozen
`python/corpus-structure/semantic_alembic/versions/semantic_tc02_foundation*` files.

`ci model change deploy 0a18054ef8c3410f8227db17429b0d70 --json` **failed** as
`50705736ab7647cba2a91239efb94ad3`. Its actual effects are **migration and archive persisted**:
`ci db status --maintenance --json` subsequently reported revision/head
`semantic_tc02_foundation`, and `ci release check --release release:802cb26342921d5b799d8e032fe5746d175ab4ef8a40c4d13272cb84a34e407a --json`
passed immutable archive verification on2026-11-10. The deploy failed native admission because
characterization boundary classes lacked the existing private-product placement marker, so
shape regular expressions entered the generic graph/native constraint collection. Archive
integrity is not native admission. No activation or selection occurred. The classification
correction and an exact-predecessor successor are still required.

The failed candidate `a5382a24b3b14c00bcb0c02c5e858ce1` was refused before effects when the
product-reference docstring changed after preview. It is held unchanged. All subsequent
tracked semantic source changes, including formatting, require a fresh preview.

## Classified private products and exact byte limits

The declaration correction marks the characterization boundary family under the existing
`SourceRecordProduct` placement marker. It keeps boundary shape constraints in generated/native
JSON Schema validation and excludes those private shapes from generic graph property
applicability; the generic native regular-expression policy was not weakened.

`products.yaml` owns the successor from `semantic_tc02_foundation` to
`semantic_tc02_products`. Preview `5efe00806c434b9c86e1c8311b13e77e` and rollback-only candidate
`5e1ff7c2f1274d8b8178566e55163261` passed. The reviewed four native operations change only
three reader byte preflights and the execution descriptor; there is no ordinary DDL. Reader
limits now measure exact canonical JSON bytes, rather than possibly compressed PostgreSQL
storage size. Registration `206f4304195c45c9a166ef8e16d45e5b` passed.

`ci model change deploy 5e1ff7c2f1274d8b8178566e55163261 --json` **passed** as
`bfea30140cab409eafb2d574f33e2a43`, reaching `semantic_tc02_products` and completing migration,
archive, admission and verification for
`release:c921ad244b60d4e79556a9042f102936a6d58c853c9c14f9c902c30bbfaca0e2`.
`ci db status --maintenance --json` confirmed that exact head, and
`ci db check --release release:c921ad244b60d4e79556a9042f102936a6d58c853c9c14f9c902c30bbfaca0e2 --json`
**passed** native correspondence against execution model
`execution:15ef4bb441f87154e566f6613f1b676222ac331e872a1b310408c32282855829` and physical model
`physical:25e00284c6df711ca4984084729ede3cdc391119efe61f49052cdc87f257ee34`
(verified2026-11-10). No activation or selection occurred.

The focused native test command is running as `878b4aaa546549a088a79ebf93e3d071`; its outcome
has not yet been accepted here.

Native attempt `878b4aaa546549a088a79ebf93e3d071` **failed** all four call phases before
publication: its existing observation-only fixture had no `AnnotationLayer` boundary. The
fixture now explicitly requests characterization via production `characterization_inputs`,
using a separate `characterization_pdf` test profile. Existing fixture profiles and assertions
remain unchanged. The failed result is held unchanged.

## Functional guard correction and bounded graph checks

Native receipt `bfaaa53ca00b4e7999823c9ac8af05a7` **failed** two composition/capture
cases while two publication/refusal cases **passed**. The first execution of the composed
view validator exposed PostgreSQL operator precedence in JSON containment operands. Both
source-scope operands are now parenthesized. The same forward correction replaces recursive
path enumeration with deduplicated `(owner,target)` reachability, preserves the published
membership order while using a distinct internal page position, and declares C collation for
portable keyset and local identifier ordering.

`guards.yaml` binds predecessor `semantic_tc02_products`. Final preview
`ecdd842b223e44d29bed73663cadce97`, candidate `df2267a7c8364706be544054f8b73b5b`,
registration `c3de62d05c1a42218f8c5c7e82b971cc`, and deployment
`cfffe8d21e534977b6ca01bc71272136` **passed**, reaching `semantic_tc02_guards` on2026-11-10.
The reviewed four native operations change the validator, indexed node and membership
readers, and execution descriptor; there is no ordinary DDL. The earlier two-operation
candidate `2e45e6a6d0054b809cda97576b588569` was not registered or deployed. The same
`release:c921ad244b60d4e79556a9042f102936a6d58c853c9c14f9c902c30bbfaca0e2` was admitted.
No activation or selection occurred.

The selected cross-release acceptance correction arrived after that candidate was registered.
`cross-release.yaml` owns a separate forward revision, preserving the frozen guard migration.
It permits a sealed V1 native layer under its original admitted archived release to be reused
by a new rule layer and composed view. Each enclosing product remains bound to its own
producing task release, and exact base/source/dependency pins remain mandatory. Unsupported
formats are refused. Functional qualification is pending this successor; no claim that the
current deployed guard head already implements cross-release reuse is made.

Cross-release preview `d557085c5bff4c7aad5f518a6c951780` passed, but its candidate
`ab74e318ed3647a983e3168cd70e5750` **failed** rollback-only authoring with SQLSTATE42601.
The new format guard required a parenthesized `CASE` expression inside PL/pgSQL `IF`.
The failed result is held. A direct diagnostic compiled every characterization function
in an explicitly rolled-back maintenance transaction after that correction; it established
SQL definition syntax, not runtime admission or functional behavior. A fresh managed preview
is required and underway; the failed candidate was never registered or deployed.

Corrected preview `512a8b7e7f8f49efa9fd3b65a6841281` and rollback-only candidate
`4c6fb00a7b374850b60dae99e0605c0c` **passed**. The exact reviewed three native operations
change only the characterization validator, pinned product reader and execution descriptor;
there is no ordinary DDL or ACL change. Registration `a9a7a5e41d1c4bbf8bb65df5a5f5204f`
**passed**, writing the four frozen `semantic_tc02_cross_release` migration products.
Deployment `af82f066c60743a48a00e1178868e7a6` is underway; its outcome is not yet claimed.

Deployment `af82f066c60743a48a00e1178868e7a6` **passed** migration, archive, admission and
verification, reaching `semantic_tc02_cross_release` with unchanged release c921. Both
`uv run ci db status --maintenance --json` and `uv run ci db check --release release:c921ad244b60d4e79556a9042f102936a6d58c853c9c14f9c902c30bbfaca0e2 --json`
**passed** after deployment on2026-11-10. A fresh seven-case native module is running as
`40970b26268e43098853321e22137690`; final functional outcome is pending. Existing same-run
unfinished reads remain a separate control from the cross-release fixture, which legitimately
completes R1 before selecting its original SourceView into R2 through the existing selector.

Native result `40970b26268e43098853321e22137690` **failed**: seven selected, one passed
(the invalid-refusal case), six failed at the same first-call graph expression. Its recursive
query alias `r` collided with the enclosing PL/pgSQL `ops.run` record variable. Both recursive
aliases now use `reach_`. The exact two expressions were executed in rolled-back diagnostic
`DO` blocks retaining that enclosing record declaration. This diagnoses the collision; it
does not replace protected native tests. The failed result is held. `reachability.yaml`
requests a separate forward successor from `semantic_tc02_cross_release` to
`semantic_tc02_reachability`, preserving every earlier migration. Preview
`7c30e1c4a3fd4e379221985698a1a4ef` passed; candidate
`ed668965a56f4c88b122db50bcbe9ea5` is underway.

Reachability candidate `ed668965a56f4c88b122db50bcbe9ea5` **passed**. Its two reviewed native
operations change only the validator and execution descriptor, with unchanged ACLs and no
ordinary DDL. Registration `0efd90c26a304f13ad3f5979cf560fc0` **passed**. Deployment
`b7f9e471e81644fe85769cdd12069d09` is underway; acceptance remains pending real protected
publication and consumer checks after deployment.

Deployment `b7f9e471e81644fe85769cdd12069d09` **passed** migration, archive, admission and
verification at `semantic_tc02_reachability`. Native correspondence for c921 also **passed**.
Fresh native result `3f98a01daa9b4059ad066da42ca6c2f7` **failed** three of seven selected
cases; four **passed**: protected publication/refusal, shared diamond DAG and cycle refusal,
and real unfinished-run capture with live/detached indexed pagination and page3/4 off-page
membership context. Two completion cases exposed strict tuple decoding of native JSON
`receipt.observation_ids`; the bridge now uses the existing canonical JSON validation route.
The cross-release case legitimately finalized R1 and then reached preparation of R2, where
the test helper reused global realization id `z`. That helper now accepts an explicit
realization id and the second release uses `z-new-rule`. No SQL guard or selection prerequisite
was weakened. The failed native receipt is held; affected consumer tests must pass on the
formatted corrected source before acceptance.

## Stopped checkpoint — 2026-11-10

The operator requested ending the turn and handling remaining work in bulk. Exact retry
`0a008697b02d4616b51f71a57133536f` had already started for the three unresolved native nodes.
The owning managed process was promptly canceled and drained to exit130; its supervisor
settled **interrupted** with three selected nodes. No background test remains. This receipt
is preserved, and no outcome for either corrected path is inferred from it.

Current development native head is `semantic_tc02_reachability`, deployed by
`b7f9e471e81644fe85769cdd12069d09`, with release
`release:c921ad244b60d4e79556a9042f102936a6d58c853c9c14f9c902c30bbfaca0e2` admitted and
native-correspondence checked. The latest completed full native module remains
`3f98a01daa9b4059ad066da42ca6c2f7`: four passed and three failed. The two corrections
(strict JSON receipt decoding in `PreparedUnitCompletion.apply`, and an explicit distinct
R2 realization id in the test helper/fixture) are implemented but **unverified**. Joint
layer/view completion, the full ordinary compose bridge, and the final cross-release new-rule
layer/view/capture path must pass on final source. Final broad checks and complete union
accounting remain with the coordinator. All worker production and test source edits are
frozen at this checkpoint; no activation, selected completed run or NLP invocation occurred.
