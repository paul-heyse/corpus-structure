# D1 · Knowledge representation

**Proposed (2026-10-28).** This document defines what the pipeline produces, independent of
storage ([D3](D3-database.md)) and of the methods that produce it ([D4](D4-method-catalog.md)).
Every other document refers to the types defined here. The [worked trace](trace.md) shows each
type on real Siegrist text.

## 1. Scope and design goals

The representation must:

1. hold any domain's knowledge without new tables or code per domain (statistics now, business
   documents and email later);
2. keep every fact traceable to exact source text;
3. keep separate what the source **states**, what a method **proposes**, what the pipeline
   **believes**, and what was **derived** or **decided** by an agent;
4. represent n-ary, conditional and hypothetical statements (theorems, definitions, exceptions)
   without flattening them;
5. make evaluation a structural diff between two claim sets (goldens versus a run).

The model has six planes. The first five are the knowledge; the sixth is how it was produced.

| Plane | Types | Owner of writes |
|---|---|---|
| Schema | Classes, predicates, qualifier specs, enums, rules ([D2](D2-schema-and-guidelines.md)) | Schema loader |
| Evidence | `Document`, `Rendition`, `Segment`, `Span` | Ingest methods |
| Entities | `Entity` (including `Statement`), aliases | Consolidation only |
| Claims | `Claim`, `ClaimEvidence`, `ClaimLink` | Consolidation only |
| Derived models | Derived claims, verifier results | Validation and verifiers, through consolidation |
| Provenance | `Observation`, plus the operations records of [D3](D3-database.md) | Any method, append-only |

## 2. Observations versus claims

The central rule: **methods write observations; only consolidation writes entities and claims.**

- An **observation** is one method's output on one unit: a mention, a relation, a record, a
  classification, a normalized value, a link candidate, a claim proposal, or a judgment. It
  carries the method configuration and task that produced it, a score, and an outcome. It is
  never edited or deleted.
- A **claim** is the pipeline's consolidated belief that the source states something, with the
  observations that support it, the evidence spans, a status and a confidence.

Opus and human interventions are observations too (with `kind = judgment` or
`kind = claim_proposal` and a method of family `agent` or `human`). They influence claims only
through consolidation ([D5](D5-consolidation-identity-confidence.md)), which applies documented
precedence. This one rule replaces the old system's separate nomination, admission and
acceptance machinery.

## 3. Evidence

### 3.1 Document, rendition and canonical text

A `Document` is one retained original (an HTML page, a PDF, an email message). Its identity is
`(project, source_uri, content_hash)` where `content_hash` is the SHA-256 of the original bytes.

Each document has a **canonical text**: a deterministic, reading-order linearization produced
by its ingest adapter. All offsets in the system are character offsets (Unicode code points) into
a canonical text. Rules for the canonical text:

- Block elements are separated by `\n\n`; list items by `\n`; table cells by `\t` and rows by
  `\n`.
- Inline math keeps its LaTeX source between its original delimiters, e.g. `\(a \in \R\)`.
  Display math keeps `\[ … \]`. Nothing inside math is rewritten.
- HTML entities are decoded; whitespace inside a block collapses to one space; the result is
  NFC-normalized.
- Text that is not content (navigation, scripts, app widgets, footer) is excluded by the
  adapter's declared rules ([D4 M01](D4-method-catalog.md#m01-ingesthtml)).

The canonical text is versioned by the adapter configuration. Each (document, adapter
configuration) pair is a **rendition**; segments and spans belong to a rendition, and a run
selects one rendition per document. Changing the adapter produces new renditions beside the old
ones instead of rewriting them.

### 3.2 Segments

A `Segment` is a contiguous range `[start, end)` of a rendition's canonical text with a kind and
a parent. Segments form a tree rooted at the document segment. Kinds:

| Kind | Meaning | Siegrist source |
|---|---|---|
| `document` | Whole canonical text | page |
| `section` | Headed section | `<h3>`, `<h4>`: each heading opens a section, nested by level, up to the next heading of the same or higher level (Siegrist has no wrapper elements) |
| `unit` | An author-delimited numbered unit | `<div class="unit">`, usually with an `id` |
| `paragraph` | Block of prose | `<p>` |
| `list`, `list_item` | Lists | `<ol>`, `<ul>`, `<li>` |
| `details` | Collapsible proof or solution | `<details>` |
| `math_display` | Display formula | `\[ … \]` |
| `math_inline` | Inline formula | `\( … \)` |
| `heading` | Heading text | `<h1>`–`<h6>` |
| `table`, `table_row`, `table_cell`, `caption`, `footnote` | Tables and notes | as named |
| `sentence` | Sentence, from segmentation | spaCy |
| `email_message`, `quoted_block`, `signature` | Email structure (later) | — |

Segment attributes (`attrs`) hold author markup verbatim: element id, CSS classes, `<dfn>`
terms with their offsets, link targets. Author markup is an **input**: the adapter also emits it
as `author_markup` observations so that methods can use it ([D4 M01](D4-method-catalog.md#m01-ingesthtml)).
Evaluation does not use author markup as a gold for anything the pipeline consumes it for
([D7 §6](D7-evaluation-goldens-outer-loop.md#6-independent-witnesses)).

A segment also carries `parse_status`: `ok`, `partial` (some content dropped, with reason) or
`failed`. A failed segment is retained so that its absence of claims is explained, not silent.

### 3.3 Spans

A `Span` is `(rendition, start, end)` with its text. It is the only anchor type: every citation
of evidence resolves to one or more spans. A span records the smallest segment that contains it.
Spans are deduplicated by `(rendition, start, end)` and upserted by the repository layer for
any writer (ingest, methods, consolidation), so citing an offset never requires owning span rows.

## 4. Entities

### 4.1 Definition

An `Entity` is a resolved identity of an instance of a schema class. It has:

| Field | Meaning |
|---|---|
| `type` | Schema class name, e.g. `DistributionFamily`, `RandomVariable`, `Statement` |
| `label` | Canonical display label (chosen by consolidation, [D5 §3](D5-consolidation-identity-confidence.md#3-entity-resolution)) |
| `aliases` | Every surface form observed, each with kind `label`, `symbol`, `abbreviation`, `term` or `expression` |
| `scope` | `global`, or `local` with a scope segment |
| `key` | Deterministic identity key (§10) |
| `attrs` | Identity attributes declared by the schema (`ci:identity_keys`); never facts |

**All facts about an entity are claims.** `attrs` holds only what the schema declares as part
of identity, such as the family and canonical name of a `FamilyParameter`. A property like "the
mean of the gamma distribution is kb" is a claim, not an attribute.

### 4.2 Global and local entities

- A **global** entity denotes something that is the same wherever it is mentioned: a
  distribution family, a concept such as "location-scale family", an organization.
- A **local** entity exists only within a scope segment: the random variable `X` of one theorem,
  the symbol `a` of one definition. Two mentions of `X` in different theorems are different
  entities. Siegrist often binds a variable at section level ("Suppose again that `X` has the
  normal distribution…"); the scope segment is then the section. Scope assignment is the job of
  the symbol-scoping method ([D4 M13](D4-method-catalog.md#m13-resolvesymbol_scope)).

The schema declares each class's scope (`ci:scope`, [D2 §3](D2-schema-and-guidelines.md#3-the-ci-annotation-vocabulary)).

### 4.3 Statements

`Statement` is a core class present in every domain. A statement is an authored unit of meaning:
a definition, theorem, proposition, proof, example, exercise, remark, convention, assumption,
or (later) a contract clause, a policy, an email request. It is a local entity anchored to one or
more segments, with a `kind` from the `StatementKind` enum (core values, extendable by domains):

`definition`, `theorem`, `proposition`, `lemma`, `corollary`, `proof`, `example`, `exercise`,
`solution`, `remark`, `convention`, `notation`, `assumption`, `narrative`.

Statements give claims a home. A theorem is a statement whose claims are premises and
conclusions; a proof is a statement linked to the statement it proves; a definition is a
statement that defines an entity. Statement grouping is what lets a consumer reconstruct "the
affine transformation theorem, its premise, its conditions, its conclusion and its proof" from
claims.

## 5. Claims

### 5.1 Structure

A claim is a statement-level assertion with one subject, one predicate and one object, plus
qualifiers:

```text
Claim
  key            deterministic identity (§10)
  subject        Entity
  predicate      schema predicate, e.g. stat:has_distribution
  object         Entity | Value (exactly one)
  qualifiers     map of qualifier name → value (§5.2, §5.3)
  statement      Statement entity | null
  statement_role premise | conclusion | definiens | restriction | example_value | null
  status         §8
  establishment  stated | derived | agent_asserted
  confidence     probability in [0, 1] (D5 §6)
  evidence       list of (Span, role)       role ∈ primary, supporting, condition, definition
  supports       list of Observation        the observations it was consolidated from
```

The design follows Wikidata's statement model (main value, qualifiers, references, rank), which
has held up across open domains. Our `evidence` corresponds to its references and our `status`
to its rank.

### 5.2 Core qualifiers

Every claim may carry these, whatever the domain:

| Qualifier | Values | Meaning |
|---|---|---|
| `modality` | `asserted` (default), `supposed`, `defined`, `conventional`, `exemplified`, `posed`, `cited` | How the source puts the claim forward; see below |
| `polarity` | `positive` (default), `negative` | "X is not normal" is a negative claim, not an absent one |
| `hedge` | null or a `phrase` value | "typically", "approximately" |
| `attribution` | null (the document's author) or an entity | Who says it, when not the author |
| `conditions` | a condition tree (§7) or null | Under what conditions the claim holds |
| `scope` | null or `{segment, extent}`, extent ∈ `statement`, `section`, `document` | Where a supposition applies when broader than its statement |
| `valid_time` | null or an interval value | When the fact is true in the world (business domains) |

Modalities:

| Modality | Use | Example |
|---|---|---|
| `asserted` | The author states it as true | The conclusion of a theorem |
| `supposed` | Assumed within a statement or scope; not asserted beyond it | "Suppose that X is normally distributed…" |
| `defined` | A stipulation that makes something true by definition | "Then X = e^Y has the lognormal distribution" in a definition |
| `conventional` | An author convention, explicitly optional | "it's convenient to consider a constant as having a normal distribution" |
| `exemplified` | Values given in an example or exercise setup | "The radius of the rod is normally distributed with mean 1 cm" |
| `posed` | A quantity or question an exercise asks for | "Find the probability that…" |
| `cited` | Reported from another source | "Smith (1990) showed…" |

`supposed` is what keeps hypothetical premises from becoming facts: a query for "what is
normally distributed" returns nothing from a premise unless it asks for suppositions.

### 5.3 Schema-defined qualifiers

A predicate may declare additional qualifiers in the schema ([D2 §4](D2-schema-and-guidelines.md#4-predicates-and-qualifiers)).
The statistics pack declares, for example, `param_values` on `has_distribution`: a map from
family-parameter canonical names to formula values. Schema qualifiers are how n-ary facts with
one primary subject and value stay a single claim.

### 5.4 When to reify instead

A fact becomes a separate entity with role claims (reification) only when one of these holds:

1. it has two or more participants of equal standing and no natural primary subject (a contract
   between two parties; a meeting);
2. other claims must refer to it as a thing (an event that has its own time, location and
   participants);
3. it recurs as the same identity across sources and should be counted once.

Otherwise it is one claim with qualifiers. Theorems, definitions and proofs are reified as
`Statement` entities by rule 2. The schema declares reified classes with `ci:reify`.

### 5.5 Claim links

Relations between claims are typed links, not claims:

| Link | Meaning |
|---|---|
| `derived_from` | A derived claim and the claims it was computed from |
| `contradicts` | Two claims that cannot both hold under their conditions |
| `equivalent_to` | Two claims with the same meaning from different evidence (different sources or statements) |
| `alternative_of` | Competing readings of the same evidence (faithful ambiguity) |
| `refines` | A more specific claim and the general one it refines |

Relations between statements (a proof proves a theorem; a corollary follows from a theorem) are
ordinary claims with `Statement` subjects and objects, using core predicates `proves`,
`follows_from` and `refers_to`.

## 6. Values

A value is a tagged JSON object. Every value has `t` (type). Value types:

| `t` | Fields | Example |
|---|---|---|
| `text` | `v` | `{"t":"text","v":"location-scale family"}` |
| `number` | `v` (decimal string), `unit` (pint unit string or null) | `{"t":"number","v":"0.002","unit":"cm"}` |
| `bool` | `v` | `{"t":"bool","v":true}` |
| `enum` | `enum`, `v` | `{"t":"enum","enum":"ParameterRole","v":"scale"}` |
| `entity` | `ref` (entity key) | used inside qualifiers and condition trees |
| `formula` | `latex`, `sympy`, `parse`, `symbols` | below |
| `set` | `latex`, `sympy`, `parse`, `symbols` | `ℝ`, `(0, ∞)`, `ℝ ∖ {0}` |
| `date` | `v` (ISO 8601) | business domains |
| `interval` | `start`, `end`, `start_incl`, `end_incl` (values or null for unbounded) | valid time |
| `phrase` | `span`, `text` | text kept but not interpreted |

### 6.1 Formulas and symbol bindings

A formula value keeps the source LaTeX exactly (`latex`), a normalized SymPy form when the
expression parses (`sympy`, as `srepr`), the parse outcome (`ok`, `partial`, `failed`), and a
**symbol binding map**:

```json
{
  "t": "formula",
  "latex": "a + b \\mu",
  "sympy": "Add(Symbol('a'), Mul(Symbol('b'), Symbol('mu')))",
  "parse": "ok",
  "symbols": {
    "a":  {"bind": "free"},
    "b":  {"bind": "free"},
    "mu": {"bind": "param_of", "claim": "clm:…premise", "param": "mean"}
  }
}
```

Binding kinds:

| `bind` | Meaning |
|---|---|
| `variable` | The symbol denotes a local entity (`"entity": key`), e.g. a random variable |
| `param_of` | The symbol is the value given to parameter `param` in the referenced `has_distribution` claim |
| `param_expr_of` | The symbol occurs inside the value given to `param` (σ in a variance of σ²) |
| `family_param` | The symbol denotes a family parameter entity (`"entity": key`) |
| `free` | A symbol introduced by this statement, restricted by its conditions |
| `constant` | A mathematical constant (e, π) |
| `unresolved` | Not bound; a resolution gap counted by D6 metrics |

Symbol bindings are the general form of what the old system called a governing input
association: which source-backed symbol supplies which parameter, under which premise. Unresolved
bindings never block a claim; they lower its completeness and are measured.

### 6.2 Canonical form

For keys and comparisons, a value has a canonical form: formulas and sets by **normalized
LaTeX** (source macros expanded by the domain's macro map; spacing commands `\,`, `\;`, `\!`,
`\left`, `\right` and whitespace removed; braces around single tokens dropped, so `b^{2}` is
`b^2`). The SymPy form is never part of a key, so adding or upgrading the parser never changes
keys; consolidation fuses candidates whose formulas SymPy proves equivalent ([D5 §5.3](D5-consolidation-identity-confidence.md#53-fusion)); numbers as normalized decimal strings with pint base units; text NFC-casefolded with
collapsed whitespace. Formula equivalence for evaluation uses SymPy simplification
([D7 §5](D7-evaluation-goldens-outer-loop.md#5-alignment-and-scoring)), not canonical form.

Canonical form is written from the parse tree of the one math grammar (D4 M11), not by string
rewriting: macros expand by whole command name (`\P` never matches inside `\Phi`), and a value
that does not parse keeps its verbatim LaTeX, whitespace-collapsed, with `parse: partial` or
`failed`. A value must parse under its slot's declared range (formula, set, relation, membership);
a mismatch is a validation issue, not a silent coercion.

> Decision: [ADR-0009](../adr/0009-math-grammar-authority.md)
> Status: **Tested** in the spike instruments (2026-10-28): 86 of 86 S0 values read, canonical forms decided all but a handful of value comparisons ([s0.instruments](../design_review/evidence/2026-10-28_design-spikes/records/s0.instruments.json)); production code not written

## 7. Conditions

A condition is a JSON tree. It states under what circumstances a claim holds. Every node
names its type in the key `op` (`{"op": "member", "x": …, "set": …}`); the other fields are
as listed. Inside a ClaimProposalBatch, `claim` nodes carry the batch's local refs; consolidation
replaces them with claim keys.

| Node | Fields | Meaning |
|---|---|---|
| `and`, `or` | `args` (list) | Conjunction, disjunction |
| `not` | `arg` | Negation |
| `claim` | `ref` (claim key) | The referenced claim holds (a premise) |
| `member` | `x` (formula), `set` (set) | `a ∈ ℝ` |
| `cmp` | `rel` (`<`, `<=`, `=`, `!=`, `>`, `>=`), `lhs`, `rhs` (formulas) | `t < 1` |
| `pred` | `name` (schema condition predicate), `args` (entities or formulas) | `independent(X_1, X_2)` |
| `forall` | `var`, `set`, `body` | Indexed families: for `i ∈ {1, 2}` … |
| `phrase` | `span`, `text` | Anchored condition text not interpreted |
| `unsupported` | `span`, `text`, `reason` | A condition the language cannot state |

Rules:

- A theorem's conclusion lists its premises as `claim` nodes and its restrictions as `member`,
  `cmp` or `pred` nodes in one `and`.
- A condition shared by several conclusions (one "Suppose X₁ and X₂ are independent" governing a
  list of results) is repeated in each conclusion's tree; the shared premise claim is one claim,
  referenced by key from each.
- `phrase` and `unsupported` keep the condition visible to consumers. A claim whose condition
  tree contains either is never presented as unconditionally true.
- Condition predicates (`independent`, `identically_distributed`, …) are declared by the domain
  schema ([D2 §5](D2-schema-and-guidelines.md#5-condition-predicates)).
- Trees translate to z3 for consistency and implication checks when every leaf is `member`,
  `cmp` over parsed formulas, or a `pred` the domain maps to z3 ([D5 §8](D5-consolidation-identity-confidence.md#8-validation)).

## 8. Statuses and non-positive states

### 8.1 Claim status

| Status | Meaning | Set by |
|---|---|---|
| `candidate` | Consolidated; confidence or validation not yet sufficient | Consolidation |
| `accepted` | Confidence at or above the type's threshold and validation passed | Consolidation |
| `rejected` | Adjudicated false, or a hard validation failure | Consolidation, applying judgments |
| `ambiguous` | Member of an `alternative_of` group not yet resolved | Consolidation |
| `conflicting` | Linked by `contradicts` to an accepted claim; both kept | Validation |
| `unsupported` | The source states something the schema cannot represent; predicate `core:unschematized`, object a `phrase` | Consolidation |

### 8.2 Establishment

| Value | Meaning |
|---|---|
| `stated` | The source states it; it has primary evidence |
| `derived` | Computed from stated claims by a declared rule or verifier; has `derived_from` links |
| `agent_asserted` | Asserted by an agent without a span. Allowed only for schema-level knowledge proposals, never for corpus claims; consolidation refuses it for claims |

Acceptance never changes establishment: an accepted derived claim stays derived.

### 8.3 Where each non-positive state lives

| State | Representation |
|---|---|
| Input unavailable | `Segment.parse_status = failed` or a `failed` ingest task |
| Selected but empty | Task outcome `empty` (the method ran and found nothing) |
| Faithful ambiguity | Claims with status `ambiguous` linked by `alternative_of` |
| Unsupported representation | Claim status `unsupported`; condition leaves `unsupported` |
| Failed recovery | Task outcome `failed`, with error |
| Unreviewed | No golden alignment and no judgment; reported by evaluation coverage ([D7](D7-evaluation-goldens-outer-loop.md)) |
| Unresolved symbol | Formula symbol binding `unresolved` |

## 9. Observations

An observation has: `task` (which records method configuration and run), `kind`, optional
`span` and `segment`, a JSON `payload`, a `score`, and an `outcome` (`produced`, `empty`,
`failed`). Kinds:

| Kind | Payload (summary; JSON Schemas in [D3 §6](D3-database.md#6-jsonb-contracts)) | Typical producers |
|---|---|---|
| `author_markup` | markup type (`dfn`, `unit`, `link`, `details`), attributes | M01 |
| `mention` | `label` (schema class or term category), `text`, attributes | M06, M08, M09 |
| `relation` | `label` (predicate), head and tail mention refs or spans | M07, M08 |
| `record` | `structure` name, fields → spans or values | M06 |
| `attribute` | mention ref, attribute group, value, score | M06 |
| `classification` | target (segment), task name, label(s) | M05, M22 |
| `value` | span, normalized value (§6) | M11, M12 |
| `scope` | mention ref, scope segment, binding | M13 |
| `link` | mention ref, candidate entity key or new-entity proposal, score | M14, M15 |
| `claim_proposal` | a full claim in D1 form with local entity references | M10, agent |
| `judgment` | target (observation, claim key, alternative group or identity group), decision, rationale | M16, agent, human |
| `verification` | claim key, verifier, verdict (`consistent`, `refuted`, `not_checkable`), detail | M21 |

## 10. Identity and keys

### 10.1 Hashing

`key = <prefix> + ":" + hex(sha256(canonical_json(parts)))[:32]`, where `canonical_json` sorts
keys, uses no insignificant whitespace, encodes UTF-8 and NFC-normalizes strings.

| Object | Prefix | Parts |
|---|---|---|
| Document | `doc` | project, source_uri, content_hash |
| Rendition | `ren` | document key, adapter config hash |
| Segment | `seg` | rendition key, kind, start, end |
| Span | — | natural key `(rendition, start, end)` |
| Global entity | `ent` | type, identity attributes, normalized canonical label |
| Local entity | `ent` | type, scope segment key, normalized symbol or label |
| Statement | `stm` | anchor segment keys (sorted) |
| Claim | `clm` | subject key, predicate, object key or canonical value, identity qualifiers |
| Method config | `cfg` | method name, method version, canonical params |

A key is computed when an entity is first created. A global entity that consolidation links
to an entity of the reference run keeps that entity's key and canonical label
([D5 §3.3](D5-consolidation-identity-confidence.md#33-global-entities)), so keys are stable
across runs. A statement's `kind` and label are attributes, not identity.

**Identity qualifiers** are those that change meaning: `modality`, `polarity`, `statement`,
canonical `conditions`, and every schema qualifier the schema lists in `ci:identity_qualifiers`
(for example `param_values`). Evidence, confidence, hedge text and attribution phrasing are not
part of the key.

### 10.2 Run scoping

Entities, claims and claim links are **materialized per run** and immutable once the run
finishes. A key identifies the same meaning across runs, which is how runs are compared,
judgments carried forward and claims diffed. Observations belong to tasks; a task reused from
cache in a later run contributes its existing observations, so unchanged work is never repeated
([D6 §4](D6-orchestration-metrics-policies.md#4-caching-and-reuse)).

The project records one **promoted run**. "Current knowledge" means the promoted run's claims.

### 10.3 Stability limits

Keys of global entities depend on the canonical label consolidation selects; a resolution change
that merges two entities changes a key. Goldens therefore never reference run keys: they carry
their own local references and are aligned structurally ([D7 §5](D7-evaluation-goldens-outer-loop.md#5-alignment-and-scoring)).
Judgments target observations or claim keys; a judgment whose target key no longer exists in a
run is reported as orphaned, never silently dropped ([D5 §7](D5-consolidation-identity-confidence.md#7-applying-judgments)).

## 11. Invariants

| ID | Invariant |
|---|---|
| INV-01 | Every `stated` claim has at least one evidence span with role `primary` |
| INV-02 | A claim's object is exactly one of an entity or a value |
| INV-03 | Every predicate, class, enum value and schema qualifier used exists in the run's schema version |
| INV-04 | Only consolidation writes entities, claims and claim links; observations are append-only |
| INV-05 | A local entity has a scope segment; a global entity has none |
| INV-06 | A `supposed` claim is referenced by at least one condition or has a `scope` qualifier |
| INV-07 | `derived` claims have at least one `derived_from` link; `agent_asserted` claims never appear in a corpus run |
| INV-08 | Condition trees reference only claims in the same run |
| INV-09 | A claim with a `phrase` or `unsupported` condition leaf is not reported as unconditional |
| INV-10 | Spans lie within their rendition's canonical text and their text equals the substring |

## 12. Worked example in brief

From [trace unit T3](trace.md#t3-normal-affine-transformation), Siegrist *Normal*, unit `rel1`:
"Suppose that X is normally distributed with mean μ and variance σ². If a ∈ ℝ and b ∈ ℝ ∖ {0},
then a + bX is normally distributed with mean a + bμ and variance b²σ²."

| Ref | Claim | Modality | Conditions |
|---|---|---|---|
| C1 | `X` `has_distribution` Normal, `param_values {mean: μ, variance: σ²}` | supposed | — |
| C2 | `Y` `defined_as` `a + b X` | defined | — |
| C3 | `Y` `has_distribution` Normal, `param_values {mean: a + bμ, variance: b²σ²}` | asserted | `and(claim C1, member(a, ℝ), member(b, ℝ∖{0}))` |

`X` and `Y` are local `RandomVariable` entities scoped to the unit; C1 is the premise and C3 the
conclusion of statement `S1` (kind `theorem`); the proof in `<details>` is statement `S2` with a
claim `S2 proves S1`. In C3, `μ` binds `param_of C1 mean` and `σ` binds `param_expr_of C1
variance`. The standard deviation `|b|σ` is a `derived` claim, never stated as `bσ`.

## 13. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D1-1 | Is spaCy sentence segmentation reliable on math-dense paragraphs, or should sentences be split with math spans masked? | Spike S1 |
| OPEN-D1-2 | Do variable scopes need a `section` extent in practice, or does `statement` scope plus "Suppose again" resolution suffice? | Spike S0 reference annotations |
| OPEN-D1-3 | Should `FamilyParameter` identity use role names or source symbols when a source names no role ("parameters μ and σ")? Current proposal: canonical name = role if stated, else symbol; later `parameter_role` claims add roles | Spike S0, D2 review |
| OPEN-D1-4 | Is `section` the right scope extent for Siegrist's page-level standing assumptions (the lead-in "we fixed random variable Z")? | Spike S0 |
