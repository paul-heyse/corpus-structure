# Design principle audit

The living diagnostic account maintained by the
[audit skill](../../../.claude/skills/design-principle-audit/SKILL.md). The
[repository binding](../design_principles/binding/corpus-structure.md#design-principle-audit)
owns freshness and disposition. This account diagnoses; it does not choose remedies, amend
accepted scope, certify alignment or qualify the product.

<a id="baseline"></a>

## Current broad baseline — 2026-11-03

**Source-inspected.** Source commit `fe67cc8c5b67de5f99b8fd2c148a13c6febb2ac8` plus the identified
uncommitted M1 work below. The commit publishing this refresh is distinct from the inspected
source. The source HEAD remained unchanged through contributor inspection; dirty publication SQL
changed and was re-read. Subsequent changes require affected conclusions to be reconciled.

Applied standard: core3.3, efficient-architecture heuristics1.0, code-intelligence1.4,
test-assessment1.2 where tests/support inform a claim, and the repository binding selected by
standard.toml. No incoming library preference or principle subset constrained diagnosis.

The previous broad source baseline was ad4593f (2026-10-29). Subsequent UM and M1 scoped refreshes
were leads with their own dates/exclusions, not whole-system verification. Current inspection
replaces stale broad diagnoses rather than carrying their summaries forward. Earlier accounts
remain recoverable with `git show fe67cc8c:docs/design_review/audit/README.md` and adjacent pages.

### Included working-tree context

The inspected tree included changes to DESIGN/D7, the M1 coordinator/evaluation companion,
ADR-0053, STATUS and .gitattributes, plus the current M1 qualification evidence folder. These
supply functional/maturity context; their existing test receipts are not fresh audit runs.
Dirty source includes cli/schema, physical declarations, native authoring/admission/source-view
builders, publication/reference SQL and forward101 artifacts. Relevant tests were context only.
No product behavior, plan, ADR, dependency, database, service or persistent default was changed
by this audit. Required turn-end maintenance reformatted one existing call in
ingest/pdf_recognition_methods.py; its diff was read as formatting-only and remains unstaged
outside the audit commit.

The following hashes identify decisive dirty source bytes. Paths beginning semantic/, model/ or
cli/ are relative to `python/corpus-structure/src/corpus_structure/`; rev/ means
`python/corpus-structure/semantic_alembic/versions/`.

| Decisive dirty path | SHA-256 |
|---|---|
| `ingest/pdf_recognition_methods.py` (maintenance formatting only) | `66eab5a14b05b9e0a4cf2365338bfbc41d003a79db9c621e0cc0ead9723c7506` |
| `cli/schema.py` | `b9096b06fd2dbf1d07818893f0b51973cdf94732acc1a3d2114886d3359c4418` |
| `model/semantic/physical.yaml` | `357b9c727914c4924c825435fec2111220cdcf7953673ecf638c2ce49a3171dc` |
| `semantic/execution_admission.py` | `60df17c61b58313a222019b757a8c9f68b0e8ccdaff021495cf3e16b576bf5c1` |
| `semantic/native_candidate.py` | `9affd5b1143cc14306eaeda87212a4d296b7600373d6873a4d005dfc3d2bba44` |
| `semantic/source_view_native.py` | `9ad86f2805d7c8ca65d93b4ae8eba36f9e77df3cd327f21250faec93c844ad65` |
| `semantic/sql/closure.sql` | `f0d5e79103c500b59eaab5d61084861665dbd99d4e767f0e11c193e6b864ad57` |
| `semantic/sql/record_publication.sql` | `1347b30bf4ed752a24eb4e0d8c8a18721fe6fc3ddc3fbc1ca1f5c4875ecc1dde` |
| `semantic/sql/record_references.sql` | `a81f89c362fb7426f410af41b013d0154d347a0c10af99957d6ca1680d87be2f` |
| `rev/0101_m1_records.py` | `ea5459791eda52af0172bd0a9617aa9727e3a1fb53a5467000698565538ce747` |
| `rev/semantic_m1_records_20261103_admission.sql` | `fa90598f6771816d4753bdc460bedddcb31fb5f3d64b1a875663ac07163b7c37` |
| `rev/semantic_m1_records_20261103_native.json` | `c924b22f3b1f030015f3567fe477ae3b18775622f924ba791ca0fed8e8aabad1` |

During inspection record_publication.sql changed from
`236f2955025c8cc3924cd88e7cb461874e56c857ae8f23546e5dba913596dd8d` to the recorded later bytes.
The native contributor re-read the JSON-expression repairs; no diagnosis relies on the transient
forward101 bugs. That migration remains under separate M1 qualification. Hashes identify inspected
bytes, not a claim that every line in each artifact was audited.

## Inspection and limits

Three independent read-only contributors inspected semantic authority, native persistence and
production execution. The coordinator inspected serving, CLI/MCP, exports, reference evaluation
and supporting command/environment/qualification code, read decisive cross-boundary sources,
and reconciled inherited findings. A fresh reviewer challenged consequential diagnoses and
omissions, including the trust premises behind native immutability and repeated assurance.

The functional target came from DESIGN §1 and current D-document/ADR owners. Current M1 work is
an extension with its own unqualified boundary; unfinished proposed capability is not automatically
a defect in prior supported scope. Reachable core/schema algorithms were followed as current
dependencies; their older legacy label is not a diagnosis. Retired HTML/M19 internals were not
re-audited and do not establish current supported-path defects.

All foundations informed the inspection: owner/change locality and narrow contracts (FP-01/02/06),
composable production/effect lifetimes (FP-03/05), explicit model adequacy and semantic authority
(FP-04), and qualitative necessary work, preparation, materialization, contention and recovery
(FP-07/A4). Relevant DP/core gates and CI fidelity/coverage/evidence/evaluation criteria constrain
findings independently. This is neither an exhaustive principle matrix nor an acceptance verdict.

<a id="scenarios"></a>

Representative challenges were a new identity qualifier/behavioral role, another pack,
compiler/provider change and archive read, interruption/retry and publication, changing selection
across query/follow-up/export, empty/missing/undecided reference units, larger source batches and
dense relation/witness expansion. Source contracts sufficed for the published diagnoses; there
was no uncertainty that warranted a new executable probe for this account.

**Coverage limits:** selected SQL bodies rather than every kernel; no exhaustive invariant-body
correspondence, complete provider/library conformance matrix, independent numerical verification,
whole test-architecture refresh, actual reference/fitting journey, migration-chain replay,
deployed ACL/mutation qualification, actual CLI/MCP transport journeys, performance/RSS or M1
release qualification. The separate [test account](../test-audit/README.md) retains its own baseline.
No blanket absence claim rests on an empty search or an unexamined component.

**Checks:** tests, native/provider execution, benchmarks, `just test-all` and full `just hygiene`
were **not_run**: this was a static diagnostic refresh, not a product change or qualification.
**failed, 2026-11-03:** `just docs-check` built the site but reported unresolved targets in
architecture/plans/library/evidence pages outside this audit. No diagnostic listed an audit page.
These unrelated links were not repaired. Publication maintenance is reported separately in the
handoff and commit; a failed full docs check is not relabelled as passed.
Failed/interrupted historical receipts remain with their original owners and evidence strength.

<a id="deviations"></a>

## Current synthesis

Material corrections since the older broad account include compiled qualifier projections,
released operation/implementation products, invariant diagnostics, shared scientific evidence,
archived query compatibility and follow-up pins, public read hydration, explicit purpose principals,
body-level physical attestation, forward-native evolution, cached archive opening, propagated
analytics settings and inclusion of empty producer units in reference sampling.

Remaining concrete diagnoses concern independently authored vocabulary subsets and literal roles,
rule-value translation, unresolved identity presentation, stale architecture
guidance, late source-establishment refusal, unrealized accepted policy inputs, representative
selection, candidate-inclusive row standing, coverage/explanation/path amplification, legacy split
provenance, reader effect authority, advertised operational behavior, provider attribution,
literal agent production and repeated candidate scans. DA-053 adds outstanding-claim renewal scope.
Topic pages bound these claims and give contrary evidence; none selects an implementation priority.

Questions about repeated representation conversion, Unicode identity parity, exhaustive invariant correspondence, simultaneous
multi-pack support and result-level deployment attribution remain explicitly unresolved.
Cumulative native checks protect declared trust/consistency obligations; their avoidability is
unresolved, rather than presumed from repetition. Missing extra immutability triggers inside the
trusted publisher do not establish a current restricted-runtime violation.

## Finding navigation

| Topic | Finding identities and their current diagnosis/correction |
|---|---|
| [semantic model and authority](semantic-model-and-authority.md) | [DA-001](semantic-model-and-authority.md#da-001), [DA-002](semantic-model-and-authority.md#da-002), [DA-003](semantic-model-and-authority.md#da-003), [DA-004](semantic-model-and-authority.md#da-004), [DA-005](semantic-model-and-authority.md#da-005), [DA-006](semantic-model-and-authority.md#da-006), [DA-007](semantic-model-and-authority.md#da-007), [DA-008](semantic-model-and-authority.md#da-008), [DA-009](semantic-model-and-authority.md#da-009), [DA-010](semantic-model-and-authority.md#da-010), [DA-011](semantic-model-and-authority.md#da-011), [DA-026](semantic-model-and-authority.md#da-026), [DA-027](semantic-model-and-authority.md#da-027), [DA-028](semantic-model-and-authority.md#da-028), [DA-034](semantic-model-and-authority.md#da-034), [DA-046](semantic-model-and-authority.md#da-046), [DA-048](semantic-model-and-authority.md#da-048), [DA-049](semantic-model-and-authority.md#da-049) |
| [native integrity](native-integrity.md) | [DA-029](native-integrity.md#da-029), [DA-030](native-integrity.md#da-030), [DA-031](native-integrity.md#da-031), [DA-032](native-integrity.md#da-032) |
| [structure and invariants](structure-and-invariants.md) | [DA-012](structure-and-invariants.md#da-012), [DA-013](structure-and-invariants.md#da-013), [DA-014](structure-and-invariants.md#da-014), [DA-015](structure-and-invariants.md#da-015), [DA-016](structure-and-invariants.md#da-016), [DA-017](structure-and-invariants.md#da-017), [DA-040](structure-and-invariants.md#da-040), [DA-041](structure-and-invariants.md#da-041), [DA-044](structure-and-invariants.md#da-044), [DA-053](structure-and-invariants.md#da-053) |
| [served claims](served-claims.md) | [DA-035](served-claims.md#da-035), [DA-036](served-claims.md#da-036), [DA-037](served-claims.md#da-037), [DA-038](served-claims.md#da-038), [DA-039](served-claims.md#da-039), [DA-050](served-claims.md#da-050), [DA-051](served-claims.md#da-051) |
| [boundaries and composition](boundaries-and-composition.md) | [DA-018](boundaries-and-composition.md#da-018), [DA-019](boundaries-and-composition.md#da-019), [DA-020](boundaries-and-composition.md#da-020), [DA-045](boundaries-and-composition.md#da-045), [DA-047](boundaries-and-composition.md#da-047), [DA-052](boundaries-and-composition.md#da-052) |
| [execution fit](execution-fit.md) | [DA-024](execution-fit.md#da-024), [DA-025](execution-fit.md#da-025), [DA-033](execution-fit.md#da-033), [DA-042](execution-fit.md#da-042), [DA-043](execution-fit.md#da-043) |
| [local reasoning and assurance](local-reasoning-and-assurance.md) | [DA-021](local-reasoning-and-assurance.md#da-021), [DA-022](local-reasoning-and-assurance.md#da-022), [DA-023](local-reasoning-and-assurance.md#da-023) |

## Ownership and use

Each structural cause has one primary home. IDs and surviving anchors remain stable; Git before
this refresh preserves removed diagnosis bodies and their dated evidence. Retired identities are
not reused. A removed diagnostic claim is not automatic closure of a scheduled plan obligation.

Architectural owners/ADRs retain accepted meaning; reviews retain solution reasoning; active
plans retain scheduled disposition and closure evidence. The phase0 exception owns DA-001–025
alignment-review disposition; current series own their scheduled scope. Follow the
[plan directory](../../plans/README.md) rather than copying their progress here. New unscheduled
observations remain diagnostic until a later review/planning engagement selects work.

A consuming review cites this account's publication revision and stable finding anchors, then
reconciles intervening source/standard changes. Inherited dated evidence is not newly tested by
being linked from this account. Ordinary implementation does not initiate a new broad audit.

## Prior engagement anchors

These anchors preserve current consumers' reading routes. Their original dated observations are
recoverable at the pre-refresh revision above; this current baseline does not retroactively expand
their coverage or requalify their source.

<a id="m1-public-reference-refresh"></a>
<a id="m1-source-evidence-refresh"></a>
<a id="m1-initial-target-refresh"></a>

M1-20261103-r1/r2/r3 consumed distinct initial-target, source-evidence and public/reference slices.
Current strengths and limits are reflected above; the corresponding M1 reviews retain their own
source dates and execution exclusions.

<a id="unified-model-refresh"></a>
<a id="sql-authoring-refresh"></a>

UM-20261101-r2/r3 inspected narrower model/SQL-authoring subjects. They are historical input to
this refresh, not a second current broad baseline.
