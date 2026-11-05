I would remove the agent-task benchmark from the milestone entirely. I was wrong to make agent performance a release criterion after you had specified first-principles evaluation. **The intended consumer tells us which structures are worth producing. The source material and the specification for each operation tell us whether those structures were produced correctly.** That applies to intermediate outputs, final outputs, and decisions about adding another parser.

I would revise M1 to say:

> **Progressively enrich the corpus with source-grounded, independently assessable structure. Each operation must declare what distinction or relationship it adds, preserve the evidence for its output, and support a granular assessment of what it captured, missed, misidentified, or linked incorrectly. A useful contribution can be retained even when a subsequent operation fails to assemble a complete record.**

### What this means for the existing implementation

The current run gives a particularly good illustration. In the repository’s *memoryless* probe, GLiNER located the term `memoryless`, returned no defining text under the core-only schema, and proposed `qs` from a formula suffix as an alias. A whole-definition grade collapses those into one failed record. A structural evaluation preserves three separate findings: [probe and source evidence](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/design_review/evidence/2026-11-04_m1-state-inspection/README.md).

| Operation | Finding | Consequence |
|---|---|---|
| Locate the term occurrence | `memoryless` was located at the correct source span. | Retain the occurrence. This is a successful piece of structure. |
| Extract its defining passage | No defining text was returned. | Record a miss on this example. Investigate clause boundary detection, context, or record formation. |
| Link an alias to the term | `qs` was located in the source, but the proposed alias relationship is unsupported. | Preserve the raw observation for diagnosis; do not expose the alias as an established link. Test attachment to unrelated formula text. |

The important point is that **the same output can be correct as a span, wrong as a semantic role, and wrong again as a relationship**. Nor should the successful span receive credit for a definition that was never extracted. That is the level of discrimination I would carry through the system.

## 1. Give each structuring operation its own contract and assessment

I would organize evaluation around the **operation being performed**, rather than around the model or the final record family. GLiNER can contribute to several operations; several parsers may contribute to one operation. “GLiNER performed well” is consequently less informative than “term boundaries improved, while alias attachment regressed.”

| Structuring operation | What the evaluator inspects | Example of a useful finding |
|---|---|---|
| **Source reconstruction and segmentation** | Text fidelity, reading order, section membership, list boundaries, table coordinates, formula placement | “The exception paragraph was retained, but assigned to the preceding section.” |
| **Mention discovery and boundaries** | Whether relevant occurrences were found and whether their spans include exactly what the role requires | “Detected the amount but omitted ‘up to,’ losing the bound.” |
| **Semantic typing and role assignment** | Whether a located occurrence has the correct type or contextual role | “Both departments were found; Finance is the approver and Procurement is the requester. The roles were reversed.” |
| **Term normalization and concept linking** | Surface form, proposed normalized term, candidate target set, selected concept, and legitimate unresolved/new-concept cases | “The correct concept was retrieved but not selected”; separately, “the correct concept was never considered.” |
| **Relation extraction and attachment** | Predicate, direction, endpoint identities, evidence for the relationship, and competing attachments | “The form and procedure were correctly identified, but the form applies to onboarding, not renewal.” |
| **Qualification and scope** | Which statement or step a condition, exception, negation, threshold, or attribution governs | “The emergency exception was extracted verbatim but attached to every approval step instead of one.” |
| **Record or workflow assembly** | Whether individually correct fields belong together; whether order, prerequisites, alternatives, and unresolved fields are represented faithfully | “All three steps were found, but two alternative paths were serialized as consecutive mandatory steps.” |
| **Cross-document consolidation** | Correct merges, false merges, missed equivalences, version boundaries, and preservation of distinct source occurrences | “The policy and its revision describe the same workflow, but their approval thresholds should remain version-specific.” |

For concept linking in particular, I would **always distinguish discovery, candidate generation, and selection**. If the system misses an occurrence, improving the linker cannot help. If it detects the occurrence but its domain dictionary lacks the right concept, a better ranking model cannot help. If it retrieves the right concept and then selects the wrong one, that is a useful test for the interpretation layer. A single linking score hides three different engineering decisions.

The final structured representation gets an assessment of its own, still directly against the source. A workflow can contain individually correct steps and an incorrect dependency; a table can contain correct values bound to the wrong headers. These are **structural integration errors**, observable without asking an agent to perform anything.

## 2. Use source-first review and output-first review together

For every operation, I would use two review directions:

- **Source → structure:** Select a bounded source passage, table, list, or document pair independently of parser output. Identify the relevant structure at the layer under review, then inspect what the system captured or missed. This catches silent omissions, including passages where nothing was emitted.
- **Structure → source:** Select emitted mentions, classifications, links, or records and inspect their cited source. Determine whether the literal, type, association, and scope are supported. This catches invented links, incorrect classifications, duplicate structure, and plausible-looking records assembled from unrelated evidence.

This does **not** require authoring a complete structured replica of a book or company corpus. The evaluation unit can be deliberately narrow: *all explicit term definitions in these sampled passages*, *all approval-role assignments in these procedures*, or *all header-to-cell bindings in these tables*. That gives a meaningful denominator when one is wanted, without pretending all knowledge in the document has been exhaustively enumerated.

Where quantification is premature, the review should remain qualitative and structured. A finding such as **“in three multi-actor clauses the system consistently assigns the first organization as approver, even when the verb assigns approval to the second”** is more actionable than a small-sample aggregate accuracy estimate. Preserve the examples, evidence, and suspected failure mechanism; mark the inference about cause separately from the observed error.

## 3. Make changes assessable at the layer they affect

For a change to a schema, parser, context policy, or inference rule, I would require a **before/after structural diff** on the same source cases:

| Diff category | What the review should show |
|---|---|
| Newly captured | The exact previously missing span, role, concept, relation, or qualifier now produced correctly |
| Corrected | The old and new interpretations, with source evidence showing why the new one is better |
| Regressed | Previously correct structure now missing, mistyped, mislinked, or overextended |
| Newly spurious | Additional output that looks structurally valid but lacks source support |
| Still unresolved | The remaining ambiguity, missing context, missing candidate, or inability of the schema to express the source |

Run the comparison in two modes when dependencies matter. **First, hold upstream inputs fixed** to isolate the changed operation—for example, give two linkers the same mentions and concept candidates. **Second, rerun the affected downstream structural stages** to see whether a corrected link survives assembly or introduces a bad merge. Both evaluations concern inspectable corpus structure. Neither requires an end-user task or a judgment about answer quality.

For each finding, the durable evaluation record can be compact: **source anchor; operation and version; expected structure or permissible alternatives; actual output; judgment; error category; supporting explanation; and old/new disposition.** A human or an LLM assessor can author the explanation. The assessor’s job is to compare a specific output with specific evidence under a declared rubric.

## 4. Change the immediate M1 work order

I would make four concrete changes to the [current M1 coordinator](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/plans/first-production-milestone_2026-11-03.md):

1. **Keep the existing complete-record grade and narrow its interpretation.** The development result—190 missing reference occurrences, 80 matching table occurrences unaccepted, zero accepted readings—is a real result for complete-reading qualification. It does not tell us the precision of term spans, concept links, table values, or header attachments. In particular, the 80 table matches are the first place I would inspect individual bindings: cell identity, value, header path, unit, note, and row semantics. Determine which parts are right before deciding what needs repair. [Protected assessment](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/design_review/evidence/2026-11-04_m1-independent-assessment/README.md)
2. **Make independently located GLiNER outputs assessable before record assembly.** The current [family-pack compiler](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/python/corpus-structure/src/corpus_structure/methods/record_packs.py) is organized around structured record fields. Preserve that path, but expose the attributable mentions, field proposals, and relation candidates at their own level. Where the existing reports contain them, assess retained outputs first. Where a native call emitted no candidate or did not expose the relevant stage, record that limit rather than inferring why it failed.
3. **Replace the all-five-families product gate with independently qualified structural capabilities.** A term inventory can qualify as a term inventory. A table value can qualify as a source-located value while its unit remains unresolved. A proposed concept link stays provisional until its own evidence supports it. Complete-record acceptance remains available for the stronger claim. The release manifest should say exactly which operations and source populations have been assessed.
4. **Select the next parser or schema change from recurring structural errors.** Missing mentions point toward discovery or source preparation. Correct mentions with missing concept candidates point toward ontology or retrieval coverage. Correct candidates with wrong selections point toward disambiguation. Correct fields with wrong relationships point toward grouping or attachment. Unsupported source distinctions point toward a representation change. This gives each proposed addition a specific problem to solve and a direct way to judge whether it solved it.

**The revised completion criterion is a versioned corpus enrichment with a source-grounded account of what structure was added, which parts are correct, what remains missing or uncertain, and how each change affected those judgments.** Enterprise use determines why approvals, exceptions, responsibilities, and workflow dependencies deserve priority. Their evaluation remains a direct examination of whether the system represented them faithfully.

# Question on using embeddings

**Yes. I would add embeddings to the revised first milestone, with one specific first job: given a term or entity mention at a known source location, retrieve the concepts it could refer to.** That fills a gap between GLiNER extraction and corpus consolidation. GLiNER can identify *what was said here*; the embedding layer can find *where else the corpus describes something similar, even in different words*; the linker can then assess *what relationship the evidence actually supports*.

I would make **concept linking the first implementation, clause and workflow alignment the second, and source-grounded concept digests the first cross-document product**. None of these needs to wait for accepted whole records. Each can be evaluated directly against the source.

## Where this fits in your existing design

The repository already contains much of the right conceptual decomposition. [D4’s M04 and M14 method specifications](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/design/D4-method-catalog.md) distinguish **computing embeddings** from **proposing concept links**. M04 treats a vector as derived data, not a source assertion. M14 combines normalized aliases, lexical matching, and vector neighbors against a *frozen reference inventory*, so an extraction cannot become evidence for its own correctness.

The [S7 embeddings and linking plan](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/plans/design-spikes-s0-s1/S7-embeddings-linking.md) also asks the right experimental question: **which correct links do vectors recover beyond aliases, lemmas, and fuzzy matching?** It even calls out a meaningful hard case: a fuzzy matcher can mistake *normal distribution* and *standard normal distribution* for the same concept. S7 is a proposed study on the older Siegrist inputs, not evidence that an embedding linker is already working in M1.

I would revive that study with two changes: **use the current source-anchored PDF products, and evaluate contextual mentions rather than predominantly embedding aliases or whole paragraphs.** I would also preserve an existing [design decision](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/target-pipeline-design/registers/design-questions-and-decisions.md#notion-40b141b5836981bd8742d2195fc16a53): embed *claims* after qualification. A mention can be embedded as soon as it has a source anchor; a claim used for comparison should already carry its polarity, modality, conditions, attribution, and scope. Those are different objects at different points in the pipeline.

## 1. Embed the occurrence and the target separately

The useful unit is usually **the occurrence in its context**, not the isolated term and not the whole document. Consider this illustrative enterprise case:

| Object | What I would give the encoder |
|---|---|
| Source occurrence | **“supplier setup”** in “Complete supplier setup before issuing the first purchase order.” Heading: **New vendors**. |
| Candidate concept A | **Vendor onboarding** · process · establishing a new supplier relationship, including required registration and checks. |
| Candidate concept B | **Vendor master activation** · system operation · enabling an existing supplier record for transactions. |
| Candidate concept C | **Vendor onboarding checklist** · document · form recording completion of onboarding requirements. |

An exact-alias lookup might miss all three if “supplier setup” has not been registered. Dense retrieval can nominate them despite the wording difference. But **the candidates represent three different things**: a process, a step within that process, and an artifact used by the process. If the source says only “supplier setup,” the correct output may be an unresolved choice between A and B. If another passage explicitly says “supplier setup, referred to here as vendor onboarding,” that passage supplies evidence for the scoped alias. If it says “activate the vendor master record in SAP,” B becomes a substantially better reading.

This division has a direct methodological precedent in BLINK: encode a mention in context and the target entity’s description separately, retrieve a shortlist, then assess the pairs. Its results support the architecture; its benchmark does not tell us how accurately it will resolve your company-specific terms. [ACL Anthology](https://aclanthology.org/2020.emnlp-main.519/?utm_source=chatgpt.com)

I would create two versioned input representations:

- **Occurrence representation:** exact mention text, its containing sentence or list item, the nearest informative heading, and limited context needed to disambiguate it. Retain the source anchor separately. For a table header, include its parent header and caption; for a process step, include its procedure heading. Test whether adding this context improves the link rather than assuming more text is always better.
- **Concept representation:** stable target ID, canonical label, known aliases, type, source-backed definition or registry description, and applicable scope. For a mathematical parameter, include its parent family and role. For an enterprise system or workflow, include its business domain or owning unit when known.

This also works before the corpus has a mature ontology. Start with a frozen glossary, domain pack, registry, or curated set of source-backed definitions. For terms outside that inventory, retain the local occurrence and allow **provisional links between usages or definition passages**. That gives you a way to discover concepts without prematurely declaring that two mentions are identical or that every unfamiliar term requires a new canonical node.

## 2. Add a hybrid candidate generator, with an explicit decision after it

I would put the operation **after source-aligned mention discovery and before identity consolidation**. Its input can come from GLiNER, an explicit definition pattern, an abbreviation expansion, or a native table header. A complete five-family record is unnecessary.

For each occurrence:

1. **Generate lexical candidates.** Use exact identifiers, scoped aliases, released normalization rules, and fuzzy matching. An equipment tag, form number, or policy ID should retain its own exact-match signal.
2. **Generate embedding candidates.** Retrieve the nearest target descriptions from the eligible inventory. Scope the universe by corpus, version, and reliable type information. If GLiNER is unsure whether something is a process or system operation, keep both types eligible.
3. **Combine and deduplicate by target ID.** Preserve which channel found each candidate, its rank in that channel, and the source context used. Return a small bounded list rather than dozens of neighbors per mention.
4. **Assess the proposed link separately.** Use explicit definitions and aliases, type and scope compatibility, parent entity, source version, and known identity exclusions. Add a pairwise reranker only if independent review shows that correct targets routinely appear in the shortlist but are ordered badly.

The output worth persisting is something like: **“Occurrence X may denote concept Y; dense rank 2, no registered alias match, compatible type, local definition available, standing: candidate.”** That is a useful, inspectable addition to the corpus. The raw vector alone is not.

I would keep cosine similarity as a **ranking feature**, not a probability that two things are identical. If later incorporated into your mathematical interpretation layer, lexical agreement, cosine, and GLiNER typing can be jointly evaluated features; they are not independent votes. Existing source-backed identity exclusions should continue to govern merges. A chain of close neighbors should never, by itself, merge an entire cluster. The repository’s [identity-exclusion decision](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/adr/0029-identity-exclusions-scoped-reference.md) already provides the right boundary.

## 3. Apply embeddings to distinct linkage questions

I would resist creating one generic `semantically_related_to` graph. It is hard to evaluate and gives later stages little guidance about what an edge means. Instead, declare the question that caused each candidate pair to be generated.

| Priority | Linkage question | What embeddings contribute | What establishes the final relationship |
|---|---|---|---|
| **First** | **Which concept does this occurrence denote?** | Recover targets despite abbreviations, paraphrases, and vocabulary differences | Scoped aliases, definitions, entity/type compatibility, source evidence, or an unresolved result |
| **First extension** | **Where is this term defined or explained?** | Find a glossary entry, defining passage, or table explanation outside the extraction window | Verify that the passage actually defines or explains this usage; distinguish a definition from a mention or example |
| **Second** | **Which clauses or workflow steps should be compared?** | Pair passages across documents or revisions despite changes in wording | Compare actor, action, object, prerequisite, threshold, exception, and effective version field by field |
| **Later** | **Which unlinked usages may describe a new concept or distinct sense?** | Surface groups of contextual occurrences for inspection | Examine representative source passages and counterexamples; preserve distinct senses, singletons, and ambiguous memberships |

The third use is particularly valuable for company knowledge. Suppose one policy says **“Finance approval is required above $25,000”** and another says **“Finance may review purchases above $50,000.”** A good embedding system *should* put these passages near each other. That is a successful **comparison link**. Treating them as duplicates would be a serious **equivalence error**. Their proximity makes the changed threshold and obligation easier to discover; the structured comparison makes clear what changed.

Likewise, for the textbook case, *central limit theorem* and *normal distribution* are reasonable neighbors for topic exploration. They are incorrect identity targets for each other. Your [family-assembly probe](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/design_review/evidence/2026-11-03_m1-family-assembly/README.md) already contains exactly this kind of misleading association. I would put it in the permanent evaluation set: the system should be able to preserve both mentions, nominate related material, and refuse the erroneous definition link.

## 4. Use the links to build a structural digest

For the **digest** part of your question, I would build a **concept dossier** before a topic-clustering or summarization pipeline. For each concept or provisional sense, assemble:

- **Definitions and scope:** source-quoted definitions, including which document, division, or period they apply to.
- **Terminology:** accepted aliases, proposed aliases, and similar terms explicitly judged distinct.
- **Usage and relationships:** representative occurrences, workflow steps where the concept appears, related forms or systems, and the standing of each relationship.
- **Variants and exceptions:** changed thresholds, different role assignments, superseded procedures, and qualifications that prevent statements from being combined.
- **Open questions:** ambiguous occurrences, plausible alternative targets, and references for which no suitable concept exists yet.

Embeddings help find relevant material and choose **non-redundant source examples**. Once passages have been grouped by sense, role, scope, and version, a diversity-aware selector can avoid returning five near-identical examples. Exceptions and meaningful revisions should be retained explicitly even when their wording is nearly identical to the general rule. Relevance-plus-diversity selection has an established extractive precedent in MMR. [ACL Anthology](https://aclanthology.org/X98-1025/?utm_source=chatgpt.com)

This gives you a digest with an intrinsic test: **Does it contain the documented senses, definitions, important variants, and exceptions? Are any entries grouped under the wrong concept? Can every entry be traced to its source?** No generated-prose score or downstream agent evaluation is needed.

## 5. Model and storage choice

**For the first English CPU experiment, I would run `intfloat/e5-small-v2` as the compact baseline and `Qwen3-Embedding-0.6B` as the one larger challenger.** E5-small-v2 produces 384-dimensional embeddings and documents different input conventions for queries and passages. Qwen supports task instructions and up to 1,024 dimensions; it also lets you reuse the model family already considered in S7. Run each with its documented input convention and benchmark on your actual occurrence–concept pairs. I would not start by provisioning an 8B model or a permanent second inference service. [Hugging Face](https://huggingface.co/intfloat/e5-small-v2?utm_source=chatgpt.com)

There is a project-specific reason for making this comparison explicit. The later [CPU pipeline design](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/docs/target-pipeline-design/foundation.md) proposes **Jina embeddings v5 small**, and the design register flags the discrepancy with the older Qwen plan. Jina is a credible alternative, especially if you want to compare its retrieval and text-matching configurations. Its published weights are **CC BY-NC 4.0**, which matters for your intended company deployment. If the deployment license is already addressed, I would use Jina as the larger challenger instead of automatically testing three models. The model selected for occurrence linking need not prejudge the later qualified-claim comparison. [Hugging Face](https://huggingface.co/jinaai/jina-embeddings-v5-text-small?utm_source=chatgpt.com)

**Use the existing PostgreSQL environment and pgvector.** The repo already [pins the vector extension](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/ops/postgresql/extensions.txt), while the current [source search](https://github.com/paul-heyse/corpus-structure/blob/8695e869a8f38bbd521dd88470fff86009f94f05/python/corpus-structure/src/corpus_structure/serve/source_search.py) is lexical. Retain that search as a baseline. Start with **exact cosine search** on the pilot inventory. Introduce HNSW only when scale warrants it, and then distinguish *index recall versus exact nearest neighbors* from *semantic recall versus the correct concept*. An index can return the exact nearest neighbor while the encoder has ranked the wrong concept first. [GitHub](https://github.com/pgvector/pgvector?utm_source=chatgpt.com)

Version each derived vector by source or target ID, rendered input digest, context recipe, model revision, encoding profile, and dimension. Version the **candidate list** separately by target-inventory snapshot and retrieval policy. That way, adding a new glossary entry can change the candidate ranking without forcing the source occurrence to be re-encoded.

## 6. Evaluate linkage at the level where it can fail

I would make the first experiment a **paired lexical-only, dense-only, and hybrid comparison**, using the same frozen target inventory and the **same final budget of unique candidate IDs**—for example, five per occurrence. Otherwise, the hybrid method can look better simply by returning more possibilities.

| Stage | Direct evaluation |
|---|---|
| **Mention discovery** | From independently sampled passages, which linkable occurrences were found or missed? Also test the linker on supplied reference mentions so an upstream extraction miss does not masquerade as a linking failure. |
| **Inventory coverage** | Did the intended target actually exist in the frozen inventory? Distinguish a legitimate new/local concept, an ambiguous occurrence, and an existing target that retrieval missed. |
| **Candidate generation** | For occurrences with a known target, was an acceptable ID in the top five? Show the exact cases dense retrieval rescued, those it displaced, and the irrelevant candidates it introduced. |
| **Link selection** | With candidate lists held fixed, did the selector choose the correct scoped target or appropriately abstain? Inspect wrong-sense, broader/narrower, same-topic, and wrong-version confusions separately. |
| **Digest assembly** | On a bounded concept, inspect correct and incorrect memberships, missing senses and exceptions, unnecessary duplicates, and source fidelity. |

Two controls are especially important. **Withhold aliases learned only from the source unit being tested**, as S7 already proposes; otherwise the evaluation can reward the system for retrieving a label it just copied into its own dictionary. And **include deliberately close but distinct pairs**: standard normal versus normal, requester versus approver, onboarding process versus onboarding checklist, and two policy versions with different conditions. On a small pilot, a source-cited before/after review of those cases is more informative than a single average score.

**The first deliverable I would ship is a source-anchored concept-link table plus a structural diff:** for each reviewed occurrence, show the lexical candidates, the contextual embedding candidates, the reconciled shortlist, the selected or unresolved relationship, and the evidence for that judgment. Start with one statistics slice for continuity and one enterprise glossary/procedure slice for your actual target domain. That will tell you exactly **which linkage embeddings add, which distinctions they blur, and whether the next investment belongs in mention extraction, the concept inventory, candidate retrieval, or semantic disambiguation**.