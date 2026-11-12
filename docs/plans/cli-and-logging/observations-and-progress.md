# Owned observations, correlation and progress

**Delivered contract, 2026-11-10.** [Coordinator final acceptance](../cli-and-logging_2026-11-10.md#final-acceptance)
owns CLD-01/06/07/08 and relevant CLD-09 decisions. This plan develops O05/06 and supports O04/07/08.

## CLD-01 / I01 — One bounded journal, distinct live reads

Select one newline-delimited safe JSON journal per managed observational invocation, written only
by its owning process. Immutable chunks would add publication/index coordination without a useful
benefit for this bounded single-host workload. Keep settled `open_artifact` unchanged; add a narrow
`read_observations` owner operation for this designated live role. A current settled-only refusal
does not require weakening all artifacts or seeking approval merely to add that operation.

Register the journal path/filesystem identity through the managed publication owner. Live reads
hold the existing lease and verify owner/path/regular-file identity with no symlink following.
They return a bounded observed prefix, not a claim of immutable complete content. The current test
reportlog special case is precedent for live reading, not an authority for arbitrary artifact access.
[Publication/leases/read owner](../../../python/corpus-structure/src/corpus_structure/cli/managed.py).

Version1 observation models belong beside managed operation/report contracts; domain report meaning
and native outcomes stay with their existing owners. A row contains local sequence, timestamp,
event kind/severity/stage, safe message/approved fields, available typed correlation bindings,
producer identity/sequence, assurance and any omission marker. Distinguish missing from false/zero.
Never infer provider assurance from common formatting or causal order from cross-process timestamps.

Use initial defaults grounded in existing diagnostic envelopes: 8MiB retained journal, 64KiB maximum
encoded record, 100 returned rows (up to1000) and 256KiB examined per page (64KiB–1MiB allowed).
Collection reserves room for a bounded truncation marker; after the cap stop ordinary retention,
track omitted counts and preserve operation accounting separately. Oversized payloads become bounded
located omissions. A filtered request cannot scan indefinitely looking for enough matches.
These are diagnostic policy limits, not domain execution limits or performance claims.

Serialize/sanitize/bound each complete row before append under one writer lock shared by local
logging threads. Flush complete rows; no assumption that a filesystem write commits a whole record.
A live unfinished last line stays pending with cursor before it. At closure an unfinished line
means incomplete/corrupt coverage, while prior complete rows remain readable. A malformed complete
record reports corruption and a safe stopping cursor; do not silently skip it and claim completeness.

Cursors bind result, journal identity/version, complete byte offset and sequence. Reject replacement,
shortening and incompatible reuse. A response includes observed/examined extents, selected count,
pending tail, collection omissions and running/unsealed/sealed standing. Live growth can continue
after the cursor. Close producers, drain channels, close journal and record final length/digest
before ordinary settlement; sealed replay pins that digest and uses authenticated settled access.
Execution decision, 2026-11-10: verify the complete bounded sealed journal (at most8MiB) once per
independent read operation before selecting its page; a held read/watch scope can reuse that
authenticated input. Each new CLI process rechecks bytes. Inode identity alone is not content
authentication. This bounded integrity work is preferred to another authenticated chunk/index
scheme; live prefix reads remain unsealed and make no digest-authenticated content claim.
Report authentication_bytes separately from examined page bytes. The64KiB record ceiling includes
its newline, ensuring progress at the minimum examination budget. Complete corrupt rows stop that
stream with explicit corruption rather than repeatedly polling an unchanged cursor.
Do not rewrite the manifest on every row. If sealing fails, preserve native outcome and report
diagnostic custody unavailable. A killed owner leaves partial unsealed observations and an unsettled
workspace under existing protection; no automatic semantic recovery is inferred.

## CLD-06 / I02 — Complete pipeline and producer integration

Add exact `structlog==26.1.0` during execution, with intended lock-only changes and affected checks.
Use stdlib integration plus ordinary StreamHandler, not an additional RichHandler full renderer.
Native processing is early severity filtering → scoped context merge → level/logger/time enrichment
→ structured exception transformation with locals off → owned nested safe normalization/bounds →
`ProcessorFormatter.wrap_for_formatter`. Foreign `foreign_pre_chain` adds the corresponding fields
and allowlisted `ExtraAdder` values, initially `database_notice` and explicitly consumed method
fields, then applies the same exception/safe normalization. No arbitrary record dictionary capture.

Safe normalization creates an owned JSON-compatible nested tree before sink fan-out. Bound messages,
notes, groups and depth/bytes, not only frames; unsupported values get bounded type/omission detail,
not uncontrolled repr. Required safe field policy uses existing credential/control rules. Each
destination removes formatter metadata and applies a non-mutating projection. JSONRenderer supplies
machine event encoding; human rows summarize structured exceptions, with explicit Rich traceback/
frame views through the report presenter. Do not feed a structured exception array blindly into a
console exception formatter expecting raw exc_info. Filtering foreign records belongs in stdlib
filters or later reads: raising DropEvent inside ProcessorFormatter is unsafe.

ProcessorFormatter shallow-copies records/event dictionaries; nested values still share references.
Its exception clearing affects the copy. RichHandler can inspect the original foreign record and
rebuild its message even with `keep_exc_info=False`. One final renderer is therefore a consequential
contract. [Stdlib integration26.1](https://www.structlog.org/en/26.1.0/standard-library.html),
[tagged formatter](https://github.com/hynek/structlog/blob/26.1.0/src/structlog/stdlib.py),
[RichHandler15](https://github.com/Textualize/rich/blob/v15.0.0/rich/logging.py),
[exception API](https://www.structlog.org/en/26.1.0/api.html#structlog.tracebacks.ExceptionDictTransformer).

Use INFO as the initial approved-scope collection threshold and expose that policy in inspection
metadata. Read-time severity is a minimum level from DEBUG/INFO/WARNING/ERROR/CRITICAL; it cannot
recover rejected rows. Stage/method selectors match recorded values exactly.
Configure the approved application/method logger routes once per process; do not force-reconfigure
unrelated third-party loggers or install/remove competing global handlers per concurrent MCP call.
Route safe observations to invocation-owned writers using explicit bindings. CLI setup restores
prior owned routes when embedded tests return; a long-lived MCP process configures once. Capture
stderr at the current invocation scope, not module import. Keep first-use caching off initially;
module logger declarations stay lazy, with no eager module-level bind/new. Explicit bound loggers
are preferred; contextvars tokens are restored in finally at invocation/tool/attempt boundaries.
Capture context before a thread/queue handoff; arbitrary readers/executors do not inherit structlog
async dispatch guarantees. No stdout logging in MCP or JSON report channels.

Optional live sink failure degrades diagnostics without changing business outcomes. Retention
failures become explicit managed diagnostic availability and preserve the primary failure/cancel
identity; a logging call never establishes successful custody. Normalization must not raise on an
unsupported value; cancellation/termination signals are not swallowed by a broad sink catcher.

Actual integration includes Invocation.stage/failure boundaries; results inspection/watch; selected
database notices/method warnings; regeneration and `ci run resume`; automated provider capture and
fresh semantic MCP invocation events. Regeneration/resume need a new managed **observational**
wrapper linking their semantic run. Native run creation/completion/cancellation remains native;
the wrapper reports its invocation and known acquired bindings without absorbing task authority.
Keep present direct correction retention choice intact. Do not retain every log call by default.

CLD-CA02 enables the distinct typed exception product for unexpected retained schema defects,
while expected refusals retain their existing validation owner. CLD-CA03 completes ordinary initial
regeneration under ADR-0080: a frozen one-shot SourceRunCreated notification carries actual
run/project/release after native commit and supervisor adoption, inside both cleanup regions and
before graph selection. Its optional callback leaves native resource/settlement authority intact.
The CLI persists those bindings beside acquired storage. The current interleaved replacement is
governed by [ADR-0089](../../adr/0089-isolated-source-plan-observations.md): native plans bind
identity in per-node driver contexts; BEP owns its implementation and qualification. Earlier
CLD receipts describe the preceding linear execution boundary. Ordinary diagnostic binding failure is isolated; BaseException still
reaches native cleanup. Actual initial-source failure/interruption and independent native queries
exercise this boundary. Association is never inferred from method rows, and the notification
does not promise atomicity across native and managed stores. Qualification remains coordinator-owned.

Children never append to the parent journal. Pass a named bounded safe spool path in the existing
explicit child environment; one writer per child process serializes tool threads. Parent drains
complete rows during waiting and after existing cancellation/process-group drain, assigning parent
sequence while preserving producer sequence/identity/assurance. The channel is transient transfer
under the same managed lifetime, not another store. Bound it independently, avoid directory scans
and one artifact per event, and never indefinitely block provider work behind diagnostics. Original
provider receipts stay evidence; imported rows are selected observations of them.
[Provider transfer](../../../python/corpus-structure/src/corpus_structure/intervene/automated.py),
[MCP events](../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py),
[context contracts](https://www.structlog.org/en/26.1.0/contextvars.html).

## CLD-07/08 — Selection, joins and useful progress

Add `ci results inspect RESULT --view summary|observations|timeline`, default summary, with
`--severity`, `--stage`, `--method`, `--provider-invocation`, `--task`, `--attempt`, `--after`,
`--limit`, `--max-bytes`, `--examined-bytes` and `--json`. An attempt selection supplies provider
invocation, task and attempt together; an integer alone is not a globally qualified attempt.
The latter three controls bound returned rows, encoded response bytes and examined journal bytes
separately. Use default response budget256KiB, maximum1MiB; omit complete rows with an explicit
continuation/coverage marker when the full envelope would exceed it. Views consume the same owner
selection: outcome/custody, typed identities, observations, coverage and owner-backed next actions.
Sequence pagination follows parent journal order; timeline preserves explicit causal links and
declares its local ordering, not a fabricated global total order. Summary uses latest owner facts;
collection filters and presentation filters remain distinct. No new remote lookup is implicit.

Join already recorded managed/run/provider/task/request references with their existing reader/
lease/purpose contracts. Unavailable links remain explicit; absent observations are not inactivity.
Retain native versus provider-reported assurance and known-versus-unknown counts. Initial bounded
producer inspection ships in CLD-06; CLD-07 completes these actual cross-owner joins and affected
CLI/MCP inspection consumers. CLI-specific custody need not become an MCP semantic command family.

Extend results watch from that owner with latest useful observations, scoped counts/denominator,
cleanup standing and typed next actions. Preserve test reportlog support and test-only recovery
restrictions. Semantic run resume, result recovery and waiting are distinct actions. Quiet time
does not establish a stalled worker. Final stdout remains one typed result; changes are append-only
bounded stderr lines for captured agents. Do not add another supervisor or timer-derived progress.

I03/CLD-09 selects optional Status/Live/Progress only for a concrete multi-task terminal consumer.
If selected, explicit stderr Console, both redirect flags false, unknown totals and context-managed
cleanup are mandatory. No display is required for headless acceptance. Async logs, bytes serializers,
custom wrappers and remote telemetry remain retained with coordinator triggers.
[Live15](https://github.com/Textualize/rich/blob/v15.0.0/rich/live.py),
[Progress15](https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py).

## Acceptance and migration boundary

Execution exposed a concrete report-read gap (CLD-IR11): compact check excerpts cannot supply
earlier native diagnostics by result ID. Extend the existing bounded step side channel with safe
stream payloads and exact collection/omission counters, retaining one versioned recipe-output
artifact before settlement. A bounded typed `results output` read selects step/stream and a
declared retained-text cursor without exporting files or rerunning checks. Default compact
reports remain available. This is an additional consumer of existing managed custody, not a new
log store. Interrupted/failed native checks keep their original outcome when output retention fails.
Compact excerpts derive from the same already-safe retained selection. For oversized output this
is explicitly an excerpt of the retained prefix, with truncation disclosed; it is not represented
as the native end tail. Retire the separate raw-tail sanitizer, whose clipped multiline credentials
could bypass complete-token redaction. Preserve compact bounds and useful complete-fit output.

Exercise same-process concurrent producers, partial UTF-8/JSON rows, malformed complete rows,
filtered examined-byte exhaustion, cursor replacement/shortening, sealed digest mismatch and
retention overflow. Check safe nested secret-bearing foreign extras and grouped exceptions,
sequential CLI/concurrent MCP isolation, interrupted child final draining, killed owner partial
reads and replay with producer execution disabled. The operator waived the real Claude CLI provider
journey on2026-11-10. Use controlled interrupted subprocesses and actual local stdio MCP/native
integration for identity/receipt behavior; do not label that evidence external-model execution.
All other applicable tests remain in scope.

Configured-chain/backend capture verifies processors and streams; capture_logs alone bypasses
processors and is insufficient. Use independent expected identities/assurance and exact stream
bytes. Reserve a bounded process check for unresolved actual MCP thread/context/shutdown behavior,
not a benchmark campaign. Remove superseded local formatting/handlers and obsolete lifetime tests
as consumers migrate. Planned tests are **not_run** in authoring; unavailable required journeys stay
open in CLD-10. Existing native outcomes and raw evidence custody remain independently authoritative.
