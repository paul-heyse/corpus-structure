# Parsing pipeline — connected target model

**Proposed · 2026-10-30.** Companion to the [functional review](parsing-pipeline_2026-10-30.md).
This is a proposed target, not an implemented schema, accepted decision or deployment claim.
It extends the [mathematical decomposition proposition](symbolic-math-decomposition_2026-10-30.md)
to original HTML, canonical documents, prose, TeX and mathematical interpretation.

## 1. Meaning and authority

LinkML and its trusted execution companion define the supported concepts, relationship kinds,
roles, constraints, operations, outcomes, dependency recipes and transitions. PostgreSQL holds
immutable source/build/product instances and admitted release-scoped executable contracts.
SQLAlchemy metadata, runtime boundaries, JSON Schema, RDF/SHACL and analytical views derive
from that authority. A parser tree, Pydantic object or NetworkX graph is an owned representation,
never another independently editable source of domain meaning.

Executable algorithms remain implemented by qualified libraries and discrete Python contracts.
An operation definition identifies its implementation and supported semantics; it does not turn
arbitrary SQL, Python expressions or graph mutation instructions into a new workflow language.
Resolve an admitted release once per operation and pass prepared inputs into pure kernels.
Parsing a token never requires a policy lookup or transaction of its own.

The goal is a fully connected domain model. Every supported interpretation-changing behavior
has an owner, contract, producer and consumer. Library internals need not become ontology
instances. Unsupported semantics have explicit outcomes and a remedy, not silent defaults.

## 2. Source, structure and interpretation

| Concept | Required meaning and relationships |
|---|---|
| Source artifact | Immutable original bytes, media type, content identity and retrievable custody; existing document identity remains separately identifiable. |
| Representation | A byte or text coordinate space with source, encoding/normalization recipe, producing build and completeness. Raw bytes, decoded HTML, canonical text and expanded TeX are different representations. |
| Source component | An occurrence with a category and half-open range in exactly one representation. Components of a complete lexical partition cover the declared input once, in order, without gaps or overlap. |
| Structural node | A construct over components: element, attribute, text region, paragraph, formula, group, argument, script, binder or supported other construct. Its topology need not be a tree globally. |
| Structural relationship | Identified typed edge with endpoints, ordering/multiplicity, scope and producing operation. Containment, reference, argument position and binding are distinct relations. |
| Transformation mapping | Ordered source and target extents, producing operation and mapping kind. Many-to-many maps allow decoding, normalization, expansion and rearrangement. |
| Interpretation | Context-qualified reading of structure, declarations used, alternatives, assumptions, result state and links to source occurrences. |
| Assessment | A named mathematical or structural question over pinned products, with conditions, algorithm/policy and typed evidence outcome. |
| Product/build | Immutable output identity, source and dependency bindings, implementation revision, coverage, diagnostics and publication boundary. |

These are semantic responsibilities, not a demand for a physical table or task per concept.
Representations can share immutable text buffers. Store ranges instead of duplicated substring
payloads where practical. A compact partition can be a typed sequence; edges queried across
objects require relational identity and access paths. Preserve existing fixed-table variation
as additional release rows where it fits, introducing physical tables only for concrete instance
storage, joins or integrity responsibilities.

### Complete decomposition

Require complete coverage separately for original bytes, decoded source where decoding succeeds,
and the whole canonical representation. Canonical whitespace, separators and synthetic markers
need extents too. Current TextLayout is a useful block/token projection, not proof of this full
partition: following-space flags are not whitespace ranges, and math/reference atoms are coarse.
Reuse or derive compatible layouts from the partition; decompose math in its own mapped view
when finer structure is requested. No second permanent tokenizer is implied by separate contracts.

Retain markup, delimiters, comments, punctuation, whitespace, text-mode content, unknown commands,
unrecognized fragments and material excluded from canonical content. Lexical categories do not
claim resolved semantics. An HTML attribute name/value has lexical identity even if DOM repair
discards a duplicate attribute. A TeX control symbol is not automatically a mathematical symbol.
Overlapping composite structures sit above the disjoint lexical partition.

For `x + x`, two identifier occurrences remain distinct after SymPy constructs `2*x`. The
coefficient is derived, not a literal source occurrence. A macro call can generate several
mathematical nodes. Conversely a subscripted mathematical symbol covers several source pieces.
Links must permit these cardinalities rather than attaching one span to each shared library object.

### HTML source and repaired structure

Capture original lexical components independently of repaired DOM serialization. The HTML
decoder/parser must expose its effective encoding and repair policy. Maintain separate kinds
for exact copy, decoded equivalent, normalized, derived, excluded and synthetic output. Record
mapping confidence/availability independently: an unknown origin is not an exact range.

An implied `tbody` is synthetic; its relation to a nearby source construct does not give it an
original tag span. A character reference may map several source characters to one decoded
character. Collapsed whitespace may map a run to one space. Foster parenting can change order.
Do not infer source positions by searching reserialized DOM output or taking `sourceline` as an
exact range. Preserve original bytes even if decoding fails; undecoded bytes remain categorized
as undecoded material rather than disappearing.

The chosen target requires complete original and canonical partitioning. Precise semantic mapping of every repaired
node is a separate capability that needs qualified implementation support. Until supported,
publish its explicit unavailable/partial coverage or refuse a consumer requiring exact mappings;
never describe a partially mapped result as complete provenance.

## 3. Ports, adapters and prepared execution

Transformation mappings can reference multiple named representations, including external macro
definition/fallback artifacts as well as the invocation and argument ranges. Record the effective
macro selection, default-argument rules and producing release as derivation dependencies; matching
expanded spelling alone does not establish origin. The existing macro reader discards lexical
definition offsets, so supplying this custody requires producer changes, not just a mapping table.

Use operation-shaped ports, with exact Python signatures settled when a candidate is selected:

| Port responsibility | Input → output | Adapter responsibility |
|---|---|---|
| Source decomposition | Immutable source + lexical recipe → complete categorized components | Token boundaries, source coordinates and explicit malformed-input handling. |
| Structure recognition | Representation/components + frontend configuration → native structure and typed structural view | Grammar/HTML repair, ambiguity, syntax diagnostics and supported source mapping. |
| Canonical projection | Qualified structure + source profile → canonical text, segments and transformation links | Reading order, exclusions, insertions, normalization and author markup. |
| Interpretation | Structure + admitted context + demand → qualified readings/native mathematical objects | Symbol roles, binders, conventions, assumptions and supported native construction. |
| Assessment | Pinned interpretations + named question/policy → evidence-bearing result | Appropriate symbolic, numerical, matching or graph algorithm and honest uncertainty. |

These ports define responsibilities, not mandatory serialized passes. Compatible adapters may
fuse work and emit several products. Preserve native capabilities through owned handles/views
instead of forcing every library into a generic node dictionary. Distinct native implementations
can satisfy different capabilities under the same semantic authority.

Adapter capabilities declare media/grammar support, coordinate system, repair/ambiguity policy,
position fidelity, representation/lifetime and implementation version. Unknown required support
refuses during preparation. Swapping a parser preserves the declared contract or creates a new
explicit recipe/result meaning; syntactically matching output shapes are insufficient.

### Demand and states

Lexical decomposition, structural recognition, occurrences, interpretation, symbolic values and
specific assessments are independently requested capabilities with explicit prerequisites.
They need not all be constructed for a source-inspection request. Existing M09 `extract.math`
and M11 `normalize.formula` continue to require interpreted results until their contracts and
M13/downstream consumers deliberately change together.

Keep computation lifecycle separate from semantic outcome and coverage. Model not-requested,
pending/running, available, failed and cancelled work as needed. Within an available result,
distinguish complete/partial coverage and ambiguous, unsupported, invalid or unknown meaning.
A timeout is attempt-dependent and retryable under a changed budget; it is not timeless semantic
failure. An unevaluated `Integral` is an available mathematical object, not an evaluated integral.

Extend existing execution transitions/effects rather than invent a second task manager. Local
temporary stages need not become durable operation attempts. Seal and publish coherent products
through protected admission only after their required scope is complete; explicitly partial
products must not be consumed under complete-result contracts.

### Reuse and ownership

Separate reusable context, reusable syntax and reusable assessment. Keys include the dependencies
that affect each result: source/representation, grammar/frontend revision, profile, kind, effective
macros, declaration scope including absent declarations, assumptions and implementation. Assessment
adds conditions, question, evidence policy, precision and sampling. Different source anchors may
reuse relative computational products without collapsing evidence occurrences.

Prefer existing rendition/comparison/operation owners. Reconstruct native trees/objects only when
needed; retain durable decomposition when later queries or independent operations need it. Do not
persist every parse alternative or internal algebraic rewrite. A stored `srepr`, pickle or printed
formula is not by itself a stable executable interchange contract.

Reference evaluation retains its own inputs, preparation scope and decisions. It must never
seed source interpretation with reference data. On-demand requests pin archived source and
release context; current defaults cannot reinterpret an old answer.

## 4. Library realization

The review's mechanism tables retain detailed APIs and sources. Preferred direction is to
extend current native compositions, qualifying replacements where they remove real work:

- HTML repair and selection: html5lib/lxml with compiled selectors remains the semantic baseline;
  complete original lexical custody is an additional responsibility, not something serialization
  recovers. Selective extraction is a derived view, not a replacement for full source custody.
- TeX/math: reuse the current total TeX scanner and SymPy-derived Lark grammar; assess pylatexenc
  for structural-only demands and Tokenizers for a replacement lexical/alignment responsibility.
  Keep unresolved mathematical meaning separate from structural validity.
- Prose: shared source-bound token layouts feed appropriately configured spaCy pipelines.
  Matching/alignment consumes the same coordinate authority, retaining heuristic attribution.
- Mathematical objects: use SymPy's native sets, relations, scoped assumptions and unevaluated
  calculus/statistics objects where the model establishes their semantics. Calculation is requested
  separately; mathematical equivalence does not automatically change persisted identity.
- Persistence: LinkML-derived Core metadata and typed bulk relations remain primary. Nested
  Pydantic models are boundary views; they do not replace explicit edge identity in shared/cyclic
  structures. ORM adoption requires a concrete benefit over current Core, not relational vocabulary.
- Graphs: build a declared NetworkX view only for useful algorithms. Preserve parallel edges and
  ordering explicitly, retain isolates, and release the view with its owning operation. Never use
  generic reachability to establish binding or mathematical implication.

No all-purpose parsing service, universal persisted AST or new configuration language is selected.

## 5. Integration and compatibility

Retain document, rendition, segment and build identities as distinct scopes. Existing rendition
identity follows canonical text, the complete segment tree (including parse state/reason, attributes
and sentences) and effective macro table; parser diagnostics belong to builds. A source decomposition
and mapping can differ across builds even when canonical text is identical. Therefore give them
their own build/product identity and keep links to the shared rendition. Do not attach one mutable
parser-specific mapping to the rendition as if all producing builds had identical provenance.

Reuse `SemanticReader.text_layouts`' existing producing-task selection and `reused_task_id`
resolution pattern for build-bound products. It already refuses multiple candidate builds;
do not invent another selection rule or choose the latest build implicitly. A consumer's pinned
run/build selection must identify the decomposition and mappings as well as its shared rendition.

Changed canonical content or segmentation creates new rendition/anchor identities under the
existing rules. Add mappings and explicit selection for consumers rather than rewriting old
anchors. Source custody, parse diagnostics, model release and native-support compatibility remain
discoverable on read. Native schema changes use reviewed forward migrations; historical meanings
and frozen migration bytes remain intact.

Migration must cover source profiles, ingest/sentences, mathematical methods, scope/binding,
quote placement, source frames/packets, observations, measurements, queries/exports and evaluator
boundaries where their consumed contracts change. Do not migrate grading policy merely because
the parser implementation changes. An adoption proposal identifies D1/D2/D3/D4/D5/D6/D7/D8 and
ADR clauses requiring changes; this target does not amend those authorities.

## 6. Qualification questions before adoption

1. Which supported HTML frontend can supply complete lexical source extents and enough repair
   provenance without maintaining a bespoke HTML parser? Compare instrumented upstream support,
   a separate established lexical frontend and constrained exact-mapping support.
2. Which source/syntax relationships need durable relational queries versus compact typed products?
3. Which consumers can use decomposition only, and which require interpreted completeness?
4. Which mathematical and source conventions must become explicit admitted definitions?
5. Which graph and numerical workloads earn their preparation/conversion costs?

The [review scenarios](parsing-pipeline_2026-10-30.md#scenarios) define the intended examples.
The target is not fully realized until native adapters, model enforcement, publication and actual
consumer use satisfy those contracts. A richer schema or wrapper alone does not establish it.
