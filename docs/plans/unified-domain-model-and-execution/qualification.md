# Qualification: the union restated, the book-run diagnosis, and the final runs

**Status:** Not started. Plan authored 2026-11-19. Writing this plan authorizes no execution.

This companion owns the designs of **UDM-20** (the book-run diagnosis), **UDM-21** (environments
at the head), **UDM-22** (the managed union on final source) and **UDM-23** (the whole-book run).
It is where this series takes over validation from the declared-data-operations plan (the DDO
plan), by the operator's decision of 2026-11-19: the series owns the whole qualification,
restated for its own target, including the whole-book run and the diagnosis of why the last one
stopped. Package state, the queue, finding dispositions, the shared contracts and the flexibility
frame are the [coordinator's](../unified-domain-model-and-execution_2026-11-19.md), whose
[glossary](../unified-domain-model-and-execution_2026-11-19.md#glossary) defines
terms such as *release*, *demand*, *fate*, *intent*, *seal*, *lease* and *watermark*. The term **qualification union** is the coordinator's; this companion supplies its
content.

**Baseline and evidence.** The plan was authored against commit `cb4e09667`, whose production
source is identical to `5139eaba3`. Source facts are **Interface-checked by source inspection,
2026-11-19** at that commit. Every receipt, result identifier, run outcome and environment state
in this document is **quoted** from the DDO plan, its companions, the test series' plan or
`STATUS.md` as they stood at `cb4e09667`. None was re-observed: the managed result store was not
opened and no command was run for this plan. Where the earlier documents only narrate a cause
and cite no observation, this document says "narrated". Every design statement is **Proposed**.
The investigation behind this companion is the
[validation mapping](../../design_review/evidence/2026-11-19_udm-plan-authoring/validation.md),
which lists what it read fully, sampled and did not read. `src/…` and `tests/…` are relative to
`python/corpus-structure/`, the production package is `src/corpus_structure/`, and module paths
below are relative to it.

**Names used for environments.** The coordinator's glossary defines the stage, canonical
development, the book and N-numbers; the identifiers below are quoted. *Stage* is the owned stage database, object
identifier 130661481, with the bounded project `ddo-current-pdf-bounded`. *Canonical development*
is the development database, object identifier 131763263, on the dedicated PostgreSQL cluster at
port 5434. *The book* is the project `nce-grinstead-snell-full-book` on canonical development: one
document of 518 pages, organized into 29 regions. *N-numbers* are the frozen native revisions of
the deployed migration tree (`semantic_ddo_pe_nNN`); the head at the baseline is N29.

## Why this work exists, and what is being validated

The DDO plan left its qualification open. Its closing package was to run one assembled union on
final source; that run has not happened, no full test run has passed since 2026-11-10 (quoted
from the test series' plan), the exclusive fault lane has never been run, and the whole-book run
last ended in failure with its causes narrated and its four repairs never exercised against the
book. This series changes the source again, and deliberately: it replaces how validity is
selected, how programs are identified, when a native revision is authored, what the execution
path regenerates and how results are cached. So the thing being validated is the target of this
series, as realized on its final source. That has three consequences.

First, the open obligations cannot simply be copied. Some observe behaviour this series does not
touch and carry unchanged. Some are stated in terms the target removes (a seal keyed on the
kernel digest, a validity claim made by leaving the family absent, a watermark with a kernel
component, a release identity that hashes generator sources) and must be restated. A few are
superseded outright, and the target introduces behaviour the earlier union never named.

Second, evidence is gathered once, at the end, and the final runs only observe; the
[rules](#rules-of-this-qualification) below say why.

Third, one piece of validation cannot wait for the end: the diagnosis of why the last book run
did not complete (UDM-20), which is early and independent of the design packages.

## Baseline at `cb4e09667` (quoted unless marked)

### Environments

| Environment | Native revision | State |
|---|---|---|
| Stage | N29 | Release `39b65416…`, runtime `e639e1aa…`, generation 26; native deployment `16e5153d…` and application deployment `02e840dc…` passed |
| Canonical development | N29 | Migrated with `ci db migrate --expected-predecessor semantic_ddo_pe_n23`; deployment `2822093d…` settled passed. Separate `ci db check` and `ci release check` on N29 are not recorded |
| The book project | Selects N23, generation 4 | The head is N29. Generations 1 to 4 were N13, N18, N21 and N23. Two N23 leases expired, so no lease blocks activation |
| Earlier development database | Inert | Connections disabled |

The 29 original descriptors are registered in nine projects with inventory digest
`ad051b0d…f2e27`, and were byte-verified after N13, N18, N21 and N23. Readback after the N29
migration is recorded as pending. Between N23 and N29 the recipe identities of capture,
organization, organized-source discovery and construction changed; the definition, recipe and
eligibility identities of sentence and formal-evidence work agree across N23, N24 and N29.

### The last book run

Run `1dd5d45ded4b4ea38399fb121a44d28c`, on N23, under the 16 GiB policy
(`whole-book-host-execution-policy.json` in the evidence folder `2026-11-16_ddo-current-native`:
owned state 17,179,869,184 bytes, packet 603,979,776, reply 201,326,592, one million rows).
Capture published all 518 pages. Organization was fulfilled and discovery attached. Of 29
regions, 20 completed, retaining 3,411 sentence occurrences (between 1 and 1,035 per region).
Nine sentence attempts "timed out in settlement" at the 120-second limit. The whole-view
composition refused two checks, `sequence-ordinal` and `binding-covers`, and its final binding
query "was still running after six minutes with no new derivation" when the coordinator received
a cooperative interrupt. The result settled failed "with a nested physical-join uncertainty". One
completion intent was left unresolved. The operator then stopped execution.

The causes are narrated and no probe is cited for either. The settlement timeouts are attributed
to recursive canonical JSON, on the ground that the retained-intent write computed the same
payload digest twice. The stalled binding is attributed to the composition taking its regional
inputs as sequences and the binder joining independent optional roles relationally, which risks
a cross product. Four commits target these:

| Commit | Revision | What it changes | Recorded check (quoted) |
|---|---|---|---|
| `66c36d4c8` | N26 | Materializes PDF access edges once for both inventory directions; a related 120-second statement timeout had been seen in `sem.ddo_model_class_contract` | 16 native controls `ebb58af2…` |
| `956661772` | N27 | Computes the completion payload digest once and shares it between the stored digest and the validation seal | 5 stored-seal controls `215ea070…` |
| `1d3640990` | N28 | Selects independent optional binding roles role by role instead of by a join | 82 binding controls `1a87bdc6…` |
| `590b67b7a` (with `1fab40234`, `67a6e7a51`) | N28 | Composes captured document populations as sets, with ordering applied at presentation | Unit and permutation tests; "native capture pending" |

None has been run against the book. The N29 book invocation is recorded as unstarted, and the
retry of the native composition fixture, `82ba7773…`, was interrupted by the operator.

Established from source for this plan: the 120-second limit is
`DatabaseSettings.completion_statement_timeout_seconds` (`settings.py:70`), applied at
`semantic/claim_lifetime.py:161` by `_deadlines` (`:204–211`), which sets `statement_timeout` and
`lock_timeout` for the transaction through `set_config`; the lock timeout it sets is the renewal
lock timeout, whose default is 5 seconds (`settings.py:71`). A search of the production package
finds `statement_timeout` nowhere but `settings.py` and `claim_lifetime.py`. The binding is
executed by `execute_binding` (`semantic/data_operation_bindings.py:1682`) as one statement
through `connection.execute(statement)`, called from `semantic/data_operation_demands.py:991`,
with no deadline set in Python. That is consistent with a query still running after six minutes.
The two refusals are raised at `semantic/data_operation_bindings.py:1198` and `:1244`. Whether
the server applies a statement timeout of its own, by role or by database, is not established:
the cluster's provisioning files are not in the snapshot that was read.

### The test and qualification surface

`ci test` has two lanes (`cli/testing.py:42`): *ordinary* and *fault*. With no narrowing, a run
requires both. A path or `-k` narrows to the ordinary lane. The fault lane is serial and
exclusive, owns its selection and refuses narrowing, a worker count and provider selection.
Provider tests are opt-in evidence: the ordinary lane excludes them, `--providers-only` selects
and requires them, a missing prerequisite reports `blocked` with the prerequisite named, and an
empty provider selection is `not_run`. `ci test coverage ORIGINAL RETRY…` accounts for a
required selection by test identity across attempts, the original attempt supplying the required
selection, and reports missing lanes, unresolved identities and differences of source and
context; `ci test review ORIGINAL RETRY` is the bounded view of a chain. Collection receipts
never supply functional coverage (8,824 identities were collected, quoted). Settled successes
that are not held expire in a day, and failures and interruptions in a week; `ci results hold`
and `ci evidence retain` keep what a plan depends on. All of this paragraph is from the
validation mapping's reading of `cli/testing.py` and the `ci` skill.

## Rules of this qualification

**Credit follows source.** A receipt establishes behaviour for the source and native context it
was observed on. When source that could affect the observed behaviour changes afterwards, the
receipt keeps its original scope and earns no credit for the changed source. This is the DDO
plan's rule
([preservation companion](../declared-data-operations/preservation-adoption-and-qualification.md),
"Qualification and adoption consequences") and it is unchanged. Every receipt quoted in this
document was observed before this series' changes, so none of them is credit toward this series'
union. They are recorded because they say where behaviour last stood and which failures are held.

**Evidence is gathered on final source.** *Final source* is the commit at which every functional
package of the series is implemented and its superseded machinery removed, with the last native
revision of the series deployed. UDM-22 and UDM-23 run there and nowhere earlier. Checks made
during the design packages are targeted and local, as the repository's testing rules require;
they tell an implementer that a slice works and they are not union evidence.

**Final runs observe; they do not tune. Measurement is planned only where a named decision needs
it.** No default, bound or placement is left for UDM-22 or UDM-23 to settle. Each such choice is
settled earlier, by a bounded observation on the stage named in the package that owns the
decision. If either final run reveals a needed change, the change is made within the series and the affected evidence is gathered again,
by the rule above; the owning package makes it. The planned measurements
are these and no others. UDM-20 observes query plans, wait state and timings, because an
unexplained failure to complete the product's main workload is a serious correctness and
completion risk; it is a diagnosis with a stated end and seeks no speedup. UDM-06 observes that
**conservative validity** completes within settlement's limits under concurrent completions,
which decides whether its lock design stands before revision A is frozen
([validity companion](lowered-operation-facts-and-validity.md)). UDM-13 sets its three cache
size defaults from footprints observed on the stage, and UDM-14 its two on-disk store budgets
from the bytes of one stored entry of each kind ([cache companion](cache-system.md)). UDM-16
observes the input sizes of the rich-rule views, which decides their placement
([analytical placement companion](analytical-placement-sql-and-retirement.md)). Elsewhere the
series describes benefits qualitatively and plans no benchmark.

**Environments follow the revisions; canonical development and the book are adopted twice.** The
series plans three native revisions, authored and frozen close together in the order A, B,
transition: revision A for validity (UDM-05 and UDM-06, with the decimal bound of UDM-18),
revision B for roles, grants and support edges (UDM-03 and UDM-07, with UDM-19's removal of the
release-side authored-SQL machinery if it changes installed bytes), and the identity transition
(the native slice of UDM-10, the explicit kernel predicate of UDM-11 in the generated guard and
the installed-object changes of UDM-12, and UDM-09's differing objects if its equality premise
fails). UDM-11's model-change commands install nothing and change outside any revision. A
byte-changing repair from UDM-20 joins revision A, or the next planned revision that is not yet
frozen. Each changes the kernel identity and forces every release to be
prepared again. After the transition and UDM-11, a change that alters no installed byte produces
no revision and therefore no adoption.

*Stage* follows every revision: each is replayed rollback-only and then deployed there, as every
revision since N14 has been, and the design packages' targeted native checks and bounded
observations use it. *Canonical development and the book project* are adopted twice in the whole
series: once at the current head (N29) in UDM-21, and once at the final head on entry to UDM-23,
after the last revision is frozen. Both adoptions end with the re-adoption check that UDM-21
defines. The reason is cost. Every adoption of canonical development is a migration of the
database that holds the 29 originals, followed by re-verification of their custody and
re-activation of the book, and every change of capture or discovery recipes means the book's
derived data is regenerated from the original. Regenerating between revisions would be done again
after the next one and would earn no credit. The DDO plan reasoned the same way when it placed
development adoption after its last native successor, "so that … nothing is regenerated twice".

**Outcomes are reported as the repository requires**: `passed`, `failed`, `blocked` with the
missing prerequisite named, or `not_run`, each with the command that produced it. A controlled
or mocked provider is never `passed` for a provider obligation. Outcomes are never turned into a
percentage.

**Chandra OCR is excluded.** By the operator's direction of 2026-11-16, restated on 2026-11-19,
Chandra OCR, the migration of its results and its qualification are outside scope. Incompatible
Chandra-generated results are discarded; no converter and no reader is added; the raw PDFs remain
the originals. It is recorded here as excluded and is not an obligation of the union.

## The qualification union, restated for the target

The validation mapping lists 24 open obligations taken from the DDO plan and its companions.
Each is restated below as an observable behaviour, with its route and the evidence that would
satisfy it. "Obligation n" means row An of the validation mapping. The standing column says
whether the obligation is **carried** unchanged, **restated** because the target changes its
subject, or **dropped** because the target supersedes it. The evidence for every row is a
receipt on final source, accounted by test identity; the quoted receipts are context only.

| Obligation | Behaviour to observe | Route | Standing | Package |
|---|---|---|---|---|
| 1 | The whole product suite passes on final source in the ordinary and fault lanes, with the required selection accounted by test identity | `uv run ci test`; `ci test coverage`; `ci test review` | Carried. No full run exists to carry credit from | UDM-22 |
| 2 | Repository checks pass on final source | `uv run ci check` and its steps | Carried | UDM-22 |
| 3 | Native request, concurrency and recovery: two demands share one request; a stale owner is displaced; revoked support is honoured; a writer crash, a known rollback and an unknown commit are told apart; an exact intent replays; sibling work proceeds; retirement is bounded | `ci test`, native tests against a registered head | Restated in one part: an intent now records validator identity per family and not the kernel digest (UDM-10, UDM-12), so "exact replay" is judged against the new record. The cross-release fan-in assertions left unverified at N28 are observed first in UDM-20 | UDM-22 |
| 4 | Binding and admission matrices: same base, exact cardinality, incomplete against empty discovery, wrong role, source, contract or support | `ci test`, native | Restated where admission selects by a **lowered operation attribute** instead of an identifier list (UDM-05). The two negative controls recorded as expecting older error codes are routed to their owner before UDM-22; if unresolved at the run, they are second-class failures with that owner | UDM-22 |
| 5 | Provider qualification on real providers: PDF capture, recognition and enrichment through Docling with CUDA and RapidOCR; Nemotron; spaCy, HanLP, the formal and coreference providers, GLiNER; the E5 encoder | `ci test --providers-only -- PATH`; provider preflights; `ci ingest` | Carried. Nemotron inference on the head is recorded as unverified; the eight process-managed providers are recorded as open | UDM-22 |
| 6 | Rich, public and serving behaviour: structural issue, dossier, gap and detached export; rich admission, reading and pagination; source revocation; refusal of an old continuation; event fit, issue and score; the tool and resource journeys | `ci test`, native; `ci` export and verify | Restated: continuation and reuse now rest on the declared reuse basis and the **cache tiers** (UDM-13 to UDM-15), and the move of cachetools to 8.0.1 changes the read-basis digest once, so existing cursors refuse once by design. No receipt for the tool and resource journeys is cited in the earlier plan; they are observed here for the first time | UDM-22 |
| 7 | Graph fidelity: isolates and unresolved endpoints, parallel roles and self-loops, strongly connected components, equal-value cutoff, wrong-snapshot cursors, mapping-sensitive rooted assessment, with independently authored expectations | `ci test` | Carried (`not_run` at the earlier plan's authoring). The single support-edge meaning of UDM-07 is its subject for the support graph | UDM-22 |
| 8 | Export and detached verification keep source and prediction releases separate and exclude protected labels | `ci` export and verify; `ci test` | Carried | UDM-22 |
| 9 | Fault behaviour: writer crash, cancellation in each of three phases, quarantine, and the budget and retirement controls of the execution host | `uv run ci test --lane fault` | Carried. No fault-lane receipt has ever been recorded | UDM-22 |
| 10 | Model, compiler and identity examples with independent expectations; the reuse and change matrix (unchanged recipe, equal-content cutoff, added member, replicates) | `ci test` | Restated: the identities under test are the target's layers (**program identity**, kernel, validator per family, code, release), and release identity no longer includes generator sources (RC11) | UDM-22 |
| 11 | Source evolution: `ci model change` preview, candidate, registration and deployment; migrated callers; recovery from a partial apply | `ci model change …`; `ci test` | Restated: a candidate that changes no installed byte is not authored (UDM-11), and the preview explains generated-SQL differences (UDM-19) | UDM-22 |
| 12 | PostgreSQL realization: fresh-target installation, privileges, rollback replay against uncertain effect, once-only initialization, helper retirement | `ci test` on a private host; `ci model change` | Restated: grants derive from **program declarations** (UDM-03), programs reach installation through the typed registry (UDM-09), and the `TEMP` grant is typed (UDM-17). The earlier plan's "remaining inline authoring" is superseded by those packages and is not a union row | UDM-22 |
| 13 | Generality: an independently specified context that is not statistics runs through the same machinery | `ci test` | Carried. It doubles as the observation that a pack-extensible vocabulary accepts a second pack's members | UDM-22 |
| 14 | PDF product equivalence, tamper detection, resume and failure classification; the round-trip oracle on each kind of PDF publication | `ci test`; `ci run resume` | Carried. The 13 failures of the N13 attempt stay held as recorded | UDM-22 |
| 15 | Set-wise validity: revocation, supersession, protected closure; pinned reads; share locks; set form | `ci test`, native | Restated: every existing operation now states its claim. The 27 classified today name their families and every other existing operation declares `none`, which is what its absent family meant, so its behaviour is unchanged. Only an operation added without a claim is undetermined and receives **conservative validity** (RC05, RC14) | UDM-22 |
| 16 | The 29 originals are registered and read back byte for byte through the normal reader from canonical development | `ci db check`; `ci release check`; readback against the inventory digest | Carried. Readback after N29 is recorded as pending. It is part of the re-adoption check | UDM-21, repeated on the final head at UDM-23 |
| 17 | The whole book runs to completion: 518 pages, 29 regions, a fate for every demanded family in every region, and the whole-view composition | `ci run` on the book under the stated memory policy | Restated: the run is on the series' final release, from the original, with a new demand; its pass criteria are those of UDM-23 | UDM-23, after UDM-20 |
| 18 | One demand is interrupted under control, resumed, and then repeated unchanged with no work done | `ci run`; `ci run resume` | Carried for interruption and resume, which were demonstrated on N18 and N21 and not since capture's recipe changed. Restated for the repeat, which has never been demonstrated: with the kernel component removed from the watermark (UDM-12), "no work" is judged against the new watermark | UDM-23 |
| 19 | The construction produced regionally in production agrees with the retained whole-book construction (the comparison the DDO plan names PE-S33) | `compare_retained_book_construction.py` in the evidence folder `2026-11-16_ddo-current-native` | Carried. The script requires the exact retained demand and a complete admitted population, and refuses while products are pending; UDM-23 states how it is pointed at the new demand and which disagreements the recorded recipe change predicts | UDM-23 |
| 20 | Development adoption is complete: derived data is regenerated under the head | `ci db migrate`; `ci release activate`; the book run | Restated: regeneration happens once, under the series' final release at the second adoption, and not under N29 | UDM-21, UDM-23 |
| 21 | Integrated recognition through Nemotron works on the head, and the managed launcher restores the generation it owns | `ci ingest` in the Integrated profile | Carried | UDM-21 for the bounded check; UDM-22 for the provider receipt |
| 22 | Chandra OCR | none | Excluded by the operator; not an obligation | none |
| 23 | The bounded native composition control completes | Native composition fixture on stage | Dropped as a separate obligation; it becomes the first reproduction of UDM-20 and its assertions join obligation 3 | UDM-20 |
| 24 | Documentation and decision-record checks pass | `uv run ci docs check`; `uv run ci adr lint` | Carried | UDM-22 |

Four narrower expectations inside these obligations are **dropped** because the target removes
their subject; each is replaced by a target obligation below. They are listed once, with the
passages they come from, under [What this supersedes](#what-this-supersedes).

### Obligations the target introduces

These are behaviours of this series' design. Each design package states its own acceptance
evidence in its companion. The rows here are what the union must show on final source, by test
identity, for the target to count as qualified. Tests for them are written in this series under
the test series' contracts: expectations authored independently of the code under test, scenario
construction from the model's owner, and a correspondence claim tested by changing the
declaration inside the test. Every design package's acceptance tests are part of the required
selection.

| Target obligation | Behaviour to observe | Owning package |
|---|---|---|
| T1 | An operation whose validity family is undetermined compiles, runs and publishes under **conservative validity**, and the run reports it with the `validity_undetermined` diagnostic. It is never refused for being undetermined. The union shows this with a fixture operation left deliberately undetermined, run on the stage; the book does not exercise it | UDM-06 |
| T2 | A generator edit that changes no installed program byte produces no native revision: the candidate is not authored | UDM-11 |
| T3 | Acquisition performs no generation. It compares the installed kernel with the digest the release records, and refuses on a difference | UDM-08 |
| T4 | A repeated identical read from the command line, in a new process, reuses a continuation page, after authority is rechecked | UDM-14 |
| T5 | Declaring a validity family on an operation inside a test causes every guard, validator and dispatch to select that operation, with no edit to any program | UDM-05 |
| T6 | Editing one family's validator program, one of that program's callees or the family's completion guard reconfirms only work sealed under that family; work sealed under other families is not replayed | UDM-10, UDM-12 |
| T7 | A change confined to the kernel does not move the inputs watermark, so a waiting obligation whose prerequisites are unchanged is still skipped | UDM-12 |
| T8 | A vocabulary's **declared openness** governs: a member outside a closed vocabulary refuses; a member outside a vocabulary that is open with known members is accepted and reported | UDM-02 |
| T9 | One **compiled model** per identity of the model sources: every consumer observes the same one, and a changed declaration yields a new compiled model without a restart | UDM-01, UDM-13 |
| T10 | A program that calls a name absent from the typed registry is refused at generation | UDM-09 |
| T11 | Refusal at generation or preparation occurs only for internal inconsistency (a field outside the declaration, a member outside a closed vocabulary, a self-contradictory or unmet family claim, a dangling name) and for omissions in the integrity layer (a grant, guard, role, support-edge kind or privileged-effect owner). An undetermined declaration or an unknown term of an open vocabulary never refuses | UDM-03, UDM-07 |
| T12 | A long-lived process notices on its next use that the active generation changed, without being told | UDM-13 |
| T13 | Immutable release content is not hashed again at each acquisition; an explicit verification command detects a tampered archive | UDM-12 |
| T14 | A fresh request reuses a served result under its declared basis, if the premise of UDM-15 is settled in favour; otherwise this row is recorded as not adopted | UDM-15 |
| T15 | A source demand under a release uses that release's archived slices after the working tree's copy changes | UDM-18 |
| T16 | Timestamps in analytical exports are labelled UTC whatever the machine's zone | UDM-16 |
| T17 | Nothing imports the earlier model, and neither retired migration tree exists | UDM-04, UDM-19 |

The book does not exercise T1. Every operation of the book pipeline (capture, organization,
discovery, sentence, formal, math, linguistic, construction and composition work) declares
`none` or names its families, so the book runs under the same generic validity as today, unless
the operator chooses to mark an operation undetermined. Whether the conservative path fits inside
settlement, whose lock timeout is five seconds and which is the phase where the last book run
failed, is settled by UDM-06's bounded observation on the stage before revision A is frozen, and
so before either final run.

## What this supersedes

The qualification scope of the DDO plan's closing package (DDO-12) passes to this series in full.
The DDO plan's documents are not edited by this series; the coordinator records superseded items
for the operator's later reconciliation (UDM-24). The passages whose qualification content this
companion replaces:

- [preservation-adoption-and-qualification.md](../declared-data-operations/preservation-adoption-and-qualification.md)
  `:296–317`, "Qualification and adoption consequences": the rule that evidence keeps its scope is
  kept; the additions to the required union are obligations 14, 15, 17 and 18 above; "Steps 8 and
  9 follow integration of every slice" becomes UDM-23 and UDM-22.
- The DDO coordinator's statements that DDO-12 owns the qualification union, and its "Next
  execution" for the book
  ([declared-data-operations_2026-11-12.md](../declared-data-operations_2026-11-12.md), the
  sections dated 2026-11-18, and `STATUS.md` "Next execution"): the pending canonical checks,
  custody recheck, book activation, bounded composition control and Nemotron verification are
  UDM-20 and UDM-21; the book retry, coverage, repeat and comparison are UDM-23.
- [products-and-support.md](../declared-data-operations/products-and-support.md), three passages
  whose qualification controls are dropped expectations. `:527–535` (PE-S21): a completion seal or
  receipt whose kernel digest differs runs the full completion battery; replaced by T6.
  `:575–576`: the inputs watermark changes when the kernel digest changes; replaced by T7.
  `:422–423, :451`: a null validity family means "no per-kind validator applies"; that claim is
  now made explicitly as `none` (obligation 15), and a genuinely absent claim is T1. The design
  supersession itself is stated in the
  [programs and identity companion](programs-identity-and-revisions.md) and the
  [validity companion](lowered-operation-facts-and-validity.md).
- The fourth dropped expectation is that acquisition compares the checkout's regenerated capture
  with the installed descriptor; it is replaced by T3 (UDM-08).
- The test series' closing package,
  [TDM-18](../test-domain-model-and-execution_2026-11-17.md#tdm-18), is **not** superseded. Its
  relation to UDM-22 is stated in that package below.

## UDM-20 — Book-run diagnosis

**Why first.** Two failures stopped the last run, and the account of each is a narrative. If the
narratives are right, four commits have already repaired them and the final run should complete.
If either is wrong or incomplete, UDM-23 would discover it after every design package has landed,
when the cause is hardest to isolate and the cost of a failed run is highest. The package depends
on no design package and runs on the source as it stands.

**Vision.** The package reproduces each failure on the smallest case that shows it, observes the
database while it happens with the database's own facilities, and writes down what each
observation decides. Its product is an evidence record for each failure with one of three
conclusions: *explained and repaired* (the cause was observed and the bounded case now completes
with a margin), *explained and not repaired* (the cause was observed and a change is needed,
which is named and routed, or a repair is made and awaits the revision that carries it), or *not
reproduced at bounded scale* (with the largest scale tried). It runs on stage, which is at N29
and is owned scratch. It does not touch canonical development and does not start a whole-book
run.

**How the database is observed.** The completions run on the product's worker connections, not
in the diagnostician's session, so a setting made for one session captures nothing. Statement and
plan capture is therefore configured for the worker role on the stage database for the duration
of the diagnosis, as a role-level setting made with the administrative login (`ALTER ROLE … IN
DATABASE … SET`): `session_preload_libraries` naming PostgreSQL's `auto_explain` module,
`auto_explain.log_min_duration`, `auto_explain.log_nested_statements` and
`log_min_duration_statement`. The settings take effect on new connections, so the workers are
restarted once. The settings applied are written into the evidence record. When the diagnosis
ends they are removed (`ALTER ROLE … IN DATABASE … RESET`), and the record includes a reading of
`pg_db_role_setting` showing that none remains. Nothing of this kind is configured on canonical
development.

**Step 0: keep what the failed run left.** Failures in the managed result store expire in a week.
Before anything else, the result of run `1dd5d45d…` and the interrupted fixture retry `82ba7773…`
are placed on hold and copied with `ci evidence retain`, and three facts are read from them and
from stage: which nine regions timed out and how large each was (pages, sentence occurrences,
completion payload size); what the "nested physical-join uncertainty" in the settled result
refers to, by reading the classification that N29 added for nested uncertainty in execution error
groups; and the state of the one unresolved completion intent. If the records have already
expired, the package says so and proceeds from the plan's narration alone.

**Reproduction 1: settlement at the 120-second limit.** The smallest scope is one region. The
package takes the largest of the nine regions that timed out, as an excerpt of the book's
original registered in the stage project (or by whatever narrower scoping of a demand the product
offers, chosen at entry), and runs the sentence work for that region alone on N29. For contrast it
runs the largest region that completed, which had 1,035 sentence occurrences. Observed:

- *Settlement time against the limit.* The wall time of each completion transaction, read from
  the statement durations in the database's log, next to the 120 seconds of `settings.py:70`.
  Decides whether the N27 repair gives a margin or only moves a region from just over the limit
  to just under it.
- *How the time is spent.* The completion runs inside installed functions, so a plain `EXPLAIN`
  of the call shows nothing useful. With nested statements logged, `auto_explain` records the
  plan and time of each statement the functions execute. Decides whether the time is in
  canonical JSON, as narrated, or elsewhere: validity selection, a support walk, or an inventory
  read like the one N26 repaired.
- *Growth with payload.* The same observation on two or three regions of different size. Decides
  whether settlement time grows roughly in proportion to the payload or faster. Faster growth
  means a larger region or a larger book would hit the limit again whatever the digest costs, and
  the settlement program needs a different shape.
- *Waiting against executing.* `pg_stat_activity` (state, wait event, transaction and query start)
  and `pg_locks` with `pg_blocking_pids`, sampled every few seconds while a completion is in
  flight, and the error code of any timeout: a statement timeout and a lock timeout are different
  codes, and the lock timeout in force is five seconds, not 120. Decides whether "timed out in
  settlement" was computation or contention between the regional workers and something else
  holding a lock.
- *Whether the server has a timeout of its own.* `SHOW statement_timeout` under each application
  role, and the per-role and per-database settings in `pg_db_role_setting`. Decides whether the
  binding query's lack of a deadline is real or whether a server setting bounds it, and what the
  effective bound on every other statement is.

**Reproduction 2: the composition's binding query.** The smallest scope is the native composition
fixture whose retry was interrupted; completing it is also what obligation 23 asked for. The
package then composes over two, four and eight regional inputs taken from the excerpts of
reproduction 1. Observed:

- *The plan of the generated statement.* The binding is one statement produced by
  `binding_statement`; the package renders it for the compiled binding and asks the database for
  `EXPLAIN` first, without executing, then for `EXPLAIN (ANALYZE, BUFFERS)` inside a rollback-only
  transaction with a session statement timeout, so that the diagnosis cannot itself run
  unbounded. Decides whether a cross product is present: a join with no condition between
  regional inputs, with a row estimate that is the product of its inputs. The statement the
  binder produced at commit `1d3640990`'s parent is explained the same way for comparison. It is
  rendered by a probe in the evidence folder that imports that revision's
  `data_operation_bindings.py`, obtained with `git show`; no second working tree is created and
  nothing from that revision is deployed.
- *Growth with the number of inputs.* Rows and time at two, four and eight inputs. Decides whether
  growth is additive, which is what selection role by role should give, or multiplicative.
- *Behaviour with a region withheld.* One regional input is deliberately left incomplete. Decides
  whether the two refusals of the last run were the correct answer to nine missing regions
  arriving promptly, or a separate defect: `binding-covers` is the expected refusal when families
  are missing, while `sequence-ordinal` reported source members without population positions and
  may be independent of the timeouts. The expected behaviour under the flexibility frame is
  specific: an incomplete population is a legitimate state, the composition records an explicit
  fate for it promptly, and it does not run a query for minutes first.
- *Wait state*, as in reproduction 1, while the binding runs.

**What each result feeds.**

| Observation | If it shows | It goes to |
|---|---|---|
| Time inside the seal or payload digest | The seal's cost still dominates | UDM-10 and UDM-12, which redefine what the seal covers: whatever the per-family seal hashes is computed once per completion, and that becomes an acceptance point there |
| Time inside validity selection or a guard | Selection by identifier list is costly at book scale | UDM-05, which replaces those selections; the observed statement becomes one of its examples |
| Time inside a support walk | The walk is the cost | UDM-07 |
| Settlement time growing faster than payload | The limit will be reached again | A change to the settlement program, routed as below; and the pass criteria of UDM-23 name the margin |
| Lock waits | Contention between regional workers | The owner of the lock named by `pg_locks`; if it is the project lock N28 introduced, that commit's owner |
| A cross product remains in the binding | The N28 repair is incomplete | A repair to the binder, routed as below |
| No server-side statement timeout | The binding path is unbounded | A decision, owned by this package, on a declared deadline for binding execution in `DatabaseSettings`, applied through the same `_deadlines` route, so that a stall becomes a classified failure with a fate and not an indefinite wait |
| Composition with a withheld region is slow or refuses the wrong check | Partial populations are not handled as a state | A repair in the composition; this one matters to the flexibility frame directly |

**Decisions the package owns, and repairs.** The package owns the diagnosis, the choice of
bounded cases and the decision on a binding deadline. Its authority to repair is bounded. Where a
cause lies inside the subject of a design package, the finding goes to that package (UDM-05,
UDM-07, UDM-10 or UDM-12) as an input and is repaired there, not here. Where it lies in code that
no design package owns (the binder, the composition, the shape of settlement, a binding deadline
in the database settings), the package makes the smallest repair that lets the bounded case
complete, because the series owns the whole-book run and nobody else will.

A repair that changes no installed byte is observed on the bounded case at once. A repair that
changes installed bytes, which generating the programs and comparing them with the current frozen
objects decides, joins the next planned revision that is not yet frozen: revision A, otherwise B,
otherwise the transition. It plans no revision of its own. Such a repair is confirmed on the
stage once the revision that carries it is deployed there, by running the bounded case again;
until then the package's conclusion for that failure reads "diagnosed; repair pending" with the
revision named. If a needed repair turns out to be a design question larger than a bounded fix,
the package stops and reports it to the coordinator as an open premise of UDM-23.

**Bounds.** Every reproduction runs with a statement timeout and a wall-clock limit set in
advance. The scale ladder stops at eight regional inputs and at the largest single region. If
neither failure reproduces within those bounds, the package records "not reproduced at bounded
scale" and does not escalate to a whole-book run: UDM-23 then carries the same passive
observations (the activity and lock samples and statement durations) so that a recurrence is
explained by the run that shows it.

**Where the evidence goes.** A dated folder under `docs/design_review/evidence/` with a README,
the rendered statements, the plans and the samples, and one evidence record per failure, finalized
with `uv run ci evidence finalize`. The versions of PostgreSQL and of the interpreter are recorded
with the results.

**Prerequisites.** None.

**Native revision.** None of its own; a byte-changing repair joins a planned revision as above.

**What this keeps open.** The diagnosis protects the exploratory property that matters most at
book scale: a partial result is a result. A region that cannot be completed, or a population
with members missing, has an explicit state and fate, and the rest of the document's knowledge is
still composed or its absence is stated. The package closes nothing in the model. The one thing
it may add, a deadline on binding execution, bounds how long the machinery waits and does not
bound what content is admissible; a binding that exceeds it is reported as a classified
operational failure, not as invalid knowledge.

**Acceptance evidence.** For each of the two failures, the record states the cause with the
observation that shows it (a plan, a statement duration, a wait event), and the observation is
one that would have looked different had the narrated cause been wrong: time attributed to named
statements, not a total. A reproduction that merely completes is not an explanation and is
recorded as "not reproduced". Where a repair is made, the bounded case that failed or stalled
before it completes after it, under the same policy and bounds, with the before and after plans
retained; for a repair carried by a revision, that observation is made on the stage after the
revision is deployed and is added to the record then. The composition with a withheld region
returns its refusal and records its fate within the binding deadline. The settings of the
diagnosis itself (the capture settings, timeouts, sampling interval, scale) are in the record,
with the reading that shows the capture settings were removed.

## UDM-21 — Environments at the head

**Vision.** The package finishes the adoption of N29 that the earlier plan left pending, so that
canonical development and the book project are in a known, checked state before the design
packages begin to change installed programs, and so that the originals are known intact. This is
the first of the two adoptions of canonical development and the book. It follows UDM-20's
diagnosis, so that any cause found in canonical-development state (the unresolved intent, the
leases) is settled before adoption; repairs that change installed bytes arrive with the series'
revisions, not here. It performs the recorded pending steps in order:

1. Run `uv run ci db check` and `uv run ci release check` against canonical development at the
   head. These were deferred when the N29 deployment was interrupted at command exit.
2. Re-verify the 29 originals: read all 29 descriptors back through the normal reader, and hash
   the bytes at their 28 local paths with a system tool, comparing both with the recorded
   inventory digest `ad051b0d…f2e27` and the per-file digests. The expectation is the inventory
   recorded before the migration, not anything the database computes about itself.
3. Settle what the failed run left: the one unresolved completion intent is replayed exactly or
   retired by the route its remediation names, and the absence of live leases is confirmed.
4. Activate the head's release for the book project with `uv run ci release activate`, moving
   generation 4 to 5 under the expected-generation check.
5. Run the bounded Integrated recognition check through Nemotron on the head (one page, on
   stage), confirming that inference requests are actually made and that the launcher restores
   the generation it owns. The last attempt was interrupted before demand registration with zero
   inference requests.

**What must be regenerated, and when.** The package states this and does not do it. Because the
recipes of capture, organization, organized-source discovery and construction changed between N23
and N29, the book's capture must be produced again from the original PDF, which means all 518
pages are recognized again, and everything downstream of capture is re-derived. Sentence and
formal-evidence definitions agree across the revisions, so their products could be reused, but
only where their exact resolved inputs and current trust still match; with capture regenerated,
that is something the run observes through its equal-content cutoff and is not assumed here.
Encoder vectors are regenerated under the current numerical policy; no reader for the old ones
exists. The N28 change lets an active release attach unfinished equivalent work across
generations, but discovery's recipe changed and uses fresh execution.

None of that regeneration is started under N29: each of the series' revisions forces releases
to be prepared again, so derived data generated now would be generated again and would earn no
credit. Regeneration happens once, in UDM-23.

**The re-adoption check.** Steps 1, 2 and 4 are defined here once and named *the re-adoption
check*: the database and release checks, the 29 originals re-verified against the recorded
inventory, and activation of the book under the expected-generation check. UDM-23 repeats it on
the final head, after the series' revisions are deployed to canonical development. Those are the
only two times it runs.

**Decisions it owns.** How the unresolved intent is settled; whether activation proceeds if a
check in step 1 reports a difference (it does not: the difference is diagnosed first). Failure
behaviour: any original whose bytes or descriptor differ from the inventory stops the package
and is reported to the operator before anything else is done, because the originals are the one
thing that cannot be regenerated.

**Consumer scope (complete).** Canonical development; the nine projects holding the 29
descriptors; the book project; stage for the Nemotron check. No source changes.

**Prerequisites.** UDM-20 supplies the diagnosis of what the failed run left in canonical
development, the unresolved intent in particular, so that step 3 settles it knowingly.

**Native revision.** None.

**What this keeps open.** Nothing is closed. Activating the book on the head keeps the working
loop available during the series: bounded demands against the book can be run by any design
package that wants real material, without waiting for the final run.

**Acceptance evidence.** Receipts for the two checks. A custody statement listing 29 descriptors
and 28 paths with digests equal to the pre-migration inventory, produced by a tool independent of
the application. The book project's generation read back as 5 selecting the head's release. A
Nemotron receipt showing a non-zero count of inference requests and the restored launcher
generation. Each is dated and names the commit and native revision it was observed on.

## UDM-22 — The managed union on final source

**Vision.** Once every functional package is implemented and the last native revision is
deployed to stage, the package freezes the source at a named commit and runs the whole
qualification union there: every carried and restated obligation above except those belonging to
the book, and every target obligation. Its product is an account, by test identity and receipt,
of what passed, failed, was blocked or was not run on that commit, with every failure assigned
to an owner. The run observes and does not tune: it settles no default, bound or placement.

This will be the first full-run profile the project has had since 2026-11-10 and the first run
of the fault lane at all. The package therefore does not assume that the suite is close to
passing, and it is designed to produce a useful account whatever it finds.

**The run.**

1. Record the final-source commit, the native revision and the registered head of stage, and the
   provider prerequisites present (for the process-managed providers, the assets variable
   `CORPUS_PM2_NATIVE_TEST_ASSETS`; without it that selection reports `blocked`).
2. Run `uv run ci test` with no narrowing. This is the *original attempt*: it requires both
   lanes and it supplies the required selection for everything that follows. It is held as soon
   as it settles, whatever its outcome.
3. The fault lane runs serially and exclusively and refuses a worker count. It needs the native
   host to itself, so no other session runs native work while it runs. The package arranges that
   with the operator in advance, because other sessions share the workstation.
4. Run the provider selections with `uv run ci test --providers-only -- PATH` for each provider
   family of obligation 5. A controlled converter or double never satisfies these. An empty
   selection is `not_run` and is treated as a defect of the selection.
5. Run `uv run ci check`, `uv run ci docs check` and `uv run ci adr lint`.
6. Retry failures with `ci test retry`, which recollects the required selection, and account for
   the chain with `ci test coverage ORIGINAL RETRY…` and `ci test review ORIGINAL RETRY`. The
   failed original is retained and never relabelled.

**Triage.** Each failing identity is read and put in one of three classes.

- *A defect of this series' design or implementation*, including a default, bound or placement
  that the run shows to be wrong. For such a defect the change is made within the series and the
  affected evidence is gathered again; the owning package makes the change, and the coverage report's source
  differences say which earlier receipts still stand. If the change alters installed bytes, a
  further revision is needed, the stage follows it, and the union's native rows are observed
  again on it.
- *A failure outside this series' design.* Examples the earlier plans already record: the two
  negative binding controls expecting older error codes, if their owner has not resolved them by
  the run, the held failures of the N13 PDF attempt, and the provider two-region timeout the test
  series keeps open. It is recorded with its
  identity, its receipt and its owner (the test series, the DDO plan's reconciliation, the test
  audit, a provider's owner) and routed there. It is not repaired here and not absorbed into the
  series' scope, and it stays visible in the closing account as open.
- *A defect of the test, harness or environment.* A stale expectation, a missing prerequisite, a
  `ci` command that failed its contract. A `ci` defect is repaired at once in its owning layer, as
  the repository's rule requires. A stale expectation in a test this series wrote is this
  series' to fix; in a test it did not write, it is routed.

**What counts as passing.** The package is complete when every identity of the required
selection has, on final source, either a passing receipt or a recorded failure of the second
class with a named owner, and no identity is unaccounted for. The target obligations T1 to T17
(T14 only if UDM-15 adopted it) and every restated obligation must have passing receipts: a
failure among them is by definition of the first class. The closing account states the result per obligation in the repository's four
words and gives no aggregate figure. Whether open second-class failures prevent the series from
closing is the coordinator's and the operator's judgment at UDM-24, made with that account in
hand.

**Relation to the test series' closing package.** TDM-18 requires the same kind of run for its
own purpose: the ordinary, provider and fault selections on accepted source, reconciled by
identity. The two are not merged. UDM-22 does not close any finding of the test series or
refresh its audit. But one run on one commit can serve both, and repeating it would be waste. The
package therefore offers its original attempt, its retries and its coverage report to TDM-18 by
receipt identifier. The test series judges for itself whether the source and selection are
applicable to its findings. The native consumers that TDM-18 records as lacking production
prerequisites are checked at step 1; any still lacking is a `blocked` row here with the
prerequisite named.

**Consumer scope (complete).** No production source changes by design. Tests written by this
series' design packages are part of the selection. The managed result store, the evidence folder
for retained copies, and stage.

**Prerequisites.** The functional packages UDM-01 to UDM-19 supply final source, with UDM-15
only for the queries whose premise was settled; T14 is otherwise recorded as not adopted. UDM-20
supplies the knowledge that the native composition path completes, with any repair it made
confirmed on the stage. The bounded observations of the design packages are complete, UDM-06's
settlement-fit observation among them.

**Native revision.** None.

**What this keeps open.** A qualification union can quietly become a rule that every declared
behaviour be determined. This one does not: T1, T8 and T11 require that undetermined and open
declarations run and are reported, so a wrong implementation that refused them would fail the
union. T1 is shown by a fixture operation left undetermined on purpose, because every existing
operation states its claim. Routing outside failures instead of absorbing them keeps the series'
scope what the operator decided and leaves other owners' choices to them.

**Acceptance evidence.** The original attempt's identifier and outcome; the coverage report
showing no missing lane and no unresolved identity for the required selection; a fault-lane
receipt, the first; a provider receipt per family on real providers, or a `blocked` row naming
the prerequisite; the three check receipts; and a triage table with one row per failing identity
giving its class, owner and receipt. The account is independent of the code under test in the
sense that matters here: the required selection comes from the original attempt and not from
whatever a retry chose to run.

## UDM-23 — The whole-book run

**Vision.** On final source, with the series' revisions deployed to canonical development and
the book activated on the final release, the book is processed from its original PDF under one
demand. That demand is interrupted under control, resumed, completed, and then repeated
unchanged; and the retained construction is compared as the earlier plan required. This is the
series' end-to-end validation: the one observation that the target, assembled, does the
product's main work.

**Entry.** This is the second and last adoption of canonical development and the book. Deploy
the series' frozen revisions to canonical development with the expected predecessor. Repeat the
re-adoption check of UDM-21 on the final head (the two checks, custody of the 29 originals,
activation of the book on the final release). Confirm that UDM-22's native and provider rows
passed on this same source, and that Nemotron is reachable: an earlier run failed on an absent
endpoint.

**The run.**

1. *Start* the book under the stated memory policy: the 16 GiB policy recorded in
   `whole-book-host-execution-policy.json` (owned state 17,179,869,184 bytes, packet 603,979,776,
   reply 201,326,592, one million rows). The policy file used is retained with the run. If UDM-20
   showed that a bound must change, the changed policy is a new file with the reason recorded and
   not an edit of the old one.
2. *Interrupt during capture*, after a recorded number of pages have been acknowledged, by the
   cooperative route, and confirm cleanup: no live lease, no orphaned process, the provider's GPU
   memory released. Capture's recipe changed, so the resume behaviour demonstrated on N18 and N21
   is demonstrated again.
3. *Resume* the same demand with `ci run resume`. The acknowledged pages are reused and only the
   rest are prepared.
4. *Interrupt once more during regional work*, after some regions have settled and while others
   are in flight, and resume. This is the phase in which the last run failed and in which no
   interruption has been demonstrated; settled regions must not be redone and in-flight attempts
   must resolve to a definite state.
5. *Complete.* The demand reaches a terminal state.
6. *Repeat unchanged.* The same demand is submitted again with nothing changed. It must do no
   work.
7. *Compare.* Run the retained-construction comparison (PE-S33). The retained script requires
   the exact retained demand, and this run has a new demand on a release whose construction
   recipe changed between N23 and N29. If the script hard-codes the demand, a successor copy
   that names the new demand is placed in this package's evidence folder and the retained
   script is left unedited. The disagreements the recorded recipe change predicts are written
   down before the run, so that a disagreement is judged against a prior statement.

**What counts as passing.** All of the following, each observed and none inferred from the
executor's own summary alone.

- Capture is published for all 518 pages with its protective checks committed.
- All 29 regions reach a terminal state without an infrastructure failure. No settlement times
  out; the longest settlement is recorded next to the limit, with the margin UDM-20 named.
- Every demanded family in every region has an explicit fate. This is a statement about
  coverage and not about success: a region whose content yields a partial, unknown or
  unsupported result has a fate saying so, and that passes. A timeout, an unclassified error or
  a missing fate does not.
- The whole-view composition is published, or, where a region's fate legitimately leaves its
  population incomplete, records its own explicit fate promptly. It does not stall.
- After each interruption, cleanup is established by an independent process and lease check, and
  the resume reuses what was acknowledged: the counts of pages or regions redone are read from
  the database and compared with the counts recorded at the interruption.
- The unchanged repeat creates no new derivation, makes no provider request and starts no native
  attempt. The expectation is zero, and it is checked by counting derivations, attempts and
  provider requests in the database and the provider logs before and after, by a query that is
  not the executor's.
- The comparison runs to a conclusion on the complete admitted population. A refusal because
  products are pending is `blocked`, not `passed`. A reported disagreement is a finding to be
  read: it is a failure of the run unless it is among the disagreements predicted before the run
  from the recorded change of construction recipe.
- The run's report lists the operations that ran under conservative validity. The expected count
  is zero, because every operation of the book pipeline states its claim; a different count is
  explained by an operation the operator chose to mark undetermined, or it is a finding.

The run observes and does not tune. The observations it retains (rich-rule input sizes,
settlement times, lock waits, cache footprints) are compared with the bounded observations that
settled the corresponding choices on the stage. A contradiction is a finding: the change is made within the series and the affected evidence is gathered again,
this run included.

A run that completes after an unplanned failure and a manual intervention is recorded as what it
was: the failed attempt is retained, the intervention is described, and whether the subsequent
completion satisfies the obligation is stated with that qualification, not silently.

**What is retained.** The demand identifier, the release and runtime identifiers, the native
revision, the book project's generation and the final-source commit; the policy file; the
managed result of every attempt, including the interrupted and any failed ones, placed on hold
and copied with `ci evidence retain`; the counts used for the reuse and no-work checks with the
queries that produced them; the comparison's output and the predictions written before it; the
observations named above; and, if UDM-20 ended "not reproduced", the passive activity and lock
samples. These go to a dated evidence folder with
a README and records finalized by `uv run ci evidence finalize`. The regenerated derived data
itself stays in canonical development; it is the adopted state that obligation 20 asks for.

**Decisions it owns.** The points of interruption; whether a disagreement in the comparison is
explained; whether an attempt that needed intervention is offered as satisfying the obligation.
Failure behaviour: a failure during the run is first classified with UDM-20's observations. A
cause inside this series' design returns to its package, and the run is repeated after the
repair, since the source changed. A cause outside it is recorded and routed as in UDM-22, and
the obligation stays open with its owner named.

**Prerequisites.** UDM-21 supplies checked environments and the re-adoption check. UDM-22
supplies final source whose native and provider rows passed. UDM-20 supplies the explanation of
the previous failures, its repairs confirmed on the stage, and the margin to watch.

**Native revision.** None.

**What this keeps open.** The pass criteria are written so that the run validates the machinery
without constraining the knowledge. Coverage means every demanded family has a fate, in whatever
state the content supports; competing, partial and unknown results pass as themselves. An
operation the operator marks undetermined runs and is listed. Nothing is closed.

**Acceptance evidence.** The list under "What counts as passing", with each item's receipt or
query result, dated and tied to the final-source commit. The independent parts are the ones a
wrong implementation would get past otherwise: the no-work repeat is judged by counts taken
outside the executor; reuse after resume is judged against numbers recorded before the resume;
and the comparison's expected construction is the retained one, produced by a different route
than the regional production it is compared with.

## Sequence

UDM-20 starts at once and depends on nothing; UDM-21 follows its diagnosis and is the first
adoption. Neither waits for the design packages, whose revisions go to stage only. When all
functional packages are complete, the source is frozen: UDM-22 runs on stage and the
workstation, the second adoption deploys the series' revisions to canonical development, and
UDM-23 runs. UDM-22 precedes UDM-23 because a whole-book run on source whose native tests fail
would be an expensive way to find a defect that a test already shows. If either final run
reveals a needed change, the change is made within the series and the affected evidence is
gathered again, including the affected rows of the other run. The series closes at UDM-24
only when both accounts are on the same commit.

## Open premises

| Premise | Evidence that settles it | Work it constrains |
|---|---|---|
| The settlement timeouts were caused by the duplicated payload digest (narrated) | UDM-20, reproduction 1: time attributed to named statements | Whether the settlement program needs more than the N27 repair; the margin named in UDM-23 |
| The binding stall was a cross product from sequence inputs and relational role joins (narrated) | UDM-20, reproduction 2: the plan before and after `1d3640990` and growth with inputs | Whether the binder needs a further repair before UDM-23 |
| The `sequence-ordinal` refusal was a consequence of the nine missing regions and not a separate defect | UDM-20, the withheld-region case | A possible repair in the composition |
| No server-side statement timeout bounds the binding path | `SHOW statement_timeout` and `pg_db_role_setting` on stage and canonical development | The binding deadline decision in UDM-20 |
| The retained comparison script can be pointed at a new demand without changing what it compares | Reading the script at entry to UDM-23 | Whether a successor copy is needed for step 7 |
| The failed run's records are still in the result store | Step 0 of UDM-20 | How much of the diagnosis starts from records and how much from narration |
| A demand can be scoped to one region of the book without registering an excerpt | Reading the demand's scoping at entry to UDM-20 | The construction of the bounded cases only |
| Sentence and formal-evidence products will be reused after capture is regenerated | Observed in UDM-23 through the equal-content cutoff | Nothing in the plan; it affects only how much work the run does |
| The fault lane can have the native host to itself | Arrangement with the operator before UDM-22 | When UDM-22's step 3 runs |
| One full run can serve both this series and TDM-18 | The test series' own judgment of applicability | Whether the test series repeats the run |
| The premise of served-result reuse is settled (DA-075) | Decided in UDM-15 | Whether T14 is a union row or recorded as not adopted |

## State

| Package | State |
|---|---|
| UDM-20 | Not started |
| UDM-21 | Not started |
| UDM-22 | Not started |
| UDM-23 | Not started |
