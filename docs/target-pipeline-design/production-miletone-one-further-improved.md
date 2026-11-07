## My assessment

**The strongest next step is to improve how the existing observations are interpreted, qualified, and connected.** The repository now has much of the machinery needed for this: retained linguistic annotations, substantial GLiNER output, source-bound components, contextual retrieval, scoped relationships, finite probabilistic inference, a working Splink integration, and rooted dossiers.

The largest opportunities I found are in the connections between those capabilities:

1. **Make more of the retained evidence available to downstream operations.**
2. **Represent the conditions, roles, and scope surrounding a statement more completely.**
3. **Create relationships between distinct occurrences through explicit source evidence.**
4. **Use joint inference and learned reliability to resolve specific remaining ambiguities.**
5. **Assemble the resulting relationships into concept families, comparisons, dependency views, and structural gap reports.**

That sequence would increase the quantity, quality, and connectivity of the structured representation without requiring another general extraction model.

I reviewed `main` at [commit `88fd5d1`](https://github.com/paul-heyse/corpus-structure/commit/88fd5d108015e471758e6d3fcd4109fa88d9114a), including the current WCE plan, production code, assessment reports, finalized evidence records, and the attached library guides. This was a source and recorded-results review; I did not rerun the providers or database journeys. Some large raw results are Git LFS payloads, so I distinguish their recorded conclusions from results independently reproduced during this review.

## 1. What the current implementation changes about the recommendation

Several capabilities that were previously recommendations are now implemented. The next work should build on them.

| Area | What is already present | Where I see the next opportunity |
|---|---|---|
| spaCy | Named token, phrase, and dependency patterns; role expansion; overlapping spans; reconstruction from retained annotations | Better semantic recipes for subjects, defining content, attribution, qualifications, and clause scope |
| GLiNER 2.5 | Entity, attribute, relation, and structured-record support; retained raw outputs; directed definition attachments | Better candidate meanings and task schemas; targeted use of classification and record constraints |
| Contextual linking | Exact, lexical, and embedding candidate retrieval; explicit relationship selection and abstention | Produce more source-supported relationships between distinct occurrences |
| Probabilistic interpretation | Exact finite inference with factors, hard masks, marginals, alternatives, and event unions | Richer factors, compatible learning targets, and eventually more scalable inference |
| Artifact identity | Actual Splink execution, scoped candidates, external nominations, alias blocking, and evaluation | Recover missing endpoints, broaden nominations, and improve comparison features |
| Knowledge assembly | Root-qualified dossiers and typed comparison | Connect comparisons, exceptions, variants, and downstream dependencies to those roots |

These are visible in the current [linguistic and definition composition](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/definition_applicability.py), [GLiNER adapter](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/gliner.py), and [latest WCE repair dispositions](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/plans/witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07).

Three findings particularly inform my priorities.

**First, some missing links are caused by missing representations.** The artifact assessment identifies 13 supported pairs, but three depend on native-only captions that have not entered the projected cohort. Improving a matching model cannot recover pairs whose endpoints it never receives. The production discovery function explicitly skips artifacts without an appropriate projected citation. [Artifact evidence](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-artifact-pilot.json) · [Discovery implementation](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/artifact_identity.py)

**Second, retrieval and relationship interpretation remain different bottlenecks.** The latest contextual run retains 90 candidate lists and correctly withholds the false link from the affine-transform `X` to an unrelated red-ball count. It still lacks the exact formula `Z` occurrence and an eligible standard-normal target. All 90 selection decisions in that particular run report insufficient evidence. This is evidence for improving occurrence capture, target capture, and relationship witnesses separately. [Contextual repair account](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-completion-repair/composition/README.md)

**Third, more sophisticated probabilities have not yet demonstrated better selections in the assessed table frame.** Both weighted modes selected all nine supported readings at each assessed scale. Coupling changed the marginals, but did not improve those top selections. That makes the next mathematical question “which additional relationships or evidence should the model represent?” before “which inference library should execute it?” [Matched table-policy results](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-completion-repair/table/README.md)

## 2. Recover more structural value from the evidence already retained

### O01 — Bring currently unrepresented native evidence into the ordinary pipeline

**I would make this an immediate priority.**

The native-only captions are a concrete starting point. The broader opportunity is to ensure that useful retained items can participate in ordinary structural operations even when their location precision differs.

A retained caption, fragmented paragraph, or graphical label might support:

- An item-level reference to its original location.
- A captured artifact title or identifier.
- A candidate relationship to another source item.
- An unresolved interpretation that remains inspectable.

It should acquire an exact character span only when that correspondence is established. This allows incremental structure to survive while each downstream operation uses the precision it actually requires.

The first implementation should extend the existing source/projection owner and reuse the current artifact and contribution consumers. It does not need another extraction service.

I would also examine a bounded portion of the retained GLiNER content that currently ends in unresolved or unlocated diagnostics. The assessment records substantial retained provider content beyond the components that have been semantically assessed. Some of that may become usable through better field interpretation, source alignment, or composition. Its presence alone does not establish useful information, but it is a more grounded place to investigate than immediately adding another parser. [Retained-content assessment](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-gs120/assessment/benefit-account/README.md)

**The assessment should follow the transformation:** native opportunity present → representation available → component captured → candidate link available → relationship supported. That tells you exactly which change created additional usable structure.

### O02 — Attach located qualifications to useful components

The current `LocatedDefinitionComponent` records a term, content, interpretation, scope, version, alternatives, and evidence. It does not itself carry typed, located attachments for every condition, assumption, exception, or parameterization associated with that particular component. The named-component constructor also deliberately requires complete contiguous roles, while retaining partial and discontinuous evidence upstream. [Component types](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/structural_products.py) · [Named-component construction](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/definition_applicability.py)

**I would extend the representation around those components with explicit qualification relationships.**

For example:

| Relationship | What it adds |
|---|---|
| `has_condition` | The circumstances under which a statement applies |
| `has_assumption` | A premise needed for the stated result |
| `has_parameterization` | The local meaning or configuration of variables |
| `has_exception` | A stated exclusion or alternative case |
| `attributed_to` | Who is asserting or being described as asserting something |
| `has_modality` | Required, permitted, possible, hypothetical, or otherwise qualified |
| `precedes` / `depends_on` | A stated ordering or prerequisite |

Those are proposed semantic roles, to be aligned with the existing model’s vocabulary. Each attachment should retain its own located evidence and the identity of the statement it qualifies.

This would address actual recorded gaps involving Event F, positive variance, normal parameters, local urn labels, exercise requests, and a zero-wait convention. The evidence is careful that a qualification missing from one component may still be retained elsewhere; the opportunity is to **connect that retained information to the component that needs it**. [Granular source findings](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-gs120/assessment/benefit-account/README.md)

This is also directly applicable to company knowledge. Using our illustrative purchase-review sentence, a useful representation can preserve:

- The reviewer as actor.
- Completing the form as the action.
- The form as the object.
- The requirement’s modality.
- High-risk purchases as its applicability condition.
- Approval as its ordering boundary.
- An approved exception as an exception to that requirement.

The qualification belongs to the statement. It should not become a collection of disconnected keywords.

This extension can deliver useful partial structure immediately: an action and its condition can be represented even while an artifact reference or version remains unresolved.

## 3. Further use of spaCy: improve semantic composition

### O03 — Develop richer recipes over the linguistic annotations already stored

The existing spaCy integration is substantially more capable than a basic tokenizer-plus-NER pipeline. It already supports the matcher families, named dependency roles, several span-expansion strategies, and retained annotation reuse. spaCy’s matching facilities are well suited to combining lexical and grammatical evidence of this kind. [spaCy Usage Documentation](https://spacy.io/usage/rule-based-matching?utm_source=chatgpt.com)

I would concentrate on three extensions.

#### A. Distinguish the subject, content, and speech act of a statement

The current assessments contain revealing errors:

- An integral attached to `Y` when its subject is the probability that `X` is less than `Y`.
- A historical contrast involving “instead of defining” interpreted as a performed definition.
- A term truncated to “a set,” omitting “of constant density.”

These are specific opportunities for better composition of nominal phrases, dependency roles, negation, contrast, attribution, and defining content. [Recorded cases](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-gs120/assessment/benefit-account/README.md)

I would make a statement’s *function* explicit: definition, explanation, reference, historical attribution, hypothetical example, instruction, or unresolved. The words and their grammatical relationship can be correctly located while the statement’s function remains uncertain.

#### B. Qualify procedure frames before treating them as workflow knowledge

The current procedure machinery already extracts actor, action, object, modality, condition, exception, and ordering evidence. It also nominates broadly from prose verbs, and the source assessment records ordinary clauses receiving spurious procedure-action roles. [Procedure-role implementation](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/structural_roles.py)

The next step is a qualification operation that distinguishes:

- A prescribed step.
- A description of how a process operates.
- A worked example.
- A mathematical or factual assertion.
- An unresolved procedural interpretation.

Section headings, list structure, modality, grammatical form, and surrounding clauses can contribute evidence. GLiNER classification can provide an additional reading on the same passage.

This is particularly useful for your eventual enterprise setting: policy, procedure, example, exception, and historical practice often appear together.

#### C. Reuse qualified frames in downstream comparison

The current clause-comparison route also extracts fields through separate text patterns. Once a source-bound procedure frame has been constructed, its actor, action, object, modality, condition, and exception should become reusable inputs to comparison.

That would let the system compare changes such as:

- A responsibility moving from one role to another.
- An optional step becoming mandatory.
- A new exception being introduced.
- A condition narrowing the population to which a procedure applies.

Lark fits here as a parser for bounded grammatical structures—comparators, ranges, quantities, dates, and condition expressions—while spaCy supplies the linguistic relationships around them. Your existing [structural parsing](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/structural_parsing.py) and [comparison method](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/structural_products.py) provide the foundation.

## 4. Further use of GLiNER 2.5: improve the questions and candidate meanings

I would expand GLiNER’s use selectively, with different questions for different operations.

The application already supports attributes, relations, and records. The definition pack already requests term/content entities, an interpretation attribute, and a directed attachment. Consequently, the useful next change is to improve what those categories mean and how their outputs compose.

### More discriminating local classifications

Promising questions include:

- Does this passage perform a definition, refer to one, or discuss one historically?
- Is this clause an instruction, a process description, or an example?
- Does this phrase express a condition, exception, attribution, or temporal limitation?
- Does a candidate span name the subject, define it, or merely mention it?

Use the source passage and candidate roles as the unit of analysis. These questions can complement deterministic recipes while preserving disagreement between them.

### Record constraints where records have meaningful structure

GLiNER’s schema supports descriptions, classification examples, record modes, cardinality, and exclusivity. Those capabilities are useful when the source really contains repeated records or constrained role assignments—for example, several workflow steps, each with an action and possibly an actor, object, and condition. [Tagged GLiNER schema](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py)

The constraints should reflect the domain. A statement may have multiple conditions, one qualifier may govern multiple statements, and an action may legitimately have multiple participants.

### Revisit joint decoding only after improving the candidates

The actual JointIE investigation is particularly informative: 149 definition windows contained 2,143 term proposals, 117 content proposals, and 22 proposed attachments. The bounded joint-decoding trial produced structurally coherent but semantically wrong edges, including `binomial distribution → Section 5.2`. The investigation therefore leaves that configuration inactive. [JointIE evidence](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-gs120/joint-ie-investigation001/README.md)

My recommendation is to address the imbalance and meaning of term/content candidates, then compare independent and joint decoding on the same cases. Graph constraints become useful when they constrain plausible semantic alternatives.

**Decide remains a reasonable targeted challenger for classification.** Its documented specialization is classification with supplied labels. I would introduce it when a clearly defined classification problem remains after testing the existing checkpoint and linguistic evidence. It would not address missing content spans by itself. [Hugging Face](https://huggingface.co/fastino/GLiNER2.5-Decide-1B?utm_source=chatgpt.com)

## 5. Improve connectivity through explicit references and richer identity evidence

### O04 — Generate more relationships between distinct source occurrences

The current retrieval machinery already combines exact, lexical, and dense retrieval. The next opportunity is to produce the evidence that turns a candidate into a particular relationship.

I would prioritize:

- Explicit “as defined in” or “see section” references.
- Declaration/use relationships within a source-established scope.
- Acronym introduction and subsequent use.
- References from procedure steps to controlled artifacts.
- Statements that explicitly rename, specialize, supersede, or qualify another item.
- Source-established inheritance of conditions across a paragraph, list, or procedure.

These mechanisms can reuse the current contextual selector. Each produces exact endpoints and the premises supporting the relationship.

A mention can still be structurally useful when its target is unresolved: it can connect to its clause, source scope, reference cue, and candidate targets. The assembled view should preserve those relationships and the unresolved selection.

The current [contextual candidate producer](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/contextual_candidates.py) and [retrieval layer](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py) are the appropriate integration points.

### O05 — Expand Splink’s inputs and comparisons

Splink is already integrated. Its next value comes from better candidate populations and more informative comparisons.

#### Broaden the external nomination contract

There is a consequential restriction in the current implementation.

`retained_artifact_nomination` requires a matching non-null normalized code and a unique same-view caption. The ordinary candidate generator already includes compatible exact-code pairs. Therefore, the current external nominations are effectively a subset of a population already generated by exact-code matching.

Their overlap does not tell us whether broader source-supported nomination would be valuable. [Nomination contract](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/artifact_identity.py) · [Pair generation](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/artifact_identity.py)

I would add distinct nomination routes for source-supported cross-view references, explicit renaming, and artifact lineage. Each route should preserve the question being answered: reference resolution, maintained-artifact identity, and immutable-version identity are different relationships.

#### Give the scorer more than exact agreement

The current scorer uses fixed parameters for exact code and title agreement. Fuzzy title similarity helps admit candidates, but the statistical model largely reduces a non-identical title to disagreement.

A richer comparison can distinguish exact agreement, spelling variation, meaningful token overlap, missing values, and substantive conflict. Splink provides thresholded string comparisons, array intersections, and custom comparison levels for this purpose. [Splink](https://moj-analytical-services.github.io/splink/api_docs/comparison_library.html?utm_source=chatgpt.com)

Term-frequency adjustments can distinguish the informativeness of common and rare values. An agreement on a generic title should contribute differently from an agreement on an unusual controlled identifier. [Splink](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/term-frequency.html?utm_source=chatgpt.com)

The underlying model combines evidence approximately as:

\[
\log \frac{P(M\mid\gamma)}{1-P(M\mid\gamma)}
=
\log\frac{\pi}{1-\pi}
+
\sum_k
\log\frac{P(\gamma_k\mid M)}{P(\gamma_k\mid \neg M)}
\]

where \(M\) is the match event and \(\gamma_k\) is a field-comparison result. This makes feature dependence consequential: title tokens, a title embedding, and aliases manufactured from that title are strongly related evidence. They should not be interpreted as three independent confirmations. [Splink](https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html?utm_source=chatgpt.com)

For the present corpus, all 142 artifact alias states remain unknown. I would recover authentic alias evidence before tuning alias-based matching. For future company material, the same machinery could address forms, policies, systems, organizational entities, and controlled documents, with the relevant namespaces and version distinctions preserved.

## 6. The strongest mathematical extension: richer joint interpretation

### O06 — Extend the existing finite model with meaningful coupled factors

Your existing solver already performs exact inference over its retained candidate universe. In simplified form:

\[
P_C(z\mid E)
=
\frac{
\mathbf{1}[z\text{ satisfies hard constraints}]
\exp\!\left(\sum_f \ell_f(z_f;E)\right)
}{
Z_C(E)
}
\]

Here \(z\) is a joint assignment of candidate interpretations, \(E\) is the consumed evidence, and \(C\) is the retained candidate space. The implementation computes marginals and union events in log space, preserves coherent alternatives, and explicitly records candidate-relative standing and unknown omitted-candidate mass. [Finite inference implementation](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py)

**The next advance is to connect decisions whose meanings actually depend on one another.**

For a source passage, these might be:

- Whether it performs a definition.
- Which phrase is the subject.
- Which content describes that subject.
- Which condition qualifies the relationship.
- Which later occurrence uses that locally defined meaning.

For a procedure, they might be:

- Whether a clause is a required action.
- Which role performs it.
- Which artifact it consumes.
- Whether an exception applies to that action or another clause.
- Whether two references concern the same artifact lineage.

The additional structure comes from those dependencies. Joint inference can compare complete interpretations that isolated classifiers cannot assess coherently.

Two design details matter.

**Shared evidence must be represented in the factors.** Recording that observations are dependent does not automatically correct their numerical combination. A dependency parser, a rule, and GLiNER may all be responding to the same wording. Factor design must account for that shared origin.

**Hard constraints should express established impossibility.** Uncertain linguistic preferences, likely attachment, and semantic similarity usually belong in soft factors. A strong but fallible parser judgment should not silently eliminate the correct alternative.

#### Learn a few interpretable weights

A useful next experiment is to fit a small number of weights for explicit references, grammatical attachment, conflicting scope, and other meaningful features.

If independent judgments identify acceptable assignments \(A_j\) within candidate set \(C_j\), one possible objective is:

\[
\mathcal L(\theta)
=
-\sum_j
\log
\frac{\sum_{z\in A_j}e^{\theta^\top f(z,E_j)}}
{\sum_{z\in C_j}e^{\theta^\top f(z,E_j)}}
+
\lambda\|\theta\|^2.
\]

This supports partial supervision: multiple assignments may remain acceptable. The model learns how evidence distinguishes those alternatives.

For small retained candidate sets, the existing exact sums and SciPy optimization are sufficient to investigate this. The important design work is defining the variables, features, and assessed event.

#### Where pgmpy adds value

**pgmpy becomes compelling when a useful sparse model exceeds the current enumerator’s reach.**

The current default guard is 65,536 joint states. A model with many local decisions connected through a small shared state can have a large Cartesian product while remaining tractable through variable elimination. pgmpy exposes elimination order and induced-width tools relevant to this distinction. [pgmpy](https://pgmpy.org/api/generated/inference/pgmpy.inference.VariableElimination.html?utm_source=chatgpt.com)

I would integrate it as an alternative executor behind the existing request/result meaning. With the same factors, it should preserve the same model answers.

That adapter needs deliberate treatment of normalization and numerical stability. In the inspected pgmpy implementation, some Markov-network query paths return factors without automatic normalization. The current repository’s log-space safeguards should be preserved. [Tagged pgmpy inference source](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/inference/ExactInference.py)

My recommendation is to develop the richer local models now, then adopt pgmpy when a concrete model benefits from structured elimination.

## 7. Pyro: learn reliability and uncertainty across related operations

### O07 — Add hierarchical reliability when the grouping has meaning

Pyro’s distinctive opportunity is uncertainty about parameters and shared effects.

A proposed operation-reliability model could be:

\[
y_i \sim \operatorname{Bernoulli}
\left(
\sigma\!\left(\alpha+\beta^\top x_i+u_{g(i)}\right)
\right),
\qquad
u_g\sim\mathcal N(0,\tau^2).
\]

Here:

- \(y_i\) is an independent judgment of a specific operation.
- \(x_i\) contains evidence features for that operation.
- \(g(i)\) identifies a meaningful shared mechanism or context.
- \(u_g\) allows reliability to vary across those contexts while sharing information.

This could distinguish, for example, attachment reliability in explicit definitions from attachment reliability in historical discussion, or a well-supported procedure pattern from a sparse one.

Pyro supports this partial-pooling approach; its official tutorial explicitly compares pooled, separate, and hierarchical binary-trial models. [Pyro Tutorials 1.9.1 documentation](https://pyro.ai/examples/baseball.html?utm_source=chatgpt.com)

### Resolve the current learning-target mismatch first

The repository already has a regularized logistic baseline in `operation_fitting.py`. The recorded census found no eligible `relation.defined_by` events under the selected fitter contract, despite many other emitted relationships. The existing defining-text attachments and contextual proposals have different semantics. [Fitting availability](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/README.md)

I would deliberately select an operation you actually emit and want to improve—such as defining-text attachment correctness or a specific scoped-role attachment—and connect its exact output identities to the independent judgments.

Then:

1. Exercise the existing prior-only and logistic baselines.
2. Inspect which features and contexts explain errors.
3. Introduce hierarchical effects where uneven evidence or shared mechanisms make them useful.

This can proceed on the current development corpus. It does not require a new-corpus readiness gate.

For a small initial Pyro model, MCMC provides a useful way to inspect parameter uncertainty. Pyro exposes effective sample size, chain-convergence diagnostics, and divergent transitions; those help distinguish uncertainty in the data from problems fitting the model. [Pyro documentation](https://docs.pyro.ai/en/stable/mcmc.html?utm_source=chatgpt.com)

A later extension could integrate uncertainty over factor weights into the interpretation model itself. That would separate uncertainty among candidate readings from uncertainty about how strongly the evidence should favor them.

The first consumer should be operation-level diagnostics and comparison. A learned reliability estimate should acquire a production selection role only through an explicit policy.

## 8. Turn the growing structure into richer assembled knowledge

### O08 — Add concept families, typed neighborhoods, and dependency views

This is where the previous improvements can produce a much more connected corpus.

#### Concept families and variants

The current `semantic_target_groups` groups exact authenticated meanings within an inventory. That preserves origins and is useful for deduplication. It does not itself discover related definitions, specializations, differently scoped senses, or near-equivalent formulations. [Grouping implementation](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py)

I would add a derived family-navigation view around those groups:

- Related definitions.
- Broader and narrower formulations.
- Different local meanings of a term.
- Explicit specializations.
- Alternative or differently scoped versions.

Embeddings can nominate nearby groups. Shared typed relationships and explicit source statements can justify stronger connections. Exploratory family membership can remain useful without merging identities.

#### Structural gap and relationship-pattern analytics

Use the existing relational and graph foundations to expose patterns such as:

| Pattern | Structural question it reveals |
|---|---|
| Use with no eligible definition | Was the definition missed, unavailable, or outside the established scope? |
| Reference with several candidate targets | What distinguishes the targets? |
| Procedure step with an unlinked input | Is the input named elsewhere? |
| Requirement with an unattached exception | Which statement does the exception qualify? |
| Comparison without a concept or clause root | What does this change concern? |
| A single weak bridge joining two neighborhoods | Is the connection supported or conflating meanings? |
| A dependency chain broken at one endpoint | Which missing component prevents composition? |

These are direct assessments of corpus structure. They do not depend on an agent completing an external task.

Many can begin as typed SQL joins or small graph projections. Broad clustering is useful when a particular navigation question calls for it; it should preserve relation kinds and scope.

#### Richer rooted dossiers

Rooted dossiers are already delivered. The latest native examples retain two qualified members and exclude an unrelated component. Both members fit the display budget, so those results establish membership and delivery rather than an optimization advantage. [Rooted dossier evidence](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json)

A concrete extension exists in `derive_dossier_members`: comparison reports are skipped when a root is supplied because their sides lack the required definition-sense endpoint. [Dossier assembly](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/structural_products.py)

I would connect comparison sides, uses, exceptions, variants, and dependent steps to the root through explicit relationships. A dossier could then show:

- What a concept means in its stated contexts.
- Where it is used.
- What conditions and exceptions qualify it.
- What changes between applicable versions.
- Which other statements or procedure steps depend on it.
- Which connections remain unresolved.

The existing supported-facet selection is a reasonable presentation mechanism. More elaborate optimization, such as SciPy MILP, becomes relevant if interacting display constraints create a real selection problem. It is secondary to enriching the membership itself. [SciPy v1.18.0 Manual](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html?utm_source=chatgpt.com)

## 9. How I would assess and sequence this work

I would extend the existing granular assessment system. Each increment should show what structural opportunity it captured, corrected, connected, or left unresolved.

| Operation | Assessment focus |
|---|---|
| Native-to-consumer representation | Useful retained items made available; location precision preserved |
| Span and role extraction | Complete boundaries, correct subject/content roles, speech-act interpretation |
| Qualification | Condition or exception location, host attachment, scope, omissions |
| Candidate generation | Supported targets represented; genuinely new pairs nominated; exclusions preserved |
| Relationship selection | Correct endpoints, direction, relation type, scope, and justified abstention |
| Joint interpretation | Better exact role or attachment decisions; retained acceptable alternatives; regressions |
| Identity resolution | Pair meaning, field contributions, namespace/version compatibility, unsupported bridges |
| Dossier assembly | Root relevance, connected variants and exceptions, evidence completeness |
| Display selection | Useful facets represented and necessary qualifications retained within the budget |

For each comparison, keep separate accounts of corrected cases, new supported structure, lost structure, spurious additions, and unresolved cases. Candidate counts and repeated policy arms should not be mistaken for additional knowledge.

For learned probabilities, Brier score and log loss can be useful development diagnostics. They do not establish calibration by themselves; scikit-learn explicitly discusses their combination of calibration and discrimination effects. [scikit-learn 1.9.1 documentation](https://scikit-learn.org/stable/modules/calibration.html?utm_source=chatgpt.com)

### Recommended sequence

**First: increase usable structural coverage.**

Recover the native-only endpoints, improve role/content interpretation, attach located qualifications, and add explicit reference/declaration relationships. These address demonstrated gaps and can deliver independently useful partial results.

**Second: connect and exploit the resulting products.**

Broaden artifact nomination, enrich Splink comparisons, connect comparisons and exceptions to dossier roots, and add concept-family and broken-chain views.

**In parallel on a bounded question: improve the mathematics.**

Select an existing operation with appropriate independent judgments. Compare the current baseline with a small learned factor model or operation scorer. Use the same candidates when assessing scoring, and report candidate expansion separately.

**Then adopt pgmpy and Pyro for their distinct strengths.**

| Tool | Recommended role |
|---|---|
| **spaCy** | Primary engine for richer linguistic composition over retained annotations |
| **GLiNER 2.5** | Targeted semantic proposals, classifications, attributes, relations, and record readings |
| **Lark** | Bounded typed parsing of structured fields and condition expressions |
| **Splink** | Richer scoped identity comparisons over better candidate populations |
| **SciPy** | Existing numerical foundation, small-model optimization, and specific constrained problems |
| **scikit-learn** | Interpretable operation-scoring baselines and diagnostic comparisons |
| **pgmpy** | Structured inference when useful models exceed practical enumeration |
| **Pyro** | Parameter uncertainty and partial pooling across meaningfully related operations |

**I would define the next production increment around richer qualified components and relationships between distinct source occurrences.** Those outputs would supply more meaningful inputs to the analytical methods, expand the assembled knowledge immediately, and make subsequent improvements in inference or reliability measurable at the precise layer they affect.

Understood—I’ve treated the latest push as a CLI update and kept this review anchored to the substantive model code already inspected at [commit `88fd5d1`](https://github.com/paul-heyse/corpus-structure/tree/88fd5d108015e471758e6d3fcd4109fa88d9114a).

I’ve now completed the specificity review. **Several recommendations needed a concrete implementation prescription, and a few needed correction:** GLiNER’s schema plumbing is more complete than my earlier wording suggested; the semantic model already contains useful condition types; and the first statistical learning target should be an attachment event the pipeline actually emits.

The strongest immediate work is to **recover omitted source material, improve the grammatical ownership of extracted information, and connect existing observations through explicitly typed relationships**. Those changes also give the probabilistic methods better questions to answer.

I checked the supplied library documentation against the repository, Context7, and primary library documentation/source. The changes below are proposed; I have not implemented or benchmarked them.

## 1. What changes in the recommendations

The identifiers below refer to the opportunities in the previous review.

| Earlier recommendation | Disposition | Concrete replacement |
|---|---|---|
| **O01 — Recover more value from retained content** | Improve | Repair caption projection at its source, then reuse the existing passage and artifact extraction paths. |
| **O02 — Attach qualifiers to extracted knowledge** | Improve | Attach each qualifier to its governing proposition or relationship, then lower supported readings into the existing `Qualification` and `Condition` types. |
| **O03 — Make fuller use of spaCy** | Improve | Change five specific behaviors: role expansion, clause boundaries, negation scope, predicate interpretation, and repeated comparison fields. |
| **GLiNER — Use more schema capabilities** | Correct | Keep the existing schema transport and optional cardinalities. Change extraction descriptions and add a focused clause-classification task. |
| **O04 — Produce more source-supported links** | Improve | Extend explicit reference, naming, and declaration relationships across selected views, with scope and endpoint identities retained. |
| **O05 — Improve Splink linkage** | Improve | Broaden authenticated candidate nomination and replace binary title matching with multilevel title/alias evidence. |
| **O06 — Use more sophisticated joint inference** | Correct | Model a specific shared uncertainty, rather than treating a joint support bonus as a general dependence correction. Keep pgmpy conditional on a concrete computational need. |
| **O07 — Learn reliability, potentially with Pyro** | Correct | Add an event contract for emitted defining-text attachments; fit the existing logistic baseline first. Use Bayesian logistic uncertainty before introducing a hierarchy. |
| **O08 — Improve navigation, gaps, and dossiers** | Improve | Add explicit comparison-to-root bindings, three typed gap reports, and a separate similarity neighborhood over existing embeddings. |

## 2. Recover omitted content through the existing source projection

### The specific problem

The omission is upstream of artifact scoring.

In [`project_section_nodes`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py), the table branch projects cells and then returns before ordinary child traversal. Downstream, artifact discovery iterates projected `native_text` pieces, while identity-record construction requires an exact projected citation. A caption retained only in the native document can consequently be unavailable to both operations.

The source-reference assessment identifies authentic native-only captions for **Tables 5.8, 5.9, and 6.1**. These give this recommendation an immediate, inspectable target. [Source-reference evidence](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-completion-repair/source-references/README.md)

### The prescribed change

Extend the canonical projection as follows:

1. In [`published_section_drafts`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/ingest/pdf_section_views.py), qualify caption targets selected through the actual native containment or caption relationships.
2. In `project_section_nodes`, emit those captions’ original text as ordinary `native_text` pieces, including captions associated with tables whose cell projection currently returns early.
3. Deduplicate caption visits by their **physical native pointer**. Equal text at different locations remains separate evidence.
4. Give the resulting projection a new recipe identity and expose bounded caption passages through the existing structural input.
5. Let the existing scoped artifact discovery and `ArtifactCitation` construction consume them.

This should recover the known omitted endpoints without OCR reruns or an artifact-specific alternative citation system.

For unresolved GLiNER records, I would similarly constrain the earlier “recover more from raw outputs” suggestion: **emit an independently valid, exactly located component when one exists; preserve unresolved grouping separately.** I would not make open-ended raw-output mining a separate workstream without identifying a particular field that is currently retained but inaccessible.

**Assessment:** verify that the three known captions acquire exact passages and become discoverable, while retaining their original pointers and avoiding duplicate caption occurrences.

## 3. Replace “use spaCy more fully” with five concrete changes

The useful expansion is primarily in how the existing annotations are interpreted.

### A. Expand semantic roles without losing complements or absorbing unrelated text

The current nominal expansion in [`structural_roles.py`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/structural_roles.py) follows a small dependency whitelist. It can omit meaningful complements. Its span helper also filters tokens and then returns their minimum-to-maximum character interval, which can reintroduce excluded material between those endpoints.

Change this to:

- Start with the retained base noun phrase.
- Add explicitly permitted nominal complements, including relevant prepositional complements.
- Stop at independently predicated clauses and competing coordinated heads.
- Retain token membership and coalesced source extents.
- Produce a single contiguous span only when the intervening material belongs to the role.

For example, extracting **“a set”** from **“a set of constant density”** should retain the complement when it belongs to that nominal expression. Conversely, taking an unrestricted dependency subtree can absorb another proposition; that should not become the default expansion.

Use separate grammatical recipes for active definitions, passive definitions, copular definitions, naming constructions, and reported assumptions. A copula alone should not establish that a sentence is a definition.

### B. Attach conditions by grammatical ownership

[`PreparedAnnotationRules.match`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/annotation_rules.py) currently clips expanded roles at configured lexical boundary words such as `if`, `unless`, and `except`.

Replace this with a head-governed operation:

1. Identify the proposition’s predicate head.
2. Match its directly attached subordinate clause and marker.
3. Extract the qualifier’s own extent.
4. Record the qualifier-to-host relationship.
5. Propagate a qualifier across coordination only when the grammatical reading supports that propagation.

spaCy’s `DependencyMatcher` supports explicit parent/child and other dependency relationships. Use direct relationships for the initial recipes; broader ancestor matching should be a separately justified pattern. [spaCy API Documentation](https://spacy.io/api/dependencymatcher?utm_source=chatgpt.com)

The output should preserve the original proposition, its body, its qualifiers, and unresolved attachment alternatives.

| Source example | Intended distinction |
|---|---|
| “Estimate X if A, and report Y if B.” | A qualifies estimating X; B qualifies reporting Y. |
| “If A, estimate X and report Y.” | Retain the coordinated scope reading, with the basis for applying A to both actions. |
| “The word ‘if’ introduces a conditional.” | The quoted word does not truncate the content. |
| “Use method A, except for archived records.” | Preserve an exception attached to that instruction. |

### C. Scope negation instead of rejecting every negated match

The definition-component path currently skips matches carrying negation extents. This can discard a valid positive definition whose defining content contains a negative clause. [Definition extraction implementation](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/definition_applicability.py)

The required change is to record **which predicate the negation modifies**:

- “X is defined as a function that does not vanish” contains a positive defining act and negative embedded content.
- “X is not defined here” does not supply a positive definition.
- “Do not heat and stir” may require an unresolved coordination-scope reading.
- “Do not heat, but stir” distinguishes the two actions.

The same treatment should preserve modality and attribution. Their meaning depends on their host, not simply their presence in the sentence.

### D. Extract neutral predicate frames before classifying procedures

`procedure_frames` currently begins with prose verbs, and its behavior heuristic treats `must`, `shall`, and `should` as evidence of prescription. That conflates grammatical form with discourse function: a mathematical restriction and an operational instruction can both contain “must.” [Current frame extraction](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/structural_roles.py)

Split the operation into:

- **Predicate-frame extraction:** predicate, actor, object, voice, polarity, modality, conditions, exceptions, and ordering cues.
- **Behavior interpretation:** prescribed action, described process, assumption/restriction, example, or unresolved.

Use retained heading, list, and example context in the second step. Keep the existing conservative coordination inheritance, but expose which role or modal was inherited and from which predicate.

This makes the same extraction useful for company workflows, policy statements, descriptions of existing processes, and textbook exposition.

### E. Preserve multiple conditions and participants in comparison

[`ClauseReading`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/structural_products.py) currently prohibits duplicate dimensions, and consumers assume one field per dimension.

Before feeding richer predicate frames into comparison, change that representation to support **a typed collection within a dimension**, including conjunction, disjunction, and unknown grouping. Update consumers that currently construct a simple dimension-to-field dictionary.

Otherwise, extracting two conditions or several affected objects more accurately would still lose information at the comparison boundary.

### Reuse the existing condition model

My earlier wording also understated what is already present. The active semantic model contains `Qualification`, atomic and comparison conditions, conjunction, disjunction, negation, claim references, and `EscapeCondition`. [Existing semantic types](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/model/semantic/core.yaml)

The prescription is to **connect located readings to those types**:

- Reuse the existing witnessed-component and scoped-attachment pattern for qualifier-to-host links.
- Lower a reading into a structured condition when its meaning is supported.
- Preserve located text and an unresolved interpretation when it is not.
- Keep exception, attribution, and modality roles distinct; an exception does not automatically become Boolean negation.

Use Lark for bounded formal expressions within these readings—comparators, intervals, identifiers, or an explicitly defined condition notation. A general natural-language condition grammar would be a much larger and less well-supported change.

## 4. Expand GLiNER through extraction policy and focused classification

### What is already implemented

[`GlinerPack.compile`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/gliner.py) already passes the declaration through native `Schema.from_dict()` and checks its round trip. [`family_pack`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/record_packs.py) already supports descriptions, optional scalar fields, and multiple defining-text fragments in the V2 definition pack.

Therefore, “add descriptions and cardinality support” was inaccurate as an infrastructure recommendation.

### The first change: descriptive entity and relation declarations

The local `definition_pack` currently supplies bare entity and relation labels. Change those declarations to include versioned descriptions that distinguish the intended roles:

| Role | Proposed description emphasis |
|---|---|
| Defined term or expression | The exact expression whose meaning is being stated; distinguish it from a nearby example, referenced concept, or historical subject. |
| Defining content | The words or formula that supply the meaning, including meaningful nominal complements and predicates. |
| Defining/explanatory attachment | The directed relationship from that term occurrence to the content that defines or explains it in this source context. |

Keep the current threshold as the baseline while assessing this change. The observed imbalance between terms and defining content does not, by itself, identify a better numerical threshold.

### The second change: a clause-level classification task

Use the existing GLiNER worker for a focused task over located clause candidates and their retained context.

I would separate two questions:

- **Clause function:** definition, explanation, assumption, prescribed action, described process, unresolved.
- **Presentation context:** example, reported/attributed statement, historical discussion, unresolved.

This avoids forcing overlapping distinctions into one exclusive label: a definition can appear in a historical discussion or an example.

Use a classification-capable `native-combined-v2` pack for this task. Retain the original clause identity, context selection, model profile, and returned scores. Feed the result into behavior interpretation and definition applicability as an additional observation.

The existing definition/explanation attribute on a term can remain, but it should not carry the entire interpretation of a proposition.

### Keep the current partial-record behavior

Do not make fields globally required merely to obtain fuller records. Preserve `optional_one` and `zero_or_more` where the source can legitimately be incomplete. Similarly, broad `exclusive=True` settings can prevent a shared condition or content fragment from participating in more than one valid reading; apply exclusivity only to a specific assignment rule that requires it. These distinctions are explicit in the native [GLiNER schema implementation](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py).

**Assessment:** compare the description change and classification change separately. Inspect missed defining content, wrong term/content roles, incomplete content spans, incorrect attachments, and incorrect clause classifications. Increased extraction count is useful only alongside those distinctions.

## 5. Make linking broader through explicit relationships, then improve Splink evidence

### A. Broaden nomination without weakening identity semantics

The current external artifact nomination path requires equal codes and a unique same-view caption. That makes its candidates a subset of the exact-code route, so it cannot substantially improve candidate coverage. [Artifact discovery and nomination](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/artifact_identity.py)

Change nomination to consume the actual retained relationship:

- Exact left and right occurrence identities.
- Relationship kind and endpoint roles.
- Original source witness.
- Applicable work and numbering scope.
- Any unresolved alternative targets.

An authenticated reference relationship should be able to nominate a pair across selected views or through an explicitly observed alias without requiring code equality again.

Add an explicit **numbering namespace** with an observed/unknown/unresolved state. A native pointer identifies occurrence context; it does not automatically establish the domain in which “Table 1” is unique.

Keep separate meanings for:

1. The same physical occurrence exposed through overlapping views.
2. Occurrences belonging to the same artifact lineage.
3. An observed revision within that lineage.
4. A directed citation to an artifact in another work.

This also supplies a concrete route for broader concept linking. Use spaCy patterns to extract witnessed naming statements such as “X, hereafter Y,” full-name/acronym introductions, and explicit renaming declarations. Retain the declaration and its scope. String similarity can nominate alternatives, but it cannot supply the missing naming statement.

For symbols, consume the existing `declares` relationships to expose declaration-to-use navigation. Repeated spelling alone should not bind symbols across examples or sections.

### B. Replace the two binary Splink comparisons

The current Splink model uses exact code and exact title comparisons with fixed parameters. Fuzzy title similarity can admit a candidate, but its title evidence then collapses to exact match or mismatch. [Current scoring implementation](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/artifact_identity.py)

I recommend two initial comparisons:

| Comparison | Ordered evidence levels |
|---|---|
| **Scoped code** | Unavailable namespace/code; exact namespace-and-code agreement; disagreement. |
| **Title and observed aliases** | Unavailable; exact normalized title; observed alias overlap or title-to-alias agreement; high fuzzy title similarity; moderate similarity; disagreement. |

Use one compound title/alias comparison so related name evidence is not counted twice as if independent. Splink’s `CustomLevel`, `ArrayIntersectLevel`, explicit null levels, and configurable comparison levels support this directly. [Splink](https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html?utm_source=chatgpt.com)

For a concrete first challenger, Jaro–Winkler boundaries of **0.95 and 0.85** are reasonable declared comparison bins for prose titles. They are starting policy choices to inspect, not semantic-equivalence thresholds. Keep controlled codes and formula symbols under their own normalization rules.

Additional changes:

- Strip a separately represented artifact designator from the title comparison.
- Preserve unknown aliases as unknown, rather than treating them as observed empty lists.
- Apply term-frequency adjustment initially to exact title agreement.
- Keep work/kind eligibility and explicit incompatibilities outside the evidence sum.
- Retain comparison levels and weight explanations for every scored pair.

### C. Train with the correct label population

One API detail materially changes the implementation: **`estimate_m_from_pairwise_labels` assumes every supplied row is a positive match and ignores `clerical_match_score`.** A mixed positive/negative assessment table must therefore be filtered before it reaches that API. [Splink](https://moj-analytical-services.github.io/splink/api_docs/training.html?utm_source=chatgpt.com)

Estimate agreement probabilities from independently supported same-lineage pairs. Use rejected pairs to assess false links and ranking, and estimate nonmatch behavior within the relevant eligible population. Do not let impossible cross-work pairs dominate the nonmatch distribution.

For comparison levels with insufficient observations, retain explicit provisional parameters. Keep candidate-generation assessment separate from scoring assessment: broader nomination should be judged on newly reachable supported pairs; improved scoring should be judged on the ordering and explanation of comparable pairs.

## 6. Turn existing relationships into navigation, gap reports, and richer dossiers

### A. Add comparison-to-root bindings

Rooted dossier construction currently excludes comparisons because their sides have clause fields but no definition-sense endpoint. Simply removing that exclusion would admit comparisons without establishing relevance to the root. [Dossier construction](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/methods/structural_products.py)

Add a retained binding containing:

- Comparison reference and side.
- Exact component reference.
- Supporting relationship decision.
- Applicable premise references.
- Original citation.

Then a comparison side can enter a dossier as a variant, exception, revision, or conflict. The opposite side remains available as comparison context, without automatically inheriting the root’s sense.

For dependencies, admit explicit semantic `depends_on` relationships with compatible scope and qualified endpoints. Computational dependencies—such as a product’s dependence on an embedding file—remain separate.

### B. Add a similarity neighborhood without changing identity groups

Keep the existing exact semantic target groups. Add a separate navigation product over the existing pinned embeddings:

1. Compute cosine neighbors using `NearestNeighbors(metric="cosine", algorithm="brute")`.
2. Initially retain **mutual top-five neighbors**.
3. Store both ranks, distance, representation digests, and embedding profile.
4. Display the similarity reason alongside separately typed source-supported links.

The neighbor operation is directly supported by scikit-learn. The choice of mutual top-five is a proposed bounded navigation policy; it makes no identity claim. [scikit-learn 1.9.1 documentation](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.NearestNeighbors.html?utm_source=chatgpt.com)

I would initially expose ranks and distances rather than impose an unvalidated universal similarity cutoff. Qualitative inspection can then identify whether weak neighbors warrant a radius restriction. Do not turn connected components of this graph into equivalence classes.

### C. Implement three specific gap reports

| Report | Exact question | Useful output |
|---|---|---|
| **Unresolved binding** | Does this retained reference or symbol use have a uniquely selected compatible target? | Source occurrence, candidate targets, and whether the issue is no candidate or ambiguity. |
| **Unknown applicability premise** | Which required scope, parameterization, convention, version, or sense premise remains unknown? | The dimension, reason, and supporting source material. |
| **Unconnected supported comparison** | Does an independently supported comparison lack a retained binding to a concept/root? | Comparison sides and the missing binding operation. |

These can be read-only projections over existing typed products. They do not require a general completeness engine.

Every report must state the inspected selection and operation status. “No selected declaration link” is a meaningful finding; “the document contains no declaration” is a stronger claim that the same query does not establish. Failed or unrun operations should produce an unavailable state.

I would also defer the proposed MILP dossier-selection work. The immediate opportunity is to establish more justified membership relationships; optimization becomes useful when there is a real conflict between eligible content and a display budget.

## 7. Fit an event the pipeline actually emits

This is the most important correction to the statistical recommendation.

The recorded availability census contains **82 `definition.defining_text_attachment` relations**, while the fitter’s existing `relation.defined_by` event has no compatible emitted rows in that selected cohort. It also reports no matching protected event evaluations. [Operation-fitting evidence](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/README.md)

### The selected event

Add an event such as:

> Is this directed attachment between these exact term and defining-content occurrences supported within the scope actually claimed by the emitted relation?

Extend the event contract consistently in:

- [`evaluate/operation_fitting.py`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/evaluate/operation_fitting.py)
- [`semantic/operation_policy.py`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/operation_policy.py)
- [`semantic/sql/operation_event_fitting.sql`](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/python/corpus-structure/src/corpus_structure/semantic/sql/operation_event_fitting.sql)

Retain separate judgments for term role, content role, attachment, and claimed scope. Missing additional information remains a separate extraction gap; this event does not require a complete structured recreation of the surrounding knowledge.

An incorrect attachment must not discard an independently useful term or content component.

### The initial feature and model specification

Use four source-derived features:

1. `log1p(term_character_length)`.
2. `log1p(defining_content_character_length)`.
3. Signed content-to-term gap, divided by the inspected passage length.
4. Presence of a versioned definitional cue, such as “is defined as,” “is called,” “we call,” or “denoted by.”

Compute them from emitted source anchors and frozen source context. Evaluator judgments and reference-overlap scores must not become features.

Reuse the existing `StandardScaler → LogisticRegression` pipeline and current defaults: `C=1`, `lbfgs`, tolerance `1e-6`, maximum 2,000 iterations, and unit observation weights.

The model estimates:

\[
P(Y_i=1\mid z_i)=\operatorname{logit}^{-1}(\alpha+\beta^\top z_i).
\]

Compare it with the class-prior baseline. Report event counts by judgment state, convergence, coefficients, Brier score, log loss, and the underlying facet errors. Ambiguous and unassessed events are not negatives; repeated executions of the same event are not additional independent observations.

This is a bounded development fit. It does not need a new corpus or an agent-task evaluation, and unavailable fitting parameters should not block the structural outputs.

### Where Pyro fits

The first Pyro challenger should be **Bayesian logistic regression over the same event and features**:

\[
\alpha\sim N(0,1.5^2),\qquad
\beta_k\sim N(0,1),\qquad
Y_i\sim\operatorname{Bernoulli}
\left(\operatorname{logit}^{-1}(\alpha+\beta^\top z_i)\right).
\]

Those are proposed regularizing priors on standardized features. Check a narrower and wider coefficient prior to reveal sensitivity.

For this small continuous model, use `NUTS` and `MCMC`, initially with four chains, 1,000 warm-up steps, and 1,000 retained draws per chain. Inspect divergences, effective sample sizes, and split-\(\hat R\); Pyro exposes the relevant diagnostics. [Pyro documentation](https://docs.pyro.ai/en/stable/mcmc.html?utm_source=chatgpt.com)

Return posterior probability means and credible intervals through a separate algorithm/output contract. Substituting posterior mean coefficients into the current logistic scorer does not generally produce posterior mean probabilities.

I would **not add source/producer random effects immediately**. Seventeen policy executions over the same source are not seventeen independent source groups. A hierarchy becomes justified when a named mechanism—such as repeated layout contexts—shows shared residual error that the available judgments can distinguish from ordinary features or producer changes.

## 8. Specify the joint-inference question before adopting pgmpy

### The current coupling needs a narrower interpretation

The existing coupled table policy awards a bonus when all linked choices select supported readings. That is an authored joint preference; it does not, by itself, establish a statistical model of dependence.

The recorded marginal-role experiment already has both weighted modes selecting all nine supported readings. Differences in their probabilities therefore do not demonstrate better interpretation on those cases. [Table-policy evidence](https://github.com/paul-heyse/corpus-structure/blob/88fd5d108015e471758e6d3fcd4109fa88d9114a/docs/design_review/evidence/2026-11-06_wce-completion-repair/table/README.md)

### A concrete next model

For the bounded existing table example, model:

- \(M\): the retained correspondence between a schematic explanation and the observed cells.
- \(R_j\): the role of each selected cell.
- A factor linking each role to that shared correspondence.

\[
P(M,R\mid E)\propto
\phi_{\text{correspondence}}(M;E)
\prod_j\psi_j(M,R_j;E_j)
\prod_h H_h(M,R).
\]

The shared correspondence evidence enters once. Each cell can remain unresolved independently. Hard masks express source-established impossibilities.

This also gives a useful pattern for later linguistic interpretation: several propositions may depend on the same scope declaration, convention, or attribution. The shared variable should represent that particular uncertainty. If the source already establishes it exactly, represent the established fact directly.

For learned weights, start with a small conditional log-linear model over independently judged acceptable assignments:

\[
L(\theta)=
\sum_i\left[
\log Z_i(\theta)
-
\log\sum_{x\in A_i}e^{\theta^\top f_i(x)}
\right]
+\frac{\lambda}{2}\|\theta\|^2.
\]

Here \(A_i\) is the set of assignments compatible with the source judgment. Partial judgments leave unspecified decisions marginalized.

Use the existing enumerator for the partition sums, SciPy `logsumexp` for stable arithmetic, and `minimize(method="L-BFGS-B")` with the feature-expectation gradient. Begin with only correspondence and compatibility weights, with declared ridge regularization. [SciPy v1.18.0 Manual](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html?utm_source=chatgpt.com)

### The actual pgmpy adoption criterion

Keep the existing exact log-space interpreter until a useful policy exceeds its 65,536-state guard and has a factorization with manageable intermediate factors.

For that case, use `DiscreteMarkovNetwork` and `DiscreteFactor`, because the current model supplies potentials. The adapter must preserve normalization, overlapping event unions, coherent alternatives, unresolved states, cancellation, and failure semantics.

Two implementation details matter:

- The inspected `VariableElimination.query` path returns an **unnormalized** factor for a discrete Markov network. [pgmpy](https://pgmpy.org/_modules/pgmpy/inference/ExactInference.html?utm_source=chatgpt.com)
- `get_partition_function()` forms the full factor product before summing, so it does not supply the intended scalable normalization route. [pgmpy](https://pgmpy.org/_modules/pgmpy/models/DiscreteMarkovNetwork.html?utm_source=chatgpt.com)

A variable-elimination adapter therefore needs an explicit normalization strategy and numerical checks. Numerical underflow must remain distinguishable from genuinely zero support.

## 9. The implementation sequence I would now recommend

I would organize the next work into four increments:

| Increment | Concrete scope | Layer-level evidence of value |
|---|---|---|
| **1. Recover and qualify source structure** | Caption projection; role extents; qualifier ownership; scoped negation. | Known omissions recovered; correct content retained; qualifiers attached to the right hosts. |
| **2. Improve semantic interpretation** | GLiNER descriptions; clause classification; multivalued comparison fields. | Fewer role confusions and truncations; clearer distinction between instructions, descriptions, assumptions, and examples. |
| **3. Connect and assemble** | Scoped cross-view nominations; richer Splink comparisons; comparison-to-root bindings; gap reports and similarity navigation. | Newly reachable supported links; fewer false links; justified dossier membership; identifiable stranded evidence. |
| **4. Learn specific uncertainties** | Attachment-event logistic fit; optional Bayesian challenger; bounded shared-correspondence model. | Interpretable event predictions and uncertainty, assessed against the exact operation being modeled. |

The first three increments can deliver useful structure continuously. The statistical work should refine particular decisions and expose uncertainty around them.

**My revised priority is to complete the source-to-role-to-relationship chain first, while making the emitted attachment event available for a small learning experiment in parallel.** That gives spaCy, GLiNER, Splink, and the existing analytical machinery concrete additional work to do—and gives pgmpy and Pyro precisely defined roles when their capabilities become useful.