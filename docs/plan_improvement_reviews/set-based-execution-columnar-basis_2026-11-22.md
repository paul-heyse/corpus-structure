# A typed, set-shaped basis for Set-Based Execution through SBX-09

**Review date and baseline.** Inspected on 2026-11-22 at `b5ff78b22` with a clean tree. The
reviewed coordinator is [Set-based execution](../plans/set-based-execution_2026-11-21.md) with
its eight companions. The footprint is the production code of SBX-01 through SBX-09 under
`python/corpus-structure/src/corpus_structure/`, the shared wire, port, JSON and completion
modules, the generated native routines of the frozen root `semantic_sbx_current_root`, the
existing Arrow and DuckDB owners, and the fixture preparation that qualification pays for.
SBX-10 to SBX-22 were read as consumers that the proposals would simplify, absorb or reorder.
Library baseline: PyArrow 26.0.0, DuckDB 2.0.0, adbc-driver-postgresql 1.13.0, pgpq 0.12.0,
psycopg 3.3.6, PostgreSQL 18.7.

The operator asked for a first-principles assessment of three things: efficiency across the
SBX-01 to SBX-09 scope, redesign around PyArrow and DuckDB, and use of their advanced features
where a redesign is warranted. The framing was that the design phase permits breaking change when
the functional outcome is kept, and that whole designs are assessed, not individual operations.
Every recommendation is **Proposed**. Source statements are **Inspected** at the baseline and
probe results are **Tested** on the stated date. No timing or memory measurement was taken, so
the claims are that named work is removed, not that a given speedup results.

**Independence.** By operator instruction this review did not read
`set-based-execution-efficiency-and-analytical-redesign_2026-11-22.md` or its evidence folder.
Overlap or disagreement with it is uncoordinated. The four earlier SBX reviews already integrated
into the coordinator are treated as plan baseline.

**Evidence.** Three hop-by-hop source traces, three library capability inventories and an
independent challenge of the draft were produced for this review. The retained probes are in the
[evidence folder](../design_review/evidence/2026-11-22_sbx-columnar-basis/README.md). Counts
taken from `corpus_structure_dev` describe a prior root, not the frozen one, and are marked.

## Combined judgment

The series changed *what* is stored, proved and reused, and those changes are sound: the partition
as the unit of identity, proof and reuse; rules as declarations with fingerprints; proofs keyed on
premises; computation keyed on declared reads; role-relative references; PostgreSQL as the
authority that commits product, proof and use atomically. None of that should move.

What the series did not change is the **carrier**. A population travels everywhere as one JSON
document holding a hand-typed value, and the only form any holder trusts is its bytes. Three
consequences follow.

1. **Values carry their own types, and both sides re-read them.** Values are tagged lists
   (`["integer","12"]`, `["mapping",[[key,value],…]]`). Python owns an encoder, a decoder that
   re-encodes to detect non-canonical input, pydantic models and JSON Schemas
   (`data_operation_value_codec.py:17-24,140-157`). PostgreSQL owns `data.ddo_normalize`, a
   recursive PL/pgSQL normalizer, and schema calls per item.
2. **Identity is recomputed at every holder.** A digest is sha256 over canonical text, so each
   holder that wants to trust a body rebuilds that text. One partition body is tag-encoded at
   least three times, parsed about six to ten times and serialized eight or more times between
   producer, authority, worker and consumer. In PostgreSQL `ddo_identity` normalizes again on
   each call: once for the partition and once per field group.
3. **Set work is done procedurally, twice.** Python joins with dicts, sets and SQLite tables of
   JSON blobs indexed by `json_extract`. PostgreSQL iterates `jsonb_array_elements` and resolves
   each field with `ddo_partition_field`, a linear scan of the tagged mapping per row and per
   path (`data_operation_partition_native.py:116-156,191-209`;
   `data_operation_rule_native.py:478-632`; `data_operation_reference_native.py:169-173`).

The unit of exchange also sets the unit of work. A completion is one document (the retained
sentence answer was a 92 MB request for 1,002 blocks and 25,543 tokens), so every boundary
performs whole-value passes, and retention and publication do that value processing between
taking the request-row lock and committing.

These shapes are sufficient to explain the recorded difficulty. They are not a measured cause:
the plan's attribution of the slow native endpoints is still open.

**The tagged form buys something real.** Collection declarations and schemas reach admission as
data from the kind row, and one installed routine admits every collection because each value
carries its type. That is the mechanism behind the coordinator's "a new population: one
collection declaration, no new table, program or resolver". Any redesign has to say what happens
to that property. This review keeps it.

**What the pilot did and did not decide.** The typed-population pilot compared Arrow with the
immutable carrier and kept the carrier, on the rule that a candidate must remove a complete
repeated path "without equivalent work or a second persistent authority". For what was compared,
that was right: the Arrow candidate was built from tagged rows at acquisition and converted back
to Python rows for canonical publication, so it sat between two JSON authorities and added work.
This review reopens that decision on the day it was recorded, because the comparison could not
show what happens when the typed form is the carrier from the producer onward and those
conversions do not exist. Held to the pilot's own rule, the proposal below removes the tagged
encode and decode, the frozen-tree construction and the worker packet format from the population
path, and adds no second authority.

**Recommended target.** A homogeneous population is a typed relation in process and on the wire,
and a set of item rows in PostgreSQL.

- In process it is columns: produced as columns, validated, diagnosed and digested by one set
  plan, and handed between processes as a sealed Arrow buffer.
- It crosses into PostgreSQL by binary COPY inside the authority's transaction as generic item
  rows: keys, a few typed columns for the fields that declared rules and addresses read, and each
  item's canonical text.
- PostgreSQL stays generic. It verifies digests by aggregating item text, evaluates declared
  rules and reference closure as set SQL, and stores the same rows it verified.
- The identity definition does not change, so no identifier, proof or key moves.
- JSON documents remain for headers and small control calls.

Two probe results make this credible for the cases they cover. A generated expression over typed
columns reproduced the present partition identity for 60 of 60 synthetic partitions in DuckDB and
in PostgreSQL, against both Python `canonical_identity` and the installed `data.ddo_identity`;
the covered types are integer, boolean, string, list and absent fields. And a staged typed
relation, a set-returning routine with no document parameter and a typed result worked in one
session and one transaction. **Tested 2026-11-22.**

The recommendations are one intervention. [I01](#I01) to [I03](#I03) are a single decision about
the carrier, its identity and its boundary; [I04](#I04) and [I05](#I05) follow from it;
[I06](#I06) answers the question about advanced features. [I07](#I07) to [I10](#I10) stand
largely on their own. [Integration](#integration) states the order and what is given up.

## The fundamental actions

Stated without reference to current code, delivering the outcome requires these actions on a
population.

| Action | Today | Under the target |
|---|---|---|
| Acquire provider output | Per-row dict construction | Columns built once; `pyarrow.json` with an explicit schema where the provider emits JSON |
| Establish shape | pydantic walk, JSON Schema, tagged decode with a re-encode check; schema calls per item in SQL | The Arrow schema in process; one schema check per item at the authority |
| Establish population rules | Python loops and bisects; SQL windows over `jsonb_array_elements` with a path function per row | Windows, anti-joins and range joins over columns |
| Compute identity | Encode, serialize and hash at each holder | Canonical item text produced once by the producer; aggregated and hashed at each boundary |
| Partition and group | Dicts of lists; per-group, per-path, per-item loops | A key column and `GROUP BY` |
| Resolve references | Per-reference loops and per-reference joins | Typed address columns and one join |
| Admit and store | One JSONB document parameter, parsed and re-walked | COPY of item rows, verified and kept |
| Hand to a worker | JSON inside a string inside JSON, pickled | A sealed Arrow IPC buffer or file |
| Hydrate a consumer | Row-at-a-time fetch, parse, serialize and hash for a memo key, decode, freeze | Rows by key, memo keyed on the stored digest, Python objects only where a model library needs them |
| Replay, export, verify | SQLite JSON store with per-row lookups; Parquet relations written but not read back as rows | Joins over the Parquet relations |

Some consumers need Python objects: spaCy `Doc` reconstruction, HanLP word lists, construction
matching and navigation over per-token mappings. A typed carrier does not speed those kernels up.
It removes the passes around them and lets them convert only the columns they read. Steps that
only compare, join, count or re-serialize need no Python objects: partition headers, digest
checks, placement, the dense-ordinal, order and span rules, reference closure, sentence
membership, the canonical kernel and projection digests.

<a id="I01"></a>
## I01 — A typed relation as the carrier in process and between processes

**Current approach.** A population is a tuple of canonical JSON packet bytes plus a header. Each
process acquires it by parsing, re-canonicalizing, hashing and freezing into `MappingProxyType`
trees, behind a process-local cache whose key itself costs a parse, a serialization and a hash
(`sentence_partitions.py:79-158`). Workers receive it as JSON text inside a string inside JSON
through a spawned `ProcessPoolExecutor`, and the parent re-acquires the reply the same way
(`data_operation_cpu.py:117-148`, `canonical_sentences.py:673`).

**Proposed.** Derive one Arrow schema per collection from the effective model, in the derivation
that already yields pydantic models and JSON Schemas, and carry the population as a table.
The [projection contract](../plans/set-based-execution/common-analytical-basis.md#projection-contract)
already states the intent; the proposal makes it the ordinary carrier and retires the tagged
packet as a transport form in process.

- One table per collection with the partition key, item address columns and one column per
  declared field. A partition is a run of the key.
- The model's optional-value states (`present`, `known-absent`, `unknown`, `unavailable`) and
  explicit null are five states. Each optional field therefore carries a small state column, not
  a presence bit. Arrow has no absent state and the Arrow JSON reader merges absent with null;
  the identity probe's first run failed on exactly this.
- A reference is flat typed columns: role, occurrence, collection, partition key and key parts.
- HanLP units are a sparse union by `record_type` with nested `children` and `roles` lists. They
  need either struct-with-discriminator columns or child relations. A partition digest spans all
  record types in item order, so the canonical item text of [I02](#I02) is what keeps identity
  simple whichever layout is chosen. That layout is **untested**.
- Types the engines cannot hold exactly travel as canonical text with their tag: decimals beyond
  76 digits (the corpus holds a 103-digit value), unbounded integers, and floats, whose canonical
  form is Python `float.hex()`.
- The validated carrier of SBX-08 keeps its meaning. Holding the type means the population was
  established; it holds a table and its established facts in place of frozen trees.

**Benefit.** The tagged encoder and decoder, frozen-tree construction and thaw, the acquisition
caches and their key hashing, and the worker packet format leave the population path. A worker
hand-off becomes an Arrow IPC buffer: pickle protocol 5 sent a table's buffers out of band, and a
memory-mapped IPC file is page-shared. Heuristics H15, H16 and H19; DP-02, DP-06, DP-13.

**Transport seal and content identity are different things.** The worker packet's sha256 seals a
transfer, and a digest of IPC bytes can keep doing that. It cannot name content: logically equal
Arrow data serializes to different bytes when built differently, through slices, bytes under null
slots, dictionary order and chunking (**Tested 2026-11-22**). Content identity is I02.

**Adverse case.** A family whose every consumer needs Python objects and whose rows are deeply
nested gains only the removal of surrounding passes while paying for a more involved layout.
HanLP units are nearest to it. They still pass through admission rules, reference closure and
digests, which are set work, so the case holds for them. It would not hold for a population that
PostgreSQL never inspects and Python always consumes whole.

<a id="I02"></a>
## I02 — Keep the identity definition; produce canonical item text once

**Current approach.** `canonical_identity(domain, value)` hashes the canonical JSON of the tagged
value. Python and PL/pgSQL each hold a generic implementation, and a holder that wants to trust a
body runs one over the whole body. PostgreSQL's serializer now takes a single regular-expression
pass for object-free arrays up to 32 MiB, but normalization is still recursive and
`ddo_identity` still normalizes on every call
(`data_operation_value_native.py:107-118,303-345,667-672`).

**Proposed.** Keep the definition exactly, and split the work by who is best placed to do it.

- **The producer emits each item's canonical tagged text once**, as a column, from typed columns.
  The expression is generated in process from the collection schema, where the model is already
  bound. Nothing is installed in the database, so a model edit needs no native revision.
- **Hard scalars are spelled once, in Python or Arrow**, and carried as canonical text: floats,
  decimals, UTC instants and wide integers. The generated expression only frames, escapes and
  concatenates. Neither engine formats `float.hex()` natively, DuckDB has no counterpart to the
  PostgreSQL instant formatter, and decimal trimming is owned by `data.decimal_canonical`.
- **A digest is an aggregate.** The partition digest is sha256 over the frame and the ordered
  item texts. Both engines compute that with `string_agg … ORDER BY` in one `GROUP BY`.
- **The authority verifies without rebuilding.** PostgreSQL aggregates the submitted item texts
  and compares the digest, and checks each item once for canonical form and shape. It does not
  re-normalize the partition once per digest.
- The generic Python encoder remains the reference and the implementation for headers.

**What the generator must guarantee.** Total coverage of the tag set or refusal at generation
time. No dependence on engine locale, time zone or collation. The expression text enters no
fingerprint, since otherwise a generator edit would flip keys and fail the operator's first
test. Parity vectors are generated per collection from the schema, not hand-picked.

**Conditions from the probes.**

- DuckDB spells nine C0 control escapes in upper-case hex where the canonical form is lower case.
  The expression rewrites them, or the model refuses those characters.
- `set` and `bag` members sort by their own canonical bytes and `set` deduplicates; open mappings
  need a run-time key sort. These need a sort inside the expression and are **untested**.
- There is no incremental sha256 in either library. A group's text is buffered once, which is
  small at partition grain.

**Evidence and its limit.** The probe is one hand-written row shape with integer, boolean,
string, list and absent fields. It shows the approach is viable. It does not show coverage of
floats, decimals, timestamps, sets, bags, optional-value states or nested mappings.

**Is this safer than two generic twins?** It adds a producer that encodes from native types,
which is a new kind of twin. It is acceptable because the authority still checks every item
against the generic definition before trusting it, so a generator defect yields a refusal, not a
wrong identity. The cost moves from normalizing every body at every holder to checking each item
once at admission.

**Alternatives.** Hashing Arrow IPC bytes is not viable as content identity (I01). A new framing
chosen for ease of implementation would change every identifier and add a second encoder, which
the coordinator already declined.

**Rule impact.** The DuckDB pins hold and the kernel-trial seam carry the rule that identity
stays in Python. It still does, as the definition and the reference. Producing canonical text in
the engine should nonetheless be decided as a change. DP-01, DP-04, DP-06, DP-11; H12, H14, H20.

<a id="I03"></a>
## I03 — A set-shaped boundary, and item rows as the stored form

**Current approach.** Every native call is `SELECT ops.fn(:payload::jsonb)::text`. Retention
validates the whole completion against an inline schema, canonicalizes it, hashes it and stores
it as JSONB. Publication reads it back and normalizes, schema-checks and digests each body again.
Partition bodies are stored as JSONB and every rule, group digest and reference check walks them.

**The coordinator's premise.** Partition bodies were chosen over rows because "nothing in
PostgreSQL consumes tokens relationally; every consumer is Python reading a block", with "a
consumer that needs keyed access to items … inside PostgreSQL" named as a reason to reopen. The
frozen root shows PostgreSQL is such a consumer today. Admission rules (`dense_ordinal`,
`ordered_by`, `span_within`, `unique`, `refers_to`), per-item schema calls, group digests and
reference address lookup all run over `jsonb_array_elements(body[1])`. The trigger has been met.

**Proposed storage: generic item rows with a declared-read projection.**

- One generic relation holds an item per row: product, collection, partition key, item ordinal,
  the item's address key, and the item's canonical text. No per-collection table.
- A few typed generic columns carry what declared rules and address lookups read: ordinal, start,
  end and the address parts. Which fields populate them comes from the collection declaration.
- The partition row keeps its key, ordinal, placement, digest and group digests, and remains the
  unit of identity, proof and reuse.

This preserves "a new population is one declaration". Digests become aggregates, admission rules
become windows over typed columns, reference closure becomes an anti-join on address columns, and
a point read by address becomes an index lookup instead of a fetch of the whole partition, which
serves the operator's second test better than today. A rule over a field outside the projection
still reads the item text, once per item.

Fully typed per-collection columns are the stronger form and the costlier one: each new
population, field or field group would need DDL, grants and a native registration, or dynamic SQL
inside a security-definer routine. They should follow a demonstrated need, as a projection
derived from item rows, which the coordinator already allows.

**Proposed boundary.** For population-bearing calls, COPY the item rows inside the authority's
transaction and call a routine that reads them and returns rows. Control calls with small
payloads (claim, renew, resume, inspect) stay as documents.

- **Writes stay on the SQLAlchemy transaction's psycopg connection**, staged with pgpq as the
  PDF path does (`semantic/arrow_transfer.py:134-171`). ADBC cannot join that transaction, and
  admission, proof and settlement must commit together.
- **Retained rows are the stored rows.** Retention exists for lost-acknowledgement recovery, so
  what it keeps must be logged and survive a crash. The rows are written once under a retained
  state, and publication changes their state. They are not staged in a temporary or unlogged
  relation and copied again.
- **The write surface needs an owner.** COPY needs insert privilege on the relation for the
  purpose role, where today writes enter only through definer routines. Rows must be bound to the
  caller's attempt so one writer cannot stage under another's key. The PDF staging path has a
  precedent in which the caller prepares and authenticates the target; reuse it.
- **Refusals become rows.** Attach and completion isolate per-item refusals with savepoints
  (`request_attachment_native.py:2263-2327`). Set evaluation returns violations as typed rows
  naming the item and the rule. That changes the refusal contract and its controls.
- **Order the work around the request-row lock.** Scope rows are locked `FOR SHARE` and do not
  block each other; the exclusive locks are on the request and task rows
  (`data_derivation_native.py:350`). A cheap fence check comes first so a stale worker is refused
  before the authority validates anything. Content checks that read only the submitted rows
  (shape, canonical form, digests, rules local to a partition) can then run before the
  request-row lock. Reference closure to bound inputs, support availability, the trust-snapshot
  comparison and replay comparison stay under it. Whether renewal waits are caused by long
  sections under that lock is **Inspected, not measured**; the event fixture's log shows 13
  renewal statements of 250 ms or more totalling 68.2 s, and the plan records two cancellations
  at the 10 s limit.
- **Committed reads may use ADBC.** `fetch_record_batch` streams Arrow from a set-returning
  routine with bounded batches when the call is unparameterized, under the exact-snapshot pattern
  the companion export uses. Bound parameters return one unbatched result.

**Preserved.** The kind contract, content identity, stored-equals-submitted, atomic product,
proof and use, fencing and recovery. Stored-equals-submitted becomes exact: the stored text is
the submitted text and the digest is over it.

**Rule impacts.**

- [ADR-0128](../adr/0128-wire-contract-boundary-validation.md) holds that physical parameters
  and results remain JSON. It would be superseded for population-bearing calls.
- Item-row storage follows the route the plan names for a layout change:
  [ADR-0144](../adr/0144-sbx-partitioned-products.md), DESIGN and D3. Sealed worker transport
  follows [ADR-0145](../adr/0145-sbx-custody-boundary.md).
- Driver fidelity must be designed for. ADBC truncates nanosecond timestamps on ingest and wraps
  `infinity` on fetch without error, cannot ingest structs, and returns numerics as text. pgpq and
  ADBC use opposite JSONB conventions. Use one ingest route per unit owner. Carrying hard scalars
  as text (I02) avoids most of this. (**Tested 2026-11-22**)

**Adverse case.** A routine dominated by authority checks on a handful of rows gains nothing from
COPY. Claim, renew and resume are of that kind and stay as documents. H2, H3, H8, H18, H23;
DP-03, DP-10, DP-19.

<a id="I04"></a>
## I04 — Member products: a set-shaped envelope and typed references

Formal, construction, contextual and learned products hold heterogeneous members with small
bodies (in the development database's prior root, about 82,000 member rows averaging 624
bytes). Forcing those bodies into columns would trade one bespoke encoding for a wide sparse one.
The relational part is the envelope and the references, and the item-row form of I03 already
fits it.

- **Carry the context once per product.** The identical context dict is repeated in every packet
  and compared per packet in Python, in SQL and again in detached verification
  (`construction_products.py:970-985,1293-1298`).
- **Verify each member once.** Publication normalizes a member body three times (in the loop, at
  insert and in the `expected_members` comparison) and runs three schema checks
  (`data_product_admission_native.py:193,229-237,381,400-417`). One pass whose result is reused
  preserves the kind contract and identity. The full outer join that follows is also the replay
  guard when nothing was inserted, so it stays for the replay case.
- **Extract references into typed rows at admission.** Closure, live and detached resolution,
  selected witnesses and change impact become joins. Today they are per-reference PL/pgSQL loops
  with a JSONB accumulator as an index, per-reference authorization and selects in Python, and a
  branch ladder over merged dicts in `change_impact.py:223-352` (the last **not re-checked** by
  the independent challenge).

H9, H10; DP-07, DP-16.

<a id="I05"></a>
## I05 — One relational engine in process, with one rule about who evaluates what

DuckDB already has an owner, `analytics.py`, with invocation-scoped connections, a memory limit
and a private spill directory. With typed inputs it can take over set work that Python does
procedurally.

**Ownership rule.** The authority evaluates declared rule forms, because their proofs must not
rest on the producer's honesty. The producer evaluates only attested rules. A producer check of a
declared form is an optional early diagnostic that establishes nothing. A rule is never evaluated
for effect in both places.

**A producer plan per population.** One statement takes the typed rows through the attested
rules, typed diagnostics, canonical item text, and partition and group digests, and emits rows
for COPY. The probe did this for a nested token stream with four invariants and a per-block
digest: 40 of 40 digests matched the repository's canonical JSON and exactly the injected
violations were reported, as a `list<struct<rule, ordinal, detail>>` beside each digest
(**Tested 2026-11-22**).

**Moving attested rules to declared forms is an option, with a cost.** Sentence membership, HanLP
span alignment and coverage are attested because they are Python loops. As joins they could be
declared forms, the route the coordinator names for narrowing attestation. That adds work inside
the authority's transaction and grows the form vocabulary, which the coordinator lists as its
first risk. It is worth doing only for a rule whose attestation is a real weakness. Rules that
depend on Unicode-aware regular expressions or edit distance stay in Python in any case: RE2
character classes are ASCII-only and `levenshtein` counts bytes.

**Detached verification as joins.** `verify_detached_result` is a hand-written
referential-integrity pass (existence of each referenced row, bag equality of inputs, set
equality of outputs, counts, digest recomputation) served by SQLite lookups through
`json_extract`. The export writes a Parquet file per relation whose rows no code reads back; the
verifier loads `closure.jsonl` (`serve/demand_export.py:360-379,557-560`). Expressing the checks
as anti-joins, `EXCEPT ALL` and grouped counts over those relations removes the SQLite store and
the per-product lookups. Columns that hold JSON text still need JSON work for digest
recomputation until item text replaces them. SBX-12 is already heading here; the proposal is that
this be the verifier's only form.

**Scratch stores.** About ten modules keep SQLite scratch stores. "Read programs and scratch
stores" is an accepted decision, so replacing them wholesale is a rule impact. This review
proposes replacing two, the selected-record index and the PDF certifier's store (I07), and
leaves the rest to their owners.

**Conditions from the probes.**

- Give the plan a table of known length, not a single-use reader. A reader is estimated at one
  row, and the optimizer then built the hash table on the large streamed side. So the producer
  plan is fused but does not stream at its input, and aggregates and sorts break pipelines.
- Use binary collation and explicit `NULLS FIRST`; use `EXCEPT ALL` where multiplicity matters;
  write `coalesce(bool_and(x), true)` for empty groups; report contiguity as ranges, not per row.
- Recursion with `USING KEY` needs role, occurrence and generation in the key; a node-only key
  drops an arm at a diamond (already recorded).

H4, H7, H8, H9; DP-13, DP-14, DP-16, G8.

<a id="I06"></a>
## I06 — The advanced features, composed

The request named streaming Acero and the fusing of many actions into one streaming operation.
Fusion is the right idea. The engine for it here is DuckDB, with Acero in a narrower place.

**One composed walk, annotation to canonical.**

1. **Ingress.** The provider's output becomes an Arrow table built by column against the
   collection schema. Where a host returns JSON, `pyarrow.json` with an explicit schema decodes
   and shape-checks in one native pass: it rejected unknown fields, missing required values, type
   mismatches, overflow and duplicate keys (**Tested**). DuckDB's JSON reader is not a substitute.
   It rounded `1.5` to 2, coerced `true` and `"7"` to integers and ignored extra keys.
2. **Worker hand-off.** The table crosses to a CPU worker as a sealed IPC file, memory-mapped on
   the other side. Low-cardinality columns such as record type, part of speech and tag are
   dictionary-encoded; slices are compacted first, since a slice keeps its parent buffers alive.
3. **The plan.** One DuckDB statement, generated once per collection schema and rule set and
   cached with the model binding (H12): a materialized CTE over the table; windows for order and
   contiguity; an IE or range join for containment; list lambdas over nested fields; the item
   text expression; ordered `string_agg` and sha256 per partition and per field group; typed
   diagnostics. A `COPY` data-modifying CTE writes diagnostics to Parquet with key-value metadata
   while the statement returns the rows, from one scan (**Tested**).
4. **Egress.** `to_arrow_reader(batch_size=…)` feeds the pgpq encoder batch by batch into COPY,
   with no intermediate table. Both ends stream (**Tested** separately; the composition is
   **untested**).
5. **Admission.** Set SQL over the item rows as in I03.
6. **Read back.** A point read is an index lookup. A population read is typed rows, as Arrow
   through ADBC for a committed cut. The canonical kernel adds a self-reference per row and
   re-serializes; over columns that is a projection, and whether it still warrants a worker
   process is a custody question for SBX-07, not a performance one.
7. **Replay.** Parquet sorted by partition key and item, with row-group statistics, so point
   reads prune; filters push down into datasets and Parquet, not into plain tables or readers.

**Dispositions.**

| Capability | Disposition | Basis |
|---|---|---|
| DuckDB fused plan with a `COPY` data-modifying CTE | Adopt for producer plans and export | Tested: one scan, two outputs |
| DuckDB windows, IE, range and ASOF joins, list lambdas | Adopt for rules, containment and correspondence | Tested plan shapes; tie and direction rules stated per use |
| DuckDB temp macros with `query_table`, generated plans | Adopt for stable preparation | Prior probe; H12 |
| Arrow IPC with memory mapping; pickle protocol 5 | Adopt for worker hand-off | Tested |
| `pyarrow.json` with an explicit schema | Adopt for JSON provider output | Tested |
| Acero `Declaration` plans | A narrow place, not the engine | See below |
| PyArrow compute kernels | Single-table vector checks | `validate(full=True)` checks physical structure only and does not enforce non-nullable fields (Tested) |
| Parquet sort order, statistics and dataset pushdown | Adopt for replay | Tested pushdown; layout untested |
| ADBC fetch and ingest | Committed reads; ingest only where a unit runs wholly on ADBC | Tested; cannot share the authority transaction |
| DuckDB `postgres` extension | Immutable and replay reads only, if at all | Tested read-only: scans share one exported snapshot, each scan task opens a backend connection, unconstrained `numeric` becomes `DOUBLE` by default. Write path untested |
| `json_normalize` | Cross-check only | Reproduced canonical bytes; contract undocumented |
| IPC bytes as identity, VARIANT, Arrow extension types through DuckDB, DuckPGQ, Quack, DuckLake, Flight | Not adopted | Non-canonical bytes; key reordering and scale loss; extension identity lost at the engine boundary; no named consumer |

**Acero.** A fused filter, project, left-anti join and grouped aggregate ran lazily over a
Python-supplied reader, and closing the reader stopped the plan (**Tested**). Three properties
keep it from being the relational engine here. With threads on, `to_reader` applied no
backpressure and drained the whole source while the consumer was paused; single-threaded it
stopped after 34 batches (**Tested**). No spilling for joins or aggregates is exposed to Python
(**Inspected**, Python options only). Order is lost through joins, and the Python API lacks fetch,
write and sink options. A second relational engine also needs its own reason (H4, H25). Its real
place is an order-preserving filter-and-project stream, single-threaded: between an IPC reader
and the COPY encoder, or inside a CPU worker where a DuckDB connection with its own thread pools
and memory limit is unwanted. Nothing in this review needs it yet.

<a id="I07"></a>
## I07 — The PDF path: stay columnar once the data is columnar

The PDF path is the one place with Arrow at rest, and it leaves Arrow at each step that matters.
Certification re-reads the IPC files it just wrote, converts them with `to_pylist`, dumps each
row to JSON, inserts into SQLite, sorts there and folds frames in Python
(`pdf_certification.py:142-160,238-350`). `LogicalRows` digests per row and per cell through
`as_py` (`capture_storage.py:36-71`). The validation oracle reads staged rows back as JSON text
into an Arrow file of JSON strings and then into SQLite and dicts. Adoption commits a transaction
per IPC batch, and access rows go in as parameter batches. Two algorithms compute one logical
identity on the encode and decode sides. These source statements were **not re-checked** by the
independent challenge.

**Proposed.** Certify with DuckDB over the memory-mapped IPC batches: a binary-collated sort by
family and key, duplicate refusal as a grouped count, stream descriptor against parts as a
grouped aggregate, frames from a generated expression. Compute logical row digests by column.
Stage a document's batches in one transaction and send access rows by COPY. SBX-17 left the
external sort open between DuckDB and the existing SQLite; this resolves it, and the two digest
algorithms can become one.

This re-shapes SBX-14 to SBX-17 without enlarging them and is independent of I01 to I03.
H16, H17, H26.

<a id="I08"></a>
## I08 — Derive binding rows once per read, in the authority

Three native paths repeat the same admitted read.

- **Attach.** Python reads `ops.data_binding_rows`, builds a binding document and submits it. For
  each item `ddo_require_binding` re-runs the same read into an array and scans it per input, and
  the loop appends with `results || …` (`request_attachment_native.py:2259-2271,2328-2329`;
  `binding_admission_native.py:748,756`). There is already a per-batch cache keyed on the item
  digest, and the routine also evaluates a frozen binding predicate, so it is more than a row
  comparison.
- **Frontier readiness.** `ddo_obligation_readiness` runs per obligation in a select list and
  calls the binding read each time (`obligation_readiness_native.py:167,423`); the latest-use
  subquery is repeated four times.
- **Binding.** Seven to nine statements per obligation, with no batching across obligations, and
  `acquire_data_read_context` once per obligation and again per hydrated item.

**Proposed.** Materialize the binding rows once per read and join against them in all three. For
attach, consider sending only what Python decided and letting SQL derive the rest from the pinned
read, so that a forged or stale binding cannot be expressed at all. Which fields are Python's
choice (parameters, inference, populations) was **not traced** and bounds how far that goes.

**Result reads** are the largest recorded group (22 calls in the event fixture). Their body
disclosure walks tagged bodies per product (`ddo_admitted_body_access`). Under I03, disclosure
over item rows is a filter on rows and projection columns. Beyond that this review has no
specific proposal for the read routine; its attribution remains with SBX-11. DP-01; H1, H5, H12.

<a id="I09"></a>
## I09 — Python passes to remove regardless of the carrier

1. **Key hydration on the stored digest.** Hydration serializes and hashes both `json_body` and
   `meaning_body` to build a memo key when the row already carries its digest
   (`data_operation_consumers.py:84-92,324-334`). H14 applies exactly: proving the input
   unchanged repeats the work being avoided. The fetch uses `yield_per=1` on purpose, so that a
   driver batch cannot exceed the owned packet before the capacity check. Under item rows the
   bound becomes a row and byte limit on the query, which replaces it.
2. **One walk per JSON boundary for the calls that remain.** A result is parsed, walked by
   pydantic, validated by Draft 7 and walked again by the projector; a request is walked, then
   dumped. Keep the properties ADR-0128 requires and merge the walks.
3. **Drafts.** A draft is validated twice against the writer schema, written with three fsyncs,
   re-read and re-hashed, and the whole original request is re-sent to retire it
   (`completion_drafts.py:176-273,303-342`). Under I03 the draft is the sealed Arrow file that is
   staged, and retirement names it by digest.

Request-identity computation, the Python projection walk that builds read-projection keys, was
**not assessed**.

<a id="I10"></a>
## I10 — Thread, memory and fixture policy

**Thread pools need one owner.** `analytics.py:144-146` sets DuckDB `threads` and `memory_limit`.
It does not set `async_threads`, which defaults to 128 on this host, and nothing sets Arrow's
pools, which default to 32 CPU threads per process. Every worker process owns its own. Adopting
I05 without a policy would multiply them across test workers and CPU workers (H21). Whether this
contributed to the memory pressure that paused qualification is **not established**; the recorded
cause is concurrent runs with private clusters.

**Fixtures.** The long setups are executed demands: the event fixture's setup contains eight
attaches, seven retentions and 22 result reads. They shorten with the product. The lever that
does not depend on the product is prepared-state reuse across affinity groups. Each distinct
group repeats the cohort, the database clone and `prepare_kernel`, which is memoized per recipe
with a 16-entry limit per worker. The bounded cohorts stay with the efficiency amendment.

<a id="integration"></a>
## Integration, interactions and sequencing

**What is given up.** The series has 262 commits since the coordinator was added, a registered
sole root, and three interrupted cohorts that kept 306, 301 and 296 passed identities. I01 to I03
replace the physical layer that revision A built: the partition, rule, reference and read native
generators, the tagged codec on the population path, the carriers and the worker packet. All
qualification evidence for the population path would be void and earned again. Independent
semantic expectations carry over: identity vectors, the shared change scenarios and the refusal
controls. This also reopens the pilot's carrier decision on the day it was recorded.

**The choice in front of the operator.** The reset installs a sole cold root in an empty
database, and the coordinator said to finish the carrier choice before cold-root authoring.

- *Decide first.* Stored layout and boundary are settled before the root is authored, and the
  root is authored once. Qualification of the present root stops where it is paused.
- *Qualify first.* The present root is accepted and development resets onto it. The functional
  target is reached sooner. The passes this review identifies remain in every later journey, and
  a later change of stored layout means a second root and a second reset, which the design phase
  permits.

This review recommends deciding first. The difficulty that paused qualification comes from the
carrier, and qualifying the present root means paying for those passes across the whole
remaining inventory in order to accept a layer that is then replaced.

**Order if the decision is taken.**

1. Decide the carrier, identity production and boundary together, with the rule impacts on
   ADR-0128, ADR-0144 and ADR-0145 and the identity hold. This is a substantial ownership change
   in the binding's sense, so a focused design review applies.
2. Prove it on one vertical slice, annotation to canonical. The canonical kernel is a pure
   transform with no model call, the family has admission rules, group digests and references,
   and the shared change scenarios already state the expected results for moved, renamed, split
   and merged blocks.
3. Extend to HanLP units, then apply I04 to member products.
4. Author the cold root once, and reset.

I08 and I09 change native routines and so the registered root. They can land with step 1's
authoring, or on the present root at the cost of renewing its registration. I07 and I10 are
independent of the root.

**Effect on the remaining packages.** SBX-08 and SBX-09 keep their purpose with a different
carrier. SBX-10's derived views become queries or columns. SBX-11's keyed reads become index
lookups on item rows. SBX-12's typed relation interface, Parquet replay and removal of the SQLite
index are the same design arriving from the read side, and its two backings would share one
schema with the write side. SBX-18 and SBX-19, the gated kernel trial, would have less to decide
for the validation and reference families; that is a proposal, and the trial's own decision
stands. SBX-14 to SBX-17 take I07.

**If the carrier decision is declined**, these remain worthwhile in this order: I08, I09, I10,
I07, the parts of I04 that need no staging, and detached verification over the existing Parquet
relations.

## Limits

- No timing or memory measurement was taken.
- The internals of the slow native endpoints remain unattributed, and lock waits were not
  measured.
- Member counts and routine counts come from the development database's prior root. Member counts
  per product and the split of Python-side time among pydantic, Draft 7 and serialization were
  not measured.
- Not read in full: the generated SQL of structural admission and projections, the learned
  primary kernel body, the PDF worker pipe and the SQLAlchemy lowering modules.
- Untested: identity parity for floats, decimals, timestamps, sets, bags, optional-value states,
  nested mappings and the HanLP layout; COPY of item rows under a real purpose role; the composed
  DuckDB-to-pgpq stream; Parquet layout for point reads; DuckDB writes through the `postgres`
  extension; whether `take` zero-fills null slots for every Arrow type.
- The other review of this date was not read.
