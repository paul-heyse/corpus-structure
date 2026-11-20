# Causal analysis of UDM operability

**2026-11-20 UTC.** Main at `3edc28fa5`, Python 3.14.10. The starting checkpoint has
N42 installed on stage and the book at N29, generation 5, in canonical development.
This investigation uses retained managed results, source and a private test host. The
file probe renders asset identities from temporary copies of archived source. The
production stages and whole-book run retain their standing in the qualification plan.
[Current qualification](../../../plans/unified-domain-model-and-execution/qualification.md#retained-fit-custody-and-rich-producer-authority)

## Findings in order of leverage

1. **Observed code reach is governing two different decisions.** The N42 transform
   refusal is caused by changes in the observed import graph. The same design area
   also turns incomplete lowering knowledge into demand-scoped production. Binding
   a release to executable code is necessary. The open design question is which
   artifact should bind execution, and which facts should establish producer reuse.
   This is the first structural priority because it affects both startup and rework.
2. **Model connectivity stops at some consumer boundaries.** Rich admission can read
   the facts it needs from the current model. Its failures came from applying those
   facts at the wrong authority boundary and from choosing the wrong validity family.
   M1 had two independent declarations of what the same prepared port needs. Both
   failure modes can surface before a long execution begins.
3. **Connected evidence expands into repeated physical work.** The event journey
   is paying for extensive setup and repeated support acquisition. Existing selected
   cuts and producer receipts provide the domain facts needed to carry established
   guarantees through the workflow. The evidence identifies duplicate work and
   a cumulative timing problem. It leaves the dominant remaining query open.
4. **Qualification obscures which promise has been exercised.** Native parity,
   application archival, executable acquisition, provider publication and scoped
   result readback each establish a different property. The operator currently
   needs to reconstruct this sequence across managed attempts to locate the first
   failed property. Use the existing preparation preview and managed result surfaces
   to expose those decisions with their owning facts.

These findings favor improving how a small set of existing facts is projected and
enforced. A single generic executor would still need different authority, identity
and lifecycle semantics. The simpler target shares acquisition and interpretation
where facts and premises coincide, and gives each different decision a clear owner.
[Execution-fit and assurance heuristics](../../design_principles/core/efficient-architecture-heuristics.md)

## Case evidence

### N42 admission and executable acquisition

**Tested.** Guarded Standard deployment and Integrated application admission passed
(`5cb34f8319ca4c71aaa504eccda86df1`, `aa866a00932f49129fb709da4ce09ad1`).
Main reproduced all 624 installed programs. The cold demand
`cfbf7d53d411497b85442167f7d2b70e` stopped during port acquisition before inference.
The structured stack reaches the **Integrated transform** at
`pdf_transforms.resolve_pdf_transform_port`, then
`verify_prepared_product`. The pending capture task is where orchestration recorded the
failed attempt. The mismatching asset belongs to the transform.

The prepared release captured `pdf-integrated/profile-assets` from `2bf51bf28`.
At execution, the transform port derives the asset again. The common verifier requires
the acquired artifact to equal the derived artifact. When callable discovery cannot
close the workload, the observed basis still includes the broader discovered module
digests. The asset embeds that observed digest and an attributed unknown list. Incomplete
discovery withholds reuse, while observed equality still governs executable admission
through the required resource check. The retained breakdown identified `observed_code`
as the differing field and equal material parameters, execution-custody files and reuse
flags. [Asset construction](../../../../python/corpus-structure/src/corpus_structure/semantic/operation_code_assets.py#L21) ·
[Code identity fallback](../../../../python/corpus-structure/src/corpus_structure/semantic/code_identity.py#L479) ·
[Prepared asset verification](../../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_prepared_products.py#L61)

The [probe](probe.py) replayed the actual asset constructor with retained Integrated
parameters and the installed interpreter. It predicted equal identity on relocating
identical source and a changed asset on editing either the transform callable or the
declared input. It then isolated the two intervening source edits.

| Change from the authoring source | Observed result |
|---|---|
| Identical bytes under another directory | Exact archived asset and observed-code identity |
| M1 planner capture edit alone | Asset changed. The only changed observed module was `semantic.m1_products`. |
| Event read sharing edit alone | Asset changed. The only changed observed module was `evaluate.declared_operation_events`. |
| Both intervening edits | Reproduced the main-checkout asset digest `c18cf79e…` exactly. |
| Edit the actual transform callable | Asset changed. The observed transform module changed. |
| Change declared transform input operation | Asset changed. The observed code basis matched. |

The baseline scan saw 615 modules and retained 117 source-level unknowns. Reuse proof
remained incomplete in every variant. The experiment isolates the fingerprint cause
from the path and parameter hypotheses. It establishes that both edits reached the
PDF asset through observed module digests. It leaves open whether those modules can
affect the selected transform's output. A selected runtime boundary test must settle
that question before changing material identity or reuse policy. The asset constructor
starts from both shared methods and all four mode-specific entry points, so selecting
Integrated currently starts discovery from code for three other modes as well.
[Counterfactual observations](raw/pdf-transform-identity.json)

**Proposed correction and check.** The immediate operating route is to prepare and
admit Standard and Integrated from the execution checkout, then verify their selected
port acquisition before starting a provider or a long workload. For the structural
repair, name and enforce three contracts at their existing owners: executable source
and binding correspondence, output-determining material, and proof sufficient for
reuse. Keep exact loaded callable, source and provider resource verification. Choose
the executable acquisition identity from the actual admitted boundary. Use observed
and unresolved dependencies to explain possible impact and withhold unsafe reuse.
Derive the relevant material and preview its first differing field. Compare the
selected transform capability with each intervening edit and with a genuine transform
dependency change. Rebound callable, changed model or worker bytes, and mismatched
execution profile must still refuse. If a legitimately required dependency cannot
be isolated, retain the wider refusal and name the unresolved dependency in the
preparation output.

### Rich admission and policy authority

**Tested.** The N40 rich writer failed while verifying historical fit material because
the path re-entered the protected presentation check (`50757742720b4fcba376a7da64100cbc`).
The existing model already kept the admitted release grant and the current principal's
authorization separate. N41 used the original cut, disclosure and access universe
for historical material, with the live check at current effects. The writer then
reached a second defect (`eec85e184dd040b1a13946c95c029761`). A generic rich input
helper required the rich validity family from the policy issuer. That issuer declares
family `none` and provides a public authorization through its own effect and native
receipt. N42 takes a family requirement from the consuming call and checks issuer
kind and actual authority separately. The actual rich journey passed, including
rejection controls and ordinary readback (`a145dbfebc9f4fc991ef7c511bb1cba2`).
The 18 private rich native controls also passed (`f1e49e25216340e0a46fb638f9ecc9fb`).
[Historical and live effect checks](../../../../python/corpus-structure/src/corpus_structure/semantic/effect_policy.py#L170) ·
[Policy validation at rich admission](../../../../python/corpus-structure/src/corpus_structure/semantic/rich_admission_native.py#L1347)

**Proposed correction and check.** Treat producer requirements as part of the typed
consumer input role. For the established rich input behavior, project the required
output role plus the CPU, publication, effect, family and disclosure requirements
from the existing admitted operation and support contracts where supported. Add a
typed requirement to the same owner for any genuinely absent fact. Check that the
declared producer can satisfy the consumer before application preparation passes,
and run one mixed-family actual journey with separately authored expectations for
ordinary policy output, protected fit data, and current effect refusal. Changing
a live principal must change live authority. Modifying a historical grant or receipt
must change material verification. Each check should name the fact and role responsible.
This proposal can retire hand-conveyed requirement arguments and duplicate selectors
only once every caller uses the typed projection.

### M1 source acquisition and selected readback

**Tested.** Three failures occurred in order. The fixture treated archived logical
module names as disk paths (`1e0a55beca9b43e3be696f74eb6f422a`). The shared executor
now resolves loaded source paths and checks their bytes. The next attempt supplied
`methods.m1_source.plan_candidates` for verification while its module was outside the
manually maintained capture subset (`42a03041b83a404a838264f3104835a0`). The runtime
verifier caught the missing owner. Adding that module to capture allowed actual GLiNER
execution and native publication. The next failure came from the assertion reading
the whole upstream demand through an 8 MiB result bound
(`8fefb2735f17470aaf9d8df805600379`). The assertion now reads the M1 operation;
its final provider receipt is open. [M1 acquisition projection](../../../../python/corpus-structure/src/corpus_structure/semantic/m1_products.py#L118) ·
[Scoped M1 readback](../../../../python/corpus-structure/tests/orchestrate/test_m1_declared_native.py#L112)

**Proposed correction and check.** Derive required captured modules and verification
from one typed declaration of the supplied callable surfaces. Reuse the application
resolver for fixture acquisition. Require the preview to identify an omitted module
before any work claim. An exact source relocation should pass with its newly resolved
physical path, while a rebound callable or different bytes should refuse. Run the
actual producer and check its selected result, CPU and logical provider receipt, and
zero new receipts on identical repeat. Treat assertion scope as part of test intent,
so the M1 assertion consumes the warranted operation cut even when upstream work grows.

### Operation-event execution and test cost

**Measured for the retained attempts.** The earlier group spent about 835 seconds
before the intentional disclosure refusal and expired during frame support acquisition
(`8f33fea76bfa47ca9c1ca874ea151412`). The bounded retry reached that marker at
486.4 seconds. It published both structural reports, frame, fit and authorization.
It entered the first test's scorer assertions 838.2 seconds after setup began.
The existing 900-second watchdog then expired in scorer request attachment
(`4fad3ac113214a0e87d4d94cd679da1e`), with two authority cases unrun. Timing markers
show that pre-frame work shrank across the attempts. The runs combine more than one
change, so the difference does not quantify the benefit of any individual edit or
the cost of a single SQL routine.

Source shows two removed duplicates. Identical event cuts share one authenticated
support index, and unchanged same-release validity avoids a second correspondence
check. Remaining candidate amplification is visible in source. Index acquisition
paginates the frontier before acquiring the whole scoped support closure. Support
export builds validity explanations and can revisit shared closure for each root
or page. No nested statement timings were retained for the final scorer attachment.
[Selected index acquisition](../../../../python/corpus-structure/src/corpus_structure/semantic/demand_results.py#L342) ·
[Support validity traversal](../../../../python/corpus-structure/src/corpus_structure/semantic/support_edges.py#L332)

**Proposed correction and check.** Give the real integration journey separately
observable assertions for bounded source preparation, native frame/fit/issuance and
scoring. Preserve one genuine end-to-end receipt. First measure cumulative boundaries
on a private replay, sample database waits, then inspect nested statement timing
only in the remaining slow phase. If support reconstruction dominates, carry
validated material within a pinned cut and compute shared validity premises once.
Keep per-root explanation and reacquire changed epochs and current authority. Verify
exact scorer output, disclosed authority leaf, rejection of a substituted use,
rejection of counterfeit authored parameters, and refusal of protected frame/label
disclosure. The current evidence supports narrowing setup and repeated reads. A
higher watchdog would only answer whether the same work eventually finishes.

### Book attachment, checkpoint uptake and retry

**Tested within retained scope.** The N29 census found the canonical book at generation
5 with zero live leases and unpublished intents. The same-named historical operation
recipes all differ from N42 Standard. Native request meaning includes recipe and
attachment looks for an eligible episode through the resulting request. The series-wide
census has hashes, not canonical recipe inputs, so the first differing determinant
for each operation is still unestablished. The more detailed N35 to N36 draft comparison
identified changed implementation revision and support contract, unchanged profile and
output roles, and false reuse eligibility on both sides. Thus the observed refusal
follows admitted inequality. Whether those changed fields represent a meaningful
algorithm or output change needs a finer comparison.
[Qualified regional comparison](../2026-11-19_udm20-regional-confirmation/README.md) ·
[Request meaning and attachment](../../../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L1557)

There is a second, already evidenced route to repeated work even with equal recipe.
The capture implementation slice was complete, but its profile was reuse-ineligible
because lowering-code closure was incomplete. Native attachment then binds execution
scope to the demand. A runtime change created a new demand and fresh request under
that rule. The checkpoint relation independently compares material producer recipe
and implementation as well as native schema, source and lowering custody. Durable
same-demand recovery still works. On N36, `dc348ca3780f4a96ad7dd8378389cc98` retained
the demand, published three receipts and cleared its leases. The unchanged repeat
`5b739336836c439b93d8fc47cd151d2e` published zero receipts.
[Equal-recipe replay diagnosis](../2026-11-19_udm20-regional-confirmation/README.md) ·
[Checkpoint material projection](../../../../python/corpus-structure/src/corpus_structure/semantic/pdf_spool_native.py#L244) ·
[Independent stop and resume evidence](../2026-11-20_udm27-managed-stop/README.md)

**Proposed correction and check.** Explain attachment and spool rejection by first
different canonical field and its source, with separate answers for a new request,
retained producer adoption, and checkpoint uptake. Then compare a transport-only
or orchestration-only edit with a changed parser, schema or provider asset using
the same source pages. Adoption should survive the first change only when all
required material can be established. Changed material, forged or active producers,
revoked support and modified replay bytes still refuse. Verify original attribution,
current publication and a zero-work repeat through native state and managed results.
Historical outputs remain historical evidence regardless of current eligibility.
Apply these cases against a bounded private snapshot before using the book.

## Choice of mechanism and verification

| Candidate | Disposition from these cases |
|---|---|
| Use the current admitted relations and fix their projections | First choice for rich authority, preparation screening and request/read scope. The required facts already exist. |
| Compile one typed consumer requirement and one callable acquisition specification | First consolidation to prototype. It targets manual parallel declarations, validates combinations early and can remove duplicate family/owner selectors. Compare downstream source capture, effect guards and denial semantics before retiring them. |
| Model a policy as independently versioned relational rows | Use this where a policy has its own authorized editor, release lifecycle and multiple runtime consumers. Compare with deriving rows from the existing declaration. Reusing a current relation avoids a second authority, migration, and compatibility burden. |
| Share prepared material and validation work within their existing lifetime | Apply to an authenticated cut with known premises. Keep the domain distinctions and attribution. A pooled generic cache or permanent receipt format needs its own measured or operational justification. |

The row-only comparison uses the existing admitted `command_class` for PDF capture.
An isolated PostgreSQL control keeps the actual generated selected-receipt verifier
fixed, then changes one fixture definition row for PDF capture to a different class.
The corresponding valid and refused cases test that the guard interprets model
data. Separate controls change principal, selected support, output and sealed
receipt. This demonstrates the shape of a useful relational mechanism and its
security boundary. The test directly edits a disposable fixture row; in operation,
the author changes the typed declaration and publishes its admitted release
projection. For rich admission, a row-only design should likewise keep the
producer declaration, required effect and historical authority separately owned.
[Native row-mutation control](../../../../python/corpus-structure/tests/semantic/test_source_capture_native.py#L199)

**Tested in this investigation.** `uv run ci test --native-host private` passed all
14 selected identities (`b2927d425e054ce0b5ca5fec5f89fe82`). The nine capture cases
exercise the generated guard, including valid and changed command rows. The other
five verify a real producer helper edit with stable downstream recipe, equal-value
cutoff, revocation and fresh independent support, a family-local validator change,
and rejection under a distinct consuming request. These bounded controls use the
currently admitted relations and compiler.

Sequence the work by cheapest discriminating evidence. First make application
preparation report the affected operation, asset, and expected/actual basis
before a provider starts. Use `ci model change inspect` for preview effects,
`ci schema explain-operation` for admitted roles and scoped native fates, and
`ci results inspect` for invocation standing. The retained
`ci results inspect cfbf7d53d411497b85442167f7d2b70e --view observations --severity ERROR`
reports the port refusal and its stack. A separate archive comparison identified the
transform asset and its changed inputs. Include that attribution in the existing
operator surfaces. Next derive shared producer and
consumer facts, and resolve the execution-custody and material-identity split.
Then use the event phase evidence to remove repeated support work. The remaining
whole-book qualification is the final integration observation of those corrections.

Acceptance for a candidate implementation is a predictable change boundary. A
declared policy or actual producer edit changes the affected operation, explains
the affected checks and leaves unrelated eligible work available. The opposite
direction uses the same route with an unchanged determinant, revoked authority,
changed binding or interrupted work. Explain the decision from a scoped operator
view and verify one independent native readback. The current investigation supports
the specific findings above. Whole-book and final provider coverage belong to the
owning plan. [UDM-22 and UDM-23](../../../plans/unified-domain-model-and-execution_2026-11-19.md#package-queue)

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Other**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Causal evidence for UDM startup, change propagation and recovery](records/udm22.operability-causality.json) | UDM-22 | partial | UDM-22, UDM-23 | 2026-11-20 |
<!-- evidence-index:end -->
