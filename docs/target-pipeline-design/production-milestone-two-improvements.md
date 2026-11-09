## Overall assessment

**The implementation has made substantial progress. I would keep the current model set and concentrate the next increment on turning its existing observations into better connected, more precisely assessed structures.** Several of the latest failures occur after the relevant span, antecedent, predicate, or definition has already been found. Those cases now give you concrete opportunities to improve role assignment, contextual representation, and composition.

I reviewed the repository at **[`e55bcfc`](https://github.com/paul-heyse/corpus-structure/commit/e55bcfc546c65dd5c3261414f79b618c71c8903b)** and confirmed that it remained the latest commit at the end of the review. The review covered extraction, source alignment, contribution assembly, the four M2 integrations, retrieval, evaluation, probabilistic consumers, and execution. I inspected retained results and representative raw records; I did not rerun model inference or training.

I also reviewed the complete GLiNER attachment, including its supplement. It is identical to the current repository’s GLiNER guide, and the November 9 GLiNER/spaCy review already incorporates many of its capabilities. Consequently, some recommendations below concern completing accepted work, while others identify specific implementation gaps or refinements beyond that review. [Existing review](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md)

The highest priorities are:

1. **Use already successful parser outputs more directly in structural composition.**
2. **Repair two gaps in question-level and comparison-level evaluation visibility.**
3. **Diagnose GLiNER losses separately at proposal, role scoring, decoding, and record assignment.**
4. **Improve d1’s task-specific inputs and the information retained in contextual queries.**
5. **Run more discriminating structural comparisons before selecting additional modes or training models.**

## 1. What the latest results actually demonstrate

The distinction between a successful execution path and an improved semantic result is particularly important here. The repository generally records that distinction carefully.

| Area | Latest demonstrated result | What remains open |
|---|---|---|
| **Public condition statement** | The p289 assumption passed native admission at **run 477/cut 594**. Reader, CLI, fresh MCP, and detached verification returned the same result. | This establishes one complete publication journey from retained M1 evidence. It does not establish a four-model M2 improvement across the corpus. |
| **HanLP definition composition** | The repaired binomial declaration chain completed through native HanLP and the declaration producer, with private target custody and detached verification. | Independent semantic qualification and broader applicability remain separate questions. |
| **d1 interpretation** | The revised comparison recovered exact **`1/8 → 0.125`**, while preserving the supported definition classification. | The roulette quantity, condition-host choice, and `She → A gambler` choice remained unsupported. |
| **Competitive retrieval** | Three positive definitions ranked first in both literal and Dipo-enriched arms; the negative control remained unlinked. | There was no incremental gain. Eight eligible targets cannot meaningfully test top-10 recall. |
| **GLiNER diagnostics** | Six windows produced inspectable candidate pools; 19 of 24 supplied spans were scoreable, with exact score agreement on 126 shared query/span pairs. | No ordinary definition attachment decoded. Several required endpoints were already in the pool. |
| **Discourse analysis** | The Dipo comparisons distinguish segmentation, tree topology, nuclearity, relation, and selected context. | Correct boundaries do not consistently imply correct discourse placement. |

Sources: [public condition](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-public-condition/README.md), [native definition](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-native-definition/README.md), [interpretation comparison](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-interpretation-pair/README.md), [retrieval comparison](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-adoption-preflight/README.md), [GLiNER diagnostics](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-gliner-boundary/README.md).

Two results are especially informative:

- **Maverick already clusters “A gambler,” “She,” and “her,”** but the later d1 referent decision fails even when the correct candidate is explicitly supplied.
- **HanLP already nominates the fair-coin assignment predicate as the condition host,** but d1 still returns no match with the reviewed host available.

These localize the remaining problem to interpretation or consumption in those cases. They do not indicate that the corpus needs another coreference or syntactic parser. [Parser results](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-08_pm2-parsers/README.md)

There are also architectural strengths worth preserving:

- Exact source locations and original observations survive later transformations.
- Native labels remain distinguishable from normalized interpretations.
- Independent local GLiNER fields are retained even when a complete record cannot be assembled.
- Runtime limits, empty results, failures, and unexamined scope remain distinguishable.
- Native verification and detached replay provide unusually strong evidence that a delivered statement is the statement that was actually derived.

The current status remains appropriately conservative: full-book qualification and eligible fit/calibration populations are still open. [Current status](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/STATUS.md)

## 2. Two concrete implementation changes I would make first

### 2.1 Preserve typed outcomes for every attempted d1 question

There is a specific inconsistency in the current result path:

- `pm2_native.py` marks a request **`empty`** when every text/number/date answer lacks a span.
- `pm2_result.py` creates interpretation products only for **`succeeded`** requests.
- `pm2_interpretation_products.py` already supports a missing answer as **`state="unresolved"`**.

Consequently, the same missing answer produces a typed unresolved contribution when another question succeeds, but produces no such contribution when every question is missing. The raw answers remain retained; the missing information is in the typed question-level view. [Native execution](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/pm2_native.py), [result projection](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/pm2_result.py)

**Change:** validate and project question outcomes for valid completed `empty` d1 replies as well as successful replies. Retain:

- Question identity and assessed source scope.
- Native `found` value.
- Unresolved state.
- Absence of an answer span.

Keep the operation outcome `empty`. No source occurrence should be fabricated.

**Verification:** put the same absent read into an all-empty request and a mixed successful request. Its typed outcome and attempted-question accounting should agree.

This is a small change with direct value for the granular assessment you want.

### 2.2 Make persistent semantic failures visible in comparison summaries

`compare_assessments()` categorizes `unsupported → unsupported` as `unchanged`. Its `still_unresolved` category covers `ambiguous` or `unassessed`.

That transition definition is defensible, but the resulting summary can conceal the current condition. The actual d1 comparisons show no “still unresolved” cases even though the host, referent, and quantity failures persist. The detailed judgments and README explain this correctly; the summary does not make it obvious. [Comparison implementation](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py)

**Change:** preserve the transition categories and add an orthogonal final-state summary:

| Final state | Meaning |
|---|---|
| Supported | The requested structure is supported. |
| Persistently unsupported | The same structural failure remains. |
| Ambiguous | Evidence supports competing readings. |
| Unassessed | No applicable judgment exists. |
| Not comparable | Inputs or semantic grain prevent the intended comparison. |

For unsupported cases, attach a stage diagnosis: missing proposal, wrong role, wrong binding, correct candidate offered but rejected, incomplete normalization, or unavailable delivery.

This should be a modest extension to the existing evaluator, not a separate evaluation framework.

## 3. How I would better use GLiNER2.5

### 3.1 Complete the explanation of why a candidate disappears

The latest boundary diagnostic is valuable because it already separates representability from proposal availability.

For Binomial Definition 3.6, the exact term, naming subject, `n` restriction, and `B` declaration were present in the ordinary pool. Some intended term/content scores were low. The `p` restriction was absent, but supplying it still produced a weak content-role score. Increasing the pool therefore addresses only part of the problem. [Boundary evidence](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-gliner-boundary/README.md)

The current diagnostic retains proposal and pair scores, but only the names of the boundary auxiliary tensors. I would add a **bounded decoding trace for inspected candidates**:

| Stage | Retain for the inspected candidate |
|---|---|
| Alignment | Exact source extent, model extent, representable/refused outcome. |
| Proposal | Present/absent, proposal rank, candidate origin. |
| Role scoring | Query identity, pair logit, applicable temperature and threshold. |
| Query selection | Relevant NULL/abstention result; count guidance state. |
| Overlap handling | Retained or suppressed, with the conflicting candidate. |
| Record assignment | Proposed instance, selected field or absence, assignment conflict where observable. |

There is an API distinction to respect: `score_candidates(return_auxiliary_logits=True)` returns start/end/inside logits. It does **not** return NULL/count outputs; those require a bounded adapter over the pinned forward result. Attribute, entity, and record-field decoding also have different rejection mechanisms. [Pinned boundary implementation](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py)

Only label a rejection cause as observed when the decoder exposes it or the exact decoding rule reproduces it. Otherwise report that the retained diagnostics do not establish the cause.

This gives each failure an actionable next step instead of encouraging threshold changes across unrelated failure modes.

### 3.2 Qualify GLiNER as a scorer of independently generated spans

The repository has now established a useful preliminary result: explicit-span scoring can agree with native scores on shared candidates in the tested configuration.

The next experiment should compare:

1. Ordinary GLiNER discovery.
2. Fixed, independently produced spaCy/HanLP/source-native spans scored by GLiNER.
3. A bounded union of native and independently produced spans.

Feed all three into the **same role and binding consumer**. Preserve candidate origin and exact occurrence identity.

The missing qualification is the **jointly packed candidate population**. The 126 matching scores came from individually supplied spans; they do not establish behavior for an entire native-plus-injected set. Test nested spans, repeated strings at different positions, candidate order, capacity, and known wrong-role alternatives.

This is a promising way to combine your existing parsers:

- Rules and syntax nominate exact clause or noun-phrase boundaries.
- GLiNER supplies schema-conditioned role evidence.
- The existing composition layer determines which binding is supported.

Explicit-span scoring itself does not establish a condition host or a complete definition. [Current diagnostic adapter](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/gliner.py)

### 3.3 Turn retained assertion groups into inspectable candidate relationships

The normal extraction path already retains individual returned fields and their grouping composites before whole-record assembly. That is the right behavior for progressive structuring.

A narrower opportunity remains: `_with_group_attachments()` currently derives associations for table and definition groups, while assertion fields primarily remain connected through the returned-group composite. [Contribution adapter](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/contribution_adapter.py)

**Change:** extend the existing mechanism to expose candidate associations such as:

- Predicate → subject.
- Predicate → object.
- Predicate → condition.
- Predicate → attribution.
- Predicate → quantification.

These must retain the meaning **“the extraction model grouped these fields”**. They are not independent confirmation of a relation and should not acquire a fabricated relationship confidence.

The consumer can then compare these proposals with spaCy dependencies, HanLP roles, and independently assessed attachment rules. A subject–predicate relationship can remain useful when the object is absent.

This is one of the clearest ways to increase connectivity from information already collected.

### 3.4 Expand span attributes through small, controlled tasks

The definition pack already uses span attributes. A useful next task could assign local polarity, modality, or mention status to an explicitly located predicate/event mention.

Use:

- A small released label vocabulary.
- `applies_to` restricted to the intended mention type.
- `qualify_labels=True`.
- Separate retention of the mention, attribute prediction, and supporting literal cue.
- A comparator using the existing syntactic interpretation.

GLiNER attributes are scored at retained entity spans, so they cannot recover a missing mention. Single-label attributes use softmax/argmax: a returned winner does not provide an independent abstention guarantee. Furthermore, attribute labels participate in boundary queries, so adding attributes can change competition in the shared candidate pool. [Pinned attribute decoder](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/engine.py)

**The essential additional control is a no-attribute arm.** Measure whether adding the attribute changes mention recovery as well as attribute correctness.

A good first panel would contain two nearby mentions with opposite local status, an irrelevant sentence with the opposite status, and an unresolved case. This tests whether the model attaches the property to the right occurrence.

### 3.5 Use record formation and constraints for diagnosed grouping problems

Natural anchored records should remain the baseline for explicit actions and assertions. The literal-only assertion repair has demonstrated why combining literal extraction with inline classification choices needs care.

The advanced record capabilities become useful for specific errors:

| Capability | Appropriate use |
|---|---|
| Optional fields | Preserve incomplete source-grounded records without requiring every role. |
| Cardinality | Express a task’s actual field structure. |
| Exclusive assignment | Prevent the same occurrence being incorrectly assigned to competing instances where exclusivity is semantically valid. |
| Latent anchors | Investigate repeated records when a useful seed exists but the schema’s chosen anchor is inadequate. |
| Anchorless records | Investigate genuine records without a stable explicit anchor. |
| `Classifier.score()` / `decode()` | Enforce meaningful constraints among classification decisions. |
| `JointIE` | Compare jointly constrained entity/relation assignments for a specific relation family. |

Exclusivity needs particular care: one actor can legitimately participate in several actions, and one condition can govern several coordinated actions. The constraint should follow the source semantics.

The earlier feasible-but-unsupported JointIE results justify keeping graph feasibility and semantic correctness separately assessed. These capabilities are documented in the supplied [GLiNER guide](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/libraries/parsing/gliner2.md); several are already conditional investigations in the current plan.

### 3.6 Specialize only after identifying the responsible error

If repeated failures remain after source, schema, and composition repairs, the guide gives you a credible training route:

- Use exact reviewed spans and record identities.
- Validate examples and inspect alignment failures.
- Measure proposal recall with gold injection disabled.
- Measure role accuracy conditional on the correct span being offered.
- Measure grouping accuracy conditional on the required fields being available.
- Preserve nested and repeated-occurrence supervision.
- Treat capacity truncation or skipped samples as explicit coverage loss.
- Compare a pinned LoRA/DoRA adapter with the unchanged checkpoint before considering full tuning.

The native `dry_run_recall_steps` facility is particularly useful for avoiding a misleading result where a model scores injected gold candidates well but cannot propose them at inference. Also inspect contained-span deduplication during training; legitimate nested labels should not disappear inadvertently.

The existing [learned-extraction plan](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/plans/production-milestone-two/learned-extraction-investigations.md) already establishes this direction. The current six-window panel supplies error hypotheses, not yet a sufficient specialization dataset.

## 4. Better use of HanLP, Maverick, Dipo, and d1

### HanLP: expose more of the modifier and clause structure already retained

HanLP is already doing useful work in the definition declaration chain and condition composition. Its output includes substantially more structure than the current separately projected qualifier vocabulary.

The cue builder currently focuses on condition, exception, modality, negation, and attribution. Native SRL modifiers remain within frames, while constituency products primarily expose labels and spans. [HanLP product transformation](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/pm2_hanlp_products.py)

I would add a versioned transformation that:

1. Projects temporal, purpose, manner, and causal SRL modifiers as **located modifier-to-predicate candidates**.
2. Preserves native role labels alongside any normalized role.
3. Exposes clause containment and parent/child relationships where a consumer needs scope.
4. Joins these products to GLiNER fields and Dipo EDUs through exact source coordinates.

This can provide structure such as an action’s temporal limit or stated purpose without another model call. The gambler passage’s “until her capital reaches …” is an existing example worth pursuing.

The transformation must preserve linguistic distinctions: a temporal phrase is not automatically a deadline, and a native causal modifier is not automatically an accepted causal claim.

I would also widen the successful condition construction deliberately. The current `hanlp_condition_groups()` requires a unique same-sentence active host, one subject, one object, nonoverlapping roles, and one condition per host. [Condition composition](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/m1_source_capture.py)

Add separately assessed constructions for:

- Passive events.
- Copular states.
- Intransitive events.
- Multiple qualifiers on one event.

Retain a useful qualifier-to-host candidate when a complete subject–predicate–object record is unavailable.

### Maverick: consume local identity evidence and choose informative representatives

The integration already retains detected mentions, supplied mentions, cluster membership, overlapping mentions, and partition validity. Those are substantial capabilities.

The immediate consumer improvement is in referent context. The current recipe selects the nearest earlier located cluster member, which may be another pronoun. [Contextual recipes](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/contextual_query.py)

**Change:** prefer an informative earlier name or nominal using retained POS/phrase evidence, while optionally retaining the nearest mention as a second signal. Keep the cluster and the representative-selection decision separately attributable.

Also make parser-derived local links directly inspectable as their own products. A later d1 disagreement should not erase a useful Maverick proposal or become a universal prerequisite for its availability.

For broader context, measure cross-partition reference opportunities before increasing scope. Successful child scopes do not establish that chains crossing their boundary were recovered. Segmented joint clustering is an appropriate later investigation when such misses are demonstrated.

### Dipo: retain the relationship in the context, not just neighboring words

The Dipo adapter preserves ordered trees, nuclearity, relation labels, and segmentation provenance. The contextual query recipe currently renders a generic “Discourse neighbor” and takes only the first EDU from the selected sibling range. Much of the parser’s distinctive information therefore does not reach the query representation. [Contextual recipe](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/contextual_query.py)

A revised recipe should retain:

- Focal EDU.
- Complete selected sibling text within the declared budget.
- Relation label.
- Nuclearity and focal side.
- Parent/sibling range.
- Any omitted context.

That representation can distinguish an explanation, temporal limit, contrast, or condition from arbitrary adjacency.

The evaluation should follow the strong pattern already present in the Dipo assessment: boundaries first, ordered splits second, relation/nuclearity only on comparable splits, then context selection. The operations fixture demonstrates why this matters: forcing a heading boundary did not ensure its correct attachment. [Dipo assessment](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-08_pm2-parsers/dipo-assessment.md)

### d1: make the decision interface specific to the operation

The compact option aliases are already implemented. The remaining candidate rendering still includes substantial native structure, and generated candidate criteria use generic wording equivalent to “choose this candidate if supported.”

That is a reasonable generic interface, but it warrants a controlled task-specific comparison given the offered-candidate failures. [Request rendering](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/orchestrate/pm2_stage.py), [question declarations](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/semantic/interpretation_questions.py)

I would introduce small renderers for each decision:

| Decision | Model-facing representation |
|---|---|
| Condition host | Exact qualifier clause, each candidate predicate with its clause/arguments, and the attachment question. |
| Referent | Exact focal mention, each candidate’s phrase and sentence context, and an explicit identity question. |
| Definition link | Exact use, candidate term, complete defining content, and scope distinctions. |
| Quantity | Exact focal clause, requested magnitude/unit/role, and explicit absence behavior. |

Keep durable IDs, full native payloads, and custody metadata in retained records. Continue restricting answer spans to authorized source fields.

Compare the existing and revised renderings with identical candidates and source, including candidate-order controls. This tests an interface hypothesis; the evidence does not yet establish that rendering caused the failures.

For quantities, divide the operation into magnitude, unit, semantic role, original span, and normalization. In the roulette case, a positive magnitude of `1`, a unit of “dollar,” and a loss role are distinct facts. The current one-answer quantity contract and strict normalizer cannot express all of them independently. [Quantity comparison](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-quantity-span/README.md)

## 5. spaCy remains a strong route for targeted improvements

The existing named-rule, phrase, dependency, and overlapping-span infrastructure is a useful baseline. I would first use it to produce explicit candidate roles and attachments from retained annotations.

For learned extensions, choose the task precisely:

- **Correct spans, wrong labels:** compare `SpanCategorizer` over the same fixed candidate set.
- **Missing representable spans:** improve rules/parser proposals, then consider `SpanFinder`.
- **Correct endpoints, wrong relationship:** use a typed pair scorer.

`SpanCategorizer` separates candidate suggestion from labeling and supports overlapping spans; `spacy.preset_spans_suggester.v1` can consume an existing span group. It does not itself express the relation between a qualifier and one of several candidate hosts. [spaCy API Documentation](https://spacy.io/api/spancategorizer?utm_source=chatgpt.com)

For a binding scorer, the unit should be:

```text
(focal occurrence, candidate occurrence, relation, bounded source context)
```

Useful features include dependency path, clause membership, SRL role compatibility, distance, coordination, local coreference, and modality/negation scope. Start with a regularized lightweight model when independently judged pairs exist. A custom spaCy `TrainablePipe` becomes worthwhile if shared representations materially improve that task.

This direction is already proposed in the repo. The next step is to instantiate it for a recurring error with adequate labels. Missing labels must not silently become negatives; stock span categorization requires a fully judged task slice or a different explicitly masked loss. [Learning plan](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/plans/production-milestone-two/learned-extraction-investigations.md)

## 6. Strengthen evaluation around structural opportunities and error stages

I would make the following assessment dimensions visible for each operation:

| Layer | Question |
|---|---|
| Source coverage | Was the relevant passage examined? |
| Representability | Can the required extent be expressed under the source/token map? |
| Proposal | Was the correct occurrence nominated? |
| Role | Was it assigned the appropriate meaning? |
| Binding | Was it linked to the correct predicate, referent, definition, or record? |
| Normalization | Was the typed transformation exact and justified? |
| Composition | Did a useful partial or complete structure survive? |
| Delivery | Is that same structure available with its declared standing and evidence? |

These can be qualitative case judgments, aggregate counts, or both. They do not require agent-task evaluations.

### Make the retrieval comparison discriminating

The current comparison is controlled, but all eight eligible targets fit inside top-10, and all positive targets already rank first. Dipo changes the rendered context for only two cases. It therefore supplies little room to demonstrate improvement. [Retrieval evidence](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-adoption-preflight/README.md)

The next comparison should:

- Use more eligible targets than the retrieval budget.
- Include genuine competing senses, neighboring concepts, and definition-versus-use distinctions.
- Report producer exclusions separately from ranking failures.
- Separate cases actually receiving contextual enrichment from unchanged controls.
- Assess d1 selection conditional on the correct target being offered.

The exponential-density miss should first be examined on the fixed offered list. Its correct target was already ranked first.

### Grade semantic correctness and exact boundaries separately

The public condition journey initially failed one reference frame and passed a separately authored role-anchor frame without changing the underlying private product. That history is retained honestly. [Condition evidence](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-public-condition/README.md)

Use separate judgments for:

- Correct semantic relationship.
- Correct role membership.
- Exact extent or lexical-anchor agreement.
- Payload completeness.
- Admission eligibility.

This preserves strict source fidelity while making useful partial structure visible. Changed rubrics should remain separately versioned, with fresh opportunities used to establish generalization.

## 7. Mathematical and probabilistic improvements

### Preserve the existing candidate-relative semantics

The current finite interpreter computes a distribution of the form:

\[
q(x\mid C,E)
\propto
\mathbf{1}_{\mathrm{feasible}}(x)
\exp\!\left(\sum_f \phi_f(x_f)\right),
\]

where \(C\) is the retained candidate universe. It explicitly marks probabilities as provisional and candidate-relative, with omitted candidate mass unknown. It also computes a record event as a union of derivations, avoiding double counting overlapping derivations. These are sound choices. [Finite interpreter](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py)

Keep candidate-set size, exclusions, and unresolved alternatives alongside these probabilities. A sole feasible candidate is not thereby empirically certain.

### Dependence metadata needs an actual numerical treatment

One important implementation distinction: `DependenceScope` connects the diagnostic dependency graph, but does not adjust factor weights. The numerical computation still sums the supplied log potentials.

As new parser signals enter these models, shared provenance alone will not prevent double counting.

**Prescription:**

- Deduplicate equivalent observations from repeated windows or the same native group.
- Represent shared evidence through a grouped/joint potential, or eventually one discriminative compatibility model.
- Retain disagreement and shared-source identity explicitly.
- Compare resulting attachment decisions on fixed cases.

The table interpretation code already offers a local pattern for allocating shared evidence jointly. Reuse that pattern where the semantics fit. [Table interpretation](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/table_interpretation.py)

### Add semantic diagnostic features before fitting richer policies

The current record-policy features largely measure presence, location, exactness, unresolved fields, transformations, alternatives, and diagnostics. A fully located wrong antecedent can look structurally strong under those features. [Record policy](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/semantic/record_policy.py)

Retain operation-specific features such as clause compatibility, native cluster membership, qualifier-host agreement, scope crossing, and conflicting role assignments. Freeze a small feature set per operation when suitable labels exist.

The absence of an eligible fit/calibration population is a reason to keep these as inspectable diagnostics for now.

### Splink has a concrete extension opportunity

Splink is already integrated for artifact linkage, including alias blocking and exact pair-population control. Its current scoring model uses exact controlled-code and exact title comparisons; fuzzy title similarity primarily helps nominate candidates. [Artifact identity](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/semantic/artifact_identity.py)

Where reviewed misses justify it, add a versioned graded title comparison—exact, strong lexical agreement, weaker agreement, missing—and possibly observed-alias agreement. Account for title/alias correlation. Keep reference, lineage, revision, and supersession as distinct questions.

For **pgmpy**, a concrete future trigger is measured difficulty with exact inference over the current retained joint. For **Pyro**, it is a specified latent-variable or hierarchical model with suitable observations. Neither currently addresses the most clearly demonstrated extraction and selection failures.

## 8. Runtime and scale improvements

Three code-supported opportunities deserve measurement:

1. **Use GLiNER’s existing microbatching.** The worker supports batches up to four, while principal M1 and definition callers submit singleton requests. Group compatible windows by profile, schema, and policy; preserve per-window source maps and outcomes. Measure throughput, memory, output parity, and cancellation. [Worker](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/methods/gliner_worker.py)

2. **Keep a healthy PM2 worker alive across compatible fallback waves.** The current orchestration closes the worker before scheduling limited-scope children, potentially reloading weights at each depth. Preserve claim maintenance and exclusive GPU custody while measuring load count and elapsed time. [Orchestration](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/python/corpus-structure/src/corpus_structure/orchestrate/pm2_stage.py)

3. **Reduce portable proof amplification.** A bounded live read was reduced to two rows totaling 5,463 bytes, while a selected detached witness still carried about 336 MB of relation files. Item-addressable producer products and shared immutable evidence could reduce this burden while preserving exact replay. [Bounded reads](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-bounded-retrieval/README.md), [detached evidence](https://github.com/paul-heyse/corpus-structure/blob/e55bcfc546c65dd5c3261414f79b618c71c8903b/docs/design_review/evidence/2026-11-09_pm2-affine-ordered-source/README.md)

These are performance opportunities supported by code and retained measurements; their proposed improvements have not yet been measured.

## Recommended next implementation sequence

| Order | Deliverable | Structural evidence of success |
|---|---|---|
| **1** | d1 empty-question projection and final-state assessment summaries | Every attempted question is visible; persistent failures are clear. |
| **2** | Existing parser evidence consumed through typed role associations | Correct condition hosts, local referents, and partial assertion relationships remain independently inspectable. |
| **3** | Task-specific d1 rendering and decomposed quantity extraction | Fixed-candidate decisions improve; magnitude, unit, and role are assessed independently. |
| **4** | GLiNER decoding trace and packed explicit-span comparison | Each miss is assigned to a responsible stage; gains reach the shared consumer. |
| **5** | HanLP modifier/clause projections and revised contextual recipes | More relevant scope and relationship information survives transformation. |
| **6** | Larger, discriminating retrieval and structural comparison populations | Improvements hold beyond the current exposed examples and ceiling cases. |
| **7** | Measured batching, worker reuse, and evidence-size improvements | Broader processing remains practical without losing coverage or replay. |
| **Conditional** | Span/pair training, GLiNER adapters, broader scopes, or probabilistic backends | A recurring diagnosed limitation and suitable evaluation population justify the extension. |

**The next meaningful milestone is a richer network of independently inspectable structures from the current model set:** qualified predicates, modifier-to-host candidates, local reference chains, definition/use links, decomposed quantities, and discourse-aware context. Each should have its own coverage and correctness assessment. That moves the corpus toward the company-knowledge representation you want while allowing every useful, well-grounded partial result to stand on its own.