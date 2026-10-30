# A domain-model-driven parsing pipeline

**Proposed · functional extension review · 2026-10-30.** Library-focused inquiry against source
`b402438c359edef1b30f43a2cd35e049b08f9d5f`; worktree initially clean. The
[target model](parsing-pipeline_2026-10-30_target-model.md) develops the recommended architecture.
This review extends [mathematical decomposition](symbolic-math-decomposition_2026-10-30.md)
to original HTML, structural documents, prose and their downstream consumers.

## Conclusion

Adopt complete source decomposition plus explicit transformation/interpretation relationships as
the foundation. Retain html5lib's HTML5 semantics through the existing lxml composition. Extend
the current LinkML/SQLAlchemy/PostgreSQL execution authority into discrete parsing contracts,
with native library adapters and demand-driven preparation. Use graph or nested object views
where their algorithms and access patterns help; neither becomes the domain authority.

The operator confirmed original markup/text **and** canonical representations as the fidelity
target. Each component needs a category and start/end range, including material excluded from
an interpretation. “Repair” below means HTML5 tree construction, including valid omitted tags
and recovery from malformed input. It does not mean changing source files or assuming they are
broken. The operator specifically favors html5lib to preserve that behavior; this review retains it.

The strongest new capabilities are inspectable complete decomposition, explainable transformations,
reusable context-bound interpretation, and explicit contracts governing the whole parsing path.
Changing parser libraries alone would not supply them. Exact source-to-repaired-DOM mapping is
not yet qualified; the review identifies the concrete missing mechanism instead of promising
that a wrapper or tokenizer offset solves it.

## Baseline and assessment method

Static inspection covered ingest, profiles, segmentation/token preparation, mathematical grammar,
transformation/preparation, scientific comparison, source projection, metadata/compiler contracts,
source frames and adjacent packet/evaluation obligations. Architecture owners D1–D8, ADR-0035,
current production-efficiency plans and the earlier math review establish existing commitments.
Review criteria are core 3.3, efficient-architecture guidance and applicable profile 1.4, selected
through [standard.toml](../design_review/design_principles/standard.toml). FP-04/05/07, DP-09/13–15
and H4/H6/H12/H15/H28 especially shape the proposed realization. No audit premise was refreshed.

Bounded library researchers read the supplied guides across HTML, language/runtime and relational
modeling; the earlier full SymPy/Tokenizers assessment remains applicable with source/version
checks. Context7 supplied first lookups; installed/tagged sources settle consequential discrepancies.
Concrete recommendations below distinguish source-verified interfaces from proposed compositions.
No product tests, benchmark campaign, dependency changes or migrations ran for this review.

A read-only psycopg catalog inspection of the configured `corpus_efficiency_20261030` database
on 2026-10-30 confirmed existing `sem.execution_operation`, `sem.execution_transition`,
`sem.execution_edge`, effect relations and `ops.rendition_build.text_layout`. Across visible
releases there were 200 operation rows, 108 transitions and 168 state edges; these are catalog
observations, not completeness metrics. Original bytes remain addressed through
`kb.document.original_path` plus content hash. Existing contract infrastructure is real, but its
presence does not establish coverage of every parsing decision.

### Current strengths and boundaries

Library baseline: installed/product html5lib 1.1, lxml 6.1.3, cssselect2 0.10.1,
regex 2026.9.29, Lark 1.3.1, SymPy 1.14.0, spaCy 3.8.18, LinkML/runtime 1.12.1,
RDFLib 7.6.0, pySHACL 0.40.1, jsonschema 4.26.0, Pydantic 2.14.1, NetworkX 3.7 and
SQLAlchemy 2.1.5. Guide version labels are historical: spaCy's guide targets 3.8.16,
the concurrency guide targets Python 3.15.2 versus this repository's 3.14.10, and live
SQLAlchemy 2.1 documentation now describes 2.1.6. Tokenizers is a retained spike dependency,
not an installed product parsing dependency. No version move is recommended merely to match a guide.

| Responsibility | Current implementation and implication |
|---|---|
| HTML semantics | `ingest/html.py:799` uses `lxml.html.html5parser.HTMLParser(namespaceHTMLElements=False)`, records encoding/errors and data-loss warning counts, then constructs canonical content. Preserve this behavior. |
| Profiles | `ingest/profile.py` consumes generated SourceProfile shapes, validates declared vocabulary and compiles cssselect2 roles. Source conventions already have a model route. |
| Hidden behavior | `TAG_KIND`, transparent/text-block sets, separators, normalization boundaries and inline atom handling still make consequential decisions in implementation. They need identifiable contracts, not necessarily a database row for every branch. |
| Source fidelity | DOM text is serialized with selective author markup and diagnostics. That is not complete original markup decomposition or durable source-to-canonical mapping. |
| Data structures | `core/evidence.py` already validates recursive Segment trees, containment, canonical NFC and rendition-bound range identity. Recursion in Pydantic is already used. |
| Relational authority | `semantic/metadata.py` derives fixed Core tables from the physical LinkML module. Execution variation is release data; protected publication is already separate from pure preparation. |
| Shared preparation | Persistent `TextLayout` artifacts and `PreparedMathInput` already avoid some repeated tokenization/parsing. Mathematical conversion is partly lazy; ambiguity resolution can still construct SymPy values. |
| Downstream promises | M09 extracts mathematical mentions/relations, M11 records expressions and interpretation status, M13 consumes their observations. Packet/citation/frame construction depends on canonical offsets and structural segments. |

## Opportunities

<a id="O01"></a>
### O01 — Complete decomposition and explicit coordinate mappings

**Recommend as the foundation.** Supply source inspection and later analyses with complete
categorized partitions of immutable original representations. Retain source markup, attribute
spelling, delimiters, whitespace, comments and unknown fragments independently of DOM interpretation.
Record original bytes, decoded text, canonical text and expanded TeX as separate coordinate spaces.
Represent exact, decoded, normalized, reordered, excluded, derived and synthetic mappings with
explicit coverage and cardinality. A source component's category need not assert its final meaning.

Require complete original and canonical partitions separately. Existing TextLayout covers selected
blocks with coarse math/reference atoms and following-space flags; it does not by itself provide
extents for all canonical whitespace, separators or synthetic insertions. Reuse it as an explicit
projection rather than relabel it the complete decomposition.

This enables questions such as “which original material produced this sentence?”, “what was
excluded and by which convention?” and “which two occurrences contributed to this simplified
formula?” without rerunning independent ad hoc extraction. A failed semantic parse can still
yield a complete lexical decomposition. Conversely complete lexical coverage does not establish
complete structural or semantic interpretation.

Preserve the existing `core.tex.tokens` total code-point scanner initially. Tokenizers
`Split(Regex(...), behavior='isolated').pre_tokenize_str` can retain matches and unmatched stretches;
`NormalizedString` supports normalization alignment. Neither establishes mathematical symbol
roles or arbitrary expansion provenance. Ordinary vocabulary encodings are not the full source
partition. Evaluate a replacement only when it removes an existing responsibility or provides
needed alignment; do not add a duplicate permanent lexer.

For HTML, neither html5lib tree walking nor lxml reserialization reconstructs original syntax.
Decoder normalization, duplicate attributes, implied nodes and reordered content make that
impossible in general. Complete original lexical capture must complement html5lib, with a
qualified mapping mechanism. Instrumenting private tokenizer/tree-construction APIs is a
candidate with maintenance cost, not a selected implementation. A bare stream position at token
emission is insufficient for exact extents and provenance.

Primary source explains the gap: html5lib's `_inputstream` replacement-decodes and normalizes
newlines; `_tokenizer.emitCurrentToken` normalizes names and removes duplicate attributes;
`HTMLParser._parse` constructs its private tokenizer and may reparse after an encoding change.
Custom tree builders receive decoded strings, clone formatting nodes and relocate table text.
A custom TreeBuilder alone is insufficient. Source lexical capture may be a justified extra
pass even without a speed benefit, because it supplies otherwise unavailable source fidelity.

**Required investigation:** establish an existing source-location frontend or maintainable
html5lib integration that supplies raw coverage and mapping while retaining HTML5 behavior.
If only a narrower mapping profile is feasible, declare that limitation precisely rather than
claim the complete target is delivered. Original bytes remain intact in every case.

<a id="O02"></a>
### O02 — Model-owned operations behind parser ports

**Recommend together with O01.** Extend existing operation/transition/effect and analysis-demand
definitions with source decomposition, HTML structure interpretation, canonical rendering,
relation projection, text preparation and mathematical interpretation responsibilities. Define
their applicability, input universe, invariants, result dimensions, dependencies, effects and
native capability requirements. Normalize definitions once into prepared contracts.

Co-design ports with native adapters rather than freezing a generic interface before examining
the libraries. Keep parser construction/repair policy in the HTML adapter, source conventions
in the source profile/model, mathematical meaning in interpretation contracts, and protected
effects in publication. Additional supported behavior becomes release rows when finite support
exists. Executable support remains independently implemented and verified; a declaration cannot
authorize an unavailable algorithm.

The value is local extension: a new source convention or adapter has one declared meaning and
discoverable effects, instead of new special cases in ingestion, query and evaluation. A pipeline
stage is a logical capability, not automatically another process, SQL transaction or durable task.

<a id="O03"></a>
### O03 — Relational structures with useful native views

**Recommend.** Model occurrence and edge identity, relation kind/direction, order, multiplicity,
binding scope, source/target representation and producing build. A containment tree is one view;
references, overlapping spans, alternatives and provenance form other structures. They should
not be hidden in opaque nested payloads once joins or constraints depend on them.

Retain LinkML `SchemaView` normalization and generated Core metadata. Use SQLAlchemy joins,
bulk execution and `Select.cte(recursive=True)` where relational traversal fits. ORM adjacency
relationships, eager loaders and write-only collections are candidates for concrete object
workloads, not a reason to replace current Core or protected publication with an identity map.

Pydantic recursive models, discriminated unions and reusable `TypeAdapter` objects support
validated boundary shapes. They do not themselves supply graph identity, cross-record foreign
keys or support arbitrary cyclic object serialization. Use node/edge references for shared or
cyclic structures; derive nested tree views where suitable. Avoid an ORM→nested model→NetworkX
round trip when rows or a native tree already answer the question.

NetworkX `MultiDiGraph` can support declared dependency or relationship algorithms with occurrence
IDs as edge keys. Topological ordering applies to declared DAGs; strongly connected components
help only for relationships where cycles have defined meaning. Ordered syntax children require
explicit position attributes. Preserve isolates and parallel edges. No graph add/remove call
changes semantic authority merely because it mutates a derived workspace. The owning operation
defines input projection, permitted edits, validation, result mapping and lifetime.

<a id="O04"></a>
### O04 — Shared preparation and demand-driven interpretation

**Recommend.** Extend existing preparation rather than introduce another global cache/service.
Source inspection can request decomposition; structure-aware consumers request recognition;
mathematical consumers request context-qualified SymPy objects and particular assessments.
Keep not-computed, incomplete, ambiguous, unsupported, invalid and failed results distinguishable.
Do not mark a weaker result interpreted merely because a parser accepted the text.

Lark typed starts, explicit ambiguity, position metadata and cached operation-local resolver
summaries remain useful. Packed forests can avoid tree expansion but do not remove Earley
recognition. Forest transformers do not reproduce ordinary tree shaping automatically.
`pylatexenc.LatexWalker` with a declared `LatexContextDb`/macro specification can serve structural
TeX demands; it is not a replacement mathematical authority. Select it only where it removes
unnecessary mathematical recognition rather than adding another mandatory pass.

Use SymPy native operations and unevaluated objects under admitted bindings and assumptions.
The earlier math review retains the concrete equality/domain/statistics opportunities and the
1.14-versus-development parser boundary. `x+x` becoming `2*x` never removes the two original
occurrences. Retain source definedness before transformations can erase domain holes.

Existing M09/M11 promises still require interpretation. A decomposition-only method or changed
observation/coverage contract must migrate M13 and other consumers deliberately. Reuse keys
include complete stage dependencies, including missing declarations; numerical/reference evidence
policies remain separate. Lazy execution saves work only when some consumers do not demand it.

<a id="O05"></a>
### O05 — Better composed HTML/text extraction

**Recommend preserving complete custody; selectively extend extraction views.** Keep compiled
cssselect2 role matching and use compiled XPath or Parsel where the query actually benefits.
Main-content extraction through Trafilatura is a useful optional derived view, never the complete
source authority. Evaluate extruct for explicitly attributed JSON-LD, Microdata, RDFa and other
embedded metadata as separate observations. Publisher-declared metadata is evidence about a
declaration, not automatically verified domain knowledge.

Share source-bound token layouts across sentence segmentation, spaCy matching and scope work.
`Language.pipe`, selected components, explicit annotations and Matcher/DependencyMatcher let
the native engine own linguistic work while the model owns role meaning. Retokenization changes
indexes; preserve source coordinates and declared mappings. Rule patterns and statistical model
outputs retain their distinct establishment and uncertainty.

RapidFuzz sequence alignment/opcodes and scored candidate retrieval can reuse token layouts
and prepared candidates for quote placement. Similarity does not become exact source identity;
report the cascade step, edit/alignment evidence, scope and ambiguous candidates. Avoid dense
all-pairs comparisons or repeated normalization when selectors and native cutoffs suffice.

<a id="O06"></a>
### O06 — One validation authority, explicit graph and payload guarantees

**Recommend.** Author structural and behavioral distinctions once; derive runtime boundaries,
JSON Schema and RDF/SHACL projections. JSON Schema handles payload shape and referenced variants;
relational/native constraints handle identity, ordering and cross-record consistency; supported
SHACL paths/cardinalities can assess declared graph relationships. These are complementary
guarantees, not three competing copies of parsing policy.

Reuse compiled validators and a pinned `referencing.Registry` where schema references need
resolution. RDFLib `Dataset`/named graphs provide contextual source/release views; choose the
actual validation graph deliberately rather than unintentionally validating a union. pySHACL
rules/inference may create derived facts but cannot silently upgrade parser readings or heuristics
to source assertions. Existing `semantic/ontology.py` conformance validation explicitly disables
inference, advanced features, imports and in-place mutation; preserve that boundary. Any rule
expansion is a separately admitted derived operation, not a quiet validation-mode change.
Separate validation failures from validator/runtime errors and unassessed
coverage. Enforce once at the boundary where the relevant uncertainty enters, carrying immutable
validated products through transformations that preserve its premises.

<a id="O07"></a>
### O07 — Execution and lifecycle matched to useful work

**Recommend the ownership discipline; conditionally select mechanisms.** Prepare profiles,
selectors, grammars and models at their actual validity lifetime. Batch native text work; avoid
serializing live lxml/spaCy/Lark objects through worker queues. Select process isolation or native
thread execution from actual library behavior and deadline requirements, not the presence of a
generic executor API. The current mathematical SIGALRM deadline requires a process main thread.

Evaluate bounded `Executor.map` buffering, appropriate chunking and worker initialization on the
repository's Python 3.14.10 runtime. Account for native thread pools before multiplying process
workers. Cancellation must drain owned work and prevent partial publication. Context/resource
ownership must survive asynchronous execution; immutable source identity is not a lifetime handle.
Do not import Python 3.15-only features from the supplied concurrency guide without an explicit
runtime decision. No numerical throughput or memory benefit is established by this review.

## Library mechanisms and full-guide dispositions

The following consolidates the full-guide research; candidates do not imply adoption of an
entire library ecosystem. Source/installed interfaces were inspected on 2026-10-30; composed
runtime behavior and proposed benefits remain unqualified.

| Guide / capability family | Mechanism and disposition |
|---|---|
| html5lib | Retain `HTMLParser` and lxml tree builder for HTML5 interpretation. `getTreeWalker` and filters are useful structure/projection mechanisms, not lexical round trips. Private decoder/tokenizer/tree-builder lineage integration remains an investigation. Serializer filters alter the view, not original custody. |
| lxml | Keep native trees, compiled `etree.XPath`, namespace handling and parser diagnostics. Smart-string origin identifies parent/text/tail/attribute, not exact source extents, and can retain the whole tree. `iterparse`/parser targets are conditional streaming mechanisms; HTML5 construction context can prevent early subtree disposal. XML validation/XSLT/objectify do not by themselves replace the HTML/domain model. |
| Parsel/cssselect/cssselect2 | Retain one compiled `Matcher` for role dispatch. Parsel chained selection/JSON/JMESPath is conditional on an extraction consumer; another CSS facade adds no source fidelity. Existing pseudo-element refusal and actual Matcher tuple handling need no correction. |
| Trafilatura/extruct | `bare_extraction` offers an optional article view; `extract_metadata` supplies selected heuristic metadata. extruct `syntaxes` can limit declared-metadata work; `return_html_node=True` provides Microdata origins only. Microformats requires raw input; parsed-tree integration and exact provenance need qualification. Per-syntax errors must remain distinguishable from absent metadata. |
| regex | Preserve bounded delimiter/lexical matching, named literal lists and Unicode semantics. Capture histories/`spans` and `\G` can help contiguous recognition within established regions; recursion and fuzzy regex are not substitutes for HTML5 or mathematical interpretation. |
| Lark | Native grammar composition, typed starts, explicit ambiguity and position metadata are directly relevant. `ForestVisitor(single_visit=True)`/`ForestTransformer` are conditional direct-summary mechanisms; `TreeForestTransformer` omits ordinary shaping/filtering/propagated positions. Cache callbacks only when pure, preserving correlated alternatives. LALR save/cache and TextSlice restrictions are not applicable speedups for current dynamic Earley lexing. |
| pylatexenc | Stable 2.x `LatexWalker.get_latex_nodes`, `LatexContextDb`, `MacroSpec`, `EnvironmentSpec`, `pos`/`len` and `latex_verbatim` support structural inspection. Version-3 `parse_content`/parsing-state/context APIs are prerelease distinctions. Rendering/encoding is a separate projection. It has no current production role to remove. |
| RapidFuzz | Existing token `partial_ratio_alignment` and `Levenshtein.opcodes` are useful native primitives. A new recipe using `extract`/`extract_iter` could return competing placements with edit explanations. Long-needle partial alignment does not establish a unique globally optimal location. `cpdist` fits selected pairs; `cdist` is dense Cartesian work, not an index. |
| spaCy | Keep `Doc(words, spaces)`, `Language.pipe(as_tuples=True)` and native matchers with consumer-owned mutable Docs over shared layouts. Historical selection favors the configured parser over simpler sentence alternatives; do not change it on API availability alone. `memory_zone` is conditional on actual worker retention needs; returned Docs/Tokens/Spans/Lexemes cannot outlive it. Training, transformer and entity-linking families need separately selected capabilities. |
| SymPy | Reuse the earlier full-guide assessment: native object structure, exact domains, sets, assumptions, targeted comparison, unevaluated calculus/statistics and explicit numerical execution. No universal solver, automatic role inference or source-fidelity guarantee follows. Development `locals`/all-readings APIs are absent from the pinned production version and require semantic qualification. |
| Tokenizers | Native Split and alignment are conditional alternatives to an existing lexical responsibility. No need for learned vocabulary IDs to obtain source boundaries. Normalization, added tokens, truncation and decoding have distinct provenance semantics; avoid offset-free batch APIs for source decomposition. Training/multilingual/1.0 features have no current parsing requirement. |
| LinkML | `SchemaView.class_induced_slots`/`induced_slot` prepare effective definitions. Reuse existing metadata compilation; `gen-sqla` ORM output or SQLite-oriented SQLStore does not replace protected PostgreSQL publication. Generator support for a schema feature does not establish native enforcement. |
| RDFLib | Dataset/named graphs suit scoped interchange; RDF triples do not preserve repeated assertion occurrences without occurrence nodes. Avoid rows→RDF→NetworkX as the default topology path: the installed converter keys edges by predicate, not domain occurrence. Preserve graph/release custody explicitly. |
| pySHACL | Use declared paths/cardinalities and deliberate graph selection. Installed validator enables Dataset union semantics: pass the intended graph explicitly. `focus_nodes`/`use_shapes` support targeted checking but do not discover all nodes affected by change. Rules/inference are explicit derived work, not lifecycle truth maintenance. |
| jsonschema | Prepare the declared dialect, `check_schema`, reusable validators and local `referencing.Registry`; `iter_errors` preserves diagnostic paths. Format checks are opt-in, unknown formats do not establish validity, and payload validation does not enforce relational custody. |
| Pydantic | Recursive shapes, discriminated unions and reused TypeAdapters are useful generated boundaries. `frozen=True` does not deeply freeze nested objects and `model_copy(update=...)` does not validate updates. Model actual edge references instead of serializing arbitrary cycles. |
| NetworkX | `MultiDiGraph` with occurrence keys preserves parallel relations; `subgraph_view`/`reverse_view` can avoid copies over a stable owner but share attributes. `strongly_connected_components`, `condensation` and `lexicographical_topological_sort` fit explicitly declared projections, not a union of all relationships. Retain original memberships and explicit reading order. Other graph optimization/community/backend families need a concrete question. |
| SQLAlchemy | Core `select`, joins, `exists`, set-based DML, `insert().from_select`, `returning`, bound values and transaction contexts fit current fixed metadata. Recursive CTEs require domain-specific cycle termination. ORM association objects or view-only relationships need a navigation consumer; bulk graph extraction need not allocate ORM instances. |
| Python concurrency | 3.14 `Executor.map(buffersize=...)`, chunking and initializer choices can bound work. `Future.result(timeout)` stops waiting, not execution; pool termination affects the entire pool. Direct process sentinels and `multiprocessing.connection.wait` are alternatives where independently owned termination is required. Shared memory, subinterpreters, free-threading, distributed actors and 3.15 features need an actual compatible workload, not default adoption. |

Retain general Earley pending a qualified replacement: PE-02's historical bounded investigation
found recognition dominated, forest projection small, strict full LALR conflicted and a tiny
deterministic subset had no sample coverage. These results are not new measurements and do not
rule out a useful broader subset. They do rule out claiming a speedup merely from changing APIs.

## Alternatives, interactions and priority

| Complete alternative | Disposition |
|---|---|
| Current native composition plus local wrappers/caches | Retains valuable behavior but does not deliver complete source mapping or explicit ownership of all parsing meanings. |
| Replace HTML5 parsing with a fast tree parser and infer positions afterward | Reject as the default: changes tree-construction semantics and cannot reconstruct lost original syntax. |
| Retain html5lib, add qualified source decomposition/mapping, and model connected products/operations | Preferred target; original-location support is a substantive unresolved feasibility obligation. |
| Make every lexical item a database row and every stage a durable task | Reject as an automatic rule; physical granularity follows useful joins, publication and recovery needs. |
| Use nested Pydantic/ORM objects or NetworkX as the canonical domain model | Reject as the authority; retain them as purpose-shaped derived representations where useful. |
| Eagerly materialize every syntax alternative, symbolic property and graph view | Reject as default; requested capability and completeness determine necessary work. |

O01/O02/O03 form the foundation and need joint design. O04 shares their contracts and can improve
existing preparation incrementally. O05 adds valuable optional extraction capabilities without
weakening complete source custody. O06 must govern every adopted boundary. O07 follows the selected
native realization; more concurrency cannot compensate for duplicated work or incorrect fidelity.

## Scenarios

<a id="scenarios"></a>

| Scenario | Distinction the delivered capability must establish |
|---|---|
| Valid omitted tags and malformed nesting | HTML5 interpretation, original lexical occurrences and synthetic structure remain distinguishable. |
| Entities, CRLF, encoding errors and combining Unicode | Byte/character spaces, decoding and NFC mappings are explicit; invalid material remains represented. |
| Duplicate attributes, comments and excluded scripts/navigation | Complete source capture survives DOM normalization and canonical exclusions. |
| Tables/lists and inserted reference markers | Reading order, structural relationships and synthetic text have explicit origins and positions. |
| Math with whitespace, delimiters, nested scripts and macro calls | Full partition, overlapping structures, parse views and expansion origins remain connected. |
| Two `x` occurrences and one simplified value | Occurrence multiplicity survives shared symbolic identity. |
| `f(x)` with absent, function or variable declarations | Context differences change interpretation, not source identity; unknown remains explicit. |
| A decomposition-only request | No hidden recognition or symbolic comparison is performed. |
| Interrupted worker or unsupported frontend | Source custody remains; coverage/outcome prevents partial publication as complete. |
| Changed parser with content-identical canonical output | Build-specific provenance differs without corrupting shared rendition identity. |
| Parallel edges, isolates and legal/illegal cycles | The declared graph projection preserves relation meaning and algorithm preconditions. |
| Independent reference comparison | References cannot influence extraction, interpretation preparation or source claims. |

These are acceptance questions for later implementation, not a product test campaign run here.

## Rule impacts and remaining work

The architecture strengthens A1/A3 through owned ports and native composition, A2 through connected
source/meaning/behavior definitions, and A4 through useful preparation and selective materialization.
Correctness, fidelity and execution fit remain independent obligations; schema consistency alone
does not qualify a parser or prove end-to-end performance.

Adoption must reconcile D1's canonical-only offset wording and content/build identity, D2's generated
contracts, D3's relational storage/admission, D4's method promises, D5's binding/identity, D6's
execution and D7/D8's evaluation/evidence journeys. ADR-0012/0019/0035 and relevant release/publication
decisions need clause-level assessment before changes are approved. Current plans keep their status;
the earlier F01 is not closed by this review. No new standing alignment lint or audit gate is proposed.

Before implementation planning, settle source-location integration, representation storage/query
granularity, public structure relationships, selected consumer demands and native adapter support.
The target document records the coherent destination while these technical choices retain named
investigation routes. Production implementation and qualification remain separate from review delivery.

Independent architectural reconciliation judged the bounded proposal favorable for publication
as **Proposed**, after clarifying complete canonical coverage, full rendition identity and
multi-artifact macro provenance. This establishes no implementation or product qualification.

## Capability sources

The supplied guides are orientation, not proof of installed support. Topic-level primary leads:

- [HTML5 parsing and builders](https://html5lib.readthedocs.io/en/latest/html5lib.html),
  [html5lib tokenizer source](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/_tokenizer.py),
  [lxml HTML5 parser](https://lxml.de/html5parser.html).
- [lxml XPath](https://lxml.de/xpathxslt.html), [cssselect2](https://doc.courtbouillon.org/cssselect2/stable/),
  [extruct](https://github.com/scrapinghub/extruct), [Trafilatura](https://trafilatura.readthedocs.io/).
- [Lark forests](https://lark-parser.readthedocs.io/en/stable/forest.html),
  [pylatexenc 2.10](https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/),
  [SymPy parsing](https://docs.sympy.org/latest/modules/parsing.html).
- [spaCy processing](https://spacy.io/usage/processing-pipelines),
  [RapidFuzz process](https://rapidfuzz.github.io/RapidFuzz/Usage/process.html),
  [Tokenizers alignment](https://huggingface.co/docs/tokenizers/api/encoding).
- [LinkML SchemaView](https://linkml.io/linkml/developers/schemaview.html),
  [Pydantic forward annotations](https://docs.pydantic.dev/latest/concepts/forward_annotations/),
  [JSON Schema references](https://python-jsonschema.readthedocs.io/en/stable/referencing/).
- [SQLAlchemy recursive CTEs](https://docs.sqlalchemy.org/en/21/core/selectable.html),
  [RDFLib datasets](https://rdflib.readthedocs.io/en/stable/),
  [pySHACL](https://github.com/RDFLib/pySHACL), [NetworkX MultiDiGraph](https://networkx.org/documentation/stable/reference/classes/multidigraph.html).
- [Python 3.14 executors](https://docs.python.org/3.14/library/concurrent.futures.html).
