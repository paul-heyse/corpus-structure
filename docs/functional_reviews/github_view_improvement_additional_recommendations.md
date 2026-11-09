**The updates are a substantial improvement, and the publishing work is now in place. The next pass should make the project’s semantic operations and assembled outputs much more visible.** You already have stronger demonstrations in the retained results than the landing page currently shows.

I reviewed commit [`5bddd14`](https://github.com/paul-heyse/corpus-structure/commit/5bddd141bc5783a69bab4c0350529a5a837dc8ee), inspected the GitHub README and [live documentation site](https://paul-heyse.github.io/corpus-structure/), checked the site at desktop and mobile widths, exercised search, and checked the featured examples against their evidence records.

My recommendations fall into three groups:

1. **Correct a few specific documentation defects.**
2. **Show the actual semantic transformations and assembled knowledge.**
3. **Make the documentation easier to explore and connect the project more explicitly to organizational knowledge.**

## 1. What the programming agent delivered successfully

The agent made sensible implementation choices and followed through on publication.

| Area | Assessment |
|---|---|
| README | Now explains progressive enrichment, typed relationships, source evidence, and granular assessment before development instructions. |
| Public documentation | GitHub Pages is deployed and serving the reviewed revision. |
| Build and deployment | The reviewed commit’s documentation workflow completed successfully. Its logs report 45 documentation tests passing, 702 canonical pages built and indexed, and no errors in the offline link check. |
| Repository metadata | Description, homepage, and seven relevant topics are populated. |
| Social preview | Uploaded successfully; the live preview matches the committed image. |
| Maintained visuals | The D2 diagram and HTML social-preview template have a reproducible rendering path with pinned tools. |
| Examples | The citation and positive-variance examples agree with the retained assessments. |
| Search | My live search for “variance” returned results, including the examples page in the default Current scope. |
| Scope communication | The enterprise example is labeled illustrative; the architecture page distinguishes implemented work from research questions involving pgmpy and Pyro. |

Sources: [hosted documentation run](https://github.com/paul-heyse/corpus-structure/actions/runs/42481958715), [README](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/README.md), [rollout acceptance](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/plans/github-visitor-experience_2026-11-08.md#ghv-acceptance), and [visual renderer](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/visuals/render.py).

The decisions to defer Vale, Lucide, an additional diagram tool, and a recording were reasonable. They are explicitly recorded in the plan. I would continue to judge those additions by a concrete presentation need. The existing tooling is sufficient for the improvements below.

**The principal remaining weakness is that visitors are told about sophisticated structuring, but see relatively little of the resulting structure.** The featured section citation demonstrates useful linking. It does not, by itself, convey the depth of the linguistic composition, qualification, and assembly work.

## 2. Specific corrections I would make

### A. Fix the generated “Suggest an edit” links

This is a confirmed publisher defect.

The live homepage’s edit link points to:

```text
.../edit/main/src/README.md
```

The examples page points to:

```text
.../edit/main/src/docs/examples/README.md
```

The repository files are actually `README.md` and `docs/examples/README.md`.

The cause is in the publisher: pages are staged under a temporary `src/` directory, and the mdBook edit template incorporates that staging prefix. See [the staging and edit-template logic in `scripts/docs.py`](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/scripts/docs.py).

**Prescribed change:** construct or rewrite each edit URL from the publisher’s known repository-relative `Page.path` during HTML annotation. For generated pages such as the architecture-section index, either omit the edit action or point it to the actual owning source.

Add a focused assertion to the existing publisher tests for a root page and a nested page. That directly protects the behavior that is currently wrong.

### B. Correct a stale dossier summary

The [rooted dossier README](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-06_wce-completion-repair/dossier/README.md) still ends by saying that the native, Reader, CLI, MCP, and portable journey remains pending.

Its [finalized evidence record](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json) reports those routes passing on November 7, with runs 196/cut 261 and 202/cut 273.

**Prescribed change:** add the completed result and link to that record, while keeping the earlier preflight account clearly dated as preparation history.

This matters particularly if you feature the dossier as a demonstration: a visitor following the evidence should encounter a consistent account of what was completed.

### C. Link prominently to the published documentation

The README’s badge labeled “Documentation” opens the Actions workflow. The main text links open repository Markdown. The Pages URL is present in About, but the README itself does not clearly offer the published site as a destination. [Current README](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/README.md).

**Prescribed change:**

- Add **Documentation** or **Explore the project** to the opening navigation, pointing to the live site.
- Rename the status badge **Docs build**.
- Keep direct routes to examples, architecture, and evaluation.

This is a small change that makes the publication work easier to discover.

## 3. Highest priority: show a real semantic transformation

I would make this the centerpiece of the next presentation pass.

The current examples page contains useful evidence, but much of its visible detail consists of pointers, offsets, hash prefixes, and run identifiers. Those become valuable once a reader understands the transformation. The transformation itself should come first.

### Example 1: a condition attaches to a definition in the next sentence

The positive-variance example is a strong candidate for the main README demonstration.

The retained source review establishes that the correlation exercise on physical page 289 introduces a positive-variance premise and attaches that premise to the defining predicate in the following sentence. This is more informative than the current short description makes apparent. [Attachment assessment](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441).

I would show a compact exhibit with this content:

| Part of the exhibit | What the visitor sees |
|---|---|
| Source | The two adjacent source sentences, with the premise and defining predicate highlighted |
| Located observation | The positive-variance assumption |
| Operation | Attach the premise to the definition it qualifies |
| Result | A definition component with its source condition attached |
| Assessment | A short statement that the source review supports this particular attachment |
| Evidence details | Expandable source coordinates, edge identifier, producing run, and full assessment link |

The point to communicate is concrete: **the system preserves a condition that determines how the neighboring definition should be understood.**

The evidence also places an important boundary on the presentation. The replay retains the premise in its original wording; the card should represent that textual attachment. It should not silently turn it into a claim that the system proved a normalized mathematical condition. [Qualifier replay and finalized record](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-07_nce-source-linguistics/records/nce.qualifier-scope-development.json).

This is a good reason to revisit the deferred example card: visual correspondence between the source span and the resulting field would reveal something that the current pointer-heavy prose makes difficult to see.

### Example 2: a local phrase recovers its complete antecedent

The retained constant-density case is an especially good demonstration of linguistic analysis.

The system resolves **“This set of points”** to the complete preceding description, including its restriction, while retaining the local mention. The evidence explains how this uses retained spaCy token relationships and source boundaries, including the bounded behavior when multiple antecedents compete. [Antecedent account](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-07_nce-source-linguistics/README.md#antecedent-decision) and [finalized record](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-07_nce-source-linguistics/records/nce.constant-density-antecedent.json).

A presentation could show:

1. The local demonstrative phrase.
2. The preceding description to which it refers.
3. The recovered definition component.
4. The original mention retained as evidence.

This demonstrates a distinctive aspect of your approach: additional semantic structure can be composed from annotations already collected.

I would describe it as a **demonstrated antecedent-recovery case**, with its bounded rule and evidence. That gives an engineer something specific to understand and inspect.

### Example 3: an actual assembled knowledge view

The README mentions dossiers, but the public examples do not display one.

There is a retained example with a clear assembly decision:

| Dossier element | Retained result |
|---|---|
| Selected root | `The normal density function` |
| Included facets | `terminology` and `definition` |
| Qualified members | Two |
| Support | Members are independently supported |
| Excluded material | `marginal totals`, which is supported independently but unrelated to this root |

The [finalized dossier record](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json) and [runner assertions](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-06_wce-completion-repair/dossier/run_rooted_dossier.py) establish those values.

I would show the selected concept, its term and definition evidence, and the unrelated component outside the assembled view.

That illustrates **what assembly means**: selecting related, supported material around a particular subject.

The programming agent should obtain the exact definition text from the retained output when building this exhibit. The presentation should use that actual content and identify it as a small demonstrated dossier.

### How I would arrange these examples

For the README:

- Feature the condition-attachment example.
- Keep the section citation as a second, compact example.
- Link to a richer examples page containing antecedent recovery and dossier assembly.

For the documentation:

- Give each example a short source → operation → result → assessment sequence.
- Place technical identifiers under **Inspect evidence**.
- Offer a small downloadable excerpt of the actual retained fields.

This would preserve the project’s rigor while making the results easier to understand.

## 4. Make the diagram communicate transformations

The current diagram is readable and consistently styled, but its technical content is sparse.

Its four operation boxes contain a stage name and a broad output label. The only connections in the D2 source are from source documents to the operations group, and from that group to the evidence band. There are no connections between the four operations. [Current D2 source](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/visuals/pipeline.d2).

For your original objective—showing software engineers the semantic and linguistic work—I would retain the four-stage organization and add the following specificity:

| Stage | Operations to make visible | Output to name |
|---|---|---|
| Extract observations | Locate definition spans, predicate/participant spans, qualifier cues, and reference cues | Located observations |
| Compose local meaning | Attach roles, bind conditions to their scope, recover supported antecedents | Qualified semantic components |
| Connect related material | Retrieve candidates, resolve references or declarations, select typed relationships with supporting evidence | Supported connections |
| Assemble knowledge | Group around a selected subject, compare qualified readings, expose unresolved material | Dossiers and comparisons |

The visual should make three distinctions clear:

- **The operations change the representation.** Arrows should identify what passes between stages.
- **Partial outputs remain useful.** Assembly should not appear to be a mandatory gate before any structure can be inspected.
- **Provenance and evaluation apply throughout.** The evidence band should read as shared support for the operations, rather than as the pipeline’s final product.

I would also improve the narrow-screen treatment. At the mobile width I inspected, the diagram fits, but its labels are considerably smaller than the surrounding body text. A vertically arranged variant, or a compact overview linked to a larger detailed figure, would preserve readability as technical detail increases.

For pgmpy and Pyro, the current architecture page’s research labeling is appropriate. If they appear in a richer figure, put them in a clearly labeled **Optional analytical extensions** area and describe the proposed analytical question. The main operational path should correspond to demonstrated behavior.

## 5. Give the documentation a clearer visitor route

This is the largest navigation opportunity.

The site now contains **702 canonical pages**, but the publisher emits its chapters at the same indentation level. The opening sidebar places agent instructions and status immediately after the overview. The documentation entry page still begins with design principles, ownership, and review workflows. [Publisher](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/scripts/docs.py), [publication configuration](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/site.toml), and [documentation entry](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/README.md).

For someone arriving after an interview, I would make the first reading route:

1. **Overview**
2. **Examples**
3. **Functional architecture**
4. **Evaluation**
5. **Develop locally**

Then group the deeper material under expandable sections such as:

- Architecture contracts.
- Implementation reference.
- Evidence and experiments.
- Contributor and agent workflows.
- Plans and decisions.
- Library references.

The full collection can stay published and searchable. The implementation change is to give the existing publisher an explicit ordering and hierarchy for its opening navigation.

### Correct the architecture introduction

There is a specific orientation problem:

- The architecture map says to read D0 first.
- D0 is explicitly a dated proposed design.
- D0 directs readers interested in the current pipeline back to the overview, examples, and architecture map.

That creates a loop. D0 also retains earlier assumptions, including an HTML intake route and a different model-escalation framing, which makes it a difficult first explanation of the current implementation. [Architecture map](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design/README.md) and [D0](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design/D0-target-overview.md).

**Prescribed change:** begin the architecture map with the current functional pipeline and its code-reading route. Place the D0–D9 collection under **Design contracts and target architecture**.

The newly added “Trace a result through the code” section is useful; it should move much closer to the top and explain what each linked component contributes. A reader should be able to follow one result from source capture through observations, linking, and serving without first reconstructing the project’s design history.

### Separate the three onboarding intentions

The current “Run locally” section combines static inspection, historical reproduction, and developer setup. The reproduction guide appropriately documents its release-compatibility constraints, but it is a substantial undertaking. [Current reproduction instructions](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/examples/README.md#reproduce-the-contextual-example).

I would make the choices explicit:

| Visitor intention | Route |
|---|---|
| Understand what the system produces | Readable examples with retained output |
| Reproduce a documented experiment | Exact source, release, environment, and reproduction procedure |
| Work on the codebase | Setup, doctor command, relevant code paths, contributor instructions |

For your immediate showcase goal, the first route deserves the greatest attention.

## 6. State the organizational-knowledge goal in the opening

The README describes collections of documents, but its concrete context is almost entirely the probability textbook. The enterprise use appears only in a short illustrative paragraph on the examples page. [README](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/README.md) and [enterprise illustration](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/examples/README.md#illustrative-enterprise-workflow).

I would make three points explicit near the beginning:

- **Intended application:** structuring organizational knowledge, including policies, procedures, technical documentation, and relationships between them.
- **Core principle:** useful structure can accumulate while portions of the source remain unresolved.
- **Current development setting:** a probability textbook provides the present corpus for developing and assessing the methods.

That would connect the implementation to the broader goal you have described without overstating demonstrated coverage.

The enterprise illustration could also be more concrete. Present the illustrative rule once, then show its intended actor, action, object, timing, scope, and exception fields in a compact table. Keep its illustrative status visible.

A subsequent demonstration milestone could run a small synthetic organizational document through the actual pipeline—for example, a procedure with an approval condition, an exception, and a cross-reference. Assess its extraction, attachment, linking, and assembly separately. This would be a natural extension of your current evaluation philosophy and would give the site a directly relevant enterprise example.

## 7. Make granular evaluation one of the project’s visible strengths

The existing evidence is detailed, but the reader has to work to understand which assessment belongs to which layer.

I would add a short evaluation introduction organized around the operations:

| Layer | Question being assessed | Suitable public example |
|---|---|---|
| Source capture | Did the retained representation preserve the relevant source material and location? | A specific capture or recovery case |
| Extraction | Were the correct spans and semantic roles identified? | A definition or predicate example |
| Attachment and scope | Was a condition attached to the correct host, with the required extent? | The positive-variance case |
| Linking | Was the correct target selected, and what evidence supports the relationship? | The section citation |
| Assembly | Does the view include related supported material and exclude unrelated material? | The rooted dossier |
| Coverage gaps | Which source structures were missed, and at which operation? | Printed references that never entered contextual retrieval |

Each row should link to the actual assessment and include a short observed result or limitation.

The current citation wording is already careful: nine retained decisions were checked, and four additional printed references were separately identified as upstream misses. Preserve that distinction. Those observations do not supply a book-wide recall denominator. [Contextual assessment and coverage gaps](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations).

This section would show an engineer how the system can be improved methodically. It also makes your approach to evaluation apparent without requiring them to read a long operational review first.

## 8. Additional visual and publication polish

These are worthwhile after the content and navigation work.

### Align the site identity with the repository

The live site still uses the book title `corpus-structure` and the description “Architecture, decisions and working context.” Those come from [the book configuration](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/book.toml).

I would:

- Use **Corpus Structure** consistently.
- Replace the internal description with the public project description.
- Add a small project favicon.
- Use a restrained shared palette for headings, callouts, examples, and diagrams.
- Provide suitable light and dark diagram treatments; the current white diagram rectangle is visually prominent on the dark site.

mdBook supports selective theme overrides and additional CSS, so this can remain a small extension of the current publisher. [mdBook Documentation](https://rust-lang.github.io/mdBook/format/theme/index.html?utm_source=chatgpt.com)

### Add sharing metadata to the documentation site

The repository’s social preview is complete. The inspected documentation HTML does not yet have equivalent Open Graph metadata.

Add page titles, descriptions, canonical URLs, and the existing social image at a stable Pages URL. This would improve the presentation when you send someone the documentation link directly.

There is an implementation detail for Codex: your publisher currently copies `docs/theme` after mdBook renders. Merely adding a `head.hbs` file there would not cause mdBook to apply it. Wire theme templates into staging, or add the metadata through the existing HTML annotation step. Also ensure the social image is copied into the published artifact. [Publisher implementation](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/scripts/docs.py).

### Make search initialization visible

Search worked in my check. There is still a small usability improvement available: the current integration makes the input read-only during first initialization and reports loading errors only to the console. [Search integration](https://github.com/paul-heyse/corpus-structure/blob/5bddd141bc5783a69bab4c0350529a5a837dc8ee/docs/theme/search.js).

Show a visible loading message and an accessible retry state if initialization fails. This would make the behavior understandable on a slower connection.

## 9. The next implementation package I would hand to Codex

I would organize the work in this order:

| Priority | Work | Completion criterion |
|---|---|---|
| **1 — Correctness and routing** | Fix edit URLs; update the stale dossier summary; add the direct documentation link; correct the D0 reading route | Source links and completion summaries agree with the actual repository and records |
| **2 — Demonstrate the semantics** | Build the condition-attachment exhibit; add antecedent and dossier examples; expose selected actual output fields | A visitor can see the source, operation, resulting structure, and assessment without installing anything |
| **3 — Explain the architecture** | Add concrete operations and outputs to the diagram; improve the current code-reading map | The diagram and linked explanation show how information changes through the pipeline |
| **4 — Organize the site** | Add a curated opening sequence and hierarchical reference navigation | The initial reading path reaches examples and current architecture before internal process material |
| **5 — Refine presentation** | Align metadata, theme, social sharing, mobile diagram treatment, and search loading states | The README and documentation feel like a coherent project presentation |
| **6 — Extend the demonstration** | Add a small organizational-document example, or a static interactive result inspector | A new demonstration exposes a meaningful capability using real outputs and granular assessment |

For a later interactive inspector, I would keep the implementation small: select a retained example, click a highlighted source span, see the corresponding structured field and supporting relationship, and expand the raw evidence. It could run entirely from committed example data within the existing documentation site.

**The most valuable immediate change is the semantic example exhibit.** It would let the project demonstrate, visibly and precisely, the work that currently sits behind phrases such as “compose local meaning” and “assemble knowledge.” Coupled with a more informative diagram and a clearer reading path, that would give someone visiting after an interview a much stronger understanding of what you have built and the engineering judgment behind it.