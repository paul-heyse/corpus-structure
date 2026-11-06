**I would make the next increment about deriving and checking relationships from retained evidence. I would start with spaCy and GLiNER2.5, use the existing mathematical executor for one real ambiguity, introduce Splink for a well-defined identity problem, and reserve pgmpy and Pyro for two different problems: tractable joint inference and learning about correlated errors.** The latest results give a fairly clear reason for that order.

I reviewed [`corpus-structure` at commit `bc2208f9`](https://github.com/paul-heyse/corpus-structure/commit/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b), including the PCE-00–11 coordinator, execution and assessment receipts, parser and retrieval implementations, structural products, numerical interpreter, identity resolution, and publication contracts. I used the relevant sections of the ten attached library references to assess what those libraries could add. This is a source-and-results review; I did not rerun the corpus, train a model, or change the repository.

## What the latest results say

The new implementation substantially changes my assessment from the earlier M1 review. You now have evidence that **additional correct structure can be recovered without requiring a complete record or a new parser**. You also have enough diagnostic detail to tell where additional modeling would be misplaced.

| Observed result | What I would do with that evidence |
|---|---|
| Historical replay retained **5,099 products**, including 1,136 occurrences, 3,269 proposals, 437 composites, and 25 derived relations. The 2,272 located observations referred to **447 physical occurrences**. | Work outward from distinct source occurrences and their available roles and relationships. Repeated predictions over the same words are useful alternatives or corroborating features, but they are not thousands of independent facts. [Foundation receipts](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-foundations/README.md) |
| On the same 92 source-first facets, the revised processing improved **16 supported → 30 supported**: 13 newly supported table-header attachments and one literal. Fifty-eight remained unsupported or not captured; four contextual symbol roles remained unassessed. | This is the strongest demonstrated pattern to repeat: locate the missing *relationship*, use the structure already surrounding its endpoints, and evaluate the new edge independently. The 338 added private attachment proposals were not 338 correct facts. [Paired local assessment](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-local-capabilities/README.md) |
| With **17 supplied mentions, eight passages, and 20 curated targets**, lexical retrieval captured 16 correct targets; dense/hybrid retrieval captured 17. E5 and Qwen3-Embedding-0.6B each yielded 16 supported denotations and one abstention. The independent assessment identified **14 additional passage relationships beyond denotation**. | The next linkage opportunity is to connect *automatically found occurrences* and produce more kinds of evidenced relationships. A larger embedding model would not fix the demonstrated abstention: the correct target was already present. This comparison does not settle larger-scale encoder choice. [Retrieval and admission results](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-local-capabilities/README.md) |
| In automatic definition runs 51/52, **only one of nine emitted positive readings was supported**. Eleven negative readings were supported. Seven errors treated nondefining or unrelated passages as applicable definitions; one upgraded a relevant explanation into a definition. The relevant targets ranked 2 and 9. | **Definition applicability is the first semantic defect I would fix.** It is a classification and attachment problem on these fixed pairs. More retrieval, another parser, or a better-calibrated version of the same unsupported judgment would not address the underlying defect. [Machine-readable quality result](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-structural-products/records/pce.automatic-quality.json) |
| Run 98/cut 132 admitted **four independently reviewed supplied structural statements** under three policies. Earlier local publication admitted 16 denotations and 33 source events with zero whole-record assertions. | The project has demonstrated independent publication of useful structure. The opportunity now is to **produce more of the inputs automatically** while preserving the same evidentiary standard. The four supplied statements do not establish automatic comparison or dossier quality. [Structural qualification](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-structural-products/README.md) |

My main architectural conclusion is that **your repository is now better at retaining, transporting, and assessing a structural judgment than it is at generating the evidence for some of its most valuable judgments**. That is a good position to be in: the next work can target specific missing semantics instead of building another general infrastructure layer.

## 1. Highest priority: make definitions and other relationships carry their own evidence

The clearest example is [`definition_applicability.py`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/definition_applicability.py). The implementation already gives GLiNER the usage passage, target passage, question, scope, and versions. It already distinguishes `applicable_definition`, `applicable_explanation`, `mention`, `example`, `ambiguous`, and `insufficient_support`. It explicitly asks the model to avoid confusing topical similarity with applicability.

What it does **not** require is a located answer to three different questions:

1. **What does the target passage define or explain?** Locate the term or expression and the words, formula, or structural element providing its meaning.
2. **What does the source usage refer to?** Locate the occurrence, its proposed sense, and any parent concept, parameter, or local convention that distinguishes it.
3. **Why does the target apply to this usage?** Establish the relevant sense and scope match, or identify the specific mismatch or unresolved choice.

Today, `decode_applicability` can attach a valid category to the pair of passage IDs with a generic reason. That is enough to reproduce the model’s judgment; it is insufficient to show *which part of the judgment is right*. A passage can define X, explain Y, and merely mention Z. Its function has to be assessed **relative to the particular occurrence**, not assigned once to the passage as a whole.

**I would introduce a small structural product: a relation with named endpoints and an inspectable basis.** For a definition, it would contain the defined-term occurrence, defining text or expression, evidence for their attachment, usage occurrence, sense/scope compatibility, and unresolved alternatives. An explicit cue such as “is defined as” is one possible basis. A glossary layout, mathematical declaration, or apposition can provide another. Failure to find a particular cue must not become a negative assertion that the source provides no definition.

This also prevents another all-or-nothing outcome. The system may correctly establish **“passage B defines arithmetic mean”** while remaining uncertain that a particular use in passage A denotes that concept. Retain the first result. Conversely, a well-supported denotation can coexist with an explanation that is useful but not definitional. If you want to admit one of those component assertions independently, give it its own evaluated operation and scoped publication policy rather than weakening the whole-report policy in [ADR-0065](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/adr/0065-cross-source-structural-products.md).

### The immediate spaCy opportunity is unusually concrete

[`PreparedAnnotationRules`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/annotation_rules.py) already supports `Matcher`, `PhraseMatcher`, and `DependencyMatcher`. It returns ordered matched nodes, exact extents, sentence and source-piece references, preserves overlapping matches, and checks dependency availability. But [`M1Config` and its producer](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/m1_source.py) expose and pass **only `annotation_token_rules`** on this path.

**I would wire phrase and dependency rules into the versioned producer configuration and add named bindings from matched nodes to semantic roles.** The second part matters more than simply enabling another API. A successful dependency match should be able to say *this node is the defined term, this is the defining predicate, and this subtree supplies the proposed defining expression*. Dependency-pattern order need not match surface word order; preserve the mapping explicitly. This can run over a reconstructed `Doc` from retained annotations without re-tokenizing the source or rerunning the statistical parser. [Existing composition evidence](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-parser-composition/README.md) · [spaCy API Documentation](https://spacy.io/api/dependencymatcher?utm_source=chatgpt.com)

I would start with a few constructions whose output can be independently judged:

| Construction | Structural output | Important counterexample |
|---|---|---|
| “X is defined as Y”; “we call Y X” | Term, defining expression, cue, direction and scope | “X is discussed below” or “X is useful”: a copula or mention alone does not define X |
| “Let \(s\) denote …”; “where \(n\) is …” | Symbol occurrence, declaration candidate, meaning and local scope | The same symbol in the next example has a different binding |
| “Under C, P”; “P unless E” | Condition or exception, governed predicate, scope boundary | A qualifier in an adjacent sentence governs a different assertion |
| “A must approve B before C” | Actor, action, object, obligation cue, prerequisite or ordering candidate | A passive construction reverses the surface order of actor and object; an example describes past behavior rather than prescribing it |

These rules would propose structures; they would not silently declare all matching constructions correct. Their value is that their errors become legible: wrong head, overextended defining phrase, wrong governing predicate, or missing scope.

### Use GLiNER as a complementary evidence producer

The project already runs native local entities, mention attributes, and directed relations, in addition to record extraction and classification. The whitespace run’s 107 distribution spans, 107 role labels, and 43 relation proposals establish that this machinery executes. They do not establish that those roles or relationships are correct. On the separate output audit, both wrong role labels called a *mentioned term* a *defined term*. [Local parser receipts](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-local-capabilities/README.md)

For the first experiment, compare four methods on the **same candidate lists**:

- Current whole-pair GLiNER classifier.
- Retained spaCy/structure witnesses alone.
- A compact GLiNER schema applied locally to the target, extracting term, defining expression, explanation, or example roles.
- A composed decision using the located witnesses, usage denotation, and scope.

Grade target-span discovery, role assignment, defining-expression attachment, applicability, and abstention separately. Check whether the revision removes the seven incorrect positive judgments, preserves the supported arithmetic-mean result, and describes the normal passage as an explanation where warranted. Treat those cases as exposed regression material; freeze fresh cases before making an efficacy claim.

**I would use GLiNER JointIE only if you observe the specific condition it addresses:** the correct endpoints regularly exist, but independent decoding chooses invalid types, directions, or pairings. If the right span never enters the candidate pool, test source/rule-supplied span scoring or a targeted window instead. If the defining source is absent, neither decoder can solve the problem. GLiNER attributes operate on retained mentions, and JointIE feasibility applies to its bounded candidate graph; neither supplies independent proof of a semantic reading. [GitHub](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/13-span_attributes.md?utm_source=chatgpt.com)

## 2. Increase connectivity by joining existing outputs at the right grain

I would make three changes here before adding another learned component.

**First, connect detected mentions to the existing linker.** [`contextual_candidates.py`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/contextual_candidates.py) takes `SuppliedMention` cases. Its denotation witness is created from a full registry-label or alias match. That makes the current experiment an effective isolated test of retrieval and selection, but it leaves a gap between the real parser and the real linker.

Add a second input route from actual located GLiNER/spaCy occurrences. Keep the supplied-mention route as the control. You can then distinguish:

- The parser missed the mention.
- The mention was found with the wrong boundary or type.
- The inventory lacked the intended target.
- The target existed but retrieval missed it.
- Retrieval succeeded but the available evidence did not justify selection.

For the observed normal-density abstention, that final distinction is essential. A better embedding score does not create a nonlexical semantic witness, and more confidence cannot supply a missing density definition.

**Second, produce typed links beyond `denotes`.** [`contextual_links.py`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/semantic/contextual_links.py) already represents `denotes`, `alias-of`, `defined-by`, `specializes`, `compared-with`, and `participates-in`. The larger opportunity is to implement producers that establish particular instances of these relationships from located source evidence. I would use the 14 independently identified non-denotation relationships as a starting inventory: categorize them, determine which ones have reconstructable endpoints and cues, and implement the best-supported families first.

There is a design detail worth fixing at the same time. The selector currently treats more than one distinct `(target, relation)` alternative as ambiguous. That is sensible for mutually exclusive senses answering *“which concept does this mention denote?”* It is too restrictive for a passage that legitimately **specializes one concept and compares it with another**. Scope exclusivity to the question or role. Permit multiple compatible edges while preserving genuine alternatives and existing identity exclusions.

**Third, compose qualified paths and report what they actually establish.** For example:

- A cell belongs under a specific header; the header supplies a unit; a note governs only a subset of rows. The result can be a **qualified value with an inspectable inheritance path**, even if the row’s canonical entity is unresolved.
- A formula contains a symbol; a nearby clause declares that occurrence; the declaration refers to a scoped parameter. The result can link **formula → symbol use → declaration → parameter** without asserting equivalence to every occurrence of the same glyph.
- A procedure step names a form; a source-backed alias links that form to a controlled document; a later clause specifies a prerequisite for that step. The result can expose **which document and prerequisite govern that step** without reconstructing the entire workflow.

Implement these as bounded joins on typed endpoints, source coordinates, and declared scopes—not arbitrary graph traversal. The existing [contribution adapter](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/contribution_adapter.py) already derives specific definition and table attachments. Extend it one relationship at a time, retaining the difference between an edge returned by a model, one proposed from group membership, and one justified by native geometry. Use the existing [finite inference owner](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/semantic/inference.py) only for admitted rules and premises—not to convert repeated or plausible paths into accepted facts.

## 3. Derive genuinely new information from tables, formulas, and revisions

This is where I see the strongest opportunity to increase **the quantity of meaningful insights**, as distinct from the quantity of annotations.

### Tables and formulas: infer attachments and constraints before fitting scores

Your [`native_table_geometry`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/source_preparation.py) already reconstructs nested header paths and preserves ambiguity when bands cross. The next work should be **row-label semantics, header-scoped units, footnote marker-to-note attachment, and explicit inspection coverage**. Three remaining header facets concern inspected *unstated* headers; generating more positive header links cannot close those cases.

Use deterministic constraints first. A note marker can narrow the admissible notes. A cell’s column and nested header path can rule out an otherwise nearby unit. If several alternatives survive, retain them. Report whether an attachment is forced under established and exhaustive premises, merely preferred among retrieved options, or still unknown. This produces additional partial structure without manufacturing probabilities.

For formulas, expose useful pieces of the existing Lark/SymPy analysis—operators, operands, bounds, binders, symbol occurrences and declarations—as **separate linkable products**. The repository already distinguishes syntax over captured native text from verified recognition and original glyph positioning; preserve that distinction. Four unassessed contextual prose-symbol roles need an operation and rubric for *what the symbol means here*. Producing another syntax tree cannot answer that question. [Parser composition and syntax evidence](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/design_review/evidence/2026-11-05_pce-parser-composition/README.md)

### Clause comparison: go beyond string difference

The current [`compare_clauses`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/structural_products.py) is a sound conservative baseline. It compares **supplied fields**. A missing field produces `unknown`; different scope/version produces `incompatible_applicability`; otherwise, it reports lexical equality or difference.

I would separate three dimensions that this currently combines:

1. **Lexical difference:** What words, numbers, or symbols changed?
2. **Typed semantic difference:** After a justified transformation, did the comparator, threshold, unit, actor, modality, or exception change?
3. **Applicability:** Are these two statements co-applicable, successive revisions, differently scoped, or not comparable from the evidence?

A concrete enterprise example illustrates the payoff. Suppose successive policy versions contain **“approval required above $25,000”** and **“approval required above $50,000.”** If the actor, currency, conditions, exceptions, and interpretation of *above* are verified, the system can derive:

> **The amount band whose treatment changed under this rule is \(25{,}000 < x \le 50{,}000\).**

That interval is **new structured information**. Neither passage contains it verbatim. The conclusion is reproducible from two sourced thresholds, two operators, and a declared comparison rule. The system can report it despite the versions not being simultaneously applicable. If a relevant exception changed or is unresolved, it should report the threshold difference and withhold the stronger applicability conclusion.

Use Lark for small routed grammars—comparators, intervals, uncertainty expressions, units, and identifiers—not unrestricted English parsing. Reuse the [existing scientific comparison kernels](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/semantic/scientific_evidence.py) where their assumptions fit. The [evaluator’s equivalence implementation](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/evaluate/equivalence.py) also contains useful comparator-direction and condition-tree normalization. Share reviewed pure semantics through the appropriate production owner; keep protected reference data out of the producer. [Lark documentation](https://lark-parser.readthedocs.io/en/stable/parsers.html?utm_source=chatgpt.com)

### Dossiers: optimize coverage after establishing membership

The current [`assemble_dossier`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/structural_products.py) takes supplied members, sorts them, and selects the first representatives per sense, role, scope, and version. It always retains exceptions, revisions, and conflicts. I would preserve that as the baseline and make two separate improvements:

- **Automate membership** from qualified definition, usage, comparison, and relationship products. Grade each added member against the original passage.
- **Select representatives for facet coverage.** Given a display budget, retain mandatory members, then choose passages that cover the most *additional supported facets*. Use the existing embeddings to break ties between redundant examples, not to establish membership.

This is a small maximum-coverage problem. Start with greedy selection; use [SciPy mixed-integer optimization](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html) if exact selection under interacting constraints becomes worthwhile. Compare against first-in-source-order at the **same budget**. Measure omitted senses, lost qualifications, distinct supported facets, redundant passages, and false membership. A better selector cannot repair a dossier that contains the wrong concept. [SciPy v1.18.0 Manual](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html?utm_source=chatgpt.com)

## 4. Where pgmpy, Pyro, and Splink actually belong

I would use these libraries for **three distinct questions**, each with different inputs and success criteria.

| Library | Question worth answering | My recommendation |
|---|---|---|
| **pgmpy** | Given several related uncertain choices in a local passage or table, which interpretations are compatible, and how do they affect one another? | **Design and test a real factor model now using the current solver.** Introduce pgmpy when exact sparse inference solves useful cases the current enumerator cannot. |
| **Pyro** | How does an operation’s reliability vary across source families, layouts, cue types, or recognition conditions, given uneven evidence and correlated outputs? | **Best longer-term statistical opportunity.** Use an evaluator-side hierarchical model after collecting independent judgments across enough groups. |
| **Splink** | Do two structured, multi-attribute records refer to the same real entity despite naming variation and imperfect fields? | **Run a bounded pilot when a suitable identity cohort exists.** It is a poor fit for the current definition-versus-explanation error and a promising fit for enterprise entities, artifacts, and scoped parameter records. |

### pgmpy: the missing piece is a good model of a real ambiguity

Your [`record_interpretation.py`](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py) already implements bounded exact log-space inference, individual marginals, composite events, coherent alternatives, dependency scopes, and explicit refusal. The [local interpretation consumer](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/methods/local_interpretation.py) returned `not_run` on the actual retained run **because no genuine factor policy was supplied**. No demonstrated useful sparse request exceeded the current guard. Installing pgmpy would not change either fact. [PCE mathematical implementation and decision criteria](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/plans/progressive-corpus-enrichment/parsing-and-mathematical-interpretation.md)

I would instantiate **one table interpretation problem** because there are already source-judged examples and a strong deterministic baseline:

- Decisions: header path, property described, applicable unit, target of a note, and value role.
- Evidence: native cell geometry, exact header text, explicit unit or note markers, caption text, and GLiNER role proposals.
- Couplings: a unit interpretation may fit one property and not another; a note may apply to several rows but only under one column band.
- Output: alternatives for individual attachments and an optional event such as *“this cell states this property in this unit under this note.”*

Test three levels: deterministic feasibility, independent choices, then coupled choices. A useful result is **a source-confirmed attachment corrected by the coupling, with a trace showing which independent evidence resolved it**. A failure is equally informative: the coupled model hardened an uncertain unit, double-counted a header and a model interpretation of that same header, or merely increased its score without correcting the attachment.

When real components become too large for full enumeration, pgmpy’s variable elimination is a sensible challenger. Its cost depends on induced width and factor cardinalities; a large sparse graph can be easier than a smaller densely coupled one. Compare against the current exact solver on identical factors, including infeasible cases, overlapping composite events, numerical stability, alternatives, and resource use. A MAP assignment alone would not replace the existing interface. [pgmpy](https://pgmpy.org/api/generated/inference/pgmpy.inference.VariableElimination.html?utm_source=chatgpt.com)

### Pyro: learn where the system is reliable

The most valuable Pyro model here is **not a probability that a proposition in a textbook or company policy is true**. It is a model of questions such as:

- When does a `defined_term` role from GLiNER agree with independent source review?
- Does a particular dependency construction improve attachment accuracy consistently across documents, or only in one author’s prose?
- Are unit and note attachments less reliable in tables with merged headers, even after the geometry rule passes?
- How much apparent agreement is explained by multiple outputs sharing the same source occurrence, window, or encoder?

A first model could estimate the probability of a **specific reviewed operation being correct** from operation type, cue family, layout and recognition features, with partially pooled effects for document or source family. Treat capture and correctness separately: a model of correctness among emitted links does not tell you how many links were missed. Compare it with a pooled regularized logistic baseline; inspect held-out group behavior, posterior predictions, and sensitivity to priors. Pyro supports partial pooling and exact enumeration of suitable discrete latent variables, but those are separate uses and need not enter production together. [Pyro Tutorials 1.9.1 documentation](https://pyro.ai/examples/baseball.html?utm_source=chatgpt.com)

**I would not fit that hierarchy to the current 20 applicability pairs.** They come from two usage contexts. Likewise, 64 facets from one table are not 64 independent examples of table-layout variation. The immediate investment that makes Pyro valuable is **collecting operation-specific judgments across different source groups, construction types, and hard negatives**. The existing [structural assessment frame](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/evaluate/structural_assessment.py) is explicitly development-scoped; extend the protocol deliberately for a genuine held-out assessment.

### Splink: use it for identity, not general semantic relatedness

Splink is appealing because you already retain multiple signals that can describe the same object. Its Fellegi–Sunter approach asks how much more likely a field agreement is for matching records than for nonmatching records. A match on a rare identifier can therefore carry more evidence than agreement on a ubiquitous word. Blocking and pair scoring are separate: a true pair omitted by every block cannot be recovered by a better match model. [Splink](https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html?utm_source=chatgpt.com)

I would choose one of these pilots:

| Candidate record | Fields that make the comparison meaningful | Important false match |
|---|---|---|
| **Scoped mathematical parameter** | Parent family, parameterization, role, domain, source-local symbol, declaration text | The same symbol used for different parameterizations; a rate and a scale treated as identical |
| **Enterprise form or controlled artifact** | Controlled identifier, normalized title, owner, process, business unit, version lineage | A checklist and the policy it implements; two versions confused with one identical document |
| **Asset or organizational entity** | Identifier, site, type, parent, known aliases, distinguishing attributes | Similar tags at different sites; a team confused with its parent organization |

For each pilot, **define identity before training**. “Same underlying form across revisions” and “same immutable document version” are different match targets. Use exact IDs, aliases and existing lexical/dense candidates to propose blocks or candidate pairs. Grade candidate inclusion separately. Then compare Splink’s pair scores against exact-key and lexical baselines, with hard negatives chosen for genuine semantic difficulty.

Three integration rules are important:

1. **Treat dependent signals as dependent.** Title, normalized title, alias overlap, and cosine over a description composed largely of that title are not four independent confirmations. Combine related comparisons or demonstrate their incremental value on held-out pairs.
2. **Use a meaningful eligible population.** Frequency adjustments, match priors, and EM estimates from the current tiny curated inventory should not be extrapolated to a company-wide registry. Preserve nulls and unknowns rather than scoring them as disagreements.
3. **Keep final identity authority in the existing resolver.** Splink should emit an attributable pair proposal and its field-level reasons. The existing [anchor and exclusion policy](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/adr/0029-identity-exclusions-scoped-reference.md) should still govern merges. In particular, one mistaken bridge between two groups must not collapse both through connected components.

For your current stats cohort, **better source-backed relationship production is a higher priority than Splink**. For the first enterprise corpus containing repeated assets, forms, systems, or scoped role descriptions, I would move Splink much higher.

## 5. How to assess whether the corpus actually became richer

I would extend the existing granular assessment with four explicit measures. They correspond directly to your goals of quantity, quality, connectivity, and synthesis:

| Goal | Measure |
|---|---|
| **Quantity** | Newly supported **distinct** occurrences, fields, and typed relations on the same independently specified source opportunities. Report regressions and newly spurious proposals separately. |
| **Quality** | Literal fidelity, semantic role, endpoint identity, direction, attachment, condition and scope—judged separately. A correct span with a wrong role gets credit for the span only. |
| **Connectivity** | Of independently identified cross-item or cross-document linkage opportunities, which now have a supported, correctly typed edge or path? Also inspect false bridges and unsupported merges. Raw graph density is not a success metric. |
| **Synthesis** | Which new source-supported conclusions require combining multiple retained products? Examples: an inherited table unit with its governing note; a formula parameter bound to a declaration; a changed threshold interval; a dossier that newly covers an exception without losing a conflicting version. |

For each proposed composition, run **A alone, B alone, and A+B on the same structural questions**. First hold candidate endpoints fixed to test the attachment logic. Then allow discovery to run so you can distinguish better candidate coverage from better interpretation. Keep a short before/after ledger of newly correct, corrected, lost, spurious, and still-undecidable cases. This gives you a direct empirical account of how parser outputs become more valuable in combination.

The remaining attached libraries have specific roles here:

- **scikit-learn:** Fit a transparent regularized baseline for a *particular* event—such as correct term-to-defining-expression attachment—once suitable labels exist. Your [existing fitter](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/evaluate/record_fitting.py) already addresses whole-reading events. Reuse the methodology, not the outcome labels, for a new event. Keep fitting and calibration separate. [scikit-learn 1.9.1 documentation](https://scikit-learn.org/stable/modules/calibration.html?utm_source=chatgpt.com)
- **SciPy:** Use constrained assignment where the source semantics warrant it—for example, aligning one-to-one counterpart clauses across two revisions, with an explicit unmatched option. Allow split/merged clauses outside that assumption. Do not impose one-to-one assignment on table notes or definitions that may validly apply to several targets. The project already uses SciPy for alignment and [grouped or finite-population evaluation](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/python/corpus-structure/src/corpus_structure/evaluate/record_statistics.py). [SciPy v1.18.0 Manual](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html?utm_source=chatgpt.com)
- **statsmodels:** Once there are enough independent groups, use grouped regression or GEE to diagnose associations between error rates and observable conditions such as table layout or construction type. This can distinguish a broad recipe improvement from a gain concentrated in one source. The current small, purposive cohorts are better served by case-level findings. [statsmodels 0.15.0](https://www.statsmodels.org/stable/gee.html?utm_source=chatgpt.com)
- **ppi_py:** Useful later for a precise population question, such as *“What proportion of all emitted header attachments in this frozen cut are correct?”* Use predictions over the population and an independently reviewed probability sample to correct their average error, with appropriate handling of grouping and sampling. Keep targeted error-review sets separate. The prioritized 24-output sample is valuable for finding defects; it does not become a population estimate by passing it to PPI. [ppi_py 0.2 documentation](https://ppi-py.readthedocs.io/en/latest/?utm_source=chatgpt.com)

## Recommended next increment

I would scope the next implementation around **three deliverables**, with one parallel data-expansion track:

| Deliverable | What to implement | What would establish value |
|---|---|---|
| **1. Witnessed definition and relationship production** | Wire spaCy phrase/dependency rules and named bindings; derive target-local GLiNER term/expression candidates; connect actual detected mentions to contextual linking; preserve separately assessable relation components. | Fixed-list F37 error diff, followed by fresh source-first and output-first judgments. Show which wrong definitions disappeared, which valid definitions or explanations survived, and which new edges are source-supported. |
| **2. Table, symbol, and clause composition** | Extend scoped attachment rules for row labels, units, notes, declarations, and conditions. Add small grammars and typed comparison results alongside lexical differences. | On held-fixed source cases, show newly supported attachments, resolved versus genuinely ambiguous alternatives, and at least one reproducible derived comparison with complete premises. |
| **3. One real coupled interpretation policy** | Choose a recurring ambiguity from deliverable 1 or 2; compare deterministic feasibility, independent decisions, and a coupled model using the existing solver. | Demonstrate a source-confirmed structural distinction the coupling resolves—or document that the simpler method is sufficient. Invoke pgmpy/Pyro backend work only if a real workload or statistical question justifies it. |
| **Parallel: expand the reference material deliberately** | Add source passages that actually contain normal-density, standard-normal, and parameterization distinctions; add a small enterprise packet with recurring entities, procedure steps, exceptions, and revisions. Freeze operation-specific judgments independently of outputs. | Resolve the [F39 source-coverage limit](https://github.com/paul-heyse/corpus-structure/blob/bc2208f9d6a12d3ad9cf71575fa1c6df388d885b/docs/plans/progressive-corpus-enrichment_2026-11-04.md). Create a legitimate basis for testing transfer, Splink identity matching, and eventually hierarchical reliability. |

**If choosing one engineering change first, I would build the named-witness path from retained spaCy/GLiNER occurrences into definition and typed-relation products.** It addresses the clearest observed error, uses information already collected, can create useful structure even when final interpretation remains unresolved, and supplies the variables and judgments that make pgmpy, Pyro, and Splink worthwhile later.