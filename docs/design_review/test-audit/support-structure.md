# Support structure, composition and domain authority

Findings about where test support lives, what it restates and how tests couple to production
artifacts and to each other. FP-01, FP-03, FP-04, FP-06, DP-01, DP-06, DP-17, DP-24, A1/A2/A3,
and [companion](../design_principles/core/test-assessment.md) §2 and §5. Baseline, scope and
method are in the [README](README.md). Paths are relative to `python/corpus-structure/` unless
they start at the repository root.

Several strengths bound the findings below:
- The semantic database fixture is one small, explicit fixture with real restricted principals.
- Hostile tests build a valid batch through production and then tamper with it, so the negative
  input reaches the native boundary.
- `tests/semantic/test_migrations.py` checks the migrated catalog against the declared physical
  metadata, and no test pins migration revision ids, so adding a migration (SC1) is cheap for
  schema conformance.
- The CLI hooks that journeys patch are documented (`src/corpus_structure/cli/orchestrate.py`).
- `tests/semantic/test_arrow_publication.py` says explicitly that its small registry avoids "application
  preparation or semantic result oracle". That independence is deliberate, and
  [DTA-008](#dta-008) concerns how such copies are maintained, not whether they should exist.

<a id="dta-005"></a>

## DTA-005 — Each native journey assembles its own release; no shared or product composition is exercised

**Principles:** FP-04, FP-03, DP-06, DP-01 by analogy, A2/A3; companion §2, §1.
**Subject:** implemented (18 modules under `tests/semantic` that read
`src/corpus_structure/model/semantic/core.yaml` by repository path, plus
`tests/semantic/test_statistics_model.py` and `test_statistics_cut.py`).

**Diagnosis.**
- No production code loads `model/semantic/core.yaml` or `domains/statistics/semantic.yaml` to
  compose a release.
- Production loaders exist only for the agent, observations, metrics, physical, analytics and
  contracts models (`src/corpus_structure/semantic/*.py`).
- Every test that needs a release therefore writes its own recipe:
  - read `core.yaml` by path;
  - choose the bundle root and import name;
  - layer `proposal_inputs` / `observation_inputs`, or `prepare_source_inputs` /
    `analytical_inputs`, and `domain_rule_inputs`;
  - then call `prepare_release` and `persist_release`.

The recipes already differ:

| Choice | One variant | Another variant |
|---|---|---|
| Core import name | `semantic_core` (`test_domain_operations.py`, `test_statistics_cut.py`) | `core` (`test_semantic_mcp.py`) |
| Metric dependencies | `prepare_source_inputs`, which adds them (`test_source_routing.py:36-43`) | bare `observation_inputs`, which does not |
| Rules | core and domain rules (`test_statistics_cut.py`) | domain rules only (`test_domain_operations.py`) |
| Analytics layer | present | absent |

Even the "actual CLI" journey passes in a release that the test built out of band
(`test_source_routing.py:36-43`, then `--semantic-release`).

**Consequence.**
- Tier-1 evidence describes releases the tests assembled, not one product composition. A mismatch
  with whatever composition the consumer migration and regeneration packages introduce is not
  detected.
- Adding a second pack or a dynamic class (SC5), or changing the layering order, means editing
  about 15–20 modules.
- Under SC2, release ids differ by recipe, which obstructs reproducing a failure across tests.

**Footprint.**
- *Known:* the 18 modules found by searching `tests/semantic` for the `core.yaml` path, plus the
  statistics modules.
- *Inferred:* each new consumer test will add another recipe rather than consume one.

**Counterevidence.**
- The layer helpers themselves are single owners (`observations.py`, `proposals.py`,
  `analytical_profile.py`).
- Some variations may be deliberate minimal releases; nothing marks which ones.

**Uncertainty.** Whether a production composer is planned. No plan text naming one was found
(search of the pivot documents for core.yaml, semantic.yaml and pack composition).

**Leads (optional).** One owned composition entry point, with test builders that parameterize only
what each case needs.

**Bears on:** SP-08 consumer migration; SP-09 clean regeneration ("actual source workflows for
statistics"); the phase-0 rescoping of domain packs.

<a id="dta-008"></a>

## DTA-008 — Hand-written stand-ins for production-written release, catalog and descriptor artifacts are not tied to what production writes

**Principles:** FP-04, DP-01, DP-24, FP-02; companion §1, §5.
**Subject:** implemented (`tests/semantic/test_operations.py`, `test_publication.py`,
`test_arrow_publication.py`, `test_inference.py`, `test_execution_native.py`;
`src/corpus_structure/semantic/publication.py:396-402`; `src/corpus_structure/semantic/sql/validation.sql:46-56`).

**Diagnosis.** Several tier-1 tests write rows by hand that production writes through
`persist_release` and the publication catalog. Nothing ties their shape to the writer.

- **Stand-in release rows.** The `sem.release` rows have `content_digest="test"`,
  `prepared_bytes=b"{}"` and `manifest_bytes=b"{}"`. They appear in `test_operations.py` (`setup`),
  `test_publication.py`, `test_arrow_publication.py` and `test_inference.py`.
  - `test_operations.setup()` writes such a row by default but returns the real in-memory
    `PreparedRelease`.
  - Its consumers therefore run operations against a database release that cannot be loaded and
    whose content disagrees with the object they hold. Only `archive=True` or `observations=True`
    persists a real one.
- **Hand-written catalog rows.** These are `class_definition`, `property_definition`,
  `property_applicability.constraints` and `identity_slot` rows, written by hand in
  `test_publication.py` and `test_arrow_publication.py` (a second copy of the same registry) and in
  `test_inference.py`, which also hand-writes `inference_rule` bodies.
  - Their `constraints` JSON (`{"name", "inlined", "case_policy"}`) omits `native_range`, which
    `publication.native_constraints` always writes (`publication.py:399`).
  - So publication SQL takes its `COALESCE(constraints->>'native_range', range_name)` fallback
    (`validation.sql:46,48,56`), a branch that production catalogs never take.
  - Hand-written `conditional_rule`/`conditional_atom` rows appear in `test_execution_native.py:36-43`.
- **Hand-built method descriptors.**
  - About 30 `record_method` calls in `tests/semantic` pass hand-built `SimpleNamespace`
    descriptors, mostly without `unit_type` or `Config`.
  - `record_method(method: Any)` tolerates the missing fields, so most operations tests exercise
    the NULL-tolerant branch rather than the typed descriptor's binding.

**Consequence.**
- A migration that adds a required column or check to `sem.release` or the catalog tables (SC1)
  forces edits in at least six modules.
- A compiler change to constraint keys (SC2) leaves these publication and inference tests passing
  on an obsolete catalog shape. Only the roughly 19 modules that go through `persist_release` would
  expose a writer/kernel mismatch, and only for the keys they exercise.
- A guard that begins loading or validating the persisted release (SC3) would fail every
  default-`setup()` consumer with failures unrelated to that guard. Meanwhile the stand-ins cannot
  challenge release integrity at all.

**Footprint.**
- *Known:* the sites cited.
- *Suspected:* other consequential constraint keys that are exercised only through hand-written
  catalogs. A key-by-key comparison of the SQL readers with the seeds would settle this.

**Counterevidence.**
- Isolating native publication from the compiler is a legitimate independence choice (companion §1).
- Most `setup()` consumers need only foreign-key plumbing for the release id.
- The NULL tolerance in `record_method` was introduced for unresolved legacy method metadata, not
  only for these test descriptors.
- Unit-type and configuration binding is covered where `test_execution_native.py` supplies both
  fields.

**Related.** [DTA-009](#dta-009) (the helpers that host the stand-ins).

**Bears on:** physical-catalog evolution; SP-10 release/archive integrity; later protected writers.

<a id="dta-009"></a>

## DTA-009 — Shared scenario builders live inside test modules, and their flags and defaults shape other modules' claims

**Principles:** FP-06, FP-01, FP-03, DP-17; companion §2 (case-defining inputs visible at the
call site), §3.
**Subject:** implemented (`tests/semantic`).

**Diagnosis.** `tests/semantic` has no support module. Builders written for one test module are
imported by others. At reconciliation, nine modules import from other test modules:

| Helper | Defined in | Imported by |
|---|---|---|
| `setup` | `test_operations.py` | `test_execution_native` (several local imports), `test_native_source_selection`, `test_native_agent_hold`, `test_packet_input_snapshot` |
| `fixture` (about 370 lines, 18 keyword flags) | `test_domain_operations.py:50` | `test_evaluation_boundaries`, `test_occurrence_context`, `test_source_routing` |
| `Z`, `candidate`, `seed` | `test_query.py` | `test_alternative_groups` |
| `C`, `R`, `Z`, `batch`, `seed` | `test_publication.py` | `test_execution_native` |
| `source_task`, `lease_and_read` | `test_agent_resubmission.py` | `test_composed_journey` |

Their hidden defaults and coupled flags decide what downstream tests check:
- **`setup()`'s default stand-in release** ([DTA-008](#dta-008)).
- **`fixture(two_reports=True)`** also makes `Person` globally scoped and case-preserving
  (`test_domain_operations.py:88-89`) and adds bindings. A test that asks for "two reports" silently
  gets global identity scope as well.
- **`test_occurrence_context.py:45`** replaces the late-bound `locate_proposal` name inside the other
  module's namespace (`monkeypatch.setattr(fixture.__module__ + ".locate_proposal", …)`), so its
  scenario depends on how that helper resolves names internally.
- **Magic expected values fixed by hidden structure.** For example, `test_source_routing.py:166`
  asserts `total == 7`, a number set by the patched PHASE0 stage graph and visible nowhere at the
  call site.
- **Generic names with different meanings in tier 1:** `setup` (`test_operations` versus
  `test_inference`), `seed` (`test_query`, `test_publication`, `test_arrow_publication`) and
  `fixture` (`test_domain_operations` versus `test_fact_references`). `test_execution_native`
  imports both a `setup` and a `seed`.

**Consequence.**
- A change to a hub made for one consumer's case alters other modules' scenarios. This amplifies
  churn: `test_operations.py` changed in 35 commits and `test_domain_operations.py` in 19 since
  2026-10-27. It also obstructs diagnosis.
- If `fixture` stops calling `locate_proposal` by that name, the patch at `:45` stops applying.

**Footprint.**
- *Known:* the sites cited.
- *Suspected:* other `setup`/`fixture` flag combinations with similar coupling; not all 18 flags
  were traced.

**Counterevidence.**
- Most consumers assert behaviour that the current defaults support.
- The `:45` patch would most likely fail loudly rather than pass, because its assertions check the
  authored roles.

**Related.** The same cause recurs in tier-3 support, where `world` is defined in 12 places with
different scopes and meanings ([retirement transfer](retirement-transfer.md)).

**Bears on:** every package that adds native semantic tests; selective runs; failure diagnosis.

<a id="dta-012"></a>

## DTA-012 — Tier-2 support restates source and pack declarations across directories

**Principles:** FP-04, DP-01, DP-06; companion §2.
**Subject:** implemented (conftests under `tests/{llm,math,evaluate,evaluate/golden,agent,consolidate,db,ingest}`;
`tests/validate/support.py`).

**Diagnosis.** The recipe for "the production rendition of a reference page" is restated in eight
conftests:
- the vendored or corpus root;
- `ROOT = "siegrist_random/random"`;
- the Siegrist profile and the default `SentenceConfig`;
- `source_uri=f"{ROOT}/{page}"`.

The declarations that own this are in `sources/siegrist.yaml`. `PACK_MACROS` is copied in the
llm, math and evaluate conftests (`tests/llm/conftest.py:57`). Its docstring says it lives there
"until that file exists"; the file now exists (`domains/statistics/methods.yaml`), and
`tests/agent/conftest.py:54` already derives from it.

`tests/validate/support.py:57-63` loads `tests/llm/conftest.py` and `tests/schema/test_packs.py` by
file path. That gives each a second module identity and separate caches, and couples tier-3 support
to a tier-2 conftest's internals. Sharing mechanisms are mixed: fixtures, file-path `importlib`
loads, `helpers` fixtures that expose conftests, and relative imports of test modules. This follows
from `--import-mode=importlib` with only `tests/semantic` being a package.

**Consequence.** If the source root or URI convention changes, document keys derived from
`source_uri` in the frozen `data/` reference sets diverge from production keys without failing.
Each copy must also be edited separately.

**Footprint.**
- *Known:* the sites cited.
- *Drift status:* the `PACK_MACROS` copy currently equals `methods.yaml`, so there is a drift risk
  but no drift yet.

**Counterevidence.**
- The profile itself goes through production `load_profile`/`compile_profile` once per site. That
  repeats execution, not meaning, and the execution cost is immaterial.
- `spaCy` loading is cached on a frozen config.

**Bears on:** tier-2 foundations the pivot reuses (ingest, llm, math); phase-0 rescoping of source
profiles.
