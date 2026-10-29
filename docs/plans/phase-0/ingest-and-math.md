# Phase 0: ingest and math

**Status:** Proposed (2026-10-28); P0-I-0 built and reviewed on 2026-10-28 (coordinator §11, IR
rows), the rest not built. Part of the [phase 0 series](../phase-0_2026-10-28.md), which owns shared
decisions, contracts, the dependency graph and build findings.
**Revised:** 2026-10-28, for the [domain-model alignment review](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md) and its
[target model](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md) ("TM"), following coordinator decisions 1, 19 and 23 and §9.2's RC12: I0's
literal kind subsets give way to generated member-property sets ([DA-003](../../design_review/audit/semantic-model-and-authority.md#da-003)), migrated by
P0-M-1 with the locator contract unchanged; I1a's source profiles are declared in `system`, typed
against core vocabulary and checked against the run's schema version ([DA-010](../../design_review/audit/semantic-model-and-authority.md#da-010)), and M01
emits `DelimitingStatus`. Prerequisites follow [coordinator §7](../phase-0_2026-10-28.md#7-dependencies-and-readiness).

This document builds the locator function, HTML ingest (M01 with M03, and M02) and the math
methods (the one grammar, M09, M11's grammar part, M13 and the standing context). Packages are
P0-I-0, P0-I-1a, P0-I-1b, P0-I-2a and P0-I-2b (coordinator §7).

## 1. What this document builds

**Responsibilities.**

- **Locators** (P0-I-0): the one locator contract of
  [D1 §3.4](../../design/D1-knowledge-representation.md#34-locators), as a `core` function over
  foundations' evidence types. It parses a locator, generates one for a segment, resolves one on a
  rendition, refuses ambiguous ones, and gives the structured key form and the unit key. It also
  lists a rendition's annotation units with their unit keys.
- **Ingest** (P0-I-1a functions, P0-I-1b methods): the Siegrist source profile
  (`sources/siegrist.yaml`), its loader into the profile class `system` declares, and the profile's
  check against a schema version. M01 on html5lib turns a document's bytes into the
  rendition content of [D1 §3.1–§3.2](../../design/D1-knowledge-representation.md#31-document-rendition-and-canonical-text):
  canonical text, segments, the macro table and author markup. M03 adds sentence segments
  (variant b′) as a step of M01's task. M02 writes character and math features. P0-I-1b wires them
  as methods and adds `ci ingest`.
- **Math** (P0-I-2a functions, P0-I-2b methods): the one math grammar of
  [ADR-0012](../../adr/0012-math-grammar-token-keys.md), which every reader of math in the product
  uses. It feeds three methods, each run once per rendition: M11's grammar part (validation, kind
  detection, parse status), M09 (symbol occurrences and math-internal relations) and M13 (binding
  sites and scopes). The standing-context function assembles a unit's `cN` sentences from M13's
  output.

**Where responsibility ends.**

- Model and projections (P0-M-1) owns the vocabularies and their member properties (segment kinds
  with `annotation_unit`, `section_like` and the rest, statement kinds with `claim_bearing`,
  `DelimitingStatus`, `ParseOutcome`, `MarkupKind`) and the source-profile class in `system`. This
  document reads the generated sets and never restates a kind list (DA-003).
- Foundations (P0-F-2a) owns the evidence types (`Segment`, `RenditionContent`), the content
  digest and the rendition and segment keys. It also owns
  `core/tex.py`: the TeX tokenizer, the drop list, macro expansion and the token form that keys
  use. This document produces rendition content and consumes those functions. It never computes a
  digest or a key itself.
- The repository (P0-F-4) is the only writer of evidence and observation rows. M01 hands it
  rendition content and observation drafts.
- Orchestration (P0-O-0, P0-O-1, P0-O-2) owns the method contract, the registry, tasks, reuse,
  stages, slices and when a locator is resolved for a run. It refuses, at run start, a run whose
  source profile fails this document's schema-version check (P0-O-1; DA-010). This document gives
  each method its
  `input_digest` and `Config`, and gives the resolver orchestration calls.
- The agent interface owns packet assembly, the quote cascade and citation-frame resolution. It
  calls the standing-context function and the locator function; it does not reimplement them.
- Consolidation owns the claim-level use of the grammar at finalize: parsing claim values once per
  pass and handing (status, kind, symbols) to the rule views as data
  ([D5 §8.2](../../design/D5-consolidation-identity-confidence.md#82-rule-context)). `validate`
  never imports the grammar.
- Phase 0 consolidation takes local scopes from the proposals, not from M13
  ([D5 §11](../../design/D5-consolidation-identity-confidence.md#11-by-phase)). M13's only phase 0
  consumer is the standing context of agent and golden packets.

**Change scenarios that explain the boundaries.** They show where a later change goes; none adds
scope here.

- **A second source** (the NIST pages, a business corpus) is a new `sources/<profile>.yaml`. The
  adapter reads no source fact from code (D4 M01, profile vocabulary). Keys Siegrist does not use
  (`section_source: layout`, `layout`) are accepted by the profile model but refused as "not
  implemented" until a source needs them, so a profile never silently loses structure.
- **Email thread segment kinds** come from a new adapter (`ingest.email`). It produces the same
  `RenditionContent` with the email kinds of D1 §3.2, whose roles are member properties in the model
  (`email_message` carrying `annotation_unit` and `container`; TM §11). Locators, annotation units,
  M03, M09, M11 and M13 read those properties and change nothing.
- **A second domain pack over Siegrist** names `source_profile: siegrist`. The adapter
  configuration is then equal, so the builds and renditions are shared. A profile hint naming a
  statement kind that the run's schema version lacks is refused at run start, never carried as an
  unknown string (DA-010).
- **A table with quantities** is already segmented (`table`, `table_row`, `table_cell`, with cell
  text in canonical text). M03 splits table cells, and M12 (phase 1) reads them.
- **Phase 1 additions:**
  - M13 becomes consolidation's scope source, and the paragraph extent is decided then (§3.9).
  - M11 adds SymPy conversion; the `sympy` field is stored, keys unchanged.
  - M02 adds token counts.
  - M04 embeds segment rows, which survive content-preserving re-ingest because renditions are
    content-addressed.
- **Routine changes in phase 0:**
  - A spaCy bump or an adapter port that leaves every sentence unchanged adds a build to the
    existing rendition (ADR-0019).
  - A grammar extension never moves a key, because keys use the token form (D1 §6.2). It can
    change a span's parse kind, and through M13 a unit's standing context and so its packet hash;
    the agent is then asked again for that unit. That is a real change in what the agent sees, not
    churn.

## 2. Contracts

### 2.1 Consumed

| Contract | Owner (design · this series) | Used by |
|---|---|---|
| Canonical JSON; `Segment` and `RenditionContent`; the content digest; `doc`, `ren`, `seg` and `cfg` keys | D1 §3.2, §10.1; ADR-0019 · foundations P0-F-2a | P0-I-0 (types), P0-I-1a (produces the content), P0-I-2a |
| Generated vocabularies with member-property sets (`core/_model/`, `core/vocab.py`): `SegmentKind` with `annotation_unit`, `top_level_annotation_unit`, `section_like`, `label`, `statement_anchor` and `search_block`; `StatementKind` with `claim_bearing`; `DelimitingStatus` (merging `evidence.ParseStatus` and `vocab.SegmentParseStatus`); `ParseOutcome` (renamed from `ParseStatus`); `MarkupKind` | ADR-0020; TM §11; coordinator decisions 1, 23 · [model and projections](model-and-projections.md) P0-M-1 | P0-I-0 (annotation units, uncovered blocks), P0-I-1a (kinds, statuses, hints, markup), P0-I-2a (`ParseOutcome`) |
| The source-profile class in `system`, typed against core vocabulary; change records that list the profiles a change affects | ADR-0022; [RC12](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#rc12), [R06](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r06); D4 M01 and D6 §7.2 as amended at P0-D-2 · P0-M-1, P0-M-4 | P0-I-1a |
| A schema version's statement-kind members (core and pack-scoped) | D2 §2, §3.3 · schema and rules P0-S-1 | P0-I-1a's profile check |
| `core/tex.py`: the TeX tokenizer, the drop list (every `%ignore` literal of SymPy 1.14's `latex.lark` plus the sizing commands), macro expansion over a rendition's table with the pack map as fallback, and the token form | D1 §6.2; ADR-0012; coordinator decision 13 · P0-F-2a, frozen after `s5.keys-property` | P0-I-1a (macro reader), P0-I-2a (grammar `%ignore` check, property test, symbol names) |
| D1 value model, with `parse` a `ParseOutcome` ∈ {`ok`, `partial`, `ambiguous`, `failed`}; the symbol key rule (token form; a lone control word without its backslash) | D1 §6.1–§6.2 · P0-F-2b | P0-I-2a (M11 values, M09 symbol names) |
| Observation payloads: `author_markup` with `synthesize`; `mention` with optional `math`; `relation`; `value` with optional `math_kind`; `scope` with optional `reopens` | [D3 §6.2](../../design/D3-database.md#62-observation-payloads-by-kind), as amended 2026-10-28 · foundations | P0-I-1b, P0-I-2b |
| The write by content (insert the rendition on `(document_id, content_digest)`, write segments only when it is new, a build row either way), bulk observation COPY, measurement rows carrying `task_id` | [D3 §5](../../design/D3-database.md#5-kb-evidence-observations-entities-and-claims), §6; ADR-0019 · P0-F-4 | P0-I-1b, P0-I-2b |
| Method-contract types (`Method`, `UnitView`, `UnitResult`, `ObservationDraft`, `Digest`, `Resources`, `MethodContext`) and the registry interface | [D4 §1](../../design/D4-method-catalog.md#1-the-method-contract) · orchestration P0-O-0 | P0-I-1b, P0-I-2b |
| The registry's resolution of named configurations (a named source profile and `segment.sentences/<name>` resolved into content before hashing); tasks, stages (`ingest`, `normalize`, `scope`) and reuse by digest; run kind `ingest`; documents registered by `ci project init` from the profile's index; CPU workers that run a method on the main thread of a single-threaded process | D4 §1; [D6 §2–§4](../../design/D6-orchestration-metrics-policies.md#2-the-stage-graph-and-run-lifecycle); D3 §8 · P0-O-1 | P0-I-1b, P0-I-2b |
| The Typer app and its registration; the shared conftest and per-session database | D9 §1, §4 · P0-F-1 | `ci ingest`; every database test |
| Thin fixtures extracted from the frozen spike renditions (trace segments) | D9 §4 · foundations P0-F-3 | P0-I-1a tests |
| Spike results: S5-A records `s5.macros`, `s5.coverage`, `s5.keys-property` and its extended `extension.lark`; S5-B `s5.symbols` and `s5.scope` as revision inputs, not prerequisites | [S5 plan](../design-spikes-s0-s1/S5-math-verification.md) §4, §5 · design-spikes series | P0-I-2a |

### 2.2 Produced

| Contract | Design owner | What this document implements | Consumers |
|---|---|---|---|
| Locators: parse, generate, resolve, refuse; the structured key form; unit keys; annotation units by member property | D1 §3.4, §10.1; ADR-0019; coordinator decision 14 | P0-I-0 (`core/locators.py`; its kind subsets migrated by P0-M-1) | foundations (statement and local-entity keys, fixture frames); orchestration (`ops.task.unit_key`, slices and the `{golden_set}` scope at run start); agent interface (`unit_ref`, frame generation and resolution); evaluation (golden unit keys, sampling order, re-location); consolidation (anchors, `synthesize` objects, `extref` when OPEN-D1-5 is decided); queries (`statement(locator)`, evidence locators) |
| Source profiles: the loader into the `system` class, `root`, `index`, `language`; the check against a schema version | D4 M01 (profile vocabulary); [D2 §2](../../design/D2-schema-and-guidelines.md#2-domain-pack-layout), [§12.1](../../design/D2-schema-and-guidelines.md#121-methodsyaml); ADR-0022 | P0-I-1a (`ingest/profile.py`, `sources/siegrist.yaml`) | orchestration (project init reads `index` and `root`; run start calls the check, P0-O-1); consolidation (the toy pack's `sources/toy.yaml`) |
| Rendition content, builds, segments with `DelimitingStatus` and typed hints, sentences, macro tables, author markup, parse detail | D1 §3.1–§3.2; [D4 M01](../../design/D4-method-catalog.md#m01-ingesthtml), [M03](../../design/D4-method-catalog.md#m03-segmentsentences) | P0-I-1a, P0-I-1b | everything downstream: the quote cascade (sentences, macro table), packets, consolidation (markup, `synthesize`, statement-kind hints), policies (`unit.claim_bearing`, `unit.statement_kind`), BM25 (`ts_config`) |
| M02 features | [D4 M02](../../design/D4-method-catalog.md#m02-profilesegments), [D6 §6](../../design/D6-orchestration-metrics-policies.md#6-metrics) | P0-I-1a, P0-I-1b | policies (unit context), reports |
| `ci ingest` | D8 §4; coordinator decision 10 | P0-I-1b | the operator; qualification |
| The math grammar: `parse`, the tree printer, the SymPy conversion, occurrences | D1 §6.2; [D4 M11](../../design/D4-method-catalog.md#m11-normalizeformula); ADR-0012 | P0-I-2a (`methods/math/`) | consolidation (finalize: values parsed under their slot kind); evaluation (SymPy for value equivalence, D7 §5.3); M09, M11, M13 |
| M11 values, M09 mentions and relations, M13 scopes per rendition | [D4 §3](../../design/D4-method-catalog.md#3-catalog) unit of work; [M09](../../design/D4-method-catalog.md#m09-extractmath), M11, [M13](../../design/D4-method-catalog.md#m13-resolvesymbol_scope) | P0-I-2a, P0-I-2b | metrics (`math.parse_rate`); the standing context |
| The standing-context function | [D4 §4.1](../../design/D4-method-catalog.md#41-the-packet); D7 §3.2 | P0-I-2a (`methods/math/context.py`) | agent interface (M24 packets, golden packets) |

## 3. Design of the parts

### 3.1 Locators (P0-I-0)

The function operates on F2a's `RenditionContent`, so it is a pure function of a rendition's
segments and canonical text. Generated locators are therefore identical on content-identical
renditions (D1 §3.4).

- **Parsing.** A locator is `page`, `page#id`, `page@kind:prefix` or `page@kind[n]:prefix`.
  `page` runs to the first `#` or `@`. Everything after `:` is the prefix, verbatim, so a prefix
  may contain `#`, `@`, `:` and LaTeX. `kind` is a D1 §3.2 kind or the short forms `u` and `p`.
  Anything else is a parse error naming the position.
- **Pages.** A page is the document's `source_uri` with the source profile's `root` removed
  (`siegrist_random/random/special/Normal.html` → `special/Normal.html`), per D1 §3.4 and D2 §12.1
  as amended on 2026-10-28. The function maps in both directions given the profile. Project init
  refuses two documents whose pages collide.
- **Comparison.** Prefixes and segment texts are compared after collapsing whitespace runs to one
  space and trimming, on NFC canonical text with LaTeX verbatim. A resolver prefix need not end on
  a word boundary; hand-written slice locators often do not.
- **Resolver.**
  - `#id` selects the segment whose `attrs.id` is `id`, of any kind, when exactly one segment of
    the page carries it.
  - `@kind:` selects among segments of that kind, paragraphs inside units included.
  - D1 §3.4 governs these forms. The spike resolver restricted `@p:` to paragraphs outside units
    and `#id` to units; that restriction is not ported.
  - The 13 `trace` and `core12` locators of D2 §12.2 each select exactly one segment under D1's
    forms. This is Tested on the stored S1 renditions (read-only check, 2026-10-28), and the test
    repeats it on the production renditions.
  - A locator that selects nothing, several without an ordinal, or fewer than its ordinal raises
    `LocatorRefused` with the candidates (locator and opening words of each). It never resolves to
    a nearest match. What a refusal means is the caller's decision (D1 §3.4).
- **Generator.**
  - A segment's generated locator is `page#id` when its id is unique on the page.
  - Otherwise it is `@kind:` with the shortest whole-word prefix of its collapsed text that no
    other segment of that kind starts with.
  - When another segment of the kind starts with this segment's whole text, no prefix is unique.
    The generator then takes the shortest prefix that selects only that group and adds the
    segment's ordinal among them (`@p[2]:Proof.`).
  - Generated string forms use `u` and `p` for units and paragraphs, as slices do, and full names
    for every other kind. The structured form always spells the kind in full (D1 §3.4).
- **Index.** `LocatorIndex(rendition)` is built once per rendition and use. Per kind, a sorted
  list of word sequences gives each segment's shortest unique prefix in one pass over its
  neighbours. The index answers generate and resolve without rescanning the page, so consolidation
  (an anchor per statement) and evaluation (a locator per cited sentence) do one build per page.
  A page has a few hundred segments of a kind (the four spike pages hold 412 text blocks; S1), so
  per-page work is small. The point of the index is not to repeat it per call.
- **Structured form.** `{"doc": <document key>, "id": …}` or `{"doc": …, "kind": <full name>,
  "prefix": …[, "n": …]}`. F2b hashes it; this document never hashes.
- **Annotation units.** `annotation_units(rendition)` returns, in document order, every segment
  whose kind carries `annotation_unit`, and every one whose kind carries `top_level_annotation_unit`
  and whose ancestors' kinds all carry `section_like`, each with its unit key (the string form of its
  generated locator). For Siegrist these are D1 §3.4's `unit` segments and paragraphs outside units.
  Orchestration's policy chains, evaluation's sampler and the packet assembler all take units from
  this one function.
  - The sets are M1's generated member properties (TM §11; DA-003). P0-I-0 was built with literal
    kind subsets; P0-M-1 migrates them to the generated sets in the same package as `vocab.py`, and
    keys' `statement_anchor` the same way. The locator contract and every generated locator are
    unchanged, and the IR regression tests stay as they are.
  - **Open question for the design owner:** D1 §3.4 and D2 §10.2 define a unit as a `unit`
    segment or a paragraph outside units, so a top-level list, table or figure outside any unit
    belongs to none. On the seven S0/S0-R2 pages that is two lists on Normal (lists of related
    distributions), one on ChiSquare and one figure caption on Gamma.
  - **Proposed answer:** keep D1's definition for phase 0. The function also returns these blocks
    as `uncovered` (outside every unit, of a kind carrying neither `section_like` nor `label`), so
    coverage can name the text no unit holds.

**Failure behaviour.** Parse errors and refusals are typed exceptions carrying the input and the
candidates. Generation cannot fail: an ordinal always separates identical texts.

### 3.2 Source profiles (P0-I-1a)

`ingest/profile.py` loads a profile into the source-profile class that `system` declares (P0-M-1;
coordinator decision 19; [RC12](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#rc12), [R06](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r06)): a frozen Pydantic model of the D4 M01
profile vocabulary, `extra="forbid"`, whose domain-bearing fields are typed by the generated
vocabularies, not strings. Statement-kind hints are `StatementKind` members, block and section roles
`SegmentKind` members, `synthesize.predicate` a core predicate such as `core:proves`, and markup a
`MarkupKind`. Keeping the field set equal to the `system` class until a generated form exists is
model and projections' interim guard (P0-M-1).

The hints stay in the profile: they are facts about one source's conventions over core vocabulary,
and moving them into the pack would split one convention across every pack that shares the source
(the review's refinement of DA-010). The class has these additions agreed on 2026-10-28:

- `root`: the directory pages are relative to;
- `index`: the corpus index that `ci project init` registers documents from;
- `language`: a text-search configuration (default `english`), which ingest writes into
  `kb.segment.ts_config`. It is outside the content digest (D3 §5).

`applies_to` stays relative to the corpus root, as D2 §12.1 shows. Every path it matches must lie
under `root`.

- **Loading.**
  - `load_profile(name)` reads `sources/<name>.yaml` and validates it against the class; an unknown
    core name (a misspelt kind, `Proof` for `proof`) is refused here.
  - Each selector is compiled with `cssselect2.compile_selector_list`; a `SelectorError` rejects
    the whole profile.
  - The profile is registered once, as role payloads in one `cssselect2.Matcher`
    ([text-math note](../../design_review/evidence/2026-10-28_library-text-math/README.md) §1.3).
  - The resolved profile, `version` included, is what enters `ingest.html`'s configuration hash
    (D4 M01). Orchestration's registry obtains it through M01's `Config`, which resolves
    `source_profile` by name.
- **XPath export.** The cssselect→XPath translation (`CSSSelector(css, translator="html").path`)
  appears only in a profile test that checks both engines select the same nodes. Production runs
  one engine.
- **The schema-version check.** `check_profile(profile, schema_version)` returns the profile's
  version-scoped names (statement kinds, pack-scoped kinds included) that the schema version's
  member rows lack, each with its field and name; static core names were checked at load. It is a
  pure function over the compiled schema version (P0-S-1). Orchestration calls it at run start and
  refuses the run on any result, naming the profile (P0-O-1). That is DA-010's closure: a profile
  naming an unknown kind is refused at run start. Change records list the profiles a schema change
  affects (P0-M-4).
- **`sources/siegrist.yaml`** is D2 §12.1's profile with `root: siegrist_random/random`, `index`,
  `language: english` and `details_kinds.synthesize`. Its other values are those S1 tested on 78
  pages (record `s1.corpus`).

### 3.3 M01 (P0-I-1a)

`ingest/html.py` exposes `build_rendition(raw_bytes, profile, sentences_cfg) → IngestResult`. The
result holds:

- `RenditionContent`: canonical text, the segment tree with sentences, and the macro table;
- `author_markup` drafts;
- the page title;
- `parse_detail`.

It is pure: no database, no clock. Its steps:

1. **Parse.**
   - Create `html5parser.HTMLParser(namespaceHTMLElements=False)` fresh for each document; the
     parser is stateful.
   - Call `html5parser.document_fromstring(raw_bytes, guess_charset=False, parser=parser)` on the
     original bytes, so WHATWG sniffing applies and chardet stays out.
   - Run the parse inside `warnings.catch_warnings(record=True)` to count `DataLossWarning`s.
   - `parse_detail` records `parser.documentEncoding`, `parser.errors` as (line, column, code),
     and the data-loss count.
   - Entities are decoded by html5lib's tokenizer, so no second `html.unescape` runs. D4 M01's
     "Text" bullet names one; applied to parser output it would turn a literal `&lt;` written as
     `&amp;lt;` into `<`.
   - Evidence: html5lib is Tested on 78 pages (`s1.corpus-html5lib`), and the namespace flag and
     sniffing are Measured (text-math note §1.1).
2. **Roles.** One pass over `ElementWrapper.from_html_root(root).iter_subtree()` returns each
   element's role payloads with specificity and order.
   - Elements claimed by two exclusive roles are recorded as `role_conflicts` in `parse_detail`.
   - Excluded subtrees are recorded per rule (rule, tag, classes, characters) in `parse_detail`,
     never as segment attributes.
3. **Macros.**
   - The macro source (`div.latex`) is read with `core/tex.py`'s tokenizer.
   - The reader takes `\newcommand`, `\renewcommand` and `\providecommand`, each with an optional
     `*`, then the name, `[n]`, an optional default and the body, read as TeX reads arguments.
     `\DeclareMathOperator` is read as an operator.
   - The result is the rendition's macro table, in F2a's shape. It is content: canonical forms
     expand by it.
   - Evidence: the reader is Measured to add `\P` on the 22 pages whose `\renewcommand` the spike
     reader missed (text-math note L-04; S5's `s5.macros` confirms it on the corpus).
4. **Walk.** Blocks are emitted in reading order per D1 §3.1–§3.2:
   - block separators `\n\n`, list items `\n`, table cells `\t`;
   - whitespace collapsed outside math, math verbatim;
   - sections opened by the profile's heading selectors and nested by level;
   - text placed directly in a container becomes a paragraph with `attrs.orphan` and the
     container's kind;
   - the rendering conventions of the profile's `references`, `render` and `orphan_text`.
     `references.render: browser` writes `[n]` with `n` the referenced unit's ordinal, keeping the
     last of duplicate ids, as the page script does.
   - A non-unit `div` and `blockquote` are transparent: their blocks attach to the parent, and
     their direct text is an orphan paragraph. The spike's `division` and `block` kinds are not
     ported. A test asserts every emitted kind is a `SegmentKind` member.
   - No segment with empty text is emitted: an element whose collapsed text is empty yields no
     block. An empty segment's only locator is positional (`page@p[n]:`), which an insertion
     earlier on the page moves (IR-13, coordinator §11).
5. **Delimiting.**
   - One `regex` pattern is generated from the profile's delimiters and display environments:
     `(?V1)` explicit; the named lists `\L<opens>`, `\L<closes>`, `\L<delims>` and `\L<envs>`;
     `(*SKIP)(*F)` for `\\` and for the escaped form of any delimiter not starting with a
     backslash; a possessive body that stops at the next delimiter.
   - Each block runs `finditer(text, timeout=…)`. A `TimeoutError` makes the block's math
     `partial` with reason `delimiter scan timeout`.
   - An unclosed or wrongly closed span is `partial` with its reason, and a stray closer is
     recorded in `parse_detail`.
   - Segment status comes from delimiting alone (D1 §3.1) and is a `DelimitingStatus`, M1's one
     definition replacing `evidence.ParseStatus` and `vocab.SegmentParseStatus` (TM §11; DA-002);
     the formula outcome `ParseOutcome` is M11's, never a segment's. Evidence: Tested on 517 blocks
     (`s1.profile-delimiting`; text-math note L-05).
6. **Normalization.** NFC is applied chunk by chunk between math, markup and run boundaries, so
   every boundary offset stays exact even where NFC would change a length. That is the spike's
   method; on Siegrist no character changes (`s1.corpus`).
7. **Markup and hints.**
   - Author markup goes into segment `attrs`: element id, classes, `dfn` terms with offsets, link
     targets.
   - It is also emitted as `author_markup` drafts (D3 §6.2), each typed by `MarkupKind`.
   - A `details` block of a kind the profile's `details_kinds.synthesize` names carries
     `synthesize: {predicate, object, evidence}`. `object` is the enclosing unit (its segment key
     on this rendition, and its locator); `evidence` is the summary heading's span. Consolidation
     turns it into a claim without knowing the convention (D5 §3.5; coordinator decision 17).
   - Statement-kind hints, each a `StatementKind` member: a unit takes the hint of its first hinted
     block. A section hint (the
     innermost section whose title the profile names) takes precedence and keeps the block hint
     beside it.
   - `claim_bearing: false` is carried as a hint.
8. **Sentences** (M03, §3.4), then the content is complete and F2a can digest it.

**Diagnostics never enter attributes.** `sourceline`, parser errors, exclusions, anomalies and
orphan statistics live in the build's `parse_detail`. The content digest therefore covers whole
segments with no exclusion list (D1 §3.2 as amended 2026-10-28). The spike's `attrs.sid`, `tag`
and `sourceline` stamps are not ported.

**Failure behaviour.**

- An invalid profile is refused at load.
- A document the profile's `applies_to` does not match is refused. There is no profile-free
  fallback (D4 M01; trafilatura is Measured to drop headings and every `details` summary,
  `s1.trafilatura`).
- A parse exception fails the document's task with the error. Everything else is recorded and
  continues.

### 3.4 M03 inside M01's task (P0-I-1a)

M03 is a step of M01's task. The `ingest.html` configuration names `segment.sentences/<name>`, and
the registry resolves it into the same configuration hash as the profile. One
`method_config_id` therefore identifies the build, as `kb.rendition_build` and `kb.run_rendition`
require (D3 §5, §8).

- **Which text is split.** Leaf text blocks of kind `paragraph`, `list_item`, `table_cell` and
  `caption`.
- **The Doc.**
  - The prose between inline math spans and rendered reference markers is tokenized with
    `nlp.tokenizer`.
  - Each math span and each marker enters as one word, and
    `Doc(nlp.vocab, words=…, spaces=…)` reproduces the block text exactly.
  - Math tokens get `tag_ = "NNP"`.
  - `is_sent_start = False` is set on markers and on every token of a display formula after its
    first.
- **The pipeline.** `nlp.pipe(docs, batch_size=64, as_tuples=True)` runs with the model loaded
  once per process with `exclude=["ner", "lemmatizer"]`.
- **Sentence segments** are trimmed of surrounding whitespace and never cross their block.
- **Configuration.** The hash includes the spaCy version, the model package and version, and the
  exclusions (D4 M03). `en_core_web_sm` 3.8.0 is installed as a wheel by URL in
  `[tool.uv.sources]`.
- **Evidence.**
  - The words-and-spaces route is Tested on 412 blocks of the four spike pages, with sentence
    starts identical to the spike's b′ (text-math note L-08).
  - b′ boundary F1 is 1.00 on S1's gold (`s1.sentence-gold`).
  - The three S0-R2 pages (Pareto, ChiSquare, Weibull) were not covered by that comparison. The
    acceptance checks them, because fixture citation frames depend on their sentences.

### 3.5 M02 (P0-I-1a)

`ingest/profile_segments.py` computes, for every block segment, the D6 §6 features
`segment.chars`, `segment.math_share`, `segment.inline_math` and `segment.display_math`.

- Rows are written as `ops.measurement` with the task's `task_id`, so a reused M02 task's
  measurements are read through reuse like observations (D6 §6 as amended 2026-10-28).
- Token counts and `tokenizers` join in phase 1, with the served model's tokenizer: nothing in
  phase 0 reads them, and the agent tier's caps are characters (D4 §4.1).
- `unit.statement_kind` and `unit.claim_bearing` come from the hints in segment attributes, not
  from M02.

### 3.6 Method wiring and `ci ingest` (P0-I-1b)

| Method | Unit | `input_digest` | Writes |
|---|---|---|---|
| `ingest.html` (M01 with M03) | document | the document's content hash | the rendition by content, its build, `author_markup` observations |
| `profile.segments` (M02) | rendition | the rendition's content digest | measurements |

- **M01's write.** M01 computes the content, asks F2a for the digest, and calls the repository's
  write by content:
  - the rendition is inserted on conflict do nothing;
  - segments are written only when the rendition is new, with `ts_config` from the profile's
    `language`;
  - the build row records the configuration, the task and `parse_detail` either way (D3 §5).
- **A content-preserving change** therefore writes one build row and the task's `author_markup`
  observations, and no segments.
- **Processes.** Documents parallelize across processes, not threads: html5lib is pure Python and
  holds the GIL (D4 M01). M01 tasks declare CPU resources.
- **`ci ingest [--slice NAME | PATH…]`** calls orchestration's pack-version upsert, creates a run
  of kind `ingest` through orchestration, and reports per document: rendition reused or new, segment
  counts, partial spans and parse errors. A slice selects its pages (D8 §4).

### 3.7 The math grammar (P0-I-2a)

`methods/math/` is the port of the spike's `mathgrammar/`, taken after S5-A has extended it
(coordinator decision 12). Its parts:

- **Assembly.** The grammar text is:
  - SymPy 1.14's shipped `latex.lark`, read unedited from the installed package;
  - the extension file from S5-A (`%extend`/`%override`, typed start symbols `formula`,
    `relation`, `member`, `set_expr`, `any_value`, sub- and superscripts as rules, set
    constructs);
  - `%ignore` lines generated from `core/tex.py`'s drop list;
  - a block generated from the rendition's macro classification (`GEN_SET`, `GEN_OP`,
    `GEN_STYLE`).

  **Building fails if any `%ignore` terminal of the assembled grammar is not on the drop list**
  (D1 §6.2).
- **Whole-name terminals.** An `edit_terminals` callback rewrites every control-word literal to
  end at `(?![A-Za-z])`, including the anonymous terminals of the shipped string `%ignore` lines.
  No `%override` can reach those.
  - Tested: `x \leftarrow y`, `A \leftrightarrow B` and `a \quadrant b` fail honestly as unknown
    commands, `x \rightarrow 0` parses `ok`, and no spike-page span changes (text-math note L-06).
  - The spike's regex-generated `%override` lines are not ported.
- **Construction.** `Lark(text, parser="earley", lexer="dynamic", ambiguity="explicit",
  propagate_positions=True, maybe_placeholders=False, keep_all_tokens=True, ordered_sets=True,
  start=[…])`.
  - One parser per macro classification, built lazily in a per-process dictionary. Earley parsers
    cannot be saved or pickled, and one builds in 0.05 s; there are 38 distinct classifications
    over 78 pages (Measured, L-06).
  - Macro classification reads macro bodies:
    - `\mathbb{R|N|Z|Q|C}` → set;
    - another `\mathbb{X}`, or `\text`/`\operatorname`/`\textrm`/`\mathrm` of two or more letters
      → operator;
    - a bare typeface wrapper → style;
    - anything else → not in the grammar.
- **`parse(latex, kind, macros, context) → MathResult`.**
  - `macros` is the merged table from `core/tex.py`.
  - `context` declares `functions` and `variables`.
  - The result holds the status (a `ParseOutcome`: `ok`, `partial` when only trailing `.,;` was dropped,
    `ambiguous`, `failed`), the detected kind, the tree, a reason with its category, the notes, and
    occurrences with offsets into the span.
- **Ambiguity** is resolved only from declared context. Six readings are settled:
  - application versus product decided by declared functions and variables;
  - a definition `g(x) = …` declares `g` a function;
  - a lone symbol under `any_value` is a formula;
  - a list before `\in` is a membership of each element;
  - a bare `(a, b)` under `any_value` is ambiguous;
  - readings with equal SymPy values collapse to the first, which `ordered_sets` makes stable.

  Anything else is `ambiguous`, never picked silently.
- **Failure categories.**
  - They are derived from the exception class (`UnexpectedCharacters`, `UnexpectedEOF`,
    `UnexpectedToken`), the TeX token at the error position (read with `core/tex.py`'s tokenizer)
    and the `allowed` set.
  - `UnexpectedInput.match_examples` is a last resort.
  - Transformer failures are unwrapped from `VisitError.orig_exc`.
- **Timeout.**
  - A `signal.setitimer` limit gives category `timeout`; the default is 2 s, set in M11's
    `Config`.
  - The API raises when called off a process's main thread. The spike's limit silently did
    nothing there.
  - So a misplaced caller fails loudly, and the MCP servers never import the module (coordinator
    decision 3).
  - Measured per span: median 41 ms, maximum 826 ms on a 1,532-span sample (L-06).
- **SymPy.** A subclass of `TransformToSymPyExpr` holds the extension rules' methods.
  - It raises `NotRepresentable` for products with a non-`Expr` operand, instead of taking
    SymPy's deprecated path.
  - The grammar's tests run with `-W error::sympy.utilities.exceptions.SymPyDeprecationWarning`.
  - `to_sympy(result)` is the conversion that evaluation's value equivalence uses in phase 0 and
    that M11 stores from phase 1.
  - The `pin-check` hold on SymPy 1.14.0 (`docs/pins.md`) extends to the product environment.
- **Tree printer.** It prints canonical LaTeX from a tree and serves only the property test.
  Keys come from F2a's token form, never from the tree.
- **Memo.** A bounded per-process memo keyed by (latex, kind, parser key, context) lets M09 and
  M11 share a parse when one process runs both. When they run in different processes the span is
  parsed twice. That cost recurs only when a rendition's content changes, because both are reused
  at rendition grain. If the S5 full run shows grammar time dominating the path from ingest to
  propose, M09 could instead read M11's observations.

**Execution fit.** The grammar is the dominant ingest-to-propose cost, so the design keeps its work
bounded:

- one task per rendition per method (D4 §3), reused unless content changes;
- parsers cached per process and per macro classification;
- workers are processes because of the timer;
- consolidation parses claim values once per pass, on its main thread.

### 3.8 M11's grammar part and M09 (P0-I-2a)

Both methods read every `math_inline` and `math_display` segment of a rendition.

- **The span.** The span's inner LaTeX starts after the opener's length plus leading whitespace.
  Occurrence offsets are shifted by exactly that, never found by searching the span for parsed
  text (D4 M09). The spike's `raw.find(inner)` is not ported.
- **M11** writes one `value` observation per span, parsed under `any_value`:
  - the D1 value with `t: set` for a set kind and `t: formula` otherwise;
  - `latex` verbatim;
  - `parse` (a `ParseOutcome`);
  - the free symbols, named by F2b's symbol rule, each `unresolved`, because binding is
    consolidation's (D5 §4);
  - no `sympy` in phase 0.

  Beside the value, the payload carries `math_kind` (`formula`, `relation`, `member`, `set`,
  `list`, or none when failed) and `parse_error` with the category.
- **M09** writes per span:
  - one `mention` per occurrence, with label `symbol`, `start`/`end` in canonical text,
    `math_ref` (the span's segment key) and `math: {name, base, sub, sup, constant,
    in_subscript_of}`. `name` is the token form of the occurrence, so matching across mentions
    agrees with keys.
  - `relation`s:
    - `in_set` (head: the element, tail: the set; every element of a list before `\in`);
    - `equals` (head: the left side);
    - `compares` (head: the left side of every other binary relation: order, `\ne`, `\sim`,
      `\approx`, `\to`, `\subset`).
  - Constants (the pack's `math.constants`) are marked, not dropped.
  - No notation-to-predicate mapping (`stat:has_distribution`) exists in phase 0: nothing consumes
    it, and no pack key declares it.
- **Order.** Observation ordinals are deterministic: by span start, then occurrence start.

### 3.9 M13 (P0-I-2a)

M13 reads the rendition's segments and sentences, M09's mentions and relations, and M11's
`math_kind` per span. It does not parse math (D4 M13 as amended 2026-10-28).

- **The Doc.** Per block, M13 builds the same words-and-spaces Doc as M03. Sentence starts are
  preset from the stored sentence segments (`True` at each start, `False` elsewhere), so the
  parser cannot disagree with the rendition's sentences.
- **Math tokens.** Each math token carries `Token._.math`, registered once per process behind
  `has_extension`. It holds the span's kind and its bound symbols:
  - a formula with one free, non-subscript occurrence and no `equals` binds that occurrence;
  - a list binds every occurrence;
  - a member binds its `in_set` heads;
  - an equation whose left side holds one occurrence binds it;
  - a relation binds its `compares` heads.

  These are the spike classifier's rules, now derived from M09's output.
- **Binding sites** come from patterns compiled at start-up from the pack's binder lexicon
  (D2 §12.1 `binders`):
  - `Matcher(nlp.vocab, validate=True)` for sentence-initial binders and for clause binders
    followed by a math token;
  - `PhraseMatcher(attr="LOWER")` for section-wide phrases, with patterns from
    `nlp.make_doc(phrase)`;
  - a reopen pattern bound to the binder's sentence:
    `[{"IS_SENT_START": True, "LOWER": {"IN": initial}}, {"OP": "{0,3}"}, {"LOWER": {"IN": reopen}}]`;
  - definitional equalities anywhere.

  `DependencyMatcher` is not used in phase 0. These refinements are Proposed (text-math note L-09).
- **Extents and assignment** (D4 M13 rules 1–3):
  - a site inside a unit binds to the unit, unless its sentence holds a section-wide phrase;
  - a site outside units binds from its position to the end of the enclosing section;
  - a reopen links to the symbol's previous section-level site;
  - every mention goes to the innermost site at or before it whose extent contains it; with none
    it is `unresolved`.
- **The `scope` payload** holds the mention, the binding site, the reopened site (`reopens`), the
  scope segment and the extent kind (`statement` or `section`). It also records the positions of
  the mention and the sites. Readers then never dereference a `mention_ref` across tasks, which a
  run deletion could leave dangling once M13 is reused over a fresh M09 task. Whether those
  positions get their own payload fields is foundations' call on D3 §6.2.

**The paragraph rule is omitted** (OPEN-D4-5, design-phase plan).

- D4 M13's "a standalone claim-bearing paragraph is a statement extent" came from the S0 probe
  (`code/s0e_m13_probe.py`, `--paragraph-statements`). The probe applied it only to the paragraphs
  of the sample's own units, so the 20 of 20 scopes of `s0.m13-probe-2` depend on the sample, not
  on the rendition.
- A read-only check of the spike code on 2026-10-28 ran `probe_page_patterns` and
  `s0r2_sample.context_for` three ways, with the stored renditions:
  - with the rule as the probe applied it: 20 of 20 scopes and 21 of 21 S0-R2 standing contexts,
    which reproduces both records;
  - without the rule: 18 of 20 scopes (U6's `X` and `Z` go to the section) and 21 of 21 contexts
    equal to `results/s0r2/sample.json`;
  - with the rule applied to every paragraph outside units: 19 of 20 scopes and 18 of 21 contexts
    (T2 loses both context sentences, U12 its one, H3 one of two).
- Phase 0 M13 therefore omits the rule. Its acceptance is 21 of 21 standing contexts, with 18 of
  20 scopes reported. The paragraph extent is decided in phase 1, when M13 becomes consolidation's
  scope source.
- The check ran from a session scratchpad script. It should become an evidence record in S5-B,
  where `s5.scope` re-runs the same three variants on the core, held-out and math-heavy units.

### 3.10 The standing context (P0-I-2a)

`standing_context(rendition, scopes, mentions, unit) → [ContextSentence]` is a pure function of
recorded inputs, as packet assembly requires (D4 §4.1; coordinator decision 5). Each
`ContextSentence` holds its `cN` id, the sentence segment, its generated locator and its text.
The locator and text are what the citation frame records for `cN` (D1 §10.3).

1. **Symbols.** For each symbol the unit uses (its non-constant, non-subscript mentions inside
   the unit), take the scope of its first mention inside the unit that is not `unresolved`.
2. **Context sentences.** If that binding site's sentence lies outside the unit, include it.
   Include the reopened site's sentence the same way.
3. **Filter.** Drop any sentence whose text equals one of the unit's sentences, and drop
   duplicates.
4. **Cap.** Keep the six latest in page order, then number them `c1…` in page order (D4 §4.1, as
   amended 2026-10-28). No S0-R2 unit has more than two.

Without M13 output the function returns nothing. This is the port of `s0r2_sample.context_for`.

## 4. Ports

| Spike module (`code/` in the [spike evidence](../../design_review/evidence/2026-10-28_design-spikes/README.md)) | Product module | Behaviour and tests kept | Not ported |
|---|---|---|---|
| `s1b_sample.py` `resolve`, `ws` | `core/locators.py` | Whitespace-collapsed prefix matching; the 13 slice locators | `@p:` restricted to paragraphs outside units, `#id` restricted to units |
| `s1_adapter.py`, `profile/siegrist.yaml` | `ingest/profile.py`, `ingest/html.py`, `sources/siegrist.yaml` | Roles by `Matcher`; exclusions recorded per rule; the walk and sectioning; orphan paragraphs; `[n]` numbering; `(a) ` markers; `<q>` quotes; summaries as headings; figure captions; unit and section hints; chunked NFC; the delimiter pattern and its reasons; S1's invariants and counts | The namespace-rewrite and comment-removal pass; the libxml2 path and the variant switches (`parser`, `unicode`, `math_whitespace`, `sections`); mixed `re`/`regex`; the pylatexenc `\newcommand`-only reader and `validate_span`; the XPath engine in production; `attrs.sid`, `tag` and `sourceline`; the configuration-hash rendition key; the `division` and `block` kinds |
| `s1_sentences.py` (`bp+c`) | `ingest/sentences.py` | b′ semantics: no start inside display math or at a marker; sentences within their block | The `retokenize` merge (replaced by the words-and-spaces Doc); pipelines P2–P4; masks; pylatexenc `latex2text` |
| `mathgrammar/` (`build`, `api`, `to_sympy`, the tree part of `printer`, `extension.lark` as S5-A leaves it) | `methods/math/grammar.py`, `transform.py`, `extension.lark` | `test_mathgrammar.py`: unedited shipped grammar; no source names in the extension; classification; parser cache; whole names; kinds; script structure; SymPy values; not-representable cases; ambiguity; definitions; intervals; collapse; lone symbols; occurrences; occurrences in a span | `whole_name_overrides()`; `tokens_canonical`, `_DROP` and `_TEX` (now F2a's `core/tex.py`); `canonical()` from the tree for keys; `raw.find(inner)`; the silent timeout off the main thread; the unbounded `_CACHE`; the hard-coded `CONSTANTS`; `bare_unit` (no phase 0 consumer); `coverage.py` (S5's instrument) |
| `m13_binders.py`; `s0e_m13_probe.py` (`probe_page_patterns`, `math_classifier`, `assign`) | `methods/math/scope.py` | The binder roles; extents; reopen of the previous section-level site; innermost assignment; the 20 annotated scopes as a reported reading | `phrase.split()` phrase patterns; "again" anywhere in the sentence; the pylatexenc `symbols()` engine; the paragraph rule over the sample's parts; binders parsed out of D2's markdown (`s0a_packets.BINDERS`, which no longer parses the current D2); the grammar call inside M13 |
| `s0r2_sample.py` `context_for` | `methods/math/context.py` | The context rule and its order; the 21 S0-R2 contexts | Truncation before the identity filter |

M02 has no spike module. Its features are S1's counts (`code/s1d_corpus.py`).

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case |
|---|---|---|---|---|
| P0-I-0 | Locators over F2a's types: parse, generate, resolve, refuse, structured form, unit keys, annotation units, `LocatorIndex`, pages from `root`. Built and reviewed 2026-10-28; P0-M-1 migrates its kind subsets to member properties (DA-003), with this acceptance unchanged | P0-F-2a | On a thin fixture of the four spike pages' segments (extracted from the frozen S1 renditions): the 13 D2 §12.2 locators resolve to one segment each under D1's forms, and generate → resolve returns every segment. Properties: content-identical renditions give identical locators; a structured form never holds a short kind; an edit after a block's generated prefix leaves every other block's locator unchanged | Two paragraphs where one's whole text opens the other (`Proof.` and `Proof. By induction…`): the shorter must get an ordinal over both, never a prefix that also selects the longer; a resolver that falls back to a near match on an edited page |
| P0-I-1a | The profile loader into the `system` class, typed against core vocabulary, and the schema-version check; `sources/siegrist.yaml`; M01 (emitting `DelimitingStatus`), M03, M02 as pure functions | P0-F-2a, P0-I-0, P0-M-1, P0-D-2 | On 78 pages (corpus-gated): S1's structural invariants; all 19,432 element texts equal an independent path; unit, definition-unit, `dfn`, `details` and display-math counts equal the index on 77 of 78; 8 `partial` math spans, each with its reason; 44 orphan runs; 51 figures. On the seven S0/S0-R2 pages: canonical text, segment kinds, offsets and tree, and sentences, equal the spike renditions. The macro table holds `\P` on the 22 `\renewcommand` pages. Locators round-trip on every segment of the 78 renditions. Two builds whose M03 configurations differ but give equal sentences have equal digests. The trace segment fixtures match. No segment has empty text (IR-13). Every segment status is a `DelimitingStatus` member and every hint a `StatementKind` member. A profile with an invalid selector, or naming an unknown core kind, is refused at load; one naming a kind the schema version lacks is reported by the check, which O1's run-start refusal consumes (DA-010) | An unclosed `<p>` before `<details>` (4 pages): html5lib closes the paragraph, where libxml2 nests the proof inside it; an inline formula straddling tokenizer boundaries (`mean\( \pm \)standard`) must stay one token whose text is the span; a hint spelled `Proof` loading as an unknown string that no policy ever matches |
| P0-I-1b | `ingest.html` and `profile.segments` as methods; the write by content; `ci ingest` | P0-O-0, P0-F-4, P0-O-1, P0-I-1a | `ci ingest --slice spike-pages` writes four renditions, their builds, segments, `author_markup` and measurements; a second run reuses every task; a run under a changed configuration with identical content adds build rows and writes no segment; a profile change that alters text adds a rendition beside the old one; `kb.run_rendition` selects each run's rendition | A content-identical rebuild that writes segments again (duplicate rows) or rewrites the existing rendition |
| P0-I-2a | Grammar, M11's grammar part, M09, M13 and the standing context as pure functions | P0-F-2b (with P0-F-2a's `core/tex.py`, frozen after `s5.keys-property`), P0-I-0, P0-I-1a; S5-A finished | The ported grammar tests; the `%ignore` build check; a call from a thread raises; a pathological formula returns `timeout` within its bound; the property test (§6) with every disagreement listed by cause, matching `s5.keys-property`; coverage reported per page, not a gate, beside `s5.coverage`; M09 offsets equal the source substring of every occurrence on the spike-page spans; the 21 S0-R2 standing contexts equal `sample.json` by sentence text and locator, except H3, which is expected at its corrected value (the spike's `context_for` re-found a binding site by its first 100 characters and took an earlier identical-prefix sentence; D4 M13's rules give 9504 and 11267; coordinator ruling, 2026-10-28); 18 of 20 annotated scopes reported | `x \leftarrow y` read as the product `xarrowy`, which would give M09 the mentions `a`, `r`, `o`, `w`; T2 ("Suppose again …") must yield both its context sentences |
| P0-I-2b | `normalize.formula` and `extract.math` (stage `normalize`) and `resolve.symbol_scope` (stage `scope`) as methods, one task per rendition | P0-O-0, P0-F-4, P0-O-1, P0-I-1b, P0-I-2a | On the spike pages a run writes one task per rendition and method; a rerun reuses them; a content-identical rendition reuses all three; M13's digest holds M09's and M11's payload hashes, so rerunning M09 with identical output leaves M13 reused; methods run on a worker's main thread | An M13 digest built from M09's task id, which would re-run M13 and every packet after an identical M09 rerun |

**P0-I-0.** No library beyond the standard library (`unicodedata`) and Pydantic for the locator
model. Evidence: `s1.adapter` (13 locators), `s1.rendition-identity` (the same spans under both
parsers).

**P0-I-1a.**

- Libraries:
  - `lxml.html.html5parser` with html5lib 1.1 and lxml 6.1.3;
  - the cssselect2 0.10.1 `Matcher` (cssselect 1.6.0 in the dev group, for the XPath export
    test only);
  - `regex` 2026.9.29 named lists, `(*SKIP)(*F)` and `timeout`;
  - spaCy 3.8.18 with `en_core_web_sm` 3.8.0;
  - PyYAML;
  - M1's generated vocabularies and the `system` profile class (no library of its own).
- Each is added pinned when the package uses it (D9 §2).
- Evidence: `s1.corpus`, `s1.corpus-html5lib`, `s1.rendition-identity`, `s1.profile-delimiting`,
  `s1.sentence-gold`, `s1.variants`, `s1.adapter`, `s1.trafilatura`, `s1.nist` (the vocabulary's
  non-Siegrist keys), and `s5.macros` for the reader.

**P0-I-1b.** Mechanisms are orchestration's and the repository's. Evidence: none beyond P0-I-1a.

**P0-I-2a.**

- Libraries:
  - Lark 1.3.1: `edit_terminals`, `ordered_sets`, Earley with explicit ambiguity,
    `propagate_positions`;
  - SymPy 1.14.0 (held), through the `TransformToSymPyExpr` subclass;
  - spaCy `Matcher` and `PhraseMatcher`;
  - `hypothesis.extra.lark.from_lark` in tests.
- Evidence: `s5.macros`, `s5.coverage`, `s5.keys-property` (S5-A); `s0.instruments`;
  `s0.m13-probe-2`; `s0r2.inputs` and `s0r2.scores` (the context rule). S5-B's `s5.symbols` and
  `s5.scope` revise M09 and M13 when they report, without blocking the package.

**P0-I-2b.** Mechanisms are orchestration's. Evidence: none of its own.

## 6. Tests

- **P0-I-0.** Unit tests on hand-built `RenditionContent` for every form and every refusal kind
  (none, several without an ordinal, fewer than the ordinal). Hypothesis properties over generated
  segment lists with repeated and prefix-related texts:
  - generation then resolution returns the segment;
  - an edit after a block's generated prefix leaves every other block's locator unchanged;
  - an edit inside a prefix changes at most the locators of same-kind blocks whose shortest prefix
    it touched, which is the limit D1 §10.3 states;
  - generated prefixes are whole words.

  The corpus round trip on the 78 renditions belongs to P0-I-1a's acceptance.
- **P0-I-1a.**
  - Profile tests: load, selector rejection, both engines agree per rule; an unknown core kind
    refused at load; `check_profile` against a hand-made schema version with a pack-scoped kind,
    reporting a kind it lacks and passing one it has.
  - Adapter tests on small HTML fixtures, one per D1 §3.1 convention: an empty `a.ref`, `<q>`,
    `ol.sub`, a `details` summary, orphan text, a bare `align`, each kind of unbalanced delimiter,
    a delimiter-scan timeout, `\renewcommand`, a non-unit `div`, and an empty element, which yields
    no segment (IR-13).
  - Corpus-gated tests on the 78 pages (skipped when `docs/statistics_corpus` is absent) check
    S1's figures.
  - The seven-page identity check compares against a thin fixture extracted once from the frozen
    spike renditions. It holds canonical-text hashes, segment tuples and sentence offsets, and
    names the records it came from. The comparison is independent of the production M01.
- **P0-I-1b.** Database tests on the shared per-session database: the write by content, reuse, a
  configuration change with equal content, and `ci ingest` through Typer's `CliRunner`.
- **P0-I-2a.**
  - **The ported grammar cases**, run with the SymPy deprecation warning as an error.
  - **The corpus layer of the property test** (D1 §6.2; D9 §4 "Math"). For every span the grammar
    reads on the gold pages, the tree printer equals F2a's token form, or the span is listed with
    its cause. A new disagreement fails the test.
  - **The generated layer.** `from_lark` draws strings from the assembled grammar, with explicit
    strategies for the macro terminals and for whole-name commands. The same property shrinks to a
    minimal formula. Drawing from a dynamic-lexer grammar with lookahead terminals is unexercised;
    if `from_lark` cannot drive it, the layer falls back to strategies built from the extension's
    terminals, and that is reported. The token form's metamorphic layer is foundations'.
  - **M09** offsets against the source substring.
  - **M13 and the standing context** against thin fixtures: the 20 annotated scopes from
    `results/s0/reference` and the 21 contexts from `results/s0r2/sample.json`, as sentence texts
    and locators.
- **P0-I-2b.** Database tests for task counts, reuse and the digest composition.

## 7. Indicative size

Budget 3,000 product lines (coordinator §8), tests excluded:

| Package | Lines |
|---|---|
| P0-I-0 | about 250 |
| P0-I-1a | about 1,250 (profile 200; M01 walk, serialization and markup 750; delimiting and macro reader 150; M03 150) |
| P0-I-1b | about 200 |
| P0-I-2a | about 1,150 (assembly and cache 150; parse, ambiguity, errors and occurrences 450; transformer 250; M09 and M11 100; M13 150; context 50) |
| P0-I-2b | about 150 |
| Total | about 3,000, with `extension.lark` (about 150 lines of grammar) counted apart as data |

The adapter and the grammar are the risk, as the coordinator says. Each is a rewrite against the
D4 cards, not a copy of the spike's structure.

## 8. Choices left to implementation

- Module names and splits inside `ingest/` and `methods/math/`. Whether M03 and M13 share one
  Doc-building helper (they should build identical Docs).
- `LocatorIndex`'s data structure.
- Parse and delimiter-scan timeout values, and the memo's size.
- How hints and `synthesize` are laid out inside segment attributes and payloads, within D3 §6.2.
- Which block kinds M02 measures beyond annotation units.
- Error-message wording for refusals, and the content of the `ci ingest` report.
- The ordering of `parse_detail` entries.
