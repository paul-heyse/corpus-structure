# Execution fit

**Implemented source inspected, 2026-11-03.** [Baseline](README.md#baseline). Source paths omit
`python/corpus-structure/src/corpus_structure/`. Static work-shape reasoning is not a measured
bottleneck, latency, throughput or memory claim.

<a id="da-024"></a>

## DA-024 — Earlier publication-lifetime correction retained

Publication separates private preparation, sealing and visibility. Current transaction/retry
strengths are described in [native integrity](native-integrity.md#publication-and-retry-strengths).
The original October29 evidence retains its date; no runtime requalification occurred here.

<a id="da-025"></a>

## DA-025 — Legacy rendition-keying observation no longer applies to current source execution

Current execution consumes SourceView/native recipes. The earlier HTML/consolidation internals
were not re-audited; their historical correction is not asserted. This is removal of current
applicability, not a new test result.

<a id="da-033"></a>

## DA-033 — Cumulative assurance work is observable; avoidability remains unresolved

**FP-07/A4, DP-03/10/19/23; unresolved execution-fit premise.** Admission reconstructs archived
execution projections and checks native catalogs (`semantic/sql/admission.sql:5–18,79–152`).
Publication also scans admitted memberships/derivations/facts/values and computes cardinality/identity
(`semantic/sql/closure.sql:481–550`); positioned transport has cumulative occurrence validation
(`semantic_alembic/versions/semantic_0053_positioned_syntax.sql:1032–1051`, under the package).
M1 selected-report publication reconstructs projections and validates report relationships
(`semantic/sql/record_publication.sql:254–263,292–315,390–392`). Work therefore includes existing
immutable context beyond newly staged rows.

Those checks protect real cross-row invariants and administrative deployment drift. This inspection
has not shown that a narrower check preserves every current trust/failure premise; repeated
checking alone does not establish a violation. The old broad avoidable-whole-realization verdict is
replaced with this bounded question. Staged value meaning is now selective (closure.sql:469–479),
archived reads have cached opening (archive_reader.py:213–276,391–409), and batch receipts do not
inherently describe whole runs. No timing, capacity or asymptotic production failure is established.

<a id="da-042"></a>

## DA-042 — Routine re-verification and packet reconstruction diagnosis corrected

Routine readers use `open_release` product reconstruction (`semantic/releases.py:499–508`;
`query.py:384`; `intervene/semantic_server.py:60–69`). Full `load_release` verification still
recompiles intentionally at its verification/admission boundary. MCP retains leased packets and
checks the recorded hash (`semantic_server.py:72–106`); queue preparation reuses view/unit/config
state (`orchestrate/semantic.py:900–918,1111–1118`). Distinct source units still require their own
packets. No equivalent current redundant-work manifestation was established.

<a id="da-043"></a>

## DA-043 — Repeated candidate reconstruction premise corrected at AC scope

**Source-inspected 2026-11-04, M1-20261104-r4.** Consolidation now prepares indexed candidate
premise/attribution collections rather than rebuilding the candidate-wide collections per fact;
inference uses the admitted delta route. Scientific comparison and source receipt → inference →
terminal-result atomicity remain explicit. Necessary functional-slot comparisons and actual witness
expansion still depend on the released rules and input. This removes the prior repeated-scan
manifestation; it establishes no numerical speed/capacity claim or absence of all cumulative work.
DA-033 retains its separate trust/assurance-scope question. New record lowering must compose with
these owners rather than restoring whole-candidate rescans.


<a id="da-054"></a>

## DA-054 — Annotation identity includes unrelated downstream run settings

**FP-07/A4, DP-09/10, H12/13; source-inspected 2026-11-04, M1-20261104-r4.**
`orchestrate/semantic.py:335–355` hashes the complete run dependency digest for every task;
its manifest includes all operation configurations, GLiNER libraries, extraction policy and
guideline. `semantic/operations.py:create_task` independently requires origin/current run
dependency-digest equality. Native `ops.valid_reuse` in frozen
`semantic_alembic/versions/semantic_0012_observation_inputs.sql:62–78` requires complete
recorded dependencies; `semantic/sql/execution_guards.sql` applies that gate.

Consequently a downstream GLiNER schema/configuration change repeats unchanged source/profile
annotation work, even after introducing a separate upstream annotation method. This is a concrete
dependency-granularity/amplification cause, not a speed measurement or allegation of unsound reuse.
Necessary source, profile, release, configuration and relevant library changes must still invalidate.
A different source or release is not reusable merely because its words look equal. This differs
from retired DA-025's rendition issue and DA-042's corrected packet preparation. The scheduled
M1 preparation owner retains disposition; this account supplies diagnosis only.
