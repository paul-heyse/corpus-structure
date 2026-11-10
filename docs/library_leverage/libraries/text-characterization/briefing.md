# Text characterization: integrated spaCy and Lark discovery

**Discovery, 2026-11-10; benefits Proposed.** This account investigates a comprehensive
source-aligned representation of fundamental textual and mathematical units, followed by
composition into conceptual relationships, higher-level labels/groups and analytics. Several
ordered characterization passes are appropriate. The operator selected a full target-design
inquiry, including substantial replacement of current boundaries; PM2 scope is evidence, not
the ceiling for discovery. This publication selects research directions, not adoption.

## Target and authority

Characterize language and formal notation richly enough that later consumers combine explicit
units and annotations instead of independently extracting them from raw text. When a consumer
reveals a missing characterization, investigate extending its upstream producer. Raw source
remains available for attribution and inspection. A new analytical question can require a new
characterization revision; this is not a promise to anticipate every future interpretation.

The proposed separation concerns meaning, not a fixed number of tasks, processes or persisted
objects. Linguistic dependency edges are characterizations of syntax; inferred domain edges have
different meaning and authority. A learned annotation remains a producer observation. Neither a
complete parse nor a maximally populated annotation object establishes conceptual truth.

The [knowledge owner](../../../design/D1-knowledge-representation.md),
[method owner](../../../design/D4-method-catalog.md),
[ADR-0062](../../../adr/0062-progressive-contributions.md) and
[full-book authority](../../../adr/0070-full-book-method-development.md) supply current contracts.
The [PM2 coordinator](../../../plans/production-milestone-two_2026-11-08.md) retains its own
dispositions and qualification. Its learned-model triggers do not prohibit broader discovery;
this account does not change those implementation selections. WCE's 120-page evidence retains
its original extent; the intended proving source here is the authenticated 518-page
Grinstead–Snell parent.

## Baseline and evidence

| Item | Inspected scope |
| --- | --- |
| Source | `0da4f8e614b162b791ac19dcb63f6cd33178377b`, main, 2026-11-10 |
| Worktree | Concurrent untracked `docs/design_review/evidence/2026-11-10_schema-diagnostic-failure-boundaries/` preserved; concurrent CLI/logging coordinator and command-authoring companion edits arose during research and are excluded from this account's analysis; tracked tree initially clean |
| Context | Root uv workspace/default groups, Linux x86_64/glibc2.39, Python3.14.10; independently locked model/provider projects not separately audited |
| Selected and installed | spaCy3.8.18, en_core_web_sm3.8.0, Lark1.3.1, SymPy1.14.0; spaCy/Lark/model are direct product dependencies; Lark also has an OAK/KGCL dependency path |
| Companion metadata | No installed distribution metadata for spacy-transformers, curated-transformers, experimental, layout, llm, scispacy, spacy-stanza, interegular or lark-cython in this interpreter; this does not establish their unavailability elsewhere |
| Overview coverage | Both supplied guides read end to end during planning, including addenda: spaCy2782 lines, Lark2223 lines. Execution researchers revisit them and deepen consequential mechanisms; coverage tables are in their topic briefings |
| Evidence strength | Current source, installed implementation, primary references and explicitly dated retained evidence. No new model inference, fitting, runtime probes or performance measurements |

Selection command: `uv tree --locked --offline --no-python-downloads --invert --package spacy
--package lark --package en-core-web-sm`. Installation/platform metadata was read with
`uv run --locked --offline --no-sync --no-python-downloads python -B` using
`importlib.metadata` and `platform`. Neither operation synchronized or installed packages.
Overview claims about latest releases are dated orientation; selected-release source governs
the mechanisms discussed here. Installed metadata is not runtime execution evidence.

## Reading route and research priorities

| Topic | Responsibility and question |
| --- | --- |
| [Consumer journeys](briefings/consumer-journeys.md) | What is already retained, what later consumers reconstruct, and what still requires context-dependent inference? |
| [spaCy](briefings/spacy.md) | How much richer can the shared linguistic annotation foundation become through native analysis, matching, span models and lifecycle facilities? |
| [Lark](briefings/lark.md) | Which lexical/formal structures and ambiguity-aware products could shared grammars expose beyond the current math and literal fields? |
| [Composition and interfaces](briefings/composition.md) | How should independent characterizers compose, which representations must survive, and what would distinguish a better foundation? |

Investigate the following together first. Priority is attention order, not an implementation queue.

| Lead | Proposed research direction | Decisive question |
| --- | --- | --- |
| TC-01 | Shared source-aligned characterization products, extending retained columns with reusable phrases/clauses/cues and formal units | Which later consumer operations would become composition over retained units, and which still need genuinely new characterization? |
| TC-02 | Broader native spaCy linguistic analysis and declarative matching, preserving overlapping candidates and named role geometry | Can the required fundamental units be represented faithfully, including discontinuous roles and alternative boundaries? |
| TC-03 | Lark lexical and grammar families for references, numeric/interval forms, enumerations and bounded language constructions | Which current string recognizers encode a reusable syntax, and which are already the simplest sufficient mechanism? |
| TC-04 | Independent and candidate-guided spaCy/Lark composition | Does guidance improve useful characterization without allowing one provider's missed candidate to suppress another's discovery? |
| TC-05 | Preserved ambiguity, annotation availability and exact source correspondence | Can downstream operations consume alternatives and partial products without treating unexamined scope as absent? |
| TC-06 | Learned span proposal/classification and structured tasks over shared representations | Is the missing capability boundary proposal, linguistic label, conceptual label or typed binding, and what supervision would address it? |
| TC-07 | Shared configuration, preparation, annotation interchange, batching and useful lifetime | What generic machinery and repeated work disappear after accounting for conversion, persistence, opening and change? |
| TC-08 | Complementary linking, classification and ecosystem capabilities | Which enrich fundamental characterization, which belong downstream, and which introduce redundant authority or lifecycle? |

The library briefings deepen these leads into concrete mechanisms, counterconditions and next
questions. All potentially beneficial guide families receive a disposition, including ones with
no present production caller. Existing usage and hypothetical broader value are kept separate.

## Judgment, handoff and limits

Apply [core3.3, heuristics and code-intelligence1.4](../../../design_review/design_principles/standard.toml).
FP-03/04 favor composition through explicit units and scoped meanings; FP-05 preserves dependency,
availability and alternative structure; FP-06 favors consumers understandable from retained
contracts; FP-07/H6/H12/H15/H16 challenge unnecessary eager work and repeated preparation without
shrinking the intended functional target. Rich characterization can be shared or prepared on
demand under one owner. It need not force every optional model to execute on every passage.

Relevant [patterns](../../patterns.md) are LOP-01/03/04/05/06/07/09/10/12.
[LOP-X004](../../assessment-patterns.md#lop-x004) is especially useful: a prepared product may
omit stable derivations its consumers repeatedly reconstruct. X007/X009 warn that copying or
opening a retained product can lose required state or recreate its producer. No new pattern or
alignment lint is needed.

Next, establish concrete opportunities for TC-01–05 through the codebase-audit route where
needed; use library-assessment for contextual fit and opportunity-review for complete options.
TC-06–08 remain active discovery leads, not automatically deferred by current PM2 decisions.
Compare the enriched foundation with the current retained-column/demand-driven route, including
which specialized consumers can disappear and which policies remain separately authoritative.
Accepted contract changes use existing planning, review and ADR routes; no second task ledger is
created here. The [composition briefing](briefings/composition.md) records proposed interface
effects and the concrete next questions rather than inventing a final universal schema.

Functional tests, model/provider runs, probes and benchmarks: **not_run**, deliberately; source
and reference evidence suffice for these discovery conclusions. Prior successful cases retain
their dated, bounded meaning. No new efficacy, speed, full-book qualification, deployment,
activation or selection claim follows. Publication verification is recorded in STATUS.
