# Source decomposition and HTML interpretation

**PP-02/03 implemented and scoped Tested · 2026-10-30.** Unqualified future target claims remain **Proposed**. This supporting plan develops
[PP-02](../parsing-pipeline_2026-10-30.md#PP-02) and
[PP-03](../parsing-pipeline_2026-10-30.md#PP-03); the coordinator owns execution state,
finding/opportunity dispositions, shared decisions and assembled acceptance. This document is
implementation guidance, not a second progress ledger. Authoring it changes no production contract.

## Purpose and boundary

Make the retained original and the whole canonical representation inspectable as complete,
categorized source partitions, and explain their transformations through explicit mappings.
Keep html5lib's HTML5 tree construction through lxml as the structural baseline. Original syntax,
repaired structure and canonical reading order are distinct products; none can reconstruct the
others in general. This is the foundation for source explanations, finer text/TeX inspection and
later queries that must distinguish a source statement from an adapter's repair or projection.

This plan consumes [review O01/O02/O05/O06/O07](../../functional_reviews/parsing-pipeline_2026-10-30.md)
and the [connected target §§2–5](../../functional_reviews/parsing-pipeline_2026-10-30_target-model.md).
It supplies source products to [text and mathematical interpretation](text-and-mathematical-interpretation.md).
PP-01 owns definitions and enforcement contracts; PP-04 owns durable layout, native constraints
and migrations; PP-07 owns query/graph/extraction views; PP-08 owns execution/lifetime;
PP-09 owns publication/read selection; PP-10 owns assembled migration and adoption. Product names below express meaning, not a
requirement for one table, class, task or process per concept.

## Current baseline and foundation assessment

Source inspected at `b3a8313c984a5a0be41b25eea832e74fa822b469` on 2026-10-30. The
[product manifest](../../../python/corpus-structure/pyproject.toml) pins html5lib 1.1,
lxml 6.1.3, cssselect2 0.10.1 and regex 2026.9.29. Candidate Parsel, Trafilatura and extruct
mechanisms in the review are not selected product dependencies. No dependency move is necessary
merely to match a guide's version label.

The HTML adapter in this historical baseline was retired by the PDF plan. Recover its source with
`git show 7e6289a:python/corpus-structure/src/corpus_structure/ingest/html.py`; this does not
reactivate the old producer.

| Existing owner | Preserve and extend |
|---|---|
| `ingest/html.py` (archived at `7e6289a`), `parse`, `build_rendition_with_elements`, `_Walker`, `_serialize` | One stateful `html5parser.HTMLParser(namespaceHTMLElements=False)` per document; `document_fromstring(..., guess_charset=False)`; effective encoding, parser errors and data-loss warnings; source-profile roles; canonical text, segments, author markup and sentences. |
| [`ingest/profile.py`](../../../python/corpus-structure/src/corpus_structure/ingest/profile.py), `compile_profile` | Generated SourceProfile vocabulary validation and one compiled cssselect2 matcher. Preserve actual matcher tuple handling and pseudo-element refusal. |
| [`ingest/macros.py`](../../../python/corpus-structure/src/corpus_structure/ingest/macros.py), `read_macros`; `html._macro_table` | Macro semantics already exist. The reader drops token offsets, and `_macro_table` joins DOM `itertext`; neither supplies definition custody. PP-05 extends this producer using PP-03 mappings. |
| [`core/evidence.py`](../../../python/corpus-structure/src/corpus_structure/core/evidence.py) | Recursive Segment validation, containment, NFC canonical text and rendition-bound range identity remain useful. An overlapping provenance structure need not fit the Segment containment tree. |
| [`ingest/sentences.py`](../../../python/corpus-structure/src/corpus_structure/ingest/sentences.py), `TextLayout`; [`semantic/text_layouts.py`](../../../python/corpus-structure/src/corpus_structure/semantic/text_layouts.py) | Reuse layouts as block/token projections. Their following-space flags and coarse math/reference atoms do not give every canonical whitespace or separator a component range. |
| [`semantic/operations.py`](../../../python/corpus-structure/src/corpus_structure/semantic/operations.py), `BoundReader.text_layouts` | Reuse producing-task selection and `reused_task_id` resolution. Multiple candidate producing builds refuse; no implicit latest-build rule. |

[D1 §3.1](../../design/D1-knowledge-representation.md#31-document-rendition-and-canonical-text),
[D4 M01](../../design/D4-method-catalog.md#m01-ingesthtml) and
[D3 structured source artifacts](../../design/D3-database.md#structured-source-token-artifacts)
explain the current contracts. ADR-0019 content identity includes canonical text, the full segment
tree (parse state/reason, attributes and sentences included) and effective recorded macro table;
parser diagnostics belong to builds. Existing `original_path` plus content hash retains bytes but
does not establish complete source decomposition or source-to-canonical mappings. PP-00 must route
the multi-representation extension of D1's canonical-only offset wording before adoption.

The focused foundation judgment is to extend these owners rather than introduce another ingest
service or universal AST. Keep source-profile meaning authoritative while making consequential
`TAG_KIND`, transparent/block decisions, separators, normalization and atom handling discoverable
through PP-01's contracts. Qualitative execution fit favors an immutable input buffer with ranges,
one profile preparation and one HTML5 structural parse. A separate lexical pass can be justified
because it supplies fidelity that DOM serialization cannot recover; its additional work is real.
Do not force every lexical component through a database call or keep lxml smart strings alive just
to retain offsets. No measured throughput or memory benefit follows from this assessment.

## Required products and preservation rules

1. **Original custody and representations.** Keep immutable bytes, media type, content hash and
   retrievable custody. Declare byte offsets separately from code-point offsets. A decoded source
   representation identifies effective encoding, decoder/replacement policy, newline treatment,
   producing build and any encoding reparse. Retain undecodable bytes with their category and
   outcome even if no complete decoded text is available. Never publish replacement-decoded text
   as exact bytes.
2. **Complete partitions.** Original bytes, successfully decoded source and the entire canonical
   text each have their own declared complete lexical partition: ordered half-open extents in
   one named representation, no gaps/overlap, original spelling recoverable by slicing. Preserve
   tags, delimiters, attribute names/values and spelling, comments, doctypes, punctuation,
   whitespace, raw-text contents, unknown/malformed fragments and excluded material. Partition
   categories describe lexical evidence, not resolved document meaning. A fallback unknown
   fragment is explicit; labeling an entire page unknown cannot satisfy the promised supported
   lexical distinctions. Empty input has an explicitly complete empty partition.
3. **HTML structure.** Preserve html5lib's repaired native tree and expose typed structural
   occurrences/relationships where consumers need them. Implied `tbody` has synthetic origin;
   foster-parented text can change order; duplicate lexical attributes remain even when one DOM
   attribute survives. Tree-builder clones and adoption-agency moves must not silently share one
   invented source occurrence. Structure completeness and positional provenance are independent.
4. **Canonical projection.** Keep complete canonical ranges for text, math/reference atoms,
   whitespace, block/list/table separators and synthetic markers. A synthetic separator has a
   target extent and producing rule, not a fabricated original span. A source exclusion has a
   source extent and profile/rule reason even without a target extent. Compatible TextLayouts and
   Segment views derive from, or are emitted alongside, this coverage under one coordinate owner.
5. **Transformation mappings.** Ordered source/target extent sets permit many-to-many relations
   among named representations. Carry the producing operation, recipe and mapping kind: exact
   copy, decoded equivalent, normalized, reordered, excluded, derived or synthetic. Fidelity and
   coverage/availability are separate fields. Character references, CRLF, Unicode normalization
   and whitespace collapse are not necessarily one-to-one. Unknown origin is unavailable, never
   exact. Composite structures may overlap components without breaking the lexical partition.

A source explanation must be able to traverse canonical sentence → canonical component extents
→ transformation → decoded/raw extents and exclusion/repair decisions, returning explicit missing
mapping coverage where appropriate. It must never search the serialized tree for a matching
substring to manufacture that chain.

Decomposition/mapping identity is build/product identity linked to a rendition. Two builds with
the same complete rendition content can have different source custody and mapping products.
Retain document/rendition/segment/build distinctions; do not attach a mutable parser-specific map
to the deduplicated rendition. A changed canonical value, segment tree or macro table follows
existing new-rendition/anchor rules rather than rewriting historical anchors.

## Native mechanisms and consequential limits

The review's [full-guide table](../../functional_reviews/parsing-pipeline_2026-10-30.md#library-mechanisms-and-full-guide-dispositions)
is the research input. Context7 was consulted during plan authoring on 2026-10-30; it confirms the
tokenizer position gap, but tagged source governs the pinned implementation. These are selected
mechanisms or bounded candidates, not claims of assembled support.

| Mechanism | Planned use, limits and decision route |
|---|---|
| html5lib 1.1 `HTMLParser`, lxml tree builder | Preserve HTML5 semantics including omitted tags and error recovery. `getTreeWalker` and serializer filters can implement structural projections; they cannot recover original lexical custody. Serializer filters alter the derived view only. [Parser APIs](https://html5lib.readthedocs.io/en/latest/html5lib.html), [tagged parser](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/html5parser.py). |
| html5lib `_inputstream`, `_tokenizer.emitCurrentToken`, tree-builder lineage | PP-02 investigates maintainable source tracking across decoding, CRLF normalization, replacement, lookahead/reconsume, encoding restart, normalization/deduplication of token attributes, synthetic nodes, cloning and relocation. Stream position at emission or a custom TreeBuilder alone cannot supply exact extents. [Input stream](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/_inputstream.py), [tokenizer](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/_tokenizer.py), [lxml builder](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/treebuilders/etree_lxml.py). |
| lxml 6.1.3 native elements and compiled `etree.XPath` | Preserve native traversal and compiled repeated queries with deliberate namespaces. Smart-string parent/text/tail/attribute origins can help tie a projection to structure; `sourceline` and smart-string origins are not exact ranges. Disable smart strings for scalar extraction where tree retention is unnecessary. [HTML5 composition](https://lxml.de/html5parser.html), [XPath](https://lxml.de/xpathxslt.html). |
| lxml `iterparse` / parser targets; XSLT, XML validators, objectify | Streaming is conditional: HTML5 repair can require context and moving nodes, so early subtree disposal cannot be presumed valid. XML validation, XSLT and objectify are useful for separately selected XML/transform contracts, not substitutes for HTML5 or the domain model. No second XML object model is planned. |
| cssselect2 0.10.1 `compile_selector_list`, `Matcher`, element wrappers | Prepare role selectors once per valid profile; keep role decisions and conflicts attributed. Preserve namespace behavior and the existing explicit pseudo-element refusal. Another CSS facade is not provenance. [Native API](https://doc.courtbouillon.org/cssselect2/stable/api_reference.html). |
| Parsel / cssselect | Chained CSS/XPath, JSON and JMESPath remain candidates for an actual extraction-view consumer in PP-07. Their convenience alone does not justify replacing current matcher dispatch or adding a mandatory pass. |
| regex 2026.9.29 | Retain bounded delimiters/lexical matching, Unicode semantics and named literal lists in owned regions. Capture histories/`spans` and `\G` are candidates for contiguous recognized regions; recursion/fuzzy regex cannot replace HTML5 tree construction or assert exact source mappings from repaired text. |
| Trafilatura `bare_extraction`, `extract_metadata` | Optional derived article/metadata views under PP-07, never the full source authority. Preserve heuristic attribution, exclusions and failure separately from empty content. Do not make whole-page article extraction a prerequisite for lexical capture. [Documentation](https://trafilatura.readthedocs.io/). |
| extruct `extract(..., syntaxes=...)`, `return_html_node=True` | Conditional publisher-declared JSON-LD/Microdata/RDFa/OpenGraph/Microformats observations under PP-07. Limit syntaxes to demand, retain per-syntax errors, and qualify base-URL/parsed-tree behavior. HTML node return provides Microdata origins only; Microformats needs raw input. A returned DOM node is not byte provenance; declarations are not independently verified knowledge. [Upstream API](https://github.com/scrapinghub/extruct). |

PP-02 must distinguish a library supporting complete lexical capture from one supporting enough
tree-construction lineage. Pairing two libraries is viable only with an explicit bridge that
qualifies differences in encoding, tokenization and HTML5 repair; matching node spelling is not
that bridge. The [bounded PP-02 investigation](../../design_review/evidence/2026-10-30_parsing-source-provenance/README.md)
selects instrumentation of the pinned native tokenizer/tree builder. Its result establishes
positive seams, independently from the producer qualification below.

### Selected native composition — 2026-10-30

**Implemented and scoped Tested (2026-10-30).** The adapter injects an owned tokenizer
subclass through `HTMLParser._parse`, observes the upstream emission loop and tracks stream
`char`/`charsUntil`/`unget` consumption. Tokenizer state implementations and HTML5 tree-construction
algorithms remain upstream. Pre-emission attributes preserve duplicates before native first-value
selection. Per-operation lxml builder subclasses carry occurrence and text/tail contribution
identity through insertion, cloning and reparenting. A wrapper around
`InTableTextPhase.flushCharacters` supplies ordered original token identities across its joined
buffer; the current token alone is insufficient. No global monkeypatch is selected.

Decoder contribution groups and newline preprocessing connect the original byte representation
to the native normalized decoded representation. Encoding restarts discard abandoned sidecars.
The canonical producer emits projection contributions during its existing whitespace/NFC and
serialization operations; synthetic profile markers and separators retain producing rules.
Private-hook review belongs to the html5lib upgrade responsibility, including the stream/emission
loop, lxml node mutation methods and table-text phase. Library pins and archived implementation
inputs bind the selected mechanism. Probe traces are diagnostic evidence; production uses merged
runs and immutable buffers rather than retaining an event or database row per character.

The investigation's nine cases do not establish complete lexical distinctions or full origin
coverage. Producer tests and native publication must qualify the actual products. Unknown origin
remains unknown; normalization or decoding cannot be relabelled as an exact byte copy.

## Execution packages

<a id="PP-02"></a>

### PP-02 — Decide the HTML source-location realization

**Prerequisite:** [PP-01](../parsing-pipeline_2026-10-30.md#PP-01) supplies draft representation,
component, mapping, capability and outcome contracts sufficient to compare candidates. It need
not have completed production enforcement. PP-00 supplies the approved fidelity scope and the
decision route. Investigate before PP-03 commits a physical adapter or promises exact mappings.

Compare three composed routes: a maintained html5lib source-location extension/instrumentation;
an established independent lexical frontend composed with html5lib repair; and a precisely
declared exact-mapping subset while retaining full source partitions and explicit unmapped
structure. The third route is a support capability candidate, not authorization to narrow the
operator's full original-plus-canonical target. A novel handwritten HTML parser is not the
default escape from unsupported library behavior.

Read the candidate's versioned source at the operations that lose origin; use small executable
cases only where source inspection does not settle behavior. The bounded case set covers
multibyte text, BOM/encoding declaration and restart, CRLF, replacement decoding, character
references, duplicate/mixed-case attributes and quoting, comments/doctypes, raw script/style,
omitted `tbody`, foster parenting, formatting clones, malformed/unclosed markup, excluded
navigation/macros, and a canonical separator/marker with no original bytes. Expected extents
must be hand-established from retained input and independent HTML5 expectations where needed,
not reconstructed by the same candidate serializer. Broaden only on an unresolved mechanism,
not to chase a corpus score.

The investigation exits with one actionable decision account under the existing evidence route:
selected/versioned mechanism and owned maintenance seam; supported categories and coordinate
mapping; encoding restart handling; exact/partial/unavailable structural mapping capability;
native tree compatibility; dependencies and changes to PP-01/PP-04/PP-05. If private APIs are
needed, name the narrow hooks and source-version checks required when upgrading. PP-00 routes
the consequential choice to enduring authority. No implementation is accepted from a favorable
API example alone.

If no maintainable route supplies a required guarantee, record the missing mechanism, retain
the original full target, and block PP-03's dependent capability or the affected exact consumer.
Permissible partial products must have an explicit partial contract and cannot close complete
provenance acceptance. Seek an explicit scope decision through PP-00 if one is needed; never
convert an unresolved feasibility question into an unnoticed new target. The investigation can
finish with that decision while the series still has an open delivery obligation.

<a id="PP-03"></a>

### PP-03 — Implement complete source/canonical capture and mappings

**Prerequisites:** PP-02's selected decision and [PP-01](../parsing-pipeline_2026-10-30.md#PP-01)'s
enforced construction/validation contracts for the products being emitted. PP-04's agreed storage
contract is needed before durable wiring; a pure producer can be implemented first. PP-08's owned
runtime and PP-09 admission/publication are required before making new products externally
available. A documented contract is not a working prerequisite.

1. Extend the source adapter around `parse`/`build_rendition_with_elements`, preserving current
   profile applicability refusal and HTML5 parser options. Produce original/decoded lexical
   capture under the selected frontend, including effective encoding and restart outcome. Keep
   source custody even when decoding or structure recognition fails. Establish one validation
   boundary for complete partition construction through PP-01; downstream projection does not
   rescan every component to reprove immutable coverage.
2. Carry qualified origin handles through repaired structure without exposing private html5lib
   token dictionaries as public contracts. Retain original lexical attributes and discarded
   material independently of surviving DOM properties. Distinguish exact source correspondence,
   a structural association and unavailable origin in both producers and consumers.
3. Make canonical serialization emit components and mappings at the actual transformation:
   normalization, whitespace collapse, exclusion, reading-order movement, reference/quote/list
   insertions, block/list/table separators and author markup. Avoid a later search/alignment pass
   that guesses provenance. Keep the entire canonical input covered, including material outside
   sentence-split blocks. Reuse one text buffer; store extents rather than repeated substrings.
4. Emit existing content/Segment/markup/TextLayout views compatibly where meaning is unchanged.
   When a change moves content, macro meaning or segmentation, deliberately version the recipe
   and create new content/anchor identities. Make macro-source structural handles and decoded
   ranges available to PP-05; preserve the fact that a macro block can be excluded from canonical
   reading content without losing its source custody.
5. Integrate PP-04 build-bound persistence and PP-09 protected publication with an immutable
   product manifest. Reader selection pins document, source build, rendition and product.
   Reused tasks resolve the original producer; two candidate builds refuse without an explicit
   selection. Historical builds lacking the product remain explicit unavailable/cold-rebuild
   cases under their admitted recipe, never silently relabeled current complete products.
6. Move consumers with changed inputs in the same coherent contribution: ingest/sentences,
   source profiles and author-markup outputs locally; PP-05 macro/text use and PP-07 extraction
   views through their owned interfaces; source frames/packets, quote placement, queries/exports
   and evaluation through PP-09's read contract and PP-10's assembled migration. Do not leave a new representation field that old consumers
   interpret as a canonical offset. Retire replaced duplicate scans and provenance guesses once
   all actual consumers have moved, retaining historically addressed artifacts and migrations.

Logical operations can be fused in one native pass where that preserves contracts. Large excluded
blocks still require lexical custody but should not force article extraction, spaCy preparation,
graph materialization or mathematical interpretation. Keep native tree lifetime operation-owned;
pass immutable products across workers, not live lxml elements or smart strings. Cancellation
must settle through PP-08 and cannot publish an unmarked prefix as complete input coverage.

## Acceptance and integration evidence

During execution, use focused tests of the changed pure producer, profile and stored-product
contracts; defer the integrated campaign to the coordinator's completed-scope boundary. Relevant
existing test homes are `python/corpus-structure/tests/ingest/test_html.py`,
`tests/core/test_tex.py` and `tests/semantic/test_stored_text_layouts.py` beneath the same product
project. New regression cases belong beside the responsible behavior. A future focused command
is `uv run pytest python/corpus-structure/tests/ingest/test_html.py
python/corpus-structure/tests/semantic/test_stored_text_layouts.py`; select additional cases from
the actual edits. Probes, if necessary, belong in dated `docs/design_review/evidence/` folders
with the repository's records/finalization route. No product tests were run for plan authoring.

Completion evidence must independently establish these behaviors:

- Every byte and every code point of each declared complete representation appears exactly once
  in ordered lexical extents; slicing reproduces the original representation. Check supported
  category boundaries independently, including whitespace/separators, unknowns and excluded
  material. Round-trip reconstruction alone cannot establish correct categorization.
- html5lib structure/canonical behavior remains correct for the repair and source-profile cases;
  synthetic nodes have no fabricated original tags, duplicate attributes remain inspectable,
  and decoding/normalization/reordering mappings retain their declared cardinality and kind.
- Two identical words or identical canonical renditions with different builds do not collapse
  source occurrences or select the wrong map. Missing or competing builds produce the declared
  unavailable/refusal outcome. Historical anchor identity and custody remain recoverable.
- A canonical sentence and a macro definition can be explained back to original input where
  the adapter declares support. A consumer requiring exact provenance refuses partial coverage;
  weaker consumers can inspect a truthfully qualified product without upgrading it to complete.
- A failed/cancelled operation leaves no complete published product; retries use pinned source
  and release context. Durable readback, publication fences and consumer journeys are completed
  with PP-04/PP-08/PP-09, not claimed by local pure-function tests.

Expected functional benefit is explainability and reusable source capture. Any quantitative
speed/storage claim needs a separate representative measurement; repeated parsing eliminated by
an actual migrated consumer may be described qualitatively. Existing historical receipts retain
their dates and scope. Plan-authoring checks are read-only source/document inspection;
implementation, probes and product qualification are **not_run** here. The coordinator records
current outcomes and open prerequisites at the linked PP owners.

## Delivered source-product scope — 2026-10-30

PP-02's selected seams now drive the actual producer and PP-04 storage/read path. Native
lexical distinctions include duplicate/empty/unclosed attributes, quoted/unquoted values,
comments, doctypes, raw text and malformed fragments; HTML5 ASCII whitespace preserves NBSP
in unquoted values. Native selected codec identity, actual decoded-content agreement, byte
contribution groups and newline handling preserve representation-qualified source custody.
The final tree carries qualified node names, structural/text/attribute relationships and ordered
text-slot contributions. Canonical whitespace/NFC, exclusions and separators emit mappings at
the transformation. Decoded NUL uses binary-safe UTF-8 transport.

All 78 current pages pass complete original/decoded/canonical partition and rooted
`canonical_output` provenance contracts, alongside independent category/extent and native repair
cases. Complete transformed lineage is not exact copying or universal repair attribution. Unknown
origin stays partial. Actual M01 reads retained PostgreSQL bytes, requires the admitted source
operations before computation and publishes the product atomically with the rendition. Reused
reads resolve the producer; historical unavailable and competing/corrupt products retain their
explicit outcomes. Source acquisition remains durable on later parsing failure.

[Implementation evidence](../../design_review/evidence/2026-10-30_parsing-source-provenance/implementation.md)
and the [coordinator execution](../parsing-pipeline_2026-10-30.md#pp0004-execution)
record native migration/publication/concurrency, affected consumer checks, typing and original
failed/repaired invocations. These supersede the plan-authoring `not_run` boundary for the
implemented source scope only. Future prose/TeX/math, extraction views, broader runtime/adoption
and quantitative benefits remain with PP-05–PP-10.
