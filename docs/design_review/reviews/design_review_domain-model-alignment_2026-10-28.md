# Design review: domain-model alignment through one integrated data model (design/target, combined focus)

**Reviewer:** fresh `design-reviewer` subagent (Claude Opus 5.5), 2026-10-28, read-only; published
by the coordinator without change to its judgment. **Baseline:** `6f31f75` on `main`, clean tree;
the untracked operator overviews in `docs/libraries/` were read for orientation only.
**Audit consumed:** the first account, published in `f9695d3`, with source baseline `024bb33`
([audit](../audit/README.md)). Only audit pages and STATUS changed between `024bb33` and
`6f31f75`, so its premises still hold.
**Prior review reconciled:** [phase 0 contract layer](design_review_phase0-contract-layer_2026-10-28.md).
**Supporting document:** the [target model](design_review_domain-model-alignment_2026-10-28_target-model.md).
It holds the specification that planning needs; this page holds the argument, the findings,
the judgments and the rule impacts. **Decision: Revise.**

## Summary

The system turns a set of documents into evidence-backed knowledge for any domain (DESIGN §1.1).
Statistics is the calibration domain; business documents and email are the generality check
(§1.3). The domain model is the centre of the design:

- D1's single claim form, with typed values, condition trees and bindings;
- D2's LinkML packs, compiled into every consumer;
- D3's PostgreSQL store, with knowledge materialized per run.

Several choices around the model are strong, and this review keeps them:

- observations are separate from knowledge;
- renditions are content-addressed;
- one canonical JSON function sits behind every key;
- frozen models represent an absent value as absent, never as null;
- one locator contract refuses ambiguity with typed reasons;
- key functions are pure and receive schema facts as data.

**The defect.** The model is not yet the authority over behaviour. Its types exist, but much of
what they mean is decided elsewhere, and this falls short of the core §1 MUST (FP-04, A2):

- **Facts have no single place of authorship.** Closed sets, defaults, the core qualifier list,
  which qualifiers make two claims different facts, what each category member does, and
  cross-field invariants are each written by hand in two to six places: Python `Literal`s,
  `vocab.py`, `core.yaml`, `keys.py`, Pydantic validators, D3's DDL and design prose. Most of
  these have no derivation between them (DA-001, DA-002, DA-003, DA-011, DA-012, F01).
- **Operations read representations, not the model.** Keys pick a qualifier's canonical form from
  its JSON shape. Traversals dispatch on tags in `model_dump` output. A citation is found by the
  key name `sentence` (DA-001, DA-004, DA-005, DA-013).
- **Relationships and unknowns are not first-class.** References are bare strings. An unresolved
  reference is dropped. Every reference a query joins on lives inside JSONB. Case folding merges
  distinct mathematical objects (DA-006, DA-007, DA-008, F04).
- **Change is not part of the model.** The core contracts, the key scheme, payloads and derived
  artifacts carry no version (DA-009). Source profiles carry schema vocabulary outside any schema
  version (DA-010). Other changes are unmodelled too (DA-014, DA-015, DA-017, DA-021).
- **Some execution and environment facts are misplaced.** They are local (DA-018 to DA-020 and
  DA-022 to DA-025). The one that matters for the workload is DA-024: the run lock is held through
  measurement and evaluation.

Nothing produces wrong output today. No production data exists, and migration 0001 and the key
freeze are still ahead (P0-S-1, P0-F-4). That makes this the cheapest point to correct the
authority layer.

**The target** is one model with governed projections. The *corpus-structure model* is a set of
LinkML schemas in three modules:

- `core`: the knowledge shapes, the vocabularies with their member properties, the qualifier
  specifications and the key-scheme declaration;
- `system`: the classes of `meta`, `ops`, `kb` and `eval`, with their closed sets, invariants and
  relationships;
- the domain packs.

The modules have two lifecycles. Core and system form a *model revision*, released with code.
Each pack is a *schema version*, held as data. Every consequential fact is authored once in the
model. The representations are generated from it by compilers that are pure functions of
`SchemaView`:

- the Python the core imports, generated and checked in, so that `core` still depends only on
  Pydantic and `regex` at run time;
- the per-version Pydantic models;
- SQLAlchemy `MetaData`, which drives Alembic;
- CHECKs and foreign keys;
- Arrow schemas;
- JSON Schemas carrying a versioned `$id`;
- the rule-engine context;
- the annotator reference.

Physical access-path choices (indexes, BM25, partial predicates, views) live in one hand-written
overlay bound by name to the generated tables. Operations stay ordinary domain functions over the
generated types.

**The store's shape.** PostgreSQL remains the transactional authority for instances:

- every *relationship* a query joins on or an invariant constrains becomes relational (FKs and
  edge rows);
- decision-relevant scalars become columns;
- every *value* stays a typed nested value whose schema the model governs.

**Change.** Change becomes a modelled concept, with revisions, a payload-schema registry and
change records. Each change record carries a compatibility class that decides its route.

**The operator's no-migration callout** is sound for one well-defined class of data: immutable,
versioned payloads that no constraint, key, index or query reads, plus their analytic projections
in Parquet and DuckDB. It is unsound as a general route. Anything PostgreSQL enforces or reads
takes the migration route.

**A centralized relational engine** is worth designing for, as a *contract* rather than a
mechanism. The consolidation pool becomes a set of model-typed Arrow relations:

- set-based steps (slot and alternative grouping, conflict joins, pack `views:`, metrics, run
  diffs, exports) run in DuckDB 2.0 in process;
- transactional set work stays in PostgreSQL SQL;
- identity, canonical forms, TeX, SymPy and inference stay in Python and reach the engine as data.

The review recommends twelve corrections (R01–R12). It also proposes changes to accepted rules
(review#RC01–RC19), which take effect only after operator confirmation in plan creation.

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | The domain model as implemented: `python/corpus-structure/src/corpus_structure/core/` (all modules), `settings.py`, `alembic/env.py`, `tests/conftest.py` (database fixtures), `tools/evidence/src/corpus_evidence/` (model, catalog), `scripts/pg_provision.sh`, `ops/postgresql/`. The model as accepted target: DESIGN §1–§2; D1 complete; D2 §1–§8 and §12.1; D3 complete; D4 §1, §4.3, M01; D5 complete; D6 §2–§4, §6–§7.2; D7 §3.5, §5.1–§5.2; D8 §5; D9 §1–§2; ADR-0013, 0014, 0016, 0017, 0019; the S4 pack files and S4 report; phase 0 plan §3, §4, §11; the roadmap. Baseline `6f31f75` |
| Standard | Core 3.3 with efficient-architecture heuristics 1.0. Code-intelligence profile 1.4, applied by analogy: documents for code, extraction methods for analyzers, agent answers for served claims. [Binding](../design_principles/binding/corpus-structure.md) |
| Tier · purpose | Design · target |
| Focus (operator, 2026-10-28) | **Combined.** *Libraries:* LinkML, Pydantic, jsonschema, SQLAlchemy 2.1, Alembic 1.20, pglast 8.7, PyArrow 26, pgpq 0.12, adbc-driver-postgresql 1.13, psycopg 3.3, psycopg-pool, pgvector, DuckDB 2.0. *Principles:* core §1 MUST, FP-04, A2, DP-01–DP-09, CI-01–CI-06, CI-11. All foundations, A1–A4, G1–G8 and the CI gates are assessed as the template requires |
| Target state (operator) | Complete alignment with those principles through a fully relational, integrated data model. Every representation is a governed projection of one model that knows each representation and how it may change |
| Audit input | [Audit](../audit/README.md) at `f9695d3`, source `024bb33`; DA-001…DA-025 each receive a disposition (§7) |
| Maturity and outcome | Built: P0-F-1, P0-F-2a, P0-I-0 and P0-F-2b. Next: the pack compilers (P0-S-1) and migration 0001 (P0-F-4). This decision should let both build on one model authority before keys and 0001 freeze |
| Workload premise | **Phase 0:** 78 Siegrist pages and the `phase0-golden` slice, with agent proposals only. **Phase 1:** a full first pass over about 2,500 units, giving about 10⁵ observations and 10⁴–10⁵ claims per run (D3 §11, an estimate). Up to three route iterations plus derive. Agent completions arrive while runs finish, and long runs are sequences of runs that reuse finished tasks. **Phase 2:** linking and merges. **Phase 5:** an NLP-natural second corpus, with tables with units, email threads, valid time and multi-attribute identity. **Deployment:** one host (32 cores, 188 GB shared with GPU work), one PostgreSQL 18 cluster, two processes (orchestrator and MCP server) plus worker pools |
| Expected changes | The audit's S1–S9. A business pack (§1.3) as the domain extension. Two mechanism substitutions: the consolidation pool as Python objects or as relations, and bulk writes through psycopg or Arrow encoders. Growth: the phase 1 final pass with concurrent agent completions |
| Method and coverage | Decisive sources read directly. Two contributor notes, on the schema-authority chain and on physical representation (2026-10-28, not retained in the repository), were used as leads; their consequential claims are carried below with their labels. Re-checked directly on 2026-10-28: installed LinkML 1.12.1 `pydanticgen` (no `discriminator` anywhere), `sqltablegen` (native `Enum`, no `CheckConstraint`, no JSONB), `RelationalModelTransformer`, `SchemaView` helpers, SQLAlchemy 2.1.5 `CreateView`/`CreateTableAs`, Alembic 1.20.0 `ext/checkconstraint_byname`. Context7 cross-checks: LinkML `in_subset` and PostgreSQL 18 generated-column and FK restrictions. Overviews read: `pyarrow.md` §2.3–§2.4, §4, §10, §13–§14; `duckdb_2.md` §2, §3.5–§3.6, §6.5, §7.2, §9.5, §10.3, §13.2; `alembic.md` §4.2, §6.5; `linkml.md` §3.4, §7.3. No probe, test, database or benchmark was run |
| Not examined | `core/tex.py` and the math grammar (taken as accepted); spike code beyond the S4 pack; D7 alignment; D8 MCP tools; the GLiNER2 compiler. None of these is a premise of the verdict |

**Premise that could change a recommendation:** whether one project may combine several packs.
The audit left this unsettled. It decides how rule-view qualifier names and the per-version
vocabulary are scoped (R04, R05). The target treats a combination as one schema version whose
local names must be unique, checked at compile time. A different answer changes that check, not
the architecture.

## 2. The model as it governs behaviour today

### 2.1 Who decides each consequential fact

| Fact | Authored at `6f31f75` | Also stated or interpreted in | Finding |
|---|---|---|---|
| Modality members and default | `batch.Modality` `Literal`, `DEFAULT_MODALITY` | `core.yaml` `ClaimModality` with `ifabsent`; D1 §5.2 | DA-002 |
| What a modality does | nowhere as a declaration | `keys.claim_parts` (`cited`); D5 §5.5 (`asserted`, `defined`); D8 default filter (`supposed`); INV-06 | DA-003 |
| Core qualifier list | `CORE_QUALIFIERS`, `StoredQualifiers` fields, `keys.py` constants | `core.yaml` slots; D3 §6.1 | DA-002 |
| Which qualifiers enter the claim key | `keys.claim_parts` for core qualifiers; the pack's `ci:identity_qualifiers` | D1 §5.2, §10.1; D5 §5.4, §5.5 | DA-001 |
| A schema qualifier's canonical form | the JSON shape it has (`keys.canonical_qualifier`) | — | DA-001 |
| What a segment kind does | `locators.annotation_units`, `keys.statement_anchor` | D3 BM25 predicate; D4 kind lists; `ci:target` strings | DA-003 |
| Operational closed sets | `vocab.py` | D3 CHECKs (generation planned in P0-F-4); D4 `Method.unit_type`; D6 policy literals; stage-name literals in views | DA-012 |
| Cross-field invariants | four Python copies of span ordering (`batch._Span`, `payloads._Span`, `StoredPhrase`, `StoredPhraseNode`); scope ↔ segment in two models; parse status ↔ reason | D3 CHECKs on `kb.span`, `kb.entity`, `kb.segment`, `kb.claim` | **F01** |
| Value kinds and condition operators | `values.py` | `canonical_value`, `canonical_condition`, `claim_refs`, `_bindings` (by tag); `core.yaml` mirror | DA-004 |
| Reference kinds | none (bare strings) | `Keys.of` over all tables; the side table (two named owners) | DA-006 |
| Relational structure | D3 DDL text | the planned `core/db` "from D3"; D3 §6.2 payload table | DA-011 |
| Versions | the schema version, hashed over the pack and the `core.yaml` mirror | — | DA-009 |

### 2.2 Five structural causes

**A. The model's facts have no single place of authorship.** ADR-0017 divides ownership by kind
of artifact: Pydantic owns the core shapes, LinkML owns the domain vocabulary. The facts the
system interprets cut across that division. The modality concept, for example, covers:

- its members and its default;
- its effect on identity (`cited` makes the attribution identifying);
- its role in queries (`supposed` forms a premise);
- its role in conflict detection (`asserted` and `defined` can conflict).

Each consumer states one part of it. The same holds for segment kinds and for the qualifier list.
The prior review judged G1 a pass because the `core.yaml` mirror is "held by a contract test". The
audit shows the mirror test covers value tags, bind kinds, binding fields, `EntityRef` and evidence
roles, and nothing else. Modality, polarity, scope extent, statement role, parse status, the
defaults and the qualifier list lie outside it (DA-002). So the G1 pass was too broad.

**Invariants have the same gap, and the audit did not record it (F01).** The DB CHECKs restate
Pydantic validators with no derivation between them. Span ordering alone exists in four Python
copies plus `kb.span`. A legitimate invariant change would be made in five places, and IR-13's
empty-text segments are a candidate for exactly such a change.

**B. Operations interpret representations instead of the model.**

- `keys.py` works over `model_dump(mode="json")` and re-decides meaning from tags and key names.
  An unknown value tag is keyed "as written" (`keys.py:138`). A schema qualifier dict with `t` or
  exactly `ref` is read as a value or an entity reference. Every other string is casefolded
  (`keys.py:454-462`).
- `cited_sentences` and `frame._rewrite` treat any key named `sentence` or `anchor` as a citation,
  so a qualifier named `sentence` breaks frame handling (`batch.py:324-343`, `frame.py:92-106`).
- `KeyedCandidateSet` is not a complete translation of a batch. It lacks alternatives,
  unsupported items, the derivation fields and the rendition identity, and it uses `None` where
  batches use `MISSING` (`candidates.py`).
- Drop reasons are `str(error)` (`keys.py:571` and five other sites), so C1 would have to
  classify prose.

These are all the "output-only model" shape: domain-named records exist, and procedures supply
their meaning independently (DA-001, DA-004, DA-005, DA-013). All code read at `6f31f75`
(Implemented).

**C. Relationships and unknowns are not first-class.**

- Every reference is a bare string: `EntityRef.ref`, `CandidateClaim.subject`, identity-slot
  values, binding targets. `Keys.of` resolves any id against the entity, statement and claim
  tables alike (DA-006).
- An `"outside"` statement keeps only its kind. Its citing claim is dropped and coverage stays
  silent (DA-007).
- Case folding merges `X` with `x`, and `\Sigma` with `\sigma`, in labels and literal identity
  slots (DA-008).
- In the store (F04), D3 keeps decision-relevant structure inside `kb.claim.qualifiers` JSONB:
  - modality and polarity, which every default D8 query filters on;
  - the attribution entity;
  - condition-tree `claim` references, which are the premise relationships D8's
    `transformations_of` and "premises are always returned with it" must join on;
  - entity-ranged schema qualifiers.

  Identity slots sit in `kb.entity.attrs`, which `family_profile` filters without an index.
- So INV-08 (condition references within the same run) and reference integrity have no
  store-level enforcement point. Premise joins go through JSON paths at run scale, an unexamined
  physical route (A4 unresolved).

**D. Change is not part of the model.**

- The schema version covers the pack and the `core.yaml` mirror, not the authoritative core: not
  the Pydantic shapes, not `keys.py`'s canonicalization, not the token form. `f1ba675` changed
  every key input with no version moving (DA-009).
- Generated JSON Schemas carry no `$id`, and `kb.observation` has no payload version (DA-009).
- Derived forms do not record their derivation. Re-location edits a frame in place under an id
  that results reference (DA-009).
- Source profiles name statement kinds and a predicate outside any schema version (DA-010).
- Several smaller changes are not modelled:
  - the locator limits (DA-014);
  - which M19 pass is current (DA-015);
  - the `agent_reuse` dependency (DA-017);
  - design citations of superseded evidence (DA-021).

**E. Execution and environment facts.** These are local:

- extension versions (DA-018);
- the test-database sweep (DA-019);
- coordinates (DA-020);
- the dependency check (DA-022);
- the empty binding map (DA-023);
- repeated keying preparation (DA-025).

DA-024 is the one structural execution defect. D6 §3.1 has the final consolidation transaction
lock the run row across the finalize pass, the M19 counts, `measure` and `evaluate`. At phase 1
scale, agent completions and twin settlement would stall for that whole terminal computation.

These five causes are not one root cause:

- A and B share a remedy direction: one model, and operations over its types.
- C needs representation choices.
- D needs a new concept, the change record.
- E is local.

### 2.3 Reconciling the prior review's "one validation authority (Pydantic)"

The prior review listed "one validation authority (Pydantic) across tiers" as a strength. Read as
a statement about the *validation point*, it is right and should be kept. JSONB is validated once,
at the Pydantic boundary where it enters, and never again on write (D3 §6). This is the
assurance economy of H19 and DP-03: enforce where uncertainty enters, then carry established
validity.

Read as a statement about *semantic authority*, it is wrong. The facts those validators enforce
are authored independently in `core.yaml`, `vocab.py`, D3's CHECKs, `keys.py` and design prose
(DA-002, F01). The reconciled position, which this review adopts:

- keep one validation point per trust boundary;
- move the authority for what it validates into the model;
- generate the validator from the model.

### 2.4 Fact and fidelity (code-intelligence profile, by analogy)

| Fact family or relation | Provider and revision | Fidelity | Coverage and unknowns | Identity | Gap |
|---|---|---|---|---|---|
| Renditions, segments, sentences | M01/M03 adapter config (build provenance) | extracted | `parse_status` + reason per segment | content digest; locators | none material (strength) |
| Math values | M11 grammar version | derived; `parse` outcome typed | `ok`/`partial`/`ambiguous`/`failed` | token form (ADR-0012) | key-scheme drift undetected (DA-009) |
| Claim proposals (agent, LLM) | M24/M10 task and config | inferred by a method; recorded as an observation | `rejected` items with reasons | local refs → keys | translation incomplete (DA-005); unresolved refs dropped (DA-007) |
| Consolidated claims | consolidation, per run | `establishment`: stated, derived or agent-asserted | statuses; fates per unit (D3 §8) | `clm:` keys | identity undeclared (DA-001); case (DA-008) |
| Claim → claim and claim → entity relations | consolidation | derived from typed values | none recorded when a target is missing | none of their own (inside JSONB) | F04, DA-006 |
| Verifications (M19) | the M19 task per pass | derived (rule outcome) | failing outcomes only, with per-rule counts | claim key | pass selection undefined (DA-015); verdict model unstated (CI-06, suspected in the audit) |
| Served answers | `serve`, pinned run | per the query's model | coverage per scope (D8 §5) | run id; page tokens | relies on F04 for premise and evidence closure (CI-11 unresolved; not built) |

### 2.5 Strengths that bound the remedies

Each strength below sets a condition the target must meet.

| Strength | Condition on the target |
|---|---|
| One canonical JSON function (NFC, sorted keys, floats refused) behind keys, digests and config hashes | Identity stays computed in Python and is passed to any engine as data. No key is ever computed from `jsonb::text`, VARIANT or Arrow bytes |
| Content-addressed renditions, digest leaving defaults out | Generated models must reproduce `exclude_defaults` behaviour exactly. Scheme conformance vectors (R02) detect a drift |
| Frozen models, `extra="forbid"`, `MISSING` never null; one form factory sharing shapes between forms | The generator must reproduce them, and the model's `ci:form` declarations keep one declaration for both forms |
| One locator contract with typed refusals, prepared once | Unchanged. Its typed-reason pattern is extended to keying and frames (R07) |
| Pure key functions receiving schema facts as data (`KeySchema`, `LabelRules`) | `KeySchema` becomes a compiled artifact of the model (R02) |
| One enum per D3 CHECK list (all 39 matched on 2026-10-28, per the audit); 0001 planned to generate CHECKs | Generalized: every CHECK comes from the model |
| Key tests with relational oracles; an independent token-form parity fixture | Kept independent of generation (R12) |
| ADR-0017: the pack owns domain vocabulary | Kept. What changes is that core vocabulary and shapes join the same model |
| `core` imports only the standard library, Pydantic and `regex`; modules acyclic; S9 holds | Generated Python is checked in, so the runtime dependency direction is unchanged |
| Queue claiming and `attempt` fencing; reuse keyed on content; the BM25 predicate from one constant; per-run rebuild | Kept. The one-constant pattern becomes the rule for every SQL literal list |

## 3. The target: one model, governed projections

The supporting [target model](design_review_domain-model-alignment_2026-10-28_target-model.md)
specifies this at planning precision:

- modules and lifecycles;
- concepts and contexts;
- the declaration vocabulary;
- each projection, its generator, what it enforces and how it changes;
- the relational projection of knowledge;
- translations;
- the identity model;
- the schema-change model;
- the placement of each data operation.

Its shape:

```text
                         the corpus-structure model (LinkML)
  core module ─────────────── system module ─────────────── domain packs
  knowledge shapes; vocab-     meta/ops/kb/eval classes;       classes, predicates,
  ularies + member properties; closed sets; invariants;        qualifiers, enums, subsets,
  qualifier specs; key scheme  relationships; payload classes  rules, views
      └──────── model revision (released with code) ────────┘   schema version (data;
                                                                its hash includes the revision)
                 │ compilers in schema/: pure functions of SchemaView + compiler version
   ┌─────────────┼──────────────┬────────────────┬──────────────┬──────────────────┐
   ▼             ▼              ▼                ▼              ▼                  ▼
 Python for    per-version     SQLAlchemy       Arrow          JSON Schemas       rule-engine
 core (gener-  Pydantic        MetaData + hand  schemas        ($id = revision)   context,
 ated, checked branches,       physical overlay (pool, COPY,   → decoding form,   annotator
 in) → hand-   vocabulary      → Alembic → PG   Parquet,       external           reference
 written ops   rows, registry                   DuckDB)        consumers
```

Each consequential question, in brief, with the recommendation that develops it:

1. **Where authority lives (R01).** In LinkML, for core, system and packs. Generation runs from
   the model to every form. This replaces ADR-0017's division by artifact kind with one model in
   three modules. The domain vocabulary stays in the packs. The core vocabulary, the member
   properties, the qualifier key roles and the lifecycle of each closed set join the model. D2 and
   D3 cite model files and generated renderings instead of inlining them.
2. **The fully relational model (R05).** Every relationship becomes relational:
   - claim → claim premise references and binding targets;
   - claim → entity references from qualifiers, arguments and bindings;
   - entity identity slots;
   - unresolved endpoints, as typed nodes.

   Scalar qualifiers that queries, slots and conflicts read (modality, polarity, attribution)
   become columns. Values stay governed nested values: condition-tree structure, schema qualifier
   maps, formula values with bindings, payloads. Pack-scoped vocabularies get per-version rows
   and composite FKs, so INV-03 becomes a store constraint.
3. **What is integrated where (R05, R10, supporting doc §5).**
   - PostgreSQL is the transactional authority for instances.
   - Arrow is the interchange and pool format.
   - DuckDB is the in-process engine and the analytics layer.
   - JSON Schema is the decoding and external form.

   Each is generated, and each enforces only what its projection declares.
4. **Schema change (R06 and the callout, §4.6).** Change is modelled through:
   - revisions;
   - a payload-schema registry;
   - change records with compatibility classes;
   - Alembic revisions linked to model revisions;
   - versioned derived artifacts and frames.
5. **Owned translations (R04).**
   - authored → stored;
   - stored → candidate;
   - pool → candidate;
   - candidate → rule view;
   - instance ↔ row/Arrow;
   - model → decoding form;
   - payload upcasts;
   - key carry-over.

   Each declares its source and target classes and is checked for completeness against the model.
6. **Declared identity (R02).** Qualifier specifications give each qualifier its key role, any
   condition on that role, a canonical form chosen by range and a case policy. The key scheme is
   versioned beside keys, with conformance vectors and carry-over maps.
7. **Operational and evidence vocabulary (R07, R08).** Typed reason codes; one stage and unit-type
   vocabulary; typed policy symbols; a modelled confidence-source vocabulary; selection of the
   final pass; `agent_reuse` removed until defined; and a short sealed run cut in place of the
   long lock.
8. **Infrastructure facts (R11).** One record of extension versions; lease-based template
   retention; one source for coordinates; the dependency check extended; checked evidence
   citations; the binding map filled.
9. **The centralized relational engine (R09).** The pool becomes model-typed relations, with
   DuckDB for set-based steps, PostgreSQL for transactional sets and Python for identity and
   procedural work, under explicit determinism rules.

## 4. Recommendations

Each recommendation states what the corrected operation consumes, decides and produces, and what
its consumers stop interpreting. Library mechanisms are named with their evidence strength:

- **Interface-checked:** the installed or tagged source was read on 2026-10-28, directly or by a
  contributor.
- **Documented:** an overview or primary documentation, not inspected at a locked version.

Every remedy is **Proposed**.

<a id="r01"></a>

### R01 — One model authority; projections generated from it

*Findings: DA-001, DA-002, DA-003, DA-011, DA-012, DA-020 (in part), F01; enables R02, R04–R07,
R09, R10.*

**What changes.** The model is authored in LinkML in three modules:

- **`core`:** today's `core.yaml`, promoted from mirror to authority.
- **`system`:** the `meta`/`ops`/`kb`/`eval` classes.
- **packs:** unchanged in form.

Every closed set, member property, default, qualifier specification, cross-field invariant and
relationship is declared there once. Two declarations are new:

- **The lifecycle of each closed set.**
  - *Static* sets change with code and are enforced by CHECK: statuses, unit types, stages,
    segment kinds, modalities, link types, evidence roles.
  - *Schema-version-scoped* sets can be extended by packs and are enforced per version:
    statement kinds ("extendable by domains", D1 §4.3), entity classes, predicates, pack enums.
- **The properties of each member**, as native permissible-value `in_subset` membership:
  - modality: `premise_forming`, `attribution_identifying`, `assertoric`;
  - segment kind: `annotation_unit`, `statement_anchor`, `search_block`, `container`;
  - statement kind: `claim_bearing`.

The compilers in `schema/` generate every mechanical form. They come in two stages, so the
low-risk part does not wait on the uncertain one.

- **Stage A** has no open feasibility question. It generates `core/_model/` (name a planning
  choice), checked in with a drift test:
  - one `StrEnum` per closed set, with frozensets of members per property;
  - the qualifier specifications and defaults (R02);
  - the local ↔ prefixed name tables for core elements;
  - the SQL-literal constants (the BM25 block kinds, the annotation-unit kinds);
  - validator functions for the declared invariant templates.

  Hand-written shapes import these instead of restating them. `vocab.py` becomes generated,
  `SegmentParseStatus` merges with `evidence.ParseStatus`, and the formula enum is renamed
  `ParseOutcome` model-wide (DA-002). The mirror contract test retires for every fact Stage A
  generates.
- **Stage B** follows probe Q-1 (§10). It generates the shape structure:
  - the value union discriminated on `t`;
  - the named recursive `Condition` discriminated on `op`;
  - the authored and stored variants from `ci:form`;
  - `MISSING` defaults; frozen models, `extra="forbid"`, tuples;
  - the stored prefixed aliases.

  The behaviour stays hand-written over these types: canonical forms, keys, locators, frames, the
  cascade and consolidation.
- **The fallback**, if Q-1 shows the generator cannot meet the shape contract: shape structure
  stays hand-written Pydantic, and `core.yaml`'s shape classes are *generated from it* by a small
  emitter over `model_fields` into `SchemaBuilder`. No hand-kept mirror remains in either case,
  and Stage A stands.

**Consumes:** the model files at a revision. **Decides:** nothing new; it moves the existing
decisions to one place. **Produces:** generated modules (checked in), compiled per-version
artifacts (`meta.compiled_artifact`), the CHECK and FK definitions (R05), and the JSON and Arrow
schemas (R10). **Consumers stop restating:** the modality members and default; the qualifier list;
segment-kind role subsets; operational enums; invariant checks; D2 §6/§9's inlined pack copies;
D3's DDL and its §6.2 payload table. DESIGN.md's own rule, "column- and field-level contracts live
in executable declarations … not repeated here", then holds.

**Why LinkML rather than Pydantic as the one authority.**

1. The pack must be LinkML: ADR-0017's reasons stand, since models and authors read YAML and it
   generates to several targets. So LinkML is the only language that sees domain and core facts
   together. One `SchemaView` then feeds every compiler.
2. Member properties, key roles and lifecycles are declarations, not code.
3. The change classification of R06 is a diff over one introspection API.
4. `kb.claim` *is* D1's claim. Generating the table from the same class removes the D1 ↔ D3
   restatement.

**Against it:** generator coverage. LinkML 1.12.1's own generators do not meet the requirements:

- `gen-pydantic` emits a plain `Union` with no discriminator, `Optional` defaulting to `None`, and
  unfrozen models (Interface-checked 2026-10-28; installed `pydanticgen` contains no
  `discriminator`).
- `gen-sqltables` emits native `Enum` types, no CHECKs and no JSONB (Interface-checked
  2026-10-28).
- `gen-json-schema` emits draft 2019-09 and drops predicate slots (S4).

So the compilers are ours, built on `SchemaView` and optionally on the public
`RelationalModelTransformer`. This is a deliberate bespoke projection rule set over a library's
introspection, with the gaps of the library route stated (DP-13, §F). It is not generic capability
built by hand.

**Mechanisms:**

- **`SchemaView`:** `all_enums`, `induced_slot`, `slot_applicable_range_elements`,
  `permissible_value_ancestors`, `get_uri(expand=False)` and `annotation_dict`, all present in
  installed linkml-runtime 1.12.1 (Interface-checked 2026-10-28).
- **Permissible-value `in_subset`:** a native multivalued metaslot (Documented: Context7 LinkML
  metamodel docs; Interface-checked in `meta.yaml` by contributor A). Its lint and read-back are
  unverified (probe Q-2).
- **For Stage B,** two candidates:
  - a `PydanticGenerator` subclass overriding `generate_slot` and `get_class_slot_range`, with
    `template_dir` templates;
  - an own Jinja emitter over `SchemaView`.

  Both target Pydantic 2.14's `MISSING` (stable in 2.14.1), `TypeAliasType` and
  `Field(discriminator=…)`.
- References: [linkml overview](../../libraries/linkml.md) §3.4, §5.2–§5.4;
  [pydantic overview](../../libraries/pydantic.md) §3.4, §4.1–§4.2;
  [schema-rules note](../evidence/2026-10-28_library-schema-rules/README.md) L-01–L-03.

**Challenges.**

- *A business pack adds statement kinds* such as `clause`, `request` or `policy`. A generated
  static Python enum would reject them. This is why each closed set declares its lifecycle.
  `StatementKind` is schema-version-scoped:
  - core declares its base members and their properties;
  - a pack declares additional members with the same properties;
  - the compiler materializes the union per schema version (LinkML 1.12.1's `induced_enum` does
    not materialize enum expressions, per contributor A);
  - generic shapes keep `str`;
  - per-version models type it, and the store enforces it by FK (R05).
- *Static typing of `core`:* runtime `create_model` for core shapes would lose it, so it is
  rejected for `core`. It remains the right mechanism for per-predicate branches, which are
  per-version artifacts (S4).
- *Generated code as a second source:* the drift test fails when a committed generated module
  differs from regeneration, and the module is never edited (DP-16).

<a id="r02"></a>

### R02 — Declare identity in the model

*Findings: DA-001, DA-008, DA-009 (key scheme), DA-014; consumers: keys, C1 slots and conflicts,
the rule view.*

**What changes.**

- **A `QualifierSpec` per qualifier, core and schema alike:**
  - `key_role`: `identity`, `meaning` (carries meaning outside the key, so a disagreement makes
    alternatives) or `inert`;
  - an optional *role condition*, expressed through a member property. Attribution is `identity`
    when modality ∈ `attribution_identifying`, today `{cited}`. The literal `cited` leaves
    `keys.py`;
  - the *canonical form chosen by range*: formula and set by token form; text and phrase by text
    form; an identifier string by NFC with whitespace collapsed and its declared case policy; an
    enum as `{enum: prefixed name, v}` verbatim; an entity reference as its resolved key (with
    kind check, R04); an interval recursively; a map entry by its `MapEntry` value range; a
    number as a canonical decimal with unit and basis collapsed; a date verbatim;
  - a *case policy* (`fold` for prose, `preserve` for math-bearing labels and slots), declared on
    string-ranged slots and on a class's label. `RandomVariable` labels, and literal identity
    slots whose fallback is a symbol, are math-bearing.
- **`KeySchema` compiled from these specifications**, so keys, slots, conflict detection and the
  rule view read one input.
- **The key scheme versioned *beside* keys, not inside them:**
  - the model declares `key_scheme: N`;
  - each run records the scheme its keys use, and judgment targets record the scheme of the key
    they name;
  - each scheme version has a *conformance vector*: known inputs with pinned expected keys, so
    any output change fails until the scheme moves;
  - a scheme change ships a *carry-over map* (old key → new key), computed by keying the stored
    authored inputs under both schemes.
- **Locator limits (DA-014).** D1 §10.3 states the ordinal shift within an anchor and lists
  derivation changes as a stability limit. P0CL-01's closure wording is narrowed to D1 §10.1's
  property.

**Consumes:** the compiled `KeySchema` and the typed candidate (R03, R04). **Decides:** the key
parts. **Produces:** keys with a recorded scheme. **Consumers stop:**

- `claim_parts` stops hard-coding the role rule;
- `canonical_qualifier` stops testing JSON shape;
- C1 stops restating slot and conflict rules;
- D1 §5.2, D1 §10.1 and D5 §5.4–§5.5 cite the specification instead of restating it;
- `text_form` stops casefolding math labels.

**Why beside, not inside.** A scheme number hashed into every key moves every key on any scheme
fix, even one that changes no output for most inputs. That would orphan every judgment and every
cross-run diff (DP-04, DP-09). Recorded beside, unchanged inputs keep their keys. Readers compare
keys only within one scheme, or through the carry-over map.

**Challenges.**

- *A `{"ref": "Smith"}` map entry:* the entry is canonicalized by its declared value range
  (string), so it is no longer read as an entity reference.
- *A business identifier such as `ORG-101`:* the pack declares the slot's case policy. Nothing
  guesses it from shape.
- *A business modality under which attribution identifies:* the pack gives the new member the
  `attribution_identifying` property, and no core edit follows.
- *Existing keys:* no production keys exist, and fixture tests compare equalities only, so
  changing the case rule now costs nothing.
- *The test oracle:* conformance vectors pin values, which D1 §10.1 currently forbids for fixtures
  (review#RC07). Scoping the pins to one scheme version keeps D1's intent: fixtures never break on
  a sanctioned key change.

**Evidence:** Proposed. The defects are confirmed by source reading (`keys.py:63-66`, `:432-462`;
Implemented at `6f31f75`) and by the audit's scratch probe (2026-10-28, not retained).

<a id="r03"></a>

### R03 — Operations consume the typed model, not dumps

*Findings: DA-004, DA-001 (dispatch part). Independent of R01; can start now.*

**What changes.**

- Canonical forms, traversals, citation finding and re-addressing pattern-match on the typed
  unions (`match v: case Formula(): …`). Exhaustiveness is enforced with `assert_never`, and a
  test enumerates each union's members from the model.
- A condition tree has one typed visitor, which yields nodes. `claim_refs`, `canonical_condition`
  and binding collection consume it, so the three walks with different unknown-operator handling
  collapse into one, and an unknown operator is unrepresentable after validation. The `ValueError`
  that escapes `key_claims`'s no-raise contract disappears.
- Citation positions are the fields whose declared type is `SentenceId`, enumerated from the form
  model, not keys named `sentence` or `anchor`.
- Canonical JSON is applied only to the final key parts.

**Consumers stop** reinterpreting tags and key names. A pack qualifier named `sentence` is safe.

**Mechanisms:** Python 3.14 `match`; Pydantic discriminated unions (already used);
`typing.assert_never` checked by pyrefly. **Challenge:** cost. The current single JSON walk is
cheap; a typed walk is comparable, and the final canonical JSON is unchanged. No measurement is
needed for this structural choice. **Evidence:** Proposed.

<a id="r04"></a>

### R04 — Owned, complete translations; typed references; explicit unresolved endpoints

*Findings: DA-005, DA-006, DA-007, DA-013 (drop codes), X2-01 (phase 0 plan §11).*

**What changes.**

- **The stored batch and the keyed candidate set carry the whole meaning.** They gain the
  rendition identity (a typed rendition reference, not a `KeyContext` supplied on the side),
  `alternatives`, `unsupported` items, `establishment`, `derived_from` and `rule`. Every optional
  field follows the `MISSING` convention. "Not yet keyed" and "awaiting resolution" become typed
  states, not `None`.
- **References are typed by kind in each context:** an entity reference, a statement reference
  and a claim reference, each a local ref when authored and a key once stored. The resolver has
  per-kind lookups (`entity(ref)`, `statement(ref)`, `claim(ref)`) and refuses a reference of the
  wrong kind with a typed drop code (R07). The subject is "entity or statement" by type, not by
  comment.
- **References outside the batch become typed nodes**, a core class `ExternalReference`. The
  authored `outside` item carries a descriptor: the citing sentence and quote, and the author's
  link target when there is one. It is stored with its span. It is keyed by the citing statement's
  key plus the descriptor's text form, and claims keep it as subject or object. Consolidation
  resolves it through link targets or locators, records a `resolves_to` relation and re-keys the
  citing claim to the resolved statement (a declared stability limit). Unresolved references are
  counted in coverage and rendered by queries as "an unresolved reference: …".

  This reconciles D1's OPEN-D1-5 with D2's V2 on one treatment. It also keeps D3's rule that a
  statement row always has a kind, because an `ExternalReference` is not a statement row
  (review#RC11).
- **One owner of reference checking.** `validate`'s batch checks (the side table) own it for
  batches, and the keying resolver owns kind refusals for pool candidates. D1 §10.3's "owner …
  foundations" is corrected (review#RC19).
- **Names are mapped by generated tables.** The local ↔ prefixed name map comes from
  `SchemaView.get_uri(expand=False)`, with a compile-time uniqueness check (X2-01).
  `EnumValue` gets a variant per form, so the stored form can require prefixed enum names.
  Rule-view qualifier attribute names follow a declared rule (local name if unique, else a
  mangled form), with a compile-time collision check that also covers the multi-pack premise.
- **Every translation states its completeness.**
  - authored → stored (cascade and renaming);
  - stored → candidate;
  - pool → candidate;
  - candidate → rule view;
  - instance ↔ row/Arrow;
  - model → decoding form;
  - payload upcasts;
  - key carry-over.

  Each declares its source and target classes. A test derived from the model enumerates the
  source slots, each either mapped or declared omitted (DP-08: permitted omissions are stated).

**Consumers stop** supplying side inputs whose shape no type owns, guessing reference kinds, and
reading `None`.

**Challenges.**

- *Email:* "as I wrote below" references an earlier message. It becomes an `ExternalReference`
  whose link target is the message id, resolvable within the thread.
- *A citing claim the pipeline cannot resolve:* it stays served as conditional on an unresolved
  reference, never as absence. This is the CI-04 failure the change removes.
- *Phase 0 extraction emits no `extref`:* the authored `outside` item already exists (S4 V2), so
  only its descriptor is new.

**Evidence:** Proposed. The S4 side table caught 13 of 13 seeded reference errors (Tested,
record `s4.batch-validation`, 2026-10-28). That establishes the check, not its single ownership.

<a id="r05"></a>

### R05 — The relational projection of the model in PostgreSQL

*Findings: F04, F01, DA-011 (DDL), DA-012 (CHECKs), DA-003 (SQL literals), DA-006 (store
integrity). Prerequisite: R01 (system module).*

**What changes.** A `MetaData` compiler maps the model to tables, under these rules:

- **Classes and columns.** System classes become tables. Scalar slots become typed columns, with
  types from model types (custom LinkML `types:` for `Key`, `Locator`, `CanonicalDecimal` and
  timestamp).
- **Static closed sets.** They become `text` columns with an explicit-name `CheckConstraint` whose
  name carries a digest of its member list. Alembic's opt-in `checkconstraint_byname` detects
  additions and removals *by name only* (Interface-checked: present in Alembic 1.20.0;
  [alembic overview](../../libraries/alembic.md) §4.2). The digest turns any member change into a
  detectable drop and add.
- **Invariant templates.** Each becomes a CHECK beside its generated validator (F01).
- **References.**
  - A single-valued class-ranged reference becomes an FK column.
  - A multivalued or nested reference becomes an edge table.
- **Nested values.** A class range declared `nested` becomes `jsonb`, with its schema identity
  (R06).
- **Schema-version-scoped vocabularies.** They become per-version vocabulary rows (the
  `meta.schema_*` projection D3 already has) plus composite FKs:
  - `(schema_version_id, predicate)` → `meta.schema_slot(schema_version_id, name)`;
  - entity type → `meta.schema_class`;
  - statement kind → a per-version member table.

  INV-03 thereby becomes a store constraint.

A hand-written **physical overlay** holds what the model should not:

- indexes and their partial predicates;
- the BM25 index (`postgresql_using="bm25"`, `postgresql_with`, `postgresql_where`);
- the HNSW indexes in phase 1;
- the views (`kb.run_observation`, `kb.run_rendition`), through SQLAlchemy 2.1's `CreateView` or
  `DDL`;
- the extension assertion.

The overlay refers to generated tables and columns by name and fails at import if one is missing.
Its literal lists come from member properties: the BM25 kind list is
`search_block`, already "one constant shared with the index definition", now generated.

**Knowledge rows** change as follows (sketch in the target model §6; Proposed):

- **`kb.claim`.**
  - gains `modality` and `polarity` columns, NOT NULL with the `ifabsent` defaults and a CHECK
    from the enum; they are omitted from the JSON qualifiers, so equal meaning still gives equal
    JSON;
  - gains `attribution_entity_id`, an FK;
  - gains `schema_version_id`;
  - gains `UNIQUE (run_id, id)`, which same-run composite FKs need.
- **`kb.claim_ref`** holds claim → claim edges: condition premise references and `param_of`
  binding targets, each with a kind and a tree path. A composite FK `(run_id, target_claim_id)`
  enforces INV-08.
- **`kb.claim_entity_ref`** holds claim → entity edges: entity-ranged qualifiers, `pred`
  arguments and binding entity targets, each with a role and a path, also under a same-run FK.
- **`kb.entity_identity`** holds one row per identity slot (slot, `value_entity_id` or
  `value_text`), with an FK for entity-ranged slots and an index on `(slot, value_entity_id)`. It
  serves `family_profile`'s parameter branch and the cannot-link test.
- **`ExternalReference`** entities (R04).

Edge and identity rows are *derived* projections, written by the consolidation bulk writer from
the typed instances in the same transaction and never edited (DP-01). They serve queries, which
refuse unfinished runs. So they can be written only at the run's final pass, not at every
intermediate pass (A4, H16).

**What stays nested and governed:**

- condition-tree structure;
- schema qualifier maps;
- values with their bindings;
- `valid_time`, an ISO interval with possibly partial dates, so a range type would be lossy;
- observation payloads;
- authored golden batches and frames;
- compiled artifact bodies;
- `cost` and `trigger_metrics`.

**Carrying the S6 evidence over.** The first generation is checked against the S6-tested D3 DDL
by a pglast-normalized comparison. The comparison projects each table to its columns (name, type,
nullability, default), its set of constraints and each index's `USING`, `WITH` and `WHERE`, because
raw AST equality fails on harmless differences (pglast 8.7 `parse_sql`, whose `Node` equality
ignores locations; contributor A, GitHub tag `v8.7`; [pglast overview](../../libraries/pglast.md)
§3.1, §4.3). pglast's `referenced_relations` also checks that D3 §9's queries name only tables the
`MetaData` holds. After that, D3 cites the generated DDL rendering. D3 §1's planned catalog
comparison (after `upgrade head`, against `create_all`) stays the database-level check.

**Consumers stop:**

- hand-porting DDL into `core/db`;
- writing literal stage and kind lists in SQL;
- parsing JSONB to follow references or to filter on modality;
- asserting INV-03 and INV-08 in repository code.

**Mechanisms:**

- SQLAlchemy 2.1.5: `MetaData(naming_convention=…)`, `CheckConstraint(col.in_(…), name=…)`,
  `Index(…, postgresql_using=…, postgresql_with=…, postgresql_where=…)`, `CreateView`
  (Interface-checked: `sql/ddl.py:758`, 2026-10-28), and `TypeDecorator(impl=JSONB)` with a
  Pydantic `TypeAdapter` for nested columns;
- Alembic 1.20: autogenerate from this `MetaData`, and `comparators.dispatch_for` or
  `Plugin.add_autogenerate_comparator` if a further comparison is needed;
- [sqlalchemy overview](../../libraries/sqlalchemy.md) §3.1–§3.2, §3.5, §4.2;
  [alembic overview](../../libraries/alembic.md) §4.1–§4.2, §5.5–§5.6, §6.5.

**Limits.**

- Whether Alembic autogenerate treats a `CreateView`-registered table as a table is unverified.
  The existing `env.py` already excludes `info["is_view"]`.
- `gen-sqltables` is not used: native enums, no CHECKs, no JSONB.
- The meaning of `meta.schema_*` replacement changes. D3 says a newer schema-table compiler's rows
  *replace* a version's rows. With FKs pointing at them, replacement becomes an upsert. Removing a
  name that rows reference then fails, which correctly exposes a compiler change that would
  orphan data.

**Challenges.**

- *Phase 1 volume.* Edges amount to a few per claim, so about 10⁵ rows per run. That is the order
  of S6's 40,000 support and evidence rows written in 214 ms (Measured, S6, 2026-10-28, interim
  cluster). Composite FK checks add an index probe per row, which is unmeasured (probe Q-4). If
  Q-4 shows material cost, enforce INV-03 and INV-08 in the bulk writer and keep the edge tables
  for queries. The relational shape stands either way.
- *A business query that filters on a schema qualifier* such as ownership share. The pack declares
  that qualifier `sql_visible`, which classifies the change as relational (R06): a migration adds
  a generated column or an expression index. The model knows this change needs DDL.
- *ADR-0016's "single authority" is kept:* PostgreSQL holds instances, and the model holds
  structure (review#RC02).

<a id="r06"></a>

### R06 — Schema change is a modelled concept

*Findings: DA-009, DA-010, DA-011 (versions of copies), DA-021 (in part); the operator's callout
(§4.6).*

**What changes.**

- **Revisions.**
  - A *model revision* covers core and system together: the LinkML `version` plus a content hash,
    the compiler versions and the key-scheme version. It is a `meta.model_revision` row.
  - A *schema version* covers a pack. Its D2 §2 hash also covers the model revision id, which
    closes DA-009's first gap, since the authority is now inside the hash.
  - A *payload schema* is a versioned nested class, held as a `meta.payload_schema` registry row
    (target model §9).
- **Schema identity on stored values.** Rows that outlive a model revision carry a
  `payload_schema_id` FK: observations, golden passes and frames, compiled artifact bodies,
  `rendition_build.parse_detail`, intervention `refs`. Per-run materialized rows (claims,
  entities) inherit the run's recorded model revision and schema version, so they need no
  per-row id.
- **Alembic linked to the model.** Each revision carries the model revision it realizes, through
  `context.configure(template_args=…)` feeding `script.py.mako`. `process_revision_directives`
  refuses to generate a revision whose model revision is unregistered. `on_version_apply` records
  the application. Branch labels can carry a separate data-migration lineage
  (Interface-checked: Alembic 1.20 `runtime/environment.py`, contributor A, 2026-10-28;
  [alembic overview](../../libraries/alembic.md) §2.5, §5.2, §7.5).
- **Change records.** One record per revision step, holding:
  - the from and to revisions;
  - the element changes, computed by a `SchemaView` diff (LinkML has none, so this is own code);
  - the compatibility class of each change;
  - the reason;
  - the *authorizing circumstance*: the model rule under which this kind of change is allowed,
    for example "a method version bump may add an optional field to its payload kind";
  - the migration mapping: an Alembic revision, an upcaster, or a name map;
  - the key consequences: scheme change and carry-over map;
  - the judgment carry-over;
  - the affected compiled artifacts and source profiles.

  D3's `meta.schema_version.migration` and D2 §8's table grow into this record (review#RC09).
- **Derived artifacts are keyed on their derivation.**
  - A `claim_proposal` payload records the cascade version and the schema version that derived its
    stored `batch`.
  - A golden item is keyed by pass, rendition, cascade version and schema version.
  - Re-location adds a new frame version with a parent link instead of editing the frame that
    `eval.result.golden_snapshot` already referenced.
  - Authored artifacts are never rewritten. A rename mapping is applied when items are derived
    from them.
- **Source profiles are model-governed data (DA-010).** A profile is validated at load against a
  profile model whose domain-bearing slots reference core vocabulary: statement kinds and core
  predicates such as `core:proves`. A run checks it against its schema version (pack-scoped kinds
  included), and change records cover profiles. The hints stay in the profile, because they are
  source × core-vocabulary facts. The audit's alternative of moving them into the pack would split
  one source convention across packs that share the source.

**Consumers stop** reading stored payloads under current defaults. Readers dispatch on the
recorded schema. An unknown schema id is refused, never reinterpreted (DP-24).

<a id="callout"></a>

### 4.6 The operator's callout: evolving a structured schema without migration

**What the mechanism is.** A typed nested value lives in a row: JSONB, or a file referenced by a
row. Its schema is held in a registry that every service reads. Arrow carries it in transit and in
analytics with that registry identity in its metadata. The relational shell (columns, keys,
indexes, CHECKs, FKs) is fixed by migrations. The *effective stored schema* of the nested part
evolves by registering a new payload-schema version, with no DDL.

**What Arrow does and does not contribute.** Arrow does not load structured fields into
PostgreSQL by itself:

- pgpq writes a struct only as a composite type, which is DDL that needs OIDs. It cannot write a
  struct containing `List<Struct>`, unions, dictionaries or nested lists (Documented,
  [pgpq overview](../../libraries/pgpq.md) §3.2, §4.2–§4.3).
- ADBC has no struct writer. It writes JSONB only from an `arrow.json` field into a `jsonb` column
  (source-checked by contributor B at tag `apache-arrow-adbc-25`;
  [adbc overview](../../libraries/adbc-driver-postgresql.md) §4, §5.3, §5.7).

So the payload crosses into PostgreSQL as JSON text, which the server parses into JSONB, beside
the registry id.

What Arrow uniquely gives:

1. a typed, serializable schema (`Schema.serialize()`, `pa.ipc.read_schema`) that the registry
   can store and every Arrow-speaking service can read;
2. field metadata naming the model revision, class and payload schema;
3. Parquet exports that keep the same schema with key-value metadata;
4. DuckDB reading those exports as typed columns.

The no-migration benefit is therefore real in two places: storage of immutable payloads, and
analytics. In the second, payload fields become typed analysis columns without PostgreSQL
generated columns or expression indexes. It is not a way to avoid migrating what PostgreSQL reads.

**Which changes may take the no-migration route.** A change qualifies only when *all* of these
hold:

- the class is a registered nested payload class;
- the change is backward-readable: an added optional field, or a new member of a nested closed set
  that no CHECK lists;
- no PostgreSQL CHECK, FK, index, generated column, view, D3 §9 query path or partial-index
  predicate reads the changed path. The model declares the `sql_visible` paths of each payload
  class, so this is checked mechanically against the overlay and the query patterns;
- no key, digest or identity reads the path in a way the change alters. A new optional field
  changes the canonical JSON, and so the digests, only of *new* payloads, which is expected;
- a reader upcast from every still-referenced older version to the current in-memory model is
  declared in the change record. For an added optional field, the upcast is "absent".

**Which changes may not:**

- anything a constraint, key, index or query reads;
- static closed sets (task status, observation kind, segment kind);
- relational columns and relationships;
- the BM25 block kinds;
- the `kb.run_observation` predicates;
- an identity qualifier, a canonical form or key parts. These are key-bearing and need a scheme
  or schema-version change with a carry-over map.

Renames, removals, narrowings and splits of nested fields go through versioned upcasts, never
in-place rewrites. Observations are immutable and reused across runs by content, and input digests
include upstream payload hashes, so rewriting a payload in place would silently change what reused
tasks depended on (DP-09, DP-19).

**What the change record holds for this route:**

- the payload class and its from and to versions;
- the compatibility class `nested-additive`;
- the authorizing circumstance: for an observation kind, "method `m` version `v` emits it";
- the reason;
- the upcaster;
- the confirmation that no `sql_visible` path and no key-bearing path changed;
- the Arrow schema bytes and the JSON Schema `$id` of the new version.

**Where it applies:** observation payloads, compiled-artifact bodies, golden batches, `parse_detail`
and measurement `detail`, and their analytic projections. **Where it does not:** the
decision-relevant structure of knowledge rows. Those are rebuilt per run under the run's recorded
revision anyway, so their "migration" is re-consolidation.

**The file route** (Arrow IPC or Parquet outside PostgreSQL, referenced by rows) is **rejected for
authoritative data**. A file write is not inside the PostgreSQL transaction, which breaks §B4's
one-transaction property, and files can be orphaned. It is **accepted for exports and analytic
snapshots** of finished runs.

**Failure modes to design for:**

- **Absent versus null.** Arrow has only null. The mapping is lossless only for fields whose model
  forbids null, which the batch shapes do. Fields typed `JsonValue`, where JSON null is valid,
  travel as `arrow.json` text. The model declares a null policy per field.
- **Recursion.** Arrow has no recursive types, so condition trees and nested values travel as
  `arrow.json` text or as normalized node rows.
- **Tagged unions.** These are not encodable by pgpq or ADBC, so they travel as JSON text or as a
  tag plus struct-of-optionals.
- **Key order and duplicate keys.** JSONB and VARIANT normalize them, which is harmless because
  keys are computed in Python before storage.
- **Readers missing a version.** A reader without the upcast for a referenced version must refuse.

**Evidence:** Proposed. DuckDB 2.0.0 checks run by contributor B (Interface-checked 2026-10-28):

- VARIANT with `SHREDDING` and `KV_METADATA` round-trips through Parquet;
- `parquet_kv_metadata` reads the metadata back;
- absent and JSON null are preserved on the round trip to JSON;
- field access cannot distinguish absent from null.

<a id="r07"></a>

### R07 — Operational and evidence vocabularies are modelled

*Findings: DA-012, DA-013, DA-015, DA-016, DA-017.*

**What changes.**

- **Vocabularies.** `Stage` becomes a static enum, checked on `ops.task.stage`, and the views use
  its generated constants. `TaskUnitType` becomes the one unit-type vocabulary that D4's
  `Method.unit_type` and `ops.policy_rule.unit_type` both use. Either `span` is added to it, or
  D4 drops it; one decision.
- **Typed reason codes.** `KeyingError` gets a code (`condition_cycle`, `unknown_claim_ref`,
  `dropped_dependency`, `unknown_predicate`, `wrong_reference_kind`, `unresolved_external`,
  `identity_cycle`, `segment_not_on_rendition`, …), and its message is derived from the code.
  `FrameFailure` gets `LocatorRefused`'s typed reasons plus its own codes (`cited_not_in_frame`,
  `not_in_served_packet`, `text_differs`, `not_a_sentence`). C1's `PassReport` counts by code.
- **Typed policy symbols.** `judgment(m)` splits into `decision(m)` and `confidence(m)`, each typed
  by its vocabulary. At policy and rule compile, string literals compared with an enum-typed
  symbol (`target.kind == 'alternative_group'`) are checked against the vocabulary. This is a
  small walk over `rule_engine`'s parsed expression. Its feasibility is to be confirmed in
  planning, and the fallback is `$enums` membership with a lint.
- **Confidence sources.** D5 §6.2's sources become a modelled vocabulary. Each method declares its
  source in the registry, and `policies.yaml` gains a schema holding priors, multipliers and caps
  keyed by that vocabulary (DA-016).
- **The current M19 pass (DA-015).** The run's seal (R08) records the final finalize pass's M19
  task. `explain` and coverage read that task.
- **`agent_reuse: by_unit` is removed** until its dependency is defined as a declared projection
  of the prompt parts (review#RC13; DP-09 MUST).

**Consumers stop** classifying prose, guessing the current pass, and compiling policies whose
typos never match.

<a id="r08"></a>

### R08 — Seal the run's cut in a short transaction

*Finding: DA-024.*

**What changes.** The run gains `cut_at`. One short transaction locks the run row, stamps
`cut_at = clock_timestamp()` and moves the run to its final consolidation state. It then commits.

- Agent completions and twin settlement keep taking `FOR SHARE` on the run row. A completion
  stamped after the cut counts as unresolved for that run, as today.
- The final pass reads the pool *as of the cut*. The rule `kb.run_observation` already applies to
  a finished run (`t.finished_at <= r.finished_at`) is generalized to `cut_at`, without a lock.
- The pass writes knowledge in its own transaction. Measure and evaluate then run over immutable
  rows, and `finished_at` is set at the end.
- Fates, coverage, the views and `ci promote` read the cut.

**Consumes:** the pool as of the cut. **Decides:** which tasks the run includes. **Produces:** a
finished run. **What it preserves:** the requirement behind the lock, that the pool the pass reads
equals the set of tasks counted resolved. That set is now defined by a timestamp predicate instead
of by mutual exclusion. The exclusion window shrinks from the whole terminal computation to one
row update (DP-19, H23). The protocol must be checked against the twin-settlement ordering of
D6 §3.1. Both stamp with `clock_timestamp()` after their locks, so a twin settled before the cut
is in and one settled after is out. **Evidence:** Proposed.

<a id="r09"></a>

### R09 — A centralized relational engine as a contract

*Direction 2; findings F03, DA-025 (in part); review#RC02.*

The design already has the right *shape* for this. D5 §1 has consolidation build an in-memory
evidence pool, run its steps as functions over it, and write through one bulk writer, so steps are
testable on fixtures without a database. The recommendation makes the pool's *contract*
relational and model-typed, then places each operation in the engine whose semantics fit it.

**The pool contract.** One Arrow relation per pool table, with schemas generated from the model:

- effective observations by kind, with typed relational columns and the payload as typed struct
  columns or `arrow.json`;
- candidate entities, statements and claims, with typed reference columns;
- edges.

The pool is loaded from `kb.run_observation` as of the run's cut. Procedural steps hydrate typed
objects from it where they need them. Results return as relations to the bulk writer. Python lists
and DuckDB relations can then implement the same contract, which is the mechanism-substitution
seam (FP-02), and fixtures are Arrow tables with no server, so FP-06 is preserved.

**Placement** (full table in the target model §10):

| Operation | Engine | Why |
|---|---|---|
| `canonical_json`, digests, keys, text and label forms, token form, locators, the quote cascade, math grammar and SymPy, symbol-binding rules, z3, pgmpy, `linear_sum_assignment`, bootstrap | **Python** | Identity must have one implementation. DuckDB 2.0 has no casefold (`lower('Straße')` keeps `ß`; Interface-checked by contributor B on 2.0.0); Unicode table versions differ by engine; VARIANT and JSONB reorder keys and collapse duplicates. Grammar, solver and inference are non-relational |
| Mention clustering (span overlap within a segment), alias-equality linking, slot grouping, alternative grouping, fusion by key, conflict self-joins (subject + functional predicate + interval overlap), pack `views:`, rule-view cached facts (`same_slot`, `alternative_of`, statement premises), noisy-OR, run diffs, evaluation candidate pairs, score aggregates, exports | **DuckDB 2.0, in process, over the pool relations** | Set-based joins, group-bys, anti-joins, windows and ordered aggregates with an optimizer and spilling. Pack `views:` declarations (source predicate, match, project) *are* a join spec, so they compile to one |
| Connected components for merges (phase 2) | DuckDB `WITH RECURSIVE … USING KEY (node, min(comp))` with `UNION` (Documented, [duckdb overview](../../libraries/duckdb_2.md) §6.5; components Interface-checked by contributor B on 2.0.0), *only if* cannot-link refusal is made order-independent | See F03: D5 §3.6's refusal rule is order-dependent |
| Materialization, deletion, fates, `kb.run_observation`, coverage, typed queries | **PostgreSQL SQL** | Transactional, index-backed, the instance authority |
| Streaming re-encodes (read → project/cast → write) | PyArrow 26 Acero, optional | `Declaration.from_sequence(…)` with the v26 `RecordBatchReaderSourceNodeOptions`, `filter`/`project`/`aggregate`/`hashjoin` (left/right semi and anti) and `.to_reader()`, without materializing a Table (Documented, [pyarrow overview](../../libraries/pyarrow.md) §4.2, §13.1). Experimental API; no window or recursion nodes; joins and aggregates hold state (§14.2) |
| Rule evaluation | Python, rule-engine | Per-row typed contexts; a DuckDB UDF would bring back per-row crossings |

**Determinism (DP-11).**

- Identity is exact and computed in Python.
- Relational step results are *sets*.
- Any output whose order or floating-point value matters carries an explicit order: `ORDER BY`
  key, ordered aggregates such as `product(x ORDER BY key)`, and deterministic tie-breaks by key.
  DuckDB 2.0 gives no row order and no bitwise float reduction otherwise (Documented,
  [duckdb overview](../../libraries/duckdb_2.md) §13.2).
- D5 §1's claim, "the same rows with the same keys whatever order the queue was worked", then
  holds by construction.

**F03.** D5 §3.6 merges by union-find over must-links, "refusing any union joining a cannot-linked
pair". With must-links A–B and B–C and a cannot-link A–C, the outcome depends on which must-link is
processed first. The fix is a declared order (descending match score, then key), which makes the
procedural union-find deterministic and comparable with a set-based variant (probe Q-7).

**Crossings and movement.** These are qualitative; no figures are claimed.

- The pool moves once per pass from PostgreSQL to Arrow. ADBC's `fetch_record_batch` runs binary
  `COPY … TO STDOUT`, with JSONB as `arrow.json` text and NUMERIC as text with typmod metadata
  (Documented, [adbc overview](../../libraries/adbc-driver-postgresql.md) §3.1, §5.1–§5.3). DuckDB
  consumes Arrow without a Python per-row loop.
- Hydrating typed objects for procedural steps is a per-row Python crossing, the same one the
  current design pays.
- S6 measured about 11.6 kB of observation payload per unit (Measured, interim cluster,
  2026-10-28), so a 2,500-unit pool is tens of megabytes: a modest working set on this host.
- The move back to PostgreSQL stays psycopg binary COPY (100,000 observations in 1.1 s; Measured,
  S6) until the rows already exist as Arrow. Then pgpq's `ArrowToPostgresBinaryEncoder` feeding
  `psycopg.Copy.write` removes per-row adaptation. pgpq is Alpha and has no `timestamptz` encoder
  (source-checked by contributor B at `306cdf8`), so timestamps stay server-defaulted or go
  through psycopg (R10).

**Placement in time.** Phase 0's consolidation has only M24 proposals and no slots or
alternatives, so Python lists suffice there. Make the pool contract relational now (it costs
generated schemas), and adopt DuckDB when phase 1's slots, alternatives and conflicts arrive. Its
benefit there is semantic before it is physical:

- the set-based rules are declared once, as queries over model-named columns, instead of being
  hand-coded loops that restate join keys;
- `views:` compile to joins instead of builder code.

A speed benefit is a hypothesis until measured (DP-22).

**Risks.**

- DuckDB 2.0 is a week old, and its Python result lifecycle changed: an open `execute()` result
  blocks its connection, and Arrow output is only available through relations (Documented,
  [duckdb overview](../../libraries/duckdb_2.md) §3.5–§3.6). DuckDB becomes a product dependency,
  pinned at 2.0.0; today it is only in `tools/evidence`.
- The `postgres` extension maps unconstrained NUMERIC to DOUBLE by default, which is lossy (read
  at duckdb-postgres `main` `719691f`, not the 2.0 tag). Reading through ADBC or Parquet avoids
  this. **Evidence:** Proposed.

<a id="r10"></a>

### R10 — Interchange and analytics projections

*Findings: DA-009 (JSON Schema `$id`), DA-021 (catalog DDL); callout; supports R09.*

**What changes.**

- **Arrow schemas** are generated from the model for every relational table and payload class.
  Field metadata carries `cs.model_revision`, `cs.class` and `cs.payload_schema_id`.
- **No custom Arrow extension types** initially. Extension types bring a registration lifecycle in
  every consumer (H25, DP-16). DuckDB does not treat Arrow extension metadata as semantics
  (inferred by contributor B; probe 4 of note B). Unregistered readers see `UnknownExtensionType`
  or the storage type (Documented, [pyarrow overview](../../libraries/pyarrow.md) §10.1). Use
  canonical `arrow.json` where ADBC needs it (§10.2).
- **JSON Schemas** get `$id = https://corpus-structure.dev/schema/<model revision>/<name>` in
  `CoreJsonSchema.generate`. External validation uses a `referencing.Registry` built with
  `with_resources`, `Draft202012Validator` and `check_schema` (Documented,
  [jsonschema overview](../../libraries/jsonschema.md) §4.1–§4.3). The decoding form stays a pure
  transform.
- **DuckDB exports** use `COPY … (FORMAT parquet, KV_METADATA {schema_id: …})`. Payload analytics
  use VARIANT `SHREDDING` specs generated from payload classes. Reads use `read_parquet(schema=…)`
  or `parquet_kv_metadata` (Documented, [duckdb overview](../../libraries/duckdb_2.md) §7.2,
  §8.1, §8.4).
- **The evidence catalog** derives its DuckDB tables from the `Record` model through its Arrow
  schema (`from_arrow`, or generated DDL), not from hand-written DDL (DA-021).
- **pgvector (phase 1).** The embedding specification is a modelled fact: model id, revision,
  dimension, normalization. A new embedding family is a *relational* change. It needs a new
  partial HNSW index with a literal predicate generated from the registry, because a bound
  parameter likely defeats the partial index, by analogy with S6's BM25 finding (inferred). So it
  takes the migration route. This keeps CI-13's index-and-query specification compatibility
  explicit ([pgvector overview](../../libraries/pgvector.md) §5.3, §5.5–§5.6).

<a id="r11"></a>

### R11 — Infrastructure and evidence facts

*Findings: DA-018–DA-023, DA-025.*

- **DA-018, extension versions.** One record of the expected `extversion` per extension,
  `pg_textsearch 1.5.1` and `vector 0.8.7` (`ops/postgresql/`, with a `docs/pins.md` hold row),
  read by:
  - provisioning (`ALTER EXTENSION … UPDATE TO`);
  - the fixtures' check and 0001's assertion (version, not presence);
  - `db-status`, labelled correctly;
  - the template hash, which includes the template's extension versions.

  Check at startup with `SELECT extname, extversion FROM pg_extension`, not inside psycopg-pool's
  `configure`. There `CLIENT_EXCEPTIONS = Exception` turns a mismatch into retries and then a
  `PoolTimeout` (source-checked by contributor B, tag `pool-3.3.3`, `pool.py:35`;
  [psycopg-pool overview](../../libraries/psycopg-pool.md) §5.1, §7.2). psycopg-pool, which D3 §1
  names as the connection owner, is unpinned and uninstalled. That is a pin addition when the
  repository layer lands.
- **DA-019, the template sweep.** Retain templates by lease or age, not "not current, so drop".
  Clone under a shared advisory lock that the sweep takes exclusively.
- **DA-020, coordinates.** One coordinate source. The fixtures derive from `DatabaseSettings`
  defaults; provisioning reads the port from `corpus.conf`. D3 §3's manual steps give way to
  D3 §13.
- **DA-021, evidence citations.**
  - `just evidence check` resolves record ids cited in `docs/design/` and `docs/adr/` and warns on
    superseded ones;
  - `render` tracks every record read through `query()` and `value()`;
  - `answers` and `consumed_by` become typed references;
  - the outcome vocabulary is reconciled (review#RC17).
- **DA-022, the dependency check.** Extend `check_pins.py` to Python manifests, so the stated
  `just deps` property holds.
- **DA-023, the binding map.** Fill binding §1. Proposed rows are in review#RC18.
- **DA-025, keying preparation.** Prepare annotation units and segment keys once per `KeyContext`,
  and read stored segment keys where the store has them. `member_parts` reuses `claim_parts`.

<a id="r12"></a>

### R12 — Keep semantic controls independent of the model

*Finding: F02.*

**The issue.** Generated JSON Schemas are described as "an independent test oracle" in three
places: the `core/schemas` module docstring, the docstring of `tests/core/test_shapes.py`, and
D9 §2. They come from the same models, so a wrong constraint passes both. Under R01 every
projection inherits a model mistake. So agreement between Pydantic, jsonschema, the CHECKs and the
Arrow schemas checks *derivation*, not *semantics* (DP-23, FP-04's "would a shared mistake make
the oracle agree?", test-assessment companion).

**What changes.**

- Relabel those checks as **derivation conformance**.
- Keep and grow independent semantic controls, written from D1/D2 text and external data rather
  than from the model:
  - the relational key oracles;
  - the token-form parity fixture;
  - the S0/S0-R2 batches as external data;
  - negative store tests for each invariant, written from D1 §11;
  - known-answer keys in the conformance vectors, authored once by hand.

The test audit is the natural primary home for the test-scope part once it has findings. This
review records it because it constrains R01.

## 5. Change and failure scenarios

| Scenario and kind | Owner (target) | Baseline: what must change | Target: what must change | Evidence |
|---|---|---|---|---|
| **S1:** add an identity qualifier, or a modality under which attribution identifies (*domain concept / policy*) | model `core` qualifier specs | `batch.py` (two models and `CORE_QUALIFIERS`), `keys.py`, D1's table, C1's slot and conflict code, with no check between them (DA-001, DA-002) | one declaration: a qualifier spec, or a member with the `attribution_identifying` property; regenerate; the conformance vector stays (inputs without the qualifier keep their keys) | Proposed; baseline Implemented |
| **S2, domain extension:** a business pack (§1.3) with ORG multi-attribute identity, `owns` with `valid_time`, tables with units, email threads, `clause` statement kinds (*new pack*) | the pack; core segment-kind properties; the email source profile | a qualifier ranged on an identifier string is casefolded and maps misread by shape (DA-001); statement kinds untyped in core and unchecked in the store (DA-003, DA-010); email kinds have no roles, so `email_message` would be one uncovered block (DA-003); a pack cannot give a new modality behaviour without core edits | pack declarations only: classes with `unique_keys`, entity identity rows with FKs (R05); qualifier specs with case policy (R02); `StatementKind` members added per schema version, FK-enforced; email kinds already carry `annotation_unit` and `container` properties; the profile is typed against core vocabulary (R06). No core code edit | Proposed; S4 showed the pack mechanism (Tested, record `s4.pack-lint`) |
| **S3 / S7:** change a segment kind or the BM25 block level (*domain concept, static set*) | model `core` | `SegmentKind`, the D3 CHECK, the D3 BM25 predicate, `locators.py`, `keys.py`, D4 lists | the model change is classified *relational*; a generated migration changes the CHECK (digest-named) and rebuilds the partial index from the `search_block` property; consumers read properties | Proposed |
| **S4:** a new extraction method writes observations (*composition*) | the method; the registry | payload untyped where D3 leaves it open; candidates bypass kind checks (DA-006) | the method declares its payload class and version (registry row, nested-additive or new kind); its confidence source (R07); the translation completeness test covers the new payload | Proposed |
| **S5:** re-consolidate under a new schema version (*policy*) | the change record | stored batches and goldens read under the new contract silently (DA-009) | the run records its model revision, schema version and key scheme; payloads are read by their recorded schema with declared upcasts; judgments map through carry-over; orphans are reported (D5 §7.3) | Proposed |
| **S6:** an agent query with evidence closure (*served claim*) | `serve`; R04, R05 | "what does corollary X follow from" returns nothing (DA-007); premise joins go through JSON (F04) | `ExternalReference` rows are served as unresolved, with coverage; premises join through `kb.claim_ref`; CI-11 closure follows FKs within the run | Proposed |
| **S8:** a Pydantic, Python, Unicode or extension bump (*mechanism*) | R02, R11 | keys and digests could move silently; a stale test template keeps serving (DA-009, DA-018) | the conformance vectors fail on any key change; the extension-version record fails startup and fixtures; the template hash includes versions | Proposed |
| **Mechanism substitution A:** the pool as Python lists, then as DuckDB relations | consolidation | no pool contract (D5 §1, a code shape only) | one model-typed relational pool contract; both implementations pass the same fixtures with set-equal outputs and equal keys | Proposed; probe Q-5 |
| **Mechanism substitution B:** bulk writes through psycopg `write_row`, then pgpq Arrow COPY | the repository bulk writer | n/a (psycopg only) | the same generated Arrow schema drives `Copy.set_types` and the pgpq encoder; switch when rows already exist as Arrow; timestamps stay server-side | psycopg Measured (S6); pgpq Proposed |
| **Growth:** the phase 1 final pass (10⁴–10⁵ claims) with an agent working the queue | orchestration (R08) | completions stall for the whole finalize, measure and evaluate computation, and vacuum is held back (DA-024) | completions wait only for the cut's row update | Proposed |
| **Failure:** a reader meets a payload schema version it has no upcast for | R06 | old payloads are read under current defaults | refused with a typed reason; the run fails explicitly (DP-24) | Proposed |
| **S9:** test a transformation in isolation | core | holds (strength) | holds: generated types are plain Pydantic; the pool fixtures are Arrow tables | Implemented, Tested by the existing core suite (388 package tests passed, `just check`, at `124473d`, per STATUS 2026-10-28; not rerun) |

## 6. Correctness and fidelity gates (at the baseline)

| Gate | Verdict | Own evidence or scope reason | Required action |
|---|---|---|---|
| G1 Authority | **fail** | Modality, polarity, scope extent, statement role and parse status are independently editable in Python and `core.yaml`, with no reconciliation (DA-002). Invariants are duplicated between Pydantic and CHECKs (F01). D2's pack copies have drifted (DA-011) | R01, R05 |
| G2 Semantic fidelity | **fail** | Qualifier canonical form chosen by JSON shape (DA-001); a `sentence` key misread as a citation (DA-004); case erased (DA-008); unresolved relations dropped (DA-007); `None` used for distinct states (DA-005); prose reasons (DA-013) | R02, R03, R04, R07 |
| G3 Validity | **fail** | A `StoredBatch` with dangling references, or with only supporting evidence, validates (audit probe, 2026-10-28; DA-006). `canonical_condition`'s `ValueError` escapes `key_claims`'s contract (DA-004). Profile vocabulary is unvalidated (DA-010, target) | R03, R04, R05, R06 |
| G4 Hidden behaviour | pass | `core` is pure; settings take their environment as an argument; the CLI builds settings lazily (Implemented; audit) | — |
| G5 Consistency and recovery | unresolved | DA-015 (pass selection, suspected; phase 1); DA-019 (test infrastructure only); per-run publication otherwise sound by design | R07, R08, R11 |
| G6 Transformation and reuse | **fail** | Derived forms are keyed without their derivation, and a frame is edited in place under a referenced id (DA-009); `agent_reuse: by_unit` is undefined (DA-017); a union-find order dependence in the target (F03) | R02, R06, R07, R09 |
| G7 Truthful capability claims | **fail** (minor) | Superseded record ids support "Tested" labels (DA-021); `just deps` covers less than stated (DA-022); generated schemas called an independent oracle (F02) | R11, R12 |
| G8 Library leverage | pass | No generic capability is hand-built where an adopted library clearly provides it. The bespoke compilers are required because LinkML's generators fail named requirements (§8). The hand-written evidence-catalog DDL is an authority issue (G1), not G8 | — |
| CI-G1 Fidelity | **fail** | Unknown read as absent: a dropped citing relation, with coverage silent (DA-007). Meaning relabelled by shape (DA-001) | R02, R04 |
| CI-G2 Evidence closure | unresolved | Served answers are not built. Premise and entity closure would rely on JSON paths (F04). By analogy, design claims cite superseded evidence (DA-021) | R05, R11 |
| CI-G3 Evaluation integrity | pass (design; not re-examined in depth) | Goldens are separate; `eval/` is read by no method; test pages are excluded from fitting and example sets (D7 §4) | — |

## 7. Findings

### 7.1 Additional review findings

<a id="f01"></a>**F01 — Cross-field invariants are defined twice, in Pydantic validators and in D3
CHECKs, with no derivation.**

- **Evidence.** Span ordering is checked four times in Python (`batch._Span`, `payloads._Span`,
  `values.StoredPhrase._span`, `values.StoredPhraseNode._span`) and once in `kb.span`. Local scope
  ↔ scope segment is checked in `StoredEntity` and `CandidateEntity` and in `kb.entity`'s CHECK.
  Parse status ↔ reason is checked in `Segment._well_formed` and in `kb.segment`'s CHECK. The
  object entity-xor-value rule (INV-02) is a union type and also `kb.claim`'s CHECK.
  (Implemented, read at `6f31f75`; D3 Proposed.)
- **Consequence.** An invariant change is made in up to five places. One plausible change is
  zero-width spans for inserted markers, or empty segments (IR-13). When the store is weaker than
  the boundary, bad rows enter through any writer that bypasses Pydantic. When it is stronger,
  COPY refuses valid rows.
- **Principles:** DP-01, DP-03, DP-06; G1.
- **Correction:** R01 and R05, with invariant templates compiled to validators and CHECKs.
- **Closure:** one declaration per templated invariant; generated validator and CHECK; independent
  negative tests at both boundaries (R12).

<a id="f02"></a>**F02 — Generated JSON Schemas are presented as an independent oracle.**

- **Evidence.** The `core/schemas/__init__.py` docstring; `tests/core/test_shapes.py:3-4`; D9 §2's
  jsonschema row. All three call the generated schemas an independent oracle.
- **Consequence.** A wrong model constraint passes every projection. The integrated model makes
  the shared-mistake exposure universal.
- **Principles:** DP-23, DP-22, FP-04; G7.
- **Correction:** R12.
- **Closure:** the wording reads "derivation conformance", and the independent semantic controls
  are named per contract. Lead for the test audit.

<a id="f03"></a>**F03 — Merges by union-find with cannot-link refusal depend on the order of
must-links, while D5 §1 claims order independence.**

- **Evidence.** D5 §3.6; D5 §1 (Proposed, phase 2).
- **Consequence.** With must-links A–B and B–C and a cannot-link A–C, the identities differ by
  processing order, so the same inputs give different entities and keys.
- **Principles:** DP-11, DP-12; G6.
- **Correction:** a declared order in D5 §3.6 (R09).
- **Closure:** a shuffled-order fixture gives equal partitions (probe Q-7).

<a id="f04"></a>**F04 — Decision-relevant claim structure and every relationship that queries
join on are stored only inside JSONB.**

- **Evidence.** D3 §5 `kb.claim.qualifiers`, holding modality, polarity, attribution, condition
  `claim` references and entity-ranged qualifiers; `kb.entity.attrs` holding identity slots;
  D3 §6.1; D8 §5's default modality filter, premise inclusion and `transformations_of`; INV-08.
  (Proposed.)
- **Consequence.** Reference integrity and INV-08 have no store-level enforcement. The D8 premise
  and identity joins go through JSON paths at 10⁴–10⁵ claims per run, a physical route not yet
  examined (A4 unresolved). A business pack's entity-valued qualifiers (owner, sender) cannot be
  joined or checked.
- **Principles:** DP-02 ("promote an opaque payload once decisions depend on its interior"),
  DP-07, DP-03, CI-03; G3; A4.
- **Correction:** R05.
- **Closure:** edge and identity tables with same-run FKs; D8's queries expressed as joins, with
  their plans inspected at run scale.

### 7.2 Finding index

The disposition here is this review's editorial disposition. Execution disposition is assigned at
plan creation: design findings in the [design-phase plan](../../plans/design-phase_2026-10-28.md)'s
table, and build findings in the [phase 0 series](../../plans/phase-0_2026-10-28.md) §11.
Unassigned rows stay with this review until then.

| ID | Finding | Principles · gate | Disposition | Closure evidence |
|---|---|---|---|---|
| [DA-001](../audit/semantic-model-and-authority.md#da-001) | Claim identity undeclared; canonical form by JSON shape | §1 MUST, FP-04, DP-01, DP-02 · G1, G2 | addressed by R02 (spec), R01 (location), R03 (dispatch); **refined:** core qualifiers' roles live in `core`, the conditional role is expressed as a member property | keys, slots and conflicts read one compiled spec; a map entry `{"ref": …}` and `"Shape-Rate"` canonicalized by range |
| [DA-002](../audit/semantic-model-and-authority.md#da-002) | Core closed sets, defaults and qualifier list written by hand | FP-04, DP-01, DP-24 · G1 | addressed by R01 Stage A; `SegmentParseStatus` merged; `ParseOutcome` renamed | every listed set generated; mirror test retired for them |
| [DA-003](../audit/semantic-model-and-authority.md#da-003) | Category behaviour as literal subsets | §1 MUST, FP-04, DP-01, DP-02 · G1 | addressed by R01 (member properties), R05 (SQL literals); **refined** with each closed set's lifecycle and pack extension of `StatementKind` | no consumer tests a literal subset; the email kinds have roles |
| [DA-004](../audit/semantic-model-and-authority.md#da-004) | Operations reinterpret JSON dumps | §1 MUST, FP-04, DP-08 · G2, G3 | addressed by R03 | exhaustive typed dispatch; a qualifier named `sentence` passes |
| [DA-005](../audit/semantic-model-and-authority.md#da-005) | Context translations not complete contracts | FP-04, DP-02, DP-05, DP-08 · G2 | addressed by R04 (with X2-01) | translation completeness tests; candidate set carries the whole batch |
| [DA-006](../audit/semantic-model-and-authority.md#da-006) | References untyped; two owners of reference checking | DP-02, DP-03, DP-07, CI-03 · G3 | addressed by R04 (types, owner) and R05 (FKs) | a wrong-kind reference refused with a code; D1 §10.3 names `validate` |
| [DA-007](../audit/semantic-model-and-authority.md#da-007) | Unresolved reference dropped | CI-03, CI-04, DP-02 · CI-G1 | addressed by R04 (`ExternalReference`) | "what does X follow from" serves an unresolved reference with coverage |
| [DA-008](../audit/semantic-model-and-authority.md#da-008) | Case erased in labels and literal slots | DP-02, DP-04 · G2 | addressed by R02 (case policy) | `X`/`x` and `\Sigma`/`\sigma` key apart where declared math-bearing |
| [DA-009](../audit/semantic-model-and-authority.md#da-009) | Contracts, key scheme and derived forms unversioned | DP-01, DP-04, DP-09, DP-24, CI-13 · G6 | addressed by R06 (revisions, registry, derivations) and R02 (scheme, vectors, carry-over) | the schema-version hash covers the model revision; `payload_schema_id` on cross-revision rows; vectors pinned |
| [DA-010](../audit/semantic-model-and-authority.md#da-010) | Source profiles carry schema vocabulary outside versions | DP-05, DP-01, DP-03, DP-24 · G3 | addressed by R06; **refined:** hints stay in the profile and are typed against core vocabulary (moving them to the pack rejected) | a profile naming an unknown kind is refused at run start |
| [DA-011](../audit/semantic-model-and-authority.md#da-011) | Design documents restate executable contracts | DP-01, DP-24 · G1 | addressed by R01 and R05; **refined** to cover table structure (the planned hand port of D3 into `core/db`) | D2 and D3 cite model files and generated DDL |
| [DA-012](../audit/structure-and-invariants.md#da-012) | Operational closed sets with uneven authority | DP-02, DP-03, DP-08 · G3 | addressed by R07 and R05 | `Stage` and unit type checked; policy literal typos fail at compile |
| [DA-013](../audit/structure-and-invariants.md#da-013) | Keying and frame outcomes are prose | DP-21, DP-02 · G2 | addressed by R07 | `PassReport` counts by code |
| [DA-014](../audit/structure-and-invariants.md#da-014) | Locator limits narrower than a closure check | DP-04 · G6 | addressed by R02 (text in D1 §10.3; P0CL-01 wording) | the stated limit includes the ordinal shift |
| [DA-015](../audit/structure-and-invariants.md#da-015) | No rule for the current M19 pass (suspected) | DP-19, DP-05 · G5 | addressed by R07 and R08 | readers use the sealed run's final pass |
| [DA-016](../audit/structure-and-invariants.md#da-016) | Confidence policy data split between file and prose | DP-05, DP-01 · G1 | addressed by R07 | priors, multipliers and caps keyed by a modelled source vocabulary |
| [DA-017](../audit/structure-and-invariants.md#da-017) | `agent_reuse: by_unit` undefined | DP-09 · G6 | addressed by R07: **remove** until defined (review#RC13) | option absent, or defined as a declared dependency |
| [DA-018](../audit/boundaries-and-composition.md#da-018) | Extension versions not pinned or reconciled | DP-15, DP-09 · G3 | addressed by R11 | a version mismatch fails startup and fixtures; template hash includes versions |
| [DA-019](../audit/boundaries-and-composition.md#da-019) | Sweep can drop a template in use | DP-19, DP-20 · G5 | addressed by R11 (local) | a parallel checkout's template survives a sweep |
| [DA-020](../audit/boundaries-and-composition.md#da-020) | Coordinates repeated; provisioning prose stale | DP-01, DP-24 · G1 (low) | addressed by R11 (local) | one source per coordinate; D3 §3 updated |
| [DA-021](../audit/local-reasoning-and-assurance.md#da-021) | Evidence citations as free text | DP-22, DP-21, DP-01 · G7 | addressed by R11 and R10 (catalog from `Record`) | `check` warns on superseded citations; catalog generated |
| [DA-022](../audit/local-reasoning-and-assurance.md#da-022) | Dependency check narrower than stated | DP-22 · G7 | addressed by R11 | a Python range fails `just deps` |
| [DA-023](../audit/local-reasoning-and-assurance.md#da-023) | Binding map empty | DP-24 | addressed by review#RC18 (rows proposed) | binding §1 lists §B1–§B6 |
| [DA-024](../audit/execution-fit.md#da-024) | Final transaction locks the run across measure and evaluate | FP-07, DP-19, DP-20 · A4 | addressed by R08 | completions wait only for the cut's update |
| [DA-025](../audit/execution-fit.md#da-025) | Keying repeats rendition-wide work | FP-07, DP-10 · A4 (low) | addressed by R11 (local); R09 keeps keys in Python | annotation units and segment keys prepared once |
| [F01](#f01) | Invariants defined twice | DP-01, DP-03, DP-06 · G1 | R01, R05 | one declaration per templated invariant |
| [F02](#f02) | Generated schemas called an independent oracle | DP-23, DP-22 · G7 | R12 | wording corrected; independent controls named |
| [F03](#f03) | Union-find order dependence | DP-11 · G6 | R09 | shuffled-order fixture |
| [F04](#f04) | Relationships and decision-relevant scalars only in JSONB | DP-02, DP-07, CI-03 · G3, A4 | R05 | edge and identity tables; D8 joins with inspected plans |
| X2-01 (phase 0 plan §11) | Authored → stored renaming | — | consumed by R04 (generated name map); its plan row stays the owner | as the plan states |

No audit finding is rejected.

### 7.3 Foundation and supporting-rule verdicts (baseline)

| Principle | Verdict | Basis |
|---|---|---|
| FP-01 | violated for semantic ownership; satisfied for module dependencies | Identity rules are decided in keying code, and meaning from JSON shape. `core`'s imports and acyclicity hold (audit) |
| FP-02 | violated | Contracts unversioned (DA-009); translations incomplete (DA-005) |
| FP-03 | satisfied in the main (the observation/consolidation split, the queue); violated for packs | A pack's modality or identifier qualifier needs core edits (DA-001, DA-003) |
| FP-04 / core §1 MUST | **violated** | Causes A–D |
| FP-05 | violated in parts | References, unresolved endpoints, prose outcomes, the run-cut lifecycle |
| FP-06 | satisfied | S9 holds; pure functions; local fixtures |
| FP-07 | violated (DA-024); otherwise credible | §12 |
| DP-01 | violated | DA-002, DA-011, F01 |
| DP-02 | violated | DA-001, DA-005, DA-008, F04 |
| DP-03 | violated | DA-006, DA-010, F01 |
| DP-04 | violated | DA-008, DA-009 (key scheme), DA-014 |
| DP-05 | satisfied, except DA-010 | Observations, bindings and the recorded reference run are separate |
| DP-06 | violated | Restated structure (DA-002, F01) |
| DP-07 | violated | DA-006, F04 |
| DP-08 | violated | DA-004, DA-005 |
| DP-09 | violated | DA-009, DA-017 |
| CI-01 | satisfied (design) | Observations carry task and configuration |
| CI-02 | violated | Shape-based relabelling (DA-001); prose outcomes (DA-013) |
| CI-03 | violated | DA-006, DA-007, F04 |
| CI-04 | violated | DA-007 |
| CI-05 | satisfied (design) | Rule-view universes are declared by call site (`at:`) and builder; queries state their scope |
| CI-06 | unresolved | `VerificationPayload` verdict without a stated model (the audit's suspicion; phase 4) |
| CI-11 | unresolved (not built); violated by analogy for design claims | F04; DA-021 |

## 8. Library fit and total complexity

| Capability and owner | Candidates | Semantic fit and gaps | Burden | Choice |
|---|---|---|---|---|
| Model language (model) | LinkML; Pydantic as the model; OWL/SHACL | LinkML: classes, slots, enums with permissible-value metaslots, subsets, `unique_keys`, imports, `version`, `SchemaView`; no schema diff; experimental `rules`. Pydantic: precise runtime shapes, but domain packs in YAML are needed anyway | moderate | **LinkML** for all modules (R01) |
| Python generation (schema) | `gen-pydantic`; a subclass; an own emitter | `gen-pydantic` 1.12.1: no discriminator, `Optional = None`, unfrozen (Interface-checked 2026-10-28); subclass or own emitter needed | moderate, one-time; probe Q-1 | **Stage A now; Stage B after Q-1; fallback stated** |
| Relational projection (schema → store) | `gen-sqltables`; `RelationalModelTransformer` + own `MetaData` compiler; hand `MetaData` | `gen-sqltables` gives native enums, no CHECK, no JSONB, DDL string only (Interface-checked). The transformer is public and records FK annotations and multivalued link tables (contributor A); LinkML calls its database support incomplete | moderate | **Own compiler over `SchemaView`**, transformer optional; physical overlay hand-written |
| Migrations (store) | Alembic 1.20 | Autogenerate compares named CHECKs *by name only* (opt-in plugin), PG indexes by uniqueness and expressions, no native-enum values (Documented §4.1–§4.2). Comparator and plugin hooks exist | small | **Alembic**, with digest-named CHECKs; catalog comparison test kept |
| DDL comparison (one-time port check; query checks) | pglast 8.7 | PG18 grammar; `parse_sql`; equality ignoring locations; `referenced_relations`; needs a normalizing projection; cannot prove execution | small; unpinned | **Adopt for the port check and the query-relation check** |
| Runtime validation (core, validate) | Pydantic 2.14 | Exact: frozen, discriminated, `MISSING`, `TypeAdapter`, `GenerateJsonSchema` (S4 Tested) | — | **keep**, generated |
| External validation and decoding (schema) | jsonschema 4.26 + `referencing` | Registry, multi-draft, `check_schema`; slower and less precise than Pydantic (S4 Tested) | small | **derivation check and external consumers**, not an oracle (R12) |
| Pool and analytics engine (consolidate, evaluate, exports) | DuckDB 2.0; PyArrow Acero; PostgreSQL SQL; Python | DuckDB: full optimizer, windows, `USING KEY`, ordered aggregates, Parquet/VARIANT, relation readers; new release; no casefold. Acero: experimental, no window or recursion. PG: transactional, but breaks fixture-local testing for consolidation | moderate (new product dependency) | **DuckDB for set steps (phase 1 onward); PG for transactional sets; Python for identity** |
| Interchange format | PyArrow 26 | Typed schemas with metadata; no enforcement; no recursion; null only; `unify_schemas` not semantic evolution (Documented §2.3–§2.4, §14.2) | small | **adopt** for the pool, COPY, Parquet; no custom extension types |
| Arrow → PG bulk | psycopg 3.3 binary COPY; pgpq 0.12; ADBC 1.13 | psycopg: measured, needs `set_types`. pgpq: Alpha, no timestamptz, JSONB via a string encoder. ADBC: append without upsert, JSONB only from `arrow.json`, no struct writer | small | **psycopg now; pgpq when rows are Arrow; ADBC for reads** |
| Connections | psycopg-pool 3.3.3 | `configure`/`check`/`reset`; exceptions in `configure` become retries | small; unpinned | adopt as D3 §1 states; version checks outside `configure` |
| Vectors | pgvector 0.8.7, pgvector-python | Partial HNSW per family with literal predicates; `HALFVEC(dim=None)` | phase 1 | embedding spec as a modelled fact (R10) |

**Total machinery.** The target adds roughly eight compilers or tools, each a pure function of
`SchemaView`:

1. Python generation (Stage A, then Stage B);
2. the `MetaData` compiler;
3. the CHECK, invariant and FK rules inside it;
4. Arrow schemas;
5. the registry writer;
6. the model diff and change classifier;
7. the translation-completeness tests;
8. the conformance vectors.

It adds three relational tables for edges and identity, two registry tables and one overlay
module. It removes:

- the hand mirror and its partial contract test;
- `vocab.py` as an authority;
- the hand-written `Literal`s and defaults;
- four of five copies of span ordering;
- the hand port of D3 into `core/db`;
- D2's and D3's inlined copies;
- the evidence catalog's hand DDL;
- per-change edits in four to six places for every qualifier, kind or vocabulary change.

One declaration then expands into several generated objects (H27). That is justified only because
each object has a consumer that today restates the fact by hand, and because no production data
yet exists that would make the move expensive. The proportionality test for later additions to
the declaration vocabulary is AGENTS.md's: each annotation must have a real consumer.

## 9. Alternatives and tradeoffs

| Alternative | Change propagation | Authority and composition | Machinery and risk | Decision and revisit |
|---|---|---|---|---|
| **Current baseline** (Pydantic shapes, LinkML vocabulary, `vocab.py` → CHECKs, D3 DDL hand-ported) | 4–6 edits per qualifier, kind or vocabulary change | several authorities joined by a partial contract test | low now, growing per change | rejected: A2 MUST gap |
| **Proposed: one LinkML model, generated projections, physical overlay, hand-written operations** | one declaration plus regeneration; genuinely new behaviour in its owning function | one model revision and schema version; projections derived | compilers to build; generator feasibility (Q-1) | **chosen**; revisit if the overlay grows a second physical vocabulary that mirrors SQLAlchemy |
| **Pydantic as the authority** for core shapes and operational sets; LinkML pack and `core.yaml` generated from Python; hand `MetaData` | one edit for core facts; pack facts in YAML | two authoring languages with generated bridges; change classification over two introspection APIs | an own Python → LinkML emitter; member properties as Python metadata | **the fallback for shape structure only** (R01) if Q-1 fails |
| **Operational tables as hand-written `MetaData`**, with vocabularies and invariants generated from the model | one edit per table change, in Python | D1 ↔ D3 restatement remains for knowledge tables | less compiler work | rejected for knowledge tables; acceptable for purely operational tables if the overlay sprawls (same revisit trigger) |
| **Simplest viable:** keep all forms and extend the mirror contract test to every enum, default, qualifier and invariant (the audit's lead) | edits in every place, each checked | reconciliation protocol (G1 pass), DP-01 still violated (many writable sources) | least new code; the cost recurs per change | rejected as the target; it is the right **interim** guard for anything Stage A has not yet generated |
| **Everything in PostgreSQL** (consolidation as SQL; DuckDB only for exports) | — | one engine | breaks fixture-local testing (FP-06); identity forms split | rejected; PG keeps transactional set work |
| **Files as the payload store** (Parquet/IPC referenced by rows) | schema free | breaks §B4's one transaction | orphan files | rejected for authority; accepted for exports |

## 10. Verification and uncertainty

| Claim | Label · date | Basis | Gap |
|---|---|---|---|
| Closed sets agree across Python, `core.yaml` and the CHECKs today | Tested (audit contributor scripts, 2026-10-28, not retained) | audit | nothing keeps them equal (DA-002) |
| `gen-pydantic` emits no discriminator; `gen-sqltables` emits native enums, no CHECK, no JSONB | Interface-checked · 2026-10-28 | grep of installed LinkML 1.12.1 | — |
| SQLAlchemy 2.1.5 has `CreateView`/`CreateTableAs`; Alembic 1.20.0 has `checkconstraint_byname` | Interface-checked · 2026-10-28 | installed source | Alembic's treatment of views unverified |
| Pydantic → jsonschema agreement is a derivation check | Proposed (reasoning) | F02 | — |
| psycopg binary COPY at run scale | Measured · S6, 2026-10-28 | interim cluster; rerun on `18/corpus` pending (D3 §11) | — |
| DuckDB 2.0.0 VARIANT/Parquet/`KV_METADATA`, `USING KEY` components, no casefold | Interface-checked · contributor B, 2026-10-28 | scratch data | VARIANT predicate pushdown undocumented |
| PyArrow 26 Acero reader-source node and join types | Documented (overview §4.2, §13.1; v26 release notes) | not installed | streaming memory of joins |
| Every remedy R01–R12 | Proposed | this review | — |

**Decisive feasibility questions.** These are probes to arrange within the repository's timing;
none was run.

- **Q-1 (decides RC01's Stage B, or its fallback).** Does a `PydanticGenerator` subclass, or an own
  emitter, over S4's `core.yaml` produce the following?
  - discriminated `t`/`op` unions with a named recursive `Condition`;
  - `MISSING` defaults;
  - frozen models with tuples;
  - the authored and stored variants from `ci:form`;
  - prefixed aliases.

  The test: diff against `values.py` and `batch.py`, validate S4's 135 batches, and compare the
  committed JSON Schemas byte for byte.
- **Q-2.** Do permissible-value `in_subset` member properties pass `linkml-lint` and read back
  through `SchemaView`?
- **Q-3.** Generate `MetaData` from a LinkML sketch of five D3 tables plus the overlay, and compare
  it with S6's DDL through the pglast-normalized projection. What residue remains?
- **Q-4.** Run COPY at run scale with same-run composite FKs and per-version vocabulary FKs, then
  without them, on `18/corpus`. This pairs with D3 §11's pending rerun. It decides whether
  INV-03 and INV-08 are enforced by FKs or by the bulk writer (R05).
- **Q-5.** The pool round trip: ADBC `fetch_record_batch` → DuckDB relation → Arrow →
  psycopg/pgpq COPY. Check absent versus null, JSONB, timestamptz and the memory of one join.
- **Q-6.** Key carry-over between two schemes over the fixtures; conformance vectors stable across
  two processes and a Pydantic patch bump.
- **Q-7.** A deterministic must-link order against `USING KEY` components with a cannot-link
  anti-join (F03).

**Unexamined breadth that does not change the verdict:** `tex.py` and the math grammar; D7's
alignment; the MCP tools; the GLiNER2 compiler; spike code beyond the S4 pack.

**Missing premises.**

- Multiple packs per project (§1). This affects R04's naming rule and R05's vocabulary scoping.
- Q-1's outcome. This affects RC01's Stage B.
- Q-4's outcome. This affects R05's enforcement placement.

## 11. Authority changes and dispositions (rule impacts)

These are rules the recommended design would change. They take effect only after operator
confirmation in plan creation (binding §4). The review neither edits them nor routes them.

| ID | Rule and where recorded | Proposed change | Depends | If the rule is kept |
|---|---|---|---|---|
| <a id="rc01"></a>RC01 | ADR-0017 and §B5 ("Pydantic owns the core shapes; `core.yaml` is their contract-tested mirror"); D2 §6; phase 0 plan §3 decision 1 | LinkML `core` becomes the authority. Stage A generates vocabularies, specs, defaults and invariants into Python now; Stage B generates the shape structure after Q-1. The mirror test retires. ADR-0017's "the pack owns domain vocabulary" is kept | R01, R02, R05, R06 | Generate `core.yaml`'s enums and slots *from* the Pydantic models and a Python vocabulary (an own emitter), and extend the contract test to every enum, default, qualifier and invariant. The system model then stays hand-written `MetaData` (RC03 kept) |
| <a id="rc02"></a>RC02 | DESIGN §B4 and ADR-0016 ("PostgreSQL 18 is the single authority … DuckDB serves analytics and exports only"); D3 §1 | PostgreSQL is the transactional authority for *instances*; the model is the authority for *structure and meaning*. DuckDB may run consolidation's set-based steps in process, with no persistent state | R09 | R09 shrinks to analytics and exports. Pool steps stay Python; the relational pool contract still serves exports |
| <a id="rc03"></a>RC03 | D3's header ("The DDL below is the specification for the first Alembic migration"); D3 §1 migrations row; D9 §1 (`core/db` "from D3"); D2 §6/§9 and D3 §6.2 inlined copies | `MetaData` generated from the model plus a physical overlay; 0001 still generated once and frozen; D2 and D3 cite model files and generated renderings | R01, R05 | D3 remains the DDL authority. The generated or hand `MetaData` is checked against it by the pglast-normalized comparison, a reconciliation protocol with two sources kept |
| <a id="rc04"></a>RC04 | Phase 0 plan: `vocab.py` → CHECKs in P0-F-4; `vocab.py`'s "one string enum per list" | `vocab.py` is generated from the model's system enums | R01 | `vocab.py` stays the authority for operational sets, and the model imports them through an emitter |
| <a id="rc05"></a>RC05 | D3 §1 ("Closed value sets are `text` with `CHECK` … adding a value is a one-line migration") | Two lifecycles: static sets by CHECK; schema-version-scoped sets by per-version rows and composite FKs | R05 | Version-scoped sets are validated only in Python, at the boundary and at write |
| <a id="rc06"></a>RC06 | D3 §5 and §6.1 (`kb.claim.qualifiers` holds every qualifier; `kb.entity.attrs`; no edge tables) | Modality, polarity and attribution become columns; edge and identity tables; `ExternalReference` rows; `kb.claim.schema_version_id` | R05 | References stay in JSONB. Integrity rests on repository assertions, and D8 joins use JSON paths, accepted only with plans inspected at phase 1 scale |
| <a id="rc07"></a>RC07 | D1 §10.1 status line ("fixture tests compare key equalities, never key values, so a fixture never pins a hash") | Add per-scheme conformance vectors that pin values; fixtures still compare equalities | R02 | A key-scheme drift (dependency, Unicode, dump behaviour) is detectable only by review |
| <a id="rc08"></a>RC08 | D1 §10.1, §10.3; D5 §7.3 | The key scheme is recorded per run and per judgment target; a scheme change ships a carry-over map; D1 §10.3 lists derivation changes and the ordinal shift | R02, R06 | Any canonical-form fix is an unannounced key migration |
| <a id="rc09"></a>RC09 | D2 §2 (the schema-version hash); D2 §8 (the versioning table); D3 `meta.schema_version.migration`; D3 `kb.observation` (no payload version) | Model revision; a schema version that includes it; `meta.payload_schema` registry; `payload_schema_id`; change records with compatibility classes; Alembic revisions linked; versioned frames | R06, callout | DA-009 remains, and the no-migration route has no governed registry, so it should not be used |
| <a id="rc10"></a>RC10 | D6 §3.1 (the final pass holds the update lock and sets `finished_at`); D3 §8 (fates against `finished_at`) | `cut_at` sealed in a short transaction; fates and views read the cut; measure and evaluate after | R08 | DA-024 stands; accept the stalls at phase 1, with a revisit trigger |
| <a id="rc11"></a>RC11 | D1 OPEN-D1-5 (`extref` deferred; references `unsupported`); D2 §7.3 V2 (`outside` "left unresolved"); D3 §5 statement-row note | A typed `ExternalReference` node with a descriptor and resolution | R04 | Reconcile on one of the current treatments: D1's `unsupported`, with D2 dropping `outside` |
| <a id="rc12"></a>RC12 | D4 M01 profile vocabulary; D6 §7.2 (profile overrides `ci:claim_bearing`) | A profile model typed against core vocabulary, validated against the run's schema version, inside the change model | R06 | Profile names stay validated nowhere (DA-010) |
| <a id="rc13"></a>RC13 | D6 §4 `agent_reuse: by_unit` | Remove until its dependency is defined | R07 | Define its matching rule, the applicable guideline sections, as a declared digest input |
| <a id="rc14"></a>RC14 | D6 §7.1–§7.2 (`judgment(m)`; untyped literals); D4 §1 `Method.unit_type` (`span`); D3 `ops.task.stage` and `ops.policy_rule.unit_type` (no CHECK); D5 §6.3 and D6 §7.1 prior keys | Modelled vocabularies; typed policy symbols; literal checks at compile | R07 | Policy typos compile and never match (DA-012) |
| <a id="rc15"></a>RC15 | D5 §3.6 (union-find with refusal) | Declared must-link order (score, then key) | R09, F03 | D5 §1's order-independence claim must be narrowed |
| <a id="rc16"></a>RC16 | D9 §2 (jsonschema "an independent oracle"); the `core/schemas` docstring; `test_shapes.py` | "Derivation conformance"; independent semantic controls named | R12 | The G7 claim stays untrue |
| <a id="rc17"></a>RC17 | AGENTS.md *Reporting* vocabulary against `Record.outcome` (`partial`) | Records use AGENTS.md's outcomes with an explicit scope field; or AGENTS.md admits `partial` for records only | R11 | Two outcome vocabularies |
| <a id="rc18"></a>RC18 | Binding §1 ("None yet") | Rows: §B1 → DP-02, DP-04, DP-07, CI-02, CI-03 · G1, G2. §B2 → DP-05, DP-09, DP-19, CI-01 · G5, G6. §B3 → DP-19, DP-20, CI-10 · G4, G5. §B4 → DP-01, DP-10, DP-19, CI-13 · G1, G5. §B5 → DP-01, DP-06, DP-24 · G1, G2. §B6 → DP-05, DP-15, DP-18, CI-09 · G4, G7 | DA-023 | Each review reconstructs the mapping |
| <a id="rc19"></a>RC19 | D1 §10.3 (side-table owner "foundations") against D2 §7.3–§7.4, D4 §4.3, D5 §1 (`validate`) | `validate` owns reference and type checks for batches; the keying resolver owns kind refusals for pool candidates | R04 | Two named owners (DA-006) |

## 12. Architectural judgment and decision

| Judgment | Verdict (baseline) | Scenario evidence and scope | Target (Proposed) |
|---|---|---|---|
| A1 Localize change | **violated** | S1, S2 and S7 each need independent edits in four to six owners (DA-001, DA-002, DA-003, F01) | satisfied for S1, S2, S3/S7 and S4: one declaration plus regeneration |
| A2 Encode domain meaning explicitly | **violated** (core §1 MUST, in scope) | Causes A–D: types exist, but meaning is decided procedurally, in several places, without versions; relationships and unknowns are not modelled | satisfied at Proposed strength, subject to Q-1 (or its fallback) and Q-2 |
| A3 Extend through composition | **violated** for a second pack | A pack's modality, identifier qualifiers and statement kinds need core edits; profile vocabulary is unvalidated | satisfied: §5's S2 needs pack declarations only. The toy second pack (phase 0 plan §3 decision 17) is the closure check |
| A4 Fit execution to the workload | **violated** (DA-024 at phase 1); unresolved (F04 premise joins) | The run lock spans the terminal computation while agents complete; JSON-path joins at 10⁴–10⁵ claims unexamined | credible: short cut (R08); index-backed edges written once per run (R05); a relational pool with set steps in DuckDB and identity in Python (R09). Q-4 and Q-5 settle the unmeasured parts; no speed is claimed |

**Bounded decision: Revise.** The in-scope core §1 MUST gap (A2) and the failed G1, G2, G3, G6,
G7 and CI-G1 gates on claimed behaviour require revision. Current outputs are correct, but that
cannot offset them.

**Enclosing architecture: needs revision** in the semantic-authority, identity, relational
projection and change layers. The rest is accepted for the named scenarios at the strength the
design labels it, as the prior review found:

- the claim form;
- the observation/consolidation split with per-run materialization;
- content identity and locators;
- the queue and its fencing;
- content-keyed reuse.

That acceptance is not release qualification.

**Priority by consequence, separate from prerequisite order:**

| Priority | Change and responsible component | Findings | Closure evidence or trigger |
|---|---|---|---|
| 1 | R02, R03 and R04 in `core` and `validate`: identity declared, typed dispatch, complete translations, typed references, unresolved endpoints. These are fidelity failures | DA-001, DA-004–DA-008, DA-013, DA-014 | keys from specs; exhaustive dispatch; translation completeness; `ExternalReference` served |
| 1 | R01 Stage A and R06 in `schema`, `core/_model` and `meta`: one model authority for facts; revisions and registry before any data is stored | DA-002, DA-003, DA-009, DA-010, DA-011, F01 | generated vocabularies and specs; schema-version hash covers the model revision |
| 2 | R05 in `schema` → `core/db`: the relational projection, before 0001 is generated | F04, DA-012, DA-011 | pglast port check; catalog comparison; FKs (or the bulk writer, per Q-4) |
| 3 | R07, R08 in orchestration and policies (phase 1 relevance); R12 in tests | DA-012, DA-013, DA-015–DA-017, DA-024, F02 | typed vocabularies; short cut; independent controls |
| 4 | R09, R10 in consolidation and exports (from phase 1); R11 (local, any time) | F03, DA-018–DA-023, DA-025 | pool contract with two implementations; local fixes |

**Prerequisite order:**

1. R03 needs nothing and can start at once.
2. R01 Stage A gives the vocabulary and specs that R02 and R04 consume.
3. The `system` module of R01, together with R05, gives the tables that R06's registry rows
   attach to.
4. R06 precedes R09 and R10, because the pool and exports carry registry ids.
5. R01 Stage B waits on Q-1 and blocks nothing else.

P0-S-1 (pack compilers) is where Stage A, the qualifier specifications and the name map naturally
land. P0-F-4 (0001) is where R05 lands. Both are the next packages in STATUS, which is why the
priority-1 and priority-2 items precede them in meaning.

**Next consequential decision and owner.** The operator confirms or rejects, in plan creation:

- RC01, the direction of authority;
- RC03, the DDL authority;
- RC09, the change model.

Plan creation then routes the design findings to the design-phase plan, and the build
consequences (P0-S-1, P0-F-4, R11's local fixes) to the phase 0 series. Q-1 and Q-4 are the first
probes to arrange, because they choose between stated variants of R01 and R05.
