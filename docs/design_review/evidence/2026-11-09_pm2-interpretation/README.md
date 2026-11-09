# PM2 interpretation and retained-source qualification

This account supports [PM2-07](../../../plans/production-milestone-two/gliner-and-d1-interpretation.md#PM2-07)
and [PM2-11](../../../plans/production-milestone-two/textbook-assessment-and-adoption.md#PM2-11).
It uses the authenticated Standard and Nemotron source product 1627 and the
unchanged projections selected by the finished run 407/cut 517. Run 404/cut 514
remains the source-only reference. See the [source panel and pins](../2026-11-08_pm2-parsers/raw/reference-book.json).
Chandra was outside this work.

The [development source panel](raw/source-panel.json) was authored from the
source and its native projection before opening d1 output. Its book cases
are exposed development controls. They do not establish independent A/B/C
adjudication, held-out evidence, or a like-for-like release comparison.

**Tested · 2026-11-09.** The staged d1 CUDA BF16 worker passed
`uv run python docs/design_review/evidence/2026-11-09_pm2-interpretation/native_batch_probe.py`
under the configured Nemotron handoff. A batch of mixed lengths returned
the right question populations for text, number, date, multilabel Choice and
binary decisions. It rejected a fourth, over-limit item separately. The
first request mapped a quantity and a date to the source JSON field; the
second retained an independent passage classification and text read. The
third retained a binary probability. These are observations of native
behavior, separate from quality assessment.
[Raw batch](raw/native-batch.jsonl) · [Model change request](model-change.yaml)

The local locked environment was already provisioned. Repeated attempts to
refresh the spaCy wheel hit a GitHub 504, so the successful local recipes used
the installed environment with `UV_NO_SYNC=1`. No pins changed.

**Tested development deployment · 2026-11-09.** The reviewed candidate
`65faefe54c214af79541357fd9082c1d` reached
`semantic_pm2_interpretation` on the dedicated development database. Managed
deploy `c7fd866d9de249adb9c325d981076cb2` verified archive and admission.
The project was left unselected. Run 419 at source-only cut 523 selected five
unchanged views under the successor release. There was no new intake,
recognition or projection run. [Development deployment](raw/development-deployment.json)

**Tested private results · 2026-11-09.** Same-release parser run 421 at cut 524
produced the fair-coin and gambler inputs. Interpretation run 422 at cut 525
settled all seven operations. It retained definition as a passage function,
located the fair-coin `1/8` without normalization, and reported a negative
binary observation for the supplied reason question. The host question
returned `no_match` with the assignment frame offered. The local referent
question returned `missing_candidate` with the gambler offered. These
observations verify the transport and show quality gaps in the current
questions. They do not support selecting an attachment or a link.

On task 2105, the CLI and MCP returned the same assessed extent
`[18091,18193)` and both exact host candidates, and refused a changed-facet
cursor. The offline `ci review inspect --result a96885c8f28f409da4547ac540de87d1`
passed after the exact bundle exported the focus and both candidate reasons
and resolved parser task 2100. The bundle used an explicit 512 MiB ceiling
for the retained source proof. No public source claim or semantic claim was
admitted. [Readback and detached receipt](raw/development-reader-summary.json)

**Tested development assessment · 2026-11-09.** Set 33 froze five source-only
opportunities under the current release. Two separate source-only reviewers
and the coordinator's adjudication recorded 15 protected passes. Evaluation
37 scored run 423/cut 526: the definition function was supported; the fair-coin
quantity did not satisfy the required complete structure because normalization
was unresolved despite a located literal. Three cases stayed unassessed.
The variance host lacked an appropriate prediction scope and candidate
population; the gambler frame did not freeze one focal mention and matching
candidates; the roulette question did not isolate the loss occurrence from
other amounts. These scopes supply no independent selection grade. The
retained evaluation 36 captures the earlier empty-anchor filter defect;
evaluation 37 applied the explicit assessed-extent selection. No reference
answers were used in inference. [Protected passes](raw/development-reference-passes.json) ·
[Scoped evaluation](raw/development-evaluation.json)

**Open.** This is exposed development assessment of one book. It does not
supply a like-for-like incumbent pair, verified retrieval gain, or an eligible
DMA-13 predecessor. Those gates still precede full-book derived qualification
and selection. The exact source is already available.

**Tested contextual contract · 2026-11-09.** The registered v10 configuration
schema matches the installed v10 schema exactly. The separate opt-in v11
operation retains a bounded parser reference for each focal occurrence.
The frozen native candidate `98469a11b356487a804b1fd8286dcfb3` reached
`semantic_pm2_contextual_queries`; managed deploy
`90f61c1e80ca4773a1b0dbce2504cd3d` verified archive and admission. Controlled
execution preserved the original literal, encoder target inputs and the
existing witnessed selection in both the available and unavailable encoder
cases. The retained candidate-list Reader separately resolved native run
258's 14 typed definition alternatives and refused a different view. These
checks do not show richer-query gain. The default is still v10, and exact
detached bundles refuse richer rendering until its proof can be replayed.
[Configuration contract](raw/contextual-method-contracts.json) ·
[Development deployment](raw/contextual-development-deployment.json) ·
[Focused checks](raw/focused-checks.json)

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 5 current, 0 superseded.


**pm2-interpretation**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Typed CUDA d1 batch and isolated limit](records/pm2.native-d1-batch.json) | PM2-07 | passed | PM2-07 | 2026-11-09 |
| [Private same-release d1 and exact composition](records/pm2.private-interpretation.json) | PM2-07 | partial | PM2-07 | 2026-11-09 |
| [Versioned private retrieval context](records/pm2.contextual-query-contract.json) | PM2-09 | partial | PM2-09 | 2026-11-09 |
| [Adjudicated exposed interpretation assessment](records/pm2.development-interpretation-grade.json) | PM2-11 | partial | PM2-11 | 2026-11-09 |
| [Private same-release source frame freeze](records/pm2.interpretation-source-frame.json) | PM2-11 | partial | PM2-11 | 2026-11-09 |
<!-- evidence-index:end -->
