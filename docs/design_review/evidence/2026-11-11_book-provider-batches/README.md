# CPU provider batch correspondence

**Tested, bounded panel · 2026-11-11.** BEP-06-I1/I3; outcome **partial**.

Commands and hashes are in [the record](records/bep.cpu-batch-regroup.json).
Actual workers used staged build/models/pm2 assets, CPU,4 native threads and interop1 for PM2;
GLiNER used the existing statistics M1 profile,4 threads and its pinned Base snapshot.
HanLP2.1.7, Torch2.15.0 and Transformers5.22.1 identities and artifact digests are retained
in raw startup/output data. All processes were closed by their existing owners.

## Results and inference-identity consequence

Three original members (short text, longer text, equal short text under a distinct context) were
requested individually, as a mixed batch, in reversed order and in two regrouped populations.
[Summary](raw/summary.json) compares each member to its original singleton independently.
There were no discrete output/cardinality/token/source-relative-position differences in this
panel. HanLP and D1 replies were exact. GLiNER confidence differed by up to
2.384185791015625e-7, despite unchanged selected label/text/extents. Therefore arbitrary
batching cannot be represented as byte-identical GLiNER computation. The coordinator must
choose qualified numerical semantics or freeze deterministic cohorts before task formation;
timing must not silently choose persisted inference determinants. This is no universal
threshold-safety or grouping-equivalence claim. D1 within-request set_size16 was unchanged.

Mixed HanLP admission retained a valid sentence while refusing a257-word sibling. D1 retained
one valid result while refusing a17-question sibling. GLiNER's malformed/overlimit siblings and
production cue/classification packs require their owning integration controls; this probe used
a finite statistic-entity schema to examine native batching behavior. Equal text still had
distinct GLiNER context IDs; word/subword/head output is retained for HanLP.

## HanLP prepared-sample decision

Installed service sources under services/pm2-hanlp/.venv/lib/python3.14/site-packages/hanlp/
components/mtl/multi_task_learning.py459–568 show predict rebuilding samples/dataloader;
its kwargs are unused. The MTL build_dataloader method114–154 serves training/evaluation.
No selected public prediction hook accepts previously prepared samples. Reimplementing its
task graph, reorder/finalize and native gradient handling is not selected. Keep native inference
preparation while using the actual task's bulk dataset preparation for bounded admission.
The producer's prepare_bulk path returns per-original-member lengths/limits; no sentence splits.

## Limits and preserved attempts

Probe execution is not a throughput benchmark, full production-family qualification or proof of
arbitrary numerical equivalence. CUDA, actual cross-region lane cancellation/crashes, replay and
complete source mapping remain with their owning BEP checks. The first D1 interpreter guesses
were absent, and the first GLiNER probe referenced a nonexistent report property; those probe
failures remain in raw logs. Corrected probes completed successfully with root .venv for D1,
service .venv for HanLP and existing root GLiNER worker. No production or model file was changed.

## Production cue/function pack extension

**Tested2026-11-11; bounded question passed.** The
[production-pack record](records/bep.production-gliner-exact-operations.json) retains exact commands,
input hashes, native outputs and actual shared authentication/projected classification decisions.
Current characterization questions were compiled through compile_question_families/declared_families.
The cue entity schema and character_gliner_function_v1 multi-label schema use their original
instructions, option criteria, pack versions, threshold0.5 and flat overlap policy. CPU inference
uses the selected Base snapshot with4 threads, standard attention and float32.

Seven singleton/mixed/reversed/regrouped groupings per pack produce26 original-member responses.
All26 pass authenticated_gliner_report with exact context, full batch commitment and member ordinal.
Equal text under distinct contexts remains separately attributed. All literal half-open extents
match their original source strings independently. Every classification result passes
classification_product and its selected labels match the exact offered-label order and unrounded
native confidence >=0.5. Cues are exact across this panel; function labels/cardinality agree while
confidence varies by up to3.5762786865234375e-7. No epsilon or score rounding is introduced.

This supports the selected explicit native float32 batch-observation semantics: retain each actual
attributed response and exact threshold decision, allowing batch-induced numerical variation.
It does not promise arbitrary near-threshold label stability or bitwise invariance. These native
observations say nothing about whether the model's extracted roles or function labels are correct.
Actual DB-backed source context/provenance and lane cancellation/crash behavior remain separate
integration obligations; the probe uses original whole strings with distinct context identities.

The initial attempt used M1Config's120 integer timeout directly. Production ClassificationProfile
normalizes timeout to120.0, which changes the profile fingerprint despite identical inference.
The shared validator properly refused that initial report/profile mismatch. Initial outputs and
failure remain; the corrected run normalizes the production profile before launching the worker,
and all26 final members authenticate successfully. No production file was changed for this fix.


The final exact-operation record supersedes the first production-schema panel. Cue members bind
text.model_characterization/2 plus the family digest; function members bind the actual
extract.pm2_gliner_classification/2 plus its family digest. The earlier panel used the cue prefix
for both, which cannot alter native model input but was not the exact classification header.
Its original outputs/record remain. The exact-operation rerun retains the same numerical findings
and all26 final members pass shared authentication and classification threshold projection.


## Actual lane/coalescer lifecycle controls

**Tested2026-11-11; eight bounded scenarios passed.**
[Lifecycle record](records/bep.actual-provider-lane-lifecycle.json) and
[independent summary](raw/lifecycle-summary.json) retain exact commands/results.
Actual ProviderExecution runs candidate coalescing explicitly selected for HanLP/GLiNER,
with existing staged CPU models and four native threads. The gate waits at the real reply-read
boundary after request transmission; GLiNER completes its separate native preparation exchange
before the gate targets actual extraction. Native replies are never fabricated.

For each provider, one stopped in-flight borrower leaves its useful sibling correlated as request1
at the original two-member physical batch ordinal1. No ordinal is reused. The stopped response
remains private and confers no completion rights. Whole-operation stop and SIGKILL of only the
captured owned native child produce structured private errors and drain the owned scope.
All eight final runs establish the native child stopped/joined or its joined Process object closed,
and the shared owner byte budget returned tozero. No controller thread survives.

GLiNER also refuses a32769byte invalid logical request before queueing without disturbing a valid
already-pending request, and uses actual native member preparation to refuse a600word member
while admitting its useful sibling. The useful native report is source-1 at ordinal0 in the actual
one-member physical inference envelope. Those are distinct admission boundaries; neither invalid
member becomes a successful empty report or poisons the useful sibling.

This qualifies the selected CPU lifecycle paths, not DB lease/publication fences, CUDA or an
exhaustive provider-crash matrix. The initial HanLP probe used the root project rather than the
selected services/pm2-hanlp lock project; its valid refusal remains in raw diagnostics. Initial
GLiNER probe proxies omitted Connection.send used for graceful shutdown, and inspected already
closed Process objects incorrectly. Those probe-only failures remain, as do prior HanLP closure
outputs. Corrected final probes delegate the complete connection API and check actual joined/closed
ownership. No production file was changed to repair a probe.


## Corrected production overlap policy and actual projection

**Tested2026-11-11, passed; current production-pack qualification.**
[Exact nested-projection record](records/bep.production-gliner-nested-projection.json) supersedes
the earlier exact-operation panel. That earlier panel used flat for both packs; it remains limited
flat-cue native evidence and does not qualify production nested cues. Original outputs and claims
remain recoverable, with explicit supersession; no flat result is relabelled nested.

The corrected run calls the actual gliner_cue_request and classification_request factories on
owned ModelScopes from the existing source testfixture, assigning distinct SourceViewIDs11/12/13.
Equal text under views11/13 produces distinct actual NativeSourceContext identities. The exact cue
schema runs with NESTED and the function schema with FLAT, both threshold0.5, normalized production
ClassificationProfile, exact actual operation identities, current question instructions/options,
standard CPU float32 and four native threads. These exact parameters are retained per response.

All26 native responses were projected through actual project_gliner_cues or classification_product,
rather than only the shared report gate. An independent checker verifies52 resulting occurrence
extents: original source-view ID, nonsynthetic native pointer, half-open positions and literal text.
Classification assessed_scope is retained and selected labels use unchanged native confidence>=0.5.
Original batch cardinality/member ordinals/header overlap/threshold are checked in every grouping.
Nested cue outputs were exact in this panel; flat function confidence still varied by up to
3.5762786865234375e-7 with stable discrete output. No epsilon, rounding, arbitrary near-threshold
invariance or accuracy claim follows. Source fixtures exercise the real in-memory projection
contracts; authentic captured-source DB provenance and native publication/lease fences remain
separate integration obligations. I4's existing flat protocol panel remains lifecycle evidence,
not nested cue decode qualification.


## Final custody and source applicability

Root formatting and safe cleanup changed probe-source bytes after execution without changing
provider schemas, overlap policies, profiles, original inputs or assertions. Finalization refreshes
those input hashes; retained native/raw bytes are unchanged. Native runs precede the later lazy
admission repair. The coordinator judges native worker/lane/coalescer behavior unchanged, so these
receipts remain evidence for their stated native batch, projection and lifecycle questions. They
do not qualify the final scheduler's pre-hydration admission timing or retained-state behavior,
nor DB lease/publication fencing. Final integrated native qualification is separately root-owned.
No native rerun was performed during this custody-only refresh. Superseded flat-cue panels stay
superseded and are not relabelled nested. The existing raw/** Git LFS rule supplies raw custody.
