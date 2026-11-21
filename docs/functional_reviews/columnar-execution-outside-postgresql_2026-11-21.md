# Execution outside PostgreSQL: what the row work is for, and what should replace it

**Proposed · 2026-11-21, revised the same day.** The first publication of this review took each
row-wise step outside PostgreSQL as given and asked whether DuckDB or PyArrow could express it.
The answer was narrow. The operator then asked the prior question: traced backward to where its
data comes from and forward to who relies on it, should that work exist as rows at all? This
revision answers that for the layers around the kernels, and it changes the conclusion.

In four layers, most of the row-wise Python is not required by what the system accomplishes: the
packaging of product members, the envelope around every operation, the hand-off between
operations, and the readers. There it falls into three kinds. Homogeneous populations are
packaged, stored and validated as individually addressed items that nothing addresses
individually. Python rebuilds relationships and derived data that an upstream owner, usually
PostgreSQL or the producing operation, had already resolved. And values are decoded, validated
and hashed again with no boundary crossed since the last time. The PDF path has the same three
kinds around a central proof that is sound. Inside the kernels the picture is different: there
the procedural cores dominate, an independent sample put the removable share at a minority, and
most kernel code was not examined.

The target is therefore a design, not a library: a homogeneous population stored once and
validated as a set, an address only for what is addressed, one proof per boundary, and each
relationship resolved where its owner is. Rules about custody and about which tool is used where
are means to those ends and are treated as changeable. PostgreSQL keeps its authority, and several
proposals move work toward it.

## Scope, evidence and what changed

`cs/` is `python/corpus-structure/src/corpus_structure/`. The Rust crate is outside the review.

**Inspected · 2026-11-21.** By operator direction the review reads current code and no document
older than the two latest plans. Ten purpose traces read the working tree between `3a449d134` and
`5d2ba51e5` while Domain Model Operability work continued in it: three spot checks (token and
sentence members, the selected-record hub, PDF certification) and seven wider traces (member
packaging in every producer family, the operation envelope as a trust map, hand-off along three
operation chains, the remaining readers, the rest of the PDF path, evaluation, and a coverage
sweep). Each trace was briefed neutrally and had to report the strongest evidence that the
row-wise form is required. An independent design assessment then challenged the draft, applying
the operator's test that a rule is judged by the end it serves; it narrowed the headline and
three recommendations and corrected several facts. Findings marked **[V]** were re-read in the
code by the reviewer or the challenger, and re-checked at head `f5713f9f6`. Line references drift
while that work continues, so functions are named.

**Tested · 2026-11-21.** Library behaviour cited as **[F]** is reproduced by
`uv run python docs/design_review/evidence/2026-11-21_columnar-execution-review/columnar_fidelity.py`.

**Not established.** Nothing was executed against PostgreSQL and no timing was taken. Counts of
repeated work are static counts of call sites, not measurements. Not re-verified after the
traces: the PDF repeat counts, the evaluation preflight, the resolver counts, and the math-chain
claims. [Coverage](#coverage) lists what was not examined; it includes the method libraries where
most kernel row work lives.

**What changed from the first publication.** The question, the method and the conclusion. O01 to
O10 keep their references; [correspondence](#correspondence-with-the-first-publication) says what
became of each. O11 to O19 are new.

## Method

Each trace established, for one subsystem: what it produces and for whom; what is ever selected,
referenced or revoked individually, and by which mechanism; what each check or digest proves,
across which boundary, and what failure its removal would allow; where bytes are re-examined with
no boundary in between; where something is recomputed that an owner already resolved; and what
would have nothing left to do if the unit of work were the set. Every row-wise step was classed:

| Class | Meaning | Consequence |
|---|---|---|
| R1 | The unit of a proof across a trust boundary | Keep; name the boundary |
| R2 | Individually addressed, or an identity across products | Keep the address; ask whether it must be a stored packet |
| A1 | A homogeneous set handled as items with no individual consumer | The unit becomes the set |
| A2 | Re-derivation of what an owner already resolved | Ask the owner, or keep its answer |
| A3 | Repetition on the same bytes with no boundary crossed | Once per boundary |
| P | Procedural core: object graph, model or library semantics | Keep |

A rule the code states about custody is not a reason to class a step as required. The test is
what failure the rule prevents, across which boundary, and whether a simpler mechanism prevents
it too.

## What the traces found

### Members: four kinds are addressed

A product may carry `members[]`, each a packet of id, kind, context and body, stored again as a
`kb.data_product_member` row and admitted with per-member checks
(`semantic/data_product_admission_native.py`, `_install_product`).

Of 299 declared roles, four member kinds are bound individually through PostgreSQL **[V]**:

| Kind | Input roles | Why it is a member |
|---|---|---|
| Source views | 48 | Each has its own subject and scope |
| Product manifests | 14 | Compact summaries selected across independently produced families |
| Contextual target members | 1 | One derivation per member under its own subject |
| Candidate contributions | 3 | Cues pinned individually from several reports |

All are inputs selected from a population or across products. No output role is a member **[V]**.

Every other member kind is referenced only or never addressed. They divide in two.

*Homogeneous populations.* Tokens, sentences and HanLP units. For tokens and sentences **[V]**:
no role binds them; every consumer pins the whole product and several raise on a member; the
packets are derived from the nested annotation and the product is rejected if a recomputation
differs (`semantic/sentence_products.py`, `validate_source_annotations`); and a token's dependency
head goes from an ordinal to a hashed id and back to an ordinal
(`semantic/constructions/matching.py`, `retained_native_documents`). A token packet's body is
already a five-column row. What surrounds it is a context identical for every member of the
product, a kind contract and a hash, held in the body, again as a row, and shipped a third time
by the support export, which sends every member row of every reached product.

*Heterogeneous graphs.* Formal and construction inventories, rich proposals and graph members.
Their ids are content hashes that do real work: a rich member's id is its body hash, retained
admissions match packets across products by it, and PostgreSQL fetches single members by key to
validate rich references (`semantic/rich_admission_native.py`). These are an identity across
products, not a set dressed as items.

For both groups the rules that matter are set rules: uniqueness, ordering, containment, closed
membership, referential closure, coverage, equality between stored copies. PostgreSQL enforces
shape, uniqueness and count. Closure and ordering are enforced only in Python, by the producer
and again by consumers.

**The reference model has no owner.** Products point at members of other products with stored
`{product, member}` pairs, resolved by about fifteen hand-written Python resolvers and about seven
database-side ones. References inside bodies are followed by PostgreSQL in two places only.
Dangling-reference checks exist in producers' Python for some fields.

**A precedent that was not adopted.** Five typed member projection tables exist, are validated at
admission, and include the only database-native member-to-member foreign key. No kind declares
them **[V]**, so they are never populated, yet binding selection and the support export read
them. Member-level outputs are likewise checked and used by no role. A generic typed-table
mechanism was built and nothing took it up.

### The envelope: ten boundaries, sound intent, residue around it

Between binding and publication a value crosses ten real boundaries: database to parent, parent
to worker, worker to parent, parent to model host, parent to database, principal, producer to
consumer, file custody, release and runtime, and time under a lease. The code states its
principle: each owner checks its own premises and caches carry no authority. PostgreSQL
independently recomputes the request key, product identity, the input basis of authority ports,
schemas and output witnesses, and a seal at publication skips correspondence checks when nothing
changed.

Steps with nothing left to guard, same bytes in the same process:

- the second and third decode of each input body **[V]** (`orchestrate/data_operations.py`,
  `_hydrate`);
- a deep copy straight after an owned copy (`semantic/data_operation_ports.py`, `_arguments`);
- receipt digests computed and then checked against the same parent bytes;
- a second read of the same source file in the worker, and per-call rebuilding of a descriptor
  with re-hashing of sources on prepared ports;
- three of the four per-call re-verifications of loaded source files. One bracket around the
  computation serves the end, which is real: imports inside functions mean a module can first
  load mid-call.

Python prechecks of rules PostgreSQL enforces authoritatively (member packets, output witnesses)
buy an earlier failure and nothing else. Work in progress is already moving this way: `f5713f9f6`
retired repeated field copying at port ingress.

*Required.* Claim and support re-checks at retain and at publish guard time and revocation. The
worker's check that imported code is the hashed code. The reply's echo of the request digest,
which ties a reply to its request across a process. A consumer running a producer's validator
where no proof of validity exists, because PostgreSQL admits on schema and identity only.

### Hand-off: products are re-established and re-derived at every hop

Along three declared chains (sentences to definitions; formal evidence and sentences to scoped
relations; formal evidence to symbol scope):

- **One source view is fully validated seven or more times per chain**, twice inside the sentence
  operation alone **[V]**. The end is that a hand-built source object carries no authority. If
  acquisition is the only way to construct one, the type is the proof within a process and one
  acquisition per process serves the same end. The formal operation already works this way.
- **Token and sentence rows are rebuilt from the nested annotation at seven call sites in the
  constructions library** **[V]** and again in the canonical projection, predicate evidence and
  the producer itself. The function is pure over immutable bytes.
- **Typed wrappers re-validate on every property access.** Reading the canonical product's
  reference validates and hashes the whole product, and the HanLP path reads it once per token
  **[V]** (`semantic/hanlp_products.py`, `detach_hanlp_sentence`). Neighbouring classes already
  cache the same kind of value, and the wrappers are frozen over bytes, so caching loses nothing.
- **A proof of validity exists and is half used.** A producer can record that its validator
  passed on a body under a release (`semantic/established_validity.py`); PostgreSQL checks the
  record's correspondence at completion and hands it to consumers. Only formal evidence and
  constructions emit one. The sentence product has none, and its full validator is re-run from
  five consumer modules **[V]**. Where a proof exists some consumers ignore it, and consumers of
  construction products check identity only **[V]**. The stance differs hop by hop.
- **The math chain rebuilds each formula's context about four times** to prove a stage key
  (not re-verified).

*Required.* A proof matches only within one release, so a consumer under another release must
validate. Validating against the consumer's own source catches a body that does not belong to it.

### Reads: five shapes, implemented many times

No role can read the underlying tables; one security-definer program answers a selected read with
a JSON document per page, applying disclosure per row. Every reader needs one of five shapes: the
cut and its frontier; output or member rows with bodies; raw support rows for a scope; PDF source
rows and ranked hits; a pair of releases.

- **PostgreSQL builds the use-to-output-to-product join; the index strips it and Python rebuilds
  it** **[V]** (`semantic/data_operation_read_index.py`, `append_page`;
  `semantic/selected_contribution_input.py`, `SelectedContributionScope.products`), one keyed
  lookup and a full row parse per step. The same loop is written in at least five modules.
- **Member filters run after the fact.** Kind, member, record type and family are applied in
  Python after whole bodies are fetched and decoded.
- **Paging is one obligation per call**, because the database cannot page inside a JSON body.
- **Four frontier walks, four root-product selectors, six cursor schemes, five whole-body
  decode-and-validate paths.**
- **Summaries are computed from full bodies**; the catalog makes a full source acquisition per
  row; the neighbourhood reader pulls the frontier and whole support closure to read one body.
- **The same page bytes are parsed at least three times**; cached rows are encoded, decoded and
  re-encoded as a check; page assembly re-renders the envelope and a cursor per appended row.

*Required.* One family (structures, dossier, gaps, journey) re-runs on an exported file and
compares bytes with the recorded response. The end is that someone without the database can
confirm a served response follows from the exported closure. What carries that end is one
implementation running over two sources of rows; byte equality is only the cheapest comparator.
The authority recheck on every page, the cursor's binding to cut and code version, and the graph
models, reports and statistics are required or Python-owned.

### PDF: the central proof is sound; copies and repeats surround it

The per-row identity fold is a two-language protocol and the only link between Python's
validation and the stored rows; it stays. Around it:

- **Each item is stored three ways:** rows, a JSON copy in the access table, and each box again
  in a region table nothing queries by page or geometry. The copy is built by separate Python and
  staged from a file, so about 430 lines of SQL reconcile it with the rows
  (`semantic/pdf_record_access_native.py`). That reconciliation is today what makes served items
  equal certified ones, and the JSON copy has many readers.
- **Two routines rebuild a document from rows.** The round-trip proof exercises one; every
  transform builds its whole-document input from the other **[V]**. The rows are authenticated
  either way, so this is two algorithms over the same certified data, not an unguarded boundary.
- **One enrich operation serializes the whole document about seven times, parses it about eight
  and runs full Docling validation six times**; two of those cross a boundary (not re-verified).
- **A page payload is decoded and validated about seven times in one operation**; a fresh record
  file is hashed five times, twice back to back (not re-verified).
- **Recovery rewrites every row** because the build identifier is a column of each row.

*Required.* The page payload encoding preserves absent against null and integer against float;
PostgreSQL cannot read it, so the Python digest check is the only one. Publishing recognition
observations is the durable hand-off between two operations. Spool files cross attempts and
processes. Docling validation before lowering is needed because transforms mutate the document.

### Evaluation

Protected reference data, a fitter role restricted to its partitions, and held-out calibration
are enforced by PostgreSQL through role-restricted disclosure, and its completion guards recompute
grade and event-frame facts in more detail than the Python preflight. The preflight opens a second
record index, re-derives facts the binding established, and compares bodies with arguments it
already holds. One check has no database equivalent and stays: authored reference coordinates
against retained source text.

### Kernels: sampled, not traced

The challenge classified four modules no trace had cited (rich graph validation, the contextual
layer, record assembly, source acquisition, about 4,100 lines). Their row-wise work is mostly
type-driven traversal of heterogeneous graphs, procedural construction from model replies, and
validation at a real boundary. The removable share was a minority, on the order of a sixth to a
third by a qualitative read. The hypothesis that row work collapses does not extend to the
kernels on this evidence.

### Coverage

Traced: the areas above. Swept and judged not to carry corpus-sized row work: release preparation
and model compilation, code and source custody, caches, terminology, CLI reporting. Swept and
worth a later look: demand planning, which reads and compiles a binding per pending obligation
that PostgreSQL re-verifies; release persistence, which re-prepares a release to verify bytes it
was handed. Not examined: the native generators as programs (about 63k lines), `methods/` (about
50k lines, where most kernel row work lives), model-host internals, and `core/`.

## What remains when the artifacts are removed

| Layer | What the system needs |
|---|---|
| Member populations | Four addressed kinds; content-hash identities for the graph families; for homogeneous populations a handful of set rules per record type. One way to name an item and one way to resolve a name. |
| Envelope | One check on each side of each of ten boundaries; values carried validated in between. |
| Hand-off | One validation per product per release, recorded and accepted; one acquisition of a source view per process; derived rows computed once. |
| Reads | Five answer shapes; over the raw subgraph about five join shapes (key lookup, children by foreign key, filtered scan, embedded reference to child rows, whole-graph edge listing). |
| PDF | The identity and stream folds; set checks on containment, ordinals, inventory and endpoints; one derivation of the access columns; one document rebuild; one decode per page and one hash per file per boundary. |
| Evaluation | Role-restricted disclosure, completion guards, the coordinate check, and the kernels. |
| Kernels | Largely as they are. |

## Target design

Stated as properties, with what each would retire.

**T1. A homogeneous population is stored once, carries no per-item context, and is validated as
a set.** *Retires:* per-item packets and context for those kinds, shape checks repeated at three
layers, and equality checks between stored copies.

**T2. An item has an address when something addresses it, and the address says what kind it is.**
Three cases: no address; an address derived from a natural key (a token's span within its block,
which survives a projection that drops tokens, where an ordinal would not); an identity across
products, which stays a content hash. The four bound kinds keep member binding. *Retires:* ids
computed only to be translated back.

**T3. References have one model and one resolver, and closure is checked once, by whoever holds
both ends.** *Retires:* the per-family resolvers and dangling checks; *adds* the missing ones.

**T4. One proof per boundary, and a validated value stays validated.** *Retires:* the residue
listed under the envelope and hand-off findings.

**T5. Validity is established once per product per release and accepted.** *Retires:* repeated
full validations and the hop-by-hop difference in stance.

**T6. Derived data is computed once: by its producer if consumers need it, otherwise once per
process.** *Retires:* repeated rebuilding of token rows, navigation indexes, interval indexes and
formula contexts.

**T7. A relationship is resolved by its owner and the answer is kept.** Readers that never run
offline ask for the answer; the raw subgraph is a deliberate capability for the readers that
replay. *Retires:* rebuilt joins, hand-written mirrors, after-the-fact filters and most cursor
schemes.

**T8. A derived copy is derived in one place from its source, and one algorithm does one job.**
*Retires:* copies with no reader, and the second document rebuild.

**T9. Every real boundary has a proof.** *Adds:* reference closure; the round-trip validation
using the captured policy.

## Realization: where DuckDB, PyArrow, PostgreSQL and plain Python fit

These are today's carriers for the properties above. Each entry states the need so that the
choice can change without the design changing.

| Need | Carrier today | Why | What would change the choice |
|---|---|---|---|
| A population held once and typed (T1) | PostgreSQL as the store of record. In process, plain typed rows, or Arrow where a model host or kernel produces and consumes columns | The store can enforce set rules where the data lives | Value forms Arrow cannot hold exactly stay text or stay in the canonical body **[F: X1–X2]** |
| Set rules at admission (T1, T3) | PostgreSQL | Closure is unchecked there today | Requires a declared per-record-type rule vocabulary in the model and generator support, a new mechanism with a cost. The unadopted projection tables are the warning. |
| Values carried validated (T4, T6) | Plain Python: memoised frozen wrappers | No representation change is needed | None |
| The answer shapes for online-only readers (T7) | PostgreSQL programs | The joins, filters and keysets are over its tables, under its disclosure rules | Not DuckDB work |
| Joins over the raw subgraph for replaying readers (T7) | Python over the existing index; DuckDB only if those projections are rewritten as joins | Point lookups dominate what they do today **[first publication]** | A rewrite of the projections as set operations, which would then run identically over an export |
| PDF certification scans (T4) | Arrow IPC files read directly; Python folds | Both ends are already Arrow | The engine for the frame sort is open (O02) |
| Access columns (T8) | PostgreSQL, derived once at publication from the certified rows | Removes one staged derivation | The JSON copy is not derived this way; see O17 |
| Span and ordinal work inside kernels | The Python span vocabulary (O07) | Kernels ask span questions one at a time inside procedural code, and T1 changes what is stored, not that pattern | A decision to rewrite a kernel family as set operations; then DuckDB joins and windows over tables, which are available as typed expressions **[F: E1–E8]** |
| Identity and meaning bytes | Python canonical encoder | DuckDB's JSON differs for floats and decimals **[F: I3–I4]** | None |
| Regular expressions, edit distance, float sums in ranking | Python | The DuckDB functions differ silently **[F: S1–S4]** | None |

The honest reading is that the design this review argues for needs little columnar machinery. It
needs populations stored once, values carried, proofs placed, and questions asked of their owner.
DuckDB and PyArrow become the natural carriers at the point where a kernel family is rewritten as
set operations, which the first publication called the broader direction and which remains the
operator's decision.

## Opportunities

<a id="O11"></a>
### O11 — Homogeneous member populations stored once and validated as sets

Tokens and sentences first, then HanLP units. The population is held once with no per-member
context, validated by set rules, and named by span within block where a consumer names an item.
The packet builder, the recompute-and-compare, the hash dictionaries, the id round trip, the
double wire copy and the per-member rows in the support export have nothing left to do.

Withdrawn for rich graph members, and not proposed for formal and construction inventories,
whose content-hash ids are identities.

*Conditions and costs.* Product identity includes the body, so every product of an affected kind
and every downstream request key changes; data is regenerable, and the cost is regeneration and
re-qualification. Graph inspection today shows a node per member row and would stop doing so for
these kinds, which is a visible change to decide. The detached verifier maps members by key and
changes with it. Why the existing projection tables found no adopter should be answered before a
second typed-table mechanism is built.

<a id="O12"></a>
### O12 — One reference model

One reference type and one resolver in Python now. Closure checked at admission for references
within a release once a rule vocabulary exists to declare it. Adds the missing checks; removes
per-family resolvers.

<a id="O13"></a>
### O13 — Carry validated values

Decode each input once and keep it. Memoise typed wrappers so `value`, `reference` and
`semantic_id` cost once. Memoise the derivation of token and sentence rows from an annotation.
Make acquisition the only constructor of a source object and acquire once per process. Bracket a
computation with one verification of loaded sources. Drop the second deep copy, the second file
read, the self-checked receipt digests and the per-call descriptor rebuild. Local, with no
published value changed and no native revision. Absorbs O08's decode-once.

<a id="O14"></a>
### O14 — One stance on validity at hand-off

In process and at once: use the formal proof where it is ignored, and decide what a consumer does
with a product whose producer has no validator and with one whose proof it does not check. With a
native revision: give the sentence product a proof contract, which stops five consumer modules
re-running its validator. The contract set is a closed list checked in generated programs, the
proof matches only within a release, and PostgreSQL checks the record's correspondence, not that
validation ran.

<a id="O15"></a>
### O15 — Compute derived data once

Within a process, by O13's memoisation. Across operations, where consumers need what a producer
computed: the sentence operation's full token and sentence rows, the constructions operation's
navigation index, the math extract's formula contexts with the stage key binding them to
configuration. The second form changes product bodies and goes with O11.

<a id="O16"></a>
### O16 — Keep the answer the database gave, and ask it more

Keep the use-to-product join the read program already returns instead of stripping it. Add
member, kind and record-type filters and member paging to the existing program, which already has
frontier, products and support views. Give online-only readers the answer shape they need. One
frontier walk, one root selector and one cursor scheme replace four, four and six.

The replaying family (structures, dossier, gaps, journey) keeps one implementation over the raw
subgraph and gets no separate database answer, since one implementation over two sources is what
makes replay meaningful. Absorbs O05 and O06.

*Cost.* Each change is a revision of a pinned, generated program and repeats per-row disclosure.
Which readers are online-only was read from call sites and not established for every evaluation
reader.

<a id="O17"></a>
### O17 — One derivation of the access columns, one document rebuild

Derive the relational access columns (pointer, parent, ordinal, label, section owner, regions)
inside PostgreSQL once at publication from the certified rows. Leave the JSON copy staged and
reconciled: deriving it would mean a third row-to-JSON implementation and a number-spelling
contract, and the reconciliation already achieves the end. Make the proven rebuild the one
transforms use, which removes the second algorithm without adding a whole-document digest pass.
Absorbs O04.

<a id="O18"></a>
### O18 — One document, one decode, one hash per boundary in the PDF path

Hold one validated document per process and validate before lowering and across the worker
boundary; decode a page payload once per boundary; hash a file at acknowledgement and after any
gap; supply the build identifier at load instead of storing it in every row. With O02 and O03.

<a id="O19"></a>
### O19 — Evaluation preflight reduced to what only Python can check

Keep the coordinate check and the kernels. Rely on the binding and the completion guards for the
facts they establish.

### Correspondence with the first publication

| First publication | Now |
|---|---|
| O01 schema derivation when a consumer needs it | Stands |
| O02 certify without round trips | Stands, as narrowed |
| O03 typed validation capture | Stands |
| O04 one node relation | Absorbed by O17 |
| O05 cheaper lookups on the present store | Absorbed by O16 |
| O06 typed relations for selected records | Absorbed by O16; the Parquet write stands |
| O07 one span vocabulary in Python | Stands |
| O08 decode once | Absorbed by O13; the Arrow worker packet stays withdrawn |
| O09 convert logical rows by column | Stands |
| O10 fidelity rules in the analytical owner | Stands, when a second consumer arrives |
| The broader direction | Unchanged: a kernel family rewritten as set operations, by operator decision |

## Defects found

Confirmed by reading; none executed.

1. **Two readers take a field the export omits** **[V]**. `semantic/selected_contribution_input.py`
   (`actual_graph_inputs`) and `semantic/grouped_interpretation_projection.py` read
   `request["binding"]`; the support export removes `binding` from request records in SQL, as
   declared in `model/semantic/selected-support.yaml`. The only test reaching the code supplies
   the field in its own fixture, and no native test was found that reaches it on real rows.
2. **References stored in product bodies are not validated after publication**, and `roots` and
   `environment` of the contextual meaning product were reported to have no dangling check
   (not re-verified).
3. **The round-trip validation uses default policy where the producer uses the captured policy**
   **[V]** (`semantic/pdf_publication.py`, `_native_validation_child`). Equal at publication;
   differs for a forced or later re-validation of an older publication.
4. **Consumers of construction products check identity only** **[V]**
   (`semantic/predicate_products.py`, `semantic/scoped_products.py`).
5. **No production caller:** `evaluate/record_statistics.py` **[V]**;
   `evaluate/alignment_preparation.py` and `semantic_values.py`, reachable only through
   `semantic_alignment.py`, of which production uses one type. The per-frame identity read. Parts
   of `semantic/record_projection.py` were reported unused and not re-verified.
   `select_pdf_integration` has no production caller but is the independent check in the
   streaming reconciliation tests and should stay while they rely on it.
6. **Smaller:** the recognition replay builds its sort key and pin column from the same value;
   `docs/pins.md` describes the duckdb hold by a module that no longer exists; the served-row
   codec's docstring names a disk tier that does not exist.

## Declined, and what stays

From the first publication: byte-budget paging, the JSON documents that are contracts, attaching
PostgreSQL from DuckDB, a second connection for interactive reads, an Arrow worker packet, a
second identity encoder. Added by this revision: a DuckDB span layer ahead of a kernel rewrite;
DuckDB as the offline engine ahead of a rewrite of the replaying projections; deriving the JSON
access copy in SQL; a whole-document digest check on transform input. Required as they are: the
per-row PDF identity fold, the page payload encoding, publication of recognition observations,
spool custody, the worker's code check, claim and support re-checks, and the evaluator
separation.

## Rule impacts

1. **What a product body holds, and identities** (O11, the cross-operation part of O15). A
   decision record and a native revision; regeneration of affected products.
2. **Custody statements in code** (O13): that a retained port is not a durable permission, and
   that wrappers revalidate owned bytes. The proposal keeps the ends, a single bracket and a
   single constructor, and changes the mechanism.
3. **The validity proof** (O14) gains a contract; its meaning is unchanged.
4. **Read programs** (O16) change within the existing rule that reads go through
   security-definer programs.
5. **[ADR-0135](../adr/0135-declared-facts-and-typed-database-programs.md)** and
   **[ADR-0026](../adr/0026-columnar-semantic-operations.md)**: nothing here conflicts with
   either. Neither contains a rule about attaching PostgreSQL or a row threshold for DuckDB.
6. **Store ownership.** [DESIGN §2](../design/DESIGN.md#section-2) records five invocation-owned
   SQLite stores; O02 changes what one holds.

## Order and relation to current work

1. **No native revision, no identity change:** defect 1; O13; the in-process parts of O14 and
   O15; keeping the join in the index (the first step of O16). By the hand-off trace this removes
   most repeated validation and rebuilding.
2. **Program revisions without identity change:** the rest of O16; O17; O18 with O02 and O03;
   O19; the sentence proof contract of O14.
3. **A decision on T1 and T2** (O11, O12, the rest of O15), with its regeneration cost.
4. **The broader direction**, only if chosen.

**A timing choice for the operator.** Domain Model Operability ends with a whole-book run on an
adopted final release. O11 changes identities that run would qualify. If O11 is wanted, deciding
it before that run avoids qualifying twice; if it is uncertain, steps 1 and 2 deliver most of the
benefit without it. Nothing here is approved scope.

**What would demonstrate the design.** For step 1: one chain, sentences to scoped relations, run
with results and receipts unchanged and each product validated once and each source acquired once
per process. For O11: sentence products published as a token and a sentence population with set
admission, their consumers reading rows and naming tokens by span, and the re-derivation code
gone.
