# Production milestone two foundation design review

**Decision · Accept scoped · Proposed · 2026-11-08.** Proceed with a frozen
private baseline, authenticated source mapping and the shared task boundary.
Use thin provider-specific bridges and explicit local profiles. Exact projection
evidence and physical occurrence identity have different promises. A mapped
answer may retain an exact selected spelling even when it cannot claim a native
physical occurrence. Native profile qualification, a selected release and the
accuracy of later composed claims each require their own evidence.

## 1. Scope and baseline

This design/target review covers [PM2-00–02](../../plans/production-milestone-two_2026-11-08.md#execution-queue).
The operator selected a combined focus on the HanLP, Maverick, Dipo and d1 native
mechanisms, source authority, reuse and execution fit. The reviewed source is
`9bdb0996e47d459b0be01e74ede4d2b5ec5c0b45`. The diagnostic input is
[the PM2 audit refresh](../audit/README.md#pm2-foundation-refresh). The standard
is core 3.3, heuristics 1.0, code-intelligence 1.4 and test-assessment 1.2 under
the [repository binding](../design_principles/binding/corpus-structure.md).
The reviewer is independent of implementation. Review method is static source,
contract and reference inspection with historical receipts for stated cases.

The workload is preparing real sections of a 518-page PDF and consuming bounded
sentence, section and focused evidence scopes. It includes uneven lengths,
protected layout atoms and concurrent local PDF/model activity on one device.
The same interfaces must accept running text and policy from another domain.
The textbook supplies an assessment corpus. Structural eligibility and versioned
release definitions supply operational behavior. This scope ends at retained
private evidence and its inspectable outcomes. It includes current Reader, search
and packet dependencies where exact source is promised, and excludes semantic
promotion, aggregate benefit, native production fallback and the assembled release.
[Functional target](../../design/DESIGN.md#section-1) ·
[Architecture map](../../design/README.md) ·
[Foundation contracts](../../plans/production-milestone-two/source-contracts-and-model-execution.md)

## 2. Responsibilities and fidelity

| Owner | Responsibility and change boundary |
| --- | --- |
| Native product, published source view and prepared context | The product owns the immutable native artifact. The view owns its exact recipe, ordered pieces and field choices. `NativeSourceContext` maps verified literals into those coordinates. A provider may prepare different input from them and must retain its transform. |
| Released operation and private contribution | The release owns applicability, definitions and accepted effect. The contribution owner verifies coordinates, producer/source correspondence and operation population. A physically identified occurrence additionally needs a canonical native or captured address. |
| Run, task and execution profile | The run owns selection, claim and result visibility. The task records effective determinants and terminal scope. The profile owns exact library, runtime, assets, inference settings and admitted bounds. |
| Consumer | Reader/search/packet follow pinned source and the applicable proof. Private contribution reads follow retained operation and source. Promotion and assessment use independently governed paths. |

**Implemented and interface-checked.** `map_span` enforces literal bounds and
rejects synthetic intersections. `read_span` has an explicit versioned whitespace
policy and represents a reading with pieces and gaps. `evidence_anchor` returns
selected-projection space by default. `PreparedNativeSource.native_field` requires
an unchanged complete native field before converting offsets to physical space.
The contribution `occurrence_identity` rejects selected-projection anchors.
Consequently a v10 `orig` piece with original spelling that differs from native
`text` may be exact in the selected projection and refuse the existing physical
bridge. Treat that refusal as an unavailable physical occurrence and retain the
selected evidence where its released contract permits. The two promises remain
separate even when a particular spelling agrees. [Source context and evidence
anchor](../../../python/corpus-structure/src/corpus_structure/semantic/source_contexts.py) ·
[Contribution binding](../../../python/corpus-structure/src/corpus_structure/semantic/contributions.py) ·
[Native source publication and replay](../../plans/domain-model-alignment/source-projection.md)

| CI fact family | Fidelity and identity | Coverage and consumers |
| --- | --- | --- |
| Selected source piece | Exact derived projection under product, view, recipe, field and ordered range. Physical occurrence identity is separately owned. | Exact coverage is confined to authenticated v10 selected pieces. Source consumers replay the appropriate recipe. |
| HanLP heads and spans | Inferred syntax, frames and constituency under the loaded model and native label scheme. Sentence-local heads and spans retain task and token correspondence. | Requested heads only, over admitted sentences. Generic argument roles and labels remain provider assertions for later interpretation. |
| Maverick mentions and clusters | Inferred ordered mentions and cluster partition under MES. Mention coordinates retain both inclusive native endpoints before translation. | Admitted coherent scopes only. Unscored, unresolved or unexamined links remain unknown. |
| Dipo EDUs and tree | Inferred post-merge boundaries, ordered child extents, nuclearity and relation under DMRST. Mapping to the selected source is a separate derivation. | Admitted running text only. Native discourse relations can guide context. A selected domain relationship needs its own witness. |
| d1 typed decisions and evidence | Inferred result under the exact checkpoint, renderer, question, candidate order and answer kind. A quote mapped from a permitted state field has separate exact source identity. | Actual admitted state and independent questions. Candidate text can inform a decision without becoming source evidence. |

## 3. Contracts and 4. Composition

**Proposed.** Compose authenticated prepared source → bounded provider request →
native result → checked mapping → private result completion → pinned read. The
worker handles native preparation and inference. The parent holds the claim and
publishes through `complete_unit_result`. `bind_contributions` checks actual
source text, identity, operation and local endpoints. No worker database custody
is needed. Record ineligible, eligible-unscheduled, limited, failed, cancelled,
successful-empty and successful-nonempty as distinct states. Input coverage and
availability of aligned output are independent. A valid disjoint extent may
retain ordered pieces when the role permits them. Partial atoms and fabricated
spans yield diagnostics. [Completion owner](../../../python/corpus-structure/src/corpus_structure/semantic/operations.py) ·
[Private read owner](../../../python/corpus-structure/src/corpus_structure/serve/contributions.py)

| CI operation and universe | Method and precision | Work, effects and evidence boundary |
| --- | --- | --- |
| Which prepared pieces constitute the requested scope? | Exact selected view, authenticated product proof and archived consumer recipe. | Share verification per native product and preparation per invocation. Select bounded ordered pieces without reconstructing the full product for each provider, view or cited span. Omitted required fields, reordered pieces and excluded content without proof refuse. |
| Which native observations were produced? | Scoped model input with actual prepared tokens or text, selected tasks and exact profile. Inferred output under that model. | Preflight singleton work, then pack compatible inputs. Reuse a resident instance for bounded batches. Record limits and omitted work before interpretation. No loading, waiting for the device or scoring inside a publication transaction. |
| Which source pieces can support a native observation? | Compose the provider map and source-owner map. Exact only after round-trip validation of ordered retained pieces. | Keep the operation and producing source pin. Cross-field or injected text, wrong source, ambiguity and synthetic-only support refuse with context. A later policy may use a valid retained result under compatible determinants. |

**Implemented.** `create_task` and `task_dependency_scope.sql` already own
reuse and its scoped exclusions. PM2 should retain the input, tokenizer or
renderer, ordered tasks and candidates, method version and runtime in existing
operation determinants. The source contracts allow reuse only where actual
upstream determinants and release compatibility hold. A change in a downstream
rule can consume unchanged work where that contract permits it. A changed
effective request or runtime needs a new producer origin. A successful evaluation
comparison cannot authorize reuse across release identities. [Dependency
projection](../../../python/corpus-structure/src/corpus_structure/semantic/sql/task_dependency_scope.sql) ·
[Task and reuse owner](../../../python/corpus-structure/src/corpus_structure/semantic/operations.py)

## 5. Scenarios

| Change or fault | Owner, propagation and deciding evidence |
| --- | --- |
| Apply the same operation to a procedure and a proof | This is a source instance and release binding change. The same layout, request, mapping and completion entry points should work. Vocabulary and admission change in the release. Unsupported language or lack of canonical sentences remains explicit. Independently authored fixtures must vary terminology and policy through those entry points. |
| Add a new fact family, such as a genuinely different relation | The release may need a new definition and affected consumers. Provider adapter changes are warranted for a new native shape. A second vocabulary or an already supported score kind needs no new domain operation framework. Keep unknown, insufficient evidence and none of the candidates separately typed. |
| Substitute a compatible tokenizer, model revision or physical runtime | A mechanism change belongs in its provider profile and map when coordinates change. Existing pinned output stays readable under its producing origins. Same-input native parity and new oversize/failure controls settle whether a new profile can be qualified. |
| Trace a private observation over repeated text, `orig`, or a synthetic seam | The view and mapper choose the exact ordered pieces. The contribution boundary checks its permitted anchor space. Reader/search/packet follow the original source recipe. Wrong item, partial atom, equal text at a different position and changed physical spelling need independent refusal controls. |
| Grow sections, mix lengths or interrupt one model during loading or IPC | Bound actual singleton work and batch skew before execution. Keep expensive preparation and native work outside publication. Cancel the child, drain it before releasing the device, and fence stale completions. Retain completed siblings and exact reusable origins. Confirm persistent contention and expiry/reassignment through run custody. |
| Pair cut 517 output with reviewed references | A selection or assessment change uses the evaluation owner. Compare only exact source and operation correspondence. References remain out of the model request and runtime profile. A sentence/full-view mismatch leaves acceptance open. |

## 6. Independent gates

| Gate | Verdict and basis at the proposed, scoped boundary |
| --- | --- |
| G1 Authority | Pass. Projection, physical anchor, operation and policy have distinct owners. Adapters transfer coordinates and native observations. |
| G2 Fidelity | Pass. The scoped contract preserves original spelling, native labels, score meanings and partial coverage. It explicitly excludes a physical claim where the bridge refuses. |
| G3 Validity | Pass for the proposed deterministic boundary. Existing source and contribution owners define rejection for wrong coordinate, invalid identity and unbacked contribution. Native coordinate conventions remain subject to per-profile qualification. |
| G4 Hidden behavior | Pass for the proposed boundary. Provisioning is explicit and inference is local to verified assets. Ambient downloads, code resolution and silent CPU or dtype fallback are excluded from supported operation. |
| G5 Recovery | Pass for the proposed private publication contract. Claim fencing and atomic completion own visibility. Native cleanup, interrupted model execution and physical attempt bounds remain unqualified. |
| G6 Transformation and reuse | Pass for the proposed source contract. Exact fields and transforms are pinned. Reuse follows actual dependency correspondence. Provider-specific and cross-release parity claims remain open. |
| G7 Capability claims | Pass. Development baselines, prospective profiles and evaluated selected output have separately stated scope and evidence. |
| G8 Library leverage | Pass. Native preparation, inference and decoders stay with selected libraries. Mapping and lifecycle code cover actual local custody gaps. |
| CI-G1 Fidelity | Pass. Provider assertions, derived mappings, physical occurrences and domain endorsement have separate contracts. Lack of coverage remains unknown. |
| CI-G2 Closure | Pass for authenticated baseline and proposed private contract. Exact source evidence can be replayed under the retained view or canonical occurrence where supported. Composed M2 claims and delivery are outside this decision. |
| CI-G3 Evaluation integrity | Pass for the proposed boundary. Independent references and transfer controls are separately owned and cannot supply request criteria, candidates or parameters. |

## 7. Findings and design principles

1. **PM2-R01 · Projected and physical evidence.** The current physical
   contribution path cannot identify every exact projected spelling as a
   physical occurrence. Preserve the existing guard. Carry selected evidence
   through the appropriate existing record or source scope, and retain the
   refusal in the private operation when physical occurrence is required.
   Require exact independent `orig` and `text` controls before stating closure.
   [PM2-01 disposition](../../plans/production-milestone-two/source-contracts-and-model-execution.md#PM2-01)
2. **PM2-R02 · Offline readiness and resource custody.** A manifest or
   positive Torch capability flag cannot settle native work bounds, trusted
   artifact completeness or cleanup. Start only explicit installed profiles.
   Keep absent assets and runtime failures inspectable per provider. Record
   real native output, local lock and file closure, first oversized refusal,
   and cancellation/reaping before claiming a profile. [PM2-02
   disposition](../../plans/production-milestone-two/source-contracts-and-model-execution.md#PM2-02)

**Proposed judgments.** FP-01 through FP-06 are supported for the scoped
composition by separated mapping, policy, worker and completion ownership,
explicit distinctions and isolated checks. DP-01–05, DP-07–10, DP-15 and
DP-18–24 are material here. FP-07 is supported for deterministic source work
under the current bounded private path. Native resource fit is unresolved.
Repeated product authentication and per-clause model loading would undermine
DP-10 and DP-20. Approximate transformations and precision changes require an
explicit profile and comparison under DP-11. Native APIs and thin bridge seams
satisfy the proposed DP-13, DP-14, DP-16 and DP-17 route.

## 8. Library fit and 9. Alternatives

**Interface-checked candidates.** Use each native provider entry point with an
explicit input profile and a checked source bridge. The pins below identify
initial candidates. Each operational profile still needs its exact environment
lock, artifact closure and native execution evidence.

| Profile | Native mechanism and configuration | Bridge and qualification boundary |
| --- | --- | --- |
| HanLP 2.1.7 | Use the `20250107_181612` ModernBERT Large MTL archive with its separately pinned ModernBERT config/tokenizer `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`. Request `lem`, `pos`, `dep`, `srl` and `con` together over canonical tokens with `skip_tasks="tok"`. Add `ner` when its own consumer requests it. | Check archive digest and complete state-dict loading. Verify sentence-local token IDs, one-based UD heads with zero root, spans and constituency yield. Bound real subwords and decoder work. Use one shared encoding across heads to avoid duplicate work. [Plan and exact pins](../../plans/production-milestone-two/linguistic-referential-discourse.md#PM2-03) · [HanLP mechanisms](../../libraries/parsing/HanLP.md) |
| Maverick 1.0.7 | Use `Maverick.predict` with nested canonical sentence tokens in bounded coherent sections. Stage MES OntoNotes `087a90f0380ec1f20ed19732b657f53fd3542c81` and separately resolved DeBERTa `64a8c8eab3e352a784c658aef62be1662607476f`. Isolate the CPython 3.12 dependency family and qualify the native forward seam. | Verify the checkpoint digest and deserialization. Convert both inclusive endpoints through the actual token map to half-open source pieces. Require correspondence for multi-subtoken endpoints and injected tokens. Preflight subtokens and mention work before dense scoring. [Plan and exact pins](../../plans/production-milestone-two/linguistic-referential-discourse.md#PM2-04) · [Maverick mechanisms](../../libraries/parsing/maverick-coref.md) |
| Dipo 0.2.1 | Use isolated CPython 3.12 and `DMRSTParser.predict_from_text` with `break_at_paragraphs=False`, FP32 and stride 100 initially. Stage GUM checkpoint `e33906a27f89b2703df8ab19e471aa82141d62cb` and Ettin `7662476d60abb071a5bd319c9f3074f3072c062d`. Retain the checkpoint's LoRA configuration. | Treat native checkpoint loading with `weights_only=False` as an explicit provisioning trust decision. Map final post-merge EDU boundaries through the recorded ordered input transform. The same substring can occur at multiple positions, so matching strings alone cannot recover this mapping. Bound actual windows and EDUs separately. [Plan and exact pins](../../plans/production-milestone-two/linguistic-referential-discourse.md#PM2-05) · [Dipo mechanisms](../../libraries/parsing/dipo.md) |
| Liquid d1-2B | Use the verified local `652f920e544ea37f81e4b0ce89b81d4ed0da90b1` snapshot with reviewed custom code, pinned calibration, and `AutoModel.from_pretrained`. Begin with eager CUDA BF16 and a distinct CPU FP32 smoke/reference route. Use `system_one` and `system_one_batch` for typed answers. Start with up to 16 independent questions and a provisional 4,096-token packed text row. | Bind JSON pointers and escape-aware state-string coordinates to allowed source fields. Candidate-only text, cross-field ranges and synthetic parts cannot supply evidence. Count the real packed row including suffixes and applicable media before respecting the separate padded-batch budget. Keep answer probabilities typed and calibration pinned. [Plan and exact pins](../../plans/production-milestone-two/gliner-and-d1-interpretation.md#PM2-07) · [d1 mechanisms](../../libraries/parsing/Liquid_AI_d1-2B.md) |

For Transformers 5.22.1 where compatible, use `BatchEncoding.word_ids`,
`sequence_ids`, `token_to_chars` or offset mappings only where the selected
backend exposes the needed correspondence. Pretokenized offsets can be local
to a word. Preserve the word mapping and distinguish special and padding tokens.
When a wrapper changes the input, the wrapper's realized transform is decisive.
Load local config, model, tokenizer and processor as needed with verified
artifacts. Pin a wrapper's independent dependencies and separately resolved
code alongside the model revision. Check loaded revision, selected head and actual dtype,
attention implementation and tokenizer. A generic Transformers `pipeline`
adds a second input and result convention around the providers' own execution
paths. The library's native token utilities and loaders have a useful narrower
boundary. Sentence Transformers and GLiNER remain existing baselines for their
own tasks. [Transformers guide](../../libraries/parsing/transformers.md) ·
[Sentence Transformers guide](../../libraries/parsing/sentence-transformers.md)

**Implemented precedents and proposed composition.** `pdf_gpu_slot` is a
per-operator lock among cooperating processes. It supplies the host coordination
boundary. `suspend_resident_nemotron` and `native_before_nemotron` are dedicated
local service handoffs with explicit endpoint checks. A profile using that path
must drain its child before restoration. `gliner_worker` demonstrates resident
same-interpreter spawn, bounded IPC and reaping. `pdf_recognition` demonstrates
an explicit-interpreter subprocess route for an isolated environment. Reuse
those owners or their narrow compatible mechanism. A second scheduler would
introduce competing admission and ownership. An in-process GPU provider would
make deadline and reclaim enforcement dependent on the model call returning.
The parent keeps the task and owns the serialized device interval. A controlled
failure closes or refuses only the attributable attempt and must preserve
completed siblings. `run_source_methods` currently raises on a failed result.
Continuing the rest of the graph would require a separate result policy. [Device handoff](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_capacity.py) ·
[Resident worker](../../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py) ·
[Isolated interpreter precedent](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_recognition.py) ·
[Released method graph](../../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py)

One resident profile, bounded native batching, shared source preparation and
coarse IPC make the proposed execution route credible. Multiple resident models
would trade fewer cold loads for concurrent device demand and more complicated
failure recovery. Revisit co-residency, different attention implementations,
compilation or export after a diagnosed operating limit and matched native
controls. Keep the application interpreter unchanged, use separate locks where
compatibility requires it and retain distinct execution identities for device or
inference changes. A physical batch-size retry may preserve the semantic
operation only if effective input and settings remain the same.

## 10. Verification and uncertainty

| Claim | Evidence and conditions |
| --- | --- |
| Authenticated v10 and original-spelling reads | **Tested, historical 2026-11-08.** The refreshed diagnostic account records p416/p418 at explicit 8 MiB Reader bounds and detached exact closure for view 382 on cut 517. Default or larger requests that refused their bounds stay outside this claim. Preserve the matched Reader, search and packet cases. |
| Baseline pairing and selection | **Implemented with historical receipts, 2026-11-08.** Cut 514/run 404 is source-ready. Cut 517/run 407 is the private M1 comparator within corresponding scopes. It settled 29 annotation and 29 candidate tasks. Set 32 is independently reviewed at sentence scope, and comparison with full-view predictions refused out-of-scope anchors. DMA-13 retains evaluated acceptance and cutover. |
| Exact four-way mapping | **Proposed.** Independently specify known source offsets for repeated phrases, Unicode, escaped text, disjoint pieces, omitted fields, protected atoms and source mismatch. Test each native bridge against those expected offsets and quotes, including exact `orig` with unavailable physical mapping. Then compare native grounded results over actual scoped requests. |
| Runtime and recovery | **Interface-checked.** `maintained_claims` retries an eligible renewal once after rollback and verifies remaining ownership. The retry only renews the claim. The host slot and process implementations are precedents. Each provider still needs offline cold load, warm work, mixed lengths, first oversize, failed load and cancellation/reap under its lock. Exercise expiry, reassignment and sibling evidence preservation through existing claim and completion paths. Actual native output is needed to settle physical fit after the positive Torch flag and failed NVML query. |

No fresh product, provider, fault or qualification commands were run for this
review (`not_run`). Static inspection and scoped historical evidence support the
design decision. Native claims remain subject to qualification. [Audit
revision](../audit/README.md#pm2-foundation-refresh) ·
[DMA evidence and outstanding selection](../../plans/domain-model-alignment_2026-11-08.md#audit-repair-execution) ·
[Claim lifetime](../../../python/corpus-structure/src/corpus_structure/semantic/claim_lifetime.py)

## 11. Authority and disposition

The [PM2 plan](../../plans/production-milestone-two_2026-11-08.md#execution-queue)
owns PM2-00–02 and these review findings. DA-061's prior installed-policy premise
is superseded in the consumed diagnostic delta. The verified baseline and
unavailable predecessor stay with their DMA owner. No binding rule, ADR or domain
vocabulary change is required by this recommendation. Reopen the affected
boundary if a required result cannot be expressed with the released contract,
if preserving original spelling requires a new canonical identity, or if a
qualified profile cannot meet the native workload through the existing host
custody route.

## 12. Architectural decision

| Judgment | Verdict for the scoped proposed design |
| --- | --- |
| A1 Localize change | Satisfied. Changes to a vocabulary or policy remain with release authority. Native tokenizer, renderer and inference changes stay with their profile and adapter. Consumer use of released source and result contracts remains locally testable. |
| A2 Encode domain meaning explicitly | Satisfied. Selected source, physical occurrence, provider assertion, coverage and endorsed output have separate authorities and enforcement boundaries. Their coordinate and terminal-state distinctions are required through private reads. |
| A3 Extend through composition | Satisfied. Authenticated view, thin native bridge, released method, fenced completion and private read compose without a second policy or scheduler. |
| A4 Fit execution to supported workload | Satisfied for baseline capture and deterministic source preparation under the named bounds. Existing indexed piece selection and product-level proof reuse avoid repeated native-product reconstruction. Native full-scope fit remains unresolved until each profile supplies actual work bounds, local-device and recovery evidence. |

**Accept scoped, Proposed.** Freeze the comparable private baseline, implement
source and outcome mappings, and wire the explicit runtime boundary so each
provider can qualify independently. Exclude native production execution from
acceptance until its profile has an exact offline lock and asset closure, a real
scoped output and applicable fault/limit evidence. A later selected release or
composed claim requires the relevant PM2 and DMA evidence at its own boundary.
