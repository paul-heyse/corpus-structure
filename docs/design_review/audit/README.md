# Design principle audit

This is the living diagnostic account of design principle misalignment, maintained by the
[audit skill](../../../.claude/skills/design-principle-audit/SKILL.md). The
[repository binding](../design_principles/binding/corpus-structure.md#design-principle-audit)
owns its place before a design-review engagement. Ordinary implementation reads its plan and
architectural owners; this collection is not default production-editing context.

<a id="unified-model-refresh"></a>

## Current engagement refresh — unified domain model, 2026-11-01

**Source-inspected; revision UM-20261101-r2.** Source `1cb8e620`, core 3.3 with
heuristics 1.0 and code-intelligence 1.4. Production source was clean during inspection;
concurrent changes to STATUS, PDF plans/evidence and the Arrow/DuckDB capability guides were
included as context, not fresh product qualification. The October 29 baseline and findings
below retain their original dates except for the specifically refreshed subjects here.

This refresh covers release preparation/boundaries, execution contracts and guards, lifecycle,
CLI/MCP serving, graph/vocabulary and typed analytical integrations. Source inspection establishes
implementation, not native deployment or tested behavior. Tests, provider journeys and probes
were not run for this refresh. Test architecture and uncited native guard bodies remain outside
this inspection; existing test-audit conclusions are not refreshed.

| Subject | Current diagnostic account |
|---|---|
| DA-020 | [Current narrowed diagnosis](boundaries-and-composition.md#da-020): resource settings do not reach consolidation scope construction. |
| DA-001 | [Narrowed current diagnosis](semantic-model-and-authority.md#da-001): fact identity and comparison grouping have separately consumed qualifier policies; their distinction/relationship is not a typed compiled contract. Coarser grouping can be legitimate. |
| DA-026 | Exact archived execution binding and result/effect consumers now exist; earlier missing-product diagnosis retired for that subject. |
| DA-027 | Operations/transitions/effects are consumed. Invariant-to-guard correspondence remains an unresolved scoped question, not proof that the catalog is decorative. |
| DA-028 | [Current concrete continuation](semantic-model-and-authority.md#da-028): CLI named queries import live pack code despite archiving it with the release. |
| DA-029/030 | Protected archive/activation and caller fences materially correct the earlier lifecycle diagnosis; this inspection does not requalify every admitted row or deployed ACL. |
| DA-041 | Release-projected task/run edges, terminal receipts and failure diagnostics correct the earlier missing-lifecycle diagnosis. |
| Typed/graph foundations | Effective field adapters, finite-float construction, metadata-derived Arrow fields, qualified graph closure and model-bound graph validation are implemented strengths. Earlier broad absence claims cannot be carried forward for these paths. |

Decisive sources are cited in the refreshed finding bodies and the
[engagement model map](domain-model-map.md#current-model). All other DA observations below are
**inherited at their stated October 29/28 scope**, not newly verified open defects. The review
must inspect a decisive current manifestation before relying on any inherited diagnosis.
Plans retain scheduled disposition; this refresh does not close plan obligations.

<a id="baseline"></a>

## Baseline

| Item | Value |
|---|---|
| Audited source | commit `ad4593f`, clean tree (no uncommitted changes included) |
| During the audit | HEAD advanced through documentation-only commits to `1f66fd4`. Contributors confirmed that no file under `python/`, `domains/`, `scripts/` or `ops/` changed |
| Date | 2026-10-29 |
| Standard | core 3.3 (principles, efficient-architecture heuristics; the test-assessment companion only where a test is cited as oracle evidence); code-intelligence profile 1.4, applied directly to serving, explanation, evaluation and MCP; [binding](../design_principles/binding/corpus-structure.md) |
| Kind | First refresh after the semantic-model pivot. The preceding baseline was `024bb33` (2026-10-28, pre-pivot) |
| Publishing commit | the commit that adds this account, distinct from the source baseline |

**Scope (operator, 2026-10-29): the clear go-forward design.**
- **In scope:**
  - the LinkML semantic model and pack models;
  - the release compiler;
  - the native PostgreSQL layer (`semantic_alembic`, about 1 MB of SQL: 82 distinct functions, 33
    triggers and 427 grants at head);
  - domain operations and analytics;
  - the read kernel, `serve/`, the CLI, MCP and reference evaluation;
  - run orchestration and automated extraction;
  - the go-forward parts of the design collection.
- **Legacy code is ignored for now:** `core/`, `schema/`, `pool/`, `validate/`, `consolidate/`, the
  legacy LinkML model and Alembic tree, and unreachable modules. Where go-forward code depends on a
  legacy module, the edge is recorded as a boundary fact ([DA-045](boundaries-and-composition.md#da-045)).
- **Tests** belong to the separate [test audit](../test-audit/README.md).
- **Completion** is not judged here: a plan-completeness review runs separately.
- **Labels:** each finding says whether its subject is implemented, an accepted target or proposed.

**Emphasis (operator):** domain model and semantic authority, and native integrity. Full principle
coverage still applied: every contributor considered every foundation within its slice.

**Method.**
1. **Exploration.** Three read-only passes inventoried the go-forward code, mapped the 25 earlier
   findings against current source, and mapped the plan and design state.
2. **Wave 1.** Six independent design-reviewer contributors took one architectural slice each:
   - semantic model and release authority;
   - native structure, enforcement and privilege;
   - native operations and publication;
   - domain operations and analytics;
   - consumers, served claims and evaluation;
   - execution, orchestration and boundaries.
3. **Probes.** The coordinator ran two read-only probe scripts on throwaway databases on the 5434
   cluster (P1–P6, [evidence](../evidence/2026-10-29_design-principle-audit-probes/README.md)):
   - privilege and trigger catalog;
   - publisher write access to `sem.*`;
   - schema parity body for body;
   - canonical JSON;
   - locator whitespace;
   - decimal expansion.
4. **Reconciliation.** The coordinator verified each decisive source and grouped findings by
   structural cause. It also read the design collection for adequacy and single authority.
5. **Wave 2.** Three fresh contributors traced six go-forward change scenarios end to end and
   adversarially checked the draft findings on their paths. They confirmed, narrowed or corrected
   most findings and added five.

Contributors' scratch checks are cited as observations and were not retained as evidence:
- offline `prepare_packs` runs;
- the equivalence-kernel probe;
- the establishment and NaN probes;
- edge-count scripts.

No test suite was run for the audit.

**Coverage limits.**
- **Not read in depth:**
  - most native lifecycle-guard bodies beyond those cited;
  - `eval.*` function bodies;
  - `validate_conditions`;
  - the analysis-batch publication routines;
  - `semantic/conditional_rules.py`;
  - `QualifiedGraphProjection`;
  - export internals;
  - `methods/` and `ingest/` beyond their contracts toward semantic runs.
- **Not run:** mutation probes, and journey probes that would need full runs:
  - a toy run without `--domain`;
  - finalizing a batch with `derived` establishment;
  - equivalence selection under load;
  - admission after a catalog change;
  - `load_release` after a library bump;
  - an interrupted source phase;
  - pointer coherence on resume.

  The static evidence was judged decisive, and the limits are stated in each finding.
- **Absence claims** rest on grep over the go-forward packages. Dynamic access was not traced.
- **Quantitative claims** are limited to the probe catalog figures and one cited measurement
  (release preparation, comparative leverage review, Q3).
- **Concurrent work.** A correction for the STATUS blocker exists only as an evidence draft
  (`docs/design_review/evidence/2026-10-29_semantic-consumer-regeneration/draft-0031/`). When
  applied, it will narrow [DA-026](semantic-model-and-authority.md#da-026)'s first manifestation
  only.

<a id="scenarios"></a>

**Change scenarios.** These are go-forward seeds, replacing the pre-pivot S1–S9, and are used to
show consequences. SC1–SC6 were traced end to end in wave 2.

| | Scenario | Main findings met |
|---|---|---|
| SC1 | Add an identity-bearing property or qualifier to a pack and regenerate | DA-001, DA-003, DA-026, DA-009 |
| SC2 | Compose a second domain pack with its own statement class, kinds, roles and plug-in | DA-048, DA-026, DA-028, DA-046, DA-005 |
| SC3 | Add a physical column or closed-set member through staging; correct a bad admitted fact | DA-031, DA-032, DA-029, DA-002 |
| SC4 | Bump the compiler or a byte-determinant library | DA-049, DA-009, DA-042 |
| SC5 | Add an extraction method or a second agent tier | DA-052, DA-051, DA-016, DA-012, DA-041 |
| SC6 | Query, paginate and explain while the selected result changes | DA-050, DA-035, DA-036, DA-028, DA-039 |

Verdicts:
- **SC2 cannot run end to end today.** Barriers stack: no production path persists a composed
  release; it carries no domain rules; runs fix one pack; native code refuses the pack's statements.
- **SC4 strands every archived result.**
- **SC6 keeps data pinned across pages,** but not code or follow-up references.

<a id="deviations"></a>

## Where the go-forward design deviates

The go-forward architecture has a strong core:
- pure, explicit-input release preparation;
- immutable, byte-exact releases;
- native validation driven by release rows for applicability, identity slots, key roles and case
  policy;
- protected staging;
- native run and task state machines;
- read snapshots pinned to a completed result.

The [domain model map](domain-model-map.md#strengths-to-keep) lists the strengths a remedy must keep.

The deviations share a shape. **Later contexts re-decide meanings the release could carry**: by
class name, by literal subset, from the working tree, or with a kernel of their own. **The native
layer's guarantees stop at the edges of the write path** it was built for. In order of consequence
for follow-up design:

1. **Operation bindings ([DA-026](semantic-model-and-authority.md#da-026)).**
   - Which class plays "source statement", which qualifies claims, which vocabularies hold roles,
     which modalities are inference-eligible: none of these is a release product.
   - Regeneration guesses the bindings from raw YAML. Python reads them back by name, and native
     guards restate platform defaults as literals.
   - This is the observed blocker: a valid `ToySourceStatement` is refused and run 3 is stuck.
   - The pending correction is necessary but not sufficient.
2. **Scientific equivalence ([DA-034](semantic-model-and-authority.md#da-034)).**
   - Two kernels decide sameness differently, and the one that drives selection treats casefolded
     text and sampled numeric agreement as equality.
   - It depends on a wall-clock deadline, and it collapses equal facts to one selected
     representative under an undeclared policy.
3. **Native integrity ([DA-029](native-integrity.md#da-029), [DA-030](native-integrity.md#da-030)).**
   - Immutability is enforced for some row families and only declared for admitted content,
     observations and grades. The publisher holds unused UPDATE on 29 `data` tables.
   - Archive, activation and selection run under the owner login or an assumed role, while native
     guards treat that role as proof of a reviewed routine.
4. **Compatibility lifetime ([DA-049](semantic-model-and-authority.md#da-049)).** Any patch bump
   of the eleven listed libraries, or any byte change to the execution catalog, strands every
   completed result, run and selection. Recovery is full regeneration, including paid agent
   extraction.
5. **Executable scope and composition ([DA-028](semantic-model-and-authority.md#da-028),
   [DA-048](semantic-model-and-authority.md#da-048), [DA-046](semantic-model-and-authority.md#da-046)).**
   - Runs and served plug-ins execute live pack files that the bound release archives.
   - Composition is a preparation-only product.
   - Core and generic code carry statistics vocabulary.
   - The "any domain" target has no runnable second-domain route.
6. **Served fidelity and evaluation ([DA-035](served-claims.md#da-035),
   [DA-036](served-claims.md#da-036), [DA-037](served-claims.md#da-037),
   [DA-050](served-claims.md#da-050)).**
   - Producers and consumers read coverage differently, so absence can never be stated, and every
     page carries the whole realization's coverage.
   - Selection status is not served.
   - Grades cannot tell "not matched" from "not comparable".
   - Explanations sit outside the pinned journey.
7. **Model layers and vocabularies ([DA-027](semantic-model-and-authority.md#da-027),
   [DA-002](semantic-model-and-authority.md#da-002), [DA-003](semantic-model-and-authority.md#da-003),
   [DA-012](structure-and-invariants.md#da-012)).**
   - The execution catalog and the core record classes describe rather than govern, and contradict
     each other.
   - Closed sets and behavioural roles are restated by hand across three to six owners, and one of
     them (splits) already disagrees.
8. **Native structure and evolution ([DA-031](native-integrity.md#da-031),
   [DA-032](native-integrity.md#da-032)).**
   - Relation structure has two hand-maintained authorities, which agree at head (probe P3) but
     with no body-level check.
   - Routines evolve by whole-body copies.
   - Head revisions were edited in place.
   - Results carry no deployment identity.
9. **Runs and outcomes ([DA-041](structure-and-invariants.md#da-041),
   [DA-013](structure-and-invariants.md#da-013), [DA-052](boundaries-and-composition.md#da-052),
   [DA-051](served-claims.md#da-051)).**
   - A failed consolidation is unrecorded, partial outcomes do not exist, and outcomes are prose.
   - Proposal production is welded to one method name, and attribution is declared, not
     established.
10. **Execution fit ([DA-042](execution-fit.md#da-042), [DA-043](execution-fit.md#da-043),
    [DA-033](execution-fit.md#da-033)).**
    - Immutable products are re-derived per use.
    - Consolidation reads the whole input realization and has quadratic constructions inside the
      cut.
    - Native publication revalidates whole realizations (low current consequence).

The audit only diagnoses. It does not choose corrections or render an architectural verdict; a
design review owns both. Leverage-review solution reasoning exists for several of these causes
([comparative review](../../library_leverage/reviews/README.md)).

## Findings

| ID | Finding | Subject | Page |
|---|---|---|---|
| [DA-001](semantic-model-and-authority.md#da-001) | Identity-bearing qualification declared twice, with opposite defaults | implemented | semantic model |
| [DA-002](semantic-model-and-authority.md#da-002) | Closed vocabularies restated across semantic, catalog, physical, native and code owners | implemented | semantic model |
| [DA-003](semantic-model-and-authority.md#da-003) | Declared category roles inert; roles in use are literal reconstructions | implemented | semantic model |
| [DA-004](semantic-model-and-authority.md#da-004) | Validated models and release annotations re-parsed as dicts and strings | implemented | semantic model |
| [DA-005](semantic-model-and-authority.md#da-005) | Context translations not owned as complete contracts | implemented | semantic model |
| [DA-007](semantic-model-and-authority.md#da-007) | Unresolved references and unsettled identities are prose or silent | implemented | semantic model |
| [DA-009](semantic-model-and-authority.md#da-009) | Identity determinants hand-listed; recipes unversioned and mirrored without specification | implemented | semantic model |
| [DA-011](semantic-model-and-authority.md#da-011) | Design collection carries superseded and current authority side by side | design text | semantic model |
| [DA-012](structure-and-invariants.md#da-012) | Operational sets have no go-forward authority | implemented | structure |
| [DA-013](structure-and-invariants.md#da-013) | Outcomes and refusals are prose; declared outcome domains not emitted | implemented | structure |
| [DA-014](structure-and-invariants.md#da-014) | Source coordinates: two diverging grammars, two encodings, positional keys | implemented | structure |
| [DA-016](structure-and-invariants.md#da-016) | Escalation and confidence policy declarations compile without consumers | implemented | structure |
| [DA-020](boundaries-and-composition.md#da-020) | Coordinates, principal names and resource settings repeated or unconsumed | implemented | boundaries |
| [DA-026](semantic-model-and-authority.md#da-026) | Release operation bindings have no declared product; native and Python bind by name | implemented | semantic model |
| [DA-027](semantic-model-and-authority.md#da-027) | Model layers describe the knowledge and execution records without governing them | implemented | semantic model |
| [DA-028](semantic-model-and-authority.md#da-028) | Runs and served queries execute live pack files the release archives | implemented | semantic model |
| [DA-029](native-integrity.md#da-029) | Immutability enforced unevenly across release, content, observation and grade rows | implemented | native integrity |
| [DA-030](native-integrity.md#da-030) | Principal separation does not cover the release lifecycle | implemented | native integrity |
| [DA-031](native-integrity.md#da-031) | Relation structure has two hand-maintained authorities without body parity check | implemented | native integrity |
| [DA-032](native-integrity.md#da-032) | Native evolution hand-propagated; head revisions edited; no deployment identity on results | implemented | native integrity |
| [DA-033](execution-fit.md#da-033) | Native publication re-establishes assurance per write over the whole realization | implemented | execution fit |
| [DA-034](semantic-model-and-authority.md#da-034) | Scientific equivalence has two authorities; selection consumes the sampled, casefolded one | implemented | semantic model |
| [DA-035](served-claims.md#da-035) | Coverage producers and consumers use different vocabularies; absence never statable | implemented | served claims |
| [DA-036](served-claims.md#da-036) | Selection status is an undifferentiated filter, not a served attribute | implemented | served claims |
| [DA-037](served-claims.md#da-037) | Grades conflate not-matched with not-comparable; universe conditioned on extraction | implemented | served claims |
| [DA-038](served-claims.md#da-038) | The kernel's paged query route has no production consumer; serving uses private members | implemented | served claims |
| [DA-039](served-claims.md#da-039) | Explanation and path queries are unbounded | implemented | served claims |
| [DA-040](structure-and-invariants.md#da-040) | Value admissibility enforced late and partially at boundaries | implemented | structure |
| [DA-041](structure-and-invariants.md#da-041) | Run lifecycle has no recorded outcome, partial or orphan state | implemented | structure |
| [DA-042](execution-fit.md#da-042) | Immutable products re-derived on every use | implemented | execution fit |
| [DA-043](execution-fit.md#da-043) | Consolidation and inference scale with the input realization and quadratically with the cut | implemented | execution fit |
| [DA-044](structure-and-invariants.md#da-044) | Representatives and attributions chosen by incidental ordering | implemented | structure |
| [DA-045](boundaries-and-composition.md#da-045) | Go-forward contracts still live in legacy modules; one layering inversion | implemented | boundaries |
| [DA-046](semantic-model-and-authority.md#da-046) | Semantic core and generic code carry statistics vocabulary | implemented | semantic model |
| [DA-047](boundaries-and-composition.md#da-047) | Surfaces maintained without a go-forward consumer | implemented | boundaries |
| [DA-048](semantic-model-and-authority.md#da-048) | Pack composition is preparation-only; its inputs are out of consumers' reach | implemented | semantic model |
| [DA-049](semantic-model-and-authority.md#da-049) | Archived releases and results have no declared compatibility lifetime | implemented | semantic model |
| [DA-050](served-claims.md#da-050) | Explanation and follow-up references sit outside the pinned serving journey | implemented | served claims |
| [DA-051](served-claims.md#da-051) | Producer attribution declared by configuration, never established | implemented | served claims |
| [DA-052](boundaries-and-composition.md#da-052) | Claim-proposal production welded to the `agent.opus` path | implemented | boundaries |

<a id="retired"></a>

**Retired at this baseline.** These were verified at `ad4593f` on 2026-10-29. Each keeps a stub at
its original anchor, and the earlier text is in Git.

| ID | Correction |
|---|---|
| [DA-006](semantic-model-and-authority.md#da-006) | References typed by range, `cs:reference_role` and foreign keys. The residue moved to DA-007 |
| [DA-008](semantic-model-and-authority.md#da-008) | Case preserved by default and folded only where declared |
| [DA-010](semantic-model-and-authority.md#da-010) | Profiles archived and checked against the release vocabulary. The residue moved to DA-028 |
| [DA-017](structure-and-invariants.md#da-017) | `by_unit` refused by semantic runs |
| [DA-018](boundaries-and-composition.md#da-018) | Extension versions pinned and verified (phase 0) |
| [DA-019](boundaries-and-composition.md#da-019) | Test sweep leases (phase 0) |
| [DA-021](local-reasoning-and-assurance.md#da-021) | Evidence citations checked (phase 0) |
| [DA-022](local-reasoning-and-assurance.md#da-022) | Dependency check covers the uv workspace (phase 0) |
| [DA-023](local-reasoning-and-assurance.md#da-023) | Binding §1 map populated (phase 0) |
| [DA-024](execution-fit.md#da-024) | Short seal, separate publication and evaluation |

**Inherited, not re-examined.** [DA-015](structure-and-invariants.md#da-015) and
[DA-025](execution-fit.md#da-025) keep their 2026-10-28 evidence date. Their subjects are legacy-only
and outside this baseline's scope.

**Lineage of continuing findings.** DA-001, 002, 003, 004, 005, 007, 009, 011, 012, 013, 014, 016
and 020 keep their identities where the structural cause continues. Each says how its subject
changed. DA-014 and DA-016 were reframed; DA-001 and DA-009 were narrowed.

## Reading and organizing the account

| Page | Main concerns |
|---|---|
| [domain-model-map.md](domain-model-map.md) | The go-forward model as found: contexts, concepts, authorities, translations, strengths |
| [semantic-model-and-authority.md](semantic-model-and-authority.md) | Model adequacy, operation bindings, authoritative meanings, vocabularies, identity, translations, compatibility, design-collection authority |
| [native-integrity.md](native-integrity.md) | Immutability, principals and privileges, structure authority, native evolution and deployment identity |
| [structure-and-invariants.md](structure-and-invariants.md) | Operational sets, outcomes, source coordinates, policy, value admissibility, run lifecycle, representatives |
| [served-claims.md](served-claims.md) | Coverage, selection status, evaluation, the read route, bounds, journey pinning, attribution |
| [boundaries-and-composition.md](boundaries-and-composition.md) | Legacy edges, consumerless surfaces, producer contracts, configuration |
| [execution-fit.md](execution-fit.md) | Re-derivation, consolidation scaling, native publication cost |
| [local-reasoning-and-assurance.md](local-reasoning-and-assurance.md) | Routes to current findings on these concerns; retired earlier findings |

Each finding has one primary home and lists every relevant FP, DP and CI reference. Pages may split
or merge as findings evolve. Finding IDs are stable and never reused. The
[writing guidance](../../../.claude/skills/design-principle-audit/references/audit-writing.md)
describes finding content.

## Ownership and history

- **Ownership.** This collection owns observations at its stated baseline:
  - reviews own proposed corrections and alternatives;
  - implementation plans own scheduled disposition and closure evidence;
  - architectural owners and ADRs own accepted design.

  Link to the relevant owner without reproducing progress. Existing source-review and plan finding
  IDs keep their meanings and dates.
- **Disposition of the earlier findings is stale.**
  - [Phase 0 §11](../../plans/phase-0_2026-10-28.md#11-findings-disposition) still lists DA-001
    through DA-025 as open, and the pivot coordinator explicitly declines to absorb them.
  - This refresh retires ten and keeps two inherited, but it does not edit plans.
  - The new findings (DA-026 onward) have no scheduled owner yet.
  - Reconciling both is for the plan owners.
- **Use by reviews.** A design review consumes an identified revision of this account. The binding
  grounds reviews on DESIGN §1.1, which is pre-pivot ([DA-011](semantic-model-and-authority.md#da-011)).
  A review should state which functional target it uses.
- **Refreshing.** Refresh in place before a new review engagement, using this baseline and the
  intervening changes to focus inspection. Reconsider unchanged code when its dependencies or
  expectations change.
- **Lineage and resolution.** Preserve finding identity and material lineage. Remove a resolved
  finding when its correction is established. Retired findings keep a stub at their anchor, and Git
  and the removal commit preserve the account.
