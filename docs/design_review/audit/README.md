# Design principle audit

The living diagnostic account of design principle misalignment, maintained by the
[audit skill](../../../.claude/skills/design-principle-audit/SKILL.md). The
[repository binding](../design_principles/binding/corpus-structure.md#design-principle-audit)
owns its place before a design-review engagement. Ordinary implementation reads its plan and
architectural owners; this collection is not default production-editing context.

<a id="baseline"></a>

## Baseline

| | |
|---|---|
| Audited source | commit `024bb33`, clean tree (no uncommitted changes included) |
| Date | 2026-10-28 |
| Standard | core 3.3 (principles, efficient-architecture heuristics, test-assessment companion for oracle independence only); code-intelligence profile 1.4, applied by analogy (documents for code, extraction methods for analyzers, agent answers for served claims); [binding](../design_principles/binding/corpus-structure.md) |
| Kind | First audit; there is no preceding baseline |
| Publishing commit | the commit that adds this account, distinct from the source baseline |

**Scope (operator, 2026-10-28): the implemented code plus the target model.**
- **Implemented code** is the primary evidence:
  - the `core/` package, settings, CLI and DB fixtures in `python/corpus-structure/`;
  - `tools/evidence/`;
  - provisioning and the `justfile`;
  - the process scripts, lightly.
- **The target domain model**, which is mostly design today, is assessed for adequacy and single
  authority where the code realizes it now or will:
  - DESIGN.md and D0–D9;
  - the S4 pack files that are the domain pack's design copies.
- **Labels.** Each finding says whether its subject is implemented, an accepted target or proposed.

**Focus.** The operator asked for full coverage with particular attention to deviations from the
semantic-model-first domain model: core §1 MUST, FP-04, A2, DP-01–DP-09, and CI-01–CI-06 and CI-11.
The aim is to inform follow-up design work while physical choices are still cheap. The
[domain model map](domain-model-map.md) records the model as found.

**Method.**
- Three read-only contributors examined the subject through three lenses:
  - representation, identity and contexts;
  - schema, vocabulary, storage and operation authority;
  - structure, boundaries, assurance and execution fit.
- The coordinator verified each decisive source and grouped the findings by structural cause.
- Two contributors ran scratch probes and comparison scripts on 2026-10-28. Their outputs are cited
  as observations and were not retained as evidence.
- No test suite, database or benchmark was run for the audit.

**Coverage limits.**
- **Not audited:** spike code under `docs/design_review/evidence/`, except where cited as evidence;
  the dormant Rust crate (no behaviour); `fixtures/`.
- **Tests:** examined only for oracle independence. Test architecture is the
  [test audit](../test-audit/README.md)'s separate scope. Its lead from this audit: the generated
  JSON Schemas are described as an independent oracle, although they come from the same models, so
  a wrong constraint passes both (`core/schemas/__init__.py`, D9 §2).
- **Design read only in the sections cited:** D5 beyond §1–§8, D7, D8 §2–§4 and §6, and D9.
- **Compiler code:** the S1/S4 compiler code was not read; P0-S-1 has not built it.
- **Suspected:** CI-06 for `VerificationPayload`, whose verdict names no stated model (phase 4).
- **Unsettled premise:** whether a project may combine several packs. It decides how severe
  [DA-005](semantic-model-and-authority.md#da-005)'s local-name ambiguity is.
- **Absence claims** (no check, no definition) rest on grep over `python/`, `tools/`, `scripts/`,
  `docs/design/` and `docs/adr/`.

**Change scenarios.** Seeds drawn from the plans, used to show each consequence:

| | Scenario |
|---|---|
| S1 | Add a predicate or an identity qualifier |
| S2 | Add a second domain pack (a business corpus) |
| S3 | A new rendition-adapter version changes segments |
| S4 | A new extraction method or model tier writes observations |
| S5 | Re-consolidate under a new schema version, migrating stored batches |
| S6 | Answer an agent query with evidence closure |
| S7 | Change a closed vocabulary (parse status, segment kinds) |
| S8 | Upgrade a pinned library, the interpreter or a server extension |
| S9 | Test a transformation in isolation |

S9 holds: core functions are pure and tested without infrastructure. Most scenarios meet one or
more findings below.

<a id="deviations"></a>

## Where we deviate from the domain model

At `024bb33` nothing produces wrong output: every closed set agrees and the key tests pass. The
deviations are structural, and they share a pattern. The model's types exist, but much of what they
mean is decided procedurally:
- over JSON shapes and literal subsets;
- in several independent places;
- without a version.

So the next qualifier, pack, vocabulary value or schema version has to be made in places that
nothing keeps in step. In order of consequence for follow-up design:

1. **[DA-001](semantic-model-and-authority.md#da-001), claim identity.**
   - Which qualifiers distinguish facts is split between code (core qualifiers), pack data (schema
     qualifiers) and prose.
   - A schema qualifier's canonical form is chosen from its JSON shape, not its declared range.
2. **[DA-009](semantic-model-and-authority.md#da-009), versions.**
   - The core contracts, the key scheme and derived forms carry no version.
   - `f1ba675` changed every key input with no version moving.
3. **[DA-002](semantic-model-and-authority.md#da-002), vocabularies.** Core closed vocabularies and
   the core qualifier list are hand-written in four to six places, and the planned mirror test
   covers only some of them.
4. **[DA-003](semantic-model-and-authority.md#da-003), category roles.** What a modality, segment
   kind or statement kind *does* is restated as a literal subset in each consumer, not declared as
   a property of the member.
5. **[DA-004](semantic-model-and-authority.md#da-004), JSON dumps.** Core operations reinterpret
   JSON dumps by tag and key name instead of consuming the typed model; one result is that a
   qualifier named `sentence` breaks frame handling.
6. **[DA-005](semantic-model-and-authority.md#da-005), translations.** The contexts are named, but
   their translations are not owned as complete contracts. The keyed candidate set drops batch
   alternatives and unsupported items, and naming is mixed beyond X2-01.
7. **[DA-006](semantic-model-and-authority.md#da-006), references.** References carry no kind, and
   two design sections name different owners for reference integrity.
8. **[DA-010](semantic-model-and-authority.md#da-010), source profiles.** Source profiles carry
   schema vocabulary outside any schema version.
9. **[DA-007](semantic-model-and-authority.md#da-007), unresolved references.** An unresolved
   reference is dropped rather than represented, and D1 and D2 treat it differently.
10. **[DA-008](semantic-model-and-authority.md#da-008), case.** Casefolding merges `X`/`x` and
    `\Sigma`/`\sigma` in labels and literal identity slots.
11. **[DA-011](semantic-model-and-authority.md#da-011), design copies.** Design documents restate
    executable contracts, and the copies have drifted.

The [domain model map's strengths](domain-model-map.md#strengths-to-keep) bound the remedies: one
canonical JSON function, content-addressed renditions, frozen absent-not-null models, one locator
contract, pure key functions with schema facts passed as data, and relational test oracles. The
audit diagnoses only. It does not choose corrections or render the A2 judgment; a design review
owns both.

## Findings

| ID | Finding | Subject | Page |
|---|---|---|---|
| [DA-001](semantic-model-and-authority.md#da-001) | Claim identity has no single declaration; qualifiers canonicalized by JSON shape | implemented, target | semantic model |
| [DA-002](semantic-model-and-authority.md#da-002) | Core closed vocabularies and the core qualifier list written by hand in several places | implemented, target | semantic model |
| [DA-003](semantic-model-and-authority.md#da-003) | Behavioural roles of categories hard-coded as subsets | implemented, target | semantic model |
| [DA-004](semantic-model-and-authority.md#da-004) | Core operations reinterpret JSON dumps | implemented | semantic model |
| [DA-005](semantic-model-and-authority.md#da-005) | Context translations not owned as complete contracts | implemented, target | semantic model |
| [DA-006](semantic-model-and-authority.md#da-006) | References carry no kind; reference integrity has two owners | implemented, target | semantic model |
| [DA-007](semantic-model-and-authority.md#da-007) | Unresolved references dropped rather than represented | implemented, target | semantic model |
| [DA-008](semantic-model-and-authority.md#da-008) | Canonical text form erases case distinctions | implemented | semantic model |
| [DA-009](semantic-model-and-authority.md#da-009) | Core contracts, key scheme and derived forms carry no version | implemented, target | semantic model |
| [DA-010](semantic-model-and-authority.md#da-010) | Source profiles carry schema vocabulary outside any schema version | target | semantic model |
| [DA-011](semantic-model-and-authority.md#da-011) | Design documents restate executable contracts, and copies drifted | target | semantic model |
| [DA-012](structure-and-invariants.md#da-012) | Operational closed sets with uneven authority and enforcement | target, proposed | structure |
| [DA-013](structure-and-invariants.md#da-013) | Keying and frame outcomes are prose | implemented | structure |
| [DA-014](structure-and-invariants.md#da-014) | Locator identity limits narrower than a plan's closure check | implemented, target | structure |
| [DA-015](structure-and-invariants.md#da-015) | No rule for selecting the current pass's M19 verdicts (suspected) | target | structure |
| [DA-016](structure-and-invariants.md#da-016) | Confidence policy data split between file and prose | proposed | structure |
| [DA-017](structure-and-invariants.md#da-017) | `agent_reuse: by_unit` reuse key undefined (suspected) | target | structure |
| [DA-018](boundaries-and-composition.md#da-018) | Server extension versions neither pinned nor reconciled | implemented, target | boundaries |
| [DA-019](boundaries-and-composition.md#da-019) | Test-database sweep can drop another session's template | implemented | boundaries |
| [DA-020](boundaries-and-composition.md#da-020) | Cluster coordinates repeated; provisioning prose stale | implemented | boundaries |
| [DA-021](local-reasoning-and-assurance.md#da-021) | Design claims cite evidence records by free text | implemented | assurance |
| [DA-022](local-reasoning-and-assurance.md#da-022) | Dependency check narrower than AGENTS.md states | implemented | assurance |
| [DA-023](local-reasoning-and-assurance.md#da-023) | The binding's map of binding decisions is empty | binding | assurance |
| [DA-024](execution-fit.md#da-024) | Final transaction holds the run lock across measurement and evaluation | target | execution fit |
| [DA-025](execution-fit.md#da-025) | Keying repeats rendition-wide work per statement | implemented | execution fit |

## Reading and organizing the account

| Page | Main concerns |
|---|---|
| [domain-model-map.md](domain-model-map.md) | The model as found: contexts, concepts, authorities, translations, strengths |
| [semantic-model-and-authority.md](semantic-model-and-authority.md) | Model adequacy, authoritative meanings, independent consumer interpretation, versions |
| [structure-and-invariants.md](structure-and-invariants.md) | Distinctions, state, lifecycle, enforcement |
| [boundaries-and-composition.md](boundaries-and-composition.md) | Library and infrastructure boundaries, configuration, lifecycle |
| [local-reasoning-and-assurance.md](local-reasoning-and-assurance.md) | Diagnostics, lineage, labelled claims, verification |
| [execution-fit.md](execution-fit.md) | Necessary and repeated work, locks, preparation |

Each finding has one primary home and lists every relevant FP, DP and CI reference. Pages may
split or merge as findings evolve. Finding IDs are stable and never reused. The
[writing guidance](../../../.claude/skills/design-principle-audit/references/audit-writing.md)
describes finding content.

## Ownership and history

- **Ownership.** This collection owns observations at its stated baseline:
  - reviews own proposed corrections and alternatives;
  - implementation plans own scheduled disposition and closure evidence;
  - architectural owners and ADRs own accepted design.

  Link to the relevant owner without reproducing progress. Existing source-review and plan finding
  IDs (for example X2-01 and IR-13 in the phase 0 plan) keep their meanings and dates.
- **Refreshing.** Refresh in place before a new review engagement, using this baseline and the
  intervening changes to focus inspection. Reconsider unchanged code when its dependencies or
  expectations change.
- **Lineage and resolution.** Preserve finding identity and material lineage. Remove a resolved
  finding when its correction is established; Git and the removal commit preserve the account.
