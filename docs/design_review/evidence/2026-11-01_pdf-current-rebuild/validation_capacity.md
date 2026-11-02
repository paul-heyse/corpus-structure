# Frozen PDF validation: work and capacity

Read-only assessment, 2026-11-01; implementation proposals, not measured speed claims.
Run9 was cancelled normally before sealing. Its frozen build, successful native-callback receipt,
all private rows, frozen Arrow capture and access projection remain preserved. Task/run are
`cancelled`, lease is clear, and protected publication count is zero. See
`runtime/source-prepare-attempt-003-settled.json` and the interruption receipt.

## Observed source80 critical path

The current path in `semantic/pdf_publication.py:579` is serial:

| Phase | Existing work | Run9 evidence |
| --- | --- | --- |
| Capture | Fetch nine frozen relation families in batches of256, one connection/transaction at a time; convert row JSON into Arrow string columns | Completed ~2GB `frozen.arrow` |
| Native child | Parse that JSON again; keep native/membership/reference dictionaries and lists; build SQLite payload store; reconstruct whole native dictionary; schema validation; finite traversal; private deep copy; Docling model/global callbacks; explicit-state mutation comparison | One child, ~7.2GB RSS observed; successful callback receipt preserved |
| Derived projection | Write per-item access/region JSONL, read it back and adopt128-row/8MiB batches serially | Completed 123MB projection;209,439 access items and48,279 regions |
| SQL validation | One writing SECURITY DEFINER PL/pgSQL call, holding the build fence, sequential guards, artifact verification, access correspondence and identity/projection folds | Active CPU/no wait when cancelled after17:20:00–17:25:17 ET; internal guard position was not observable |
| Seal | Consume qualified immutable validation receipt under task/build fences | Not run; no publication |

This does not establish that the interrupted SQL call was spending time in a particular guard.
The current read-only planner receipt does establish repeated-work shapes independently.

`runtime/validation-capacity-current.json` records exact frozen inventory:780,702 native,
569,604 membership,419,358 reference,209,439 access,48,279 region,544,392 companion and
780,400 endpoint rows. `inspect_validation_capacity.py` runs only read-only inventory and
EXPLAIN without ANALYZE. Its initial maintenance-role EXECUTE refusal is retained separately;
the successful invocation uses the existing permitted publisher role locally, without ACL changes.

## Reduce work before adding workers

| Current algorithm | Bounded correction to assess/implement | Obligation that must remain |
| --- | --- | --- |
| Ordered membership `LATERAL count/min/max` for each native collection field (`pdf_publication_native.py:709`) | Aggregate once by full product/revision/parent/field and join collection declarations | Empty/nonempty lengths, ordinal bounds and missing fields; each collection remains one unit |
| Region count subquery per access item (`sql/pdf_record_access_correspondence.sql:146`) | Count once by full product/revision/pointer and join access inventory | Exact zero/nonzero counts and all region/provenance comparisons |
| Region-to-page membership lookup on each region | Materialize current-build page/size map once; join by the existing text page key | Missing/ambiguous pages, exact dimensions and numeric projection semantics |
| Containment cycle paths start at every edge (`pdf_publication_native.py:665`) | Preserve exact owner counts, including duplicate same-parent edges, plus one root-reachability traversal | Root0 owners, every other record1 owner, every record reachable, no disconnected cycles or duplicate edges |
| Several native/access/reference joins omit middle revision PK key | Use the complete known product/revision/identity keys consistently | Same frozen revision authority; no broader lookup or changed equality |
| Final validator verifies every stream, then identity scalar helpers verify referenced streams again (`pdf_record_logical_identity.sql:54,83`) | Verify each immutable stream once at this validation boundary; identity consumes its verified descriptor | All streams covered, byte lengths/offsets/part hashes/roots, schema/profile and frozen binding; do not skip custody verification |

The current page-correspondence EXPLAIN contains a nested-loop join filter
`pages.member_key = r.page_no::text`. Its membership index condition covers
product/revision/root/field but not the map key: the only membership index is the ordinal PK.
It therefore revisits the page-membership candidate set per region. This is a concrete work-shape
problem; increasing worker counts does not remove it. No runtime speedup was measured here.

The Python boundary also repeats whole-value work: lowering validates schema/finite JSON;
frozen reconstruction validates schema/finite JSON; callbacks traverse finite JSON, deep-copy,
construct the native model, then build an entire supplied-state value for comparison. These
checks have different representation/custody purposes, so they cannot all be deleted merely
because they overlap. Candidate reductions are a single model-owned validation/encoding pass
per identified value, lazy explicit-state comparison, and reuse of an already-qualified immutable
callback receipt on resume. Preserve independent server-side frozen-union enforcement: native
callbacks alone do not prove that extra unreachable rows were absent from the submitted union.
Current resume only reuses a complete final witness; after interruption between callbacks and
final SQL it repeats capture/callback/projection work despite the preserved callback receipt.

## Parallelism boundaries

The host exposes32 logical CPUs. Current PostgreSQL settings are16 worker processes,
8 parallel workers,4 per Gather,64MB work_mem. All relevant custom schema/hash/reference/access
functions and the writing validator are currently `PARALLEL UNSAFE`. PostgreSQL18 documents
that unsafe expressions force a serial plan; functions that write must remain unsafe. Setting a
larger worker limit does not turn this path into a parallel plan.

After work reduction, independent per-record shape checks, per-collection membership checks,
per-stream byte checks and per-item/page projection checks are bounded local units that may
parallelize where useful over the same immutable frozen input. Preserve exact partition coverage and compare against global lookup
sets. Avoid replicating the whole native model across workers. Native Docling/global tree validation,
whole-union reachability/uniqueness, exact global inventory, canonical ordered identity folding
and final task/build fences remain global obligations. Ordered SHA folds cannot be replaced by
an arbitrary merge of worker digests without changing the identity protocol. Local frame preparation
can be parallel where useful, followed by the unchanged canonical ordered fold.

No new pool, prescribed worker count, partition receipt registry or middleware is proposed here. First fix the set-based SQL and
Arrow intake/copy path, then qualify any targeted parallel implementation against unchanged
negative controls and exact identities. No global database settings were changed.

Sources: PostgreSQL18 [parallel safety](https://www.postgresql.org/docs/18/parallel-safety.html),
[CREATE FUNCTION](https://www.postgresql.org/docs/18/sql-createfunction.html) and
[worker limits](https://www.postgresql.org/docs/18/runtime-config-resource.html), fetched through
Context7. These support capacity restrictions, not a measured product performance claim.

## Working-tree implementation checkpoint

During current source10 validation, a further read-only check found an active, unblocked
backend and temporary-file I/O. Three EXPLAIN-only access checks retained full composite-key
lookups. Ordered identity and projection sorts can legitimately spill; the sampled wait does
not identify a defective stage. One remaining optional reduction is section ownership: the SQL
helper starts an ancestry walk at every item, while root-down nearest-section propagation could
reuse shared ancestry. This is an unimplemented opportunity, not an attributed bottleneck or a
reason to interrupt valid current work. No additional benchmark or worker pool was introduced.

A further source inspection found interpreted byte-by-byte UTF-8 validation in
`ops.pdf_identity_utf8`, including canonical companion JSON and record keys. A bounded
future correction can use PostgreSQL's native `convert_from(...,'UTF8')` verifier when
the byte string contains no zero octet, preserving the existing manual path for zero-containing
strings, which PostgreSQL text cannot represent. Invalid UTF-8 must still return false;
identity bytes and folds must remain unchanged. PostgreSQL18's conversion implementation
verifies input even for equal encodings. This is an unimplemented work-reduction opportunity,
not an attribution of the active query's runtime or a reason to replace its frozen premises.

The delegated SQL package now implements the set-based owner/reachability, membership and
region/page-map changes; full composite lookup keys; one complete-identity stream verification
pass; and a PostgreSQL-native printable-ASCII string encoding path with the unchanged Unicode
fallback. These are frozen in81 and deployed through the forward82 admission correction.
Twenty-seven focused PostgreSQL controls passed, including independent invalid cycles,
duplicate edges, incomplete scalar collections, multipage/revision correspondence and corrupt
referenced/unreferenced streams. Scoped typing passed.

The three structural predicates were also executed once, read-only, against preserved run9
rows. They found no ownership/reachability defect, ordered membership defect or region/page
mismatch. `runtime/validation-sql-structural-exercise.json` retains the raw checks and plans;
this is not a required speedup benchmark. The architectural benefit is avoiding repeated
collection/page work while retaining whole-union closure. The known report-attribution defect
is separate and remains blocking until the coordinator's producer/model correction is
integrated. No new source run has started.
