# D1 · Knowledge representation

**Accepted semantic target (2026-10-29; Proposed until implemented).**
[ADR-0024](../adr/0024-semantic-release-preparation.md) governs the new semantic release,
occurrence/fact identity, ontology and preparation contracts. The detailed legacy shapes below
remain the selected runtime baseline until the [pivot series](../plans/semantic-model-pivot_2026-10-29.md)
migrates their consumers. They do not constrain new releases or require historical compatibility.
SP-01 prepares logical artifacts only; persistence, SQL enforcement and consumer adoption belong
to later packages. The decision's carried-forward clauses preserve source fidelity, qualification,
instance authority and consolidation ownership.

> Decision: ADR-0024

**Proposed (2026-10-28).** This document defines what the pipeline produces, independent of
storage ([D3](D3-database.md)) and of the methods that produce it ([D4](D4-method-catalog.md)).
Every other document refers to the types defined here. The [worked trace](trace.md) shows each
type on real Siegrist text.

## Semantic source and qualification profile

**Implemented, 2026-10-29; package acceptance remains scoped by
[SP-06/SP-07](../plans/semantic-model-pivot/domain-operations.md).** The opt-in
`model/semantic/core.yaml` declares mathematical expressions, source-bound macro environments,
explicit expression bindings, typed semantic scope, and compositional conditions. Membership,
comparison, quantification and claim references have distinct node types; an arbitrary predicate
IRI does not acquire a built-in operation from its spelling. Hedging, attribution and partial
validity intervals remain meaning-bearing qualification. Missing bounds or inclusivity stay absent.

Source occurrences preserve their exact reported values even when a canonical fact groups their
meaning. Decimal spelling and timestamp offsets do not select scientific truth. Parsing outcomes,
normal forms, numerical/symbolic comparisons and confidence are operation results, separate from
proposition identity. Located source markup can establish a source statement and what that source
presents as a proof; it does not establish mathematical validity.

> Decision: ADR-0027

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
by its ingest adapter. Evidence `Span` offsets are Unicode code points into that rendition's
canonical text. Added source/representation ranges identify their own coordinate space and unit
under §3.1.1; they never reuse canonical offsets implicitly. Rules for the canonical text:

- Block elements are separated by `\n\n`; list items by `\n`; table cells by `\t` and rows by
  `\n`.
- Inline math keeps its LaTeX source between its original delimiters, e.g. `\(a \in \R\)`.
  Display math keeps `\[ … \]`. A display environment the source places bare, outside any
  delimiters (Siegrist's `\begin{align}` and `\begin{align*}` blocks), is display math too,
  kept verbatim from `\begin` to `\end`. Nothing inside math is rewritten, whitespace included.
  > Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): the bare `align` blocks (106 in the corpus inventory) are delimited as `math_display` segments by the profile's display environments, and every one of the 19,432 element texts compared is reproduced by an independent XPath path ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json)); collapsing whitespace would change 1–5 multi-line formulas per spike page ([s1.variants](../design_review/evidence/2026-10-28_design-spikes/records/s1.variants.json))
- Math is delimited by the delimiters and display environments the source profile declares
  ([D4 M01](D4-method-catalog.md#m01-ingesthtml)). A delimiter the source leaves unbalanced
  makes its math segment `partial`, with the reason (unclosed at block end, unclosed before the
  next opener, closed by the other kind's closer); delimiting resumes at the next opener, so
  one source error never swallows the text after it. A block whose delimiter scan exceeds its
  time bound is `partial` with reason `delimiter scan timeout`. A delimited span the math
  grammar cannot read leaves the segment `ok`: the failure is the value's `parse` status (§6.2),
  kept with its category (ADR-0035).
  > Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): 8 of 28,956 math spans are `partial`, each at an unbalanced delimiter in the source, with its reason recorded ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json)); the profile-generated pattern reproduces the result unchanged ([s1.profile-delimiting](../design_review/evidence/2026-10-28_design-spikes/records/s1.profile-delimiting.json)); the scan timeout is **Proposed** (2026-10-28, [text-math note L-05](../design_review/evidence/2026-10-28_library-text-math/README.md))
- HTML entities are decoded; whitespace inside a block, outside math, collapses to one space;
  the result is NFC-normalized.
  > Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): NFKC would change no character, so NFC loses nothing ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))
- Text a browser shows but the HTML does not contain is canonical text by declared convention,
  and each insertion is recorded as markup on its segment so that a consumer can strip it:
  - an empty cross-reference link (Siegrist's `a.ref`) is `[n]`, the number the page's script
    renders; a sentence never starts at it ([D4 M03](D4-method-catalog.md#m03-segmentsentences));
  - `<q>` content stands between quotation marks `“ ”`;
  - an item of an ordered sub-list (`ol.sub`) starts with its marker `(a) `, `(b) `, …, the
    form the text itself uses to refer to it;
  - a `details` summary is a `heading` segment inside its `details`.

  The conventions are part of the adapter configuration; changing one makes a new rendition only
  when it changes the text (§3.2).
  > Status: **Tested** on the four spike pages (S1, 2026-10-28): `(a) ` markers cause no false sentence split, against 8 for the browser's `a. `; `[n]` markers, each one token that never starts a sentence, cause none, against 4–6 per page for bracketed markers read as text; an empty link leaves broken text ("By , …") ([s1.variants](../design_review/evidence/2026-10-28_design-spikes/records/s1.variants.json)); on 78 pages, with the insertions stripped, all 19,432 element texts compared match an independent path ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))
- Text that is not content (navigation, scripts, app widgets, footer) is excluded by the
  adapter's declared rules ([D4 M01](D4-method-catalog.md#m01-ingesthtml)).

A **rendition** is one content of a document: its canonical text, segments, sentences and macro
table, identified by that content (§3.2), not by the adapter configuration that produced it.
Segments and spans belong to a rendition, and a run selects one rendition per document. Each
ingest of a document by an adapter configuration is a **build**, recorded as provenance with the
parser diagnostics (`kb.rendition_build`, [D3 §5](D3-database.md#5-kb-evidence-observations-entities-and-claims)); builds whose output is
content-identical share one rendition. Ingest (M01 with M03) computes the content digest before
writing and deduplicates by it, so a content-preserving change (a port, a spaCy bump, a profile
fix that changes nothing) keeps every row and key, and a change that alters content produces a
new rendition beside the old one instead of rewriting it (P0CL-01; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

### 3.1.1 Representation-qualified source products

**Accepted target; source scope implemented as qualified below (2026-10-30).** Original source artifacts retain
immutable bytes in PostgreSQL custody ([D3](D3-database.md#parsing-product-custody)). Artifact
content identity is separate from document/acquisition identity. A representation names its
artifact/dependencies, coordinate unit, encoding or transformation recipe and producing build.
Raw bytes, decoded HTML, canonical text and expanded TeX are distinct representations; a range
always identifies one representation, its unit and half-open bounds. A decoding failure preserves
the raw bytes and explicit undecoded coverage.

Complete lexical partitions cover original bytes and the entire canonical representation
separately, and decoded source when decoding succeeds. Ordered components cover their declared
representation once without gaps or overlap, retaining whitespace, delimiters, comments, unknown
material and canonical synthetic separators. A component category asserts lexical identity,
not resolved meaning. Existing TextLayout remains a useful projection; following-space flags
and coarse formula atoms alone do not establish this complete partition. Structural nodes can
overlap above it and carry identified typed relationships with explicit endpoint, role, ordering,
multiplicity and scope; containment is one relationship, not a universal graph interpretation.

Source artifact, representation, partition, structural occurrence/edge, transformation mapping,
interpretation/assessment and producing build/product retain distinct identities. Transformation
mappings connect ordered source and target extent sets with operation/reason, fidelity and
coverage. Many-to-many, normalized, reordered, excluded, synthetic and derived output remains
explicit. Macro invocation, arguments, definition/default and fallback authorities name their
artifact and pinned dependencies. Two `x` occurrences in `x + x` survive an interpretation as
`2*x`; the coefficient is derived, not a literal occurrence.

Rendition identity remains the full content relation of §3.2: canonical text, complete ordered
segment tree including status/reason and attributes, sentences and effective macro table.
Build-specific partition/mapping/interpretation products and parser diagnostics do not enter that
digest; content-identical builds can share a rendition while retaining different provenance.
Changed canonical content or segmentation creates a new rendition and anchors. Consumers pin
the producing build/product through existing reuse resolution and refuse ambiguous selection.

Retain html5lib's HTML5 repaired structure through lxml. Complete original lexical capture and
exact repair provenance are different obligations. Encoding changes, discarded duplicate
attributes, implied nodes and reordering require qualified mappings; DOM paths, `sourceline`
and serialization do not establish exact extents. PP-02 selected native instrumentation; supported fidelity is qualified below. Partial/unavailable mapping must remain visible or refuse a consumer requiring
exact provenance; neither raw nor canonical partition completeness is thereby relaxed.

**Implemented and scoped Tested — PP-00–PP-04 (2026-10-30).** Original bytea custody,
raw/decoded/canonical complete partitions, identified HTML structural relationships and build-bound
transformation products are implemented. The qualified `canonical_output` universe traces through
admitted decoding/normalization or synthetic production; it is not a promise of exact byte copying
or origin for every repaired node. Unknown origin remains partial. Layered text products retain expanded TeX, parse views and many-to-many macro derivations.
Versioned mathematical products retain distinct occurrences, interpretation context, source
definedness and named assessments without using native values as source identity. Their
implementation and remaining assembled acceptance are owned by
[PP-05–PP-10](../plans/parsing-pipeline_2026-10-30.md#remaining-scope-execution). [Execution and evidence](../plans/parsing-pipeline_2026-10-30.md#pp0004-execution)
own the selected qualification boundary.

> Decision: [ADR-0036](../adr/0036-representation-qualified-parsing-products.md)

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
| `math_display` | Display formula | `\[ … \]`; a bare `\begin{align}` or `\begin{align*}` block (§3.1) |
| `math_inline` | Inline formula | `\( … \)` |
| `heading` | Heading text | `<h1>`–`<h6>` |
| `table`, `table_row`, `table_cell`, `caption`, `footnote` | Tables and notes | as named |
| `figure` | A figure: container of its `caption` | `<figure>` with `<figcaption>` |
| `sentence` | Sentence, from segmentation | spaCy |
| `email_message`, `quoted_block`, `signature` | Email structure (later) | — |

> Status: nested `h3`/`h4` sections **Tested** on the four spike pages (S1, 2026-10-28): sectioning by `h3` alone would remove 4–9 sections per page ([s1.variants](../design_review/evidence/2026-10-28_design-spikes/records/s1.variants.json)), and all 13 locators of [D2 §12.2](D2-schema-and-guidelines.md#122-slicesyaml) resolve to exactly one segment ([s1.adapter](../design_review/evidence/2026-10-28_design-spikes/records/s1.adapter.json)); what section extents mean for variable scopes is `OPEN-D1-2`

> Status: `figure` **Tested** on 78 Siegrist pages (S1, 2026-10-28): 51 figures, each a container with its caption kept ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))

Text placed directly in a container, outside any block element (most often a display formula
put bare in a `unit` or `details`), is a `paragraph` segment with `attrs.orphan: true` and the
container's kind, so no content is lost for want of a block element.

Production segments carry no diagnostic attributes. What depends on the parser (where an element
sat in the source file, `sourceline`, which html5lib supplies about once per page; the parser's
errors with their positions; the adapter's exclusion records) goes to the build's `parse_detail`
([D4 M01](D4-method-catalog.md#m01-ingesthtml); D3 `kb.rendition_build`), never to `attrs`, so
nothing parser-dependent is part of a key, of the rendition contract or of an identity comparison
between renditions.
> Status: **Proposed** (2026-10-28)

**Content identity.** Two builds of one document are content-identical when their canonical
text, their segments' kinds, offsets, parse statuses, attributes and tree, their sentence
segments and their macro table are identical. That relation is the rendition's identity: the
**content digest** is the SHA-256 of the canonical JSON (§10.1), with default-valued fields
left out so that adding a defaulted field later moves no key, of the canonical text, the
segment tree (each whole segment: kind, offsets, parse status and attributes, children in order,
sentences included) and the macro table, and the rendition key is the document key plus that
digest (§10.1). Because segments hold no diagnostics, the digest covers whole segments and needs
no exclusion list. The macro table is content because canonical forms
expand macros by it (§6.2): two builds that read the page's definitions differently must not
share a rendition. Content-identical builds by different adapter configurations are one
rendition, so they share every segment row and every key under it; parser diagnostics,
exclusion records and the configuration stay on each build (P0CL-01; operator, 2026-10-28).
> Decision: [ADR-0024](../adr/0024-semantic-release-preparation.md)
> Status: the relation **Tested** for canonical text, segments and sentences (2026-10-28):
> libxml2 and html5lib renditions of the seven pages S0 and S0-R2 use are identical in them
> ([s1.rendition-identity](../design_review/evidence/2026-10-28_design-spikes/records/s1.rendition-identity.json));
> parse statuses and the macro table in the relation, and keying renditions by its digest, are
> **Proposed** (2026-10-28)

> Status: **Measured** (2026-10-28, [text-math note L-01](../design_review/evidence/2026-10-28_library-text-math/README.md)): html5lib trees of the 78 Siegrist pages carry `sourceline` on 78 of about 29,000 elements, and record 17 parse errors with positions

> Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): 44 orphan runs (18 in `details`, 17 in units, 9 at section level), the same under both HTML parsers; no block is left unclassified ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))

Segment attributes (`attrs`) hold author markup verbatim: element id, CSS classes, `<dfn>`
terms with their offsets, link targets. Author markup is an **input**: the adapter also emits it
as `author_markup` observations so that methods can use it ([D4 M01](D4-method-catalog.md#m01-ingesthtml)).
Evaluation does not use author markup as a gold for anything the pipeline consumes it for
([D7 §6](D7-evaluation-goldens-outer-loop.md#6-independent-witnesses)).

A segment also carries `parse_status`: `ok`, `partial` (some content dropped, with reason) or
`failed`. A failed segment is retained so that its absence of claims is explained, not silent.
This is the delimiting status of §3.1, never `ambiguous`: ambiguity is a formula value's parse
outcome (§6.1, the schema's `ParseStatus`), which values carry and segments do not
([D3 §5](D3-database.md#5-kb-evidence-observations-entities-and-claims)).
> Status: **Proposed** (2026-10-28), answering S6's finding that the compiled `ParseStatus` has
> `ambiguous` and the segment and rendition CHECKs do not
> ([s6.dry-run-2](../design_review/evidence/2026-10-28_design-spikes/records/s6.dry-run-2.json))

### 3.3 Spans

A `Span` is `(rendition, start, end)` with its text. It remains the canonical evidence anchor:
every citation of evidence resolves to one or more spans. Representation-qualified source ranges
(§3.1.1) are additional anchors for decomposition and transformations, not replacements for this
evidence contract. A span records the smallest segment that contains it.
Spans are deduplicated by `(rendition, start, end)` and upserted by the repository layer for
any writer (ingest, methods, consolidation), so citing an offset never requires owning span rows.

### 3.4 Locators

A **locator** names a segment by what the source shows, an author id or the opening words of its
text, instead of by offsets, so it resolves on every rendition of the document in which that text
is unchanged. This is the one locator contract: slices ([D6 §8](D6-orchestration-metrics-policies.md#8-debug-slices-and-output-size)),
fixtures, citation frames (§10.3), the `statement(locator)` query and evidence locators
([D8 §5](D8-agent-and-query-interfaces.md#5-typed-queries)), `ExternalReference` resolution (§4.4) and the
statement and local-entity keys (§10.1) all use it. Its owner in the build is ingest and math, as
one core-level function over a rendition's segments that every consumer calls (P0CL-04;
operator, 2026-10-28).

| Form | Selects |
|---|---|
| `page` | the `document` segment |
| `page#id` | the segment whose author id (`attrs.id`) is `id`, when exactly one segment of the page carries it |
| `page@kind:prefix` | the one segment of that kind whose canonical text starts with `prefix` |
| `page@kind[n]:prefix` | the `n`-th segment (from 1, in document order) of that kind whose canonical text starts with `prefix` |

`page` is the document's source URI relative to the source root that the source profile declares;
project initialization refuses a corpus in which two documents have the same page, so a page
names one document. `kind` is a segment kind of
§3.2, with `u` and `p` as the short forms of `unit` and `paragraph` that slices already use
([D2 §12.2](D2-schema-and-guidelines.md#122-slicesyaml)). Prefixes are compared with whitespace
collapsed, on canonical text (LaTeX verbatim, NFC).

- **Generator.** For a segment of a rendition, the generated locator is its author id when that
  id is unique on the page. Otherwise it is `@kind:` with the shortest prefix, in whole words of
  the whitespace-collapsed text, that no other segment of the same kind starts with. When another
  segment of that kind starts with the segment's whole text (identical paragraphs, a one-word
  proof), no prefix is unique: the generator takes the shortest prefix that selects only the
  segment and those segments, and adds the segment's ordinal `[n]` among them. Generation is a
  function of the rendition's segments alone, so content-identical renditions give identical
  locators.
- **Resolver.** On a rendition, a locator selects by id, or by kind, prefix and ordinal. A locator
  that selects no segment, several where it gives no ordinal, or fewer than its ordinal, is
  **refused** with the candidates listed; it is never resolved to a nearest match. Each consumer
  decides what a refusal means: a slice fails its run's start (D6 §8), a citation frame marks its
  golden unit stale ([D7 §3.5](D7-evaluation-goldens-outer-loop.md#35-staleness-and-re-authoring)).
- **In keys** a locator enters in structured form with the document key in place of the page:
  `{"doc": <document key>, "id": …}`, or `{"doc": …, "kind": <kind name>, "prefix": …}` with
  `"n"` when the locator has an ordinal; the bare `page` form of the document segment is
  `{"doc": …}`. Kind names are spelled in full there; the short forms never reach a key. An empty
  author id, or one containing whitespace, is a syntax error and is never generated.
- **Unit key.** An annotation unit (a `unit` segment, or a paragraph outside units) is named across
  renditions by its **unit key**, the string form of its generated locator, e.g.
  `special/Normal.html#rel1`. Packets (`unit_ref`, D2 §7.3), tasks (`ops.task.unit_key`), golden
  units and golden sampling use it.

> Decision: [ADR-0019](../adr/0019-identity-follows-content.md)
> Status: the `#id`, `@u:` and `@p:` forms **Tested** on the four spike pages (S1, 2026-10-28):
> all 13 slice locators resolve to exactly one segment
> ([s1.adapter](../design_review/evidence/2026-10-28_design-spikes/records/s1.adapter.json)), and
> to the same span under both HTML parsers
> ([s1.rendition-identity](../design_review/evidence/2026-10-28_design-spikes/records/s1.rendition-identity.json));
> the generator, the ordinal form, the other kinds and the structured key form are **Proposed**
> (2026-10-28)

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
| `attrs` | Identity attributes declared by the schema (the class's identity `unique_keys`, D2 §3.1), keyed by prefixed slot name (`stat:family`, `stat:canonical_name`); never facts |
| `kind` | Statements only: the `StatementKind` value (§4.3) that consolidation chooses ([D5 §3.5](D5-consolidation-identity-confidence.md#35-statements)); a field like `label`, never identity |

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

### 4.4 External references

A reference to something outside the batch ("the last result", "definition [1]", an author `[n]`
link, an email's "as I wrote below") is a typed **`ExternalReference`** node, a core entity class,
never an `unsupported` item and never a dropped claim:

- **Authored.** It is D2 §7.3's `outside` statement item (`anchor: "outside"`, variant V2), which
  carries a **descriptor**: the citing sentence (a sentence id of the batch) and the quote that
  makes the reference, and the author's link target when there is one.
- **Stored and keyed.** The quote is located on the rendition by the quote cascade and stored with
  its span. The node is a local entity anchored at the citing statement's anchor segment, keyed
  `xrf` by the citing statement's key, the descriptor's quote in text form and the link target when
  present
  (§10.1). It has no statement `kind`, so a statement row still always has one
  ([D3 §5](D3-database.md#5-kb-evidence-observations-entities-and-claims)).
- **Used.** Claims keep it where they cite it: as subject, object, `claim` condition target or
  binding target.
- **Resolved by consolidation.** Consolidation resolves it through its link target or a locator
  (§3.4) to a statement of the run, records the `resolves_to` relation on the node and keys the
  citing claim with the resolved statement's key in its place, so it fuses with claims that cite
  the statement directly (a stated stability limit, §10.3). The node keeps its own key either way
  ([D5](D5-consolidation-identity-confidence.md)).
- **Unresolved.** An unresolved reference stays a typed node: the citing claim is served as
  conditional on it (INV-09), it counts in coverage, and queries render it as "an unresolved
  reference: …" ([D8 §5](D8-agent-and-query-interfaces.md#5-typed-queries)).

This closes OPEN-D1-5 on one treatment shared with D2's V2 (alignment review RC11; operator,
2026-10-28).
> Decision: [ADR-0023](../adr/0023-declared-identity.md) for its key; the node itself is the
> alignment review's RC11 (phase 0 coordinator decision 21)
> Status: **Proposed** (2026-10-28); the node, its key and resolution are built by foundations
> (F2e) and consolidation (C1)

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

Every claim may carry these, whatever the domain. They are named here by their local names, as
the model-facing batch writes them; stored claims, keys and compiled rows use the prefixed names
(`core:modality`, `core:attribution`, …), like every schema element (D2 §7.1).

**Identity is declared, not decided by code.** Every qualifier, core and schema alike, has a
**qualifier specification** in the model: its range, its default, its **key role**, an optional
**role condition**, its canonical form by range (§6.2), its case policy (§6.2) and its store
placement. The specifications compile into one `KeySchema`, which the key function (§10.1),
consolidation's slots and conflict detection
([D5 §5.4–§5.5](D5-consolidation-identity-confidence.md#54-slots-core-support-refinements-and-alternatives))
and the rule view read; none of them restates the rules below. The specification's fields are
fixed by [model and projections §3.2](../plans/phase-0/model-and-projections.md#32-stage-a-generation-m1).
The key roles are:

- `identity`: the qualifier enters the claim key in its canonical form;
- `meaning`: it stays out of the key but carries meaning, so candidates that share a key and
  disagree on it become alternatives (`alternative_of`), not one fused claim
  ([D5 §5.3](D5-consolidation-identity-confidence.md#53-fusion));
- `inert`: neither.

A role condition names a member property of the claim's modality under which the role becomes
`identity`. The core specifications are:

| Qualifier | Range | Default | Meaning | Key role | Condition |
|---|---|---|---|---|---|
| `modality` | `ClaimModality` (schema-version-scoped, below) | `asserted` | How the source puts the claim forward; see below | identity | — |
| `polarity` | `Polarity`: `positive`, `negative` | `positive` | "X is not normal" is a negative claim, not an absent one | identity | — |
| `hedge` | a `phrase` value | absent | "typically", "approximately" | meaning | — |
| `attribution` | an entity reference | absent (the document's author) | Who says it, when not the author | meaning | identity when the modality has `attribution_identifying` (core: `cited`) |
| `conditions` | a condition tree (§7) | absent | Under what conditions the claim holds | identity | — |
| `scope` | `{segment, extent}` (authored: extent only), extent ∈ `statement`, `section`, `document` | absent | Where a supposition applies when broader than its statement | meaning | — |
| `valid_time` | an interval value | absent | When the fact is true in the world (business domains) | identity | — |

`statement` stays a key part of its own, beside the qualifiers (§10.1). A schema qualifier takes
its role from the pack: `ci:key_role` on its slot, or the pack's `ci:identity_qualifiers` list
compiled into the same specification (§5.3, D2 §3).

`valid_time` and the cited source are identity because they change what is claimed: "ORG-101
owns P-17" for two intervals in one table statement is two facts, and "Smith showed X" and "Jones
showed X" are two reports. An attribution under a modality without `attribution_identifying`, and
the phrasing of any attribution ("as Smith (1990) showed"), stay out of the key; candidates that
share a key but disagree on `hedge`, `scope` or attribution phrasing become alternatives (P0CL-06;
operator, 2026-10-28). No member name is written in the key function: a pack modality under which
attribution identifies gets the property, and no core edit follows.
> Decision: [ADR-0023](../adr/0023-declared-identity.md)
> Status: **Proposed** (2026-10-28); the role rule is hard-coded in `keys.py` at `6f31f75`
> (Implemented, to be replaced by the compiled `KeySchema`, foundations F2d)

**Modalities.** `ClaimModality` is **schema-version-scoped**: the core members below plus the
members a pack declares, each member carrying its **member properties**, so a pack's business
modality needs only a pack declaration (phase 0 coordinator decision 18). The core members and
their properties:

| Modality | Use | Properties | Example |
|---|---|---|---|
| `asserted` | The author states it as true | `conflict_bearing` | The conclusion of a theorem |
| `supposed` | Assumed within a statement or scope; not asserted beyond it | `premise_forming` | "Suppose that X is normally distributed…" |
| `defined` | A stipulation that makes something true by definition | `conflict_bearing` | "Then X = e^Y has the lognormal distribution" in a definition |
| `conventional` | An author convention, explicitly optional | — | "it's convenient to consider a constant as having a normal distribution" |
| `exemplified` | Values given in an example or exercise setup | — | "The radius of the rod is normally distributed with mean 1 cm" |
| `posed` | A quantity or question an exercise asks for. **Reserved** until the `asks_for` predicate exists (D2 §9, OPEN-D2-15); guideline v1 records asked quantities as `unsupported` meanwhile | — | "Find the probability that…" |
| `cited` | Reported from another source | `attribution_identifying` | "Smith (1990) showed…" |

Each property has its consumers, which read the property and never a member name:

| Property | Core members | Read by |
|---|---|---|
| `premise_forming` | `supposed` | INV-06 (§11); the default query filters ([D8 §5](D8-agent-and-query-interfaces.md#5-typed-queries)) |
| `attribution_identifying` | `cited` | the claim key: attribution's role condition (above, §10.1) |
| `conflict_bearing` | `asserted`, `defined` | conflict detection ([D5 §5.5](D5-consolidation-identity-confidence.md#55-equivalence-and-conflict-across-statements)) |

`supposed` is what keeps hypothetical premises from becoming facts: a query for "what is
normally distributed" returns nothing from a premise unless it asks for suppositions.
> Status: **Proposed** (2026-10-28)

### 5.3 Schema-defined qualifiers

A predicate may declare additional qualifiers in the schema ([D2 §4](D2-schema-and-guidelines.md#4-predicates-and-qualifiers)).
The statistics pack declares, for example, `param_values` on `has_distribution`: a map from
family-parameter canonical names to formula values, which the predicate's annotation
`ci:param_map: param_values` names as the map that `param_of` bindings read (§6.1). Schema
qualifiers are how n-ary facts with one primary subject and value stay a single claim.

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
`follows_from` and `refers_to`. A structural claim (these three and `defines`) carries its
subject statement as its `statement`, with no `statement_role`, whether the author states it or
the source profile's containment rule synthesizes it
([D5 §3.5](D5-consolidation-identity-confidence.md#35-statements)); an author-stated and a
synthesized `proves` between the same statements therefore have one key and fuse.
> Status: **Proposed** (2026-10-28)

## 6. Values

A value is a tagged JSON object. Every value has `t` (type). Value types:

| `t` | Fields | Example |
|---|---|---|
| `text` | `v` | `{"t":"text","v":"location-scale family"}` |
| `number` | `v` (canonical decimal string, §6.2); optional `unit` (the unit as the source states it) and `basis` (a reference basis the source states, such as `gauge` or `absolute`) | `{"t":"number","v":"0.002","unit":"cm"}`, `{"t":"number","v":"300","unit":"kPa","basis":"gauge"}` |
| `bool` | `v` | `{"t":"bool","v":true}` |
| `enum` | `enum` (the enum's name: local in the model-facing batch; prefixed, and required to be, in the stored form, one value variant per batch form), `v` (the member, verbatim) | `{"t":"enum","enum":"stat:ParameterRole","v":"scale"}` (stored). Enum names are normalized by prefixing, never by case, and the canonical form is `{enum, v}` as stored (§6.2) |
| (entity reference) | `{ref}` (a local ref in batches, an entity key once keyed) | an entity reference, a position type, not a value: one shape, `{ref}` without `t`, in every position that may take an entity (claim objects, `pred` arguments, entity-ranged qualifiers such as `attribution` and `base_variable`), so decoding has one shape per position (D2 §7.3). Fields that only ever hold a reference (a claim's subject and statement, identity slots, binding targets) are plain ref strings. **Tested** (S4 variant V1, 2026-10-28, record `s4.batch-validation`: 135 of 135 batches valid in this shape) |
| `formula` | `latex`, `sympy`, `parse`, `symbols` | below |
| `set` | `latex`, `sympy`, `parse`, `symbols` | `ℝ`, `(0, ∞)`, `ℝ ∖ {0}` |
| `date` | `v` (ISO 8601, kept verbatim) | business domains |
| `interval` | `start`, `end` (values, absent when unbounded), `start_incl`, `end_incl` | valid time |
| `phrase` | model-facing: `text`, optional `sentence` (the `sN` or `cN` it lies in); stored: `start`, `end`, `text`, optional `coarse` | text kept but not interpreted |

A `phrase` has one field set per batch form (D2 §7.3): an author writes the text and may name its
sentence; the stored form adds the offsets the quote cascade locates on the observation's
rendition ([D4 §4.3](D4-method-catalog.md#43-output-form-and-post-processing)), with `coarse: true`
when the text was not located exactly and the span covers the cited sentence. An optional field is
absent when it has no value, never `null` (D2 §7.3).
> Status: **Proposed** (2026-10-28); the value shapes, their form-specific fields and absent-not-null
> are **Tested** against core.yaml's mirror (S4, 2026-10-28, record `s4.batch-validation`: the
> contract test and the 135 listed batches)

### 6.1 Formulas and symbol bindings

A formula value keeps the source LaTeX exactly (`latex`), a normalized SymPy form when the
expression parses (`sympy`, as `srepr`), the parse outcome (`ok`; `ambiguous` when the grammar
reads it in more than one way and declared context chooses none, [D4 M11](D4-method-catalog.md#m11-normalizeformula);
`partial`; `failed`), and a **symbol binding map**:

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
| `param_of` | The symbol is the value of entry `param` of the map qualifier that the referenced claim's predicate names by `ci:param_map` (for statistics, `param_values` of a `has_distribution` claim) |
| `param_expr_of` | The symbol occurs inside the value of that entry (σ in a variance of σ²) |
| `family_param` | The symbol denotes an entity (`"entity": key`) of a class the pack marks `ci:parameter_class` (for statistics, `FamilyParameter`) |
| `free` | A symbol introduced by this statement, restricted by its conditions |
| `constant` | A mathematical constant (e, π) |
| `unresolved` | Not bound; a resolution gap counted by D6 metrics |

Symbol-map keys are symbols in token form (§6.2), and a symbol that is a lone control word is
written without its backslash (`\mu` is `mu`), as it is in keys (§10.1).
> Status: **Proposed** (2026-10-28)

Symbol bindings are the general form of what the old system called a governing input
association: which source-backed symbol supplies which parameter, under which premise. Unresolved
bindings never block a claim; they lower its completeness and are measured. Bindings stay out of
the claim key, but they carry meaning: candidates with equal keys and different bindings become
alternatives (§10.1, D5 §5.3).

The binding kinds hold no domain names: which qualifier is a parameter map and which class is a
parameter are pack annotations ([D2 §3](D2-schema-and-guidelines.md#3-the-ci-annotation-vocabulary)),
and the predicates whose claims bind `family_param` first are the pack's `family_structure`
subset, which the binding rules read ([D5 §4](D5-consolidation-identity-confidence.md#4-symbol-binding))
(P0CL-07; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

### 6.2 Canonical form

For keys and comparisons, a value has a canonical form: formulas and sets by **normalized
LaTeX** (source macros expanded by the rendition's own macro table, recorded by M01, with the
pack's map only for names the page does not define; the commands of the drop list below, such as
`\,`, `\;`, `\!`, `\left` and `\right`, and whitespace removed, except inside a text-mode
argument, where whitespace collapses to one space; braces around single tokens dropped, so
`b^{2}` is `b^2`). The SymPy
form is never part of a key, so adding or upgrading the parser never changes keys; consolidation fuses candidates whose formulas SymPy proves equivalent ([D5 §5.3](D5-consolidation-identity-confidence.md#53-fusion)); text
NFC-normalized with collapsed whitespace and its declared case policy (below); dates by their ISO
8601 string as written, never reformatted or converted to another time zone. Formula equivalence
for evaluation uses SymPy simplification
([D7 §5](D7-evaluation-goldens-outer-loop.md#5-alignment-and-scoring)), not canonical form.

**Canonical form by declared range.** A value's canonical form is chosen by the range its slot or
qualifier declares (§5.2), never by the value's JSON shape, so a map entry `{"ref": "Smith"}` under
a string range is a string, not an entity reference:

| Declared range | Canonical form |
|---|---|
| `formula`, `set` | token form over the rendition's effective macro table (below; ADR-0035); `symbols`, `sympy` and `parse` stay outside |
| `text`, `phrase` | text form: NFC, whitespace collapsed, case per policy (`fold` by default); a phrase by its text alone, never its offsets, sentence or `coarse` |
| string identifier (a `string` range with `ci:case` declared) | NFC, whitespace collapsed, the declared case |
| `enum` | `{enum: <prefixed enum name>, v: <member>}` verbatim |
| an entity class or `Entity` | the resolved entity key, after the resolver's kind check (§10.3) |
| `interval` | recursive over its bounds and inclusivity flags |
| a map-entry range (`param_values`) | an object from each key (NFC) to the canonical form of the entry's declared value range |
| `number` | the canonical decimal (below), with `unit` and `basis` NFC and whitespace-collapsed, never converted |
| `date`, `bool` | verbatim |

**Case policy** (`ci:case`: `fold` or `preserve`) is declared on string-ranged slots and on each
class's label, and the text form and label normalization (§10.1) apply it; nothing guesses it
from a value's shape. `fold` is the default and applies to prose labels and prose literals.
`preserve` applies to math-bearing text:

- the labels of classes declared math-bearing, such as `RandomVariable`, whose label is its
  defining expression when it has no symbol;
- literal identity slots whose fallback is a symbol, such as `FamilyParameter.canonical_name`
  under OPEN-D1-3's rule (the role word, else the symbol).

So `X` and `x`, or `\Sigma` and `\sigma`, key apart where the text is declared math-bearing and
alike under `fold`. Symbols already keep case (§10.1), and the label and symbol paths now agree.
A business identifier such as `ORG-101` gets the case its pack declares for the slot.
> Decision: [ADR-0023](../adr/0023-declared-identity.md)
> Status: **Proposed** (2026-10-28); the code at `6f31f75` chooses canonical forms by JSON shape
> and casefolds every label (Implemented; DA-001, DA-008), to be replaced by foundations F2d

**Numbers** take a canonical decimal string: no exponent (`1e-3` is `0.001`), no trailing zeros
after the point and no point without digits after it (`300.0` and `300.` are `300`), no leading
`+`, one zero before the point for magnitudes below one and no other leading zeros (`.5` is
`0.5`), and `-0` is `0`. The stated `unit` and `basis` are kept as written (NFC, whitespace
collapsed) and enter the key with the value; nothing converts units for keys, so `30 cm` and
`0.3 m` are different keys, and gauge and absolute pressures never coincide. Conversion (pint)
happens only in evaluation's value equivalence ([D7 §5](D7-evaluation-goldens-outer-loop.md#5-alignment-and-scoring)),
from phase 1; phase 0 evaluation compares canonical decimals with their units as written
(P0CL-06; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28); Hypothesis properties over the canonicalization belong to
> foundations (phase 0)

Canonical form for keys is the **token form, for every formula and set value**: token normalization over the
rendition's macro table, by whole command name (`\P` never matches inside `\Phi`), with spacing
and sizing commands removed (`\big`, `\Big`, `\bigg`, `\Bigg` and their `l`/`r`/`m` forms, beside
those above). It is total and does not depend on whether the value parses, so extending the
grammar never changes a key. The parse tree of the one math grammar (D4 M11) serves validation,
slot typing, SymPy conversion and equivalence fusion.

Macro names are control words (`\` and letters); a definition of a control symbol is refused.
The **effective macro table** of a rendition, its own macro table merged over the pack's fallback
map (a page definition wins), is computed by one `core` function beside the tokenizer
(`core/tex.py`), and every reader of math calls it: the grammar's generated macro rules (D4 M11),
the token form, and the quote cascade
([D4 §4.3](D4-method-catalog.md#43-output-form-and-post-processing)). No reader merges the two
maps itself, so they cannot expand one formula differently.
> Status: **Proposed** (2026-10-28)

The token form is fixed by these rules, settled before the first production keys are written,
because any later change to them moves keys:

- **One outer pair of math delimiters is removed** (`\(…\)`, `\[…\]`, or the `\begin`/`\end` of
  one of `equation`, `align`, `alignat`, `flalign`, `gather`, `multline`, `eqnarray`,
  `displaymath`, `math`, and the starred forms of those that have one), so the same formula
  written inline or displayed keys alike; `$` is not a delimiter. An environment's layout
  argument (the column count of `alignat`) is removed with its delimiter.
  Inner delimiters cannot occur: M01's delimiting never leaves one inside a span, and the drop list
  (which includes SymPy's `\(` literal) is applied as written. Macro expansion substitutes
  arguments as TeX does, without added braces, and is bounded at depth 16 and at 100,000 tokens of output;
  an expansion past either bound stops and the value keeps that macro and its arguments unexpanded,
  their names recorded once each in `parse_detail`.
  > Status: **Tested** for parity (2026-10-28): the spike instruments' revision I-R2 and the
  > product's `core/tex.py` give the same token form on all 918 math spans of the four spike pages

- **Tokens are TeX's**, read by a TeX-rules `regex` tokenizer, not by the grammar's lexer or
  terminals (which would couple keys to the grammar again): a control word is `\` followed by
  letters, a control symbol is `\` followed by one other character, and anything else is one
  character. A `*` is never part of a control word: `\cmd*` is two tokens. The same tokenizer
  reads M01's macro definitions and locates the token at a grammar error (D4 M01, M11).
- **One declared drop list**, beside the tokenizer in `core`, holds the removed commands: every
  `%ignore` literal of SymPy 1.14's `latex.lark` (the spacing commands from `\,` and `\thinspace`
  to `\qquad` and `\negthickspace`, `\left`, `\right`, `\limits`, `\nolimits`, `\displaystyle`,
  `\vspace`, `\hfill` and the rest) and the sizing commands above. The grammar extension's added
  `%ignore` lines are generated from it, and building the grammar fails if an `%ignore` terminal
  of the assembled grammar is not on it, so the grammar and the normalizer never drop different
  sets.
- **Text-mode arguments** (`\text`, `\mathrm`, `\textrm`, `\mbox`, `\operatorname`): each
  whitespace run inside them collapses to one space instead of being removed, so
  `\text{ for all }` never becomes `\text{forall}`.
- **Control spaces**: `\ ` followed by a space, a tab, a newline or CR LF is one token, spelled `\ `,
  and blanks directly after it are skipped, as TeX skips them (in text mode also when only a
  dropped command such as `\,` separates them from it). A control space is still content:
  `a\ b`, `ab` and `a\,b` differ.

The spike instruments follow these rules since I-R2, and the product normalizer reproduces their
token form on every math span of the four spike pages (`fixtures/tex/token_form_spike_pages.jsonl`,
918 rows; record `i-r2.token-form-parity`). Status: **Tested** (2026-10-28).

A property test holds the token form and the tree together: for every parsed value the tree
printer and the token form agree, and where they cannot, the token form is the key and the case is
reported. It has two layers. The corpus layer runs over every span of the gold pages, and each
listed disagreement carries its cause. The metamorphic layer tests the token form alone, with no
grammar: the form is unchanged by inserting `\,`, `\;`, `\!`, sizing commands, braces around a
single token, or whitespace between tokens outside text-mode arguments, and it never merges `\P`
with `\Phi` or `\mu x` with `\mux`. A value that does not parse to one reading keeps its verbatim
LaTeX with `parse: ambiguous`, `partial` or `failed`. A value must parse under its slot's declared
range (formula, set, relation, membership); a mismatch is a validation issue, not a silent
coercion.

> Decision: [ADR-0035](../adr/0035-model-governed-analysis.md)
> Status: **Measured** on the spike pages (2026-10-28): 881 of 918 math spans parse; the tree and
> token forms differ on 4, all at `\big/`, which the sizing rule removes. The property test's two
> layers are Proposed (S5, phase 0); the drop list's contents are **Interface-checked** against
> the `%ignore` lines of SymPy 1.14.0's `latex.lark` (2026-10-28), and the normalizer is frozen once
> S5's key-property record (`s5.keys-property`) is final (**Proposed**, 2026-10-28)

> Status: **Measured** on the 78 Siegrist pages (2026-10-28, [text-math note L-07](../design_review/evidence/2026-10-28_library-text-math/README.md)):
> 248 of 28,956 math spans contain sizing commands, all kept by the spike's token form; 32
> text-mode groups hold several words; no control word is directly followed by `*`. The corpus
> layer exposed the spike grammar's `\left` prefix defect (`xarrowy` against `x\leftarrow y`,
> D4 M11); with the whole-name terminals, 877 of 918 spike-page spans agree, and the remaining
> parsed ones differ at sizing commands

> Decision: [ADR-0035](../adr/0035-model-governed-analysis.md)
> Status: **Tested** in the spike instruments (2026-10-28): 86 of 86 S0 values read, canonical forms decided all but a handful of value comparisons ([s0.instruments-ir2](../design_review/evidence/2026-10-28_design-spikes/records/s0.instruments-ir2.json)); production code not written

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
| `phrase` | the `phrase` value's fields (§6): model-facing `text`, optional `sentence`; stored `start`, `end`, `text`, optional `coarse` | Anchored condition text not interpreted |
| `unsupported` | as `phrase`, plus `reason` | A condition the language cannot state |

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

**Canonical form.** A condition tree enters a claim key (§10.1) in canonical form. These rules
apply bottom-up until none applies:

- an `and` inside an `and`, or an `or` inside an `or`, is flattened into its parent;
- an `and` or `or` without arguments is dropped, and a tree left empty is no condition (null);
- an `and` or `or` with one argument is replaced by that argument;
- the arguments of `and` and `or` are sorted by their canonical JSON (§10.1), and identical
  arguments are kept once;
- a `cmp` with `>` or `>=` is written as `<` or `<=` with `lhs` and `rhs` swapped, and a `cmp` with
  `=` or `!=` orders its two sides by their canonical JSON;
- the arguments of a `pred` are sorted only when the schema declares the condition predicate
  symmetric ([D2 §5](D2-schema-and-guidelines.md#5-condition-predicates)); otherwise their
  order is part of the meaning;
- a `phrase` or `unsupported` leaf enters by its text alone, in the canonical text form of §6.2,
  so offsets, sentence ids and `coarse` never reach a key;
- values take their canonical form (§6.2), and `claim` nodes carry claim keys.
> Status: **Proposed** (2026-10-28)

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
| Unresolved external reference | An `ExternalReference` node without a `resolves_to` relation (§4.4); its citing claims are conditional on it |

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
| `claim_proposal` | the authored batch (model-facing form, local references) with its citation frame (§10.3), plus the stored form derived from them on the observation's rendition | M10, agent |
| `judgment` | target (observation, claim key, alternative group or identity group), decision, rationale | M16, agent, human |
| `verification` | claim key, verifier, verdict (`consistent`, `refuted`, `not_checkable`), detail | M21 |

## 10. Identity and keys

### 10.1 Hashing

`key = <prefix> + ":" + hex(sha256(canonical_json(parts)))[:32]`. Key parts name schema
elements (classes, predicates, qualifiers, identity slots, enums) by their prefixed names, as the
stored form does (D2 §7.1), so a key never depends on which spelling a batch used. `canonical_json`
is one function, used for keys, rendition content digests (§3.2) and configuration hashes:

- UTF-8, with no insignificant whitespace;
- every string, object keys included, NFC-normalized; an object with two keys that are equal
  after NFC is refused, never merged;
- object keys sorted by code point (Python's `sort_keys` order over NFC strings, not RFC 8785's
  UTF-16 order);
- no floats: numbers are integers (offsets, ordinals), and a decimal travels as the canonical
  string of §6.2. A float in a key part is refused, never rounded; a configuration loader turns a
  float parameter into the canonical decimal of its shortest round-trip form before hashing.

| Object | Prefix | Parts |
|---|---|---|
| Document | `doc` | project name (never the project's database id), source_uri, content_hash |
| Rendition | `ren` | document key, content digest (§3.2) |
| Segment | `seg` | rendition key, kind, start, end: physical, so a segment key belongs to one rendition |
| Span | — | natural key `(rendition, start, end)` |
| Annotation unit | — | unit key: the string form of its generated locator (§3.4) |
| Global entity | `ent` | type and identity attributes; the normalized canonical label only when the type's identity attributes are incomplete (a `FamilyParameter` keys by family and canonical name alone) |
| Local entity | `ent` | type, scope locator (§3.4, structured form, which carries the document key), normalized symbol or label |
| Statement | `stm` | the statement's anchor locator (§3.4, structured form, which carries the document key) and the ordinal, within the anchor segment, of the statement's first sentence. The anchor segment is the `unit` for a statement inside a unit, the `details` block for a proof or solution, and the `paragraph` outside units; a statement in no annotation unit (a top-level list, table, figure, caption or footnote) anchors on its enclosing top-level block, never on the document; so "the unit" and "its first sentences" key alike, two statements in one block do not collide, and an edit in another block moves no statement's key |
| External reference | `xrf` | the citing statement's key, the descriptor's quote in text form (§6.2), and the author's link target, as written (NFC), when the descriptor has one (§10.3; the `outside` item of D2 §7.3). The citing sentence id is local to its batch and never a part |
| Claim | `clm` | subject key, predicate, object key or canonical value, the statement key (its own part, beside the qualifiers object), and, by prefixed name in their range's canonical form (§6.2), the qualifiers whose specification gives them the `identity` role or whose role condition holds (§5.2); a member of an alternative group whose candidates share these parts adds its own canonical values of the disagreeing qualifiers and of its disagreeing bindings ([D5 §5.3](D5-consolidation-identity-confidence.md#53-fusion)), so claim keys stay unique within a run |
| Alternative group | `alt` | the sorted keys of its members ([D5 §5.4](D5-consolidation-identity-confidence.md#54-slots-core-support-refinements-and-alternatives)) |
| Identity group | `idg` | the sorted keys of its members ([D5 §3.7](D5-consolidation-identity-confidence.md#37-identity-alternatives)) |
| Method config | `cfg` | method name, method version, canonical params |

Statement and local-entity keys are anchored by locators, not by segment keys, so they hold across
every rendition of the document whose generated locators agree: a content-preserving ingest change
moves no key, and an edit that shifts offsets elsewhere on the page moves none of the other
blocks' keys. What an edit can move is stated in §10.3 (P0CL-01; operator, 2026-10-28).
> Decision: [ADR-0019](../adr/0019-identity-follows-content.md)
> Status: **Proposed** (2026-10-28); property tests (two content-identical renditions from two
> adapter configurations give identical claim keys; an edit inside one paragraph that leaves every
> block's opening words unchanged leaves the other statements' keys unchanged) belong to
> foundations (phase 0)

**The key scheme.** The rules that turn parts into keys (the canonical forms of §6.2 and §7, the
key roles of §5.2, label normalization, the parts listed above and `canonical_json`) form a
numbered **key scheme**, declared in the `core` model as `ci:key_scheme: N` and carried by the
compiled `KeySchema`. The scheme is recorded **beside** keys, never hashed into them: each run
records the scheme of its keys ([D3 §4](D3-database.md#4-ops-methods-policies-runs-and-tasks)),
and each judgment target records the scheme of the key it names
([D5 §7.3](D5-consolidation-identity-confidence.md#73-carrying-judgments-across-runs)). Keys are
compared only within one scheme, or through the carry-over map below. A scheme number inside every
key would move every key on any scheme change, even one that changes no output for most inputs,
and orphan every judgment and cross-run diff.

- **Conformance vectors pin values, per scheme.** Each scheme has a conformance vector:
  hand-authored inputs (values of every range form, condition trees, entities with identity,
  statements on a small rendition, an external reference) with their expected keys pinned,
  computed from hand-written parts independently of the key function. A change to any output fails
  the vector until the scheme moves.
- **Fixtures still compare equalities.** Fixture tests compare key equalities, never key values, so
  a fixture never pins a hash and never breaks on a sanctioned scheme change; only the vector of
  the scheme in force pins values.
- **A scheme change ships a carry-over map** (old key → new key; translation T8 of the target
  model), computed by keying the stored authored inputs (§10.3) under both schemes. A key whose
  input is unavailable is reported, never guessed. Cross-run comparisons, carried judgments and
  reference-run key reuse go through the map when the schemes differ. A scheme change is a
  key-bearing schema change (ADR-0022): a new scheme number, a new vector and the map together.
> Decision: [ADR-0023](../adr/0023-declared-identity.md)
> Status: **Proposed** (2026-10-28); scheme 1 is frozen with conformance vector v1 once the token
> form is final (`s5.keys-property`) and the declared specifications are built (foundations F2d,
> F2e); how the outgoing scheme's functions stay callable for the map is probe Q-6

**Symbols and labels in keys.** A symbol enters a key in its token form (§6.2), and a symbol
that is a lone control word drops its backslash (`\mu` is `mu`), the form symbol-map keys use
(§6.1). Labels enter through **label normalization**, one generic core function used by keys,
by matching and by canonical-label choice: NFC and collapsed whitespace with the class label's
declared case policy (§6.2; casefolded under `fold`, kept under `preserve`), leading articles
removed, the class's head words removed and the pack's rewrites applied
([D5 §3.3](D5-consolidation-identity-confidence.md#33-global-entities) point 5). The articles,
head words and rewrites are pack data (the `aliases:` section of `methods.yaml`,
[D2 §12.1](D2-schema-and-guidelines.md#121-methodsyaml)), so core names no domain word and a
second domain normalizes through its own declarations.
> Status: **Proposed** (2026-10-28)

A supposition recorded as a context premise (D2 §7.3, statement kind `assumption`) whose
sentences fall inside another statement's anchor segment is that statement: its claims join that
statement, and no second statement is keyed. Statement kind is a field (§4.1), not identity.

> Status: **Proposed** (2026-10-28, design owner's review B3). The previous rule, keying by the
> smallest segment covering the anchor, is measured below; S6 recomputes the S0 figures under this
> rule.

A key is computed when an entity is first created. A global entity that consolidation links
to an entity of the run's reference run keeps that entity's key, so keys are stable across runs;
the reference run is recorded on the run when it is created and never changes
([D3 §4](D3-database.md#4-ops-methods-policies-runs-and-tasks) `ops.run.reference_run_id`), so
consolidation never reads the live promoted pointer (P0CL-05). Until the phase 2 identity gate,
linking reuses the reference run's keys but not its canonical labels
([D5 §3.3](D5-consolidation-identity-confidence.md#33-global-entities); P0CL-10; operator,
2026-10-28). A statement's `kind` and label are fields chosen by consolidation, not identity.

> Status: **Measured** on the S0 passes (2026-10-28): with the earliest rules (sorted anchor keys;
> label always in the key) 21 of 70 aligned claim pairs had equal claim keys; with the covering-
> segment statement key and the label rule 48 did, and the rest are real differences (../design_review/evidence/2026-10-28_design-spikes/results/s0/key_variants/, record s0.agreement-ir2).
> Under the ADR-0019 statement key (anchor locator plus first-sentence ordinal) 51 of the 70 pairs
> have equal claim keys with the label rule; 3 of the rest differ only by one statement-segmentation
> disagreement (U6), the others by the fact itself (record `s6.keys`, 2026-10-28).

**Identity qualifiers** are those whose qualifier specification (§5.2) gives them the `identity`
role, or whose role condition holds; the compiled `KeySchema` is the one list, and this section
restates none of it. For the core qualifiers that is `modality`, `polarity`, canonical
`conditions`, `valid_time` and the attributed entity under an `attribution_identifying` modality;
for a pack, the qualifiers it declares `identity` (for example `param_values`). Evidence,
confidence and attribution phrasing are not part of the key, nor are `meaning`-role qualifiers;
candidates whose keys agree but which disagree on a `meaning`-role qualifier become alternatives
(§5.2, D5 §5.3), each keyed with its disagreeing values as in the table above (P0CL-06; operator,
2026-10-28). Symbol bindings (§6.1) are outside the key as well,
because formulas key by token form, and they carry meaning too: candidates with equal keys and
different bindings become alternatives in the same way.
> Decision: [ADR-0023](../adr/0023-declared-identity.md)
> Status: **Proposed** (2026-10-28), bindings and the declared roles alike

Group keys carry their own prefixes (`alt`, `idg`), so a group key in a task's `unit_key` or a
judgment's target is never mistaken for a claim or entity key.
> Status: **Proposed** (2026-10-28)

### 10.2 Run scoping

Entities, claims and claim links are **materialized per run** and immutable once the run
finishes. A key identifies the same meaning across runs, which is how runs are compared,
judgments carried forward and claims diffed. Observations belong to tasks; a task reused from
cache in a later run contributes its existing observations, so unchanged work is never repeated
([D6 §4](D6-orchestration-metrics-policies.md#4-caching-and-reuse)).

The project records one **promoted run**. "Current knowledge" means the promoted run's claims. A
run records the run promoted when it is created as its **reference run** (§10.1); the first run
has none (bootstrap).

### 10.3 Stability limits

Keys are stable only within these stated limits; anything else that moves a key is a defect:

- **Entity resolution.** Keys of global entities depend on the canonical label consolidation
  selects; a resolution change that merges two entities changes a key.
- **Locator regeneration.** Keys anchored by locators move when a locator does: an edit to a
  block's id or opening words moves the keys anchored there; because a generated prefix is the
  shortest unique one, an edit can also lengthen or shorten the prefix of another block of the
  same kind on the page, moving its keys; and new original bytes are a new document (§3.1), whose
  key every locator carries.
- **The first-sentence ordinal within an anchor.** A statement key holds the ordinal of its first
  sentence within its anchor (§10.1), so inserting a sentence before it in that anchor, or
  re-segmenting an earlier sentence there, moves that statement's key and the keys of the later
  statements in the same anchor, and no other statement's key (DA-014).
- **External-reference resolution.** A claim that cites an `ExternalReference` (§4.4) is re-keyed
  to the resolved statement when consolidation resolves the reference.
- **Key-derivation changes.** A change to a canonical form, a key role, a case policy, label
  normalization or the parts of §10.1 is handled only through a new key scheme with its carry-over
  map (§10.1), never as a silent change to keys under the scheme in force.

Segment keys and spans move with any content change, which is why nothing that must outlive a
rendition holds them.
> Decision: [ADR-0023](../adr/0023-declared-identity.md)
> Status: **Proposed** (2026-10-28); a test that shows the ordinal shift belongs to foundations
> (F2d)

Goldens therefore never reference run keys: they carry their own local references and are
aligned structurally ([D7 §5](D7-evaluation-goldens-outer-loop.md#5-alignment-and-scoring)). An
authored batch, whether a golden pass, a fixture or an agent proposal, is kept in the
model-facing form in which it was written (D2 §7.3), with its **citation frame**: each sentence
id it cites (`sN`, or `cN` of the standing context) mapped to that sentence's locator (§3.4) and
text. The authored batch and its frame are the authority; the stored form (offsets and segment
keys) is derived from them on each rendition by the production quote cascade
([D4 §4.3](D4-method-catalog.md#43-output-form-and-post-processing)). A frame resolves on a
rendition when every locator selects one sentence whose text equals the recorded text; a golden
unit whose frame does not resolve on a run's rendition is stale until it is re-located, else
re-authored ([D7 §3.5](D7-evaluation-goldens-outer-loop.md#35-staleness-and-re-authoring))
(P0CL-03; operator, 2026-10-28).
> Decision: [ADR-0019](../adr/0019-identity-follows-content.md)
> Status: **Proposed** (2026-10-28)

The citation frame and the stored items are **core shapes**, the same for every domain. A frame
maps each cited sentence id to `{locator, text}`. A stored item is one element of the stored-form
batch (an entity, statement, claim, alternative or unsupported item, D2 §7.3) with its offsets
and segment keys on one rendition, as golden items (D3 `eval.golden_item`) and stored proposals
(D3 §6.2 `claim_proposal`) hold them. A pack's compiled batch schema types only what a predicate
contributes inside an item (its object and qualifiers) and the enum of entity classes; the frame
model and the generic item models are domain-free, reading only schema facts, and their owner in
the build is foundations, beside the keys.

**One owner of reference checks per context.** References are typed by kind (entity, statement,
claim): a local ref when authored, a key once stored.

- For **batches**, `validate` owns the reference and type checks: its batch checks, the entity-type
  side table (D2 §7.3) among them, refuse a batch reference to an unknown or wrong-kind item
  ([D4 §4.3](D4-method-catalog.md#43-output-form-and-post-processing),
  [D5 §1](D5-consolidation-identity-confidence.md)).
- For **pool candidates**, the keying resolver owns kind refusals: its per-kind lookups refuse a
  reference of the wrong kind with a typed drop code, and the dropped claim is counted.

No other component repeats either check.
> Status: **Tested** for the generic item models and the side table (S4, 2026-10-28, record
> `s4.batch-validation`: per-predicate branches over domain-free item models validate the 135 listed
> batches in both forms, and the side table, reading only the pack's schema facts, catches every
> seeded reference error); **Proposed** for the frame model, which S4 did not build, and for the
> single ownership of reference checks, which the side table's result does not establish
> (2026-10-28; alignment review R04, RC19)

Because an entity item is generic, the decoding form does not tie an entity's `scope` or identity
slots to its `type`: a model can emit a global `RandomVariable`, which only the side table refuses
after decoding. Per-class entity branches (one `entities[]` branch per class, with its scope and
identity typed by `type`) would let the decoder refuse it; they are not built, and are added if S3
shows models emitting class and scope mismatches.
> Status: **Proposed** (2026-10-28; S4 follow-up)

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
| INV-06 | A claim whose modality is `premise_forming` (core: `supposed`) is referenced by at least one condition or has a `scope` qualifier |
| INV-07 | `derived` claims have at least one `derived_from` link; `agent_asserted` claims never appear in a corpus run |
| INV-08 | Condition trees reference only claims in the same run |
| INV-09 | A claim with a `phrase` or `unsupported` condition leaf, or one that cites an unresolved `ExternalReference` (§4.4), is not reported as unconditional |
| INV-10 | Spans lie within their rendition's canonical text and their text equals the substring |

An invariant that a proposal can break is handled before anything is written: the offending item
is dropped with a counted reason, or rejected by a core rule. A `premise_forming` claim that breaks INV-06
is rejected at submission, so its author repairs the batch (D4 §4.3, D5 §8).
> Status: **Proposed** (2026-10-28)

## 12. Worked example in brief

From [trace unit T3](trace.md#t3-normal-affine-transformation), Siegrist *Normal*, unit `rel1`:
"Suppose that X is normally distributed with mean μ and variance σ². If a ∈ ℝ and b ∈ ℝ ∖ {0},
then a + bX is normally distributed with mean a + bμ and variance b²σ²."

| Ref | Claim | Modality | Conditions |
|---|---|---|---|
| C1 | `X` `has_distribution` Normal, `param_values {mean: μ, variance: σ²}` | supposed | — |
| C2 | `Y` `defined_as` `a + b X` | defined | `and(member(a, ℝ), member(b, ℝ∖{0}))` |
| C3 | `Y` `has_distribution` Normal, `param_values {mean: a + bμ, variance: b²σ²}` | asserted | `and(claim C1, member(a, ℝ), member(b, ℝ∖{0}))` |

`X` and `Y` are local `RandomVariable` entities scoped to the unit; C1 is the premise and C3 the
conclusion of statement `S1` (kind `theorem`); the proof in `<details>` is statement `S2` with a
claim `S2 proves S1`. C2 carries the restrictions stated with it on its own symbols, and no
`claim` node: a formula claim holds by stipulation (D2 guideline §10.7, rules 2–3). In C3, `μ` binds `param_of C1 mean` and `σ` binds `param_expr_of C1
variance`. The standard deviation `|b|σ` is a `derived` claim, never stated as `bσ`.

## 13. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D1-1 | Is spaCy sentence segmentation reliable on math-dense paragraphs, or should sentences be split with math spans masked? | Spike S1. **Answered** (2026-10-28): not on raw text (boundary F1 0.80, most false splits inside math), nor with an opaque mask (0.70); reliable with each inline formula merged into one token before the parser (b′, F1 1.00 on an 85-block gold two markers produced identically), adopted in [D4 M03](D4-method-catalog.md#m03-segmentsentences). **Measured** ([s1.sentence-gold](../design_review/evidence/2026-10-28_design-spikes/records/s1.sentence-gold.json)) |
| OPEN-D1-2 | Do variable scopes need a `section` extent in practice, or does `statement` scope plus "Suppose again" resolution suffice? | Spike S0 reference annotations; **answered by S0** (2026-10-28): yes; T1's "In this section", T2's "Suppose again" and U12 are section-scoped in every pass, and M13 reproduces them with section-wide and reopen binders (D4 M13) |
| OPEN-D1-3 | Should `FamilyParameter` identity use role names or source symbols when a source names no role ("parameters μ and σ")? Current proposal: canonical name = role if stated, else symbol; later `parameter_role` claims add roles | Spike S0, D2 review; **answered by S0** (2026-10-28): the role word when the unit states one, else the symbol (guideline v1 §10.4, D2); reworded 2026-10-28 to the phrase that first names the parameter (design owner's review B2), so names hold across units; parameterizations are OPEN-D2-18; confirmed at the next guideline-revision check (D7 §2) |
| OPEN-D1-4 | Is `section` the right scope extent for Siegrist's page-level standing assumptions (the lead-in "we fixed random variable Z")? | Spike S0; **answered by S0** (2026-10-28): `section`, under nested h3/h4 synthesis; `document` was never needed |
| OPEN-D1-5 | References outside the batch ("the last result", "definition [1]", author `[n]` links): a value `{t: "extref", target}` whose target is a locator (§3.4) or an author link target, usable as a `refers_to`/`follows_from` object, a `claim` node target and a binding target; consolidation resolves it to a key and reports unresolved ones; INV-09 counts a claim with an unresolved external premise as conditional (S0 gap RG-1, rank 1). Until then such references are `unsupported` | **Closed** (2026-10-28) by the domain-model alignment review's RC11 (operator, 2026-10-28): not a value but a typed `ExternalReference` node (§4.4), authored as D2 §7.3's `outside` statement item with a descriptor, keyed `xrf` (§10.1), resolved by consolidation with a `resolves_to` relation, and served as conditional while unresolved (INV-09); such references are no longer `unsupported`. Built by foundations F2e and consolidation C1 |
| OPEN-D1-6 | A `bound` binding kind for symbols bound inside a formula (Σ, ∏, ∫, set-builder), excluded from completeness counts (S0 gap RG-3) | D1 §6.1 and `BindKind` in core.yaml, next schema revision |
| OPEN-D1-7 | `param_of` targeting a premise claim other than `has_distribution` (a mean stated by `mean_value`, RG-5). Any predicate whose pack declares `ci:param_map` is now a target (§6.1, 2026-10-28); a parameter value stated as a claim's object rather than as a map entry remains open | Next schema revision |
| OPEN-D1-8 | An extent covering a run of sibling statements (RG-6) | Next schema revision |

## Production-efficiency target

**Proposed (accepted target,2026-10-30).** Symbol-role declarations carry scoped authority independently of consolidated entity attachment. Token keys remain independent of physical recognizers; source occurrences retain rendition custody and exact offsets.

> Decision: [ADR-0035](../adr/0035-model-governed-analysis.md)
