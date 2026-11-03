# M1 pinned record consumer adapters

**Tested, 2026-11-03: detached adapter mechanics only.** This bounded M1-12 slice
implements query presentation, CLI/MCP adapters and a record companion in the existing
atomic semantic export. It does not complete M1-12 or qualify CPU extraction, native
publication, accepted records, source-reading quality, calibration or scientific truth.

## Baseline and ownership

Worktree `/home/paul/.cache/corpus-structure-m1-record-consumers`, branch
`codex/m1-record-consumers`, starts from `0046d5ceab5f2fd10c7f86c918c27af67c94e7ff`.
The root's dirty production dependencies were copied as read-only inputs into the
worktree. [Dependency hashes](dependency-copy-manifest.json) name that tested snapshot;
these files are not this worker's changes and must not be copied back or committed.

[Owned files](owned-files.json) is the exact nine-file integration allowlist. The
[owned source hashes](owned-source-hashes.json) record the final worker source.
The coordinator owns integration, model declarations, native changes, plans, STATUS,
turn-end maintenance, qualification and any commit. This worker changed no main-tree
files, database state, providers or host configuration and made no commit.

The worktree checkout reported 33 existing LFS pointer anomalies in old evidence logs.
Those files were not edited and are outside the integration allowlist. All commands
ran from the main checkout using normal `uv run` with the isolated source directory
on `PYTHONPATH`. This preserves the existing root environment's editable installation;
the worktree's unapproved `.envrc` was not enabled.

## Implemented contract

`serve.record_results.serve_record_results` uses the existing read-only snapshot and
ReadSession, then the released `read_source_records` operation through
`read_completed_record_projection`. It uses the semantic owner's invocation-local
`CompletedRecordProjection.record_index`; no second index, schema store, producer
envelope read or per-record database hydration is introduced.

All five released families use `reconstruct_record` and the same common result. Each
record retains role/state values, named evidence sets and anchor precision/spaces,
original and exact decimal/scientific spellings, alternatives, derivation premises,
computation dependencies, private assertion references, actual public assertion
bindings and the persisted admission/calibration decision. Native inspection handles
name the same run and exact product content digest; they do not invent character spans.
Coverage comes from the existing ReadSession ledger. Reports preserve completed-empty
versus absent record payloads independently of whether an accepted record exists.

Primitive continuations use the shared decoder and validator. Their query fingerprint
binds normalized run/project/source/family/standing/record/interpretation selectors,
query version, cut and released projection digest, alongside release/realization/revision.
There is no moving-default selector in the new record journey. Page size and resource
bounds can change without changing the selected population. Malformed positions,
foreign filters, wrong release/projection and stale revision refuse explicitly.

The reader must first admit the entire requested run/source scope within its record,
row and canonical-byte budgets. Family/standing/identity filtering and paging operate
on that finite detached population. `population_paging_complete` describes presentation
only; `source_coverage=not_established_by_record_projection` remains explicit. Page-byte
overflow refuses instead of silently dropping records. The underlying canonical-byte
budget does not claim to bound prepared-release memory or process RSS.

CLI:

```sh
uv run ci records list --run 41 --family measurement --json
uv run ci records list --run 41 --record RECORD_ID --interpretation INTERPRETATION_ID --json
uv run ci records list --run 41 --cursor TOKEN --json
uv run ci records export --run 41 --out PATH --format parquet --json
uv run ci export --run 41 --out PATH --include-records --format jsonl --json
```

The read-only MCP `records` tool accepts the same `RecordRequest` and returns the same
`RecordPage`. CLI and MCP serialize the domain result without reconstructing acceptance.

`ci records export` captures the existing CapturedPacket and the 18 released record
relations in the same read-only snapshot. Export continues after detachment under the
existing Arrow lifetime owner. The existing atomic directory publication writes the
semantic spine and all 18 record relations together; a mismatched pin leaves no output.
Arrow fields derive from public row declarations, including empty relations. Decimal
lexical forms remain strings in JSONL and Parquet; native anchors retain their spaces,
pointers and precision. `semantic-export-3` includes record policy/projection and the
semantic release manifest, per-file hashes and a record logical digest. The existing
CapturedPacket logical digest is explicitly scoped to `captured_semantic_spine`.
The generic export remains opt-in for records; its existing contract is preserved
when `include_records=False`.

## Results

Commands below run from `/home/paul/corpus-structure`. The isolated source override
selects worker code while normal `uv run` synchronizes the main checkout environment.

```sh
WORKTREE=/home/paul/.cache/corpus-structure-m1-record-consumers
PYTHONPATH="$WORKTREE/python/corpus-structure/src" uv run pytest \
  "$WORKTREE/python/corpus-structure/tests/semantic/test_record_consumers.py" --tb=short
```

- **passed**: [focused-005.log](focused-005.log), 18 tests, after adopting the shared
  prepared index. Independent expected values cover all five families, table header/note
  membership, formula coordinate spaces, exact `1.234567890123456789e-400` and `12.000`,
  candidate/calibration standing, report absence/empty, continuation pages/refusals,
  response-byte refusal, coverage retention, all 18 JSONL/Parquet relations and atomic
  wrong-pin export refusal. Actual Typer and in-process FastMCP dispatch compare the same
  controlled detached result; service/database boundaries are substituted for that adapter
  test. It is not native or provider qualification.
- **passed**: [ruff-004.log](ruff-004.log), `uv run ruff check` on the nine files listed
  in `owned-files.json` (each argument rooted at the worktree).
- **passed**: [pyrefly-003.log](pyrefly-003.log), `uv run pyrefly check --config
  /home/paul/.cache/corpus-structure-m1-record-consumers/record-consumers-pyrefly.toml`
  on the same nine files. The temporary config only selects isolated source/test search
  paths and the existing root site-packages; it changes no checked rules or errors.
- **failed, superseded**: [failed-001.txt](failed-001.txt), first dependency snapshot
  caught an incomplete root-owned SourceRecordProjection concept during concurrent
  declaration work. Root supplied its missing attributes; no consumer check was weakened.
- **passed, earlier source**: [focused-002.log](focused-002.log), 16 tests before
  coverage/CLI/MCP additions; [focused-004.log](focused-004.log), 18 before shared-index adoption.
- **failed, superseded**: [focused-003.log](focused-003.log), 17 passed and one fixture
  failure for omitted required Coverage fields. Fixed by providing its actual reason,
  source outcome and capability fields.
- **failed, superseded**: `ruff-001.log`, `ruff-002.log`, `pyrefly-001.log`: initial
  import/line layout and dynamic TypedDict/JSON access diagnostics. Changes use the shared
  typed projection boundary and serialized test expectations; no ignores were added.
- **not_run**: database/provider operations, actual selected-result changes, actual native
  evidence retrieval, imported PostgreSQL snapshot capture, resident/spooled database
  export journeys, CPU extraction, broad qualification, root turn-end and handoff skill.

## Integration obligations

Copy only `owned-files.json` and this evidence folder's worker artifacts. Keep the root's
model/read/index/native changes as the authoritative dependencies; do not copy the worktree's
other dirty files. Run the root's maintenance after integration, then reassess affected
checks against the final assembled source/context.

The root must exercise the reader and adapters against actual completed candidate results,
including selected-result movement between pages, wrong/missing results, source retrieval,
native budget refusals and detached resident/spooled exports. Verify existing generic
exports and MCP source journeys still work. Actual five-family CPU publication, acceptance
admission, routing/coverage/gap completeness, quality/calibration gains and final M1 gate
claims remain with their owning packages. The record projection cannot establish source
absence or family-routing completeness from a missing report alone.
