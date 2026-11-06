# Test-resolution tooling and WCE assessment improvements

**Proposed recommendations; reviewed 2026-11-06.** Source inspection establishes the stated
implementation observations, not runtime correctness or measured performance. This is a
plan-improvement review with a functional-extension lens, not a refreshed diagnostic audit,
completion audit or implementation authorization.

## Judgment and inspected boundary

Keep pytest/xdist, the shared PgAdmin lifecycle and the existing receipt classifier as the
integration foundation. Improve their composition and qualify their actual distributed behavior.
Compare a small independently authored SQL contract with the existing Python route; adopt pgTAP
where it removes meaningful machinery or supplies useful SQL diagnostics. Use private clusters for scenarios requiring a
different server configuration or lifecycle, rather than replacing ordinary committed clones.
The richer tooling references justify reconsidering capabilities previously judged unnecessary
for narrower repairs; they do not justify migrating every test to a new runner.

The principal owner is [test-audit-resolution](../plans/test-audit-resolution_2026-11-05.md)
and its four companions. The adjacent footprint is [WCE](../plans/witnessed-corpus-enrichment_2026-11-05.md)
testing, assessment, verification and materially affected preparation/native infrastructure,
including all six supporting plans. WCE product redesign outside that footprint is not assessed.
Existing DTA identities, TR10-F01/F02, WCE F01–07, WCE-R01–03 and PCE F37/F39 keep their
current disposition owners. Recommendations here have no adopted implementation status.

Inspected source: `5599cb0db32c0a5f127d451de510d0fa5f7dcb8e`. Relevant dirty inputs are the
three new tooling references below and the operator's five modified Lark/spaCy/sklearn/Splink/
pgmpy overviews. These remain operator-owned; none is edited or staged by this review.
The PostgreSQL reference's advanced addendum, beginning around line1099, is included.
Core3.3, heuristics1.0, test-assessment1.2, applicable CI1.4 and the repository binding inform
the assessment. Architectural owners D3/D7/D9, DESIGN §2 and ADR-0032/0048/0056/0066 constrain it.

The current package tables and actual source take precedence over older opening status prose:
TR-01–08 are implemented and TR-10 qualification stopped; WCE00–03 have a selected delivered
foundation with WCE02 obligations remaining. Current [configuration][config] uses pytest9.1.1,
xdist3.8.0, `-n auto --dist=loadgroup`; WCE's receipts report32 workers on this host. Older TR
text and the recently published system-tool inventory describe16. Dedicated-cluster configuration
now declares256 connections and1024 locks per transaction; those settings are not proof of a
fully qualified concurrent workload. The prior serial campaign and WCE focused results keep
their original source and coverage limits.

### Source and documentation method

Read the full supplied [pytest reference][P], [xdist reference][X] and [PostgreSQL testing
reference][D], including their addenda; compare them with current consumers, rather than treating
feature availability as a finding. Context7 was the first upstream lookup: pytest9.1.1,
xdist v3.8.0 and `/theory/pgtap`. pg_prove/pg_virtualenv searches did not resolve suitable
standalone entries; installed source and primary documentation supply those contracts.
Context7 pgTAP results include development source, so installed1.3.4 definitions, release
documentation and control scripts take precedence for proposed concrete calls.

Input SHA-256, captured2026-11-06 (hashes identify bytes, not qualified claims):

| Supplied input | SHA-256 |
|---|---|
| pytest,2825 lines | `c19a9ff9abde17176f41f063f666e4d606ca8e0194a3e77829f5a6731a643d98` |
| pytest-xdist,2085 lines | `a33f9971ae4c537c34ced26e20a01c44ec8dbdd9238bce12153b86799eccc3ec` |
| PostgreSQL testing reference,1992 lines including new addendum | `8a9351e866cce3037f6022345a335fca845eace1e7e16ccb38144858b25f146c` |

Current source inspection covers root/package conftest hooks, math/scenario support, PgAdmin,
qualification_plugin, test_receipts and their controls; WCE contribution/frame/scoring/producer
tests and native SQL; current plans and retained TA/TR/WCE evidence. It follows representative
paths, not every assertion in the repository. Functional claims about optional third-party
plugins remain candidates until their exact Python3.14/dependency compatibility is checked.

## Recommended amendments

<a id="I01"></a>
### I01 — Make parallel configuration and resource assumptions current and reproducible

**Observed documentation mismatch and execution improvement; TR-08/10, WCE12.**
[Root scheduling][root] actually groups all package math items and rejects mixed/parallel
shared-cluster faults after marker deselection. [Recipes][recipes] inherit auto worker selection;
the receipt plugin already records requested worker/scheduler configuration. Preserve these strengths.
Revise the scheduled plan descriptions and inventory during adoption to describe current behavior;
retain the16-worker evidence as historical evidence, not a current default.

Make the qualification account distinguish requested concurrency, actual worker processes and
groups that execute work. Use existing per-worker events/xdist lifecycle metadata; no new resource
estimator or admission service. Record the selected host/configuration, actual concurrency and
nested page-pool limit alongside the existing source/native context. Choose worker caps through
the existing CLI/environment mechanisms when a workload comparison warrants them; do not equate
CPU count with PostgreSQL/memory/storage capacity. Keep loadgroup as the initial baseline.

Compare the current route with a bounded explicit-worker selection before selecting any new
default. Connection/lock exhaustion, migration fan-out and model/process working sets matter
together. Raising server limits again is not the first remedy for unnecessary replicated work.
Closure: actual worker overlap and grouping, normal native setup/cleanup and no unexplained
capacity failures in the final required union. FP-07/A4, DP-20/21; heuristics H10/H17/H19.

<a id="I02"></a>
### I02 — Group expensive preparation consumers rather than the whole math directory

**Alignment opportunity; TR-02/09 and shared preparation consumers.** [Root scheduling][root]
assigns every item under `tests/math` to one group. This preserves staged session preparation,
but also serializes independent grammar/kernel cases by physical location. It is a structural
opportunity; this review does not establish that it dominates elapsed time.

Retain the existing staged content/read/extract/scope fixtures and real nested worker deadlines.
Attach affinity from the collected dependency closure of the expensive shared preparation fixtures
or a small explicit mark for the same responsibility, including consumers outside that directory.
Ordinary immutable fixture names are sufficient; do not introduce a scheduling registry. Enumerate
the current actual consumers before choosing the narrow rule. Preserve cold compiler tests and
per-test mutations independently. A content-only fixture need not inherit parser/NLP affinity.

Compare retaining the directory group, narrowing it, and loadscope/worksteal on representative
selections. Prefer narrowing only when it preserves valid reuse and releases useful work; worksteal
can lose warm parser/compiler reuse as well as explicit fixture reuse. Consider both and the
nested child pools before narrowing affinity. Worksteal
in3.8 does not preserve loadgroup affinity. Composite groups are complete marker combinations,
not overlapping locks. Closure: separately selected tiers stay demand-shaped, shared consumers
execute once per intended preparation lifetime, unrelated cases can overlap, and cold/timeout/
token-position controls retain their claims. FP-01/03/06/07; DP-09/10; [X §2–3][X].

<a id="I03"></a>
### I03 — Investigate run-scoped immutable native preparation without sharing mutable databases

**Bounded design investigation; TR-06/09, WCE01/11/12.** Package `semantic_head_template` is
session-scoped, hence worker-local. [PgAdmin.semantic_template][native] performs a real upgrade
and seals a deployment for each worker requesting it. Auto32 can therefore repeat cold deployment
work; current source does not establish that all32 workers request it or that sharing wins overall.

Compare existing per-worker preparation with one run-owned sealed deployment serving independently
owned worker/test clones. Reuse PgAdmin leases, acknowledged ownership, exact policy replay and
native deployment identity; key any reuse by complete migration/extension/runtime prerequisites.
xdist's `testrun_uid`, workerinput and the documented locked once-per-run pattern are mechanisms,
not an exactly-once or cleanup guarantee. Never publish a half-built template, reuse a mutable
application database, or make ordinary pure collection acquire PostgreSQL.

Select shared preparation only if bounded comparison demonstrates useful avoided work and a
credible owner surviving worker replacement; otherwise retain worker-local templates. The
initializer cannot own deletion merely because it created a shared path: all clone consumers must
settle first. Keep genuine cold-bootstrap/migration controls separate. Required countercases are
two consumers racing initialization, initializer failure, worker death, stale/mismatched deployment,
policy mismatch and cleanup with another clone still alive. No persistent cross-run cache or new
janitor is recommended. FP-02/05/07; DP-09/19/20; [X §3.2–3.4][X].

Current disposition: retain per-worker templates. The prior shared-lock failure was repaired and
the focused native selection passed; no current measured bootstrap obstruction is established.
Enter this investigation only when repeated deployment materially obstructs a required workload.

<a id="I04"></a>
### I04 — Test distributed hook contracts through pytest's own test infrastructure

**Recommended infrastructure enhancement; TR-07/08/10.** [Receipt controls][receipt-tests]
already use independent canned artifacts and real subprocesses for collection, phase failures,
hangs and cancellation. Preserve both assurance roles. Add a small pytester-based subprocess
conformance suite for actual plugin/xdist wiring, not another framework or replacement of direct
PgAdmin lifecycle tests.

Exercise canonical selection with serial and two-worker runs: grouped and ungrouped cases,
composite groups, parameter IDs containing literal `@`, deselection, collection failure, failed
setup, teardown failure and bounded worker loss. Check actual plugin output and classification,
not manually constructed expected hooks alone. Use pytester for temporary test/config creation
and subprocess outcome assertions; retain run_process tests for the supervisor it implements.
Explicit plugin loading and isolated child config must prevent nested auto32 recursion.

Replace only temporary-module/config scaffolding and output inspection that pytester supplies
more simply; retain the existing `child` helper if its direct use of run_python better preserves
receipt ownership. New distributed scenarios are the required capability, not pytester adoption
for its own sake.

The existing aliases in [qualification_plugin][plugin] and [classifier][runner] remain the
semantic owner of execution-to-logical identity. Do not replace them with arbitrary suffix removal.
Keep the pytest9.1.1/xdist3.8 hold until upstream compatibility is verified. Test whether alias
mapping remains injective for selected composite names; reject ambiguity rather than merge claims.
Compare suffix reconstruction with capturing the original Item nodeid in a public collection
wrapper before xdist mutation, retaining it in item.stash and emitting the exact map afterward.
This could remove suffix-encoding knowledge, but requires verified hook order and explicit worker
serialization; Stash is process-local. Prefer it only if conformance establishes a simpler exact map.
Closure includes a deliberately incorrect grouping/alias behavior that the new controls reject,
raw scheduler IDs retained, and no false passed native claim. FP-02/05/06; DP-15/23.

<a id="I05"></a>
### I05 — Add a focused SQL contract suite, integrated through the existing native owner

**Conditional functional extension; TR-03/04/08, WCE01/04–06/11.** New witnessed SQL contracts
have useful independently inspectable properties: exact endpoint/source relationships, refusal
SQLSTATE, routine signatures, security attributes and privilege boundaries. A small pgTAP suite
can express these directly with SQL-local type, multiset and catalog diagnostics.
This complements actual-role Python integration tests; it is not evidence that those tests are
generally redundant.

Use independently authored literal relations and `results_eq` for promised order, `bag_eq` when
multiplicity matters, and set assertions only for true set contracts. Explicitly qualify schemas
and routine argument types for `has_function`, `function_returns`, `is_definer`, volatility and
privilege checks. Assert safe routine configuration through scoped catalog queries where needed.
The addendum correctly limits `functions_are` to names and schema/search-path scope: combine it
with signature-level expectations instead of calling it an exhaustive overload inventory.

Have PgAdmin own an isolated migrated clone; install the test-only extension there after normal
deployment checks, without adding it to the application's four-extension contract. Invoke
pg_prove as a bounded child using exact clone/purpose connection coordinates. Use the existing
pytest receipt as the file-level required item; retain SQL file identity, expected TAP plan,
raw TAP/diagnostics, process exit and actual acquired native identity. A new psql connection must
attest its own principal/database, not inherit a Python connection's claim. Resolve that bridge
before counting TAP results as native qualification. Do not sum nested assertion counts into
pytest item coverage.

Initial delivery should use hand-authored scripts with explicit plans and `BEGIN`/`finish`/
`ROLLBACK`; do not introduce resident test functions merely to use runtests. `do_tap` does not
provide runtests' test-local rollback; `runtests('schema'::name)` needs overload precision. Prove
success, a wrong SQLSTATE, duplicate-row mismatch, missing assertion, SQL execution error and
malformed/truncated TAP. A clean psql exit or a TAP-looking line alone cannot establish success.
Caller overrides must not undo pg_prove's controlled psql defaults.

Prefer this small composed lane to a wholesale pg_prove runner migration. Reuse existing Python
guards when no simplification or new SQL-level assurance results. pg_prove `--jobs` shares a DB
unless explicitly arranged otherwise: begin serial inside a pytest-owned clone and add job
parallelism only for demonstrably independent files, avoiding multiplicative outer/inner pools.
Preserve committed cross-session, pool/cursor, Python refusal and shared-cluster authentication
controls. Closure requires true positive/negative SQL/native controls and TAP-to-receipt fidelity.
FP-02/04/06/07; DP-13/14/15; [D §2–3 and addendum §1–2][D].

The source mapper preferred pytest/SQLAlchemy alone; library assessment identified pgTAP as
useful only for clearer sizeable relational expectations or focused catalog contracts. This
review recommends one bounded new-WCE contract comparison before adopting the lane: hand-author
the same positive/refusal/multiplicity case both ways and adopt pgTAP only if it removes meaningful
surrounding work or adds useful assurance. Existing native_sql_body/source_frame_admission controls
already cover substantial signature/body/ACL drift; do not duplicate their entire attestation suite.
The receipt bridge is required if the SQL lane is selected, not merely to complete original TR
repairs. No end-to-end bridge feasibility is claimed tested.

<a id="I06"></a>
### I06 — Use private clusters for server-lifecycle and configuration variation

**Recommended bounded capability, scenario-triggered; TR-06/10 and native WCE migrations.**
Keep ordinary development on the persistent dedicated database and ordinary tests on owned
clones. Use pg_virtualenv for tests whose actual subject is cold cluster setup, extension-loading
configuration, server restart or incompatible settings. This enables useful server-level
scenarios without mutating18/corpus or the unrelated18/main service.

Use the installed postgresql-common293 wrapper's nonroot/private paths and explicit PostgreSQL18
selection; normalize inherited libpq service/address settings and verify actual acquired endpoint.
Installed source confirms its default `fsync=off`/initialization `--nosync`; override durability
settings before any durability/recovery claim. A disposable cluster is not OS/service isolation
or crash-proof cleanup. Preserve failed logs and provide bounded process/cluster settlement using
the existing owner patterns, rather than interpreting wrapper exit as complete cleanup.

Do not move all eight actual shared-cluster controls merely to make them parallel. A private
scenario can qualify generic configuration/recovery mechanics; original dedicated-cluster peer
mapping and operator-authority claims need their actual environment. PostgreSQL-version matrices
are optional only when another server version becomes supported; creating multiple clusters does
not run the suite against each automatically. Closure: intentionally conflicting parent connection
environment, failed startup, interrupted child, exact endpoint and complete owned cleanup.
FP-02/05/07; DP-19/20; [D §4 and addendum §4][D].

<a id="I07"></a>
### I07 — Compose independent WCE case matrices at the question boundary

**Recommended assessment extension; WCE02–12, preserving TR-01/03/04.** Current
[operation assessment tests][assessment-tests] already distinguish source/output direction,
missing predictions, protected provenance and reference missingness. Extend these concrete
patterns into small question-specific scenario builders plus independently authored expectations,
not a universal expected-answer generator or a fixture copied from current predictions.

Use `pytest.param` with meaningful stable IDs and indirect setup only for native variants.
Generate required finite matrices deterministically; missing required cases should fail collection
or explicit inventory checks rather than silently skip. Assert count and named membership where
they establish completeness. Do not impose an empty-set policy on legitimate zero-output product
results. Keep required cases separately collected; runtime subtests are useful diagnostics within
one claim, not automatically separate qualification obligations.

Cover: right location/wrong linguistic role (WCE-R01); correct role/wrong endpoint; incompatible
versus compatible overlap; source opportunity missing after filtering; repeated windows versus
physical fact identity; exact output omitted/extra/duplicated; original family exposed under an
unchanged partition (WCE-R02); alternate parameter/header/note scope (WCE-R03); local component
valid while whole report remains unsupported; insufficient cohort without invented labels.
Add threshold endpoints, units/revisions and conditional-model refusal cases with each actual
later producer rather than declaring their outputs available now.

Keep pure scoring cases free of native publication and provider startup. Add native, Reader/CLI/
MCP/export variants only for the boundaries they establish. A/B/C source authors and held-out
labels remain protected: developer reports contain identifiers and permitted diagnostics, not
private answer populations. Closure: known wrong answers rejected, original source-first
denominator/output IDs retained, and source-quality claims bounded to independent actual sources.
FP-04/05/06; CI-02/04/06/10/12; [WCE assessment companion][W].

<a id="I08"></a>
### I08 — Improve failure diagnosis through native pytest reports, preserving durable journals

**Recommended developer capability; TR-07/08, WCE02/11/12.** Use assertion rewriting for shared
assertion support modules, narrow comparison explanations and phase-specific report sections to
show missing/extra members, exact SQLSTATE/constraint, source/output identity and the first
meaningful contract difference. Avoid giant full-object dumps and normalization that erases
multiplicity, scope or unknown/absent distinctions. Source expected values remain independent.

Use public `StashKey` for per-config/item extension state where it removes ambiguous ambient
state. Keep an explicit active observer bridge where callbacks genuinely lack a pytest Item;
moving a variable into Stash does not itself solve attribution. Existing phase and native event
journals remain durable crash evidence. workerinput can carry bounded immutable invocation
configuration; workeroutput can summarize orderly completion. Neither supplies live shared state
or survives every crash, and clean worker exit does not imply test success.

Retain setup/call/teardown and collection outcomes in reportlog/classification. Custom report
serialization is needed only if ordinary serializable user_properties/report sections cannot
carry a selected diagnostic. Do not replace native acquisition or deployment evidence with JUnit
properties; suite-level properties have xdist limitations. Closure: a distributed failure names
its exact source/question/phase without leaking labels, and a killed worker leaves an incomplete
claim with usable prior events. FP-04/06; DP-18/21; [P §6/9/10][P], [X addendum §1–2][X].

<a id="I09"></a>
### I09 — Make failure-focused iteration safe without automatic retry semantics

**Recommended workflow enhancement; TR-10, WCE12.** The existing required-node manifests and
receipt union remain qualification authority. Offer pytest `--lf` or pg_prove `--state failed,save`
for local diagnosis, with explicit no-history/no-failure behavior that cannot unexpectedly replay
everything. Saved history is not dependency analysis, required scope or native applicability.
Maintain canonical IDs and preserve original attempts when producing exact failed-node argument
files. Collection failure, interrupted and never-started cases remain pending, not absent.

Do not add automatic rerunfailures to obtain green qualification. A recovered worker and retried
test are different events; a crash may retain external effects. Default faulthandler process exit
is not a recoverable per-test timeout, and grouped xdist schedulers do not all implement crash-item
requeue. Keep supervisor settlement and the exclusive auth lane. Apply supported strict parameter
IDs, error-on-required-empty matrices and targeted thread/unraisable/deprecation warning policy
where they detect actual harness mistakes; do not blindly enable every strict option globally.
Closure: empty history, stale node, collection error, crash and cleanup failure cannot disappear
into success or silently broaden a requested failed-only iteration. FP-05/06; DP-20/21/23.

<a id="I10"></a>
### I10 — Qualify the implemented intervention once, at the integrated boundary

**Required acceptance amendment selected by the operator; TR-10 and WCE12 keep their scope.**
After chosen infrastructure changes and consumer migrations are implemented, obtain the applicable
assembled review, finalize source with root `just turn-end`, then run `just test-all` using the
selected parallel configuration. Run required `just test-native-faults` separately/exclusively;
run applicable `just hygiene`. Include any adopted SQL/private-cluster route in the declared
required union, through existing native results rather than inventing successful provider coverage.

Retain failed/interrupted records. Repair failures and rerun failing tests/checks, carrying forward
successful results with their exact source/configuration applicability. If a subsequent shared
harness/configuration change invalidates successful evidence, identify that consequence explicitly;
do not silently claim applicability or replay the whole successful suite. Rust uses release nextest
with `rustc --version`; empty selection remains not_run. Missing required providers/data remain
blocked, and complete qualification cannot be inferred from overlapped counts.

This future fresh qualification is explicitly selected for implemented improvements. It does not
resume the old1390-node pending campaign during this documentation review, erase its historical
successes, or close WCE semantic efficacy merely because tests pass. No product qualification is
run for publishing this review. FP-02/05; DP-22/23; test-assessment §4/6/8.

<a id="I11"></a>
### I11 — Separate required-union satisfaction from retained attempt history

**Recommended reporting enhancement; TR-08/10, WCE12.** `classify()` in [test_receipts][runner]
already computes per-node coverage and required_unresolved, but its aggregate status remains failed
whenever any included receipt failed. A passing repair can therefore satisfy the required-node
union without changing that historical aggregate. This is conservative existing behavior, not
evidence that earlier failures should be hidden or that current users falsely claimed a pass.

Preserve the aggregate/history and raw attempts; expose a distinct required-union result with
explicit applicability limits, or make that distinction unmistakable in the existing human report.
Prefer an additive interface over changing the existing status meaning. Required-node satisfaction
must still require eligible source/context and item-bound native evidence; empty manifests do not
establish complete qualification. Session cleanup, collection loss, Rust/provider obligations and
unavailable prerequisites need their own satisfaction, not merely a passing node union.

Closure: a failed attempt plus an eligible successful repair retains the failure while showing
resolved required-node coverage; wrong-context repairs and contextless native passes remain
unresolved. An unrelated surviving process or missing required selection must still prevent
complete acceptance. This directly supports failed-only repair without rerunning successful tests.
FP-04/05/06; DP-05/21/22; test-assessment §6. No receipt schema is changed by this review.

## Additional functional opportunities and coverage of the references

All documented families below were considered, including features that need no diagnostic defect
to be useful. “Conditional” means a concrete entry condition, not scheduled work or an installed
dependency. Retaining an existing mechanism is a positive assessment when alternatives add burden.

| Reference family | Contextual disposition and reason |
|---|---|
| P §3, addendum §2: collectors, nodes, imports, naming, namespace/root/conftest controls, duplicate/deselection handling | Existing importlib/node selection is appropriate. I04/09 strengthen identity/completeness. A custom SQL Item collector is an alternative to I05's simple wrapper, deferred until file discovery/selection actually needs it; custom Items do not automatically inherit Python fixture/assert behavior. |
| P §4, addendum §4.2/§5.4–5.5: scopes, factories, indirect/dynamic fixtures, overrides, register_fixture and node visibility | I02/03/07 reuse ordinary dependencies. Public registration is useful for a future genuinely external fixture provider; current statically declared fixtures need no dynamic registration or registry. Autouse/config usefixtures would activate unrelated work here. |
| P §5, addendum §1: generated cases, fixture variants, subtests, strict IDs/empty sets | I07/09; parameter values are not automatically copied, so mutation cases retain owned values. Required separately selectable native cases should not disappear into subtests. |
| P §6, addendum §6.2–6.3: rewriting, raises/group matching, approx, warns and assertion presentation | I05/07/08. Use exact native diagnostics and complete exception-group expectations where relevant. Approx is useful for numerical contracts with independently justified tolerance, not IDs/roles or a universal score tolerance. |
| P §7, addendum §3/§9: skip/xfail/XPASS, importorskip, marker evaluation and runtime outcomes | Preserve explicit prerequisite/inapplicable classification. New conditional WCE providers must not turn missing required coverage into optional skips. Missing transitive imports need attribution; runtime markers do not retroactively schedule fixtures. |
| P §8/14: monkeypatch, FD/binary capture, logging, tmp paths, background exceptions/current test | I04/08/09; FD capture is useful for psql/native/subprocess diagnosis, phase logging for pool/cleanup failures. Restore state and keep subprocess output bounded. Process-global patches are not thread isolation. |
| P §9/13, addendum §4–5: Pluggy dispatch/wrappers/optional hooks/specname/Stash/config/plugin requirements | I04/08 use public mechanisms. required_plugins can fail fast for a missing required runner, but manifest pinning and tested compatibility still govern. Do not add hook specifications or replace configuration parsing without a real external consumer. |
| P §10, addendum §6: reports, JUnit, cache, setup inspection, pytest.main and exits | I04/08/09. Keep subprocess isolation over repeated in-process pytest.main for harness controls. Report/warning-limit nonzero exits require accurate classification, not assumed assertion failures. |
| P §11, addendum §7: unittest/xUnit/doctest/typing | Public fixture typing is useful maintenance inside affected modules. No unittest migration is indicated. Small executable documentation examples are conditional on real public examples; a new whole-doc doctest campaign/Sybil integration is not warranted by this footprint. |
| P §12: async/AnyIO/Trio/Hypothesis | Retain existing property tests and actual MCP/task cancellation controls. New async provider fixtures must align loop/task lifetime and avoid competing auto modes. Reused fixtures do not reset for every Hypothesis example. No new async engine is selected merely from availability. |
| P addendum §8.1, X §8: pytest-benchmark, durations, worker-stats | Useful optional experiments for an identified WCE recipe/preparation regression. Durations/worker stats first locate work; benchmark measures selected pure kernels in a separate non-xdist lane when its plugin requires it. No default performance gate or speedup claim. |
| P addendum §8.2: pytest-memray | Conditional on a concrete Python allocation/retention issue in parsing, matcher preparation or large reads; compare warm/cold ownership and allowed caches. Verify Python3.14/native-wheel support first. Python allocation data alone does not account for PostgreSQL/GPU/child-process working sets. |
| P addendum §8.3: Syrupy/snapshots | Useful optional reviewed structural CLI/export diagnostics; exact scoped field assertions remain preferred for WCE semantics. Never regenerate protected semantic answers from producer output or snapshot unstable IDs wholesale. Existing Rust insta update rules remain. |
| P §12.6: coverage.py/pytest-cov | Conditional diagnostic coverage contexts can identify unexercised new WCE refusal branches. Coverage is execution attribution, not oracle independence or native/provider qualification; subprocess support must follow the installed coverage integration version. No coverage quota. |
| P/X ecosystems: pytest-mock, randomly/random-order, BDD, browser/Django integrations | Existing monkeypatch suffices for isolated policy seams. Optional seeded order variation can reveal fixture interference in a selected safe subset, not in shared auth controls or as a substitute for real interleavings. BDD/Playwright/Django have no current consumer in this footprint. |
| P/X timeout/retry/forked companions | I09 retains native faulthandler/supervisor semantics. pytest-forked inherits parent state and does not replace spawn/token transport or DB cleanup; no added fork layer. Retry plugins can hide first failures and preserve fixture effects; not selected for qualification. |
| P addendum §8.5, X §5: tox/Nox, interpreter/SSH/socket gateways, proxies and each | Conditional compatibility route when another interpreter/host/server is supported. Python3.14 is currently deliberate; remote gateways do not provision source/data/native services. `each` replicates selection rather than accelerating it. No new environment matrix now. |
| X §2/addendum §3: every distribution mode, queue heuristics/chunks/composite groups | I01/02 retain built-in scheduling. loadscope/loadfile are alternatives for real fixture locality; worksteal is queue-count based, not a historical duration model. No custom scheduler: current opportunities can use built-ins and narrower preparation. |
| X §3–4/addendum §1: identities, tmp roots, once-per-run state, CPU hooks, main thread | I01/03/08. worker_id and testrun_uid serve different lifetimes; replacements need distinct resource identity. Once-per-run initialization needs actual locking/publication. Preserve main-thread parser signal behavior. |
| X §6–9/addendum §2/4–6: lifecycle hooks, serialization, crash handling, collection/debugger limits | I04/08/09. Collection-only bypasses distribution and cannot prove real overlap. Group affinity is not a lock manager. Workeroutput/clean shutdown is insufficient for acquisition or full pass. No replacement remote runtime. |
| X addendum §7: worker-stats, rate-limit and weighted load-testing plugins | Worker statistics are useful optional diagnosis. Provider pacing becomes relevant only to an actual rate-limited external provider; prefer its existing limit owner over global file-backed throttling. Weighted repeated tests are a separate load experiment, not functional qualification. |
| D §2.1–2.4: scalar/pattern/NULL/typed/prepared/cursor/set/bag/ordered comparisons | I05. Independent literal expected rows preserve order/multiplicity and type semantics. Native prepared/cursor assertions are conditional on a concrete server cursor contract; existing driver lifetime tests remain. |
| D §2.5–2.8, addendum §1: catalog/routine/privileges/type/index contracts | I05 selectively adds signature/attribute/column-grant assertions around actual changed APIs. Cast context, enum order, domain base type, rewrite rules, operator/opclass, FDW, inheritance, language and tablespace assertions need an actually governed object. Do not assert every system catalog merely because the API exists. |
| D addendum §1.3/§1.5: expression/partial index and inventory scope | Useful when a changed WCE query depends on that index contract; assert keys/predicate/method independently. Metadata does not prove planner use or symbolic equivalence. Names alone do not establish overload identity; explicit schema and signature matter. |
| D §2.9–2.11/addendum §1.6–1.7: SQL fixtures/extensions/custom assertions | I05 prefers explicit scripts/plans; runtests lifecycle is an alternative when real resident suites emerge. skip/TODO cannot close required evidence. Separate pgtap-core/schema packaging is not needed for the initial full installed extension; check control files before splitting dependencies. |
| D §3/addendum §2: discovery, jobs, history, inline sources, TAP harness/archive/formatters | I05/09. Preserve SQL error and TAP assertion/parse failure separately, explicit file inventory and process/session boundaries. Mixed Perl TAP embedding is possible but no current consumer justifies another global runner. TAP archives are useful diagnostic artifacts, not inherently JUnit or native provenance. |
| D §3.7/addendum §3: pg_tapgen including overloaded body checksums | Conditional operator/deployment drift aid, not selected as a new qualification layer: current native frozen SQL/deployment attestation already owns body identity. Experimental generated baselines can help inspect an unfamiliar legacy schema, but require reviewed expected state, DBI/DBD::Pg availability and explicit schema exclusions. They do not supply independent semantic truth. |
| D §4/addendum §4: version/config/private paths, durability, environment and diagnostics | I06. Installed293 confirms normalization and fast defaults. Its EXTRA_REGRESS_OPTS/PG_TEST_INITDB_EXTRA_OPTS additions occur inside the package-staging branch, not blanket wrapping of arbitrary commands. Preserve logs/core diagnosis; never enter an interactive diagnostic shell in automation. |
| D §4.7–5.4: staged/custom-prefix extensions, PGXS/pg_buildext/autopkgtest, core TAP/pg_regress/isolationtester | Conditional extension-development or real interleaving tooling, not required for current application assertions. PostgreSQL core Perl TAP is separate from pgTAP and can exercise recovery/replication if those become supported responsibilities. Avoid nested temp-instance lifecycles when existing-server mode answers the question. |

## Integration, challenge and adoption route

I01/I04/I07/I08/I09 are coherent first amendments: they improve the existing harness and the
new WCE test surfaces without changing product semantics. I02 depends on identifying real fixture
consumers; do not mechanically move a directory mark onto all session fixtures. I03 remains an
investigation until shared lifecycle ownership and benefit are credible. I05 compares a conditional
SQL capability before adoption, requiring an explicit receipt bridge if selected; I06 supplies server-level scenarios only
when their isolation/configuration premise applies. Neither is a prerequisite for every WCE case.
I10 closes the implemented intervention, not every conditional option in the coverage table.
I11 makes retained failures and successful repairs understandable without changing either outcome.

Consequences determine priority: identity/provenance and independent WCE discrimination precede
throughput tuning. Prerequisite order differs: settle selected node/receipt contracts before adding
a TAP lane; settle actual reuse ownership before sharing preparation; create question-specific
independent cases with each producer rather than waiting for WCE11 to expose integration failures.
Retain existing valuable direct-owner tests, cold compilation, real-role acquisitions, committed
clones and actual SDK transports. Retire only the helper/setup branch a selected replacement
actually takes over, after all maintained consumers migrate.

These amendments require no selected §B semantic change, weakening of native grants, reference
exposure or provider truth. A proposed shared-template ownership change must receive focused
design/target assessment against D3/ADR-0032 before implementation. A new supported PostgreSQL
version or removal of actual-environment fault obligations needs separate explicit scope/decision
disposition. Updating plans is separately instructed; no package/finding state is changed here.

Challenge cases include: a faster shared template with incomplete policy replay; a clean pg_prove
exit but failed/missing TAP; a privilege assertion run as an administrator instead of the claimed
principal; the right WCE span with wrong role; one physical fact counted several times; and a
worker crash losing its orderly summary. Each recommendation's closure preserves these distinctions.
No benchmark quota, instrumentation service, test DSL, universal validator or second disposition
register is proposed. Performance/memory/compatibility opportunities outside current concrete
requirements remain conditional with the triggers in the table.

## Evidence limits and publication verification

**Interface-checked,2026-11-06:** current source and documented public interfaces support the
bounded recommendations. Installed source confirms pg_prove3.37's controlled psql invocation
and postgresql-common293's environment/package-stage behavior. **not_run:** product tests,
provider execution, database probes, installations, cluster mutation and qualification; none was
needed to publish reasoned proposals. No speedup, complete concurrency envelope or semantic
efficacy is claimed. The exact optional-plugin/provider compatibility and I03's benefit/lifecycle
question remain explicit implementation prerequisites, not unrecorded assumptions.

An independent design reviewer challenged the full draft and the revised recommendations on
2026-11-06. The review incorporated its SQL-adoption gate, retention of direct owner/runner
controls, conditional shared preparation and warm compiler reuse. Final judgment: coherent
Proposed amendments, with no material unresolved correction. That is review advice, not runtime
qualification. Publication uses `just turn-end`, `just docs-check` and scoped `git diff --check`;
the publication commit/final handoff record their actual outcomes. No publisher/resolver changed,
so `just docs-test` is not_run.

Primary capability sources: [pytest9.1.1 plugin testing](https://github.com/pytest-dev/pytest/blob/9.1.1/doc/en/how-to/writing_plugins.rst),
[fixture lifetimes](https://github.com/pytest-dev/pytest/blob/9.1.1/doc/en/how-to/fixtures.rst),
[xdist3.8 distribution](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/distribution.rst),
[worker implementation](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py),
[pgTAP1.3.4 distribution](https://pgxn.org/dist/pgtap/1.3.4/),
[pg_prove source/CLI](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove),
[pg_virtualenv293 source](https://sources.debian.org/src/postgresql-common/293/pg_virtualenv/).
Installed boundary sources: `/usr/share/postgresql/18/extension/pgtap--1.3.4.sql`,
`/usr/share/perl5/TAP/Parser/SourceHandler/pgTAP.pm` and `/usr/bin/pg_virtualenv`.

[config]: ../../pyproject.toml
[root]: ../../conftest.py
[recipes]: ../../justfile
[native]: ../../scripts/native_test_support.py
[plugin]: ../../scripts/qualification_plugin.py
[runner]: ../../scripts/test_receipts.py
[receipt-tests]: ../../tests/scripts/test_test_receipts.py
[assessment-tests]: ../../python/corpus-structure/tests/evaluate/test_operation_assessment.py
[P]: ../libraries/analytical_infrastructure/pytest.md
[X]: ../libraries/analytical_infrastructure/pytest-xdist.md
[D]: <../libraries/postgresql/pgTAP, pg_prove, and pg_virtualenv.md>
[W]: ../plans/witnessed-corpus-enrichment/assessment-source-expansion-and-qualification.md
