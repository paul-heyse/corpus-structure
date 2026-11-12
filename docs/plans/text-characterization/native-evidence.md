# Native linguistic evidence and positioned formal syntax

**Implemented; bounded functional scope Tested on 2026-11-11 source. TC-03 reopened by the
2026-11-12 completion audit for one obligation: the HanLP projector's frame/cue interpretation is
not retired ([TC-E09](../text-characterization_2026-11-10.md#TC-E09)).** TC-03 and TC-04 deliver native
and formal layers; independent semantic assessment and full-book qualification remain TC-10/11.
This document develops the native-evidence portion of the
[text-characterization series](../text-characterization_2026-11-10.md). The coordinator owns
selection, scheduled opportunity disposition, architectural adoption and assembled completion.
[Model and retention](model-and-retention.md) owns the combined enriched-document contract,
immutable base and selected annotation-layer revisions, source coordinates, identities, executable
declarations and retained-read/publication boundary. This document consumes those contracts rather
than defining a second model.

The selected baseline is [O01](../../functional_reviews/text-characterization_2026-11-10.md#O01),
formal parts of [O02](../../functional_reviews/text-characterization_2026-11-10.md#O02), and
[O03/O05/O07](../../functional_reviews/text-characterization_2026-11-10.md#O03). The seven linked
[discovery topics](../../library_leverage/libraries/text-characterization/briefing.md#topic-briefings-and-feature-index)
supply capability detail; the integrated review supplies selection. Conditional learned heads,
additional linguistic providers and acceleration remain trigger-driven branches, not baseline
execution requirements.

## Authoring baseline and focused foundation assessment · 2026-11-10

Planning source baseline is main `59eee893c`, inspected on 2026-11-10. The integrated source review
records its earlier `ab07dc9858ddbf2241ecf3712b51a05b360d461c` baseline. Relevant source paths below
were unchanged between the assigned baseline and the working HEAD inspected during authoring;
concurrent CLI/reporting documentation is excluded. No runtime behavior, provider accuracy or
performance was newly tested. Existing receipts keep their original scope and dates.

At the authoring baseline, the [annotation producer](../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py)
retains exact layout, source pieces, model/profile/configuration identities, token columns and
complete/partial/absent/not-applicable availability. The
[view restorer](../../../python/corpus-structure/src/corpus_structure/ingest/annotation_views.py)
rebuilds a consumer-local spaCy Doc without inference and checks unchanged token population,
text, dependencies and sentence ownership. These mechanisms are useful foundations, but their
private dataclasses and block-level coverage are not the future central enriched-document model.
TC-01/02 must make their custody available through the common generated layer contract and readers.

The [HanLP worker](../../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp.py)
already shares one multitask invocation over canonical sentence tokens, verifies prepared word and
subword coverage, skips tokenization and returns the native head outputs. Its
[projector](../../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp_products.py)
narrows constituency to `_PHRASES` and converts dependencies/SRL into private frame/cue
products. The delivered TC-03 retains all thirteen selected native evidence families without that
reduction. General role, coordination and cue interpretation belongs to [TC-05/06](constructions-and-interpretation.md),
so a new interpretation reuses evidence instead of rerunning HanLP or extending another projector.
The projector itself is unchanged and still live beside the new owner (TC-E09).

[Mathematical parsing](../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py)
already separates syntax, contextual interpretation and optional native symbolic construction;
its prepared route and source-bound occurrence handling survive. The authoring-baseline
[field grammars](../../../python/corpus-structure/src/corpus_structure/semantic/structural_parsing.py)
retain positioned comparator/value/unit fields and whole-field recognition. Their accepted
nominated input does not prove the nomination covered all source fields. The
[math native consumer/codec](../../../python/corpus-structure/src/corpus_structure/methods/math/native.py)
was a bounded Tree/Token representation. TC-04 now retains direct SPPF structure under the
central contract and reconstructs a factored working DAG for the mathematical consumer. The
current `lark-working-dag-1` codec preserves shared references and refuses cycles; it does not
enumerate complete rival trees.

The relevant existing architecture is [D4 progressive parser composition](../../design/D4-method-catalog.md#progressive-parser-composition),
[D1](../../design/D1-knowledge-representation.md), [D2](../../design/D2-schema-and-guidelines.md),
[D3](../../design/D3-database.md), and [D6](../../design/D6-orchestration-metrics-policies.md).
Their surviving guarantees are attributed source readings, progressive independent contributions,
released semantic authority and original source custody. ADR-0081 and the updated owners establish the
implemented primary producer/consumer boundary. These packages
introduce no parallel observation store, provider runtime or scheduling authority.

**Delivered foundation judgment; bounded functional scope Tested, 2026-11-11.** Native structures
serve as working forms, with generated detached layer data as the durable interchange. This addresses FP-04 and CI-01/02 without forcing a spaCy
Doc or a HanLP tree to represent every other analysis. Under FP-07 and H4/H12/H15/H17, prepare
models and grammar families once, consume source scopes in batches, detach useful evidence and
release live tensors/trees. A source unit, an annotation kind and a model head need not each cause
a task, transaction or model load. Native evidence and authored interpretation remain distinct
responsibilities even when physically fused in one operation.

## Shared package boundary

Both packages receive a selected immutable base document plus explicitly selected input-layer
revisions and the operation's examined source scope. The base continues to own hierarchy, physical
pages, text pieces, tables, figures, captions, math/reference occurrences and their native identities.
A prose view does not replace that document with a flattened text record. A table cell or caption
remains independently located even when included in a larger analysis window.

Every exact member keeps its own source occurrence identity. A multi-piece constituent,
continuation role or structure spanning blocks/pages uses ordered members plus a shared group
identity under TC-01. It does not assign all members one invented continuous occurrence, nor use a
bounding interval to imply that intervening text belongs. A synthetic boundary, normalized TeX
position or provider-local token index is related to source through an explicit correspondence;
it never silently acquires source-character authority.

Outputs are immutable identified annotation-layer revisions containing attributed analyses,
located native evidence, formal structures, correspondence references and family coverage. Native
label namespaces, scores and unknown states survive. TC-05/06 consume these products through TC-02
readers, not mutable objects from an earlier task. When a consumer benefits from a native Doc/tree,
it obtains a local view from retained data with the source and producer pins intact.

Preparation/design for either package can begin once TC-01's relevant concepts and mapping contract
are settled. Production integration additionally requires working TC-02 publication and retained
readers for those concepts; a proposed interface alone is insufficient. TC-03 and TC-04 have no
whole-package dependency on each other. Formal parser interiors can be added without changing the
source-owned opaque atom used by linguistic analysis.

<a id="TC-03"></a>

## TC-03 · Shared spaCy and HanLP evidence layers

**Implemented; bounded functional scope Tested, 2026-11-11.** Delivers reusable lexical,
morphological and syntactic premises of the full profile across the selected source population, preserving scheme fidelity and independent
family outcomes. This realizes O01 and supplies the native evidence required by O02/O03/O04.

### Inputs, operation and outputs

Consume TC-02's retained source hierarchy/projection, atom-preserving layout and exact token and
sentence correspondences. A request states language, native annotation profile, examined scope,
selected prior layers and required annotation families. The full profile attempts both selected
native producers: spaCy lexical/morphological/dependency analysis and HanLP lemma/POS/dependency/
constituency/SRL. Boundary-only requests remain a named cheaper profile and cannot satisfy the full
profile's dependency. Unsupported language, absent components or a failed native family produces
its own coverage result rather than a plausible-looking empty full analysis.

Use spaCy **3.8.18** with **en_core_web_sm 3.8.0**, its shared `tok2vec`, `tagger`, `parser`,
`attribute_ruler` and `lemmatizer`, retaining effective configuration and model identities.
`Language.pipe` consumes prepared source-bound Docs with context, avoiding tokenizer/model reruns
per matcher or downstream use. `Doc(vocab, words=..., spaces=...)`, `Token.idx` and token/source
maps preserve the prepared population; arbitrary whitespace remains in the exact source/layout
rather than being inferred from Boolean `spaces`. Preserve hard protected-atom and source-unit
restrictions before inference. Use `Doc.has_annotation(..., require_complete=True)` together with
owned family coverage; this API establishes column availability, not linguistic accuracy or
exhaustive interpretation. [Pipeline API](https://spacy.io/api/language#pipe) ·
[Doc constructor and annotations](https://spacy.io/api/doc) ·
[DependencyParser](https://spacy.io/api/dependencyparser) ·
[release-sensitive lexical contracts](../../library_leverage/libraries/text-characterization/segmentation-and-lexical-analysis.md).
Official spaCy pages are mutable; release-specific edge behavior must be checked against installed
3.8.18 source when implementing, rather than citing a nonexistent upstream tag.

Retain lemmas, POS, fine tags, morphology, dependency labels/heads and sentence membership with
producer scheme. Useful `Token`/`Lexeme` lexical flags, `lower_`, `norm_` and `shape_` can be
reproducible views under pinned language resources; persist a field when downstream decisions
require stable inspection rather than blindly serializing every property. Noun chunks, subtree
membership and conjunct traversal supply candidate constituent structure. They do not establish
semantic scope, actor identity or unconditional role sharing. Whole-block native views preserve
heads and sentence ownership; `Span.as_doc()` is not a transparent slice because heads outside a
span can be rewired. [Token](https://spacy.io/api/token) · [Span.as_doc](https://spacy.io/api/span#as_doc).

Use the shared root Python3.14 runtime (ADR-0091), currently `hanlp==2.1.7`, `hanlp-common==0.0.24`
from its pinned repository revision, `torch==2.15.0`, `transformers==5.22.1`, as declared in
[the root manifest](../../../pyproject.toml) and lockfile. The selected checkpoint is
`EN_TOK_LEM_POS_NER_SRL_UDEP_SDP_CON_MODERNBERT_LARGE`, archive
`en_tok_lem_pos_ner_srl_udep_sdp_con_modernbert_large_prepend_false_20250107_181612`, with the
ModernBERT-large snapshot `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13` and the current staged
artifact digests. Bind actual runtime/configuration custody from the
[artifact manifest](../../../python/corpus-structure/src/corpus_structure/methods/pm2_artifacts.json)
and executed provider operation; installed packages alone do not qualify a native run. Keep exact archive/state-dict loading,
offline-resource refusal and constituency sentinel repair where still required by this runtime.
[Selected archive](https://ftp.hankcs.com/hanlp/mtl/en_tok_lem_pos_ner_srl_udep_sdp_con_modernbert_large_prepend_false_20250107_181612.zip) ·
[backbone snapshot](https://huggingface.co/answerdotai/ModernBERT-large/tree/45bb4654a4d5aaff24dd11d4781fa46d39bf8c13) ·
[HanLP data formats](https://hanlp.hankcs.com/docs/data_format.html) ·
[multitask worker](../../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp.py).

Call the loaded model with canonical token lists, `tasks=["lem", "pos", "dep", "srl", "con"]`
and `skip_tasks="tok"`, sharing the encoder across selected heads. Verify native output token
population, head population and constituency leaf yield. Retain all located constituency nodes
and structural parent/child relationships, including labels outside today's `_PHRASES` inventory;
retain one-based UD roots/heads through an explicit native-to-common map, and PTB tags separately
from spaCy labels. SRL preserves native predicate markers, argument labels, continuation/reference
labels and every exact member. `ARG0` is not a universal actor, a missing predicate is not proof
of no predication, and a native causal modifier is not an admitted causal fact. The current
checkpoint's SRL decoding/width conditions remain visible in coverage and inspection.

The application retains source mapping, per-family availability, immutable analysis identities,
score meanings and interpretation of model-specific schemes. HanLP and spaCy disagreements coexist
as attributed analyses. Neither adapter selects a global winning linguistic analysis or relabels
native arcs to fit a consumer. Authored normalization belongs to TC-05/06 and cites the actual
native evidence on which it depends.

### Resource lifetime, reuse and failure

Hydrate compatible source scopes in coarse batches and publish detached results through the existing
operation machinery. The current HanLP worker admits at most eight sentences, 128 words per
sentence, 1024 characters per token, 32768 batch characters, 512 native subwords and 2048 padded
subwords. These are current profile limits, not promises that ordinary full-book sentences always
fit. Build outer batches using actual prepared subword lengths. Batch-only pressure can be remedied
by smaller batches without changing sentence meaning. An overlong sentence cannot be cut silently:
a changed segmentation loses relations across the cut and requires new analysis identity plus
explicit changed coverage. During execution inspect the full-book sentence population and revise
the native envelope or declare each unsupported scope honestly. Protective limits alone do not
establish full-profile fitness for all 518 pages. A limit excluding ordinary required family work
must be corrected before TC-11 closes, or the operator must explicitly select a narrower supported
target; truthful partial labels alone do not discharge that execution-fit obligation.

Native preparation, inference and mapping take place outside database publication transactions.
Retain current provider cancellation/termination ownership; do not add retries inside every head.
Malformed yield, impossible heads or partial protected-atom alignment are attributable failures or
mapping refusals, not empty successful evidence. An SRL failure must not erase already valid
located dependency/constituency results where the actual returned native result permits independent
validation. If a native all-head invocation fails as a whole, preserve that failed attempt rather
than inventing separate successful head outcomes. Other producers remain usable.

Reuse uses existing operation dependency custody, including source/layout/tokenization, selected
model/artifact/runtime/configuration, profile, actual input population and relevant source maps.
Changing construction or role rules can reuse unchanged evidence. Changing token population,
model, contextual correction or inference scope invalidates affected evidence and downstream layers.
`Doc.retokenize()` is permitted only before publication or with regenerated token-bound products;
it is not a repair applied to an already cited retained Doc. Release local Docs, arrays and model
outputs after detachment and the last native consumer; resident models stay under existing worker
admission. `memory_zone` is conditional on a real long-lived lexical-state need and must keep every
native reference within its lifetime, as described by the
[native lifecycle account](../../library_leverage/libraries/text-characterization/execution-retention-and-tools.md).

### Integration, replacement and acceptance

Implement shared native producers and TC-02 readable layer output together. Migrate construction
preparation to retained common evidence and retire the frame/cue interpretation inside the HanLP
projector once its consumers read TC-05/06 output. Preserve source checks and native observations;
removal is of duplicate meaning authorities. The downstream consumer package owns final removal of
private frame/recipe dependencies across enrichment, admission and replay. TC-03 must provide their
required evidence and explicit origin references before that migration can complete.

**Open, 2026-11-12 audit (TC-E09).** The shared producers and readable layers are delivered. The
retirement is not: `pm2_hanlp_products.py` was not changed by the TC implementation, still narrows
constituency and authors frames and cues, and is reachable through `ci run parsers` with current
readers. TC-03 has supplied the evidence those readers need; the remaining work is their migration
and the removal, or an operator decision to retain the private parser route as a non-primary surface.

Functional acceptance requirements (closure evidence is in the coordinator):

- Exact native restore and retained-read cases cover repeated equal words/formulas, non-ASCII text,
  arbitrary whitespace, math/reference atoms, captions/table cells, and discontinuous constituents.
  Independent expected source members reveal first-substring lookup, bounding-span and retokenization errors.
- A HanLP constituency label outside today's whitelist and continuation/reference SRL roles survive
  native output → generated layer → ordinary retained read with scheme, structure and member identity.
  Include missing SRL predicate, passive/copular/nominal and nested-clause cases; do not infer model
  accuracy merely from structurally complete output.
- spaCy and HanLP conflicting analyses remain separately inspectable. Missing columns, malformed
  native yields, overlong sentence admission, cancellation and absent artifacts retain attributable
  outcomes. A boundary-only result cannot satisfy a full-evidence dependency.
- Demonstrate native execution and retained replay on the same scopes with independent expected
  source coordinates. A construction-only revision reuses compatible evidence; a tokenization/model
  revision regenerates affected evidence. Replayed retained evidence performs no model inference.

Focused compile/functional checks belong during implementation. Native-provider evidence requires
actual selected artifacts; fixtures establish transformation behavior only. The coordinator owns
full-book population accounting, assembled provider qualification and broad `ci test`/`ci check`.
No measured speed or quality improvement is required or claimed by this plan.

<a id="TC-04"></a>

## TC-04 · Positioned formal syntax as reusable layer evidence

**Implemented; bounded functional scope Tested, 2026-11-11.** Delivers inspectable formal
constituents independently of domain assertion assembly and native symbolic evaluation. This supplies O02/O03's math, numeric field, interval,
identifier, date and unit syntax, with O05 retention and O07 fidelity assessment.

Deliver this package in two explicit slices. The early slice supplies working positioned formal
atom/constituent products and retained readers, including source correspondence, grammar identity,
deterministic syntax and any deliberately bounded conventional alternatives. TC-05 depends on this
slice, not completion of all TC-04 ambiguity work. The later slice integrates ambiguous-formal packed
symbolic semantics using TC-06's working algebra and retained DAG codec. That slice closes only
after TC-06 supplies those capabilities. The route is TC-04 positioned contract → TC-05 recognition
→ TC-06 packed semantics → TC-04 ambiguous-formal integration; no whole-package cycle or temporary
tree-enumeration substitute is required.

### Inputs, parser families and output

Consume source-owned formal occurrences and positioned candidate fields from TC-02, preserving
recognized LaTeX versus original PDF text and the correspondence between those representations.
A formula occurrence stays distinct even when its text equals another occurrence. A request binds
the grammar family/revision/start symbol, macro table/classification, required interpretation stage
and nominal scope. Token/field nomination must emit examined coverage alongside recognized candidates;
whole-field parse acceptance never implies source-wide discovery completeness.

Select Lark **1.3.1** and SymPy **1.14.0**, reusing the existing unedited shipped `latex.lark`
plus the owned extension, macro classification and whole-control-word terminal handling. The grammar
owner continues to distinguish syntax recognition, declared-context interpretation and optional
native symbolic values. Native symbolic conversion is performed only on an explicitly requested
operation path, with the source/context prerequisites it actually needs. A syntax consumer must not
cause equivalence work or inherit its failure. Use multiple declared starts where they distinguish
formula, relation, set or membership syntax; retain entry point and grammar identity.
[SymPy LaTeX parser source](https://github.com/sympy/sympy/tree/1.14.0/sympy/parsing/latex/lark) ·
[Lark grammar directives](https://github.com/lark-parser/lark/blob/1.3.1/docs/grammar.md) ·
[current grammar owner](../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py).

LALR with `lexer="contextual"` is selected for deterministic numeric comparisons, intervals,
identifiers, dates and units; `parser=None, lexer="basic"` supplies a reusable positioned lexical
vocabulary where syntax is not required. Use `propagate_positions=True`, positioned Token values
and postparse typed reduction. `ast_utils.Ast`/`WithMeta`/`AsList` and `create_transformer` can remove
constructor dispatch when their alias, child order and optionality contracts fit generated types;
freeze required source fields rather than retaining mutable `Meta`. `Transformer_NonRecursive`
handles deep conventional trees; an explicit `Interpreter` owns inherited-context interpretation
when needed. Native syntax recognition and conversion callbacks remain different failure domains.
[Lark options](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py) ·
[AST utilities](https://github.com/lark-parser/lark/blob/1.3.1/lark/ast_utils.py) ·
[visitors and VisitError](https://github.com/lark-parser/lark/blob/1.3.1/lark/visitors.py).

Deterministic typed formal input may use an explicit custom `Lexer` with `%declare` terminals,
source occurrence links and a token-to-character map. One typed terminal per native token is a
selected deterministic projection, not a lattice of overlapping possible token classes.
Earley/dynamic raw-source prose is owned by TC-05 and is not replaced with this route.
[1.3.1 custom input example](https://github.com/lark-parser/lark/blob/1.3.1/examples/advanced/custom_lexer.py) ·
[frontend compatibility](https://github.com/lark-parser/lark/blob/1.3.1/lark/parser_frontends.py).

For ambiguous formal populations, retain bounded explicit alternatives only when their converted
Tree representation remains a suitable physical form. Where ambiguity can share substantial
structure, use TC-06's direct forest symbolic path; never enumerate complete trees merely to obtain
a compact layer product. A deterministic field may use a compact typed syntax tree, while formula
alternatives use shared DAG terms under the same model. Their chosen representation does not change
source identity or permit a favored alternative to erase the others. Stable ordering is separate
from semantic preference; any context-based filtering or optional SymPy-equivalence grouping retains
its premises and the original derivation/support distinctions.

Output retains internal constituents, actual token/member occurrences, visible and enclosing extents
when relevant, grammar/rule/derivation identity, original surface, normalized typed values and unknown
or rival interpretations. Lark container extents can include filtered children; visible extent,
source member set and synthetic insertion boundary remain different meanings. A field can lie
inside a prose token: attach by exact source coordinates and preserve an unaligned interval instead
of expanding to a larger claimed quote. Normalization distinguishes Decimal value, comparator,
calendar validity and unit/dimension/vocabulary resolution. Successful syntax does not supply those
domain facts. References into math interiors relate to the parent protected atom without allowing
a prose grammar to split that atom.

### Execution, failures and consumer work

Prepare reusable grammar resources by effective family, macro classification and parser settings.
LALR `cache`, `cache_grammar`, `save`/`load` are available when worthwhile for deterministic startup;
Earley has no selected parser-pickle/cache route. Parser artifacts are preparation, not retained
parse results. Keep current deadline ownership and main-thread limitations visible when reusing
the existing math implementation. Do not remove its protection around parsing, trimmed retry,
ambiguity handling and optional native conversion before a replacement gives equivalent bounded
cancellation. Timeouts are not reusable successful results.
[Lark preparation implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py).

A recognition failure retains original input and `UnexpectedInput` context/category. A semantic
callback failure retains `VisitError.orig_exc`/rule context as failed interpretation. A recognized
prefix with dropped punctuation, authored recovery or unsupported tail has explicit partial/repaired
coverage and its edits; it is not source truth. Unsupported syntax, ambiguity, unresolved scientific
binding and failed optional symbolic conversion have separate outputs. In particular, a successful
positioned syntax layer remains usable when later native value construction fails.

Migrate mathematical and structured-field consumers to common layer readers. Preserve original
formula/reference occurrence custody, macro/input identity, no hidden string re-anchoring, and the
current stronger semantics of explicitly requested symbolic operations. Retire duplicated formal
parsing/normalization hidden inside record, comparison or qualification consumers as those operations
move to shared products. If a specialized domain validator still has work after parsing, it consumes
the retained constituents and explicitly authors its additional conclusion. Existing tree codecs
can remain only for the conventional forms whose fields they preserve; shared forest output uses
the generated DAG/report codec owned by TC-01/02.

Functional acceptance requirements (closure evidence is in the coordinator):

- Repeated identical formulas, Unicode comparators, signed/exponent Decimal values, interval endpoint
  alternatives, units and invalid dates retain exact independent source positions and distinguish
  syntax success from domain validation. At least one valid syntax with unresolved unit/binding
  remains inspectable rather than being discarded.
- Formula syntax can be read without constructing a SymPy value. Optional interpretation/value work
  cites the selected syntax and context; a failure there does not erase recognized source structure.
- A nested positioned formal constituent inside a protected prose atom retains its parent and exact
  interior correspondence. A subtoken field remains unaligned rather than gaining an expanded quote.
- Deterministic Tree and ambiguous DAG products roundtrip required extents, source members, rules,
  alternatives and sharing through ordinary retained reads. Exercise the fields generic Tree/Token
  copying and today's codec omit; do not use native pickle success as the semantic oracle.
- Grammar/macro/start changes invalidate the affected syntax. A domain interpretation-only change
  reuses compatible syntax. Recognition failure, callback failure, partial input and deadline expiry
  stay distinct through the consumer's inspection surface.

The coordinator records the applicable functional union, including native provider, packed
DAG/codec, replay and refusal controls. These results do not grade linguistic or scientific
correctness across the proving corpus. Later full-book qualification includes all 518
physical pages, eligible formal occurrences and explicit unsupported/partial coverage; it is not a
requirement to invent formal meaning for every source character.

## Extension branches and handoff

A technical lexical exception is a versioned preparation change, not a new semantic model. A new
formal field family adds a grammar/start/typed handler and coverage under the existing operation
contract. A new linguistic role interpretation consumes retained native schemes in TC-05/06 rather
than adding another native model. These are the expected extension points.

Additional HanLP SDP/NER heads, learned segmentation/lemmatization, extra language providers,
spaCyLayout, transformer encoders and LALR acceleration are conditional. Activate a branch only
for a named missing product promise or substantive replacement advantage, with the selected
artifact/runtime/source mapping and relevant acceptance brought into this series. Existing
[feature dispositions](../../functional_reviews/text-characterization_2026-11-10.md#feature-dispositions)
retain the detailed triggers. Installation or mention is not selection.

Authoring evidence on 2026-11-10 was source/reference inspection only; product/provider tests were
**not_run** at that date. The delivered native/formal operations, actual-provider controls and
retained-read paths are covered by the coordinator’s 2026-11-11 functional qualification account.
Model fitting, benchmarks, independent semantic assessment and full-book adoption are not implied.
