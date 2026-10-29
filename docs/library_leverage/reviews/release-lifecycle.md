# Release lifecycle and the prepared-release contract

This page records comparative judgments for:
- CBO-003 (every read session rebuilds and re-verifies the release);
- CBO-013 (the prepared-release contract, including the NaN/inf gap);
- CBO-009 (identity determinants);
- CBO-002 (the product composer);
- CBO-021 (the SchemaView lifecycle);
- CBO-017 (the execution catalog);
- CBO-024 (the ontology workaround).

Baseline, inputs and method are in the [README](README.md). Paths are relative to
`python/corpus-structure/src/corpus_structure/`. Every recommendation here is **Proposed**.

<a id="cbo-003"></a>

## CBO-003 — Split release opening from release verification

**Premise, measured.** `load_release` re-runs full preparation in every snapshot: serving, five
evaluation sites, cut materialization, regeneration and activation.

On the statistics pack, a cold `prepare_release` took **2.18–2.45 s** over three fresh processes
([evidence](../../design_review/evidence/2026-10-29_library-leverage-review-probes/README.md)). Of
that:
- **1.03–1.12 s** is OWL/SHACL graph generation, which no read path uses.
- **0.68–0.78 s** is the execution companion's compile, which itself builds and discards contracts
  OWL/SHACL.

Every load also refuses on any change to the version of any listed library. The read path therefore
depends on the whole producer toolchain.

Two premise corrections:
- `ci schema compile --out` now consumes the graph and `json_schema/*` artifacts, but no *read*
  path does.
- The archive already holds everything needed to rebuild the Pydantic boundary except each
  property's native primitive and its alias.

**Options.**
- **A.** Retain.
- **B.** Re-prepare without graphs on read.
- **C.** A two-stage compiler with separate operations:
  - **`open_release`** rebuilds the runtime boundary from archived products, with no LinkML
    involved. It checks the archive digest and the compiler and profile, and compares the
    regenerated `json_schema/*` digests with the archived ones as its library-sensitive oracle.
  - **`verify_release`** is today's full re-derivation, run at persist-replay, at activation, at run
    start and on an explicit operator command.
- **D.** A native verification record alone. It is sound only under [`sem.*` immutability](native-integrity-and-execution.md#sem-immutability)
  and removes only the row comparison.

**Revealing case: tamper evidence gets weaker.** Under C, someone who can consistently edit
`prepared_bytes`, `content_digest` and the projection rows would be served forged products until the
next verify. What remains of that risk depends on the immutability decision:
- **With immutability enforced by triggers:** only the owner or a superuser can forge, which is the
  same threat class as editing the code.
- **Without it:** keep a per-snapshot projection-row comparison inside `open_release`. The realistic
  single-operator threat is accidental corruption, which the digest catches.

**Recommendation: recommended target C, plus a process memo.**
- **Compiler 11.** Add `PropertyDefinition.native_range` and `alias`. This bumps the compiler and
  changes archive bytes.
- **Stage 2.** Factor out `build_boundary(definitions, vocabularies, rule_fragments)`. Preparation
  itself calls stage 2, so there remains one model builder.
- **Process memo.** Key it by (database identity, release_id, `content_digest` read in the
  snapshot, compiler stack). It replaces consumer caches such as the MCP `interpretation()` cache,
  and gives tests an explicit cold path to clear
  ([DTA-007](../../design_review/test-audit/evidence-and-discrimination.md#dta-007)).
- **Usage.** Serving, explain, evaluation and resume use open. Persist-replay, activation and run
  start use verify.
- **What disappears.** Per-session graph generation, re-compiling the companion on read, reading
  `sem.input` on read, the second library list, and consumer-local caches.
- **Transition.** Land this before SP-09's production regeneration. Otherwise the regenerated
  release is stranded by the compiler bump.

**Rule impacts.**
- ADR-0024's "only an explicit archive load recompiles" wording.
- `domain-model-completeness.md`'s "preserve exact manifest and relational-projection validation on
  reload" needs an amendment separating verify from open.
- `semantic-model-and-releases.md` §identity already separates runtime artifact identity.

<a id="cbo-013"></a>

## CBO-013 — Prepared-release index, and closing the NaN/inf gap

**Premise.** Confirmed and growing.
- The serving Reader scans definitions per row, and re-parses `operation_class` registry rows on
  every call.
- There are three `compact` implementations.
- `native_constraints` already archives `native_range` but has no product owner.
- **Correctness gap.** `property_adapter` builds `TypeAdapter(annotation)` without the model's
  config, so it accepts NaN and infinity that the generated models refuse
  ([pydantic](../libraries/pydantic/README.md#applicability-cbo-013)). This now sits on the serving
  boundary.
- **Pydantic serializes NaN as JSON `null` by default**, so a NaN would be served as null. That is a
  latent fidelity hazard, scratch-checked by the G1 reviewer.

**Options for the gap.**
- **(i)** Propagate config at each construction site. This needs a branch, because `config=` raises
  for bare model classes.
- **(ii)** Compile `float`/`double` as `Annotated[float, Field(allow_inf_nan=False)]`.

Scratch-checked on Pydantic 2.14.1, (ii):
- rejects NaN and infinity in derived adapters;
- leaves the JSON Schema unchanged, so archived bytes are unchanged;
- does not change how the models themselves behave.

**Options for the index.**
- Consumer caches (today).
- A non-identity index on the `PreparedRelease` root.
- Identity-bearing fields, for facts that are genuinely part of the product.

**Revealing case.** Building every class × property adapter eagerly enlarges preparation. Memoize
per release instead.

**Recommendation: recommended target, in two steps.**
1. **Fix the gap now** with option (ii). It is a correctness fix with no byte change. Also apply
   `strict` config in `property_adapter` when the top-level annotation is not a model.
2. **Add a `ReleaseIndex` on the root.** It is non-identity, held outside the archived projection
   ([LOP-X004](../assessment-patterns.md#lop-x004) countercondition), and holds:
   - class and property lookups by name and by IRI;
   - `native_range` (an identity field after CBO-003);
   - memoized field adapters built from the retained model map, not from `adapter._type`;
   - one expand/compact over archived prefixes with longest-namespace matching;
   - parsed enum, metric and `operation_class` definitions.

   Also: keep the conjunctive `_bounds`; give the type-chain walks one local helper; delete the
   duplicated alias map.

**curies is not adopted.** The gain is marginal, it would add a declared dependency, and its
semantic differences need wrapping.

<a id="cbo-009"></a>

## CBO-009 — Identity determinants, tiered by effect

**Premise.**
- Two copies of the list exist.
- **New finding:** vocabulary libraries are redundant as identity determinants. Resolved members are
  already in the identity manifest, and supplied snapshots must match, so OAK, term-validator and
  pronto output changes are caught by content. This **corrects the library assessment**, which
  suggested adding pronto.
- Acceptance-only libraries gate preparation but do not shape bytes.
- The run manifest omits SymPy.

**Options.**
- **A.** One corrected constant with exact-label refusal everywhere. Every listed library would then
  need a hold.
- **B.** Tiered by effect.
- **C.** Content-addressed identity with libraries as provenance only. This changes how ids are
  derived, at ADR level.

**Revealing case.** Pydantic validation semantics can change without the JSON Schema changing.
Those changes affect operations, and belong in run manifests.

**Recommendation: recommended target B.**
- **Identity determinants** are the byte determinants only: linkml, linkml-runtime, rdflib,
  pyoxigraph, pydantic and PyYAML. They are kept in one constant beside `SEMANTIC_COMPILER_VERSION`,
  and `releases.py` checks against the *archived* manifest.
- **Acceptance libraries** (jsonschema, cattrs, rule-engine, pyshacl) are re-run at verify.
- **Dependency moves:** declare and exactly pin pyoxigraph; drop valuesets from the set and offer it
  for removal; add SymPy to the math run manifest.
- **When a byte determinant moves:**
  - new preparations get new ids;
  - existing realizations stay readable under CBO-003-C;
  - activating the old release or starting runs under it fails verify, so the operator activates the
    newly prepared release through `ci regenerate`;
  - no `pins.md` hold is needed.

**Rule impact.** `semantic-model-and-releases.md:53`: "compiler versions" in the digest should read
as byte determinants.

<a id="cbo-002"></a>

## CBO-002 — Separate acquisition from pure composition

**Premise.** `regeneration.prepare_pack(s)` exists, but:
- It nests three wrapper roots, so identity depends on recipe order.
- `observation_inputs` runs twice, each time building a private `_view` only to check idempotence.
- Multi-pack composition runs a full `prepare_release` per pack just to harvest sources.
- Acquisition defaults are implicit: `core.yaml` through `__file__`, core rules at
  `pack.parent/core/...`, `SOURCES_DIR`, and the phase0 registry.
- 32 test files compose releases themselves ([DTA-005](../../design_review/test-audit/support-structure.md#dta-005)).

**Options.**
- **A.** Retain and patch.
- **B.** One root with LinkML `importmap` dicts. Not decisive: it needs dicts after URI
  materialization, falls back silently on missing imports ([LOP-X006](../assessment-patterns.md#lop-x006)),
  and never refuses duplicates. This corrects the library applicability's lead.
- **C.** Split acquisition from pure composition over the existing `_view` seeding.

**Revealing case.** Release ids change with composition. That is acceptable under clean regeneration
but must be deliberate. Compiler unit tests that deliberately use minimal hand bundles must not be
forced through the composer.

**Recommendation: recommended target C.**
- **`acquire_pack(path) → PackInputs`.** Named bytes with each origin recorded. Core rules and source
  profiles are explicit, and core comes through one `trusted_semantic_core()`, like
  `trusted_execution_inputs`.
- **`compose_release(*PackInputs) → (bundle, deps, profile)`.** Pure, with one root over the domain
  sources, observations, the agent module (computed from a transient candidate preview) and
  analytics. It refuses reserved names.
- **No private `_view` call** from `observations.py`.
- **Tests:** consumer and native-journey tests use `compose_release` over fixture `PackInputs` at
  session scope, together with the [CBO-010](engineering-workflows.md#cbo-010) template.
- **Scheduling:** schedule the identity change together with the CBO-003 compiler bump.

<a id="cbo-021"></a>

## CBO-021 — SchemaView lifecycle

**Recommendation: retain current, with two small adjustments.**
- Induce every class eagerly once on the merged view, so later copies do not depend on call order.
- Optionally drop the ontology's private-view deepcopy, while keeping its output copy.

Keep the `schema_map` seeding with a LOP-11 revisit on LinkML upgrades.

The redundant previews disappear with CBO-002. `materialize_derived_schema` remains ruled out, and
moving to importmap gives no gain. Under CBO-003-C, LinkML runs only at preparation and verify.

<a id="cbo-017"></a>

## CBO-017 — Execution catalog form

**Recommendation: retain current, plus cattrs `= ()` defaults** with `kw_only` dataclasses, which
delete `_collection_defaults`. The execution content bytes are unchanged.

About 31 of roughly 35 `_refs` checks are global references that class ranges could express. Moving
them would still mean:
- a generic in-document reference pass;
- a duplicate-reference policy;
- a changed `model_id`;

all to save about 40 one-line checks, with a single consumer. Drift between the hand dataclasses and
the schema already fails fast.

Revisit class-ranged references only if a second document with in-document references appears. The
generator premise is rejected: gen-python output is mutable and coercing, and PydanticGenerator has
no frozen option.

<a id="cbo-024"></a>

## CBO-024 — Ontology workaround

**Recommendation: retain current.**
- linkml-term-validator 0.4.5 is still the latest release; the LOP-11 revisit trigger is a new
  release.
- Building OAK adapters in memory would need the plugin's private `_adapter_cache`.
- No production model uses dynamic enums.
