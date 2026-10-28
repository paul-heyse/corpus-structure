# Semantic model and authority

Findings about model adequacy and about who decides a meaning: the core §1 semantic-model-first
MUST, FP-04/A2, DP-01, DP-02, DP-04–DP-06 and the code-intelligence profile CI-01–CI-04 and CI-13,
applied by analogy. Baseline, scope and change scenarios (S1–S9) are in the [README](README.md).
The [domain model map](domain-model-map.md) gives the model these findings refer to.

Most of these findings come before any incorrect output: at `024bb33` every closed set agrees, and
the key tests pass. They are structural. They show where meaning is decided procedurally or more
than once, so that the next supported change (a qualifier, a pack, a vocabulary value, a schema
version) has to be made in several places that nothing keeps in step.

<a id="da-001"></a>

## DA-001 — Claim identity has no single declaration, and qualifiers are canonicalized by JSON shape

**Principles:** core §1 MUST, FP-04, A2, DP-01, DP-02, DP-06.
**Subject:** implemented (`core/keys.py`); accepted target (D1 §5.2, §10.1; D5 §5.4–§5.5).

**Diagnosis.** Which qualifiers make two claims different facts is decided in three kinds of place:
- **Core qualifiers, in code.** `claim_parts` (`core/keys.py:432-446`) hard-codes the rule:
  - modality, polarity, conditions and `valid_time` are always identity;
  - attribution is identity only when modality is `cited`;
  - hedge and scope never are.
- **Schema qualifiers, in pack data.** `KeySchema.identity_qualifiers` comes from
  `ci:identity_qualifiers`.
- **Prose.** The same rules are restated in D1 §5.2's "In the key" column and in §10.1. D5 adds its
  own statements of the modality-dependent part: the functional slot includes "the cited source"
  (§5.4), and only modalities `asserted` and `defined` conflict (§5.5).
- **Not in the pack.** The core.yaml design copy declares the core qualifiers with no identity
  marker.

How a schema qualifier enters a key is then chosen from its JSON shape, not from its declared range
(`canonical_qualifier`, `core/keys.py:454-462`):
- a dict with a `t` key, or with exactly the key `ref`, is read as a value or an entity reference;
- every other string is casefolded.

A contributor's scratch probe on 2026-10-28 reproduced the consequences (not retained):
- `"Shape-Rate"` keys as `shape-rate`;
- a map entry `{"ref": "Smith"}` is resolved as an entity reference.

**Consequence.**
- **S1, add an identity qualifier or a modality that changes identity.** An example is a business
  modality `reported` under which attribution identifies. The change touches:
  - `core/batch.py` (both qualifier models and `CORE_QUALIFIERS`);
  - `core/keys.py`;
  - D1's table;
  - the future slot and conflict code in C1.

  Each states the rule independently.
- **S2, a second pack.** A qualifier ranged on an enum or an identifier string is casefolded, and a
  map whose entry names include `t` or `ref` is misread. Distinct meanings can share a key, or one
  meaning can split.

**Footprint.**
- Known: `claim_parts` and `canonical_qualifier`; D1 §5.2 and §10.1; D5 §5.4 and §5.5.
- Suspected: the C1 slot and conflict code, once written, will restate the rule again.

**Counterevidence.** The core identity rules are an accepted decision (P0CL-06), so they are not
drift. S1's per-predicate models will type qualifiers, but `keys.py` reads `model_dump` JSON and
would still choose the canonical form from shape ([DA-004](#da-004)).

**Leads.** One declaration per qualifier, in core.yaml or the pack:
- its key role (identity, meaning-bearing outside the key, or inert);
- any condition on that role (attribution under `cited`);
- its canonical form, chosen by range.

That declaration would compile into `KeySchema`, and keys, functional slots and conflict detection
would consume it.

**Related:** [DA-002](#da-002), [DA-003](#da-003), [DA-004](#da-004).

<a id="da-002"></a>

## DA-002 — Core closed vocabularies and the core qualifier list are written by hand in several places

**Principles:** FP-04, A2, DP-01, DP-03, DP-06, DP-24; §G "generated from one source".
**Subject:** implemented; accepted target (DESIGN §B5, ADR-0017, D2 §6).

**Diagnosis.** ADR-0017 makes the pack the owner of domain vocabulary and Pydantic the owner of the
core shapes. The closed sets inside the core shapes nonetheless have several independent
definitions:
- **Modality, polarity, scope extent, bind kind and formula parse outcome** are Python `Literal`s
  (`core/batch.py:43-48`, `core/values.py:47-50`) and also enums in core.yaml.
- **Statement role and evidence role** are `vocab.py` StrEnums (`vocab.py:202`, `:231`), core.yaml
  enums and D3 CHECK text.
- **The modality and polarity defaults** exist twice: `batch.py:58-59`, and `ifabsent` in core.yaml.
- **The core qualifier list** exists in four places:
  - `CORE_QUALIFIERS` (`batch.py:97`);
  - the `StoredQualifiers` fields;
  - the constants in `keys.py:50-51`;
  - core.yaml's slots, and D3 §6.1 in prose.
- **The delimiting parse status** has two code definitions. `evidence.ParseStatus` (a Literal with
  its severity order, `evidence.py:64-65`) is what `Segment` uses. `vocab.SegmentParseStatus`
  (`vocab.py:122`) is used nowhere (grep of `python/`, 2026-10-28). The name `ParseStatus` also
  means two different things: the segment's delimiting status in Python, and a formula's parse
  outcome in core.yaml. D3 §5 had to separate them explicitly after S6.

The designed mirror contract test (D2 §6; spike `code/s4/contract.py:108-118`) covers value tags,
bind kinds, binding fields, `EntityRef` and evidence roles. It does not cover:
- modality, polarity, scope extent, statement role or parse status;
- the defaults;
- the qualifier list.

No production mirror test exists yet; that is P0-S-1. A contributor's comparison on 2026-10-28
found every one of these sets equal today (scratch scripts, not retained). The finding is that
nothing keeps them equal.

**Consequence.**
- **S7, add a modality or a parse-status value.** About five independent edits are needed. Only
  the `vocab.py` → D3 CHECK direction is to be generated (P0-F-4). A missed `Literal` makes Pydantic
  refuse a value the pack declares, or accept one it does not.
- **S1, add a core qualifier.** core.yaml, both qualifier models, `CORE_QUALIFIERS`, `keys.py` and
  D3 §6.1 change, with no check between them.

**Footprint.**
- Known: the files named.
- Suspected: rule views and the S1 compilers will add copies.

**Leads:**
- generate one side from the other (the Python sets from core.yaml, or core.yaml's enums from
  Python), or extend the mirror test to every core enum, default and qualifier slot;
- remove `SegmentParseStatus`, or make it the one definition and rename the formula-parse enum.

**Related:** [DA-001](#da-001), [DA-011](#da-011), [DA-012](structure-and-invariants.md#da-012).

<a id="da-003"></a>

## DA-003 — The behavioural roles of categories are hard-coded subsets rather than declared properties

**Principles:** core §1 MUST, FP-04, A2, DP-01, DP-02, DP-06.
**Subject:** implemented; accepted target.

**Diagnosis.** Several categories have members whose behaviour differs. That behaviour is not a
declared property of the member. Each consumer tests membership in a literal subset instead.
- **Modality.**
  - `supposed` forms a premise and is excluded from default queries (D5 §5.1, D8 §5).
  - `cited` makes attribution identity-bearing (`keys.py:444`).
  - `asserted` and `defined` can conflict (D5 §5.5).
  - Structural claims are always `asserted`.

  Keys, consolidation, queries and the invariant INV-06 each state their own subset.
- **Segment kind.**
  - An annotation unit is a `unit`, or a `paragraph` at the top level (`locators.py:417-418`, with
    `_NOT_UNCOVERED` at `:44`).
  - A statement anchor is a `details` or a `unit` (`keys.py:386`).
  - The BM25 block level is a kind list in D3 §5; split and target kinds are D4 lists (M03, M05,
    M06).
  - `ci:target: "unit paragraph"` strings in core.yaml are not checked against `SegmentKind`.
- **Statement kind.** The kind is a plain `str` in core (`batch.py:207`, `candidates.py`). Its
  behaviour (`ci:claim_bearing`) exists only in the pack, and source profiles can override it
  ([DA-010](#da-010)).

The email kinds are declared in `SegmentKind` so that adding the source needs no migration, but no
consumer gives them a role. As `annotation_units` is written, an `email_message` under the document
becomes one uncovered block with no annotation unit (reading of `locators.py`; not run).

**Consequence.**
- **S3, a new adapter or source**, and **S7, change segment kinds:** each role subset is found and
  edited separately.
- **S2, a business pack with its own modalities or statement kinds:** each consumer must be taught
  the new member's behaviour.

**Footprint.** Known: the sites named. Suspected: C1 and the D8 queries will add further membership
tests.

**Counterevidence.** Branching over a genuine domain alternative is valid (DP-06). The defect is
that the same property is restated in each consumer, not that the code branches.

**Leads:** declare the roles as properties of the members, for example:
- a modality is assertoric, premise-forming or attribution-bearing;
- a segment kind is an annotation unit, a statement anchor or a search block.

Consumers would read the property.

**Related:** [DA-001](#da-001), [DA-002](#da-002), [DA-010](#da-010).

<a id="da-004"></a>

## DA-004 — Core operations reinterpret JSON dumps instead of consuming the typed model

**Principles:** core §1 MUST ("consumers use these definitions rather than independently
reconstruct their meaning"), FP-04, A2, DP-02, DP-08.
**Subject:** implemented.

**Diagnosis.** `core/values.py` and `core/batch.py` define the value, condition and item types.
Several operations run over `model_dump(mode="json")` and re-decide the meaning from tags and key
names:
- **Value kinds.** `canonical_value` (`keys.py:111-138`) dispatches on the `t` string. Any tag it
  does not recognize is keyed "as written" (`return dict(value)`). That covers enums today, whose
  names are therefore not normalized. A new value kind would be keyed with no normalization and no
  error.
- **Condition traversals.** There are three over the same tree, each with its own handling of
  unknown operators:
  - `canonical_condition` raises `ValueError` (`keys.py:201`), which escapes `key_claims`'s
    no-raise contract, because only `KeyingError` is caught (`keys.py:570`, `:597`, `:643`);
  - `claim_refs` ignores unknown operators;
  - `_bindings` is the third.
- **Sentence citations.** `cited_sentences` (`batch.py:324-343`) and `readdress`/`_rewrite`
  (`frame.py:70-106`) treat any dumped key named `sentence` (a string) or `anchor` (a list) as a
  citation, including keys inside raw schema qualifiers.

  A scratch probe on 2026-10-28 showed it: a qualifier `{"sentence": "life imprisonment"}` was
  reported as a cited sentence, and `readdress` refused the batch.
- **Qualifier canonical form by shape** ([DA-001](#da-001)).

**Consequence.**
- **S7 and S1, add a value kind or a condition operator.** Four places change, and no exhaustiveness
  check covers them.
- **S2, a pack qualifier named `sentence` or `anchor`.** It breaks frame handling.

**Footprint.** Known: `keys.py`, `batch.py` (`cited_sentences`), `frame.py`.

**Counterevidence.** Working over canonical JSON is what keys need in the end, and a single walk is
cheap. The defect is where the meaning is decided, not that JSON is used.

**Leads:** dispatch on the typed union (pattern matching over the models, with an exhaustiveness
check), and list citation positions from the form models.

**Related:** [DA-001](#da-001), [DA-005](#da-005).

<a id="da-005"></a>

## DA-005 — Contexts are named, but their translations are not owned as complete contracts

**Principles:** FP-04 (contexts and translations explicit), A2, DP-02, DP-05.
**Subject:** implemented (`core/candidates.py`, `core/values.py`); accepted target (S2 adapter, C1
pool, rule view).

**Diagnosis.** The design has authored, stored, keyed-candidate, consolidated, rule-view, decoding
and served contexts ([map](domain-model-map.md#contexts)). The translations between them are owned
unevenly:
- **The keyed candidate set is not a complete translation of a batch.** It is the type both rule
  call sites read. It lacks:
  - batch `alternatives` (D5 §11 keeps their members `ambiguous`; D5 §8.2 `claim.alternative_of`);
  - `unsupported` items (which D5 §5.1 turns into `core:unschematized` claims);
  - a proposal's `establishment`, `derived_from` and `rule`;
  - any rendition identity: offsets in `StoredEvidence` mean something only against a `KeyContext`
    the caller supplies.
- **It uses `None` where the batches use MISSING** (`candidates.py:25, 43, 52`). `key=None` means
  "not yet keyed", or, together with `anchor="outside"`, "awaiting resolution" ([DA-007](#da-007)).
- **Naming is mixed beyond X2-01**, the authored → stored renaming open for P0-S-1:
  - `EnumValue` is shared by both forms (`values.py:150-176`), so the stored form cannot enforce
    the prefixed enum names D1 §6 and D2 §7.1 require.
  - `KeySchema` mixes prefixed predicates and qualifiers with `symmetric_predicates` "named as
    condition trees name them" (`keys.py:280-281`).
  - The rule view names qualifiers locally (D5 §8.2), but local names are unique only within one
    schema version (D2 §7.1).

**Consequence.** **S4, a new method writes candidates**, and **S5, re-consolidation:** each consumer
needs side inputs whose shape no type owns. The batch → candidate and candidate → view translations
are where meaning gets re-derived.

**Footprint.** Known: `candidates.py`, `values.py`, `keys.py`. Suspected: the S2 adapter and the C1
pool.

**Counterevidence.** D5 §8.2 deliberately passes derived view attributes as view-builder
arguments. Whether a project may combine several packs, which decides how severe the
local-name ambiguity is, was not established.

**Leads:** one owned translation per boundary that carries the whole batch, and the MISSING
convention in every context.

**Related:** X2-01 (phase 0 plan §11), [DA-004](#da-004), [DA-006](#da-006).

<a id="da-006"></a>

## DA-006 — References carry no kind, and reference integrity has two named owners

**Principles:** DP-02, DP-03, DP-04, DP-07, CI-03.
**Subject:** implemented; accepted target (the side table).

**Diagnosis.** Every reference is a bare string; what kind of thing it names, and in which address
space, is left to the reader:
- `EntityRef.ref` is "a local ref in a batch, a key once stored" (`values.py:63-66`).
- `CandidateClaim.subject` is "an entity or statement id" (`candidates.py:54`).
- Identity slots map to a "local ref or literal" (`batch.py:180`).
- `SymbolBinding.entity` and `.claim`, and `AlternativeItem.refs`, are plain strings.

`Keys.of` resolves any id against the entity, statement and claim tables alike
(`keys.py:529-535`). A scratch probe on 2026-10-28 showed three consequences:
- A claim whose subject is a statement and whose object is a claim keys without complaint, though
  D1 §5.5 says relations between claims are links.
- When an entity-ranged identity slot is missing from `entity_identity`, the batch-local ref is
  hashed as literal text. Equal identities written as `e1` and `e7` then key apart.
- A `StoredBatch` with a dangling subject, a dangling statement and a dangling `pred` argument
  validates, as does one with only `supporting` evidence, although INV-01 asks for primary
  evidence.

`_Batch._well_formed` checks only that local ids are unique (`batch.py:270-280`).

The design names two owners for reference checking:
- D1 §10.3 places the side table in foundations, beside the keys.
- D2 §7.3–§7.4, D4 §4.3, D5 §1 and D9 P0.4 assign reference and type checks to `validate`.

**Consequence.** **S4:** candidates that reach the keyed set without passing submission validation
get no kind checking, and keying gives a key to a reference of the wrong kind. **S2:** each new pack
widens the slot-ownership hazard.

**Footprint.** Known: the models named, and `Keys.of`. Suspected: INV-01 and INV-10 have no
enforcement point in the implemented core.

**Counterevidence.**
- S4's side table caught 13 of 13 seeded reference errors (record `s4.batch-validation`).
- At finalize, ids are prefixed keys (`ent:`, `stm:`, `clm:`), so the kind is recoverable.
- Keying drops unknown references.

**Leads:** reference types by kind for each context, a resolver that checks the kind, and one named
owner for the side table.

**Related:** [DA-005](#da-005), [DA-007](#da-007).

<a id="da-007"></a>

## DA-007 — An unresolved reference is dropped rather than represented

**Principles:** CI-03, CI-04 (unknown is not absent), DP-02.
**Subject:** implemented (`core/keys.py`); accepted target (resolution in consolidation, `extref`
deferred under OPEN-D1-5).

**Diagnosis.** An `"outside"` statement (D2 §7.3, S4 V2) carries only its kind. Nothing records what
it points at, so resolution has to be rebuilt from the evidence of the claims that cite it. While it
is unresolved:
- `Keys.of` raises;
- the citing `follows_from` or `refers_to` claim is dropped (`keys.py:382-383`, `:533-534`);
- `test_outside_statements_wait_for_consolidation` asserts exactly this.

The design disagrees with itself here. D1 (OPEN-D1-5) keeps such references `unsupported` until
`extref` exists, while D2's V2 admits them as `outside` statements that consolidation "leaves
unresolved".

**Consequence.** **S6:** "what does corollary X follow from" returns nothing, and per-unit coverage
(D8) does not show that a relation was lost.

**Leads:** a typed unresolved endpoint kept on the claim, which reconciles D1 and D2 on one
treatment.

**Related:** [DA-006](#da-006), [DA-013](structure-and-invariants.md#da-013).

<a id="da-008"></a>

## DA-008 — The canonical text form erases case distinctions that identify mathematical objects

**Principles:** DP-02, DP-04.
**Subject:** implemented (`core/keys.py`).

**Diagnosis.**
- **Labels.** `normalize_label` uses `text_form`, which casefolds (`keys.py:63-66`). It is applied
  to local-entity labels (`keys.py:370`), which D5 §3.4 says are the defining expression when the
  entity has no symbol.
- **Literal identity slots** also pass through `text_form`. OPEN-D1-3 makes a parameter's canonical
  name its symbol when no role word exists.
- **Symbols** keep case through `symbol_form` (`Sigma` and `sigma` differ), so the two paths are
  inconsistent.

A scratch probe on 2026-10-28 showed both: `a + b X` and `a + b x` give one label, and `\Sigma` and
`\sigma` both become `\sigma`.

**Consequence.** **S1 and S2:** a random variable `X` and its value `x`, or a matrix `\Sigma` and a
scalar `\sigma`, can collapse into one local entity or one parameter identity. This is common
notation in statistics.

**Footprint.** Known: the two paths. How often it collides in the corpus is not measured.

**Leads:** case-preserving forms for math-bearing labels and slots; casefolding only for prose.

<a id="da-009"></a>

## DA-009 — Core contracts, the key scheme and derived forms carry no version identity

**Principles:** DP-04 (canonicalization versions and claimed equivalence), DP-01 (derived forms
identify their derivation), DP-09, DP-24, CI-13.
**Subject:** implemented; accepted target.

**Diagnosis.**
- **The schema version does not cover the authoritative core.** It hashes the pack files including
  core.yaml (D2 §2), and core.yaml is only the mirror. It does not cover:
  - the Pydantic core shapes;
  - `keys.py`'s canonicalization;
  - `tex.token_form`.
- **No contract version.** The generated `core/schemas/*.json` carry no `$id` or version, and
  `kb.observation` has no payload version (D3 §5).
- **A concrete instance.** `f1ba675` changed the stored form (local to prefixed names) and every
  key-hash input, across `batch.py`, `candidates.py`, `payloads.py` and `keys.py`. No version moved
  anywhere, and core.yaml stayed at 0.2.0.
- **Key stability.** D1 §10.2 says a key identifies the same meaning across runs, and carried
  judgments, run diffs and reference-run key reuse rely on that. D1 §10.3's stability limits list
  content edits only, not changes to how keys are derived. No key-scheme version enters a key or
  sits beside one.
- **Derived forms without their derivation.**
  - `ClaimProposalPayload` requires the derived `batch: StoredBatch`, while the authority
    (`authored` plus `citation_frame`) is optional (`payloads.py:200-221`). It records no cascade,
    compiler or schema version, although D5 §5.6 re-derives the stored form per rendition.
  - `eval.golden_item` is derived once per (pass, rendition) (D3 §7), keyed without the cascade or
    schema version.
  - Re-location rewrites a golden pass's frame in place, under the id that
    `eval.result.golden_snapshot` references.
- **Dependency drift.** Keys and digests depend on Pydantic's dump behaviour (`exclude_defaults`),
  on the `unicodedata` tables and on `regex`. By design no test pins a key value, so a change in any
  of these would go unnoticed (`tex.py`: "after freezing, a change to any output is a key
  migration").

**Consequence.**
- **S5, and any fix to a canonical form or the cascade.** Keys move between runs with nothing
  marking a scheme change, so carried judgments, cross-run diffs and reference-run reuse mismatch
  silently. Stored batches and golden items made under the old contract are read under the new one.
- **S8, a dependency or interpreter bump.** Digests and keys could move silently, which defeats
  rendition deduplication and task reuse.

No production data is stored yet, so this is a mechanism gap, not damage done.

**Counterevidence.**
- Orphaned judgments are reported, not dropped (D5 §7).
- Goldens never hold keys.
- Unicode's stability policy and Pydantic's dump semantics make silent drift unlikely.

**Leads:**
- a version for the core contracts and the key scheme that enters keys or sits beside them;
- derived artifacts keyed on the versions of their derivation;
- versioned rather than edited re-located frames;
- key-derivation changes added to D1 §10.3.

**Related:** [DA-011](#da-011), [DA-021](local-reasoning-and-assurance.md#da-021).

<a id="da-010"></a>

## DA-010 — Source profiles carry schema vocabulary outside any schema version

**Principles:** DP-05, DP-01, DP-02, DP-03, DP-24.
**Subject:** accepted target (D4 M01, D2 §12.1, D6 §7.2); `payloads.py` is implemented.

**Diagnosis.** `sources/<profile>.yaml` is "about the source's HTML, not the domain" (D4 M01).
Yet it:
- names statement-kind values (`block_hints`, `section_hints`, `details_kinds`);
- names a predicate (`synthesize: {predicate: core:proves}`);
- overrides `ci:claim_bearing` ("the source profile's explicit hint first", D6 §7.2).

M01 writes these into segment `attrs`, which are inside the content digest, and into `author_markup`
observations. Those observations' `value` is untyped `JsonValue`, and `synthesize.predicate` is only
pattern-checked (`payloads.py:96-100`). The profile table in D4 specifies no validation against the
statement kinds or the predicates. M01's reuse key includes no schema artifact, and D2 §8's
migrations rewrite only goldens and kept claims.

**Consequence.**
- **S5 and S7, rename a statement kind or `core:proves`.** Profiles, renditions and reused
  observations keep the old names, and consolidation turns them into `kb.entity.kind` values
  (D5 §3.5), a column without a CHECK.
- **S2, a second pack that extends the statement kinds over the same source.** Its profile hints are
  validated against neither pack.

**Footprint:** suspected; no profile loader exists yet.

**Leads:** validate profile vocabulary against the schema version that reads it, or move the
domain-bearing hints into the pack.

**Related:** [DA-003](#da-003), [DA-009](#da-009).

<a id="da-011"></a>

## DA-011 — Design documents restate executable contracts, and the copies have drifted

**Principles:** DP-01, DP-24; §G "generated from one source".
**Subject:** accepted target (design text).

**Diagnosis.** DESIGN.md says field-level contracts "are not repeated here", yet:
- **D2 inlines the pack files as "S4's pack file"**, and the copies already differ from the S4 files:
  - four statistics rule lines are now prefixed, and a `derive` comment changed;
  - the `MapEntry` description and a `RandomVariable` sentence changed.

  The rule changes are labelled Proposed; the `MapEntry` change is not labelled. An older third copy
  is the spike's `code/schema/core.yaml` (version 0.1.0).
- **D3 restates `vocab.py` and `payloads.py`** in its DDL and in its §6.2 payload table.
- **A concrete drift.** `core/evidence.py:31-33` reserves `attrs.parse_reason` because "D3 has no
  column for it". D3 now has a `parse_reason` column with a CHECK (D3 lines 375-376).

**Consequence.** **P0-S-1's port** must decide which copy of the pack to follow, and nothing compares
the copies. **S7:** a contract change made in code leaves the design text stale, or the reverse.

**Leads:** design text that cites executable files and their versions rather than inlining them,
or a check that the copies are equal.

**Related:** [DA-002](#da-002), [DA-020](boundaries-and-composition.md#da-020).
