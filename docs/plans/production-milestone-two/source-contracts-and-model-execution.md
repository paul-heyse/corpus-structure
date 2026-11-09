# M2 source contracts and model execution

**Foundation implemented · 2026-11-08.** Owns PM2-01 and PM2-02, realizing source review
[O01](../../functional_reviews/production-milestone-two_2026-11-08.md#O01) and
[O08](../../functional_reviews/production-milestone-two_2026-11-08.md#O08).
The [coordinator](../production-milestone-two_2026-11-08.md) owns disposition.
The provider companions own their task semantics and native-specific limits.

<a id="PM2-01"></a>

## PM2-01 · Map native observations to retained source

Consume the release-qualified `native-section-text-v10` view, its prepared layout,
exact native product, ordered field addresses and pieces, synthetic separators and
protected atoms. Preserve the selected `text` or `orig` field on each native piece.
The projection and anchor owners determine this field choice. Retain each request's
selected scope and ordered provider-to-layout map. For HanLP and Maverick, bind canonical
tokens to the effective model tokens and their containing sentence. For Dipo, map
native text and EDU boundaries through the actual parser input. For d1, map the
serialized evidence strings and any media transform. Keep each coordinate space
named at the consuming boundary. Provider rendering, label normalization and source
coordinates are distinct. Preserve valid disjoint extents. A boundary inside an
indivisible protected atom, a fabricated synthetic span, or an ambiguous mapping
can produce a diagnostic with its input scope. It cannot supply an exact witness.

Use existing native source publication and detached completeness replay. Bind the
archived consumer policy to the selected projection and share one authenticated proof
per native product across views and providers. The current exact-closure evidence
covers view 382 at cut 517 under its recorded bounds. Preserve supported historical
reads under their own recipes. Current provider inputs use the current released
projection. [DMA projection and formula witnesses](../domain-model-alignment/source-projection.md) ·
[Portable verification](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py)

Use existing retained operation, report, and contribution contracts to express
scope, native result and alignment availability. Reuse their vocabulary and
introduce a new released field or type only for a distinction that the consumers
cannot otherwise express. Carry native coordinates, native label scheme and score
kind, including explicit unavailability. Preserve ineligible, eligible but
unscheduled, limited, failed or cancelled, successful empty, and successful
nonempty outcomes and their reasons. Scope coverage and output availability are
separate. The same operations handle the selected source and a different source
profile. Vocabulary, criteria, operation applicability and admission come from
the existing release and pack authorities.

**Transformers integration.** At Transformers 5.22.1, inspect and use the selected
backend's `BatchEncoding.word_ids`, `sequence_ids`, `token_to_chars`, or returned
offset mapping as appropriate when the provider exposes those encodings. With
pretokenized text, verify whether character offsets are local to the supplied token
and use word IDs and the canonical map where required. Special/padding entries and
pieces across synthetic seams never obtain source authority from offsets alone.
Use explicit provider maps when wrapper normalization, injected speaker tokens,
parser text preparation or the d1 renderer changes the input. Check exact ordered
round trips with repeated text, Unicode, whitespace, protected atoms, sentence
boundaries and omitted pieces. Keep tokenizer revision, normalization, padding,
special-token, overflow and truncation semantics in the relevant profile or input
identity. [Transformers guide §§3.1–3.3](../../libraries/parsing/transformers.md) ·
[Transformers 5.22.1 tokenizer source](https://github.com/huggingface/transformers/blob/v5.22.1/src/transformers/tokenization_utils_base.py) ·
[Canonical layout](../../../python/corpus-structure/src/corpus_structure/ingest/sentences.py) ·
[Source anchor owner](../../../python/corpus-structure/src/corpus_structure/semantic/source_contexts.py)

**Reuse.** Bind operation version, scope, actual source and prepared input, model,
tokenizer/renderer, task order and definitions, candidate order and definitions,
effective inference settings, and exact runtime to the existing dependency projection.
Retain durable outputs at the semantic boundary that consumes them. A new downstream
interpretation, mapping from retained coordinates, or admission rule can reuse the
same upstream work only when its actual determinants and release compatibility
permit. A changed input, requested head, representation, question or effective
runtime invalidates the affected provider operation. Preserve exact producing
origins. An evaluation-reference compatibility finding does not license producer
reuse across releases. [D6 local publication and reuse](../../design/D6-orchestration-metrics-policies.md)

**Closure.** Independently specified source slices round-trip through all four maps.
Keep the p416 and p418 original-spelling Reader, search and packet checks at their
explicit work bounds. Native publication and detached replay refuse omitted or reordered
required fields, substituted occurrences, and unauthenticated exclusions.
Wrong-source, partial-atom and fabricated-offset controls yield inspectable typed
outcomes and no exact witness. A changed downstream rule can consume unchanged
eligible provider outputs, and a changed effective provider input cannot. Use a
second vocabulary and policy fixture through the same entry points. Freeze the
public read and interpretation dependencies for the early PM2-08 journey. Shared
shape work can begin against PM2-00's source inventory while provider-specific
coordinate details are qualified under each profile.

<a id="PM2-02"></a>

## PM2-02 · Qualify and operate the native provider profiles

Use current run-owned task admission, fencing, worker cleanup and retained receipts.
The existing claim renewal retries once after a retryable lock or statement timeout
and confirmed rollback while the same running attempt still owns
sufficient lease time. Keep that retry at the claim boundary, distinct from a new
provider attempt. Preserve completed scopes when ownership expires or is reassigned.
[Claim lifetime](../../../python/corpus-structure/src/corpus_structure/semantic/claim_lifetime.py)

Each provider runs its native entry point in its exact compatible environment.
Use a separate lock where package or interpreter compatibility, resource isolation,
or cancellation requires it. Keep the application on CPython 3.14.10. Begin with
the reference settings from PM2-03–05 and PM2-07. Their exact lock and qualified
scope are outputs of this package. Preserve GLiNER and contextual embedding profiles
as current CPU baselines. Start with at most one M2 GPU profile resident at a time,
coordinated with the existing host device lifecycle. Reuse a loaded instance across
bounded batches. Preparation, loading, batching and scoring stay outside database
publication transactions. Keep an explicit CPU smoke/reference route where it
qualifies and record its distinct runtime. Unavailable GPU or model assets yield a
typed prerequisite or attempt result through the existing operations.

**Artifact and runtime selection.** Start from the pinned installed Transformers
5.22.1 where compatible. The [Transformers guide](../../libraries/parsing/transformers.md)
covers 5.22.2, so verify each relied-on behavior for the selected lock. In the
5.22.1 AutoModel path the requested Hub revision is resolved for model assets, with
a separate `code_revision` route. Pin config, tokenizer and processor explicitly
when wrappers resolve them separately. Stage verified artifacts offline for routine
execution, including transitive model files and reviewed code where a custom model
requires it. Keep the trust decision for executable model code or serialized Torch
checkpoints at provisioning. Verify startup against the loaded assets and runtime,
including model/head identity, `dtype`, active attention implementation and
input conventions. Use the same retained profile and invocation identity, with
diagnostics where supported. Inspect the native model's forward and wrapper before
requesting `attn_implementation` or a placement change. Those switches cannot
be presumed to preserve a custom decoder, d1's attention or multimodal processing.
[Transformers 5.22.1 AutoModel source](https://github.com/huggingface/transformers/blob/v5.22.1/src/transformers/models/auto/auto_factory.py) ·
[Transformers guide §§2.3, 4.3, 5.2, 6.1, 7](../../libraries/parsing/transformers.md)

**Bound actual work.** Preflight individual requests before packing. Qualify
sentence/subword and decoder limits for HanLP, post-tokenizer and mention limits
for Maverick, window/EDU limits for Dipo, and fully packed row and padded batch
limits for d1. Exercise a cold load, representative warm work, mixed lengths and
the first oversized boundary with the model's real tokenizer and decoders. Start
with eager native inference, including the checkpoint's required attention path.
Check GPU diagnostics and an actual native load. The review's failed NVML query
and positive Torch availability flag establish neither the operating envelope nor
device incapability. On interruption, release device/attempt resources and keep
completed scopes eligible for exact reuse. A retry may reduce only physical
batch size under the same effective input. A changed scope, inference setting or
device records a separate effective attempt. Avoid loading one model per clause
or launching separate workers for heads that already share native work.

**Choices and closure.** A second scheduler, generic Transformers pipeline, or
continuous generation batching would duplicate custody or bypass native
segmentation and typed outputs. Revisit a precision, compiler, attention kernel,
alternate runtime, export or co-resident profile only for a recorded operating
problem, with matched native outputs and the relevant decision or calibration
checks. Under each initial profile, record exact dependency locks and artifact
hashes, a working native grounded output and explicit accepted bounds. Verify
failed load, over-limit single input, cancellation, bounded retry, persistent
contention, expiry and reassignment. Verify preservation of another provider's
completed result. A proposed profile may remain blocked
with the missing asset, compatible lock or device prerequisite recorded. Only
its dependent scope waits. [D6 orchestration and GPU sharing](../../design/D6-orchestration-metrics-policies.md)

## Foundation execution evidence

**PM2-01 · Implemented and tested · 2026-11-08.** The provider bridges retain their native coordinates,
use the authenticated layout and protect indivisible atoms, synthetic gaps and
distinct source pins. The retained result keeps native answers, exact selected
projection evidence and the reason when canonical occurrence identity is
unavailable. The task determinant covers operation version, ordered effective
request, allowlisted d1 field, source map and exact runtime profile. The private
claim adapter uses the existing maintained owner, terminal completion and Reader.
The selected source and alternate vocabulary share this path. An actual d1 CUDA
answer and a limited sibling operation settled through maintained claims and
reopened through the private Reader. Exact same-release reuse survived a changed
downstream policy. The changed allowed field produced a new task.
[Native Reader and reuse receipt](../../design_review/evidence/2026-11-08_pm2-foundation/records/pm2.private-native-reader.json)
[Source maps](../../../python/corpus-structure/src/corpus_structure/methods/pm2_source.py) ·
[Result binding](../../../python/corpus-structure/src/corpus_structure/methods/pm2_result.py) ·
[Claim adapter](../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2.py)

**PM2-02 · Passed for the initial development profiles · 2026-11-08.** The resident supervisor
holds the shared local device slot through native child teardown. Each runtime
uses its exact interpreter, locked dependencies and verified offline artifacts.
The profile evidence covers all four CUDA models, actual admitted bounds,
persistent capacity contention and d1 native cancellation with restoration of
the configured incumbent service. HanLP and Dipo also produced grounded source
locations on the two frozen scopes. Maverick's two frozen arms returned empty.
Its separate alternate-vocabulary case returned grounded mentions and clusters.
[Profile results and exact locks](../../design_review/evidence/2026-11-08_pm2-foundation/README.md#locked-native-profiles) ·
[Resident supervisor](../../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py)

Provider-specific semantic consumers begin in PM2-03–07. PM2-08 owns the
assembled private Reader and MCP journey. Retained PM2-02 operating limits
apply to the tested profiles on the development host. The mixed-profile journey preserved the settled d1 result while an expired Dipo
attempt refused and the new owner settled the exact request. Shared claim-owner
checks cover the bounded renewal retry and attempt fencing. The provider
companions own extended scopes, and PM2-12 owns selected-release qualification. The native scope and outcomes are separate
from a claim of textbook benefit.
