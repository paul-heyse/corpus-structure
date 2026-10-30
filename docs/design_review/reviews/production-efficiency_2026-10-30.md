# Production efficiency design review

**Decision: Revise.** **Source baseline:** `7fadeff`, reviewed2026-10-30. **Tier:** design;
**purpose:** target; **focus:** combined efficiency-principle and library-focused review.
Diagnoses below are source-established unless explicitly Measured. Remedies are **Proposed**.

The most useful direction is to make work follow the information and result actually required:
prepare interpretation context and candidate indexes once, avoid general analysis before its
consumer needs it, retain suitable intermediate results, and move immutable preparation outside
retry/transaction boundaries. Additional concurrency is a later physical choice. The current
system already has valuable caches, native analytical kernels and explicit ownership; replacing
these wholesale would discard strengths without removing the identified causes.

**Operator boundary:** this engagement deliberately does not refresh, amend or claim freshness
of any audit account or audit premise. No audit revision is consumed as the current diagnostic
baseline. Production code only: testing code, fixtures as a design subject, harnesses and
qualification architecture are excluded. No implementation, accepted decision or existing plan
has been changed by this review. Current independent source bytes may be used as production
measurement inputs. Unrelated concurrent documents remain untouched.

## 1–3. Scope, responsibilities and preservation contracts

Assessment uses core3.3, efficient-architecture heuristics1.0 and the code-intelligence profile1.4
from `standard.toml`. The profile applies to attributed extraction, analytical views, uncertainty
and evidence-backed answers; this review does not recast document analysis as program analysis.
The functional target remains the complete semantic domain model. Semantic authority does not
require every logical operation to allocate an object, invoke a worker, rehydrate a complete
representation or rebuild its proofs at every internal boundary.

| Production responsibility / inspected footprint | Efficiency assessment and existing strengths |
|---|---|
| Ingest and linguistic analysis: `ingest/html.py`, `sentences.py`, `delimit.py`; `methods/math/scope.py` | Cached spaCy pipeline, `nlp.pipe` over prepared Docs, compiled delimiter patterns and cached matchers already exist. F04/F05 identify remaining token preparation and interval-search work. |
| Mathematical recognition/extraction: `methods/math/{grammar,spans,methods,transform,context}.py`; `semantic/domain_operations.py` | Context-sensitive parser memo, parser-per-macro-class preparation and explicit ambiguous/partial/failure states are strengths. F01/F02 concern algorithm and context boundaries. M13 consumes persisted observations; it does not reparse every formula. |
| Scientific analysis, matching and production reference evaluation | F02/F03/F06 cover repeated transformations, comparison preparation and candidate construction. Explicit undecided evidence and ambiguous identities must survive optimization. |
| Schema/release preparation, boundary models, ontology and validation | `semantic/prepare.py` has immutable-input LRU reuse; `boundary.py` and archive products support demand-built models. Separate product opening from explicit verification/admission. F09/F10 address remaining read/startup costs; no unsupported claim that compilation occurs on every read. |
| Native storage, publication, source custody and acquisition | Fixed relation layout, protected native operations, existing transaction borrowing and one retry owner are strengths. F07/F08 concern duplicate transport preparation and scalar acquisition. |
| Relational/graph analysis, queries, explanations and exports | Recursive value closure and property-role filtering are already set-based. ADBC imports the exact snapshot; analytical registrations/readers have owners. F11 concerns complete resident capture, not absent query pushdown. |
| Run/task orchestration, provider preparation, CLI/MCP lifetimes | F08/F10 cover unused packet work and eager import costs. Keep fencing, skipped logical populations, source hashes and purpose-specific authorization. |
| Native Rust / other runtime mechanisms | The Rust crate is a starter scaffold, not an alternative production analytical engine. No Rust migration recommendation follows from availability. Development/documentation tooling is outside production scope. |

Preserve exact source-relative offsets, evidence occurrence identity, typed/qualified/repeated
relationships, declared scope, exact decimals, release and dependency identity, complete required
input universes, unknown/unsupported/ambiguous distinctions, scientific policy and evidence tiers,
atomic visibility and truthful partial results. Numeric agreement cannot become symbolic proof.
A cheaper sentence segmenter or recognizer that changes these meanings is a contract change,
not an equivalent optimization.

## 4–5. Workloads, measurements and change scenarios

[Bounded production measurements](../evidence/2026-10-30_production-efficiency/README.md) use no
testing helpers and perform no database writes. Host: Ryzen9 9950X3D,16 physical/32 logical CPUs;
process affinity exposes32 logical CPUs. These are single observations, not capacity guarantees.

| Observation | Result / interpretation |
|---|---|
| Historical triggering receipt |172.1857s over78 pages/28,956 math spans. It includes work surrounding production calls and is not a production source-to-answer or isolated symbolic-comparison benchmark. It is retained context, not a test-design assessment. |
| Unprofiled production LocationScale page |19,436 source bytes;195 spans; rendition0.2381s, cold reading6.4024s, warm reading0.001526s. Both runs:174 OK/19 ambiguous/2 failed. Existing memoization is demonstrably useful for this context. |
| Same page with cProfile | Cold30.9644s, warm2.0048s;174 OK/18 ambiguous/3 failed. Instrumentation perturbed deadline-sensitive behavior. Earley chart processing is a useful hotspot lead; cumulative totals affected by asynchronous interruption are not trustworthy percentages. |
| Fresh import of `corpus_structure.cli.app` |1.51s process wall time including launcher/interpreter; peak RSS325,196KiB; import trace app cumulative1.082s. This is one observed process, not incremental memory attributable solely to CLI registration. |
| Current archived release sizes, read-only |1,969,281 and2,238,070 archive bytes, plus manifests18,456/20,165 bytes. F09 fetches/hash-checks these bytes before its warm cache lookup. |

The page experiment separates rendition/NLP preparation from reading, but does not isolate all
recognition, resolver and transformation costs under non-perturbing measurement. It establishes
neither the speedup of an unimplemented parser nor the dominant cost of every production workflow.
No full-corpus rerun or broad benchmark matrix was needed to establish the repeated work below.

Revealing scenarios are repeated formulas under the same versus changed macro/binding context;
a domain adding new symbol/value kinds; replacing the recognizer without changing ambiguity;
one changed document; many similar entity/claim candidates; a narrow source scope in a large
corpus; a publication retry; warm repeated reads; and an analytical realization larger than RAM.
Domain extension must change declarations/context preparation coherently; it must not require
independent semantic rules in every parser, scorer and consumer.

## 6. Independent gates

These verdicts are bounded to the inspected mechanisms and proposed performance changes.
They are not a whole-codebase correctness certification or implementation acceptance.

| Gate | Verdict and reason |
|---|---|
| G1 authority | Scoped pass: retain model/release/source authority; no competing writable authority proposed. |
| G2 fidelity | Unresolved for parser/segmentation substitutions: ambiguity, kind, offsets and rendition changes require explicit qualification. No equivalent speedup is claimed from them. |
| G3 validity | Scoped pass for retained native/boundary enforcement; moving established preparation must preserve where uncertainty enters. No blanket validator removal recommended. |
| G4 hidden behavior | Scoped pass for measurements: pure production calls plus read-only SQL; future reuse must exclude ambient state and reference leakage. |
| G5 consistency/recovery | Unresolved for proposed spooled capture/private publication preparation until snapshot, lifetime and retry contracts are realized. Preserve current protection meanwhile. |
| G6 transformation/reuse | Unresolved for new prepared context, numeric kernels and capture formats; complete keys, semantics and canonical receipts are conditions of adoption. |
| G7 truthful capability claims | Pass for this assessment: structural findings, single-run measurements and proposed benefits are separated. |
| G8 library leverage | Revise: the native RapidFuzz scorer is hidden by a Python forwarding wrapper; other recommendations compare capabilities without assuming adoption is sufficient. |
| CI-G1/G2/G3 | Preserve typed claims, evidence closure and reference isolation. Proposed replacements remain unqualified against these gates; no new global fidelity/evaluation verdict is asserted. |

## 7. Findings and corrective boundaries

Finding disposition remains **proposed for subsequent planning** in this review. No existing
execution status is copied into a new ledger. All quantitative gains below remain unmeasured.

<a id="F01"></a>

### F01 — General recognition and expanded ambiguity precede useful demand

`methods/math/grammar.py:308–319` selects Earley/dynamic with explicit ambiguity. At634–645,
the resolver recursively constructs/resolves child trees before filtering admissible branches,
then transforms competing readings to SymPy; flag walks recur at551–578/650–653. Every
`spans.read_spans:102–114` request enters `any_value`. A consumer needing occurrences still
purchases this common interpretation path. **FP-07/A4; DP-10/13; H6/7/9/10.**

Compare grammar restructuring and typed entry points first where recognition dominates. Compare
context-bound subtree summaries in the existing resolver with Lark packed-forest traversal for
expansion costs. `ambiguity='forest'`, `ForestVisitor(single_visit=True)` and appropriate forest
transformers can retain sharing. Forests do not eliminate Earley chart work; current tree
transformers cannot be attached unchanged. LALR/contextual subsets need a proven admission rule:
a successful deterministic parse does not establish that the general grammar had no alternative.
Do not choose arbitrary parse priorities to obtain a faster answer.

Closure: establish equivalent declared interpretation outcomes across representative grammar and
context variation; separately measure recognition and downstream resolution without deadline
instrumentation changing the population. This review does not prescribe a new parser prematurely.

<a id="F02"></a>

### F02 — Context and reusable mathematical values stop at consumer boundaries

`semantic/domain_operations.py:3021–3047` parses with constants before projecting bindings already
present in the value. Scientific reference reading supplies variable/free bindings at
`scientific_evidence.py:940–946`. Grammar has function/variable/constant context, but consumers
construct it differently. A memoized result still calls a fresh transformer through
`grammar.to_sympy:870–895`; both scientific operand readers do so. M09/M11 independently prepare
reading inputs at `methods.py:194–197,268,345–347`. **FP-04/07; DP-08/09/10; H12/14/15.**

Introduce one model-derived interpretation-context boundary and operation-local prepared operands,
with distinct syntax/occurrence and mathematical-value products. Precompute stable context identity
where worthwhile; share compatible M09/M11 work without one durable artifact per method. Keep the
existing memo rather than layer an overlapping global cache on it. Reuse covers grammar/transformer,
kind, effective macros, bindings and constants; comparison reuse also covers conditions/policy.

Early extraction does not possess later resolved scopes. Feeding M13 outputs back indiscriminately
would create a cycle. Only authorized prior declarations can narrow parsing; any new lexical/binder
stage must have explicit uncertainty and model-defined outputs. Shared values must not collapse
source occurrence identity. Closing evidence must distinguish semantic equivalence from changed
OK/AMBIGUOUS classification.

<a id="F03"></a>

### F03 — Scientific comparisons rebuild work for repeated operands and sample points

`scientific_evidence.py:486–516,607–612,988–1007,1033–1045` applies general simplification and
repeated substitute/evaluate operations. Equation differences evaluate the same base at the same
points repeatedly. **FP-07; DP-10/11; H6/9/12.**

Prepare operands and reuse base evaluations within the comparison. Prefer structural equality and
applicable targeted transformations before general symbolic fallback. Consider `lambdify` with
explicit NumPy modules and optional CSE only where repeated evaluations amortize code generation.
Small twelve-point comparisons may not repay it. Govern generated functions by the admitted
expression vocabulary; preserve singularities, assumptions, exactness, seeds, conditions and evidence
tiers. This path was not measured by the78-page observation.

<a id="F04"></a>

### F04 — NLP retains sentence bounds but reconstructs reusable tokens

`ingest/sentences.py:54–68,107–174` caches the pipeline and batches prepared Docs correctly.
`ingest/html.py:657–670` retains extents; `methods/math/scope.py:229–239,273–280` reconstructs
source token Docs. **M13 does not rerun spaCy pipeline components.** **FP-07; DP-10; H12/16/17.**

Compare a compact operation-scoped token/offset representation with reconstructing it, including
retention/serialization costs. Do not persist complete spaCy Docs automatically. Inspect model
component dependencies with `nlp.analyze_pipes()`; compare a smaller component set or `senter` only
as an explicit method-configuration change. Sentence boundaries affect rendition identity, source
anchors and units. Math atoms, display-boundary suppression and exact whitespace must survive.
The measured page's small rendition cost makes this lower priority than its math reading.

<a id="F05"></a>

### F05 — Scope resolution rescans flat collections already ordered by position

`methods/math/scope.py:165–167,246–256,315–319,335–348` repeatedly finds enclosing segments and
rescans same-symbol sites/reopening candidates. **FP-07; H5/9/15.** Use private hierarchy/interval
indexes or an ordered sweep and per-symbol position indexes. Preserve shortest extent, tie order,
statement/section scope and reopening rules. This needs no new semantic authority or generic index
framework. Benefit is workload-dependent and unmeasured.

<a id="F06"></a>

### F06 — Matching/citation operations repeat preparation inside candidate loops

`evaluate/semantic_alignment.py:463–633,664–720,810–942` reconstructs names, attributes and
identity metadata in entity pairs, then rebuilds dense claim/group matrices for up to eight passes.
Subject/predicate eligibility is invariant across those passes. `methods/llm/cascade.py:218–252,
322–329` sorts/slices/tokenizes the same frame repeatedly. Its52–56 typing wrapper hides the native
RapidFuzz scorer identity. **FP-07; DP-09/10/13/14; H4/7/9/12.**

Prepare model-derived side indexes and eligible claim edges before expensive comparisons. Separate
invariant comparisons from those changed by `claim_map`; recompute the dependent part only. Begin
with smaller dense `linear_sum_assignment` components when their independence is proven; sparse
matching is a candidate, with explicit handling of zero/absent edges, unmatched nodes and ties.
Do not prune plausible global candidates through an undeclared similarity heuristic.

Keep `fuzz.partial_ratio` itself as the native scorer, fixing typing without a runtime forwarding
function or copied private capsule. Prepare frame sentence/token data once per batch. Consider
`cpdist`/bounded `cdist` only for already-eligible comparisons. Preserve exact-cited precedence,
nearest-anchor ordering, multiplicity, offsets, coarse/located outcomes and fallback labels.

<a id="F07"></a>

### F07 — Derived publication freezes a fixed transport twice, again on retry

`semantic/arrow_publication.py:345–368` builds `AppendPublication`, then its derived constructor
at256–285 builds it again. The constructor96–173 performs IPC ownership copying, full row
conversion and canonical sorting/bytes. `domain_operations.py:2002–2026` constructs this within
`publication._publish:586–613`'s retry transaction. **FP-07; DP-10; H12/16/23/24.**

Compose the already-owned immutable transport. Build it after span IDs resolve and before entering
the retry owner; keep admission, source revision fences, staging and atomic publication inside.
Preserve the first ownership boundary for caller-mutable buffers and identical canonical receipt
bytes. Do not hoist inference mechanically: it depends on the newly published revision. This is
high-priority removal of demonstrated whole-batch duplication without a new engine/cache.

<a id="F08"></a>

### F08 — Narrow scheduling prepares unused packets; source acquisition remains partly scalar

`orchestrate/semantic.py:662–698` decides scope/limit skips, yet `queue_agent:492–510` still builds
provider packets. `_packet_for_unit:363–430` repeats run/source/document-reference work.
`semantic/domain_operations.py:710–720` separately checks/loads source frames per report despite
set-based surrounding acquisition. **FP-07; DP-10; H5/6/8/12.**

Separate logical task population/classification from provider packet preparation. Share immutable
run/configuration/document preparation, construct expensive packets for admitted work and bulk-load
distinct origin frames plus ordered sentences. Retain skipped identity, reason and unknown coverage.
If skipped task identity currently commits to full packet bytes, change that contract explicitly;
do not merely omit the hash. Preserve original frame/source custody and final effect fences.
This scheduling cost is independent of the172-second math observation.

<a id="F09"></a>

### F09 — Warm archive opening still transfers and hashes the complete archive

`semantic/archive_reader.py:318–342` selects the complete release, checks finalization, hashes
`prepared_bytes` and the manifest, and only then consults the engine-scoped cache. Current archives
are about2MB each. `releases.py:495–581` additionally rederives/compares projections at explicit
verification, used by `orchestrate/{project,commands}.py:80,99` and regeneration resume164.
**FP-07; DP-09/10; H12/14/18/19.**

Use a cheap snapshot-observed finalized header/runtime key before fetching payloads on a genuine
cache hit, conditional on the same protected immutable archive authority. Retain full verification
for unfinalized/untrusted/historical paths and explicit admission. Examine whether source execution
is reopening an already admitted product or deliberately performing new verification; retain each
needed uncertainty check rather than replacing `load_release` globally. Do not share authorization,
project pointers or mutable facts through a release cache, and do not add another certificate table
when existing finalization suffices.

<a id="F10"></a>

### F10 — Every CLI group eagerly imports unrelated analysis dependencies

`cli/__init__.py:13–25` imports all groups during app registration; the import trace includes
scientific evaluation, SciPy and analytical dependencies before a command is selected. One measured
app import costs1.51s/325,196KiB peak process RSS. **FP-07; DP-10/17; H6/12/26.**

Keep command metadata/registration cheap and defer production kernels to the owning command or
lifespan. Use existing Typer structure and ordinary local imports before inventing a plugin system.
Preserve help/completion, typed refusal handling and explicit initialization. Pool configuration
already avoids queries in its configure callback; pool/principal checks are distinct safety
boundaries, not generic startup work to delete. Long-lived MCP benefits and one-shot CLI benefits
must be measured separately.

<a id="F11"></a>

### F11 — Complete detached analytical capture is fully resident before use/export

`semantic/analytics.py:599–651` calls `read_all()` for each spine relation and retains every table;
`serve/export.py:50–108` writes after capture. DuckDB's memory limit does not bound these retained
Arrow inputs. **FP-07; H15/16/17/21.** This is a capacity limitation, not an observed current OOM.

Retain the resident packet for small inputs. Compare a detached on-disk capture: consume ADBC
batches, normalize exact values, use `ParquetWriter.write_batch`, accumulate counts/schema/digests,
then atomically publish a complete manifest and close PostgreSQL snapshots before long analytics.
DuckDB/Arrow can scan the detached files. Preserve the same logical spine, snapshot, ownership and
incomplete-capture refusal. Do not obtain lower memory by holding a database snapshot throughout
long downstream computation. CandidateInput's repeated trusted-builder comparison should be solved
within the same owned-input boundary, not another cache.

## 8–9. Library fit and composed target

The proposed target is a small set of operation-shaped prepared products under existing semantic
contracts: text/token context; mathematical interpretation and lazy values; comparison-side
indexes; immutable publication transport; and resident or spooled analytical capture. They need
not be services or universal durable artifacts. Choose an operation-local object first; promote
persistence only when actual reuse and recovery justify it.

| Library | Concrete disposition / capability and source |
|---|---|
| Lark1.3.1 | Compare typed starts, grammar restructuring and [SPPF visitors/transformers](https://github.com/lark-parser/lark/blob/1.3.1/docs/forest.rst). Forest sharing treats expansion, not all recognition cost. |
| SymPy1.14 | Existing parser/transformer remains a baseline. [Targeted algorithms](https://docs.sympy.org/latest/explanation/best-practices.html), prepared operands and conditional [lambdify](https://docs.sympy.org/latest/modules/utilities/lambdify.html) reuse require exact policy preservation; no blanket simplify-to-numerics substitution. |
| spaCy3.8 | Existing [Doc-aware pipe](https://spacy.io/api/language#pipe) batching is appropriate. `analyze_pipes`, component dependencies and [SentenceRecognizer](https://spacy.io/api/sentencerecognizer) inform an explicit segmentation comparison. |
| RapidFuzz3.14.6 | Restore native callable identity; [extractOne/cdist/cpdist](https://github.com/rapidfuzz/RapidFuzz/blob/main/docs/Usage/process.rst) follow semantic candidate reduction and preserve scorer/cutoff/precision. |
| SciPy1.18.1 | Keep [linear_sum_assignment](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html) on suitable components; `min_weight_full_bipartite_matching` is conditional on sparse/full-matching semantics, not a universal replacement. |
| regex | Existing cached patterns and bounded searches are strengths. Prepare repeated quote patterns within a frame where useful; do not use regex as a mathematical grammar substitute. See the local capability overview's matching/timeout sections. |
| pylatexenc | Candidate structural frontend, not currently declared. [LatexWalker2.10](https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/), context/macro specs and source coordinates can own nested syntax, not mathematical meaning. Resolve2.10 versus3beta compatibility before selecting APIs. |
| Tokenizers | Candidate, not a current production import/direct dependency. `encode_batch`/offsets can serve neural model inputs; [tokenization/alignment](https://huggingface.co/docs/tokenizers/quicktour) does not supply spaCy scope or sentence semantics. No adoption solely for the current reading hotspot. |
| GLiNER2 | Candidate/catalog proposal, not a current measured cost. [Batched/schema-composed extraction](https://github.com/fastino-ai/GLiNER2) may share encoder work if an extraction mechanism is deliberately substituted. It does not establish current source-grounded mathematical/scientific semantics. |
| DuckDB2.0 | Preserve native relational grouping/joins and resource cleanup. Use [relational/Arrow interfaces](https://duckdb.org/docs/stable/clients/python/relational_api.html) and file scans for operation-shaped inputs; a native engine does not fix eager Python-side materialization. |
| PyArrow26 | Preserve exact schemas and ownership. [ParquetWriter.write_batch](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetWriter.html) and record batches support detached capture. Native conversion must match scale, ties, overflow, signed zero and missingness. |
| RDFLib7.6 | Graph scope is already explicit; SHACL disables imports/entailment/in-place mutation. Constant core shapes reparse at `ontology.py:920–969`: lower-priority reusable preparation, with mutable-Graph isolation (`selected += shapes` precludes blindly sharing one Graph). [Prepared queries](https://rdflib.readthedocs.io/en/stable/intro_to_sparql.html) and `Graph.addN` are available but no hot repeated SPARQL path was established. No new graph store recommended. |

Context7 was the first capability lookup, followed by pinned/installed interfaces and primary
sources. Local overviews orient the comparison; documentation for a newer version does not prove
availability at the installed pin. No library-account baseline is refreshed by this table.

Compare complete alternatives: more workers alone keeps repeated work and duplicates preparation;
a universal persistent analysis cache adds identity, invalidation and retention machinery;
operation-local preparation is the simplest first correction. A single persisted mega-IR risks
forcing weak consumers to load rich products. An always-streaming database pipeline risks long
snapshots. Preserve current mechanisms where their lifecycle fits, and change only the boundary
that creates amplification.

## 10. Evidence limits and settling questions

Source inspection establishes duplicate freezes, matrix/metadata reconstruction, scalar frame
reads, unused packet construction and pre-cache payload transfer. It does not quantify savings.
Only startup, one production page and archive sizes were newly measured. No worker-count, memory
capacity, full-corpus production or alternative-parser speedup claim is made.

Before choosing a replacement, settle grammar recognition versus resolver cost without perturbing
semantic deadlines; context authorization and staging; the reuse lifetime of symbolic operands;
component/segmentation fidelity; candidate density/ties/cycles; transport ownership/canonical bytes;
and the larger-realization capture requirement. Known cases must independently challenge ambiguity,
negative/unknown results, different scope under identical text, changed macros and exact values.
This specifies later acceptance needs; it does not conduct or redesign testing code here.

## 11. Proposed rule impacts and disposition

| ID | Rule / proposed change / outcome if retained |
|---|---|
| RC01 | ADR-0012's one grammar/token-form/source-offset contract: changing internal ambiguity representation or sharing prepared values can preserve it. Multiple recognizers or a structural frontend establishing independent meaning need a successor decision. If retained, keep one authoritative interpretation and optimize its grammar/resolver. F01/F02. |
| RC02 | Recorded sentence method/model configuration: a smaller pipeline/segmenter may change rendition and anchor identity. Adopt only as explicit new configuration/release; otherwise retain current segmentation and pursue token reuse. F04. |
| RC03 | Skipped task identity currently may include rendered packet bytes. Revise that dependency explicitly if separating cheap logical skips from executable packets; otherwise packet-dependent hashing remains a constraint and savings are narrower. F08. |
| RC04 | Fully resident AnalyticalPacket as capture contract: permit an equally snapshot-qualified detached file realization if capacity warrants it; otherwise state the resident capacity boundary and preserve complete spines. F11. |

No rule is changed here. Recommendations are unscheduled proposals owned by this review until
separately adopted through plan creation; existing plan statuses remain unchanged. No audit
premise, accepted ADR or functional-review document is updated.

## 12. Architectural judgment and next decision

| Judgment / foundations | Verdict within this efficiency review |
|---|---|
| A1; FP-01/02/06 | Existing module/operation ownership provides a useful base. Local lifetime corrections are well scoped; shared interpretation/context and comparison preparation need a deliberate contract before wider change. Those new boundaries remain unresolved. |
| A2; FP-04/05 | Existing source, release, typed value and lifecycle distinctions are preservation constraints. New context authorization, staged products and any segmentation change remain unresolved; no whole-domain completeness certification is made. |
| A3; FP-03 | Existing native libraries and owned analytical inputs are composable strengths. Reuse owned transport and native scorers directly; additional universal services/frameworks are unjustified by this evidence. |
| A4; FP-07 | Violated for the demonstrated fixed-transport duplication (F07), excluded-unit packet preparation (F08) and repeated invariant candidate setup (F06). Other opportunities have the conditions described above; F11 capacity fit remains unresolved for larger realizations. Bounded execution and correct outputs do not justify this avoidable work. Remedies remain Proposed. |

**Bounded decision: Revise the production efficiency architecture before expanding it.** The
review establishes concrete improvement opportunities; it does not prove a globally optimal design
or that every operation is slow. Enclosing production correctness and broad domain-model completeness
are not independently recertified by this focused engagement.

First remove clear local duplication/native-boundary losses (F07/F06), then settle shared
context/prepared-analysis and candidate-index contracts (F01–F03/F06). These enable the largest
analysis redesign comparisons. F08/F09 address workload-independent upstream costs; F04/F05/F10
are local preparation/lookup improvements. F11 follows a concrete larger-realization requirement.
Priority and dependency differ: the shared context contract can be prerequisite to a faster parser
without itself being the dominant elapsed cost. The next owner is plan creation, carrying these
findings, library mechanisms, countercases and proposed rule changes into an explicit adoption
choice. No implementation is authorized by publishing this review.
