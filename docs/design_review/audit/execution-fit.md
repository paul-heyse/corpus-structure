# Execution fit

These findings apply FP-07/A4 and the efficient-architecture heuristics. They are assessed
qualitatively for the workload the go-forward design declares:
- a regenerable corpus, beginning with the statistics trace and the toy transfer fixture;
- release-bound runs that publish into realizations;
- served queries and explanations;
- reference grading.

Static evidence can establish repeated or amplified work. No elapsed time in this page is a
claim, except where an existing measurement is cited with its conditions. Baseline, scope and
scenarios are in the [README](README.md).

Paths are relative to `python/corpus-structure/src/corpus_structure/` unless they start with `rev/`
(`python/corpus-structure/semantic_alembic/versions/`) or `docs/`.

Choices that fit the workload and should be kept:
- **Sealing.** A short seal transaction followed by one SERIALIZABLE publication with a single
  retry owner (`orchestrate/commands.py:257-286`; `semantic/publication.py:583-612`).
- **Read transactions.** These close before projection starts in `consolidate_cut`.
- **Reads.** Batched value-graph closure and keyset paging in serving, with no per-row queries.
- **Reuse.** Twin reuse of completed tasks keyed on a dependency manifest and checked natively
  (`valid_reuse`).
- **Scope lifetimes.** DuckDB lifetimes are owned by the scope, and the release-bound analytical
  decimal profile has a single boundary.

<a id="da-024"></a>

## DA-024 — Retired at this baseline

*Was: "The final consolidation transaction holds the run-row lock across measurement and
evaluation" (accepted target, 2026-10-28).*

The go-forward path resolves it:
- finalization holds `FOR UPDATE` only in a short seal transaction;
- consolidation runs in separate REPEATABLE READ reads, then one SERIALIZABLE publication;
- evaluation is a separate `ci eval` route.

Evidence: `orchestrate/commands.py:252-286`; `semantic/domain_operations.py:210, 687, 1976`;
`semantic/publication.py:583-612`, verified 2026-10-29 at `ad4593f`. The earlier text is in Git.

<a id="da-025"></a>

## DA-025 — Keying repeats rendition-wide work for each statement (inherited, not re-examined)

*Inherited from the audit at `024bb33` (2026-10-28). Applicability limit: its subject (`core/keys.py`
keying, reached only through legacy consolidation) lies outside this baseline's go-forward scope.
It was not re-examined.*

An exploration pass on 2026-10-29 noted:
- `KeyContext` now prepares rendition-wide work once per rendition (`core/keys.py:919-958`);
- keying is reachable only through legacy `consolidate/assemble.py`;
- the semantic analogue (`LocatorIndex` built per descriptor, `semantic/domain_operations.py:1243`)
  was not assessed.

**Principles:** FP-07, DP-10.

**Original diagnosis:**
- `statement_anchor` walked the annotation units once per statement;
- `KeyContext.segments` re-derived segment keys the store already held;
- `member_parts` recomputed `claim_parts`.

<a id="da-033"></a>

## DA-033 — Native publication re-establishes assurance on every write and scales with the realization, not the batch

**Principles:** FP-07, A4, DP-03 (reuse established immutable validity), DP-10, DP-20, DP-23;
heuristics H10, H18–H20; §G "we validate it repeatedly". **Subject:** implemented, and the accepted
decision. ADR-0025 and SP-03 say publication "validates candidate plus admitted state"; this
finding also judges that decision's realization.

### Diagnosis

The native publication path is built around the whole realization and the whole run, not around
the incoming batch. This shows in three ways.

**(a) Full admission on every write.**
- `require_execution_release` runs from BEFORE triggers on:
  - every insert or update of `data.realization`;
  - every insert into `data.batch`;
  - every insert or update of `data.project` (`rev/semantic_0026_admission.sql:113-127`; 0029
    redefines the project guard).
- Each run of it:
  - decodes the release's whole `prepared_bytes` archive to jsonb;
  - re-checks authored SQL and the inference profile;
  - hashes about 89 function bodies;
  - compares 34 triggers and 71 reader grants;
  - scans `pg_class` across five schemas with `has_table_privilege`
    (`rev/semantic_0030_admission.sql:11-16, 73-125`).
- Each guarded row write pays this. It is a fixed cost per batch, not per data row. The premises
  change only on migration or activation.

**(b) Whole-realization validation on every batch.**
- `publish_contract_batch` (`rev/semantic_0027_transport.sql:142-163`):
  - runs `validate_state`, `validate_occurrence_context`, `validate_entity_source` and
    `validate_alternatives` over the entire realization;
  - recomputes `fact_identity` for every admitted fact (153-155);
  - re-runs applicability, `validate_property`, report-meaning identity and the Qualification check
    for every occurrence (156-163).
- These are row-at-a-time PL/pgSQL loops:
  - `validate_pre_inference_state` recomputes `value_meaning` recursively for every typed value, so
    nested meanings are recomputed once per ancestor (`rev/semantic_0011_*.sql:11`);
  - `validate_occurrence_context` re-expands payload JSON and hashes candidate citations for every
    evidence edge (`rev/semantic_0030_source_frames.sql:228-262`);
  - derivation grounding is an array fixpoint (`rev/semantic_0007_inference.sql:86-94`).
- Consolidation publishes a source batch and an inference batch in one transaction, then runs
  `finish_evaluation`, which validates occurrence context and entity sources again.
- Per run that is: `validate_state` twice, occurrence context and entity source three times each,
  and the fact recheck twice.

**(c) Whole-run receipt.**
- The batch receipt holds the run's entire canonical content as single values:
  - natively, one `jsonb_build_object` over every relation, stored in `data.batch.content`
    (`rev/semantic_0027_transport.sql:62`);
  - in Python, the same bytes in memory, sent as one bytea parameter
    (`semantic/publication.py:346-359`; `semantic/arrow_publication.py:150-170`).
- Consolidation publishes one batch per cut, which is the whole run
  (`semantic/domain_operations.py:2059-2100`).

Admitted rows cannot change through publication: `ON CONFLICT DO NOTHING` plus conflict checks,
and an immutable evaluated realization. So their local validity is re-established without any new
premise. Only the relational invariants need admitted context, and those could be limited to the
entities and facts a batch touches:
- cardinality;
- identity uniqueness;
- ranges over accepted values.

### Consequence

- **Fixed cost per publish** grows with archive and catalog size.
- **Validation cost per batch** grows with realization size.
  - Today each run publishes one consolidation batch and one inference batch into a *fresh* output
    realization (`semantic/domain_operations.py:2059-2107`). The realization is therefore about the
    batch, and the repetition is a constant two-to-three-fold factor.
  - It becomes growth with history only if incremental or append publication into one realization
    is introduced. The publication contract allows that; no current operation does it. **Current
    consequence: low.**
- **Transaction width.** All of it runs inside one SERIALIZABLE transaction that reads the whole
  realization. That widens predicate locks, and the retry owner repeats everything up to three
  times (`semantic/publication.py:576-613`).
- **Size ceiling and memory.** The receipt puts a predictable ceiling on run size, set by
  PostgreSQL's value-size limits; probe not run. Peak memory holds several whole-run copies. The
  native construction as one jsonb value was reported by one contributor and not re-verified by the
  second.

### Counterevidence

- The per-write recheck does catch operator DDL changes made between writes.
- Exact receipt bytes give real idempotency and lost-commit resolution.
- The statistics and transfer runs completed.
- Nothing has been measured.
- The recheck partly compensates for missing preventive immutability
  ([DA-029](native-integrity.md#da-029)).

**Evidence:** structure diagnosed from source; cost and ceiling suspected. A scenario reviewer
narrowed the growth claim (W2-B, 2026-10-29).

**Lead:** check a deployment identity once per transaction; validate candidate rows plus the
admitted rows they affect, set-based, computing meaning once per value per batch; key the receipt
by a digest over a streamed canonical order.

<a id="da-042"></a>

## DA-042 — Immutable products are re-derived on every use

**Principles:** FP-07, A4, DP-10, DP-23, DP-24, CI-13; heuristics H12, H19, H20, H25.
**Subject:** implemented.

### Diagnosis

Two products whose premises are established and immutable are rebuilt from their producers on
every use.

**The release, on every read session.**
- Query, explain, export, the MCP server and evaluation all call `load_release`
  (`semantic/query.py:320-345`; `serve/journey.py:81`; `intervene/semantic_server.py:56-65`;
  `evaluate/semantic.py`). It:
  - refuses when installed library versions differ from the archive;
  - re-runs `prepare_release` in full, including OWL/SHACL generation, a JSON Schema per class and an
    execution-model compile against the current approved symbols;
  - compares every product byte for byte (`semantic/releases.py:391-466`).
- `prepare_release` also refuses unless the archived compiler version equals the current one
  (`semantic/prepare.py:561-566`).
- Long-lived processes pay the cold preparation once. `prepare_release` is an in-process
  `lru_cache(maxsize=8)` keyed on full input bytes plus the stack (`semantic/prepare.py:577-584`),
  and the MCP server caches per process (`intervene/semantic_server.py:59-66`).
- Each read session still re-reads and byte-compares every archived projection row
  (`semantic/releases.py:463-465`).
- Every CLI invocation pays the full cold preparation.
- **Measured** (comparative leverage review, statistics pack, one workstation, three fresh
  processes, 2026-10-29): cold `prepare_release` takes 2.18–2.45 s, of which OWL/SHACL generation is
  1.03–1.12 s. See the
  [leverage review evidence](../evidence/2026-10-29_library-leverage-review-probes/README.md), Q3.

**The agent packet, on every MCP tool call and every queued unit.**
- `SemanticAgentSession.active()` renews the lease and calls `agent_packet` on every
  `read_unit`, `read_instructions`, `propose_claims` and `release` (`intervene/semantic_server.py:68-87`).
- `agent_packet`:
  - takes the input-snapshot lock;
  - reads the full rendition content and observations;
  - runs document references;
  - hashes the packet;
  - captures the source frame (`orchestrate/semantic.py:351-444`).
- Queue preparation repeats this for each selected segment and caches only the `LocatorIndex`
  (`:498`, `:598-610`, `:675-684`).
- The premises are already fixed: the input revision is fenced, rendition content is immutable, and
  the source frame and packet hash are immutable (0018, 0030).

### Consequence

- Every CLI read process repeats preparation and graph generation it never uses.
- Per-task agent work multiplies by the number of tool calls, each with rendition- and
  document-wide reads.
- Re-running the producer over a digest-verified archive is not independent assurance (DP-23).

The compatibility consequence — re-derivation under the current stack makes archives unreadable
after any byte-determinant change — has its own home in
[DA-049](semantic-model-and-authority.md#da-049).

### Counterevidence

- Byte-exact re-derivation is a deliberate integrity mechanism (ADR-0025).
- Clean regeneration was chosen in ADR-0024.
- The refusal is honest.
- Re-deriving the packet does guard against drift.

**Evidence:** structure diagnosed from source; release preparation cost measured as cited; packet
cost not measured.

**Lineage:** the release half is the premise of the leverage review's
[CBO-003](../../library_leverage/reviews/release-lifecycle.md#cbo-003), which holds the solution
comparison.

<a id="da-043"></a>

## DA-043 — Consolidation and inference work scale with the input realization, and quadratically with the cut

**Principles:** FP-07, A4, DP-10, DP-12; heuristics H5, H8–H10, H12, H19, H23. **Subject:** implemented.

### Diagnosis

- **(a) The whole input realization is read.** `_known_input` reads every membership of the input
  realization, then all their selected facts, values, supports, exclusions and evidence, through
  IN-lists of every id (`semantic/domain_operations.py:481-681`).
  - The narrowing sets `references` and `classes` are computed and never used (`:453-470`).
    Narrowing happens only after the load (`:1812-1824`).
  - SQLAlchemy expands each IN-list into one bind parameter per element (statement compilation,
    no database). That points to a hard failure above PostgreSQL's 65,535-parameter limit. The
    `kb.span` insert uses three parameters per coordinate (`:2116-2138`).
- **(b) Per-fact registry work.** A registry scan plus `json.loads` runs for every known fact
  (`:571-577`, `:598-605`).
- **(c) Repeated validation.** About ten validations run per claim ([DA-004](semantic-model-and-authority.md#da-004)).
- **(d) Quadratic constructions inside the cut.** Premise sets are rebuilt per candidate
  (`:3241-3262`), a set is rebuilt per row (`:1903-1909`, `:1965-1969`), and properties are
  scanned per fact (`:3348-3356`).
- **(e) Pairwise comparisons in each functional slot.** Each can take up to 5 s of symbolic
  simplification plus sampling (`:2748-2847`), so a heavily populated slot grows quadratically.
- **(f) Inference.**
  - It is a naive fixpoint: each round re-runs every rule over the whole work table, with one round
    trip per rule (`semantic/inference.py:140-160`).
  - Transitive rules emit one derivation per witness pair, which is cubic along a chain
    (`:196-222`).
  - Native verification loops over every derivation (`rev/semantic_0007_inference.sql:35-94`).
  - It runs inside the SERIALIZABLE publication transaction, which the retry owner repeats
    (`semantic/domain_operations.py:2085-2103`).
- **(g) Machinery without inputs.** The rule policy is recompiled on every consolidation (`:2002`),
  and 26 spine projections are compiled for an empty `CandidateInput` (`:2010-2022`;
  [DA-047](boundaries-and-composition.md#da-047)).

### Consequence

- Latency grows across generations with accumulated knowledge, not with the cut.
- Growth can fail outright at protocol parameter limits.
- Long serializable transactions widen the conflict and retry window.
- A pack that declares a transitive predicate — a capability ADR-0027 accepts — would make
  publication blow up predictably. No current pack declares one; only `symmetric` exists.

### Counterevidence

- Everything is deterministic.
- The read transactions close before projection.
- Nothing is measured.

**Evidence:** structure diagnosed from source; parameter-limit failure suspected.
