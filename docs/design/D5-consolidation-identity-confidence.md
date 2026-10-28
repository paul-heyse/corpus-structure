# D5 · Consolidation, identity and confidence

**Proposed (2026-10-28).** How a run's observations become entities, claims and claim links
([D1 §4–§8](D1-knowledge-representation.md#4-entities)); how identity, fusion, alternatives and
conflicts are decided; how confidence is estimated and calibrated; how judgments and
validation set status. Consolidation is methods M17 and M18 of
[D4](D4-method-catalog.md#11-consolidation-summary) and the only writer of knowledge rows.

## 1. Shape

Consolidation is a **pure function** of: the run's effective observations
(`kb.run_observation`), the judgments that apply to the run (§7), the run's **reference run**
(for identity), the schema version and the policy version. The reference run is recorded on the
run when it is created, as the project's promoted run at that moment (`ops.run.reference_run_id`,
[D3 §4](D3-database.md#4-ops-methods-policies-runs-and-tasks)), and never changes; it is null at
bootstrap, before any run is promoted. Consolidation reads only it, never the live promoted
pointer, which may move while a run waits (P0CL-05; operator, 2026-10-28). Given the same inputs
it produces the same rows with the same keys, whatever order the queue was worked in.
> Status: **Proposed** (2026-10-28)

It runs in passes inside the stage graph ([D6 §2](D6-orchestration-metrics-policies.md#2-the-stage-graph-and-run-lifecycle)):

| Pass | Does | Writes |
|---|---|---|
| **Assemble** | Entity resolution (§3), symbol binding (§4), candidate claims, keys, fusion, alternatives (§5) | entities, aliases, anchors, claims with status `candidate` (or `unsupported`), evidence, supports |
| *check* (not consolidation) | M20 conditions (phase 2), M21 verifiers (phase 4): expensive checks, run as tasks on the candidate claims, keyed by claim key; no tasks in phases 0–1 | `verification` observations |
| **Finalize** | M19 rules over the in-memory pool, one run-level step (§8.1); then confidence (§6), judgments (§7), validation outcomes (§8), statuses (§10), claim links | M19's `verification` observations (bulk); claim `confidence`, `status`; `kb.claim_link` |
| *derive* | M23 on finalized claims | `claim_proposal` observations (derived) |
| **Assemble + finalize (incremental)** | Same steps restricted to derived proposals and the claims they touch (§9) | derived claims and links |

**Materialization.** Each pass rebuilds the run's knowledge rows in one transaction: delete the
run's entities, claims and links (cascade), insert the new set. Rebuilding is cheap at the
volumes of D3 §11 and removes a class of incremental-update bugs. Because keys are
deterministic, `verification` and `judgment` observations that target claim keys remain valid
across rebuilds. A finished run is never rebuilt.

**Code shape.** `consolidate/` builds an in-memory **evidence pool** (§2) from the database,
runs the steps as functions over it, and writes rows through one bulk writer. No step queries
the database directly, so steps are testable on fixtures built from the trace. The M19 runner and
the view builder live in `validate`, below `consolidate`, and consume the core keyed-candidate
claim type that the pool's candidates and submitted batches both adapt into (D9 §1, P0CL-08).

## 2. The evidence pool

What each observation kind contributes:

| Kind | Contributes to | Notes |
|---|---|---|
| `author_markup` | statement anchors and kind hints; `dfn` terms as concept mention candidates; containment relations the source profile declares (§3.5) | Markup is input; evaluation does not score what it supplies (D7 §6) |
| `mention` | entity candidates | Clustered by span (§3.1) |
| `attribute` | identity attributes or claims, as the schema declares | `ParameterRole` on a parameter mention becomes a `parameter_role` claim candidate |
| `record` | candidate claims for predicates with `ci:extract: record` | Field spans resolve to mention clusters |
| `relation` | **core** candidate claims (subject, predicate, object) | Encoders do not produce qualifiers or conditions |
| `classification` | statement kinds; sentence modality; polarity, hedge, attribution cues | Applied to candidate claims by evidence sentence |
| `value` | object values for candidates whose object span matches; parsed formulas for LLM values | M11 is also called directly on LaTeX inside proposals |
| `scope` | local entity scopes; symbol binding sites | §3.4, §4 |
| `link` | identity decisions for global entities; pairwise merges | §3.3, §3.6 |
| `claim_proposal` | **full** candidate claims, entities and statements | From M10, M24, M23 |
| `judgment` | overrides (agent, human) or confidence sources (local LLM) | §7 |
| `verification` | validation outcomes and confidence sources | §8 |

Every pool element keeps its observation id, so every row written can list its supports
(`kb.claim_support`, `kb.entity_mention`).

## 3. Entity resolution

### 3.1 Mention clusters

Mentions from different methods that denote the same text occurrence are clustered first:
two mentions of compatible types join a cluster when their spans overlap with intersection over
union ≥ 0.5, or one contains the other and they share the head token (spaCy head of the longer
span). Inside math, mentions cluster by math segment and symbol. A cluster's type is the
highest-confidence type among its members, weighting each method by its measured precision for
that type once goldens exist (equal weights before). Entities named by LLM proposals join the
cluster their located evidence span falls in; a proposal entity without located evidence forms
its own cluster anchored to its unit.

### 3.2 Which class, which scope

The cluster's class decides its scope (`ci:scope`, D2 §3.1): global classes go to §3.3, local
classes to §3.4, `Statement` to §3.5.

### 3.3 Global entities

1. **Identity attributes.** For classes with `ci:identity_keys`, identity attributes come from
   attribute observations, record fields or proposal `identity` fields; the canonical label is
   derived from them (for `DistributionFamily`, the normalized family name: "normal").
2. **Linking.** M14's `link` observations rank candidate entities of the run's recorded
   reference run (§1; D4 M14). A cluster takes the top candidate when its score is at least the
   accept threshold and beats the runner-up by the margin; it proposes a new entity when the best
   score is below the new-entity threshold; otherwise it is in the **identity grey zone** and
   forms an identity group (§3.7). New entities proposed for the same identity in different units
   of this run meet here, by key (point 3), so no method reads this run's earlier proposals.
3. **Keys.** `ent:` over type, identity attributes and normalized canonical label (D1 §10.1).
   A key is computed only when an entity is first created; linking to an existing entity
   reuses its key, so keys stay stable across runs while the entity's identity is unchanged.
   Until the phase 2 identity gate, linking does **not** reuse the reference run's canonical
   label: the label is chosen afresh in each run by point 4, so a label chosen at bootstrap does
   not persist through promotion before identity is measured (P0CL-10; operator, 2026-10-28).
   From the phase 2 gate, linking reuses key and canonical label.
   > Status: **Proposed** (2026-10-28)
4. **Canonical label.** The identity-derived label when the class declares identity keys;
   otherwise the most frequent normalized surface form among mentions with score ≥ 0.8,
   preferring a `dfn` term or a page title. Ties break lexicographically, so the choice is
   deterministic.
5. **Label normalization** (for matching, and for labels of classes without identity keys):
   NFC, casefold, collapsed whitespace, leading articles removed, the class's head words removed
   and its adverb rules applied (`methods.yaml`: "normally distributed" → "normal"). In phase 0,
   without M14, clusters of one type with equal normalized labels are one entity.

### 3.4 Local entities

A local entity is identified by `(type, scope locator, normalized symbol or label)` (D1 §10.1):
the scope is named by the locator of its segment
([D1 §3.4](D1-knowledge-representation.md#34-locators)), not by the segment key, so an edit
elsewhere on the page that shifts offsets leaves the key unchanged (P0CL-01; operator,
2026-10-28). The scope segment is the extent of the binding site that M13 assigned to the
cluster's symbol mention; a mention with `binding: unresolved` takes its unit (or paragraph
outside units) as scope and is flagged so the gap is measured. LLM proposal entities marked
`local` take the scope of the M13 scope observation at their located evidence; without M13
output (phase 0), the proposal's `extent` (D2 §7.3): the anchor of their statement, or the
enclosing section.

`Y = a + bX` style variables (T3) are local entities whose label is the defining expression and
whose symbol is the one the source introduces, if any; their `defined_as` claim carries the
formula.

### 3.5 Statements

Statements are identified as D1 §10.1 keys them: the locator of the anchor segment (the `unit`
for a statement inside a unit, each `details` block, a paragraph outside units), in the
structured form of [D1 §3.4](D1-knowledge-representation.md#34-locators) that carries the
document key, and the ordinal of the statement's first sentence within the anchor. The anchor is
named by locator, not by segment key, so statement keys survive a content edit elsewhere on the
page (P0CL-01). A segment holds one statement by default. It holds several when
proposals or goldens split it by kind, as guideline §10.3 does for a unit that mixes kinds ("A
corollary of …", "Recall that …"). A context-premise `assumption` statement (D2 §7.3) whose
sentences lie inside another statement's anchor segment joins that statement; its claims become
that statement's claims. Each `details` block is kind `proof` or `solution` by its summary text
and markup. A paragraph outside units holds a statement when a claim proposal or a claim-bearing
classification places one there. Kind: author-markup hint
(highest weight), M05 classification, proposal `kind`, in that order of precedence until the
confidence model learns weights. Markup hints are skipped when the consolidation configuration
sets `use_markup_hints: false` (witness ablations, D7 §6). The label is `<kind> <unit id>`, `<kind>
unit <n>` for a unit without an id, else `<kind> ¶<n>` (D2 §6); kind and label are not identity.

**Relations implied by containment** are declared by the source profile
(`details_kinds.synthesize`, [D4 M01](D4-method-catalog.md#m01-ingesthtml); D2 §12.1), never by
consolidation code: M01 records the declared claim on the block's `author_markup` observation, so
consolidation stays a function of observations (§1), and turns it into a claim between the two
statements, with `establishment: stated` and the declared evidence span. Siegrist's profile
declares that a `proof` or `solution` block inside a unit yields `<block statement> core:proves
unit-statement`, with the `details` summary span as evidence; a source without the convention
declares nothing (P0CL-07; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

### 3.6 Merges and cannot-links

After §3.3–§3.5, pairwise evidence can merge entities of the same class:

- **Must-link**: M15 pairs with match probability ≥ the merge threshold; agent or human
  `merge` judgments.
- **Cannot-link**: different identity attributes where the schema declares them identifying;
  local entities with different scopes; agent or human `split` judgments.

Merging is union-find over must-links that refuses any union joining a cannot-linked pair; a
refused union is recorded as an identity conflict (counted, and routed by policy). Splits
override earlier merges because judgments are applied before merges are computed.

### 3.7 Identity alternatives

A grey-zone cluster produces an identity group: the candidate entities with their
scores. Until a judgment resolves it, the cluster links to the top candidate (so claims are not
lost) and the group is listed for routing (`identity_grey_zone` metric, D6 §6). Judges see the
mention in context, both candidates' labels, aliases and three of their claims.

### 3.8 Aliases, anchors, confidence

Aliases: every member mention's normalized text, with kind `symbol` for math mentions, `term`
for `dfn` terms, `label` otherwise. Anchors: the scope segment for local entities, anchor
segments for statements. Entity confidence: the noisy-OR of member mention scores, times the
link score when linked; it is reported, and claims do not inherit it (claim confidence is
estimated on claims, §6).

## 4. Symbol binding

Every formula or set value in a candidate claim (objects, `param_values`, condition leaves) gets
its binding map (D1 §6.1). The rules are the guideline's (D2 §10.7), so the pipeline produces
what the goldens encode. For each symbol, find its **first appearance** in the unit or its
standing context, from M09's symbol occurrences, and take the first rule that applies:

1. **Variable** if M13's binding site for the mention is a mention in a cluster resolved to a
   local entity: `{"bind": "variable", "entity": key}`.
2. **Family parameter, in a family-structure claim** (a predicate in the pack's
   `family_structure` subset; statistics: `has_parameter`, `parameter_domain`, `parameter_role`,
   `derived_parameter`, `identical_parameter`, `construction_formula`, `transformation_of`,
   `special_case_of`), if the symbol is an alias of an entity of a class the pack marks
   `ci:parameter_class` (statistics: `FamilyParameter`) whose named identity slot holds the
   entity the claim is about.
3. **Parameter of a claim** if the first appearance lies inside an entry of the map qualifier
   that another claim's predicate names by `ci:param_map` (statistics: `param_values` of
   `has_distribution`): `param_of` when the entry's value is exactly the symbol (`\mu` for
   mean), `param_expr_of` when the symbol occurs inside it (`\sigma` in `\sigma^2`), with `claim`
   and `param`, the entry's name.
4. **Family parameter** if the unit names the symbol a parameter of an entity it defines or
   describes (an alias of a `ci:parameter_class` entity belonging to it) and rule 3 does not
   apply.
5. **Free** if the symbol is introduced in this claim's value, by a restriction ("If c ∈ (0, ∞)"),
   as an index, or as a dummy variable bound inside the formula.
6. **Constant** if it is a known constant (`e`, `\pi`, and those in the pack's macro map); such
   symbols are never introduced, so rules 1–5 do not catch them.
7. Otherwise **unresolved**, counted in the claim's `completeness.unresolved_symbols`.

Bindings are part of the value, not of the claim key (D1 §6.2 keys formulas by their token form),
so improving binding does not change claim identity.

The rules read the predicates, qualifier and class they need from pack declarations
([D2 §3](D2-schema-and-guidelines.md#3-the-ci-annotation-vocabulary)), so consolidation names no
domain predicate and a second domain pack binds through its own declarations (P0CL-07; operator,
2026-10-28).

> Status: **Proposed** (2026-10-28). It restates guideline v1's binding table, which is Tested on
> annotators (S0-R2, binding accuracy 0.94 for Sonnet). The earlier order made T1's `a` and `b`
> `free`, where guideline v1 and the trace make them `family_param`. Reading the rules' predicates
> from pack declarations is Proposed (2026-10-28) and not yet exercised by a second pack

## 5. Claims

### 5.1 Candidates

| Source | Candidate |
|---|---|
| Proposal claim (M10, M24, M23) | **Full**: subject, predicate, object, qualifiers, conditions, statement and role, evidence. Local refs resolve to the entities of §3; condition `claim` refs resolve to the keys of the same batch's claims |
| Record (M06) | **Core plus fields**: the claim the record maps to, with qualifiers the record carries (for example `param_values` names without values) |
| Relation (M07, M08) | **Core**: subject and object from the head and tail clusters; qualifiers from classifications of the evidence sentence (modality from M05, polarity, hedge and attribution from M22); no conditions |
| Attribute (M06) | **Core**, for attributes the schema maps to claims |
| Unsupported item of a proposal | Predicate `core:unschematized`, subject the statement whose anchor holds the item (a paragraph outside units becomes a `narrative` statement for this, §3.5), object a `phrase` value; status `unsupported` |

Statement and role for core candidates: the statement whose anchor contains the evidence
sentence; role from the sentence's modality (`supposed` → premise, `defined` → definiens,
asserted in a theorem → conclusion), else none.

### 5.2 Normalization and keys

Qualifier defaults are dropped (`modality: asserted`, `polarity: positive`); values take their
canonical form (D1 §6.2); condition trees are canonicalized (flatten nested `and`/`or`, sort
arguments by canonical JSON, replace claim refs by keys). Formula and set values enter keys in their normalized LaTeX form (D1 §6.2), never their SymPy
form. Keys are computed in dependency order:
a claim's key depends on the keys of claims its conditions reference, so candidates are keyed in
a topological order of condition references; a reference cycle is malformed and both candidates
are dropped with a reason (counted).

### 5.3 Fusion

Candidates with the same key are one claim: supports, evidence spans and source votes are
unioned. This is how a statement found by the local LLM and by Opus, or on two pages under
identical meaning and statement, becomes one claim with two independent supports. The key's
identity qualifiers include `valid_time` and, under modality `cited`, the attributed source entity
([D1 §10.1](D1-knowledge-representation.md#101-hashing)), so "ORG-101 owns P-17" stated for two
intervals in one table statement stays two claims, and one fact reported from two sources stays
two claims (P0CL-06; operator, 2026-10-28).

**Disagreeing qualifiers are not fused.** Full candidates (§5.1) with equal keys that disagree on
a meaning-bearing qualifier outside the key (`hedge`, `scope`, attribution phrasing) are kept
apart as an alternative group (§5.4 point 3, `alternative_of` links), because fusing them would
keep one reading and drop the other without a record. A qualifier one candidate leaves null and
the other sets counts as a disagreement. Claim keys are unique within a run (D3 `kb.claim`), so
each member is keyed by the claim's key parts plus its own canonical values of the disagreeing
qualifiers; the group key is the hash of the sorted member keys, as for every group. Core
candidates carry no reading of their own and fuse as supports (§5.4 point 1) (P0CL-06; operator,
2026-10-28).
> Status: **Proposed** (2026-10-28); the member key extends D1 §10.1's claim parts for this case
> only

Candidates in the same slot (§5.4) whose keys differ only in formula or set values that M11
proves equivalent (`simplify(a - b) == 0`; set equality) are fused too, under the same
disagreement rule; the fused claim takes the smallest of their keys, which keeps the choice
deterministic.

### 5.4 Slots: core support, refinements and alternatives

A **slot** groups candidates that answer the same question:

- for predicates with `ci:functional: true` (one object per subject): `(subject, predicate,
  statement, valid_time, cited source)`, the cited source being the attributed entity under
  modality `cited`, because one object per subject holds per validity interval and per reporting
  source; candidates that differ there are two facts, not two readings (P0CL-06);
- otherwise: `(subject, predicate, canonical object core, statement)`, where the object core is
  the entity key or the value's canonical form without qualifiers.

Within a slot:

1. **Core candidates are absorbed.** A core candidate (relation, attribute) in a slot that also
   has a full candidate with the same core does not become a claim; its observation becomes a
   core support of every full candidate with that core. A core candidate alone in its slot
   becomes a claim with `completeness.qualifiers_from: "encoder"`.
2. **Refinements.** When one full candidate's qualifiers strictly extend another's (it adds
   conditions or `param_values` entries and agrees on the rest), the more specific claim is kept
   and the other contributes its supports to it, unless the other has an independent primary
   evidence span elsewhere (then both are kept with a `refines` link).
3. **Alternatives.** Remaining full candidates with different keys, and the candidates §5.3 keeps
   apart, form an **alternative group** (`alternative_of` links; group key = hash of the sorted
   member keys). Members are `ambiguous`
   until a judgment resolves the group (§7) or, when the policy enables it, the top member's
   confidence exceeds the next by the auto-resolution margin (then the others are `rejected`
   with reason `alternative_lost`, counted separately from adjudicated rejections).

Derived claims (`establishment: derived`) never enter a slot: they neither compete with nor
absorb the claims they were derived from, and are assessed on their own (§9).

Slots are the mechanism that decides between "two readings of one sentence" and "two facts":
only candidates for the same question compete.

### 5.5 Equivalence and conflict across statements

- **Equivalence.** Claims whose keys differ only in `statement` share a *meaning key* (the key
  computed without `statement`). They are linked `equivalent_to`. This is how the same fact
  stated on two pages is counted once by queries that ask for facts, not occurrences. Whether
  the meaning key is stored is `OPEN-D3-4`.
- **Conflict.** Two claims with the same subject and a functional predicate, positive polarity,
  modality `asserted` or `defined`, different objects, overlapping validity (`valid_time`
  intervals that intersect, or either null), and conditions that can hold together are linked
  `contradicts`. Without M20, "can hold together" is approximated by identical
  canonical conditions; with M20, by satisfiability of the conjunction. The later-finalized
  claim of a contradicting pair with an accepted partner gets status `conflicting`; both are
  kept. Local subjects rarely conflict (different theorems have different `X`); global ones do
  (the mean of the gamma family under shape–scale versus shape–rate parameterizations, which the
  schema separates by `param_values` keys, so a real conflict signals a binding or parameter
  role error).

### 5.6 Evidence

A proposal's evidence is located on the run's own rendition: the proposal keeps its model-facing
batch and citation frame as the authority, and the stored form consolidation reads is derived per
rendition by the production quote cascade ([D4 §4.3](D4-method-catalog.md#43-output-form-and-post-processing)),
so a proposal reused from another run never cites spans of a rendition this run did not select
(P0CL-03). Every evidence item from a proposal with a located quote becomes a span with its role. An
unlocated quote falls back to the cited sentence's span with role `primary` and
`evidence_coarse: true` in the claim's `completeness`; without a cited sentence the item is
dropped as malformed (counted). This keeps INV-01 without inventing precision.

## 6. Confidence

### 6.1 Meaning

A claim's confidence estimates the probability that an adjudicated golden annotation under the
current guideline would contain the claim (aligned at the full tier, D7 §5). It is calibrated on
the dev split and reported with its calibration error; it is not a probability that the claim is
true in the world. Statuses use thresholds per **predicate group** (the predicate's `ci:group`, D2 §3.2; default
the predicate itself) from the policy (default accept
at 0.8).

### 6.2 Sources

Each claim has one discrete observation per **source** that could have produced or checked it:

| Source | States |
|---|---|
| Encoders (M06 and M07 together, one source, because they share an encoder) | `supports`, `silent`, `not_run` |
| Patterns (M08) | as above |
| Local LLM proposal (M10) | `supports_full`, `supports_core` (same core, different qualifiers), `silent`, `not_run` |
| Agent proposal (M24 extract) | as M10 |
| Local LLM judge (M16) | `accept`, `reject`, `unsure`, `not_run` |
| Rule validation (M19) | `pass`, `warning`, `not_applicable` |
| Verifiers (M20, M21) | `consistent`, `refuted`, `not_checkable` |
| Author markup agreement | `agrees`, `disagrees`, `none` (for statement kinds and `dfn` terms) |

`silent` (the method ran on the claim's unit and did not produce it) is different from
`not_run` (no task of that source on the unit), and `not_run` is treated as unobserved. This is
the reason D4 rule 2 records `empty` outcomes.

### 6.3 Cold start (phases 0–1)

Before enough goldens exist (fewer than 30 aligned claims per predicate group), confidence is a
fixed-weight noisy-OR over supporting sources with per-source priors from the policy's `priors:` block (D6 §7.1; defaults agent 0.9,
local LLM full 0.6, core 0.4, encoders 0.4, patterns 0.5), multiplied by 0.7 per rule warning,
by 0.2 for a `refuted` verification, and capped at 0.5 for claims with
`completeness.evidence_coarse` or more than one unresolved symbol. These numbers are policy
data, not code.

### 6.4 Latent-truth model (phase 2 onward)

A Dawid–Skene style Bayesian network per predicate group: a latent binary variable `T` (the
claim is in the golden) with every source variable of §6.2 as a child, `P(source | T)` a
conditional table per source configuration.

- **Model.** `pgmpy` `DiscreteBayesianNetwork` with edges `T → S_i`. Sources known to be
  correlated beyond `T` (an LLM proposal made with encoder hints) get an edge between them, or
  are merged into one compound source.
- **Fitting.** Claims aligned with dev-split goldens have `T` observed. Their tables are fitted
  with `DiscreteBayesianEstimator` (Dirichlet prior, equivalent sample size 10) and used as the
  prior for `DiscreteEM` over all claims of the run with `T` latent. Tables are shared across
  predicates of a group and specialized per predicate only when that predicate has ≥ 100
  aligned claims.
- **Inference.** `VariableElimination` gives `P(T = 1 | sources)` per claim. The network is
  small, so exact inference over the run is fast; claims with identical source vectors share a
  query.
- **Calibration.** Reliability diagram and expected calibration error on dev-split claims
  (cross-fitted: tables fitted without the fold being scored). If ECE > 0.05, an isotonic map
  (scikit-learn `IsotonicRegression`) is fitted on the dev predictions and applied.
- **Products.** Besides claim confidence, the fitted tables give each method's measured
  sensitivity and false-positive rate per predicate group. These are what escalation policies
  and phase 3 de-escalation use (D6 §7).

The test split never contributes to fitting or calibration (D7 §4).

## 7. Applying judgments

### 7.1 Who decides

| Precedence | Judgments | Effect |
|---|---|---|
| 1 | Hard validation errors (§8) | `rejected`, regardless of judgments below; a contradicting agent `accept` is reported as a rule–judgment disagreement for the outer loop |
| 2 | Human judgments (rare; the operator steers mainly through guidelines) | Override |
| 3 | Agent adjudication (M24 `adjudicate`) | Override |
| 4 | Policy and confidence (§6, §10) | Default |

Local LLM judgments (M16) are a confidence source, never an override: using them as both would
count them twice.

### 7.2 Decisions

| Decision | On | Effect |
|---|---|---|
| `accept` | claim | `accepted`, unless precedence 1 |
| `reject` | claim | `rejected` |
| `choose` | alternative group | Chosen members leave the group; others `rejected`. Several chosen with `faithful: true` keeps them `ambiguous` as a faithful ambiguity, closed to further routing |
| `merge`, `split` | entity pair or identity group | Must-link or cannot-link in §3.6 |
| `unsure` | any | No effect on status; the target stays routable to the next tier |

### 7.3 Carrying judgments across runs

Judgments target observation ids, claim keys, entity keys or alternative-group keys, and record
the guideline version they were made under. In every later run they apply when the target
exists. A target that no longer exists makes the judgment **orphaned**: reported in the run
summary with its target and never silently dropped. An alternative group whose membership
changed (a new reading appeared) makes its judgment **stale**: the chosen member keeps its
status if still present, and the group is routed again. When the guideline changes, judgments
stay in force until the outer loop marks them for re-adjudication (D7 §8).

## 8. Validation

### 8.1 Order

Rules (M19) run inside the finalize pass: one run-level step over the in-memory pool, after
assembly and before confidence, that bulk-writes its `verification` observations as one M19 task
per pass ([D4 M19](D4-method-catalog.md#m19-validaterules)). Per-claim tasks would cost more in
task, digest and transaction machinery than the microseconds of rule evaluation, and caching
them saves nothing because every pass rebuilds (P0CL-13; operator, 2026-10-28). The incremental
pass (§9) runs M19 over the claims it assembles. Condition checks (M20) and verifiers (M21) are
expensive and stay separate tasks, run between assemble and finalize on candidate claims by
claim key. Finalize reads all of them:

| Outcome | Effect |
|---|---|
| Rule `error` fails | `rejected`, reason the rule id (precedence 1, §7.1) |
| Rule `warning` fails | Confidence source state `warning` |
| z3: conditions unsatisfiable | `rejected`, reason `unsatisfiable_conditions` |
| z3: overlapping conditions with a different object | `contradicts` link (§5.5) |
| z3: one claim's conditions imply another's, same object | `refines` link |
| Verifier `refuted` | Confidence source state `refuted`; routed to a judge by policy |
| Verifier `consistent` | Confidence source state `consistent` |
| `not_checkable`, `not_applicable` | Nothing; counted as verification coverage |

### 8.2 Rule context

Rules are rule-engine expressions compiled under a typed context whose resolver is generated
from the schema version (D2 §7.4). **Two call sites, one rule** (design authority, 2026-10-28,
from the [schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-04, L-05): rules run at batch submission (M24, golden
passes, M10) over the batch's own items, and at finalize over the run's candidate claims inside
the consolidation pass (§8.1). A view builder presents both as the same claim view over the core
keyed-candidate type, so one compiled rule serves both; each rule's `at:` names where it runs
(`family_params` is incomplete at submission, for example).

**Readers per call site.** At submission the view reads formula symbols with `core/tex.py`'s TeX
tokenizer ([D1 §6.2](D1-knowledge-representation.md#62-canonical-form)), which is total and fast,
and never the math grammar, because the submission runs in an MCP worker thread where the
grammar's timeout cannot fire. A rule that needs the grammar's parse (slot typing, structure of
sub- and superscripts) declares `at: [finalize]`, where M11's values are in the pool (P0CL-14;
operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

Symbols available to `when` and `check`:

| Symbol | Type | Content |
|---|---|---|
| `claim.id` | string | the local ref at submission, the claim key at finalize |
| `claim.key` | string or null | null at submission |
| `claim.predicate` | string | |
| `claim.subject`, `claim.object` | mapping | `key`, `type`, `label`; `object` is null for value objects |
| `claim.value` | mapping | the D1 value for value objects (`t`, and `latex`/`v`) |
| `claim.qualifiers` | mapping | qualifiers with defaults filled in |
| `claim.statement` | mapping or null | `key`, `kind` |
| `claim.statement_role`, `claim.establishment` | string | |
| `claim.evidence_count`, `claim.unresolved_symbols` | integer | |

Facts about the claim pool are **cached attributes of the view**, computed once per claim by the
view builder (OPEN-D2-3, answered 2026-10-28). The generic builder computes the domain-free ones:
flattened condition nodes, statement premises and the "given as a parameter value elsewhere" map
(over the pack's `ci:param_map` qualifiers, §4). Domain facts are pack data: `rules.yaml`'s
declarative `views:` section ([D2 §7.4](D2-schema-and-guidelines.md#74-to-rule-engine-rules))
names, for each projected field, a source predicate, a match and the field projected, and the
generic builder compiles it, so a second domain's cross-claim rule needs no Python in the builder
(P0CL-07; operator, 2026-10-28). Statistics declares `claim.family_params` there: canonical
names from `has_parameter` claims of the family, any status except `rejected`; at submission
only those in the batch, which is why rules reading it run `at: [finalize]`. Registered functions
remain for parameterized lookups: `claims_of(id, predicate)`, `is_a(type, class)` (schema
inheritance), `value_type(v)`. Neither reads the database during evaluation; the view builder
reads the pool once.
> Status: **Proposed** (2026-10-28): the `views:` section is not yet built or probed

### 8.3 Invariants

INV-01 to INV-10 (D1 §11) are asserted when rows are written. A violation fails the
consolidation task with the offending keys; it is a bug, never a claim status.

## 9. Derived claims

M23's proposals enter an incremental assemble and finalize (§1). A derived claim:

- has `establishment: derived`, `derived_from` links to its sources and the rule id in the link
  detail;
- has the conditions guideline §10.7 gives a claim of its predicate, built from its sources'
  conditions: a derived formula or family-structure claim keeps only the restrictions on its own
  symbols and no `claim` nodes (rule 2); any other derived claim has the conjunction of its
  sources' conditions (rule 3);
- is `accepted` when every source is `accepted` and validation passes; `candidate` otherwise;
  confidence is the product of its sources' confidences;
- becomes `rejected` (reason `source_rejected`) when a source is rejected at a later finalize.

Derived claims are excluded from golden precision denominators (the guideline tells annotators
not to state derived facts, D2 §10.7) and scored separately for correctness (D7 §5).

## 10. Status assignment

Finalize assigns each claim the first status that applies:

1. `rejected` by a hard validation error or unsatisfiable conditions;
2. the status set by a human or agent judgment;
3. `unsupported` for `core:unschematized` claims;
4. `ambiguous` for members of an unresolved alternative group;
5. `rejected` with reason `alternative_lost` for auto-resolved alternatives;
6. `conflicting` when linked by `contradicts` to an accepted claim;
7. `accepted` when confidence ≥ the predicate group's threshold;
8. `candidate`.

## 11. By phase

| Phase | Realization |
|---|---|
| 0 | Proposals from M24 only, for the units of the run's scope (the `phase0-golden` slice, D6 §7.4). Reference run: null until the first promotion, so every entity is new; once one exists, linking reuses its keys but not its canonical labels (§3.3 point 3). Entities: identity by type and normalized label (§3.3 point 5); local scopes from the proposals' `extent`, keyed by its locator (§3.4), not M13. Bindings as the proposals state them (local refs resolved to keys; §4 does not run). Statements: keyed by anchor locator and first-sentence ordinal (§3.5); kind from author markup, else the proposal's `kind` (M05 is phase 1); containment relations from the source profile's `details_kinds.synthesize` (§3.5). Claims: §5.1–§5.2 and §5.6, evidence located on the run's rendition from each proposal's citation frame; fusion by canonical form only, with `valid_time` and the cited source in the key and candidates that disagree on a meaning-bearing qualifier kept apart as alternatives (§5.3; SymPy equivalence is phase 1). A batch's `alternatives[]` keep every member claim with status `ambiguous` and `alternative_of` links; nothing resolves them until adjudication (phase 1). Status: M19 rules, run inside the finalize pass (§8.1; no `check` tasks); agent proposals `accepted` unless a rule error; no agent judgments. No derived claims (trace T3 D1 is phase 2) |
| 1 | Encoder and local LLM candidates; slots and alternatives (§5.4); M13 scopes; M14 linking against the recorded reference run; cold-start confidence (§6.3) |
| 2 | Latent-truth confidence and calibration (§6.4); M15 merges; M20 conflicts (the first `check` tasks); derived claims (§9); from the identity gate, linking reuses canonical labels too (§3.3 point 3) |
| 4 | Verifiers as confidence sources |

## 12. The trace through consolidation (T3, phase 1)

Observations on unit `rel1`: M06 mentions `X` (×3, math), "normally distributed" (×2), "mean",
"variance"; M07 relations `has_distribution(X, normally distributed)` and `has_distribution(a +
b X, normally distributed)`; M09 symbols and `in_set(a, \R)`, `in_set(b, \R \setminus \{0\})`;
M13 binds `X`, `a`, `b`, `\mu`, `\sigma` to the unit; M10 proposes C1–C4.

- §3: "normally distributed" links to `ent:normal` (lemma rule, M14); `X` and `a + bX` become
  local `RandomVariable`s `ent:X@rel1`, `ent:Y@rel1`; the unit becomes `stm:rel1` (kind
  `theorem` from the `p.math` block class, agreeing with M05), the `details` block `stm:rel1-proof`
  with `proves`, as the Siegrist profile's `details_kinds.synthesize` declares (§3.5).
- §4: in C3, `\mu` binds `param_of C1 mean`; `\sigma` `param_expr_of C1 variance`; `a`, `b`
  `free` (restricted by C3's conditions).
- §5: both M07 relations are core candidates in the slots of C1 and C3 and are absorbed as core
  supports; C1–C4 are full candidates with distinct keys; no alternatives.
- §6 (cold start): C3 has sources local LLM `supports_full`, encoders `supports`; noisy-OR
  1 − 0.4 × 0.6 = 0.76 → `candidate` at threshold 0.8; with M21 `affine_normal` `consistent`
  (phase 4) or an agent `accept`, it becomes `accepted`.
- §9: M23 derives D1 (standard deviation `|b| \sigma`) from C3, `derived_from C3`.

## 13. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D5-1 | Is the slot definition (§5.4) right for non-functional predicates with formula objects (two `pdf` claims for one family in one statement)? | S0 reference annotations; phase 1 alternative-group review; not exercised by the S0 core units (2026-10-28: no unit states one formula predicate twice for a subject) |
| OPEN-D5-2 | Minimum aligned claims per predicate group before the latent-truth model replaces cold-start weights, and which sources must be merged for conditional independence | Phase 2 calibration experiment |
| OPEN-D5-3 | Default auto-resolution margin for alternatives, and whether it should exist before calibration | Phase 2 |
| OPEN-D5-4 | Mention-cluster overlap rule (IoU 0.5 or head sharing) on math-adjacent mentions such as "normally distributed with mean \(\mu\)" | Spike S2 |
