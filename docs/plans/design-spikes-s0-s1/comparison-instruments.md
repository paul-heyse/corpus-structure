# Comparison instruments: plan

**Status: Complete (2026-10-28)**: the instruments executed and folded into the design; see the coordinator's status. Written as **Proposed (2026-10-28).** Part of the [S0/S1 plan series](../design-spikes-s0-s1_2026-10-28.md).
These are the throwaway tools that let S0 compare claim batches with each other and with the
trace, and that S2 and S3 will reuse to score GLiNER2 and the local LLM against the S0
reference. They live in the spike's `code/instruments/` and are not product code.

## 1. Why a separate document

S0's central measurements (agreement between two annotators at three tiers, agreement with the
trace, key stability) depend entirely on how two claim batches are aligned: which entity in A is
which entity in B, when two formulas are the same, when two condition trees are the same. A
defect in that alignment would silently corrupt every S0 number.

The design now specifies the pieces: the batch in
[D2 §7.3](../../design/D2-schema-and-guidelines.md#73-to-json-schema-for-llm-claim-proposals),
quote location in [D4 §4.3](../../design/D4-method-catalog.md#43-output-form-and-post-processing),
canonical forms and keys in [D1 §6.2 and §10](../../design/D1-knowledge-representation.md#62-canonical-form),
alignment and scores in [D7 §5](../../design/D7-evaluation-goldens-outer-loop.md#5-alignment-and-scoring).
The instruments implement those specifications as written, so S0 is also the first test of them
on real annotations; where implementing one reveals a gap or ambiguity, the instrument records
the choice it made and the S0 report proposes the design change. S2 and S3 reuse the same code,
and the phase 0 `evaluate` package can port what survives.

The instruments must not become their own oracle: §8 describes the independent checks.

## 2. Batch contract

### 2.1 Two forms of `ClaimProposalBatch`

Both forms of D2 §7.3 are modelled with Pydantic 2.14 (`BaseModel` with
`ConfigDict(extra="forbid")`, so an unexpected field is an error, not silently dropped):

| Part | Model-facing form (what annotators and LLMs write) | Stored form (what the reference holds) |
|---|---|---|
| `entities[]` | `local_ref`, `type`, `label`, `scope` ∈ {global, local}, `extent?` ∈ {statement, section} for local entities, `symbol?`, `aliases[]`, `identity{slot: value}` | adds `scope_segment` (segment key) for local entities |
| `statements[]` | `local_ref`, `kind`, `anchor`: `"unit"` or sentence ids | `anchor`: segment keys |
| `claims[]` | `local_ref`, `predicate`, `subject`, `object` (`{ref}` or a D1 §6 value), `qualifiers`, `statement?`, `statement_role?`, `evidence[]`: `{sentence, quote, role}` | `evidence[]`: `{start, end, role, coarse?}` |
| `alternatives[]` | `{refs: [claim local refs] (2 or more), reason}` | same |
| `unsupported[]` | `{local_ref, sentence, quote, reason}` | `start`, `end` instead of `sentence`, `quote` |

Values are a discriminated union on `t` (D1 §6); formula and set values carry `t`, `latex` and
`symbols` (the D1 §6.1 binding map, whose `variable`/`family_param` bindings name an entity local
ref and whose `param_of`/`param_expr_of` bindings name a claim local ref plus `param`); `sympy`
and `parse` appear in neither form. Condition trees are a discriminated union on `op` (D1 §7),
with `{"op": "claim", "ref": …}` nodes holding batch-local refs.

The spike adds an envelope around each batch, outside the D2 contract: unit id, rendition key,
pass name, annotator model and date. The envelope is what lets a batch be re-anchored.

### 2.2 Schema lookup through LinkML

Per-predicate rules (subject and object classes, allowed schema qualifiers, enum values) come
from the schema, not from code. This is the `entity_types` side table D2 §7.3 describes, which
JSON Schema cannot express:

- D2 §9's statistics schema v0 and D2 §6's core schema v0 (`core.yaml`, written out in full in
  D2 since 2026-10-28) are copied verbatim into `code/schema/statistics.yaml` and
  `code/schema/core.yaml`; any edit needed to make them load is recorded as an S4 observation.
- `linkml_runtime.utils.schemaview.SchemaView` loads it; the lookup uses `all_classes()`,
  `class_ancestors()` (so a mixin domain such as `Distributed` admits its classes),
  `induced_slot()`, enum permissible values and the `ci:` annotations (`ci:role`, `ci:object`,
  `ci:qualifiers`, `ci:scope`).
- This is a lookup only. Compiling the schema is S4's question; whether v0 loads cleanly and
  whether list-valued annotations survive (OPEN-D2-6) are recorded as byproduct observations for
  S4. If v0 does not load, the lookup reads the YAML directly and the failure is reported.

### 2.3 Validation results

Validation follows D4 §4.3 step 3 and D1 §11 and never stops at the first error. Each item is
reported in one category:

| Category | Examples |
|---|---|
| Malformed | Pydantic `ValidationError` entries (stable error `type` and location) |
| Unknown schema element (INV-03) | Predicate, class, qualifier or enum value not in v0 |
| Type mismatch | Subject or object class outside the predicate's domain or range (via `class_ancestors`) |
| Reference error | Local ref that does not resolve; a binding that names the wrong kind of ref; a condition `claim` node pointing outside the batch (INV-08); a reference cycle among conditions (D5 §5.2) |
| Invariant | INV-01 (stated claim without primary evidence), INV-02, INV-05 (local entity without extent or scope segment, global with one), INV-06 (supposed claim neither referenced nor scoped), INV-09 (claims with `phrase`/`unsupported` condition leaves marked conditional), INV-10 (located spans inside the canonical text and equal to it) |

A test file holds deliberately invalid batches, one per category, that must each be reported in
that category.

## 3. Quote locator and stored-form conversion

`code/s0_locate.py` (the name the S0 brief uses) converts a model-facing batch into the stored
form. It implements D4 §4.3 step 2 for each evidence item, unsupported item and statement
anchor:

1. exact match within the cited sentence;
2. exact match within the unit;
3. exact up to spacing: a `regex` pattern of the quote's non-space characters joined by
   `(?:\s|\\[,;!])*`, matched in canonical text itself (no offset map), cited sentence then unit;
   then the same after expanding the rendition's argument-free macros on both sides;
4. fuzzy: `rapidfuzz.fuzz.partial_ratio_alignment` (cutoff 85, trailing `.,;:` stripped) within
   the cited sentence, refined inside its window (widened by 30% of the quote) by `regex`
   `BESTMATCH` `(?b)(?:quote){e<=⌈0.15·len⌉}` with a 0.2 s timeout, the rapidfuzz window kept
   when the refinement fails.

Every located span, at every tier, is snapped outward to word boundaries. Every result records
the tier and step that located it, the number of exact matches when more than one exists
(ambiguity), and, for tier 4, the score and the edit counts. The cascade is ADR-0009's
(revisit I-R1, 2026-10-28), measured on 499 quotes under seeded errors in `code/regex_probe.py`;
it replaced a tier 3 with an offset map and a tier 4 with a fixed-width window, which cut words
when a quote's length differed from the source span. An unlocated quote falls back to its cited sentence's span with
`coarse: true` (D5 §5.6); without a cited sentence the item is reported as malformed. Local
entities' `extent` is resolved to a `scope_segment`: `statement` → the anchor segment of the
statement that binds it; `section` → the enclosing section segment from S1's adopted synthesis.

**Re-anchoring.** Given a stored batch on rendition R and a new rendition R′, the locator
re-derives quotes from R and locates them in R′; items that fail are listed. This keeps the S0
reference usable if S1 changes a rendering convention after annotation.

**Tests.** Planted cases with hand-written expected spans: quotes from the trace for T1–T4 against
S1's canonical text; a quote spanning an `a.ref` gap under each rendering convention; quotes
across `<q>` marks and across a list marker; a quote with `$…$` and re-spaced LaTeX; a quote that
occurs twice in a unit; a long quote with one typo (tier 4).

## 4. Value equivalence

Two values are compared in tiers, and the deciding tier is recorded per comparison (this tally
is evidence for OPEN-D7-2, which S5 decides):

All three automatic tiers read formulas through one math grammar (`code/mathgrammar/`,
ADR-0009, revisit I-R1): SymPy's Lark LaTeX grammar extended by directives, typed by the slot's
range, with ambiguity resolved only from declared context. It replaced a string-rewrite shim
whose defects were review findings F2, F3 and F5a.

1. **Canonical form, D1 §6.2.** Formulas and sets by normalized LaTeX, written from the parse tree: source macros expanded
   from the page's macro table (S1 `renditions.json`), then D2 §12.1's fallback macro map; spacing commands, `\left`, `\right` and
   whitespace removed; braces around single tokens dropped (`b^{2}` → `b^2`). Numbers as
   normalized decimals with pint base units; text NFC-casefolded with collapsed whitespace. The
   same function produces the keys of §6, so key agreement and canonical-form equality cannot
   diverge.
2. **SymPy, D7 §5.3.** The grammar's tree converted by a subclass of SymPy's Lark transformer
   (SymPy 1.14); equal when `sympy.simplify(a - b) == 0` within a time limit; sets
   compared as SymPy sets (`\R`, `(0, \infty)`, `\R \setminus \{0\}`). Parse failures are
   recorded with their LaTeX for S5.
3. **Numeric fallback, D7 §5.3.** When simplification times out or is inconclusive: evaluation
   at random points satisfying the claims' `member` and `cmp` conditions (rejection sampling
   over reals; fixed seed), equal when all points agree within 1e-9 relative. Numbers: equal
   after unit conversion within 1e-9 relative.
4. **Manual.** Remaining pairs go to `results/s0/manual_equivalence.tsv` with the root's decision
   and reason.

## 5. Alignment and agreement (D7 §5)

### 5.1 Entities

Per unit, entities align one-to-one by maximizing summed similarity with
`scipy.optimize.linear_sum_assignment` (D7 §5.2):

- type must be equal (a cross-type pair gets a prohibitive cost and is reported unmatched);
- local entities: normalized symbol and the same scope segment;
- global entities: canonical label or alias equality after D1 §6.2 text normalization, with
  `rapidfuzz.fuzz.token_sort_ratio` on labels as a graded similarity for near-matches;
  `token_set_ratio` is not used because it scores a label contained in a longer one as identical
  ("normal distribution" against "standard normal distribution");
- `FamilyParameter`: the identity attributes (family, canonical name);
- overlapping evidence as tie-breaker.

The similarity weights and the unmatched threshold are implementation choices D7 leaves open;
they are recorded, and §8's hand alignment checks them.

### 5.2 Claims

With the entity mapping applied, claims are matched one-to-one per unit and tier, maximizing the
number of matches (D7 §5.3):

| Tier | Two claims match when |
|---|---|
| core | Same predicate; subjects aligned; objects aligned (entities) or equivalent (values, §4) |
| full | core, plus equal modality and polarity, equal statement role, equivalent identity qualifiers (`param_values` key by key), and equivalent conditions |
| evidence | full, plus the primary evidence overlaps a primary span of the other or lies in the same sentence |

Condition equivalence: both trees canonicalized (D5 §5.2: nested `and`/`or` flattened,
arguments sorted by canonical JSON), leaves matched one-to-one: values by §4, `claim` leaves by
the alignment of the referenced claims, `phrase` leaves by span overlap. (z3 equivalence, which
D7 allows once M20 exists, is not used here.) Alternative groups match when the other side has a
group over the same readings, or any one reading (`ambiguity_collapsed`). `unsupported` items
match by evidence-span overlap.

### 5.3 Scores and agreement outputs

Per unit and predicate: counts in each batch, matches at each tier, unmatched on each side
(`agreement.tsv`). For two annotator passes the comparison is run with A as reference and B as
prediction, then symmetrized (D7 §3.3); against the trace or the reference it is one-directional
(precision, recall, F1 per tier, D7 §5.4). Also reported, as D7 §5.4 defines them: binding
accuracy over aligned formula values, scope accuracy over aligned local entities, unsupported
recall. Each score has a 95% interval from 1,000 bootstrap resamples over units (D7 §5.4),
reported with n; with twelve units these intervals are wide and are said to be.

A per-field breakdown attributes full-tier failures (modality, polarity, statement role,
conditions, `param_values` keys and values, bindings, extent). For categorical fields on aligned
claims, Cohen's kappa via `statsmodels.stats.inter_rater.cohens_kappa`, reported with n as a
secondary statistic.

## 6. Keys

For each batch, claim keys and meaning keys are computed as D1 §10.1 and D5 §5.2 specify: local
entity keys from type, scope segment key and normalized symbol; global entity keys from type,
identity attributes and normalized label (the batch's label stands in for consolidation's
choice); claim keys over subject key, predicate, object key or canonical value (§4 tier 1), and
identity qualifiers (modality, polarity, statement, canonical conditions, schema identity
qualifiers), in topological order of condition references. The meaning key drops `statement`.

Reported: for aligned pairs, the share whose claim keys coincide and the share whose meaning keys
coincide, with the cause of each mismatch (label, scope segment, canonical LaTeX, conditions).
D5 §5.3 fuses candidates by key and by SymPy-proven formula equivalence; the gap between key
agreement and core-tier agreement shows how much fusion depends on the SymPy step, and supplies
evidence for OPEN-D3-4.

## 7. Contract for S2–S7

S2–S7 score with the instrument revision **I-R2** (coordinator row 24), frozen and named in each
record's `inputs`, against the **v1 reference** (`results/s0r2/reference_v1/`, with the held-out
units' adjudicated batches in `results/s0r2/adjudication_v1/`); the v0 reference
(`results/s0/reference/`) is reported beside it only where a brief asks (coordinator §3.5):

- S2 (GLiNER2) produces mentions and relations, not full claims. Its scoring needs a mention-level
  alignment (span overlap and type against the reference's entity evidence) and reports which
  reference claims have a matching relation at the core tier; that alignment is revision I-R3.
- S3 (local LLM) produces model-facing batches; they pass through the validator, the locator and
  all three tiers exactly as S0's and S0-R2's passes do, with and without the contested items of
  `results/s0r2/contested.tsv` (package C1).
- S5 uses the value tiers (§4) and the key functions (§6) of I-R2; S6 uses the keys; S7 uses the
  entity alignment for its linking cases.

A spike that needs an instrument change makes it as a new revision package in the coordinator,
never by editing a frozen revision in place. Once the phase 0 build ports alignment and scoring
into `evaluate/`, that module is their product home; the spikes keep scoring against their frozen
revision (single home after a port).

| Revision | Changes | Package |
|---|---|---|
| I-R1 | the math grammar, slot-type validation, value tiers on the grammar, the quote cascade | done (2026-10-28) |
| I-R2 | ADR-0012 token-form keys in `mathgrammar` and `instruments/values` (sizing commands dropped by the shared list); reruns of S0-G and S0-R2 figures with superseding records | coordinator row 24 |
| I-R3 | Mention-level alignment (span overlap and type against the reference's entity evidence, one-to-one; contested items neutral) for S2 and S7 | coordinator row 24b |

## 8. Packages

| Package | Scope | Outputs | Done when |
|---|---|---|---|
| I-A | Pydantic batch models (both forms), schema files and `SchemaView` lookup, validator, invalid-batch tests, locator and stored-form conversion with planted tests | `code/instruments/{batch,schema_lookup,validate}.py`, `code/s0_locate.py`, `code/schema/`, `results/s0/instruments_tests.md` | Every invalid batch reported in its category; every planted quote located at its expected span or reported as expected-unlocated |
| I-B | Value equivalence, aligner, scores, keys; verification (§9) | `code/instruments/{values,align,scores,keys}.py`, `results/s0/aligner_verification.md` | §9 checks pass, or each failure is fixed or reported with its effect on S0 numbers |
| I-R1 | Revisit (ADR-0009): the math grammar module, slot-type validation, value tiers on the grammar, the quote cascade of §3, a symbol-occurrence API for M13 | `code/mathgrammar/`, `results/mathgrammar/`, revised `code/instruments/`, `code/s0_locate.py`, tests | Existing suites pass; F2/F3/F5a pass on the grammar; the cascade reproduces the probe's figures; grammar coverage recorded by kind with failure categories |

I-A needs S1-A's canonical text for its locator tests; I-B is built and verified on T1–T4 trace
data before S0's passes exist.

## 9. Verification that does not reuse the instrument as its own oracle

- **Hand alignment.** Before running the aligner on T1–T4, the root writes the trace's tables as
  stored batches and aligns one pass to them by hand (which entity is which, which claim is
  which, and the tier at which each pair agrees). The aligner's output is compared with that
  hand alignment; differences are investigated before any S0 number is reported.
- **Perturbations.** Each trace batch is perturbed in known ways and compared with its original:
  swap the "respectively" pairing in T2; drop the `claim` condition from T3's conclusion; replace
  `\lvert b \rvert \sigma` with `b \sigma`; change T3's premise modality from `supposed` to
  `asserted`; rename a local symbol; reorder `and` arguments; rewrite a formula equivalently
  (`b^2 \sigma^2` versus `\sigma^2 b^{2}`). Each perturbation has an expected outcome (which tier
  fails, or none for the equivalent rewrites).
- **Validator tests** use deliberately invalid batches, kept in the folder (§2.3).
- **Equivalence spot-check.** A sample of the SymPy and numeric tiers' "equal" decisions is
  re-checked by hand and reported.
