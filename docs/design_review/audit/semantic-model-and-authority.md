# Semantic model and authority

These findings concern the go-forward domain model and who owns each meaning:
- the LinkML semantic modules and pack models;
- the release compiler;
- the operation bindings, vocabularies, roles, identity recipes and translations through which
  later contexts consume the release, or fail to.

This was an operator emphasis area. Findings are at the [audited baseline](README.md#baseline); the
model as found is in the [domain model map](domain-model-map.md).

Paths are relative to `python/corpus-structure/src/corpus_structure/` unless they start with
`domains/`, `docs/`, `tests/` (`python/corpus-structure/tests/`) or `rev/`
(`python/corpus-structure/semantic_alembic/versions/`).

"Offline preparation" means `prepare_pack`/`prepare_packs` run by audit contributors without a
database on 2026-10-29. Its output was not retained.

<a id="da-001"></a>

## DA-001 — Identity-bearing qualification is declared twice, with opposite defaults and different consumers

**Principles:** DP-01 (G1), DP-04, FP-04. **Subject:** implemented.

*Continues, narrowed.* The 2026-10-28 finding concerned claim identity split between code, pack
data and prose, with qualifiers canonicalized by JSON shape. The pivot corrected that:
- keys are declared per qualification attribute (`cs:key_role`) and validated
  (`semantic/prepare.py:611-627`);
- primitive forms follow the declared range;
- fact identity refuses undeclared qualifiers (`semantic/types.py:269-293`).

What remains is a second declaration of the same question.

### Diagnosis

Two declarations decide which qualifiers distinguish facts:
- **The property declaration.** `cs:key_role` on a `Qualification` attribute governs fact identity
  in Python (`semantic/types.py:283-293`) and natively (`data.value_meaning`, `rev/semantic_0008_*.sql:2-30`).
  Evaluation follows it too (`evaluate/semantic_alignment.py:731-736`). The default is `meaning`, so
  an attribute with no declaration is identity-bearing. `identity` behaves exactly like `meaning`.
- **The predicate declaration.** `cs:qualifiers` and `cs:identity_qualifiers` govern only
  disagreement and equivalence grouping. Grouping identity is the qualification minus
  `cs:qualifiers − cs:identity_qualifiers` (`semantic/domain_operations.py:2640-2660`). Listing a
  qualifier in `cs:qualifiers` makes it *non*-identifying for grouping, which is the opposite
  default.

Nothing relates the two. Preparation only allow-lists the predicate annotations
(`semantic/prepare.py:93-94`) and stores them as raw JSON rows. It checks neither that the names
exist on the qualification class nor that they agree with `key_role`. The legacy pack validator
did both (`schema/pack.py:391-424`: "ci:key_role … contradicts … ci:identity_qualifiers"), and the
go-forward compiler dropped the check. Statistics already shows the split: `transformation_of`
lists `param_mapping` in `cs:qualifiers` but not in `cs:identity_qualifiers`, and `param_mapping`
has no `key_role`, so it is in the fact id but not in the grouping key.

### Consequence

A pack author reading `cs:identity_qualifiers` will believe it governs fact identity. Adding a
qualifier makes it identity-bearing for facts and either identity-bearing or not for grouping,
depending on which list it appears in. The disagreement is silent (scenario SC1).

**Uncertainty:** grouping coarser than fact identity may be intended, but nothing declares it.

**Evidence:** diagnosed from source (two contributors, 2026-10-29).

<a id="da-002"></a>

## DA-002 — Closed vocabularies are restated across semantic, catalog, physical, native and code owners

**Principles:** DP-01 (G1), DP-02, DP-03, DP-06. **Subject:** implemented.

*Continues the 2026-10-28 finding, through new mechanisms.* The legacy `core/vocab.py` is now
generated. In the go-forward model, the same closed sets are restated in several owners.

### Diagnosis

| Closed set | Owners as found | Divergence |
|---|---|---|
| Establishment | `core.yaml:595-599`; physical CHECK (`physical.yaml:1710`); literals and precedence in `semantic/consolidation.py:231, 253-256`; untyped in `ClassMembership`, the membership table and the catalog | The boundary admits `derived`; assembly refuses it ([DA-040](structure-and-invariants.md#da-040)) |
| Coverage outcome | `core.yaml:606`; `observations.yaml` `SourceCoverageOutcome`; `semantic/outcomes.py:9-10` Literals; catalog outcome domains; physical CHECK `:939`, which also restates the source→semantic translation as a `CASE` | Only catalog⇄Literal is checked (`semantic/contracts.py:600-605`) |
| Statement and evidence roles | `core.yaml:696-720`; hand copies `AgentStatementRole`/`AgentEvidenceRole` (`model/semantic/agent.yaml:127-143`); native literal vocabulary ids | A new core role is admitted natively but never offered to agents; a pack role is refused by both |
| Reference split | `reference.yaml:148-152` `{dev,test,reserved}`; `eval.reference_set` CHECK `{dev,test}` (`physical.yaml:2132`); `eval.document_split` CHECK `{dev,test,reserved}` (`:2344`); legacy `core.vocab` splits still used (`evaluate/split.py:35`; `evaluate/semantic.py:563`) | **Disagree**: LinkML admits `reserved` for a reference set; the database refuses it |
| Typed value kind | Physical CHECK, 17 kinds (`physical.yaml:528-530`); writer `consolidation.lower`, 10; reader `query._values.decode`, 13; native refuses `interval`/`expression`/`missing` | A kind the CHECK admits can fail a whole served page |
| `IdentityEndpointKind` | `agent.yaml:121`; physical CHECK `:2075` | — |
| Run and task status | Catalog lifecycles; physical CHECKs (`:1287`, `:1387`); native `VALUES`; legacy `RunStatus`/`TaskStatus` in reports | See [DA-012](structure-and-invariants.md#da-012) |

The structural reason is in the physical compiler. It accepts only primitive ranges
(`schema/relational.py:633`, "unsupported physical range"), and `physical.yaml` imports only
`linkml:types`. Every closed set therefore becomes `range: string` plus SQL text, and is restated
again in revision SQL ([DA-031](native-integrity.md#da-031)).

### Consequence

Extending any of these vocabularies edits three to six owners. One divergence (splits) already
exists, and another (value kinds) breaks serving if a native writer ever emits an admitted kind the
reader lacks.

### Counterevidence

The outcome-parity check exists, and native code refuses unknown values observably.

**Evidence:** diagnosed from source.

<a id="da-003"></a>

## DA-003 — Behavioural roles of categories: declared roles are inert, and the roles in use are literal reconstructions

**Principles:** FP-04/A2, DP-01 (G1), DP-03, DP-06. **Subject:** implemented.

*Continues the 2026-10-28 finding.* The release now provides the right mechanism:
`enum_members(subset=)` resolves inherited member properties from the archive. Two roles use it
correctly: `claim_bearing` (`orchestrate/semantic.py:558`) and `premise_forming`
(`serve/read.py:107`). Most behaviour still keys on literals.

### Diagnosis

**Declared, with no go-forward consumer:**
- the `ClaimModality` subsets `conflict_bearing`, `attribution_identifying` and `reserved`
  (`core.yaml:667-695`). The toy pack marks `toy:reported` attribution-identifying to no effect,
  because fact identity always includes attribution. The reserved modality `posed` is not refused;
- `cs:extract`, accepted at `semantic/prepare.py:96`;
- `cs:role: qualifier`;
- `cs:key_role: identity`, which collapses into `meaning` (`semantic/types.py:288`);
- `cs:qualifiers` applicability: any qualifier is accepted on any predicate.

**Behaviour that keys on literals instead:**
- statement roles `{"premise","example_value"}` and `statement_kind == "assumption"`
  (`semantic/domain_operations.py:3022`, `:3245-3248`);
- `"primary"` evidence as an eligibility rule (`:73`, `:1411`; `evaluate/semantic_alignment.py:125`);
- establishment precedence (`semantic/consolidation.py:253-256`);
- the default qualification `{"modality":"asserted","polarity":True}` for structural claims
  (`semantic/source_projection.py:88`; `semantic/domain_operations.py:1540, 1584, 1611`);
- a guideline rule recognized by id prefix in one place and section membership in another
  (`:3285`, `:3292`);
- serving's label properties `{"label","aliases","name","canonical_name"}` (`serve/read.py:296`).
  The release declares `cs:role: display`, which identity resolution and reference packets consume
  (`semantic/domain_operations.py:575, 602`; `orchestrate/semantic_references.py:103-115`);
- the "open" and "success" task-state classes, restated in at least seven places
  (`orchestrate/semantic.py:689`; `intervene/automated.py:47, 205-215`; `orchestrate/commands.py:270, 317`;
  natively `rev/semantic_0023_execution.sql:249, 447`);
- "agent task", defined by three different predicates at five sites:
  - natively, `tier='agent' OR family='agent'`;
  - status reporting, `tier == "agent"` (`orchestrate/commands.py:316`);
  - propose, the MCP lease and the automated provider, `name == "agent.opus"`
    (`orchestrate/semantic.py:99, 584-591`; `intervene/semantic_server.py:126`;
    `intervene/automated.py:57, 202`).

  See [DA-052](boundaries-and-composition.md#da-052);
- statistics-specific binding kinds in evaluation (`evaluate/semantic_alignment.py:148, 158`);
- modality eligibility for inference, as native literals ([DA-026](#da-026)). The statistics rule
  `stat.one_distribution_per_statement` restates `conflict_bearing` as
  `modality in ['asserted','defined']`.

### Consequence

- A new pack cannot attach behaviour by declaration. For example, it gets premise behaviour only by
  naming a kind `assumption`.
- A display property under another name resolves identity but cannot be searched by label.
- A second agent operation would be counted by status reports but invisible to automated
  extraction and the MCP queue.

**Evidence:** diagnosed from source (five contributors, 2026-10-29).

**Lead:** express each role as a member or property declaration consumed through `enum_members` or
the operation rows.

<a id="da-004"></a>

## DA-004 — Validated models and release annotations are re-parsed as dicts and strings

**Principles:** core §1 MUST, FP-04, FP-06, DP-02, DP-08; A2; heuristics H12, H19. **Subject:**
implemented.

*Continues the 2026-10-28 finding.* The legacy keying path was corrected with typed dispatch
(`core/keys.py`). The go-forward code repeats the pattern.

### Diagnosis

- **Operations.**
  - `_entity_mappings` validates each `AgentStoredBatch`, calls `model_dump`, and walks the dicts
    (`semantic/domain_operations.py:849-853`). It branches on `"kind"`, `"outcome"` and `"role"`
    strings throughout (`:1389`, `:1410-1411`, `:1719`, `:1787`, `:2974`, `:3025`).
  - The same object and qualification are re-validated repeatedly through `_reference`,
    `_entity_references`, `_claim_references`, `_source_fact_id`, the projection passes and
    `FactValueLowerer.add`: about ten times per claim, by one contributor's count, not re-verified.
  - `proposals.locate_proposal` dumps, deep-copies and mutates the validated batch
    (`semantic/proposals.py:410, 458-497`).
  - Evaluation dispatches on value-kind strings (`evaluate/semantic_alignment.py:195-433`).
- **Release annotations.**
  - `PropertyDefinition` types `case_policy`, `key_role` and `reference_role`
    (`semantic/types.py:80-102`).
  - `cs:scope`, `cs:role`, `cs:functional`, `cs:qualifiers`, `cs:param_map` and the slot-group
    tokens stay raw JSON in the `operation_*` registry rows (`semantic/prepare.py:1037-1071`).
  - Each consumer decodes and compares strings, including `.lower() == "true"`
    (`semantic/domain_operations.py:571-605, 821-825, 899-1036, 2646-2674, 3019`;
    `serve/read.py:296-303`; `orchestrate/semantic_references.py:34-37, 104-113`).
  - Class-level `cs:case` (label case) and property-level case policy (key case) share a name, and
    nothing declares how they differ.
- **Contract binding.** The declared `resolve_identity` operation is bound to the private
  `_entity_mappings` (`semantic/contracts.py:86`).

### Consequence

- A new batch section, value kind or reference position needs coordinated edits in proposal
  checking, entity mapping, both exclusion passes and known-input loading.
- Every policy driven by an annotation touches each consumer.
- Local tests need dicts shaped like database rows.
- The repeated validation and decoding add per-fact work ([DA-043](execution-fit.md#da-043)).

**Evidence:** diagnosed from source.

<a id="da-005"></a>

## DA-005 — Context translations are not owned as complete contracts

**Principles:** core §1 MUST, FP-01, FP-04, DP-01, DP-06, DP-08, DP-17; G2, G6; A2; ADR-0018.
**Subject:** implemented.

*Continues the 2026-10-28 finding.* The specific losses it recorded — dropped alternatives and
unsupported items — no longer occur. The translations between contexts are still procedural and
unowned.

### Diagnosis

- **Candidates → rule view: semantics defined by legacy types and legacy pack rules.**
  - The executed rules are the legacy-format `domains/<pack>/schema/rules.yaml` plus the core rules
    and `methods.yaml` aliases, folded into `operation/domain-rules.yaml` (`semantic/regeneration.py:125-133`).
  - The rule-visible object model comes from legacy `schema.rules`, `schema.rulelang`,
    `validate.views` (including private names), `pool.steps` and `consolidate.finalize.GRAMMAR_KINDS`
    (`semantic/domain_operations.py:2298-2454, 2938-2950`).
  - The translation is lossy. `ValueView(kind, latex, scalar, None, kind, reading)` (`:3182`) leaves
    `enum` always `None` and sets `slot_kind` to the value's own kind, while the legacy meaning is
    the slot's declared kind.
  - `defined_symbol` is computed only when the kind is literally `"formula"`
    (`validate/views.py:178-180`). Statistics' predicates use `Formula`, so current statistics
    behaviour holds. A pack using core `ExpressionValue` (`kind: expression`) would see
    `guideline.formula_excludes_defined_variable` pass vacuously.
  - LinkML ranges are mapped ad hoc to rule types (`:2338-2353`).
- **Agent batch → occurrence.**
  - The translation is spread across one 920-line function, `_project_cut`
    (`semantic/domain_operations.py:1066-1987`).
  - Exclusion rows are built twice (`:1488-1546`, `:1703-1795`), and evidence-row encoding is
    written three times.
  - Core class names are hard-coded (`"AgentStoredBatch"`, `"AgentClaim"`, `"SourceObservation"`).
  - Native validators implement the same translation a second time from raw payload paths and the
    positional `claims/<n>` item grammar (`rev/semantic_0030_source_frames.sql:184-262`).
- **Agent report → evaluation prediction.**
  - The evaluator rebuilds the prediction from the raw `AgentStoredBatch` payload, not from admitted
    facts.
  - It finds admitted claims by re-deriving the occurrence item key `"claims/" + index`
    (`evaluate/semantic.py:635-754`, `:706`).
  - It deduplicates the two sides differently: predictions by production fact identity, references
    by canonical authored bytes (`evaluate/semantic_alignment.py:738-757`).

### Consequence

- A domain using core value kinds gets rules that compile but never fire.
- Adding a rule-visible field means editing legacy modules.
- A change to occurrence item keys silently empties predictions, which looks like a zero grade.
- Precision and recall are skewed wherever production identity and authored bytes disagree.

### Counterevidence

Rules compile against release vocabularies at admission and refuse typos
(`semantic/prepare.py:1101-1109`). ADR-0018 and ADR-0027 deliberately retain the rule engine. The
defect is the authority over the view schema, not the engine.

**Evidence:** diagnosed from source.

**Related:** [DA-045](boundaries-and-composition.md#da-045),
[DA-014](structure-and-invariants.md#da-014).

<a id="da-006"></a>

## DA-006 — Retired at this baseline

*Was: "References carry no kind, and reference integrity has two named owners" (2026-10-28).*

References are now typed:
- by range (`EntityValue.target: Entity`, `core.yaml:65-72`);
- by `cs:reference_role: fact`, validated and enforced (`semantic/prepare.py:632-641`;
  `semantic/domain_operations.py:439-442`);
- by 71 physical foreign keys.

The residue — claim references that remain bare strings resolved through a local-first fallback —
is a matter of unresolved-reference handling and continues in [DA-007](#da-007). Verified
2026-10-29 at `ad4593f`. The earlier text is in Git.

<a id="da-007"></a>

## DA-007 — Unresolved references and unsettled identities are coverage prose or silent defaults, not typed states

**Principles:** DP-02, DP-04, DP-12; CI-03, CI-04; G2, G5. **Subject:** implemented.

*Continues the 2026-10-28 finding, partly improved.* Most drops now leave coverage rows, and claims
that reference an external-reference entity become `candidate` with an uncertainty. The typed state
is still missing.

### Diagnosis

**Two encodings for one concept.**
- A claim's subject, `EntityValue.target`, alternative members and the statement reference are bare
  strings (`model/semantic/agent.yaml:59-73`). They resolve "local handle first, otherwise a known
  id" (`semantic/proposals.py:274-277, 305`; `semantic/domain_operations.py:433, 1355, 1417`,
  `mapping.get(t, t)`).
- Identity-exclusion endpoints carry an explicit `kind: local|known` (`agent.yaml:91-95, 118-121`).
- Evaluation uses a third fallback, `"unresolved:" + entity` (`evaluate/semantic_alignment.py:226-230`).

**What happens when resolution fails:**
- *Outside statement:* coverage only (`semantic/domain_operations.py:1256-1262`). The claim keeps
  no endpoint, and the reference description is not projected. Proposal input injects the sentinel
  kind `outside` into the statement-kind enum (`semantic/proposals.py:73-76`).
- *Cyclic or unavailable premise:* the claim is dropped, with a prose partial-coverage row
  (`:1378-1386`).
- *Unresolved subject or unrepresentable endpoint:* the claim is dropped, with a partial-coverage
  row (`:1418-1425`, `:1454-1464`).
- *Ambiguous global label* (two or more known anchors): each mention becomes a new singleton entity,
  with nothing recorded (`:946-959`).
- *Identity-key cycle:* the loop breaks without progress and leaves source-local identities, with
  nothing recorded (`:1043-1045`).

The `resolve_identity` contract declares only `applied | conflict`
(`model/semantic/execution-model.yaml:4782-4805`).

The `mapping.get(t, t)` fallback is also how known global ids pass through. So the deeper defect is
an untyped namespace: local handles and global ids share one string field with `kind: "entity"`.
The fallback itself is a symptom. This is suspected (W2-C, 2026-10-29).

### Consequence

- A query cannot tell "unresolved" from "absent" ([DA-035](served-claims.md#da-035)).
- Facts about an ambiguous mention look like ordinary facts about a new entity.
- Recursively keyed entities never merge, and nothing shows it.

**Evidence:** diagnosed from source.

<a id="da-008"></a>

## DA-008 — Retired at this baseline

*Was: "The canonical text form erases case distinctions that identify mathematical objects"
(2026-10-28).*

Case is preserved by default and folded only where a class or property declares it
(`semantic/types.py:92, 239-240, 282-283`). The statistics pack marks the random-variable class and
`canonical_name` as case-preserving (`domains/statistics/semantic.yaml:120, 238`), and
consolidation passes the declared case into label normalization. Verified 2026-10-29 at `ad4593f`.
The earlier text is in Git.

<a id="da-009"></a>

## DA-009 — Identity determinants are hand-listed, and identity recipes are unversioned and mirrored without a specification

**Principles:** DP-01, DP-03, DP-04, DP-09, DP-23, DP-24; CI-03; G1, G6. **Subject:** implemented.

*Continues, narrowed.* The 2026-10-28 finding concerned core contracts and the key scheme having
no version. The release id now covers the compiler version, profile, sources, dependencies and
resolved vocabularies, and every semantic key embeds `release_id`. What remains is the recipe
layer and the determinant lists.

### Diagnosis

**Determinants are mixed and hand-listed.**
- The release-id manifest includes eleven library versions and the compiler version
  (`semantic/prepare.py:820-832`).
- The library list is kept by hand twice (`semantic/prepare.py:414-426`; `semantic/releases.py:30-42`).
- Neither list includes sympy or numpy, which drive equivalence assessment ids
  ([DA-034](#da-034)).
- The run dependency manifest has its own hand-kept library list keyed by method name, which also
  omits sympy (`orchestrate/semantic.py:130-143`). It keys twin reuse
  (`semantic/operations.py:226`) and native `valid_reuse`.
- **So the determinants are both over-inclusive and under-inclusive.**
  - Over-inclusive: eleven compile libraries refuse on any patch release, even when no byte would
    change ([DA-049](#da-049)).
  - Under-inclusive: sympy, the Unicode tables and the interpreter influence bytes or decisions but
    are recorded nowhere. Casefold identity depends on Python's `unicodedata` and PostgreSQL's
    Unicode version (`semantic/types.py:247, 290`; native `value_meaning`). Their agreement is
    checked once per database lifetime, in revision 0003 (`rev/0003_protected_publication.py:21-25`).
    The interpreter appears only in the preparation cache key (`semantic/prepare.py:433`).
- Six version constants exist (compiler 10, execution 2, analytical-4, authored-select-1, agent
  semantic-1, semantic-domain-2). Only the first two enter release identity.

**Recipes are unversioned and maintained as unspecified mirrors.**
- ADR-0025 deliberately has native code recompute identities so that an untrusted writer cannot
  bypass them. Those enforcement mirrors are legitimate.
- But each recipe exists as two or more hand-written implementations with no specification, no
  version and, except one, no differential check.

| Recipe | Python | Native | Conformance evidence |
|---|---|---|---|
| Value meaning, canonical JSON, decimal | `semantic/identity.py:13-66` | revisions 0006 and 0008 | differential vectors (`tests/semantic/test_publication.py:423-467`) |
| `fact:` with qualification key roles and casefold | `semantic/identity.py:76-103`; `semantic/types.py:269-300`; re-coded in `semantic/inference.py:174-187` | `data.fact_identity` | end-to-end only |
| `occ:`, `derivation:`, `alternative:`, `identity-exclusion:` | `semantic/identity.py:69, 107`; `semantic/inference.py:214-222`; two sites in `domain_operations.py` | `rev/semantic_0027_transport.sql:146-149`; `validate_state`; `validate_alternatives`; exclusion validator | end-to-end |
| Statement entity id; `evidence:` id over raw citation JSON | `semantic/source_projection.py:19-30`; `domain_operations.py:1395, 1499, 1759` | `rev/semantic_0030_source_frames.sql:199-258` | end-to-end; no subclass case |
| Receipt content bytes | `publication.py:346-359` **and** `arrow_publication.py:150-170` | `rev/semantic_0027_transport.sql:62` | compared at runtime |
| Locator grammar | legacy `core/locators.py` | `ops.source_locator_segment` | none ([DA-014](structure-and-invariants.md#da-014)) |

- Evaluation has its own qualified-meaning projection for deduplication
  (`evaluate/semantic_alignment.py:719-752`). Its key includes statement and statement role, so it
  is a distinct identity notion rather than a third copy.

**The two canonical-JSON implementations agree only on an unstated subset.** Probe P4 (2026-10-29):
- native `data.canonical_json` renders `[1e-05,1.0E2,-0.0,0.1,…]` as `[0.00001,100,0.0,0.1,…]`;
- Python `canonical_bytes` renders it as `[1e-05,100.0,-0.0,0.1,…]`;
- the producers are safe only because decimals travel as strings or `{"decimal": …}` objects.

The two Python receipt encoders also normalize numeric scale differently. A lost-commit lookup
could raise a false conflict for a batch with mixed numeric scales; this is latent, because
`confidence` is unset.

### Consequence

- A library patch bump with unchanged meaning changes every semantic identity.
- A recipe change depends on someone remembering to bump the compiler version.
- `'admitted fact meaning changed'` cannot tell a deliberate recipe change from corruption.
- Drift on the publication path fails closed, which costs availability ([DA-026](#da-026) is one
  instance). Where native code is weaker, drift is silent.
- A sympy change could silently allow stale observations to be reused.

### Counterevidence

Byte-exact identity is a deliberate design (ADR-0024/0025), and native recomputation prevents silent
divergence on the main recipes.

**Evidence:** diagnosed from source; canonical-JSON divergence measured by probe P4.

<a id="da-010"></a>

## DA-010 — Retired at this baseline

*Was: "Source profiles carry schema vocabulary outside any schema version" (2026-10-28).*

Source profiles are archived into the release as `source-profile/<name>.yaml`
(`semantic/regeneration.py:102-109`). They are validated against the release vocabulary
(`ingest/profile.py:20-36, 112-122, 280-298`). The residue — runs load the live profiles rather than
the archived ones — belongs to [DA-028](#da-028). Verified 2026-10-29 at `ad4593f`. The earlier text
is in Git.

<a id="da-011"></a>

## DA-011 — The design collection carries superseded and current authority side by side, and restated contracts drift

**Principles:** FP-04 (scoped authority), DP-01, DP-22, DP-24; ADR-0001 ("keep sections current").
**Subject:** design text.

*Continues the 2026-10-28 finding,* whose subject was design documents restating executable
contracts. The pivot added a second cause: the collection now carries superseded and current
decisions in the same sections.

### Diagnosis

- **The functional target that grounds reviews is pre-pivot.**
  - DESIGN §1.1–§1.3 are labelled Proposed and describe the pre-pivot pipeline. §1.3's generality
    check names the packages `core`, `schema` and `consolidate`, and §1.2 lists RDF publication
    out of scope.
  - The binding grounds design reviews on "the functional target in DESIGN §1.1". The go-forward
    target actually lives in the functional reviews' target models.
- **§B blocks stack superseded text beside current text.**
  - §B2 keeps its ADR-0014 Proposed block ("rebuilt per pass and materialized per run") beside the
    ADR-0027 target.
  - §B4 keeps the superseded ADR-0021 text — "migration 0001, the pool and the engine not yet
    built", payload-schema registry, consolidation pool — beside ADR-0025's "domain classes are
    release rows". It also states "the operational database remains on semantic_0005", contradicted
    by STATUS.
  - §B3 ("the pipeline never calls it", "not yet built") is stale: `ci regenerate` spawns and waits
    on the agent provider.
  - §B6 ("routing not yet built") is partly stale. Escalation routing is a declared deferral, but
    propose routing is built ([DA-016](structure-and-invariants.md#da-016)).
- **Restated facts drift.**
  - The compiler version is stated as 6 and 7 in D2 (D2:27, D2:74) and as 8 in DESIGN §B5, while
    the code says 10 (`semantic/types.py:11`).
  - D3:23 names the dead `semantic/routines.py` as the supplier of protected staging and native
    enforcement ([DA-032](native-integrity.md#da-032)).
  - D3:25 says the application never receives migration credentials, while release archival uses
    them ([DA-030](native-integrity.md#da-030)).
  - D3:55 asserts that native fatal-diagnostic policy "matches Python", although the two are
    separate definitions sharing a message-keyed exception.
  - D3 §13 describes `corpus` and `corpus_ro` ([DA-020](boundaries-and-composition.md#da-020)).
  - D8 §1 says MCP serves query and explain, but the MCP server has seven extraction tools.
  - D3 still contains about 48 legacy `CREATE TABLE` statements.
- **Structure.** DESIGN says "This file plus `docs/design/sections/` is the architectural
  authority", but `sections/` is empty and the D-documents live in `docs/design/`.

### Consequence

- A design review held now would ground itself on a stale functional target.
- A reader cannot tell which of two adjacent blocks governs.
- Restated facts — versions, suppliers, credential rules — have already drifted from the code.

**Evidence:** coordinator design-collection pass and contributor citations, 2026-10-29. The design
text was read at `ad4593f`. DESIGN and the architecture map changed in `ad4593f` itself; the stale
blocks above persist after that commit.

<a id="da-026"></a>

## DA-026 — Release operation bindings have no declared product, so native and Python code bind platform roles by name

**Principles:** core §1 MUST, FP-04, FP-02, A2, A3, DP-01 (G1), DP-02 (G2), DP-05, DP-06, DP-08,
DP-24; §E change locality; plan SP-03's "release-aware" native predicates. **Subject:**
implemented.

### Diagnosis

A release must decide which admitted class plays "source statement" for the agent operation, and
which class qualifies agent claims. No release product owns that decision. It travels as follows:
1. **Inferred from raw pack YAML before LinkML resolves it.** The scan matches
   `is_a == "SourceStatement"` and `is_a == "Qualification"`, direct children only, and requires a
   unique child per pack: a second direct subclass is refused, and subclasses through mixins or
   deeper levels are not seen (`semantic/regeneration.py:64-73, 87-96, 164-183`).
2. **Encoded by rewriting agent-boundary ranges.** The phantom attributes
   `AgentStatementBinding.statement` and `AgentClaim.qualification` carry it
   (`model/semantic/agent.yaml:25-28`; `semantic/proposals.py:51-72`).
3. **Read back by class and property name.** A documented fallback to `"SourceStatement"` exists for
   older archives; it cannot tell an old archive from a malformed one
   (`semantic/statement_types.py:8-20`). Python consumers do use the binding
   (`semantic/domain_operations.py:1345-1348, 1437-1440`; `semantic/consolidation.py:255-260`).
4. **Not reachable by native guards.** The guards are frozen per revision and pinned by body hash,
   and `NativeGuardBinding` passes a symbol and a static version `"1"`, with no class, vocabulary or
   policy parameters (`semantic/contracts.py:289-306`). The release projection has no binding rows
   (`semantic/releases.py:149-262`). So native code restates platform defaults by name:
   - **Statement class — the observed defect.** The occurrence-context guard requires membership of
     a class named exactly `SourceStatement` (`rev/semantic_0030_source_frames.sql:172-178`). Python
     publishes membership only in the bound class. A valid `ToySourceStatement` is refused, and the
     fresh MCP run 3 is stuck sealed and consolidating (STATUS, 2026-10-29).
   - **Role vocabularies.** `vocabulary_id='StatementRole'` and `'EvidenceRole'`
     (`rev/semantic_0030_source_frames.sql:163-171`), and the literal `'primary'`.
   - **Payload formats.** The definitions `'AgentStoredBatch'` and `'SourceObservation'` are
     repeated across the validators of several revisions, together with payload JSON paths
     (`payload->'claims'`, `outcome='located'`, the item grammar `^claims/[0-9]+$`;
     `rev/semantic_0030_source_frames.sql:184-262`; also `eval.*` functions).
   - **The operation version.** `x.operation_version <> 'semantic-domain-2'`
     (`rev/semantic_0027_exclusions.sql:66`) mirrors `semantic/domain_operations.py:47`. Bumping
     the Python `VERSION` would make native code refuse every identity exclusion until a new
     revision is written.
   - **Inference eligibility.** `role='modality' … IN ('asserted','defined')`, polarity, no
     `hedge`, `establishment='stated'` (`rev/semantic_0014_entity_input.sql:253-261`). The policy
     itself is an accepted decision (ADR-0027). The defect is that it is expressed as literals
     rather than as a declared subset: `conflict_bearing` governs nothing, and a pack modality
     cannot opt in. The realization plan anticipated a declared subset
     (`docs/plans/semantic-model-pivot/domain-model-realization.md:117`).
5. **Restated as Python literals.** `semantic/source_projection.py:86`
   (`prop.range != "SourceStatement"`).

The native Qualification check accepts any descendant of a class named `Qualification`
(`rev/semantic_0027_transport.sql:162`), not the bound range. That is consistent with what the
producer writes, because entity-attribute and statement facts are always typed with base
`Qualification` (`semantic/domain_operations.py:1585, 1612`). So the producer applies two class
policies, and neither is declared ([DA-003](#da-003)).

**Composition.** With `statistics + toy`, offline preparation bound `ToySourceStatement` for all
sources, statistics included. The roles have no binding at all: statement and evidence roles are
fixed hand copies in `agent.yaml` ([DA-002](#da-002)), so a pack role is refused at the agent
schema and again natively.

### Consequence

- **Supported behaviour:** a pack specialization the platform explicitly provides for is refused,
  and fresh frame runs cannot complete.
- **Credible change:** each of these needs a new frozen revision, regenerated descriptor hashes, a
  new Python constant and matching Python edits, owned by unrelated components (§E, A3):
  - a new pack;
  - a second qualification subclass;
  - a pack modality;
  - an operation-version bump;
  - a pack-specific role.
- **The pending correction is necessary, not sufficient.** Draft-0031 reads `property_applicability`
  for the class *named* `AgentStatementBinding`. It fixes the symptom but keeps binding by naming
  convention, and it leaves roles, eligibility, payload formats and the operation version as they
  are.

### Counterevidence

- The name lookups read release rows scoped by `release_id`, and most native validation is
  release-driven: applicability, identity slots, key roles and case policy.
- Inference eligibility is an operator decision.

**Evidence:** diagnosed from source (four contributors), offline preparation, and the operational
refusal recorded in STATUS.

**Lead:** the compiler emits typed binding rows (operation → role → class, vocabulary, subset or
policy) once per release, consumed by Python resolution and by parameterized native guards.

<a id="da-027"></a>

## DA-027 — Model layers describe the knowledge and execution records without governing them

**Principles:** FP-04/A2 ("Does that model govern behavior, or merely describe outputs?"), DP-01,
DP-02, DP-03, DP-16, DP-21, DP-24; G1, G2, G7; heuristic H27. **Subject:** implemented, judged
against the accepted completeness target: "Logical relationships drive boundary references and
relational descriptors".

### Diagnosis

Two model layers look authoritative and do not govern behaviour.

**The trusted execution catalog.**
- **Size and boilerplate.** `model/semantic/execution-model.yaml` has 8,366 lines: 116 concepts (101
  described as "X in the transitioned semantic model", 96 with one boilerplate identity sentence),
  57 relationships (43 with the same boilerplate cardinality scope) and 27 invariants, plus
  lifecycles, operations and projections.
- **What compilation checks** (`semantic/contracts.py:418-605`): internal cross-references,
  approved Python symbols, the native guard table, and parity of outcome domains with code Literals.
- **What runtime consumes:** coverage outcome translations (`semantic/outcomes.py:64-100`), a
  projection's implementation and lifetime (`semantic/analytics.py:238-256`), and `model_id`
  equality at activation. Concepts, relationships and invariants are never consumed, and nothing
  reconciles them with `core.yaml` or `physical.yaml`.
- **Where it contradicts the semantic model:**
  - its `Qualification` requires `scope` and plural `conditions`
    (`execution-model.yaml:1501-1515`), where core has an optional `scope`, a singular `condition`,
    and `hedge`/`valid_time` (`core.yaml:128-145`);
  - its `Entity` uses `identity_keys` and `display_label` (`:1038-1042`), where core uses `label`
    and `aliases`;
  - `Membership.establishment` is untyped;
  - it has no `SourceStatement` concept, although native code enforces `SourceStatement`
    membership.
- **Codes and lowering:**
  - invariant `failure_code`s (for example `identity.exclusion_conflict`) are never emitted;
    native code raises 321 distinct prose messages ([DA-013](structure-and-invariants.md#da-013));
  - lifecycles are lowered by hand into the frozen `ops.execution_edge` `VALUES`
    (`rev/semantic_0023_execution.sql:3-44`). The revision header says "generated at development
    time", but no generator is in the repository. There are 38 native edges against 40 catalog
    transitions. The missing pair, `reference_pass_record` and `reference_grade_record` going from
    private to recorded, is enforced by the reference routines instead. Parity rests on a test that
    samples six task edges (`tests/semantic/test_execution_native.py:85-101`);
  - guard versions stay `"1"` while their bodies change. `finish_evaluation` has six definitions,
    and since the catalog was introduced at 0023 guard bodies changed in 0027 and 0029. Body
    identity is attested by the descriptor's digests ([DA-032](native-integrity.md#da-032)), so the
    version field is decorative rather than a gap in detection.
- **Activation effect.** Any byte edit to `execution-model.yaml`, `contracts.yaml` or
  `reference.yaml` changes `execution_model_id`. Once a descriptor carrying the new id is deployed,
  writes and selection for every archived release refuse ([DA-049](#da-049)).

**The core record classes.**
- `AssertionOccurrence`, `SemanticFact`, `Derivation`, `ClassMembership`, `Evidence` and `Coverage`
  (`core.yaml:157, 181, 502, 356, 368, 381`) are never referenced by name or used as a boundary.
- The stored occurrence carries statement context, role, establishment and evidence roles that the
  core class lacks (`semantic/publication.py:94-170`).
- Selection, Assessment, Support, AlternativeGroup, the entity and fact inputs, and
  IdentityExclusion have no class in the release. They exist only as boilerplate catalog concepts,
  physical tables, string-typed transport dataclasses and native guards.

So the knowledge, decision and lineage records are governed by `physical.yaml` plus native SQL.
Two other layers describe them and disagree with each other.

### Consequence

- A reader or agent consulting the catalog or the core classes gets meanings that differ from what
  governs.
- The target's physical projection mapping (concept to table) is absent.
- The catalog is large maintained machinery with no distinct protection, and editing its text
  invalidates every archive.
- No model owns occurrence or decision semantics.

### Counterevidence

Implementation-binding approval is real governance: catalog data cannot name imports. Outcome
parity is checked. The lifecycle catalog was plausibly the authoring source for the native
lowering. `physical.yaml` is a single derivation source for the MetaData.

**Evidence:** diagnosed from source; edge counts from a contributor's comparison script
(2026-10-29).

<a id="da-028"></a>

## DA-028 — Runs and served queries execute the live pack files that the bound release archives

**Principles:** DP-01, DP-05, DP-09, FP-04; CI-10, CI-13; ADR-0024 ("releases own … executable
scope"; "future releases still cannot silently change the meaning of bound operations"); ADR-0030
("queries … bind the selected result's archived release"). **Subject:** implemented, judged against
accepted decisions.

### Diagnosis

`prepare_pack` archives the pack's operation inputs into the release:
`operation/{methods.yaml, guideline.md, queries.py, policies.yaml, slices.yaml}` and
`source-profile/*.yaml`. Their digests determine the release id (`semantic/regeneration.py:133-160`).

Execution and serving read the working-tree copies instead:
- `start_bound_run` loads the release, but reads slices, policies, guideline and the method registry
  from the live `DOMAINS/<domain>` (`orchestrate/commands.py:92-161`);
- the registry reads the live `methods.yaml` and `SOURCES_DIR` (`orchestrate/registry.py:235-245`),
  and profiles are read from `SOURCES_DIR` even when the prepared release is supplied
  (`orchestrate/project.py:121`; `ingest/profile.py:138-149`);
- the run's dependency manifest records those live inputs (`orchestrate/semantic.py:141-177`);
- the pack is a CLI option defaulting to `statistics`, independent of the project's active release
  (`cli/orchestrate.py:148-150`). Nothing checks that the pack matches the release;
- `ci query` imports the live `domains/<run domain>/queries.py` (`cli/query.py:42-57`;
  `serve/registry.py:24, 52-79`). Continuation tokens bind release, realization, revision and
  projection (`serve/journey.py:119-130`). The plug-in *code* is identified only by one shared
  literal version string, `"semantic-1"`, inherited by every generic and pack query
  (`serve/queries.py:56`). Plug-in edits cannot be detected.

Evaluation does read the archived inputs (`evaluate/semantic.py:171, 194`), so slice definitions
have two authorities.

### Consequence

- A run can bind release R, whose archived inputs are X, while executing pack inputs Y.
- Editing `guideline.md` changes the release id, but runs never consume the archived guideline.
- Editing a plug-in changes the answers for an archived result without changing the release, the
  token or the result binding. Continuations resume under different code.
- *Suspected:* `ci run --project <toy project>` without `--domain` would run the statistics methods,
  policies and guideline against the toy release (not executed).

### Counterevidence

The run manifest records exactly what was used, so lineage exists, and regeneration prepares and
runs from the same bytes at the same moment.

**Evidence:** diagnosed from source (three contributors independently).

<a id="da-034"></a>

## DA-034 — Scientific equivalence has two authorities, and selection consumes the sampled, casefolded one

**Principles:** core §1 MUST, FP-04, DP-01 (G1), DP-05, DP-08, DP-11, DP-18; G4, G6, G7; A2; heuristic
H1. **Subject:** implemented, judged against the accepted target: one explicit scientific-equivalence
operation, with evaluation independence coming from reference data.

### Diagnosis

One domain question — are two reported values the same? — has two executable definitions that
decide it differently.

- **The domain path, which drives selection.**
  - `ReleasedRulesPolicy.scientific_decisions` converts release values into legacy `core.values`
    (`semantic/domain_operations.py:2183-2249`).
  - It calls the legacy `evaluate.equivalence.ValueComparator` (`:2627`, `:2782-2822`), reaching into
    its private `_constraints` (`:2810-2812`).
  - Its tiers: canonical text with NFC and casefold; symbolic `sympy.simplify` under a 5-second
    wall-clock `SIGALRM` deadline (`methods/math/grammar.py:398-424`); and numeric, where agreement at
    sampled points yields `equal=True` (`evaluate/equivalence.py:51`, `NUMERIC_POINTS = 12`).
- **The evaluation path.** `evaluate/semantic_alignment.equivalent` uses probes only to disprove:
  coincident points stay `undecided`, and text compares exactly.
- **A contributor's probe (2026-10-29, scratch) shows they disagree in both directions:**

| Pair | Domain path | Evaluation path |
|---|---|---|
| `"Normal"` / `"normal"` | equal (canonical) | not equal |
| `(x^2)^{1/2}` / `\|x\|` | equal (numeric, "simplify inconclusive; 12 points") | undecided |
| `\sqrt{x^2}` / `x` | different (numeric counterexample) | undecided |

**What selection does with the domain verdict.**
- Facts judged equal are unioned (`:2839-2860`). Each equivalence component keeps only its first
  member by canonical bytes; the rest leave `data.selection` (`:3375-3378`).
- No plan or design text declares this collapse policy.
- Consumers then serve the deselected facts as `candidate` ([DA-036](served-claims.md#da-036)).

**The declared contract disagrees.** It says `precision: exact`, `no implicit rounding` and
`effects: []` (`execution-model.yaml:5475, 5496, 5512`). In practice:
- the tier and its detail depend on a wall-clock deadline, and enter `assessment_id` (`:2697-2713`);
- timeouts are not memoized;
- the deadline requires the main thread and is process-global (`grammar.py:398-424`);
- `OffMainThread` is a `RuntimeError` that the surrounding handler does not catch (`:2823`).

**Other definitions.** Grading uses yet another notion of value sameness
([DA-005](#da-005), [DA-037](served-claims.md#da-037)). `consolidate_cut(policy=…)` accepts any
object whose version string matches (`:2002-2008`).

### Consequence

- In a functional slot, facts that differ only by case, or agree only at sampled points, collapse to
  one selected fact.
- Evaluation of the same pair says different or undecided, so selection and evaluation disagree
  about one proposition.
- Results can differ with machine load (DP-11).
- Changing what "equal" means requires editing a module outside the go-forward scope
  ([DA-045](boundaries-and-composition.md#da-045)).
- The kernels cannot run in worker threads or server tools.

### Counterevidence

Equivalence is recorded as an assessment with its tier, and `undecided` stays distinct. Numeric
agreement at 1e-9 is strong practical evidence. Collapsing duplicates may be meant to avoid double
counting. Separate kernels can be argued for non-circularity, but the target puts independence in
reference data.

**Evidence:** diagnosed from source; divergence probe-confirmed by a contributor (scratch,
2026-10-29).

**Related:** the leverage review's [CBO-006](../../library_leverage/reviews/retirement-dependencies.md#cbo-006)
holds solution reasoning.

<a id="da-046"></a>

## DA-046 — The semantic core and generic code carry statistics and mathematical-text vocabulary

**Principles:** FP-04/A2 (model adequacy), DP-06, DP-01. **Subject:** implemented, judged against
DESIGN §1.3: "the core holds nothing statistics-specific" (Proposed).

### Diagnosis

- **The core model.**
  - `StatementKind` lists definition, theorem, lemma, corollary, proof, exercise, solution and
    assumption (`core.yaml:612-666`).
  - `SourceStatement.proves` (`:515-532`).
  - The binding kinds `family_param`, `param_of` and `param_expr_of` (`:259-290`).
  - LaTeX macro classes.
  - The modalities `exemplified` and `posed` (`:686-690`), and the statement role `example_value`.
  - The toy pack must inherit `StatementKind`, so its agent schema offers theorem and exercise
    (offline preparation).
- **Generic code.**
  - Serving resolves labels through the statistics slot `canonical_name` (`serve/read.py:296`).
  - Domain operations hard-code `"assumption"`, `{"premise","example_value"}` and formula-symbol
    logic (`semantic/domain_operations.py:3022, 3248`).
  - The mathematics-specific `cs:param_map` sits in the generic annotation allowlist
    (`semantic/prepare.py:95`) and in operation code (`:3019`).
  - Evaluation hard-codes `tex`/`latex` and the statistics value kinds
    (`evaluate/semantic_alignment.py:143-164`).

### Consequence

A second domain (business documents, email) inherits irrelevant kinds and behaviours, and must
borrow mathematical names to get behaviour ([DA-003](#da-003), scenario SC2).

### Counterevidence

Mathematical expressions can legitimately span domains, and statistics is the first corpus.

**Evidence:** diagnosed from source and offline preparation.

<a id="da-048"></a>

## DA-048 — Pack composition is a preparation-only product, and its operation inputs are out of every consumer's reach

**Principles:** FP-03, FP-04, DP-03, DP-05, DP-08, DP-19, DP-24; CI-10. **Subject:** implemented
(offline composition), judged against the target "any domain" (DESIGN §1.1, §1.3).

### Diagnosis

- **Composition namespaces each pack's inputs.** `prepare_packs` stores each pack's operation inputs
  as `pack/<name>/…` (`semantic/regeneration.py:74-79`). The comment says the namespacing is
  deliberate: "pack-scoped … not a merged executable graph" (`:73`).
- **Consumers address only root names.**
  - `operation/domain-rules.yaml`: `semantic/prepare.py:896-904`;
    `semantic/domain_operations.py:46, 826, 2303`.
  - `operation/slices.yaml` and `operation/evaluation-split.yaml`: `evaluate/semantic.py:166-196`.
  - Nothing reads the `pack/<name>/…` names.
- **The release is admitted without rules.** The rule-admission check runs only if the root rules
  artifact exists (`semantic/prepare.py:1101-1109`). Offline preparation of `statistics + toy`
  produced a release with no root `operation/domain-rules.yaml` — only the two prefixed copies — and
  admitted it cleanly.
- **Nothing downstream can run it.**
  - No composition-level owner exists for rules, aliases, slices, the split or plug-ins.
  - Runs and serving fix one domain per run (`ops.run.options.domain`; `cli/query.py:52-57`;
    `orchestrate/commands.py:117-161`).
  - No production path persists a composed release. `prepare_packs` is reachable only from the
    offline `ci schema compile` (`cli/schema.py:44-49`). The only `persist_release` caller is
    `ci regenerate`, which takes a single `--domain` (`cli/regenerate.py:30, 82`).

### Consequence

- A composed release refuses at its first consolidation: "release has no declared domain rules
  operation" (`semantic/domain_operations.py:2002, 2302-2306`).
- Before that, identity aliases are silently empty (`:826-827`) and the evaluation split silently
  falls back to defaults (`evaluate/semantic.py:166-177`).
- Together with [DA-026](#da-026), [DA-028](#da-028) and [DA-046](#da-046), the second-domain target
  has no runnable route (scenario SC2).

### Counterevidence

Composition was committed deliberately (`7491a01`), but no ADR records its semantics.

**Evidence:** diagnosed from source; offline preparation observed (W2-A, 2026-10-29). Footprint
known for rules, aliases, slices and the split. Suspected for source-profile addressing and for
class or slot name collisions between packs (not exercised).

<a id="da-049"></a>

## DA-049 — Archived releases and results have no declared compatibility lifetime: any stack or catalog change strands them

**Principles:** DP-24 (G2), DP-09, DP-19, DP-21; CI-13 (the lifetime of a pin is undeclared); FP-03;
heuristics H13, H14. **Subject:** implemented, judged against ADR-0024's "reproducible future
interpretation" and the completeness review's O01: "operations already bound to another release
retain their meaning".

### Diagnosis

Compatibility of an archived release with the running system is exact equality. Nothing classifies
what may change. Two mechanisms enforce it, one in Python and one natively.

**In Python, exact stack equality on every use.**
- `load_release` refuses unless all eleven listed library versions equal the archived strings
  (`semantic/releases.py:442-443`).
- It also refuses unless the semantic compiler version and the execution compiler version (through
  `execution_model_id`) are unchanged (`semantic/releases.py:446-452, 467-470`;
  `semantic/prepare.py:562-565`; `semantic/contracts.py:28, 677-685`).
- `load_release` gates thirteen call sites:
  - serving (`semantic/query.py:345`; `serve/journey.py:81`) and evaluation (`evaluate/semantic.py`,
    five sites);
  - run start (`orchestrate/commands.py:99`), project initialization, resumption
    (`cli/regenerate.py:115`) and consolidation (`semantic/domain_operations.py:705`);
  - source frames, the MCP server and activation (`semantic/releases.py:502`).

**Natively, exactly one execution model admitted.**
- The deployed descriptor carries one `model_id` and one `physical_id`.
- `require_execution_release` refuses any release whose execution model differs: "incompatible
  archived execution model" (`rev/semantic_0030_admission.sql:66`).
- It runs from triggers on realization, batch and project writes (`rev/semantic_0026_admission.sql:112,
  120, 127`; `rev/semantic_0029_reference_boundaries.sql:80`).

### Consequence

**A routine pinned-library bump** — any patch release of the eleven libraries, an ordinary change
under AGENTS.md — strands:
- every completed result, which can no longer be served or graded;
- every in-flight or archived run, which can no longer be resumed or finalized;
- activation.

Recovery is full regeneration, including paid agent re-extraction, because task reuse is keyed on
the release id (`semantic/operations.py:208-226`). `docs/pins.md` holds no row for any of the eleven
libraries, so nothing warns before a bump.

**A byte change to any execution catalog input**, once its descriptor is deployed, makes in-flight
runs on older releases unable to publish or finalize. The project can then select no completed
result of its current release. There is no drain or dual-admission window. Draft-0031 keeps
`model_id` unchanged, but a correction routed through the execution catalog would leave run 3
unrecoverable.

Meanwhile the real determinants (sympy, the Unicode tables) are not part of the comparison
([DA-009](#da-009)). Compatibility is therefore both stricter and looser than meaning requires.

### Counterevidence

- The refusal is deliberate and safe: archives are never reinterpreted.
- ADR-0024 accepts clean regeneration.
- The libraries are pinned exactly, so a bump is always a deliberate act.
- Reads still work after a catalog change, because `load_release` does not call native admission.

**Evidence:** diagnosed from source (W2-B scenario SC4, 2026-10-29). A catalog-change probe was not
run.
