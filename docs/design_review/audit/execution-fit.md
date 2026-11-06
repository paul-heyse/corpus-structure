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

## DA-054 — Annotation dependency-granularity manifestation corrected

**Source-inspected 2026-11-05.** Orchestration task identity (`orchestrate/semantic.py:386–405`), Python twin selection
(`semantic/operations.py:314–320`) and native reuse
(`semantic/sql/task_dependency_scope.sql:22–38`) consume the shared operation projection.
That projection separates annotation/extraction determinants and keeps unknown keys significant
(`:3–17`); release/runtime/source equality remains required. The cited unrelated downstream
invalidation cause is removed. This establishes neither optimal granularity nor a measured speedup.

## Current cumulative-work boundary

**Source-inspected 2026-11-05.** DA-033 remains an unresolved premise, not a demonstrated
avoidable-work defect. Current publication checks facts/cardinalities (`semantic/sql/publication.sql:25–45`),
closure validates memberships/derivations/values (`semantic/sql/closure.sql:627–688`), and
activation checks actual native catalogs (`semantic/sql/admission.sql:5–152`). Narrower checking
was not shown to preserve their trust/consistency obligations. New PCE eligibility is prepared
through shared materialized grade/origin/case collections (`semantic/sql/record_publication.sql:979–1037`),
while routine archived reading retains cached opening (`semantic/archive_reader.py:243–276,391–409`).
No fresh measurement or universal execution-fit conclusion follows.
