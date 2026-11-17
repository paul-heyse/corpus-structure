# Semantic model and authority

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline and limits](README.md#baseline)). Source paths omit
`python/corpus-structure/src/corpus_structure/`; `sql/` means `semantic/sql/`; `domains/` is at
the repository root. The current model owners are described in the
[domain model map](domain-model-map.md).

The four findings below share a shape: a fact the declared model already holds, or could hold,
is written a second time by hand in code or SQL. They differ in what goes wrong when the copies
drift, so they are separate findings.

<a id="da-070"></a>

## DA-070 — Validity families and family contracts are assigned from hand-written operation-id lists, and an unlisted operation is treated as valid

**FP-04/A2; DP-01, DP-03, DP-06.**

Lowering stores each operation's `validity_family` by calling `ops.ddo_classify_validity`, a
`CASE` over literal operation ids that returns `NULL` for anything not listed
(`sql/data_operations.sql:2312–2329, 2398`). Producer validity then dispatches on that column,
and an operation with no family takes `ELSE true` (`:345–353`): its family's dependency
premises are never evaluated.

The contextual family repeats its full twelve-id list in the producer guard, the completion
guard and the dependency validator, beside a per-operation table of Python entry points,
profile and forms, and partial subsets appear in several more places
(`semantic/contextual_admission_native.py:16–21, 24–49, 154–159, 214–219`). The model already declares
those facts for each operation (`support_contract.capabilities`, `profile`,
`implementation_root`). Further per-operation literals sit in `ddo_require_completion_live`
(`sql/data_operations.sql:1495–1515`) and `release_data_attempt` (`:1290`).

**Consequence.** An omission fails open, silently, at both points:

- an operation that belongs to a family but is missing from `ddo_classify_validity` (a new
  member, a rename, a split) has that family's dependency validity skipped;
- the family completion guards have the shape `IF operation_id NOT IN (...) THEN RETURN`, and
  completion calls every guard unconditionally, each selecting itself by its own list
  (`sql/data_operations.sql:1437–1456`; `contextual_admission_native.py:154–159`;
  `definition_admission_native.py:83, 106`; `operation_event_native.py:52, 248`;
  `rich_admission_native.py:183`). An operation omitted from a guard's list skips that family's
  completion checks as well. Only a listed id whose attributes disagree is refused.

What an omitted member loses depends on the family. The generic support walk and revocation
still apply to every operation. For the artifact, definition and rich families, and for
contextual operations other than scores, the family validator adds only the digest-gated
replay of [DA-068](execution-fit.md#da-068). Changing premises are lost for record grade,
record fit and operation events (cut trust: `record_grade_native.py:416–418`;
`record_policy_completion_native.py:457–459`; `operation_event_native.py:323–330`) and for
contextual scores (the linguistic premise, `contextual_admission_native.py:227–231`): for
those, an omitted operation's derivations stay valid and reusable after their premises change.

The plan defines the column as null "when no per-kind validator applies"
(`docs/plans/declared-data-operations/products-and-support.md:422–423`), so a missing entry is
indistinguishable by design from an operation that needs no validator. No test names the
classification, and no compile-time or admission-time check ties family membership to the
model. Every such edit is also a native source edit, so it changes the kernel digest.

**Contrary evidence.** Runtime dispatch reads a lowered column rather than matching names on
each call. `ddo_classify_command` in the same file classifies by eligibility predicates, not by
an id list (`:2330–2339`), which shows the alternative is already in use.

**Footprint.** Established for the classification, the dispatch and the guard shape. All 27
listed ids exist in current source, so no member is known to be missing today.

<a id="da-071"></a>

## DA-071 — Support-graph meaning is encoded three times and the change-impact copy disagrees

**FP-04/A2; DP-01, DP-03, DP-07; CI-03.**

What a support edge means (use, episode, population, original) and how a trust scope is keyed
are not declared anywhere. They are written three times:

- validity: `ops.ddo_validity_edges` (`sql/data_operations.sql:293–336`), scope key
  `ops.ddo_scope` (`:158–164`);
- locks, read scopes and access universes: `_support_walk`
  (`semantic/data_operation_projections.py:132–240`), a deliberate superset;
- change impact: `_revocation_causes` (`semantic/change_impact.py:332–441`), with its own copy
  of the scope formula (`:427`).

The change-impact copy differs from validity in two ways. For a `use`, validity follows the
producer, populations and episode and then the episode's own recorded support, and follows the
selected support only under value substitution (`sql/data_operations.sql:299–326`). Change
impact follows the episode without expanding it, deliberately by its own comment, and follows
the selected support always (`change_impact.py:358–375`). So it misses causes validity sees and
follows edges validity does not. And it always builds
`"source:" + sha256([project, source])`, where `ops.ddo_scope` builds a `project:` key when the
source is null.

Separately, the compiler produces `potential-producers` and `selected-dependencies` projections
of operation dependencies (`semantic/data_operation_model.py:716–725`). The planner consumes
the second (`semantic/data_operation_demands.py:160–165`); the first is consumed only by graph
inspection. `changed_operations` rebuilds an equivalent graph by hand from the dependency lists
(`change_impact.py:177–193`). Operation dependencies
themselves are authored as id lists that the compiler only checks for resolution
(`semantic/data_operation_compilation.py:1830–1838`); by search, nothing checks that a computed
input role's kind is produced by a declared dependency.

**Consequence.** Change impact is the planner-facing answer to "what does this change affect".
Where a use reuses an episode from another demand, causes reached only through that episode are
missed and members are reported `unknown` instead of `revoked`; revocations in a project scope
never match; and a consumer linked to a changed producer only through a kind or discovery
relation is reported `unknown` rather than `potential`. These are wrong or weaker explanations,
not wrong admission: native validity remains the authority. A new edge kind has to be added in
three places.

**Footprint.** The divergence is established. That it shows through cross-demand reuse is
likely. Whether any current operation has a project-scoped subject was not established.

<a id="da-072"></a>

## DA-072 — The earlier core and system model is still live beside the released model, with the same closed sets declared in both

**FP-04/A2; DP-01, DP-06, DP-16; H27.**

`model/core.yaml`, `model/system.yaml` and `model/revisions.yaml` are still generated into
`core/vocab.py`, `core/_model/*` and `core/keys.py`, with their own change classifier
(`schema/change.py`), revision log and pack loader (`schema/pack.py`, `schema/lookup.py`). The
released semantic model declares the same value sets again with no derivation between them:

| Value set | Declared in |
|---|---|
| `StatementKind`, including the `claim_bearing` subset | `model/core.yaml:893`; `model/semantic/core.yaml:614` |
| `ClaimModality`, `StatementRole`, `EvidenceRole`, `Establishment`, `ScopeExtent` | both core files |
| `Relation` / `ComparisonRelation`; `ParseOutcome` / `RuleReadingOutcome`; `MeasurementScope` / `SourceMeasurementScope`; `DocumentSplit` / `ReferenceSplit` | earlier / released |
| `PdfObservationOutcome` / `DdoPdfObservationOutcome` | `model/semantic/pdf-products.yaml:138`; `data-operation-pdf-capture.yaml:8` (both inside the released model) |

The statistics pack is also declared twice (`domains/statistics/schema/statistics.yaml` and
`domains/statistics/semantic.yaml` share nine classes, 23 slots and two enums), and same-named
classes in the two core files have different shapes (`IntervalValue`).

**Consequence.** The pairs agree today. An edit to one side changes behavior only for that
side's consumers: `core.vocab` users such as `semantic/formal_evidence.py:27, 644–646` and the
generated native calls (`semantic/native_call_generation.py:105`) on one side, released-model
consumers on the other. Every model-change cycle also reads and carries the earlier model
(`schema/model_change.py:426–430, 533–538`).

**Contrary evidence.** Some earlier-model consumers are live (`ParseOutcome`, `TaskUnitType`,
`CaseRule`, `core.keys.symbol_form`, `core.values`), so this is not simply dead code. D2 states
that superseded model interpreters retire. Whether any test asserts the pairs equal was not
examined, and some equal value sets may name different meanings.

**Relation to DA-012.** DA-012 asked, as a bounded question, whether operational values
correspond to a declaration. This is the first enumerated answer: these values correspond to
two.

<a id="da-073"></a>

## DA-073 — Which operations a release contains is composed by hand-written flag logic that restates family dependencies

**FP-04, FP-06; DP-01, DP-06, DP-16.**

The acquisition manifest names no operations, only flags (`downstream`, `visual`,
`source_bindings`, `pdf_contracts`, `protected_references`, `protected_record_policy`;
`domains/statistics/operations.yaml:28–66`). `primary_operation_inputs` turns the flags into
about thirty paired bundle transformers and source collections
(`semantic/primary_operations.py:118–392`). Which family needs which upstream family is then
restated in each family's source function (`semantic/canonical_sentences.py:263–268`;
`semantic/hanlp_products.py:631`; `semantic/characterization_ports.py:316, 1152–1177`) and
again in `semantic/data_operation_preparation.py:235–236`. Target operation ids are built by
string concatenation (`primary_operations.py:26–57`).

**Consequence.** Adding or reshaping a family means editing several conditional sites that must
agree with the compiled dependency edges. An omission is refused at compile or at demand
freeze, so the cost is change locality, not a wrong result. The compiled model holds operation
dependencies, but nothing maps an operation back to the source family that must be acquired.

**Contrary evidence.** Acquisition has to precede compilation, and the module states that the
compiled demand closure, not this composition, decides what executes
(`primary_operations.py:1–6, 82–86`).

## Lower-weight observations

- The token-to-type table is duplicated between the writer and the reader
  (`semantic/prepare.py:93–104`; `semantic/archive_reader.py:40–51`), and compact-encoding
  defaults for the effective model are restated in three places
  (`semantic/data_operation_model.py:133–149, 1000–1027, 1275–1287`). Most drift is caught by a
  digest or round-trip check.
- Enforcement claims are typed as documentation or as checked. By search, about 245 records are
  `documentation` and three are explicitly contract- or native-checked. This is the current
  form of DA-027's limit: the claims are honest about what they are, and the correspondence of
  each body remains unexamined.

## Prior identities on this page

<a id="da-001"></a>
<a id="da-002"></a>
<a id="da-003"></a>
<a id="da-004"></a>
<a id="da-005"></a>
<a id="da-006"></a>
<a id="da-007"></a>
<a id="da-008"></a>
<a id="da-009"></a>
<a id="da-010"></a>
<a id="da-011"></a>
<a id="da-026"></a>
<a id="da-027"></a>
<a id="da-028"></a>
<a id="da-034"></a>
<a id="da-046"></a>
<a id="da-048"></a>
<a id="da-049"></a>
<a id="da-062"></a>
<a id="da-065"></a>

Earlier text is in Git at `fbd3f2a98`. "Not re-examined" means the last evidence keeps its
original date and may describe sources that no longer exist.

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-001 | Changed footprint, not re-verified | `comparison_projection` is still compiled (`semantic/prepare.py:940–945`); the cited consumer is gone |
| DA-002 | Not re-examined | Cited `consolidation.py` and `contracts.py` are gone |
| DA-003 | Changed footprint | `display_properties` now at `semantic/types.py:398`; cited consumers gone |
| DA-004 | Not re-examined | Cited `domain_operations.py` is gone; the question stays open |
| DA-005 | Not re-examined | Evaluator site gone |
| DA-006 | Not re-examined | — |
| DA-007 | Not re-examined | Cited owners gone; the current owner of identity decisions was not located |
| DA-008 | Correction stands | Casefold only where a property declares it (`semantic/types.py:426–429`) |
| DA-009 | Stands, not re-verified | `semantic/types.py:427` consumes `unicode_identity` |
| DA-010 | Changed footprint | Explicit acquisition is `semantic/data_operation_preparation.py:136–268` |
| DA-011 | Correction stands | Compiler 24 / boundary 13 agree with D2 |
| DA-026 | No longer applicable | Replaced by the compiled effective model and generated call artifacts |
| DA-027 | Standing limit, changed footprint | See lower-weight observations above |
| DA-028 | No longer applicable | Query plugins are gone; the successor concern is [DA-076](served-claims.md#da-076) |
| DA-034 | Correction stands | One shared scientific owner; the new identity issue is [DA-077](served-claims.md#da-077) |
| DA-046 | Standing question | `domains/toy/semantic.yaml:36–44`; see DA-072 for the duplicated core vocabulary |
| DA-048 | Changed footprint | One root per acquisition manifest |
| DA-049 | Stands | Current-only reading (`semantic/data_operation_model.py:1211–1216`) |
| DA-062 | Not re-examined | Cited `record_publication.sql` and replay module are gone |
| DA-065 | Not re-examined | Cited replay module is gone |
