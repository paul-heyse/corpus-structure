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

## DA-043 — Consolidation repeatedly scans candidates inside its publication scope

**FP-07/A4, DP-10/12/19/20; implemented.** Every candidate rebuilds premise and given-by-others
collections through candidate-wide scans (`semantic/domain_operations.py:3253–3273`). Functional
slots consider fact pairs and may perform mathematical comparison (`:2755–2822`). Inference
uses whole-work-table rule fixpoints (`semantic/inference.py:209–230`), then emits proof rows for
qualifying witness pairs (`:260–294`), inside consolidation's publication transaction
(`domain_operations.py:2104–2143`). Candidate scans repeat work as the cut grows; inference expansion
also depends on the actual selected rules and witness multiplicity. Necessary pair comparison is
not automatically removable merely because it is pairwise.

The former per-ID SQL bind-limit and repeated per-fact decoding allegations are removed:
_known_input uses subqueries and indexed definition/property lookups (`:474–625`). Shared scientific
comparison preparation and explicit relational engines are strengths. The retained diagnosis is
candidate-wide repeated reconstruction and its transaction placement, not a claim that every
consolidation step is quadratic or a measured production bottleneck.
