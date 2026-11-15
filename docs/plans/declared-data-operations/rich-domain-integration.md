# Rich domain products, evidence and admission

**Accepted planning scope · 2026-11-15; implementation Proposed.** Develops DDO-09 with producer
and consumer contributions from DDO-07/08/10/11/12. Consumes Domain-model I01/I02/I05/I09 from the
[audited review](../../plan_improvement_reviews/declared-data-operations-domain-model_2026-11-15.md)
at `4f32589d0`. The [coordinator](../declared-data-operations_2026-11-12.md) alone owns current
package/finding disposition and qualification. This companion owns the rich-family semantic target,
not a new stage, storage protocol or progress ledger.

## Responsibility and inspected baseline

D1/D5 remain the architectural owners of knowledge representation and consolidation. The
[contracts/compiler](contracts-and-compilation.md) owns generic subjects, invariants and identities;
[products/support](products-and-support.md) owns native trust/publication and physical attempts;
[change/reuse](change-reuse-and-consolidation.md) owns common currentness and substitution.
This companion instantiates those contracts for rich domain knowledge and its real consumers.

**Interface-checked by source inspection · 2026-11-15.** `semantic/domain_operations.py:_cut_input`
reads sealed `ops.input_cut`/`ops.run`, observations, tasks, method configuration and source frames
(`:848–910`); `_project_cut` admits AgentStoredBatch/NativeProposalFrame (`:1369–1420`).
`ReleasedRulesPolicy` consumes candidates, alternatives, scientific decisions and rule views.
`semantic/consolidation.py` and `record_interpretation.py` contain useful scientific/interpretive
kernels. Preserve their meaningful behavior while replacing old acquisition/publication ownership.

Private candidate standing is already enforced: the candidate-inspection schema requires
`private_uncalibrated_candidates`, its producer validates that value, and reading-resolution/finite
interpretation consumers check it. This is an existing foundation, not a missing docstring contract.
It does not supply accepted Entity/Claim/Statement/Fact semantics by itself. Implementation of this
companion, provider execution and actual admission/qualification are **not_run** at plan authoring.

## Rich contracts and semantic distinctions

The rich family must distinguish what a source says, what an operation proposes, and what the
knowledge admission policy accepts. A successful operation or a readable product grants neither
scientific truth nor accepted standing. Define the concrete effective kind/role contracts before
porting storage fixtures or public queries:

| Required meaning | Target contract and consumer |
|---|---|
| Subject and entity identity | Checked subject definitions and identity relations distinguish source occurrences, reading-local objects and resolved domain entities. Entity resolution must carry its actual evidence/policy; equal labels or local IDs cannot silently merge entities. |
| Statements and claims | Preserve attributed source statements separately from propositions/claims, including polarity, modality, qualification, conditions and scope. A graph assertion about a reading is not an assertion that its scientific proposition is true. |
| Facts and accepted knowledge | A typed assertion carries establishment/standing and supporting evidence. Accepted knowledge results from a declared admission operation with explicit policy and sufficient evidence, not renaming a candidate or copying a successful task state. |
| Evidence and alternatives | Authored facts, original-source custody, computed observations and independently attributed judgments retain distinct support origins. Preserve incompatible/exclusive alternatives and unresolved identity choices; do not count repeated copies as independent support. |
| Coverage and absence | Specify examined source/family/population scope, missing/partial/unavailable evidence and supported absence witnesses. An empty selected set is not proof of absence or complete consolidation. |
| Numerical/scientific interpretation | Parameters, units, precision, semantic comparison rules and scientific policy are declared result-affecting inputs or admitted implementation/opaque determinants. Retain the existing kernels’ explicit unsupported/undecided outcomes. |

Concrete names and released schema details are settled by the scoped design work below, using
current typed domain facts rather than inventing a parallel ontology. Product bodies, references
and input roles must encode these distinctions; canonical bytes or similarly shaped dictionaries
are not substitutes for a checked contract. The existing independent exclusion, source, fact,
coverage and scientific expectations constrain the replacement.

## The rich cut and declared operation chain

A native `CutSelection` authenticates a selected read/trust context. It is necessary custody, not a
complete rich semantic cut. The declared rich selection must additionally bind the exact relevant
product/member population, evidence/alternatives, known-fact universe, policy/rule values and their
released interpretation. Population completeness is explicit and independent of the output selector.
No implicit newest release, latest accepted knowledge or ambient policy lookup may affect results.

Separate acquisition from semantic computation and effectful admission:

1. Acquire the admitted product/member/support selection and required original-source context through
   the existing native read owner. Freeze the rich universe and policy; bounded indexed acquisition
   must include intermediate evidence and negative/population facts needed for the claimed result.
2. Prepare immutable rich values and invoke consolidation/identity/interpretation kernels using those
   values. Preparation may be shared within its validity scope; it does not hold native publication
   locks or rehydrate unrelated corpus state per candidate.
3. Produce private consolidation/interpretation products with typed coverage, alternatives, reasons
   and exact consumed binding/support identity. Partial useful results remain distinct from a complete
   accepted result. A single semantic distinction need not create another task/table/transaction.
4. A separately declared admission/publication effect evaluates the applicable standing policy and
   publishes the target knowledge view under native authorization and exact effect receipts. Failed
   later admission leaves earlier private products useful without promoting them.

Standing transitions must be explicit for the supported private/proposed/accepted distinctions.
Represent only transitions the chosen domain actually supports; do not add a universal workflow.
Wrong standing, missing required evidence or ambiguous policy cannot silently fall back to the old
run/consolidation route. Generic request coalescing, leases, trust and uncertain-commit recovery stay
with the common native owner.

Store exact consumed binding, universe and policy identities with materialized knowledge. Its
currentness is assessed against an explicit comparison target using the common change/reuse owner,
including equal-value/support cutoff; there is no second rich stale flag or invalidation engine.

## Concrete preparation questions and dependent work

These are bounded work within existing packages, not a second question-status table. The coordinator
records current disposition and evidence; implementation may begin only on consumers whose needed
contracts are settled and usable.

| Owner / question | Required settling work | Constrained work |
|---|---|---|
| DDO-01/02 with DDO-09: which rich subject and identity distinctions are needed? | Map current ClaimCandidate/FactItem/entity mappings and D1 source-reading/domain meanings to checked effective kinds, roles and subject relations. Independently specify equal-name/different-occurrence and unresolved-identity cases. | Rich product identity, schema admission and resolver input contracts. |
| DDO-09: what constitutes the exact knowledge/policy universe? | Trace `_cut_input`, `_project_cut`, `ReleasedRulesPolicy` and actual exclusions/alternatives. Specify all answer-affecting inputs and completeness witnesses, including known facts and rule views beyond native CutSelection pins. | Consolidation preparation, binding, currentness and migration correspondence. |
| DDO-08/09 with DDO-04: how is standing admitted? | Define private/proposed/accepted product contracts, authority, evidence and allowed transitions; preserve the working private-candidate guard. Pair sufficient-evidence admission with a wrong-standing/missing-evidence refusal. | Accepted publication and accepted-knowledge readers; private inspection can proceed earlier. |
| DDO-08/09: what becomes of record-policy and projection-analysis? | Follow actual algorithms and callers. Declare their surviving computation/policy products or explicitly retire the capability; remove old shells with migrated consumers. | Full family/caller closure; neither family disappears from scope because it lacks a declaration today. |
| DDO-09/10/11: can retained rich data become target-native? | Compare available evidence and question/input/output basis with target requirements. Select faithful conversion, regeneration/reassessment or inert retention/disposal; never fabricate source, request, derivation or accepted-standing custody. | Only the selected import/adoption work, not the target architecture or unrelated code retirement. |

## Consumer migration and retirement

### Evaluator authorization and disclosure

[ADR-0110](../../adr/0110-evaluator-authorized-policy-disclosure.md) settles the bounded authority
design. Protected complete-record grades, feature-fit and calibration remain evaluator products;
a dedicated native issuer publishes only an ordinary exact policy-instance authorization through
the existing command/effect/factory and completion receipt. Actual feature fitting retains its
restricted feature-fit capability. Generic selected-case comparison is not a complete-record grade.

Native validity, impact and trust locking retain full protected support. Ordinary read/export
provenance uses an explicit opaque authority leaf with allowlisted issuer/output summary and
approved standing. It excludes hidden input/support edges, request bindings, completion-intent
payloads and other outputs; graph/detached consumers report unknown protected dependencies rather
than inventing a complete closure. Authored/copied same-kind values and wrong producers refuse.
Direct revocation of the issuer/recipe/runtime/output cannot be repaired by value substitution.

The fitted-instance authorization binds predictor/calibration, numerical/family interpretation,
question/rubric, checked applicability and event/threshold procedures. Rich admission still checks
each actual new reading, interpretation, feature input, unique completed final event, finite
calibrated threshold, complete required evidence, alternatives and exact lowering membership.
Production readings need not occur in calibration samples. Preserve low-scored scored events and
no-output source coverage in their distinct fit populations. A caller's subset string is not
checked applicability, and calibrated source-reading fidelity is not scientific truth. Exact-member
assessment, where supported, has separate meaning. No implicit latest-reference rebinding occurs.
Native purpose/disclosure/revocation, counterfactual per-record refusal and actual current public
consumer controls remain required; this target decision does not close their implementation.

The concrete authorization owner is `semantic/record_policy_authority.py`. Its actual reading
recipe and effective family kind-contract identity bind feature/event interpretation across releases;
the original instance release remains authentic lineage rather than a broad equality gate. The
application source population is explicit and independent of fitting samples. Protected canonical
parameter JSON retains the exact Python digest bytes for native verification; PostgreSQL must not
guess Python floating-point spelling or substitute a numerically similar serialization.

The [operations companion](operations-and-adapter-cutover.md) owns the complete per-operation
inventory. Its rich-family entries link here for meaning and cover genuine consolidation, evaluation,
assembly, record-policy and projection-analysis responsibilities. The [interfaces companion](interfaces-and-evaluation.md)
owns native/CLI/MCP/query/export and protected assessment integration. Migrate rich named queries,
ReferenceRecord grading and current `agent_scenarios`, `serving_scenarios` and `reference_scenarios`
to real target-native source/evidence/policy inputs and public product/member references.

Once each replacement and its maintained callers work, remove ProposalSession,
HistoricalAgentPublication, old run finalization/supervision, task-origin cut acquisition and
copied-task/twin-reuse paths, their registrations/writers/grants/configuration and mechanism-only
tests. Preserve useful algorithms, actual native attempt/fence semantics and independent expectations.
Do not mark current fixtures historical to bypass a missing contract, fabricate SourceView/Task/
FactRow aliases, or keep a historical reader solely because old generated data exists.

Useful old data may be converted to ordinary target-native records through finite adoption tooling.
An old model judgment whose question/context/input/output basis changed requires a new assessment;
structural conversion is not equivalence. Existing claims can survive as honestly attributed
observations only where the target has that meaning. Conversion tooling has an explicit removal
endpoint and is absent from normal target serving/execution. The adoption companion owns the
physical route; conversion of every retained population is not a prerequisite to this design.

## Delivery and independent acceptance

Deliver shared subject/enforcement/identity changes before dependent rich publication, but develop
rich design and public read requirements alongside them. Private rich computation can integrate
before accepted publication; that does not complete the accepted-knowledge family. Move producers,
their immediate consumers and obsolete mechanism removal together. DDO-11 owns the actual physical
switch; DDO-12 owns the final functional/native/provider/public union.

| Scenario | Independent expected result |
|---|---|
| Small private consolidation | An explicit selected population with authored and computed evidence produces source-qualified private entities/statements/claims, preserving alternatives, missing coverage and policy identity. Read it through the actual selected public owner without accepted standing. |
| Accepted-standing admission | A declared operation with sufficient typed evidence and an explicit admission policy produces accepted knowledge with exact consumed bindings/support and authenticated receipt. Equal payload possession alone cannot satisfy the admission effect. |
| Missing/ambiguous evidence | Missing source, incomplete population, incompatible alternatives, wrong standing or absent policy yields the specified refusal or honest partial/undecided result. It must not silently admit knowledge or enter the old acquisition route. |
| Currentness and reuse | A policy/input/support change affects the expected subjects; unrelated changes do not. Equal admissible output/support stops downstream propagation. Directly revoked production is not rehabilitated by copied evidence. |
| Migration and reassessment | A faithfully convertible record is consumed by target-native readers without legacy imports; a changed-basis judgment is unavailable for current grading until newly assessed. No invented legacy or target custody is accepted. |
| Complete consumer replacement | Actual named query, protected reference/grading, CLI/MCP and export consumers use the rich target contracts; obsolete acquisition/publication shells and converter dependencies are absent. |

Preserve independent scientific/semantic expected values and deliberate invalid inputs. Producer
output, the same validator on both actual and expected, or an export round trip cannot establish
rich correctness. No universal accuracy threshold, provider campaign or benchmark is introduced by
this plan-writing increment. Later targeted checks and final assembled qualification follow the
coordinator’s authorized execution boundary.
