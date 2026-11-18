# Preparation identity: the head key, recipes and bindings, and the completed-capture seed

**Status:** In execution. Native keying, per-consumer acquisition and shared PDF capture are implemented.
**Created:** 2026-11-17. Writing this plan authorizes no implementation.

This companion owns the designs of **TDM-06** (the deployment key covers what the build runs),
**TDM-07** (a recipe is content, a binding is a location, and one bounded memo) and **TDM-08** (a
seed stage for the completed PDF capture). It contributes to findings
[DTA-038](../../design_review/test-audit/execution-and-qualification.md#dta-038),
[DTA-039](../../design_review/test-audit/execution-and-qualification.md#dta-039),
[DTA-040](../../design_review/test-audit/execution-and-qualification.md#dta-040) and F06, and it
depends on rule changes RC07, RC08 and RC11, which the operator accepted on 2026-11-17 and whose
required content is stated under
[What the superseding records must say](#what-the-superseding-records-must-say). Package state,
the queue, finding dispositions, shared contracts, deferrals, rejected options and external context are
the [coordinator's](../test-domain-model-and-execution_2026-11-17.md).

**Baseline and evidence.** Section references such as §4.2 mean the
[design review of 2026-11-17](../../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md),
which read source at `1afa63f88`. The plan was authored against commit `50827eb9f` (the authoring
baseline, 2026-11-17) and revised against commit `12f57dc4d` (the revision baseline, 2026-11-18),
after the model-owned SQL conversion
([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)) was completed. The conversion is
under validation, so source may still move a little; TDM-00 re-reads what changed since
`12f57dc4d`. Source facts re-read at the revision baseline are **Interface-checked by source
inspection, 2026-11-18**, and line citations are to that commit. Facts that were not re-read keep
their 2026-11-17 label: in this document those are the statements drawn from the seam advice
about where production writes, and the consumer map's classification of where each consumer's
claim starts. Nothing was run; where this document says a test or a reuse "cannot" behave in some
way, that is by reading, not run. Every design statement is **Proposed**. No speedup is claimed.
The investigation reports this companion draws on are in the evidence folder
`docs/design_review/evidence/2026-11-17_test-plan-authoring/`: the
[current-state map](../../design_review/evidence/2026-11-17_test-plan-authoring/state.md), the
[PDF source consumer map](../../design_review/evidence/2026-11-17_test-plan-authoring/pdf-source-consumers.md), the
[seam advice](../../design_review/evidence/2026-11-17_test-plan-authoring/seams.md), and the two re-reads at `12f57dc4d`: the
[identity re-baseline](../../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-identity.md) for this companion's sites and the
[boundaries re-baseline](../../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-boundaries.md) for the PDF converter boundary.
`tests/…`, `src/…`, `target_alembic/…` and `semantic_alembic/…`
are relative to `python/corpus-structure/`; repository-root paths are written as root `scripts/…`
and root `conftest.py`. The key's and the seed registry's own tests live under root
`tests/scripts/`; the identity re-baseline read them at `12f57dc4d`.

## Review integration · 2026-11-18

**Proposed.** This revision integrates I02, I03 and I05 from the
[November 18 improvement review](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md).
Its inspected checkout was `aea554e5c`. The earlier counts and line references below retain
`12f57dc4d` as their baseline. TDM-00 re-reads affected consumers as well as changed files before
execution. TDM-06's identity correction starts early, independently of the fixture migration.

## Why this work exists

Prepared test state is expensive: a deployed head database, a scenario seed built by real
producers, a prepared release, a completed PDF capture. The test system already reuses the first
two under an identity, a deployment key for the head and a recipe value for a seed. The review
found the identities right in shape and wrong in three particulars, and authoring found a fourth
that changes the account of the first.

1. The head's key does not describe the head. It hashes a migration tree the build no longer
   runs, so nothing the build executes enters the key at all (found during authoring).
2. Within the tree it does hash, the key counts file timestamps instead of content and cannot see
   imports made by the upgrade bodies the revisions execute (DTA-038). A few steps around the key
   are repeated for no reason (DTA-039).
3. A PDF scenario's recipe contains the directory of the test that built it, because production
   writes the capture workspace into the release. Every such recipe is therefore unique, is sealed
   as a seed nobody else can use, and stays registered for the worker's session (DTA-040).
4. Every consumer of the PDF source scenario runs a full capture, although most of them assert
   only on what follows the capture (F06).

**What this companion consumes.** The accepted rule changes RC07, RC08 and RC11; the seed registry,
head lifecycle and isolation classes of the earlier test-system plan (ADR-0101, ADR-0102), which
are kept; and, for TDM-08 only, the controlled PDF converter with data-described content that
TDM-09 completes ([controlled boundaries and seams](controlled-boundaries-and-seams.md)).

**What it produces.** A head key computed over the files the build executes; a recipe and binding
split with binding-aware caches; a registry route that builds a per-consumer scenario without
sealing it; and a completed-capture seed stage with its eligible consumers moved.

**Where its responsibility ends.** The perturbation table that proves the key's safety cases is
TDM-13's ([reuse and refusal evidence](reuse-and-refusal-evidence.md)); this companion names the
cases its own acceptance needs and they are written once, in that table. The single PDF recipe
composer is TDM-03's ([model binding and independence](model-binding-and-independence.md)), and
it still takes a directory; TDM-07 changes that one composer to take content and a binding
separately. The controlled converter is TDM-09's. Production is not changed here: the fact that a
release's identity contains a filesystem path is a row of the coordinator's
[production context](../test-domain-model-and-execution_2026-11-17.md#handovers).

## Baseline at `12f57dc4d`

### The key hashes a tree the build does not run

`PgAdmin.deployment_key` passes `chain=repository / "python/corpus-structure/semantic_alembic"`
(root `scripts/native_test_support.py:912`). The build is `construct_deployment`, which calls
`corpus_structure.semantic.migrations.upgrade` (root `scripts/native_deployment_build.py:10, 19`),
and that module sets `ALEMBIC_DIR = Path(__file__).resolve().parents[3] / "target_alembic"`
(`src/corpus_structure/semantic/migrations.py:14`) and uses it as the default script location
(`:18–24`). The two trees are different directories:

| Tree | Revisions | Role at the baseline |
|---|---|---|
| `semantic_alembic/` | 285 revision files, about 1.8 GB with artifacts | Frozen history. `upgrade()` does not run it. The key hashes all of it |
| `target_alembic/` | 29 revisions in one line from `semantic_ddo_current_root` to the head `semantic_ddo_pe_n13`; 32 Python and template files; 87 artifacts; about 342 MB | The chain every head is built from. No file under it enters any key component |

The consequence, by reading: adding or changing a target revision leaves the key unchanged. The
next narrowed run reuses the old head; first-use verification compares the head's revision with
`head_revision()`, which does read the target tree (`native_test_support.py:351–375`), fails,
retires the head, records a `deployment_key_gap` and builds a run-private replacement
(`:334–348`). A change that keeps the head revision the same, such as a regenerated artifact of
the newest revision, is bounded only by the catalog predicates of `verify_deployment_catalog`.
Conversely, any edit to the frozen tree, which cannot affect a head, rebuilds one. The review's
figures ("285 revisions replayed", "twenty executed bodies") describe the frozen tree; they are
restated below against the tree the build runs.

This defect predates the review (the same code stood at `1afa63f88`; the script location moved in
`e6b99719b` on 2026-11-16), and the conversion left it in place while adding seven target
revisions (N7 to N13), each a frozen generator output that no key component sees. It is the first
thing TDM-06 corrects, because the review's two corrections are meaningless while the key reads
the wrong tree.

### What the target chain executes

Every target revision has the same shape (`target_alembic/versions/semantic_ddo_current_root.py`,
read in full; the other 28 match by search). It names three artifacts and pins each by SHA-256
(`NATIVE_UPGRADE_FILE` and `NATIVE_UPGRADE_SHA256`, and the same pair for `NATIVE_STATE` and
`NATIVE_ADMISSION`, `:15–20`), reads them through a function that refuses a digest mismatch
(`:23–27`), compiles and executes the upgrade body (`:35–38`), and then calls `admit_native` and
`admit_privileges` (`:39–42`). The revision imports `native_objects` at module level (`:9`) and
`alembic_privileges` only inside `upgrade()` (`:41`).

- **The executed bodies import at module level.** All 29 `*_upgrade.txt` bodies import
  `from corpus_structure.semantic import alembic_native, alembic_privileges` at module level
  (line 6 of each); seven of them go on to use `alembic_privileges.owned_operation`. The key
  treats a body as an opaque artifact, so this import is never walked. This is DTA-038's
  omission, present in the target tree in every revision.
- **Artifacts are all pinned.** Each of the 29 revisions carries three digest pins, so all 87
  artifacts of the target tree have their content fixed by their revision's source, which the
  key's `chain` component digests. The key nevertheless records each artifact by path, size and
  modification time (root `scripts/native_deployment_key.py:146–148`), so a checkout, rebase or
  sibling worktree with identical content computes a different key.
- **The walk is module-level by design.** `import_closure` skips imports inside functions for
  chain sources (`native_deployment_key.py:41–47, 131–136`) and follows them for the construction
  entry (`:137–142`). The operator chose the module-level closure on 2026-11-13 because the full
  nested closure covers nearly the whole package.

The key's own `import_closure` was run statically (by `ast`, without importing the package) over
both trees at `12f57dc4d`; the
[identity re-baseline](../../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-identity.md) (its section 1) lists the modules.

| Sources walked | Package modules in the closure | Notes |
|---|---|---|
| The frozen tree, which the key hashes today | 25 | Includes `schema/model.py`, `schema/relational.py` and `metadata.py`, which no head build imports through the chain |
| The target tree, revisions only | 21 | No `schema/*`, no `metadata.py`, no `alembic_privileges` |
| The target tree, revisions and executed bodies | 22 | Adds only `semantic/alembic_privileges.py`; `alembic_native` is already reached through the revisions' `native_objects` import |

The construction closure, which follows function bodies from `construct_deployment`, is 15 files
and is the same at both baselines. `host_bootstrap.py` is in neither closure.

### Provisioning and the repeated steps

- `semantic_principals()` reads `host_bootstrap.PRINCIPALS` in process and returns the mapping of
  purpose to role name (`native_test_support.py:396–401`); no shell and no second interpreter
  starts. It is called once for the key (`:896`) and once for readiness (`:929`), and again from
  `tests/native_private_bootstrap.py:55`, `tests/db/test_native_host.py:14, 26` and
  `tests/semantic/test_native_fixtures.py:140` through the re-export at `tests/conftest.py:325`.
  Root `tests/scripts/test_private_cohort.py:600–612` asserts the six purposes against a literal
  mapping with no shell tool on the path.
- The script mode that used to supply the names, `pg_semantic_roles.sh --principals` (root
  `scripts/pg_semantic_roles.sh:9–12`), has no caller left: the `justfile` calls the script
  without arguments, and a search of `justfile`, `ops/` and root `scripts/` finds no other use.
- `src/corpus_structure/core/db/host_bootstrap.py` owns the principal list (`PRINCIPALS`, `:41`)
  and renders the role, template and extension statements that both provisioning scripts apply.
  Nothing the key walks imports it.
- The key records each principal as name and OID only (`SELECT rolname,oid FROM pg_roles`, in
  `PgAdmin.deployment_key`, `native_test_support.py:891–925`).
- `_publish_deployment` (`native_test_support.py:990–1052`) creates the build database from the
  server template, runs `construct_deployment`, reads the policy, seals and renames. By reading,
  it performs no step that shapes the head's content outside `construct_deployment`.
- `tests/native_private_bootstrap.py:30–106` provisions a private server by hand-written role,
  template and extension statements. The conversion routed the two shell scripts through
  `host_bootstrap` and left this module as it was. It acts on the server before any build, so its
  effects reach the key as observed server facts either way. That it restates what
  `host_bootstrap` owns is unfinished conversion work (ADR-0131's native test provisioning) and
  is not this companion's scope.
- `replay_policy` ends by reading the policy back and comparing it (`:645–648`); its caller in
  `PgAdmin.database` reads and compares again (`:755–757`).

### Recipes that carry a location

`current_pdf_recipe(directory, …)` (`tests/semantic/current_pdf_source_support.py:46–124`) calls
production's capture-source composer with `PreparedPdfAssets(directory, …)` and
`directory=directory / "owned"` (`:58–59`). Production's `pdf_capture_custody` writes both, resolved
to absolute paths, into the `pdf-capture/execution-custody` artifact
(`src/corpus_structure/semantic/pdf_capture.py:62–104`, the two paths at `:93` and `:98`), and
reads the workspace back from that artifact at run time (`:453`). The artifact is part of the
recipe's captured inputs, so the recipe value, its `recipe_id`, the release identity and the seed
key all contain the caller's directory.

- There are 23 call sites of the two `current_pdf_recipe` functions outside their definitions, and
  about 13 further helpers that pass a `directory` through to one of them (search of `tests/`).
  Most pass the test's `tmp_path`.
- `_current_pdf_source` builds its recipe from `tmp_path` and calls
  `scenario_seeds.commit_clone(recipe)` (`current_pdf_source_support.py:303`). The registry
  keys a seed by `(recipe, head name)` and keeps every seed until the session closes (root
  `scripts/native_scenario_seeds.py:200–209, 273–274`). Each test therefore builds a seed
  database, seals it, clones it once and leaves the sealed seed registered.
- `_prepared_kernel = cache(_prepare_kernel)` (`tests/semantic/data_operation_kernel_support.py:161`)
  is unbounded. `prepare_kernel` uses it only when no directory is given (`:164–167`). Callers that
  pass a per-test PDF recipe never hit it, and each miss leaves a prepared release, its model, its
  runtime and a temporary directory alive for the worker's life.
- The seed builder prepares into the seed's directory and bypasses the memo
  (`build_kernel`, `:288–292`), because the registry requires a stage's files to lie inside the
  seed directory (`native_scenario_seeds.py:237–245`) and freezes that directory after sealing
  (`:168–175, 268`).

### The PDF source scenario

`_current_pdf_source` (`current_pdf_source_support.py:270–357`) installs a converter double with
the test's `monkeypatch` (`:292`), clones the admitted-release seed (`:303`), initializes a
project, registers one blank original, freezes and registers a discovery demand, deletes the
original's file, runs `execute_data_demand` through the full capture and asserts two receipts
(`:347–356`). Everything it writes is committed and no task remains claimed or running. The
double's reply is now produced by production's shared emitter,
`StreamingPdfResult.certified_reply` (`src/corpus_structure/ingest/pdf_streaming.py:573`), so each
consumer's capture runs production's real certification; the double's *content* is still a
closure over the rows a test passes, and its preparation report is written by hand.

The [PDF source consumer map](../../design_review/evidence/2026-11-17_test-plan-authoring/pdf-source-consumers.md) (its sections 2 and 3) classifies
the scenario's consumers by test function; counts are of functions, by reading:

| Group | Recipe | Consumers | Claim starts |
|---|---|---|---|
| Default fixture `current_pdf_source` | One: default converter, no sections | 12 functions (16 cases) in 7 modules | After the capture |
| `table_source` helper | One: table converter | 4 functions in 2 modules | After |
| `structural_native_journey`, `operation_event_journey`, `primary_source_case` fixtures | One each | 2, 3 and 2 functions | After |
| Module-scoped fixtures (`current_workflow_case`, `actual_e5_native_case`, `current_contextual_case`) | One each | 3, 1 and 8 functions; already one capture per module | After |
| Factory and direct calls with their own rows | About 16 recipes | One function each | After, but nothing to share |
| Capture consumers (`test_pdf_streaming_integration`, `current_integration_journey` with 13 call sites, `companion_source`) | — | — | The capture is the claim |

Two factory consumers call the factory without `with`
(`tests/semantic/test_witnessed_publication_native.py:31`,
`test_condition_publication_native.py:56`), and one default-fixture consumer writes into the
frozen seed directory (`test_source_discovery_native.py:52`). By reading, the first two cannot
work; the third was not re-verified in depth at `12f57dc4d`. All three are unchanged, and TDM-01
repairs them before this companion's packages run.

### Delivered by the conversion

The conversion delivered two things in this companion's area, and each package below carries a
note of what that removes from it.

- Principal names are read in process (commit `781350991`), with a test of that
  (`test_private_cohort.py:600–612`). This was one of TDM-06's three repetitions.
- The controlled converter doubles certify through production (`1d22c41cb`, `8a5c074f0`), and the
  fixture-only occurrence writer is gone. This is part of what TDM-08 needs from TDM-09, and not
  the part TDM-08 depends on.

It delivered nothing else here. `native_deployment_key.py`, `native_deployment_build.py`,
`native_scenario_seeds.py`, the kernel support module, production's capture custody and the two
root test modules of the key and the seed registry are unchanged since the authoring baseline.
The target chain grew from 22 to 29 revisions, which enlarges what the key fails to cover.

## Target design

### One principle for identity and lifetime

The coordinator's contract *preparation lifetime* states the principle: a preparation may be
reused for as long as the implementation that built it is fixed, and its key names exactly the
content that determined it. What changes for each kind of prepared state:

| Preparation | What changes here |
|---|---|
| Head (keyed by what the build runs; reused across sessions and workers) | The key reads the right tree, sees executed bodies and ignores timestamps (TDM-06) |
| Seed (keyed by recipe content and head name; one worker process) | The recipe holds no location; the binding is a function of the seed (TDM-07). A completed capture becomes a seedable stage (TDM-08) |
| Pure preparation, such as a prepared release (one worker process, bounded) | One bounded memo keyed by recipe content and binding together (TDM-07) |
| Per-consumer build (not reused) | Built in the consumer's own clone, never sealed or retained (TDM-07) |

The reasoning for the lifetimes is the review's (§4.2) and is unchanged: only the head's
implementation can be fingerprinted cheaply and exactly, so only the head crosses sessions. The
key remains a hit-rate device. Verification on first use remains the authority on whether a
reused head is safe (ADR-0101), and nothing here weakens it.

### Recipe, binding and the caches that depend on them

Production's capture composer needs two locations, an asset root and a workspace, and writes both
into the release. The test system cannot remove them from the release without a production
change, so it separates them from the *recipe*:

- A **PDF recipe** is a frozen value that says what the scenario contains: the composer options
  (today `math_context` and the integration policy), any extension applied on top (the extra
  declarations and sources that TDM-03's one extension helper takes) and, for a stage that
  includes a capture, the authored content of the controlled converter. It contains no path. Its
  `recipe_id` is computed over this value alone.
- A **binding** is a frozen value holding the asset root and the workspace.
- The **bound kernel recipe** is what the composer returns for a recipe and a binding: today's
  `KernelRecipe` with captured inputs. It is what `prepare_kernel` consumes. It is never a seed
  key.

Two binding classes exist, chosen by what the consumer's claims execute, in the way an isolation
class is chosen by what a claim needs:

- **Per-worker binding.** Both locations lie inside the seed's own directory, which the registry
  allocates per seed (`native_scenario_seeds.py:213`) and freezes after sealing. The binding is a
  pure function of the seed, so keying the seed by the recipe alone is sound. The workspace is
  read-only for every clone.
- **Per-consumer binding.** The locations lie in the consumer's own temporary directory. The
  scenario is built in the consumer's own clone of the head and is never sealed, registered or
  memoized.

The rule that decides the class comes from where production writes (the
[seam advice](../../design_review/evidence/2026-11-17_test-plan-authoring/seams.md), under its question 4 on the capture workspace as a binding; by
reading). A capture claim creates a directory per request under the workspace and writes the
submitted original there; each PDF transform (organized, enriched, integrated) writes into the
same workspace. For a capture that is already complete, production creates that per-request
directory again, which is a no-op when it exists, and then returns the published result from the
database without further filesystem access; no later reader of the workspace was found. So:
**a consumer whose claims execute a capture or any PDF transform uses a per-consumer binding;
every other consumer may use a per-worker binding.** Apply this eligibility rule through the
fixture route before execution. A consumer requesting a new capture or transform through the
sealed route receives a named contract refusal. The frozen filesystem supplies a further custody
guarantee. TDM-08's pilot verifies the route and the reservation lifetime on current source.

Every cache of a product that depends on the binding is keyed by recipe and binding together. The
seed satisfies this because its binding is derived from the seed. The memo satisfies it by its
key. A per-consumer build is not cached at all.

**Alternatives rejected.**

- *One stable per-worker writable directory for every PDF test.* It makes recipes equal, but
  sequential clones would see each other's workspace files, and a repeated request or build
  identity could reach the spool-reuse or recovery branch across tests. The read-only workspace is
  what makes sharing safe.
- *Normalizing the path out of the recipe value while leaving it in the bound release.* Two
  consumers would then share a seed whose release names the first consumer's directory.
- *Keying the memo by recipe content alone.* It would return a release bound to another location.
- *Asking production to drop the directory from custody.* That is a production remedy outside
  this series; it is a row of the coordinator's production context.

**Evidence that would reopen the split.** A reader of the workspace after a completed capture
that the search missed (a post-capture consumer would then fail on a missing or stale file); or a
production decision to bind the workspace at run time, which makes most of this section
unnecessary.

## Pivotal mechanisms

| Mechanism | Use here | Limit that shapes the design | Reference |
|---|---|---|---|
| The key's own `import_closure` (static, by `ast`, never importing the package) | Walks chain sources and, new, executed bodies | A single `nested` flag propagates to every module reached, so "function-level imports of the chain's own files only" needs a per-source distinction the function does not have today | root `scripts/native_deployment_key.py:69–106` |
| `hashlib.file_digest` | Content digest of an artifact no revision pins | Reads the whole file; cost is not measured | Python 3.14 standard library, [`hashlib.file_digest`](https://docs.python.org/3.14/library/hashlib.html#hashlib.file_digest) |
| Production's script-location constant | The chain the key hashes | Importing it imports `alembic` and SQLAlchemy; the head lifecycle already imports the same module for verification (`native_test_support.py:356`) | `src/corpus_structure/semantic/migrations.py:14–27` |
| `functools.lru_cache(maxsize=…)` | The bounded memo | Bounds entries, not bytes; an evicted value lives on while a caller holds it | Python standard library, [`functools.lru_cache`](https://docs.python.org/3.14/library/functools.html#functools.lru_cache) |
| The seed registry's builder contract | The completed-capture stage | The builder runs outside any test and has no `monkeypatch`; the stage must be a frozen dataclass whose files lie in the seed directory; no task may be claimed or running; `validate_clone` runs before the directory is frozen | root `scripts/native_scenario_seeds.py:200–275`; `tests/scenario_recipes.py:9–15` |
| `pytest_configure_node` and `config.workerinput` (pytest-xdist 3.8.0) | Not selected; the candidate for computing the key once per run | The controller never collects; values must be picklable | The [library capability notes](../../design_review/evidence/2026-11-17_test-plan-authoring/library-capabilities.md), section B on pytest-xdist (controller-to-worker data); installed `xdist/workermanage.py` |

## TDM-06 — The head key covers what the build runs

**Prerequisite.** TDM-00 supplies the superseding record for ADR-0101 (RC07) and its re-read of
what changed since `12f57dc4d`. The package needs the record because it changes the key's declared
inputs, and the re-read because validation of the conversion may still add a target revision.

**Delivered by the conversion; remaining scope below.** `semantic_principals()` no longer starts
a process (`781350991`), and a test of that exists (`test_private_cohort.py:600–612`). Nothing
else in this package was delivered: the key still hashes the frozen tree, walks no executed body,
records artifacts by size and modification time, records role name and OID only, and the second
policy comparison stands. The closure over the right tree, which was this package's first step,
has been computed and is in the baseline above.

**First step: confirm the closure at entry.** Repeat the two target-tree computations of the
baseline table (revisions only; revisions and executed bodies) over the chain as it stands at
entry, and record any difference from the 21 and 22 modules found at `12f57dc4d`. The step shows
whether a revision added during validation brings in a module the rules below do not reach.

**Implementation vision.** The key function keeps its shape: a pure function from a repository,
a chain directory, a package directory, a construction entry, a lockfile and observed server facts
to a digest and its components. Five things change.

1. **The chain is the one production runs.** `PgAdmin.deployment_key` obtains the chain directory
   from `corpus_structure.semantic.migrations.ALEMBIC_DIR`, the constant `upgrade()` itself
   defaults to, and no path to a migration tree is written in test infrastructure. If production
   moves or renames the chain again, the key follows without an edit. The frozen tree leaves the
   key entirely, and with it the digesting of 287 files and the stat of 726 that no head depends
   on.
2. **Executed bodies are sources.** For each chain source that assigns `NATIVE_UPGRADE_FILE`, the
   named file joins the closure walk as a source, parsed like a module. Its module-level imports
   are followed at module level, exactly as a revision's are. In the target tree all 29 bodies
   import `alembic_native` and `alembic_privileges`; the first is already in the closure through
   the revisions' `native_objects` import, so the walk adds exactly one module,
   `semantic/alembic_privileges.py`, and the closure grows from 21 to 22.
3. **A chain file's own function-level imports count.** A revision's `upgrade()` is the program
   the chain executes, so an import inside it is executed on every build. The walk visits function
   bodies of the chain's own files and of executed bodies, and stays module-level for every package
   module reached from them. The operator's 2026-11-13 decision stands for package modules: imports
   inside package functions (for example `native_objects` importing `native_sql_body` inside a
   function) remain outside the key and are bounded by verification. At `12f57dc4d` the only such
   import in the chain is `alembic_privileges` inside each revision's `upgrade()`
   (`semantic_ddo_current_root.py:41`), which the bodies already bring in, so this item adds no
   module today; it closes the gap for a revision that imports inside `upgrade()` without
   executing a body.
4. **Artifacts enter by content, never by timestamp.** An artifact whose file name and SHA-256 a
   chain source pins as a pair of module-level constants contributes nothing of its own: its
   content is fixed by the revision's source digest, and the revision refuses to run on a mismatch.
   An artifact no source pins contributes its path and content digest. Size and modification time
   leave the key. In the target tree all 87 artifacts are pinned, so the artifact component is
   empty at `12f57dc4d` and the 29 bodies (about 94 MB together) are the only large files the key
   reads.
5. **Provisioning is covered by two rules instead of a source digest.** Anything executed during
   the build is reached from `construct_deployment`, whose closure the key already follows through
   function bodies; PgAdmin runs no head-shaping step outside it. Anything applied to the server
   before the build enters the key as an observed fact of the server. The role facts widen from
   name and OID to a structured observation of the role policy provisioning governs: login,
   inheritance, superuser, database creation, role creation, replication and RLS bypass, plus
   effective membership identities and the relevant SET, INHERIT and admin options. Reuse the
   catalog model and provisioning contract to select these facts and the clone-equivalence
   comparison to verify them. Keep one semantic owner for this policy. The source of
   `host_bootstrap.py` does not enter the key: it is not executed by a build, and a change to it
   has no effect on any server until the operator provisions again, at which point the observed
   facts change. The same holds for the private-server provisioning in
   `tests/native_private_bootstrap.py`: it acts before any build, and what it creates is observed.

Of the repetitions DTA-039 names as pure, the conversion removed the process start behind the
principal names. Two pieces remain:

- **The dead script mode is removed.** `pg_semantic_roles.sh --principals` has no caller at
  `12f57dc4d` and exists only because the test infrastructure once called it. The mode and its
  mention in the script's usage line are deleted as test-only machinery whose consumer is gone.
- **One policy comparison per clone.** The comparison inside `replay_policy` is the owner's own
  postcondition and stays. The caller's second read and comparison at `:755–757` goes.

**Decisions this package owns.** How the per-source distinction of item 3 is expressed in
`import_closure`, how the existing catalog model supplies the stated role policy, and whether the
pinned-artifact rule reads the constant pairs by name pattern or by an explicit convention check. One condition would change
item 5: if a later change makes PgAdmin apply a head-shaping step outside `construct_deployment`
(for example grants applied after construction), that step moves into `construct_deployment` so
the keyed closure reaches it. None exists at `12f57dc4d`.

**Failure behaviour.** A chain source that names an upgrade body which does not exist fails the
key computation with the missing path, as a missing module file would. A body that does not parse
fails the same way; the build would fail on it too. An unpinned artifact is digested, never
skipped. Verification on first use, replacement of a failed head and the gap record are unchanged.

**Why not the alternatives.**

- *Digest every artifact, pinned or not.* It relies on no convention, but it reads about a
  third of a gigabyte in every worker process to re-establish what each revision's source digest
  already fixes. Rejected for the pinned files; it is the rule for unpinned ones.
- *Keep size and timestamp for artifacts.* This is the defect: identical content in another
  checkout rebuilds the head. The review allows it as a fallback only if hashing unpinned
  artifacts proves expensive, and the target tree has none.
- *Follow function-level imports through the whole package.* Covers nearly every module; the head
  would rebuild on almost every edit. Rejected by the operator on 2026-11-13 and again by the
  review.
- *Add the provisioning module's source digest to the key.* It would rebuild heads on an edit that
  changed no server, and would miss nothing the observed facts catch.
- *Keep a literal path and correct it to `target_alembic`.* It repairs today's defect and leaves
  the cause, a second statement of a fact production owns.

**Consumers migrated (complete scope).** The one production-facing caller,
`PgAdmin.deployment_key` (`native_test_support.py:891–925`); the two callers of `replay_policy` in
`PgAdmin.database`; and the key's tests in root `tests/scripts/test_native_deployment_key.py`
(eight tests, unchanged since the authoring baseline), two of which pin the behaviour this
package changes and are rewritten with it:

- `test_real_chain_closure_contains_known_direct_machinery` (`:137–159`) passes the frozen tree
  as the chain (`:141`) and expects `metadata.py` and `relational.py` among the module imports
  (`:153`, `:155`). Neither is in the target tree's closure. The test takes the chain from
  production's constant, and its hand-written expected names become ones the target closure
  holds, with `alembic_privileges.py` among them.
- `test_chain_function_body_import_stays_outside_module_level_closure` (`:88–96`) asserts that an
  import inside a revision's `upgrade()` stays outside the key. Item 3 reverses that for the
  chain's own files; the test is replaced by the two-sided case under acceptance below.

The callers of `semantic_principals` need no edit. Reusable heads published under old keys become
unreachable and are removed by the existing retention of the newest three.

**Superseded machinery removed.** The literal chain path; the artifact size and timestamp
component; the second policy comparison; the `--principals` script mode.

**Acceptance evidence.** Each expectation is authored by the test, not computed by the key.

- *The key follows production's chain.* With `migrations.ALEMBIC_DIR` pointed at a small
  hand-built chain in a temporary tree, the components list that tree's files and none of the
  repository's. This fails if a literal path survives.
- *Real-tree membership.* For the repository, `module_imports` contains
  `semantic/alembic_privileges.py`, named by hand, and contains neither `metadata.py` nor
  `schema/relational.py`; no component path lies under `semantic_alembic/`; at least one lies
  under the chain production names. The first name fails if bodies are not walked (it is the one
  module only the bodies reach); the absent names and paths fail if the wrong tree is hashed.
- *Executed body, temporary tree.* A revision that executes a body which imports a package module
  `m` at module level, where the revision itself does not import `m`: the closure contains `m`.
  Editing `m` changes the key. Without item 2 this case fails.
- *Function-level import of a chain file.* A revision that imports `n` only inside `upgrade()` and
  executes no body: editing `n` changes the key. A package module that imports `p` only inside a
  function: editing `p` does not change the key. The second half pins the operator's boundary so a
  later widening is deliberate.
- *Content, not time.* Changing only the modification time of every chain file and artifact leaves
  the key equal. Changing one byte of an unpinned artifact changes it. Changing one byte of a
  pinned artifact without its pin leaves the key equal. Exercise the loader refusal for that
  altered artifact so the verified declaration remains sufficient. Preserve frozen installed-clone
  equivalence and failed-key replacement as the reuse authority.
- *Role policy is part of identity.* With the same principal name and OID, alter each selected
  capability or relevant membership option in the typed observation and expect a different key.
  Include BYPASSRLS drift with login and membership identities held fixed. Exercise actual replay
  and frozen-clone equivalence on an owned clone. Keep ordinary host roles intact.
- *The script mode is gone.* `pg_semantic_roles.sh --principals` exits with the usage error. The
  case that principals need no process already exists (`test_private_cohort.py:600–612`) and is
  not written again.
- *One comparison.* A counting wrapper on `PgAdmin.policy` records one read after replay for a
  clone, where the baseline records two.

These cases are the start of the key's perturbation table. TDM-13 owns the table, adds the
remaining determinants (lockfile, interpreter, each server fact including a role attribute, the
construction closure) and its completeness case. The pure cases sit beside the key's tests under
root `tests/scripts/`; the one case that reads a built head's version table sits in
`tests/test_db_fixtures.py`, which already builds and reuses a head. No case expects the key to
move when `host_bootstrap.py` is edited: by item 5 it must not. Targeted verification for this package is
the key's test module and the fixture tests that build and reuse a head
(`uv run ci test -- tests/scripts/test_native_deployment_key.py` from the root tree, and
`tests/test_db_fixtures.py`, `tests/semantic/test_native_fixtures.py`).

**What validation of the conversion may still move.** A further target revision changes none of
the five items; the first step records it. If production moves the chain again, item 1 absorbs
it without an edit.

## TDM-07 — Recipe and binding split, one bounded memo

**Prerequisite.** TDM-00 supplies the superseding record for ADR-0102 (RC08), which is what
permits a scenario to be built without sealing and requires a recipe to carry no location.
TDM-03 supplies the single composer.

**Delivered by the conversion.** Nothing. Production's capture custody still writes both resolved
paths into the release (`pdf_capture.py:62–104`, unchanged), both composers still take a
directory, the 23 call lines and the kernel memo are as they were, and the seed registry is
unchanged. The whole package remains.

**Shared editing surface with TDM-03.** TDM-03, which this package needs, reduces the two
`current_pdf_recipe` functions to one composer that still takes a `directory`, and the fifteen
extension sequences to one helper that carries no location. This package changes that composer to
take the recipe content and a binding as separate arguments and to return the bound kernel
recipe, and edits its callers once.

**Implementation vision.** A test or fixture describes a PDF scenario by a recipe value and
states which binding class its claims need. It obtains the scenario from the registry in one of
two ways, and receives the same kind of object from both: the stage, a maintenance engine, purpose
engines on request, and an origin for receipts.

- *Seeded.* The existing `commit_clone(recipe)` and `rollback_family(recipe)`. The registered
  builder for the PDF recipe type derives the binding from the directory the registry hands it,
  composes the bound kernel recipe, prepares into that directory and admits. The seed is sealed,
  its directory frozen, and every consumer gets a fresh clone.
- *Built for one consumer.* A new registry operation takes the recipe and the consumer's
  directory, clones the head for this consumer alone, runs the same registered builder on that
  clone with a binding in the consumer's directory, checks the stage as it would a seed's, and
  yields. It does not seal the database, does not freeze the directory, does not add an entry to
  the registry and drops the database when the consumer finishes. Its origin says the scenario was
  built for this consumer, so a receipt never shows a seed that did not exist.

The builder is one function for both routes, so a scenario cannot differ by route except in where
it executes. The existing `KernelRecipe` seed builder refuses a bound PDF recipe, recognised by
its capture-custody artifact, with a message that names the two routes; this is the mechanism's
own contract, like its refusal of a recipe that is not a frozen value, and it is what makes
"a located recipe is never sealed" true rather than conventional.

The memo becomes one function with one rule. `prepare_kernel` for a recipe without a location
keeps its key, the recipe. For a PDF recipe the key is the recipe and the binding. The memo is
bounded by entry count and allocates each entry's directory under the worker's pytest temporary
root, so pytest's existing retention removes directories after an interrupted run and eviction
never deletes a directory a caller may still hold. A call for a per-consumer binding bypasses the
memo. Pure-preparation tests that only prepare a PDF release and execute nothing ask for the
memo's own per-worker binding and therefore share an entry across tests. A cached entry is
reusable only while its binding and associated resources remain valid. Binding teardown retires
its cached preparation, and a later binding cannot retrieve that object. Eviction releases the
memo's reference without deleting resources still owned by a live caller.

Seed builds keep preparing into the seed's own directory and do not draw from the memo. The review
described one memo "shared by seed builds and direct callers" (§4.2). Reading the registry refines
that: a stage's files must lie inside the seed directory and are frozen there for the seed's life,
while a bounded memo must be free to evict. A seed is already the retained holder of its own
preparation. The cost is that a recipe used both by a seed and by a direct caller in one worker is
prepared twice, which is pure computation and is accepted; stored results showing preparation
dominating setup for such a recipe would reopen it.

**Decisions this package owns.** The names and exact fields of the recipe and binding values; the
name of the per-consumer registry operation; the memo's size, chosen so that the recipes of one
module stay warm; whether the origin of a per-consumer build is a new receipt field or a value of
the existing one.

**Consumers migrated (complete scope).** Every construction of a PDF-derived recipe from a
directory: the 23 call sites of `current_pdf_recipe` and the roughly 13 helpers that pass a
directory through, across `tests/semantic/` and `tests/evaluate/`. The package's first step lists
them from a search at entry and assigns each a class by reading what its claims execute.
Representative assignments from the
[PDF source consumer map](../../design_review/evidence/2026-11-17_test-plan-authoring/pdf-source-consumers.md), which are examples and not the
boundary of the scope:

| Site | Class | Reason |
|---|---|---|
| `_current_pdf_source` and its two fixtures (`current_pdf_source_support.py:270–383`) | Per-consumer until TDM-08 | It runs a capture in each clone |
| `OriginalSeedRecipe(current_pdf_recipe(tmp_path))` in `test_pdf_materialization_native.py:80`, `test_pdf_transform_demand_native.py:175`, `current_pdf_integration_support.py:247` | Per-consumer | Capture or transforms execute |
| `current_integration_journey` (`current_pdf_integration_support.py:229`) and `current_record_policy_journey` (`tests/evaluate/declared_record_native_support.py`) | Per-consumer | Capture is part of the journey |
| `prepare_kernel(current_pdf_recipe(tmp_path))` in `test_pdf_transform_operations.py:278–280, 335`, `test_pdf_resource_custody.py:100`, `test_current_pdf_source_inputs.py:13` | Memo, per-worker binding | Preparation only; nothing executes |
| Target recipes admitted into an existing clone through `admit_current_target` (`current_pdf_source_support.py:458–470`; about twelve support modules) | Per-consumer, prepared into the consumer's directory as today | They are admitted into one test's clone and are not seeds |

**Preserved.** `admit_kernel` as the one test-side owner of the persist, admit and bind order
(TDM-03); real producers and real purpose engines in every build; policy replay and
comparison per clone; the registry's refusals; `recipe_id` computed with canonical JSON and
`hashlib`, not with production identity functions, so test infrastructure keeps working while
the code under test is broken; every non-PDF recipe and its consumers, which already carry no
location.

**Deliberate changes.** A PDF scenario whose claims capture no longer produces a sealed seed or a
second clone: one database per test instead of two, and nothing retained after the test. A PDF
release's identity is equal for all consumers of one seed in a worker where it used to differ per
test; no test was found that depends on it differing.

**Superseded machinery removed.** `cache(_prepare_kernel)` and the `directory is None` switch in
`prepare_kernel`; the `directory` parameter of both `current_pdf_recipe` functions as the way to
state identity; the per-test sealed seeds.

**Acceptance evidence.**

- *The recipe holds no location.* Compose the same recipe with two bindings whose directories
  contain two different marker strings chosen by the test. The two `recipe_id` values are equal,
  and the recipe's canonical JSON contains neither marker. The custody artifact of each bound
  kernel recipe contains its own marker and not the other's. A recipe that still embeds a path
  fails the first half; a composer that ignores the binding fails the second.
- *A per-consumer build leaves nothing.* Around one per-consumer consumer, the server's list of
  seed databases is the same before and after, and the consumer's database is absent after
  teardown. The baseline behaviour, one new sealed seed, fails this.
- *A located recipe cannot be sealed.* Passing a bound kernel recipe with a custody artifact to
  `commit_clone` is refused with the message that names the routes, after a positive control that
  seeds the corresponding location-free recipe.
- *Seeded consumers share.* Two consumers of one PDF recipe in one worker receive clones whose
  origin names the same seed database and whose own databases differ.
- *The memo is binding-aware and bounded.* The same recipe and binding twice returns the identical
  object. The same recipe with a second binding returns a different object whose custody names the
  second directory. With a memo of size two, a third recipe evicts the first, shown by a fresh
  object on the next request. A per-consumer call returns a fresh object every time. Teardown
  of a binding prevents later retrieval of its memo entry, while a live caller retains its
  resource ownership after eviction.

Targeted verification: the seed registry tests (`tests/semantic/test_scenario_seeds.py` and root
`tests/scripts/test_native_scenario_seeds.py`, whose cases for the per-consumer route and the
refusal of a located recipe are added or adjusted here), the kernel support tests, and one
consumer module from each row of the table above.

**If production later moves the workspace out of release custody.** The conversion did not do
this. If production makes that change (the first row of the coordinator's production context), each
execution can receive its own workspace, so the per-consumer binding class and the read-only
constraint on post-capture consumers are no longer needed; PDF recipes are location-free by
construction and seedable for every consumer; the memo's key returns to the recipe alone; the
completed-capture seed need not keep workspace files; and the test-side change is confined to the
composer and the builder. The acceptance case "the recipe holds no location" continues to hold,
and its second half, about the custody artifact, is deleted with the binding.

## TDM-08 — A seed stage for the completed capture

**Prerequisites.** TDM-07 supplies the location-free PDF recipe, the per-worker binding and the
rule that decides a consumer's class. TDM-09 supplies a controlled converter with three
properties this package cannot do without: it can be installed for the duration of a call outside
any test, because a seed builder has no `monkeypatch`; its authored content (the kind of
document, the section rows, the formula outcomes) is a frozen data value, because that content
determines the state the stage holds and must therefore be recipe content, and a callable cannot
be part of a recipe; and its preparation report is a valid report produced by production, because
the stage is sealed and every clone inherits it. TDM-01 has repaired the two consumers that call
the factory without `with` and the one that writes into a frozen seed directory.

**Delivered by the conversion; the prerequisite from TDM-09 is still open.** The controlled
converter now routes through production's shared emitter: every double returns
`StreamingPdfResult.certified_reply(request, on_replay=…)`
(`src/corpus_structure/ingest/pdf_streaming.py:573`; commits `1d22c41cb` and `8a5c074f0`), either
directly or through `certify_controlled_pdf_stream` (`tests/pdf_acceptance_support.py:34–71`), and
the fixture-only occurrence writer has no caller left. That removes the earlier obstacle that a
double's reply was uncertified. It supplies none of the three properties above. The content is
still a closure: `_controlled_stream` and `_section_stream`
(`current_pdf_source_support.py:212`, `:388`) and the per-module doubles capture their rows in a
function. Installation is still `monkeypatch.setattr(PdfWorker, "stream", …)` with a pytest
fixture (`current_pdf_source_support.py:292` and five further sites), and `_current_pdf_source`
takes that fixture as a parameter, so a seed builder cannot enter it. The preparation report is
still written by hand as the reply's effective options (`b'{"fixture":"controlled-source-search"}'`
and similar, or `b"{}"`), which is not a report production would accept on recovery. Nothing of
the seed stage itself was delivered, and the whole package remains. The certified path makes the
stage more useful than it was at authoring, because each per-consumer capture now runs
production's full certification.

**Implementation vision.** A completed-capture recipe wraps a PDF recipe and adds what the
capture needs as data: the converter content, the selected sections and the demand's target. Its
registered builder runs in the seed's own database and directory. It builds the admitted-release
stage through TDM-07's builder with the per-worker binding, installs the controlled converter for
the span of the build, and then performs the steps `_current_pdf_source` performs today for every
consumer: initialize the project, register the blank original, freeze and register the discovery
demand, remove the original's file, execute the demand through capture and discovery, and require
the two receipts. It returns a frozen stage holding the kernel stage, the demand identity, the
document key, the original's bytes and the sections. Its seed files are the files under the seed
directory, which now include the capture workspace. Its `validate_clone` checks that the selected
publication of the capture exists in the clone and that the demand is complete.

The registry seals the database and freezes the directory as for any seed. A consumer whose claim
starts after the capture asks for a commit clone of this recipe and receives today's
`CurrentPdfSource` shape. It installs no converter. The fixture installs instead a stream that
fails the test with a message saying a post-capture consumer reached the converter, so a
misclassified consumer fails by name rather than by starting a real conversion.

**Consumer eligibility and pilot.** Before expanding reuse, classify consumers by their required
operations and execute one post-capture reader plus one consumer that registers another original
or executes a new capture/transform demand. The reader uses the sealed completed-capture clone.
The writable consumer uses its own binding and directory through TDM-07. Assert the fixture
route's named refusal before a post-capture consumer attempts out-of-contract work. Keep the
published capture's filesystem reservation live while authenticated clones can read it. The
production custody model owns absolute paths. A pilot that reveals a required production
correction routes the concrete issue through the coordinator before dependent migration.
The prior source inspection is useful context, while these two journeys establish eligibility
and lifetime at the current entry source. See
[I03](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I03).

Read-only state of the workspace is the registry's guarantee, not the stage's check: the registry
calls `validate_clone` before it freezes the directory (`native_scenario_seeds.py:246, 268`),
so a stage that asserted read-only files would refuse its own seed.

**Consumers moved (complete scope).** The groups whose consumers share a recipe and whose
fixtures are function-scoped, subject to the classification below:

- the default fixture `current_pdf_source`: 12 functions in 7 modules
  (`tests/semantic/test_current_source_graph_native.py`, `test_source_discovery_native.py`,
  `test_companion_export_native.py`, `test_source_search.py`, `test_native_render_journey.py`,
  `test_pdf_observation_catalog.py`, `test_native_exports.py`);
- `table_source` in `tests/semantic/current_pm2_native_support.py`: 4 functions;
- `structural_native_journey`, `operation_event_journey` and `primary_source_case`: 2, 3 and 2
  functions.

These are 23 functions, and the counts were confirmed by a syntax-tree count at `12f57dc4d`. The
first step reads each of them and confirms that its claims execute neither a capture nor a
transform. Three need particular care: `test_source_discovery_native` registers a
second original and runs a discovery demand, and the render and visual-observation consumers
register new demands that execute. Any that does capture stays on TDM-07's per-consumer route and
is named in the package's evidence.

Not moved, by decision: the roughly sixteen recipes with one consumer each, because a seed with
one consumer adds a sealed database and a clone and shares nothing, which is the case RC08 exists
to stop; the capture consumers, whose claim is the capture; and the three module-scoped fixtures,
which already capture once per module and may adopt the stage when next edited without being
required to.

**Superseded machinery removed.** The per-consumer capture inside `_current_pdf_source` for the
moved groups, and the helper's `stream` and `sections` parameters once no moved consumer passes
them. The helper remains, on the per-consumer route, for the singleton and capture consumers.

**Acceptance evidence.**

- *One capture per recipe per worker.* A counting wrapper on `execute_data_demand`, installed
  around two consumers of the default recipe in one worker, records one capture execution for the
  seed build and none for either consumer's setup. At the baseline it records two.
- *The stage holds what the capture produced.* A post-capture consumer reads the source catalog of
  its clone and finds the one document whose key the test computes itself from the project name,
  the source name and the SHA-256 of the blank original's bytes, with the standard library.
- *Misclassification fails closed.* One control registers a second original in a clone of the
  stage and requests a capture demand. The fixture's explicit contract refuses the operation
  with its named reason before filesystem writes or converter entry, and no second receipt is
  committed. An accidental filesystem `PermissionError` does not establish this claim.
- *The writable route remains independent.* The pilot that registers another original or executes
  a new capture/transform demand receives a fresh binding. Its rows and files are absent from
  another consumer's clone, with literal expected counts. Two eligible reader clones share the
  published capture and trigger no converter calls.
- *The converter content is identity.* Two completed-capture recipes that differ in one section
  row have different `recipe_id` values and yield stages whose discovered members differ in the
  authored text.

Targeted verification: the seven default-fixture modules and the four fixture or helper groups,
run by path, plus the seed registry tests.

**Deferred extension (operator, 2026-11-17).** The declared-record journey
(`current_record_policy_journey`, `tests/evaluate/declared_record_native_support.py`) runs a
four-document capture behind its own controlled converter double (installed at `:354`, certified
through the shared emitter like the others), and its `rich_publication` fixture has 13 consuming
functions on one recipe. It is a sibling builder outside F06 as the review states it. Trigger, as
the coordinator records it: TDM-08 is delivered and its stage holds; the extension then follows
the same rules, and it needs TDM-09's data-described content for that support module's converter
and TDM-07's location-free recipe.

The sibling capture stage is implemented. It serializes capture of the four controlled originals
because they share stream parts. The
[coordinator](../test-domain-model-and-execution_2026-11-17.md#implementation-evidence) records
the subsequent rich-admission readiness block and the consumer's open acceptance.

## What the superseding records must say

TDM-00 writes the records. For this companion's packages to be sound they must state the
following.

**The successor to ADR-0101, for RC07.** The key's chain is the script location production's
upgrade runs, obtained from production's constant. Sources of the key are the chain's files and
the upgrade bodies they execute; function-level imports count for those files and bodies only, and
the closure of package modules stays module-level. Artifacts enter by content: through their
revision's pinned digest where one exists, by content digest otherwise, never by size or
modification time. Steps executed during a build are reached from the construction entry;
provisioning applied to the server beforehand enters as observed server facts. Verification on
first use remains the authority. The same record carries RC10, which the
[declarations companion](declarations-retirement-and-execution.md) specifies.

**The successor to ADR-0102, for RC08.** A recipe is content only. A location is a binding the
builder receives. A seed's binding is derived from the seed's own directory. A consumer whose
claims write to a bound location is built in its own clone and is never sealed or retained.
Caches of anything that depends on a binding are keyed by recipe and binding.

**RC11 (accepted 2026-11-17), in the same successor.** ADR-0102 says "Nothing built under an
implementation override is seedable." The completed-capture stage is built behind a controlled
converter, which replaces `PdfWorker.stream`. The successor states RC11 in the coordinator's
words: a seed may be built behind a controlled boundary double when the double's content is part
of the recipe, and so of the seed's identity, and production's own protocol and checks still run;
seeds built under any other implementation override stay forbidden. Production's protocol and
checks already run behind the double, through the shared emitter; TDM-08 meets the remaining
condition, content as recipe data, through TDM-09, and its stage's origin records the double.
ADR-0102 also says recipes are requested through fixtures; the stage keeps that.

## Deferred and candidate items

The coordinator's [list](../test-domain-model-and-execution_2026-11-17.md#candidates-and-deferrals) owns these items and their triggers;
two notes belong to this design. The incremental head (DTA-039) is valid only when every key
component other than the appended revisions is unchanged, and TDM-06 makes that precondition
checkable, because the key's components then separate the chain's sources from everything else.
The key computed once on the xdist controller is not selected because it is unmeasured and adds a
second path by which a worker obtains a key. Precision cases of the key's table, beyond the
timestamp case, belong to TDM-13.

## Open questions

| Question | Evidence that settles it | Work it constrains |
|---|---|---|
| Does the selected build closure miss an import executed by a revision? | Inspect module-level and executed function-level imports at entry; use any `deployment_key_gap` receipt to identify a source outside the closure | The sources rule of TDM-06 |
| Does a post-capture consumer that registers a new demand over the seeded capture claim the capture again? | Pilot the post-capture and writable routes. A new capture or transform request on the sealed route must reach its explicit refusal | Which consumers TDM-08 moves |
| Does any default-fixture consumer depend on page or candidate custody, which the controlled converter has never supplied? | Reading the 12 functions in TDM-08's first step | TDM-08's scope |
| Do render and visual-observation demands write into the capture workspace? | Reading the two operations' effect code; the fail-closed control | Three consumers of TDM-08 |
| Is the pinned-artifact convention (a file-name constant paired with a SHA-256 constant, read through a checking function) held by every chain source at entry? | A search at TDM-06's entry; all 29 held at `12f57dc4d` | Whether any artifact needs a content digest |

## State

The prepared head, bound memo, and sealed/direct PDF routes are implemented.
The coordinator owns [capture and qualification evidence](../test-domain-model-and-execution_2026-11-17.md#implementation-evidence).
