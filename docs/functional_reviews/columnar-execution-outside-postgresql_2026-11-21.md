# Columnar execution outside PostgreSQL: functional extension review

**Proposed · 2026-11-21.** The operator asked whether the model-driven design now makes it
practical to move what executes outside PostgreSQL onto DuckDB 2.0 and PyArrow, on one columnar,
model-derived basis. The answer has two parts. The row operations performed today can be
expressed as window functions, span joins, grouped aggregates and set operations, through typed
expressions and with matching results; that was tested. But expressing them is mostly not where
the gain is. The waste the code shows is redundant serialization: the same rows encoded to JSON,
copied into SQLite and decoded again, several times per pathway. Most of it can be removed where
it stands. A columnar engine pays in a narrower set of places than the hypothesis hoped, because
the consuming end of most steps is per-row Python: hash folds, the value codec, pydantic,
validators, and spaCy, Lark and Docling objects. A broader shift is possible, but it is a decision
to rewrite kernels against relations, not something that follows from the changes already made.
This review recommends the removals, states where columnar execution fits now, and describes the
broader direction with the trial that would decide it. PostgreSQL keeps every responsibility it
has today.

## Scope and evidence

The lens was the operator's: take the row operations performed today, ask whether each can be
expressed as a window function or otherwise in columnar terms, and ask what that unlocks next.
Two scope decisions were taken on 2026-11-21: the form in which rows cross the PostgreSQL boundary
and reach worker processes is in scope, and accepted rules are worked within by default and
reopened only where one blocks a valuable opportunity.

`cs/` means `python/corpus-structure/src/corpus_structure/`. The `*_native.py` generators and
`semantic/_pdf_native_calls.py` produce programs that run inside PostgreSQL; they are the boundary
and were not analysed. The Rust crate is outside the review.

**Inspected · 2026-11-21.** By operator direction the review reads current code and not earlier
documents; the 2026-11-18 analytical inventory and its placement table are not premises. Three
code-only passes traced the pathways end to end and then applied the lens step by step: the PDF
path, declared-operation execution with its kernel families, and reads, exports, change impact and
evaluation. They read the tree at `c671c2fbf`. An independent design assessment then challenged
the draft at head `8597d8ba6` with twelve production files carrying uncommitted Domain Model
Operability edits; it withdrew or narrowed five of ten draft opportunities, and this document is
the result. Line references are to that working tree and will drift while that work continues;
function names are given where drift was seen.

**Tested · 2026-11-21.** `uv run python docs/design_review/evidence/2026-11-21_columnar-execution-review/columnar_fidelity.py`
ran on duckdb 2.0.0 and pyarrow 26.0.0 over synthetic rows in memory. Statements marked **[F]**
cite its lines. The passes also compared DuckDB expressions with production functions on random
synthetic inputs; those are reported as **observed in review, not retained**.

**Not established.** No timing was taken and no benefit is quantified. Row volumes are the bounds
and batch sizes the code declares. O03 and O04 were not independently challenged in detail.

Library orientation came from the [DuckDB 2.0](../libraries/analytical_infrastructure/duckdb_2.md),
[DuckDB CLI](../libraries/analytical_infrastructure/duckdb_2_cli.md) and
[PyArrow](../libraries/analytical_infrastructure/pyarrow.md) overviews and the installed
packages. Design judgment applies FP-04, FP-07 and A4 of the
[design standard](../design_review/design_principles/standard.toml).

## What runs outside PostgreSQL today

### The PDF path

`ingest/`, `orchestrate/pdf_streaming.py` and `semantic/pdf_*` take an original to published
records. Lowered records, companions and candidate pages are Arrow IPC files with model-derived
schemas (`semantic/pdf_record_model.py:105-127`, `semantic/pdf_payloads.py:87-123`), and adoption
into PostgreSQL is Arrow to binary `COPY` (`semantic/arrow_transfer.py:134-171`). Between those
points the rows change form repeatedly. In certification each native row goes `to_pylist`,
`json.dumps`, a SQLite table, `json.loads` (`semantic/pdf_certification.py:142-160, 286-296`);
artifact part bodies are hex-encoded on the way in and decoded again (`:157`,
`semantic/pdf_payload_validation.py:118-125`). Identity frames are then computed per row in
Python, written to a second table and read back in key order for the fold (`:286-350`). After
publication, validation reads the frozen rows from PostgreSQL as JSON, writes them to an Arrow
file whose two columns are a family name and a JSON string, and loads a second SQLite store
(`semantic/pdf_publication.py:542-565, 822-846, 286-300`).

### Declared operations

Every operation pays the same envelope around its body. PostgreSQL selects inputs and returns
references. Bodies are fetched one row at a time as tagged JSONB, deliberately, so the packet
capacity check can run before a batch arrives (`semantic/data_operation_consumers.py:235-237`).
Each is decoded and canonically re-encoded (`:244-249`), then decoded again on each of two later
calls (`:65-72`, called at `orchestrate/data_operations.py:1046, 1059`); the decoder itself
re-encodes to check canonical form (`semantic/data_operation_value_codec.py:17-24`). Arguments are
validated per role, dumped and re-validated, deep-copied (`semantic/data_operation_ports.py:211-213, 820`),
serialized as JSON strings inside a JSON packet for a spawned worker
(`semantic/data_operation_cpu.py:115-140`), validated in the worker, and the reply validated twice
in the parent (`data_operation_ports.py:600, 934`). Operations never hand data to each other;
every hop is a publication and a new read.

The bodies are about fourteen kernel families in `methods/` and `semantic/`. Much of their row
logic is positional: tokens, sentences, pieces, blocks, formal atoms and annotations are half-open
character intervals. About twenty interval indexes answer containment, overlap and nearest
questions, each built by its consumer; they are bisect-based and logarithmic, and kernels call
them as point queries interleaved with procedural logic. Inputs are whole nested products
validated as pydantic models, which the kernels walk as objects.

### Reads, exports, change impact and evaluation

PostgreSQL answers a selected read with one JSON document per call
(`semantic/data_operation_storage.py:98-132`). Support rows are copied into a SQLite scratch table
as JSON blobs with expression indexes (`semantic/data_operation_read_index.py:16-50`), and every
lookup parses the whole row and projects it through the captured contract (`:79`,
`semantic/selected_support_contract.py:163-183`). That index is the hub for contributions,
structures, dossier, exclusions, graph inspection, change impact, export verification and
evaluation. By executed work point lookups dominate, because they sit inside Python loops and
repeat: about five per output row in the contributions reader, several for the same row
(`semantic/selected_contribution_input.py:80-121`). The keys are columns; what consumers read is
mostly inside nested JSON.

### Columnar footholds already present

DuckDB has one owner with an expression-only relation wrapper and three consumers
(`cs/analytics.py`: candidate geometry, the recognition replay sort, companion inventory and
comparison). Arrow schemas are derived from the model in four places
(`semantic/arrow_types.py:13-33`, `pdf_record_model.py`, `companion_projection.py:497-516`,
`pdf_payloads.py`). Companion export brings rows out of PostgreSQL as Arrow under an imported
read-only snapshot (`serve/companion_export.py:123-198`). The detached export writes Parquet per
support relation from a captured Arrow schema (`serve/demand_export.py:369-433`).

## What the lens found

**The window and span forms are available as typed expressions.** Containment as an inequality
join, ordinal within parent, previous-end gaps, running sums with row frames, integer range
frames, gaps-and-islands, first-per-key, nearest preceding by ASOF join and bag difference all
gave the expected rows without SQL text **[F: E1–E8]**. Recursion is the one form the expression
interface lacks.

**Ordering agrees where digests depend on it.** DuckDB's default string order, PyArrow's sort,
SQLite's `BINARY` collation and Python's string order all equal UTF-8 byte order on mixed-case,
multi-byte, astral and prefix keys **[F: O1]**.

**Identity bytes belong to Python.** DuckDB's JSON equals the project's canonical bytes only for
strings, integers, booleans and nulls with fields in sorted order **[F: I1–I2]**; floats and
decimals are spelled differently **[F: I3–I4]**, and sequential hash folds are not aggregates.

**Several look-alike functions are not equivalent.** Regular-expression classes are ASCII-only
with no lookaround, edit distance counts bytes, `bool_and` over no rows is null where `all([])`
is true, float sums differ from Python 3.14's, NULLs sort last where the project's keys put
`None` first, a dense Arrow union does not import, and an extension type over text comes back as
plain text and sorts as text **[F: S1–S5, O3, X1–X2]**.

**The consuming end is usually per-row Python.** This is what limits the hypothesis. In the PDF
certification store, the one place that is Arrow on both sides at rest, the frames the fold
consumes are not in the files: each is computed in Python from nested JSON columns with a lookup
per field (`semantic/pdf_records.py:874-896`), and the membership sort key is derived, not a
column (`:925-932`). In the read hub, values are inside JSON bodies. In the kernels, span queries
are point queries inside procedural code over object trees. In each case a relation in the
middle is converted from objects and back to objects.

**Size argues against most isolated moves.** Structural comparison works on two passages, table
interpretation on at most sixteen edges, model batches on eight or sixteen items, interactive read
pages on one to a hundred rows. A keyed filter through DuckDB over a hundred thousand rows took
about a millisecond in the challenge's check, against a dictionary lookup.

**Some work is not row-shaped.** Docling tree edits, record lowering, parser forests, model
inference, sympy, the rule engine, graph algorithms, greedy selections, and the reconciliation
matching loop, where each decision changes the candidate set the next one sees
(`ingest/pdf_reconciliation.py:699-1005`).

So the second-order question has a conditional answer. Moving one step unlocks its neighbours
only if the neighbours' inputs and outputs are relations too. They are not today, and making them
so means writing kernels against columns in place of objects. That is a coherent target and this
review describes it under [the broader direction](#the-broader-direction), but it is a choice, and
the evidence here supports the narrower set first.

## Opportunities

<a id="O01"></a>
### O01 — Unify the Arrow schema derivations when a consumer needs it

Four mechanisms derive Arrow schemas from the model, and pydantic adapters for every kind are
built in one walk (`semantic/boundary.py:106-276`). One derivation beside that walk would serve
all of them. It was drafted as the keystone for everything else; with O07 to O09 narrowed it has
no new consumer, so it should happen when one appears, not ahead of it.

Two facts shape any such derivation. The value codec has forms with no faithful Arrow type:
unbounded integers, scale-free decimals of up to 16,384 digits, the optional states, bag and set
order by tagged bytes, and `linkml:Any`. Held as extension types over text they survive in
PyArrow but are opaque to DuckDB, which returns plain text and sorts it as text **[F: X1–X2]**.
And ADR-0026 fixes the analytical decimal profile at precision 38, scale 12, with originals
intact; a derived numeric column is that bounded projection, never the exact value. Optional
fields that default to missing, distinct from null (`boundary.py:227-233`), need a presence mask.

<a id="O02"></a>
### O02 — Certify PDF records without the round trips

**What changes.** The producer's store stops holding native rows and part bodies. The
`native_entry` table is a pass-through: rows are inserted as JSON and read back once, unordered
(`pdf_certification.py:142-160, 286`). Certification iterates the IPC batches directly in two
passes, stream descriptors first, and builds frames as it does now. The hex encoding and decoding
of part bodies goes. The JSON read-back of the access projection
(`pdf_payload_validation.py:354-359`) goes; the projection file is still written, as a retained
custody artifact.

**What stays.** The frame build, with its nested JSON decode and per-field descriptor lookup. A
disk sort of the derived `(family, key, frame)` set, which is all the `identity_frame` table does;
whether SQLite keeps that job or DuckDB sorts a temporary Arrow file is a secondary choice with
no evidence either way. Keyed access for the validators, which read fields, streams and parts by
key from inside procedural checks (`pdf_payload_validation.py:81-89, 214-303`) and write page rows
whose primary key is the duplicate-page refusal (`:333-346`); a dictionary index over the mapped
batches or the existing store serves that, and DuckDB should not.

**Scope.** The producer side only: `certify_native_stream`, draft publication
(`orchestrate/pdf_streaming.py:969-972`) and recertification
(`semantic/pdf_spool_recertification.py:123-126`), where the IPC files are present and verified.

**Fidelity conditions.** The inputs to the folds pass through normalizations that are part of
each digest's effective definition: nulls dropped after a JSON round trip, key-presence tests
(`pdf_records.py:904`), and companion bodies parsed to float before `Decimal`
(`pdf_certification.py:91, 158-159`). The acceptance test is that retained certifications and a
real recertification reproduce their recorded digests, over a corpus that includes
exponent-spelled floats, null against absent columns, and non-ASCII keys. A miss fails loudly at
`pdf_spool_recertification.py:136-140`. Every SQLite primary key that is today's uniqueness
refusal becomes an explicit check.

<a id="O03"></a>
### O03 — Validate published records from typed rows

The validation child's source is the PostgreSQL read-back and must stay so, since it validates
what was published. The capture can still write one typed Arrow table per family, using the stage
and companion schemas, in place of JSON strings in a two-column file, which removes one JSON
encode and decode per frozen row. The child already holds every header, native and membership row
in Python lists (`pdf_publication.py:287-306`), so its SQLite load is not protecting memory. The
membership checks made during reconstruction (`pdf_records.py:724-762`) can run first as two
window queries: ordinal equals position within `(parent, field)`, and count equals declared
length. Reconstruction, the Docling callbacks and the canonical digest stay. Not independently
challenged in detail.

<a id="O04"></a>
### O04 — One node relation for the published document

The access projection (pointer, parent, ordinal, section owner, regions) is rebuilt as a
dictionary walk by several validators: `semantic/pdf_ocr_contracts.py:203-424`,
`semantic/pdf_report_validation.py:52-192`, `semantic/pdf_integrated.py:104-402` and
`ingest/pdf_selected_enrichment.py:116-166`. Building it once and passing it would remove the
repeats. OCR page checks over the candidate batch are the densest nested loop on OCR pages and
have direct kernel forms: uniqueness by a partitioned count, monotone word ranges by `lag` over
list position, coverage with `pyarrow.compute.utf8_is_space`, since the DuckDB class is ASCII-only
**[F: S1]**. The preorder walk is recursive and small; it stays a Python walk. Whether Docling
guarantees that parent references and child lists agree decides whether section owners may be
inherited along the traversal. Not independently challenged in detail.

<a id="O05"></a>
### O05 — Make the selected-record lookups cheap where they stand

**What changes, on the present store.** A memoizing mapping, so the contributions loop does not
re-parse the same kind, request, episode and product rows. A key-only existence query, so
membership tests such as those in `verify_detached_result` (`semantic/demand_results.py`, the
endpoint-closure checks near `:1171`) do not parse a whole row including its body to answer yes or
no. Semi-joins in place of scan-then-filter where a keyed path already exists:
`evaluate/selected_references.py:555-631`, `evaluate/declared_operation_events.py:400-405`,
`semantic/data_operation_source_sets.py:399-410`.

**Withdrawn from the draft.** Rewriting detached-result verification as joins. One side of its
multiset comparison is a sealed payload inside a JSON body with a per-definition role
classification, the surrounding work is identity recomputation that stays in Python, and a join
would change which refusal is raised first.

<a id="O06"></a>
### O06 — Typed relations for selected records, after the consumer migration

**What it offers.** One firm gain: the detached export writes Parquet from tables instead of
converting each row to a dictionary and JSON strings (`serve/demand_export.py:369-433`); the
export's own spool (`closure.sqlite`, `:190`) shares the index's shape and is the natural first
place. A possible gain: scans and set comparisons for the readers that load whole relations
anyway, such as `semantic/selected_graph.py:58-63`.

**Why it waits.** Domain Model Operability states that the index keeps its deduplication, bounds,
freeze and lifetime, that its ingress is the captured byte boundary, and that replay uses captured
contracts even when ambient declarations change. A typed table must therefore keep the exact
payload bytes as a column and take its schema from the captured Arrow schema
(`demand_export.py:382-384`), not from current metadata. Point lookups dominate the hub and are a
reason not to put DuckDB under them; O05 captures most of the cost on the present store. Revisit
after DMO-04 and DMO-05's consumer migration, with those two conditions.

**What must not change in any case.** Export page files and `closure.jsonl` are replayed by
verification and keep today's bytes. The cut identity, the page hash in cache keys and the recheck
stamp are computed from the JSON form.

<a id="O07"></a>
### O07 — One span vocabulary, in Python

**What changes.** The interval indexes share one small set of queries: contains, overlaps (with
today's zero-width rule at a shared boundary), nearest enclosing by width then ordinal, nearest
preceding or following within a partition, merge of touching spans, ordinal within parent, and
offset translation, all returning rows in original order. `PositionedRows`
(`semantic/positioned_rows.py:8-44`) and the cached views of `semantic/native_source_view.py:128-229`
already provide part of it. Extending those and retiring the private indexes gives one owner for
span semantics. Two rescans are worth fixing as they are found: the per-piece rescan that merges
formal pieces, which is quadratic (`semantic/formal_products.py:484-489`), and the per-sentence
scan over a block's tokens (`semantic/sentence_products.py:235-239`).

**Withdrawn from the draft.** A DuckDB relation layer for these queries. The sentence family,
proposed as the first, has almost no span joins: token-to-sentence membership is an index spaCy
already supplies, and the body is a tree walk, the tokenizer, a host round trip and hashed ids. A
batch join needs every query known in advance, and the kernels ask them one at a time.

<a id="O08"></a>
### O08 — Decode operation inputs once

**What changes.** The hydrated value keeps its decoded form, so the two later calls do not parse
and decode again; that removes two of three decodes in a few lines. The deep copy and the
dump-and-revalidate round trip are isolation choices worth re-examining on their own terms.

**Observed defect, latent.** At `data_operation_consumers.py:244` the decoded value is passed to
`canonical_bytes`, which accepts only JSON types and `Decimal` (`semantic/identity.py:16-19`). A
body carrying a date, an optional state or a collection value would raise. No operation kind was
found that carries one; whether any can was not established.

**Withdrawn from the draft.** Arrow IPC as the worker packet. The request digest is taken over the
packet bytes and published in the execution receipt (`semantic/cpu_execution.py:204-224`). IPC
bytes are not canonical, so an IPC packet either ties execution evidence to PyArrow's writer or
needs a canonical encoding beside it, which returns the saving. The shared-memory capsule is
allocated per release, not per call; per-call segments would need new budget and lifetime
ownership. This should meet the bar the current plan sets for a codec change: a demonstrated
bottleneck.

**Conditional.** Fetching `ops.data_binding_rows` as Arrow, and model hosts returning columns in
place of line-delimited JSON, have value only with consumers that take columns; see the broader
direction.

<a id="O09"></a>
### O09 — Convert logical rows by column, with the existing encoder

The companion export's logical-row digest converts each cell individually
(`semantic/capture_storage.py:56-67`). Converting whole columns and feeding the same encoder gave
an identical digest on a mixed-type batch (observed in review, not retained), and the strict-order
check is one comparison with the previous key.

**Withdrawn from the draft.** A column-wise canonical encoder. The encoder is one call into the
standard library's JSON writer; a second implementation would be per-row string assembly with no
speed argument and a second owner of identity bytes, while DMO-02 is still inventorying digest
roles.

<a id="O10"></a>
### O10 — State the fidelity rules in the analytical owner, when the next consumer arrives

`cs/analytics.py` already fixes the time zone and refuses text. The differences in
**[F: S1–S5, O2–O3, X1–X2]** are silent, and each new kernel would rediscover them. When a second
set-shaped consumer appears, the owner should fix binary collation alongside the time zone,
require NULL placement in sorts, require a tie-break for ASOF joins and an order for list
aggregates, and say where a kernel author would look that regular expressions, edit distance and
JSON text for identity are not offered. Two conditions: DuckDB's and Arrow's thread pools are
outside the worker's thread limit and the pool inventory that receipts record
(`semantic/cpu_execution.py:243-246`), and a long DuckDB operation is not interrupted by
`check_active()`.

## The broader direction

The operator's intent is a unified basis for everything that cannot live in PostgreSQL. The code
supports a version of it, at a cost the changes so far do not pay.

**What it would be.** Record kinds have a columnar form as first-class as their pydantic form.
Operation inputs arrive as relations of pieces, tokens, sentences and annotations. Kernels are
written as relational steps around their procedural cores, each core taking a table and returning
one: region and terminal tables into Lark, token columns into the spaCy matchers, expression
tables into sympy, claim views into the rule engine. Model hosts return columns. Canonical bytes
are produced at publication from ordered columns by the one existing encoder.

**Where the relational steps were shown to work.** Against production functions on random inputs,
with no mismatches (observed in review, not retained): the three `PositionedRows` queries,
nearest-enclosing in math scope, sentence-region clipping, requested-region merging, table
geometry, and running positions in contextual input. The families with the most real span and
join work are formal evidence, scoped relations, constructions' region handling, source
preparation, math layout and predicate clipping.

**What it costs.** Every kernel family rewritten against a second representation; value forms that
do not fit Arrow natively; execution evidence redefined; and no gain at the sizes most operations
see unless connections and data persist across calls in a worker.

**What would decide it.** One family rebuilt end to end, chosen for real span work and a clean
procedural core. Formal evidence is the candidate: its span steps (maximal and crossing atoms,
merging, atoms per region) are batch-shaped, and its cores (Lark, the lexical classifier) take
and return tables. The trial answers three things that reading cannot: whether the kernel is
simpler to state, whether published members stay byte-identical, and whether per-call overhead is
acceptable. It is a decision for the operator, and it should follow O01 only as far as that one
family needs.

## Declined, and what stays as it is

- **Byte-budget paging and offset cursors.** Widths are the encoded JSON bytes of each row and the
  envelope varies with the cursor (`semantic/selected_pages.py:7-73`); a window would approximate
  and then need the same exact check.
- **The JSON documents that are contracts.** The cut header, export page and closure files, the
  feature-fit frame compared byte for byte, MCP structured content, and the wire contract.
- **Arrow delivery of selected reads through a second connection.** ADR-0026 accepts ADBC as a
  read transport over an imported read-only snapshot. A selected read writes a receipt in its own
  transaction, which an importing session does not see, and pages are small.
- **Attaching PostgreSQL from DuckDB.** Nothing found needs it.
- **Candidate capture, record lowering, Docling edits, reconciliation matching, recognition.**
  Object-graph or model work, or small, with orderings that feed published identities from Python
  insertion order (`ingest/pdf_candidates.py:191-219`, `ingest/pdf_reconciliation.py:1139, 1160`).
- **Release archive comparison, model and source comparison, record alignment, fits, graph
  algorithms, reciprocal-rank fusion.** Small, numeric with a pinned backend, or sensitive to
  float summation **[F: S4]**.
- **Change impact and identity-exclusion classification.** Expressible as full outer joins over
  Python-computed keys, with little gain.
- **Native source export.** A grouped form would change number spelling with no stated consumer
  need.

## Rule impacts

1. **ADR-0135** ([declared facts and typed database programs](../adr/0135-declared-facts-and-typed-database-programs.md))
   requires typed expressions for DuckDB over an immutable identified snapshot and says SQLite
   remains a typed local store. The window and span forms need no SQL text, so the expression rule
   does not block anything recommended here.
2. **ADR-0026** ([columnar semantic operations](../adr/0026-columnar-semantic-operations.md))
   makes PyArrow the owner of columnar representation and DuckDB the one local relational engine,
   with ADBC importing a read-only snapshot and a fixed analytical decimal profile. It contains no
   rule about attaching PostgreSQL; that statement exists only as a rejected alternative in the
   superseded Unified Domain Model plan. Nothing here conflicts with ADR-0026.
3. **The size threshold for DuckDB** (set-shaped work over roughly ten thousand rows) is in that
   superseded plan and in no accepted record. This review's working filter, that a step is worth
   making columnar when its inputs and outputs are already columns, is offered as a better test
   than size. Adopting it as a rule would be a new decision, and it is a filter, not a direction
   of travel.
4. **Store ownership.** [DESIGN §2](../design/DESIGN.md#section-2) records five
   invocation-owned SQLite stores and per-invocation DuckDB spill as implemented. O02 changes what
   one of those stores holds; replacing a store outright, or holding a DuckDB connection for a
   worker's lifetime, changes those owner statements and chooses between real alternatives, so
   either needs a decision record.

## Order and interactions

1. **O08's decode-once and its latent defect, and O05.** Small, local, and independent of
   everything else.
2. **O02, then O03.** The largest row volume. They change no published value by intent, but they
   touch certification, which Domain Model Operability is qualifying; schedule them after DMO-08
   or as a deliberate part of it.
3. **O04, O07 and O09** as the code is next worked in each area.
4. **O06** after DMO-04 and DMO-05's consumer migration.
5. **O01 and O10** when a consumer needs them.
6. **The broader direction** only by operator decision, starting with the formal-evidence trial.

No opportunity here is approved scope.

**What would demonstrate delivery.** For O02 and O03, retained certifications and a real
recovery-recertification reproduce their recorded digests on the stated corpus. For O05 and O06,
the existing reader, export and verification tests pass with expectations unchanged and export
page and closure bytes identical. For O08, operation results and receipts are unchanged.

## Observations outside the opportunities

- `ingest/pdf_stream_reconciliation.py:262-263` builds both the sort key and the pin column of the
  recognition replay from the same value.
- `docs/pins.md` describes the duckdb hold in terms of a module and a test directory that no
  longer exist.

## Step records

### Fidelity checks

| Mark | Statement | Result |
|---|---|---|
| E1–E8 | Span join, ordinal, lag, running sum, range frame, islands, first-per-key, ASOF, bag difference as expression objects | as expected |
| O1 | UTF-8 byte order across DuckDB, PyArrow, SQLite `BINARY`, Python | same |
| O2 | Order of a JSON-text key against byte order of its parts | differs |
| O3 | NULL placement against the project's `None`-first keys | differs |
| I1–I2 | DuckDB JSON and SHA-256 against canonical bytes, strings and integers, sorted fields | same |
| I3–I4 | Float and decimal spelling | differs |
| S1 | Regular-expression whitespace and word classes on non-ASCII | differs; PyArrow's kernel agrees with Python |
| S2 | Edit distance on non-ASCII | differs |
| S3 | `bool_and` over no rows against `all([])` | differs |
| S4 | Float sum against Python 3.14 `sum` | differs |
| S5 | Dense Arrow union into DuckDB | refused |
| X1–X2 | Extension type over text through DuckDB | returns text; sorts as text |

### Kernel families

| Family | Dominant row work | Procedural core | Disposition |
|---|---|---|---|
| Sentences and tokens | grouping, ordinals, hashed ids | spaCy, tree walk | stays; fix the token-list scan (O07) |
| Canonical projection | projection, membership | none | stays; small |
| HanLP | membership, batching | model, constituency walk | stays |
| Formal evidence | maximal and crossing spans, merge | Lark, lexical classifier | O07 now; trial candidate |
| Constructions | merge, overlap, nearest, grouping | Lark, spaCy matchers, evaluator | O07; broader direction |
| Structural products | small joins, greedy selection | selection | stays |
| Source preparation, M1, assembly | containment, running cursor, deduplication | cursor, window expansion, assembly | O07; broader direction |
| Scoped relations | keyed and rectangle joins, grouping | Python regular expressions | O07; broader direction |
| Table and finite interpretation | grouping, numerics | numpy solver | stays |
| Contextual | running positions, ranking, fusion | encoder, fusion sum | stays |
| Learned primary | batching | models | stays |
| Math | interval sweep, nearest preceding | Lark, sympy | O07; broader direction |
| Rich consolidation and rules | grouping, joins | rule engine, graph | stays |
| Scientific evidence | numerics | sympy, sampling | stays |
| Predicate evidence | overlap and merge | spaCy frames | O07 |

### PDF path

| Step | Where | Disposition |
|---|---|---|
| Spool inventory and recovery | `ingest/pdf_build_spool.py:290-322` | stays |
| Conversion, page envelopes | `ingest/pdf.py:282-478`, `ingest/pdf_streaming.py:145-278` | stays |
| Candidate capture | `ingest/pdf_candidates.py:97-321` | stays |
| Record lowering | `semantic/pdf_records.py:363-617` | stays |
| Rows into the certification store | `semantic/pdf_certification.py:142-194` | O02 |
| Frame build, sort and folds | `:257-350` | frame build and folds stay; sort engine open |
| Validators' keyed reads | `semantic/pdf_payload_validation.py:214-372` | keyed index; not DuckDB |
| Access projection, page and coverage checks | `semantic/pdf_access_projection.py:11-96`, `semantic/pdf_ocr_contracts.py:77-424` | O04 |
| Validation capture and child | `semantic/pdf_publication.py:802-917, 278-354` | O03 |
| Enrichment geometry, replay sort | `ingest/pdf_candidate_geometry.py`, `ingest/pdf_stream_reconciliation.py:314` | already DuckDB |
| Inline anchoring, cell classification | `ingest/pdf_enrichment.py:134-530` | stays |
| Reconciliation matching | `ingest/pdf_reconciliation.py:699-1005` | stays |

### Reads, exports and evaluation

| Stage | Where | Disposition |
|---|---|---|
| Page arrival and cut identity | `semantic/data_operation_storage.py:98-132`, `semantic/demand_results.py` | stays JSON |
| Query rows, cache, paging | `semantic/demand_query_projection.py`, `selected_query_cache.py`, `selected_pages.py` | stays |
| Record index lookups | `semantic/data_operation_read_index.py` | O05 now; O06 later |
| Contributions, evaluation readers | `semantic/selected_contribution_input.py:62-336`, `evaluate/selected_references.py` | O05 |
| Detached verification | `semantic/demand_results.py` (`verify_detached_result`) | key-only membership (O05); otherwise stays |
| Detached export Parquet | `serve/demand_export.py:369-433` | O06 |
| Export page and closure files | `serve/demand_export.py` | stay |
| Companion logical rows | `semantic/capture_storage.py:56-67` | O09 |
| Companion inventory and comparison | `serve/companion_export.py:431-637` | already DuckDB |
