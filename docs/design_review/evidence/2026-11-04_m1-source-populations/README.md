# M1 independent-origin source populations

**2026-11-04. Tested:** exact whole-page excerpt preparation, three actual native/managed
recognition canaries and complete 27-page native106 intake into 11 frozen source-ready views.
The separate dump round trip also restored all 11 complete source-frame/pin hashes through the
normal read-only principal. **Proposed:** reference membership under the intended final release, independently authored
family readings and release qualification.

This folder owns bounded M1-01 source evidence. The
[M1 coordinator](../../../plans/first-production-milestone_2026-11-03.md) owns package state;
the [evaluation companion](../../../plans/first-production-milestone/evaluation-qualification-and-gap-driven-expansion.md)
and ADR-0052/0053 own population/reference authority. Baseline inspected: `71a78774`, including
the coordinator's approved AC closure/M1 handoff changes. Full intake executed at `b99ef634`
plus the captured dirty M1 preparation slice, rather than claiming that commit alone contains
the run. Concurrent production/declaration edits
belong to their assigned workers; no such file was edited here. No references, predictions,
production answers or existing evaluator passes were read.

## Frozen source bytes and intended partitions

[source-population.json](source-population.json) freezes the three original hashes, the exact
excerpt bytes, complete physical page maps, intended origin partitions and all page identity
comparisons before reference authoring or extraction. These are purposively selected finite
cuts; they establish no unseen-origin generalization or claim of statistically independent
observations. All copied editions, chapter PDFs, HTML versions and overlapping windows of an
origin remain in that origin's partition. Existing Siegrist material remains development-only.
The native evaluator's immutable origin assignment has not yet run.

| Origin and intended partition | Original physical pages | Excerpt pages | Source-only eligibility leads |
| --- | --- | --- | --- |
| Grinstead–Snell, feature fitting | 191–200 (printed 183–192) | 10 | Chapter 5 opening through Poisson examples; explicit distribution definitions, conditions, formula declarations, numeric examples, count tables and comparison prose |
| Forbes, final-event calibration | 39–46 (printed 24–31) | 8 | Complete chapter 4, Multivariate Distributions; joint/marginal/conditional definitions, numeric hypothetical examples, Tables 4.1–4.3 and local formulas |
| NIST e-Handbook, final assessment | 218–226 | 9 | Complete sections 1.3.5.1/1.3.5.2, Measures of Location/Confidence Limits for the Mean; definitions, sample summaries, formula images and the hypothesis/rejection-region table |

Those leads are not five-family labels or independent reference answers. Every source unit,
including empty, unreadable and unsupported units, remains part of its intended source census.
The source-ready membership is frozen under the producing intake release below; the selected
view membership must be frozen under the intended final release before A/B/C authoring. Family
denominators and useful release support remain unestablished.

The local originals are identified by [SOURCES.tsv](../../../statistics_corpus/SOURCES.tsv) and
the prior [available-originals inventory](../2026-11-03_m1-population/available-originals.json).
Each original was rehashed here. Excerpts are whole documents for intake; their parent-page
scope is explicitly narrower than the original book. No original was rewritten. Existing
whole-document intake therefore applies without presenting a partial original as complete.

[prepare_source_cuts.py](prepare_source_cuts.py) uses installed `pypdfium2==5.14.0`, following
Context7's [official page-import API](https://pypdfium2.readthedocs.io/en/stable/python_api.html),
and its inspected installed implementation. It imports complete PDF pages without rasterizing
the saved PDF, rewriting text, reflowing content or assembling new quotations. All 27 page
dimensions and PDFium rendered-pixel digests match their parent page. Poppler's layout text is
byte-identical for each excerpt and corresponding parent-page range. These controls establish
the chosen page copies; they are not independent scientific or semantic readings. Visual checks
of NIST definition/table pages, Forbes tables and Grinstead–Snell formula/example pages found
the original layout retained. Original text-layer defects remain, including missing formula
glyphs in Poppler output; PDF images remain authoritative source inspection inputs.

## Actual provider canary

[provider_canary.py](provider_canary.py) invokes existing `PdfWorker.stream`, retained source
acquisition, prepared payload family, `native_before_nemotron` GPU handoff and
`RecognitionWorker.recognize_pages`. The dedicated managed service uses the existing launcher,
verified export and generation custody on port 8135. Its parent/process group is newly owned
and settled in `finally`; no existing service or database was changed.

**passed, 2026-11-04:** [provider-canary002/result.json](provider-canary002/result.json), actual
Standard/RapidOCR/formula conversion and managed triple-union recognition on three source pages:

| Origin | Excerpt / original physical page | Native status | Recognition | Retained requests |
| --- | --- | --- | --- | --- |
| Grinstead–Snell | 8 / 198 | success | succeeded | 3 |
| Forbes | 4 / 42 | success | succeeded | 4 |
| NIST | 8 / 225 | success | succeeded | 6 |

The retained [native inventory](provider-canary002/native-type-inventory.json) contains actual
native tables in all three cases (one, two and one respectively), with table-cell records;
Forbes also has three native formula items. Counts are source-recognition inventory, not record
family counts, recovered-header accuracy or accepted claims. Native and recognition observations,
submitted inputs, raw request/response bytes and immutable generation records remain in the
canary folder. No canary observation was published to native storage. The owned service's
[settlement receipt](provider-canary002/service/settlement.json) records its parent exit.

**failed, retained:** the first source-preparation attempt used unsupported `PdfPage` context
management; its partial PDF and [failure account](raw/preparation-attempt001.json) remain.
The successful helper explicitly closes pages. Provider-canary001 started and settled an owned
service, then failed before native conversion/recognition because the helper omitted the
required replay callback. Its [failure](provider-canary001/failure.json), logs and settlement
remain. Provider-canary002 passes `replay.verify` and succeeded. Neither failure was erased or
converted into passing provider evidence. Startup/shutdown logs include a Python semaphore
resource-tracker warning; no claim of warning-free service shutdown is made.

## Full native106 intake and remaining evidence

[intake_populations.py](intake_populations.py) prepares an explicitly admitted interpretation,
then runs the existing ingest-only graph (`policy_propose=False`) using configured excerpt
originals, per-origin projects and all descendants. It creates no GLiNER, agent or grading
tasks. A shared `PgAdmin.database` context owns a fresh acknowledged database and its OID;
the coordinator selected qualified native106, `semantic_m1_preparation_20261104`, through the
required explicit `--native-revision` argument. Existing live99,
run6, native102–105 artifacts and persistent defaults are outside this operation.

The complete provider envelope was 27 Standard pages plus 27 Nemotron triple-union
pages, using the normal bounded 80-region recipe. There are two base calls per page and at
most 80 crop calls per page; actual union/crop counts are retained rather than assumed to be
three calls per page. Actual full intake retained 27 successful page attempts and 70 managed
recognition requests. This supplies no five-family fidelity or M1 release result.

**passed, 2026-11-04:** [intake001/result.json](intake001/result.json), process exit 0. The
producing release is `release:3713a45c7097314fc5958b92baf814b314fdc46c5c8f031f016e177f4265efbe`.
Each source has its exact run/cut/pins and detached selected-source snapshot in its subfolder:

| Origin | Source run / source-ready cut | Analysis views | Observed intake elapsed seconds |
| --- | --- | --- | ---: |
| Grinstead–Snell | 1 / 1 | 1–2 (2) | 69.16 |
| Forbes | 2 / 2 | 3–9 (7) | 33.35 |
| NIST | 3 / 3 | 10–11 (2) | 36.85 |

These elapsed observations include each source's complete owned native/integrated work in this
run; they are not an ordinary-workload capacity, percentile latency or throughput study.
[source-native-population-summary.json](intake001/source-native-population-summary.json)
retains all 11 pins, per-view character/piece/health counts, native table pointers and provider
attempt/request totals. A nine-character Grinstead–Snell chapter-heading view remains in the
population; no unit was removed for lacking expected records. All views report conversion
success. Display coverage remains partial in substantive views; cell/inline coverage and many
formula outcomes remain unknown. Source readiness must not be relabelled complete original-page
fidelity or a family-quality result.

Before owned database disposal, the driver retained a custom-format `pg_dump`, its SHA-256,
archive table of contents, source/native revision and restore prerequisites. This preserves
native products, releases, artifacts and source-ready cuts for later exact-release consumption.
It also froze detached selected source views through existing read-only source readers.
The [dump manifest](intake001/dump-manifest.json) identifies 29,688,260 bytes, SHA-256
`95383f5b6172c04c728074e50fc32313e547ec73858ea5d307bddc300898e07e`, together with the exact
native revision, contents listing and restore prerequisites. `pg_restore --list` passed. The
manifest's restore status records its creation-time `not_run`; it is intentionally unchanged.
The separate restore result below supplies the later executed result.

The [source context](intake001/source-context.json) retains initial file hashes, dirty status,
working-tree patch and a compressed source archive, including untracked native106 artifacts.
[Loaded-module drift](intake001/loaded-source-context.json) is empty for the captured repository
source files. Its [supplement](intake001/source-context-supplement.json) retains the clean
qualification helper omitted from the initial archive and identifies two virtual module filenames
that have no repository file. Third-party provenance remains in the lockfile and the existing
native/recognition runtime recipes, rather than pretending those entries are repository files.

The owned database peaked at 184,227,519 bytes. The archive-stage output was about 71.3 MB and
available filesystem space remained 13,682,270,208 bytes. These are operation footprint receipts,
not a desktop capacity claim. The [database settlement](intake001/database-settlement.json)
confirms the owned database is absent after cleanup. The managed service parent exited 0 and a
subsequent socket check confirmed port 8135 closed. No persistent background service or source
database remains. The retained dump and detached inputs are the handoff products.

## Separate dump restore and subsequent workflow steering

**passed, 2026-11-04:** [attempt-restore004/result.json](attempt-restore004/result.json).
[restore_source_dump.py](restore_source_dump.py) restored the original full archive and verified
native106, all three producing release/run/source-ready-cut bindings, all 11 selected source pins
and SHA-256 equality of every complete detached source frame (text, pieces, native items,
ancestry and health). These source reads used the normal runtime reader with an explicitly
read-only transaction. No provider, GLiNER, reference answer or prediction was used.

The successful archive restore used the existing `postgres` native-maintenance identity only
inside the newly acknowledged owned database, retaining the original SECURITY DEFINER owners,
ACLs and native/application comments. `pg_dump` without `--create` omits database-level policy;
the original intake helper had made no such changes beyond the standard explicit106 bootstrap.
The existing `PgAdmin.policy/replay_policy` owner reconstructed that same bootstrap posture on
an equivalent106 database and replayed its captured owner/grants/settings before restoration.
[database-policy.json](attempt-restore004/database-policy.json) explicitly identifies this
reconstruction rather than claiming the original dump captured database policy. The normal reader
guard then admitted the restored state, and every source frame matched. Both owned contexts
were disposed; the receipt records their absence and free disk space.

All failed attempts remain separate:

- [Restore001](attempt-restore001/result.json): the ordinary maintenance login could not rewrite
  the pre-existing `postgres`-owned `pg_jsonschema` extension comment. Its owned clone was disposed.
- [Restore002](attempt-restore002/result.json): even after preserving identical inherited platform
  comments, original function-owner replay required a schema CREATE capability absent from the
  final source ACL. Its clone was disposed; the selected archive entries and prerequisite check
  remain. No application/native COMMENT entry was omitted.
- [Restore003](attempt-restore003/result.json): full privileged archive replay returned0 and native106
  matched, but the normal reader correctly refused the template's inherited PUBLIC TEMP posture.
  No reader guard was bypassed, and that clone was disposed. Restore004 added the existing policy
  owner route above and then passed.

**Operator steering received after restore004 had already completed and disposed its owned
contexts:** agents should operate the intended working database with the permissions they need,
without requiring disposable databases. No further clone, restore, posture replay, provider or
reconversion was performed after that instruction. The coordinator owns the persistent working
database and permission route. The scripts here preserve the historical controlled execution;
they do not select the future development workflow. Existing live99, run6 and persistent defaults
were unchanged throughout this assignment.

[records/m1.source-intake106.json](records/m1.source-intake106.json) is a local draft with unset
file hashes for coordinator finalization. An earlier provisional draft's null required date made
its finalize attempt fail before any record/index mutation; that failed draft and account remain
under `raw/`. No global evidence index or catalog was written by this worker.

References (fresh Sol 6.1 high A/B/C), independent record labels, family comparisons, calibration,
source capture/recall, policy precision gates and release/default adoption remain **not_run**.
The coordinator owns their qualification and final disposition.

## Commands and outcomes

```bash
uv run python docs/design_review/evidence/2026-11-04_m1-source-populations/prepare_source_cuts.py
uv run python docs/design_review/evidence/2026-11-04_m1-source-populations/provider_canary.py \
  docs/design_review/evidence/2026-11-04_m1-source-populations/provider-canary002
uv run python docs/design_review/evidence/2026-11-04_m1-source-populations/intake_populations.py \
  docs/design_review/evidence/2026-11-04_m1-source-populations/intake001 \
  --native-revision semantic_m1_preparation_20261104
uv run python docs/design_review/evidence/2026-11-04_m1-source-populations/restore_source_dump.py \
  docs/design_review/evidence/2026-11-04_m1-source-populations/intake001 \
  docs/design_review/evidence/2026-11-04_m1-source-populations/attempt-restore004
```

The first command **passed** for all 27 pages after the retained failed preparation attempt.
The second **passed** for the three real source canaries. The third **passed** for full native
intake and owned cleanup. The fourth **passed** for the separate full dump round trip, exact
source-frame comparison and owned cleanup after three retained failed attempts. Stdout/stderr are retained under
[raw](raw/). Python `compile(..., 'exec')` **passed** on all three helper files. A scoped
`uv run ruff check` selected no Python files under the repository's excluded evidence paths,
so lint coverage is **not_run**, not a clean-lint claim. Root maintenance, assembled functional
qualification and handoff remain coordinator responsibilities. No commit or push was performed.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Independent-origin finite source cuts and native intake](records/m1.source-intake106.json) | M1-01 | passed | — | 2026-11-04 |
<!-- evidence-index:end -->
