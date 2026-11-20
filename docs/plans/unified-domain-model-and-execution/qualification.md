# Qualification: the union restated, the book-run diagnosis, and the final runs

**Status:** In progress. Retained diagnosis and bounded native controls are recorded.
**Created:** 2026-11-19.

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
retry of the native composition fixture, `82ba77a0…`, was interrupted by the operator.

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

<a id="continuation-compatibility-amendment"></a>

## Approved continuation amendment · 2026-11-20

**Accepted target.** The operator approved
[ADR-0141](../../adr/0141-serving-continuation-and-reuse.md). This amendment governs the
remaining qualification. Historical failures and receipts below retain their original scope.
T4 now requires correct fresh-process continuation and resource replay after current native
authorization, including empty/evicted caches, independent rows/order/byte bounds and refusal
of wrong scope, revocation and changed installation. T14 retains two independently authorized
entity reads, equal rows and distinct native pins. Its one-derivation requirement is deferred.
D2 and D4 persistent hit targets are deferred, with reopening triggered by repeated rendering
or bounded page preparation that obstructs the operator's workflow. Their unused mechanisms
are retired. Authoring still verifies fresh native rendering, manifests, predecessors and exact
frozen-catalog parity. T20 covers applicable process cache races and acknowledged production
recovery. Durable PDF/checkpoint/draft reuse and T18–T22 producer recovery remain required.
An incomplete determining proof remains partial and cannot prevent safe continuation under the
managed installation contract. Final qualification follows delivery of this amendment.

**Tested, 2026-11-20 UTC.** The installed native demand reader replayed the expected
second row in a fresh process after current authorization. An incompatible installed
identity, a foreign project and revoked support each refused before body acquisition
or row derivation. Private `ci test` demand selector `d7710e99033d44edaf07c985afe1ec2d`.
The two-process offline native authoring case passed and matched all 620 frozen N38
objects. Its containing `ci test` selection failed two holder fixtures, which passed
exact retry `dbc3aa31900a4a4fb4cd561a1ad8e869`; the parity receipt is
`f3a8718e36414575be68f6414023d2f3`. These observations cover the scoped amendment
checks before final-source qualification.

**Tested, 2026-11-20 UTC.** The private successor selection passed native rich and
contribution continuation, two independently pinned entity reads, native change-impact
pagination, and the registered MCP resource and CLI contract (`4f2e3edd46704d0eb6e7839a176129dd`).
The ordinary and provider unions below establish applicability to the final head.

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
re-activation of the book. At the final head each needed output is adopted, rechecked or
regenerated from authenticated original custody according to its material basis. Intermediate
adoption would introduce more work without qualifying final source.

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
| 6 | Rich, public and serving behaviour: structural issue, dossier, gap and detached export; rich admission, reading and pagination; source revocation; refusal of an incompatible continuation; event fit, issue and score; the tool and resource journeys | `ci test`, native; `ci` export and verify | Restated: continuation validity follows the declared semantic basis. Storage-only changes may miss the cache while a compatible continuation still reads under current native authority. No receipt for the tool and resource journeys is cited in the earlier plan; they are observed here for the first time | UDM-22 |
| 7 | Graph fidelity: isolates and unresolved endpoints, parallel roles and self-loops, strongly connected components, equal-value cutoff, wrong-snapshot cursors, mapping-sensitive rooted assessment, with independently authored expectations | `ci test` | Carried (`not_run` at the earlier plan's authoring). The single support-edge meaning of UDM-07 is its subject for the support graph | UDM-22 |
| 8 | Export and detached verification keep source and prediction releases separate and exclude protected labels | `ci` export and verify; `ci test` | Carried | UDM-22 |
| 9 | Fault behaviour: writer crash, cancellation in each of three phases, quarantine, and the budget and retirement controls of the execution host | `uv run ci test --lane fault` | Carried. No fault-lane receipt has ever been recorded | UDM-22 |
| 10 | Model, compiler and identity examples with independent expectations; the reuse and change matrix (unchanged recipe, equal-content cutoff, added member, replicates) | `ci test` | Restated: the identities under test are the target's layers (**program identity**, kernel, validator per family, code, release), and release identity no longer includes generator sources (RC11) | UDM-22 |
| 11 | Source evolution: `ci model change` preview, candidate, registration and deployment; migrated callers; recovery from a partial apply | `ci model change …`; `ci test` | Restated: a candidate that changes no installed byte is not authored (UDM-11), and the preview explains generated-SQL differences (UDM-19) | UDM-22 |
| 12 | PostgreSQL realization: fresh-target installation, privileges, rollback replay against uncertain effect, once-only initialization, helper retirement | `ci test` on a private host; `ci model change` | Restated: grants derive from **program declarations** (UDM-03), programs reach installation through the typed registry (UDM-09), and the `TEMP` grant is typed (UDM-17). The earlier plan's "remaining inline authoring" is superseded by those packages and is not a union row | UDM-22 |
| 13 | Generality: an independently specified context that is not statistics runs through the same machinery | `ci test` | Carried. It doubles as the observation that a pack-extensible vocabulary accepts a second pack's members | UDM-22 |
| 14 | PDF product equivalence, tamper detection, resume and failure classification; the round-trip oracle on each kind of PDF publication | `ci test`; `ci run resume` | Carried. The 13 failures of the N13 attempt stay held as recorded | UDM-22 |
| 15 | Set-wise validity: revocation, supersession, protected closure; pinned reads; share locks; set form | `ci test`, native | Restated: every existing operation now states its claim. The 27 classified today name their families and every other existing operation declares `none`, which is what its absent family meant, so its behaviour is unchanged. Only an operation added without a claim is undetermined and receives **conservative validity** (RC05, RC14) | UDM-22 |
| 16 | The 29 originals are registered and read back byte for byte through the normal reader from canonical development | `ci db check`; `ci release check`; readback against the inventory digest | Carried. N29 readback passed in UDM-21; repeat on the final head as part of re-adoption | UDM-21, repeated on the final head at UDM-23 |
| 17 | The whole book runs to completion: 518 pages, 29 regions, a fate for every demanded family in every region, and the whole-view composition | `ci run` on the book under the stated memory policy | Restated: the run is on the series' final release, from the original, with a new demand; its pass criteria are those of UDM-23 | UDM-23, after UDM-20 |
| 18 | One demand is interrupted under control, resumed, and then repeated unchanged with no work done | `ci run`; `ci run resume` | Carried for interruption and resume, which were demonstrated on N18 and N21 and not since capture's recipe changed. Restated for the repeat, which has never been demonstrated: with the kernel component removed from the watermark (UDM-12), "no work" is judged against the new watermark | UDM-23 |
| 19 | The construction produced regionally in production agrees with the retained whole-book construction (the comparison the DDO plan names PE-S33) | `compare_retained_book_construction.py` in the evidence folder `2026-11-16_ddo-current-native` | Carried. The script requires the exact retained demand and a complete admitted population, and refuses while products are pending; UDM-23 states how it is pointed at the new demand and which disagreements the recorded recipe change predicts | UDM-23 |
| 20 | Development adoption is complete: required derived data is admitted under the head | `ci db migrate`; `ci release activate`; the book run | Restated: adopt eligible prior work, recheck it as needed, and regenerate the rest under the series' final release at the second adoption | UDM-21, UDM-23 |
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
| T4 | Actual CLI invocations in separate processes resume compatible pages after current native authorization, including empty or evicted caches. Rows, order, ordinals, diagnostics and encoded bounds match independently specified expectations. Wrong scope, revoked support, changed installation or incompatible cut refuses before data delivery. MCP resources share this contract | UDM-10 continuation amendment, UDM-14 |
| T5 | Declaring a validity family on an operation inside a test causes every guard, validator and dispatch to select that operation, with no edit to any program | UDM-05 |
| T6 | Editing one family's validator program, one of that program's callees or the family's completion guard reconfirms only work sealed under that family; work sealed under other families is not replayed | UDM-10, UDM-12 |
| T7 | A change confined to the kernel does not move the inputs watermark, so a waiting obligation whose prerequisites are unchanged is still skipped | UDM-12 |
| T8 | A vocabulary's **declared openness** governs: a member outside a closed vocabulary refuses; a member outside a vocabulary that is open with known members is accepted and reported | UDM-02 |
| T9 | One **compiled model** per identity of the model sources: every consumer observes the same one, and a changed declaration yields a new compiled model without a restart | UDM-01, UDM-13 |
| T10 | A program that calls a name absent from the typed registry is refused at generation | UDM-09 |
| T11 | Refusal at generation or preparation occurs only for internal inconsistency (a field outside the declaration, a member outside a closed vocabulary, a self-contradictory or unmet family claim, a dangling name) and for omissions in the integrity layer (a grant, guard, role, support-edge kind or privileged-effect owner). An undetermined declaration or an unknown term of an open vocabulary never refuses | UDM-03, UDM-07 |
| T12 | A long-lived process notices on its next use that the active generation changed, without being told | UDM-13 |
| T13 | Immutable release content is not hashed again at each acquisition; an explicit verification command detects a tampered archive | UDM-12 |
| T14 | Two fresh authorized acquisitions of an immutable admitted entity return equal eligible rows with distinct current native pins. Wrong scope or revoked support refuses before data delivery. Reusing one derivation across those acquisitions is deferred as an efficiency target | UDM-15 |
| T15 | A source demand under a release uses that release's archived slices after the working tree's copy changes | UDM-18 |
| T16 | Timestamps in analytical exports are labelled UTC whatever the machine's zone | UDM-16 |
| T17 | Nothing imports the earlier model, and neither retired migration tree exists | UDM-04, UDM-19 |
| T18 | Independently expected producer fates for nonmaterial edits, equal-content cutoff, one changed region, material recipe/input/contract changes, a newly applicable or changed validator, revoked support and intentional replicates | UDM-05/07, UDM-10/12, UDM-16/18 |
| T19 | Pre-retention rollback, crash after acknowledgment and unknown commit each follow their owning recovery route. Exact draft or PDF contributor evidence survives eligible adoption; stale writers, tampering and incompatible bases refuse. Concurrent consumers settle one result | UDM-25 |
| T20 | Applicable process cache races and eviction preserve read semantics. A valid continuation can rederive after eviction. Process exit and pruning leave acknowledged production drafts and PDF checkpoints recoverable | UDM-10, UDM-13, UDM-25 |
| T21 | Passive preview and exact managed retry preserve target, effective policy, and original selection. Bounded, attributed progress, typed model impact and opt-in local reuse explanations agree across terminal and JSON. Explanations attribute unknowns and dependency paths to the owning operation. Watch exit has no effect on the run | UDM-26 |
| T22 | Exact local stop, stale or unverified identity refusal, demand detach with surviving shared interest, nested uncertainty and independently verified retirement | UDM-27 |

The book does not exercise T1. Every operation of the book pipeline (capture, organization,
discovery, sentence, formal, math, linguistic, construction and composition work) declares
`none` or names its families, so the book runs under the same generic validity as today, unless
the operator chooses to mark an operation undetermined. Whether the conservative path fits inside
settlement, whose lock timeout is five seconds and which is the phase where the last book run
failed, is settled by UDM-06's bounded observation on the stage before revision A is frozen, and
so before either final run.

**Tested, 2026-11-20 UTC.** The N36 stage scalar fixture emitted
`validity_undetermined`, appeared under native conservative validity, published
the expected integer and produced zero receipts on unchanged repeat. The private
native publication retry passed as well. [T1 evidence](../../design_review/evidence/2026-11-20_udm06-conservative-validity/README.md)

<a id="code-closure-qualification"></a>

### Code closure and real reuse qualification

**Planned amendment · 2026-11-19.** This section consumes the
[code dependency closure review](../../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md)
at commit `1982a20c3`. The review's fixtures establish bounded analyzer behavior. Actual
production reuse remains open under the [UDM-10 follow-up](programs-identity-and-revisions.md#udm-10-code-closure)
and UDM-14/15. The 33 reported source locations are shared by the four captured roots.
Coverage must follow each supported workload, including newly exposed unknowns, and account for
every original site through the identity owner's resolution or justified exclusion.

**Native authoring acceptance.** D2 hit-count qualification is deferred. Run fresh installed
`ci schema native-candidate` with unavailable database endpoints, exact captured inputs and the
frozen predecessor. Require correct program/manifest rendering and frozen-catalog parity through
`no_native_change`. Preserve wrong-model, manifest, predecessor, SQL verification and ordinary
authorization controls. A source repair that changes installed bytes follows normal stage revision
and release proof before final qualification.

**T4 acceptance.** Exercise installed `ci query` demand/rich commands and `ci contributions list`,
with the next page in a fresh process and an empty cache. Require current native authorization,
the exact cut/support/root/selection, independently expected ordered rows, valid ordinal and
encoded bounds. Repeat after process cache eviction. Wrong scope, revoked support, changed
installation, changed model or incompatible cut refuses before data delivery. Exercise shared
MCP resources and change-impact through their actual entry points. A partial code analysis can
withhold cache eligibility while the conservative installation contract permits continuation.
Rebuilding bounded row populations is valid. Persistent page hit counts are deferred.

**T14 fixture and acceptance.** Keep the committed authored-publication setup and two fresh
independently authorized reads of an immutable admitted entity. Require equal eligible rows and
distinct current native pins. Wrong scope or revoked support refuses before data delivery. The
one-derivation assertion is deferred. All earlier strict reuse failures remain in their original
receipts and are historical evidence for the superseded acceptance.

**Historical strict reuse evidence under the earlier contract, 2026-11-19 onward.**
These observations retain their original scope. The continuation amendment above owns current acceptance.

**2026-11-19 implementation evidence.** The authored fixture reached native release admission
in one attempt and refused unchecked required semantics. The existing publication recipe route
then stopped on conflicting captured Python modules. The private smoke and strict T14 journey
remain opt-in with `CORPUS_RUN_UDM_T14=1` while those prerequisites are open. Restore the actual
T14 identity to the ordinary required final-source selection once it is viable. The opt-in
setting carries no qualification credit. [Receipts](../../design_review/evidence/2026-11-19_udm-workload-custody/README.md)

**2026-11-19 boundary work.** The D2 acceptance test exercises the installed candidate command
twice with unavailable endpoints and counts renderer and artifact hydration calls in the
actual processes. Its strict selection (`CORPUS_RUN_UDM_D2=1`) recorded one render and zero
hydrations in each process (`dc7ef9b998e94d898dc29fcb6055834a`). Both processes established
`no_native_change` across 617 N34 objects (`6e4b639078b54a43b20e901380a303ba`,
`a29477039b5649b7a8d75243683e1577`). The latest strict rerun reproduced the same counts and
native parity (`2979355692bf407e83e067d70505d8aa`, candidate receipts
`899834aedbd448d18be78b67fd016418` and `783fc7f564ac4eeba9cfa6b6e0690dab`). The shared custody
and cache controls passed 128 selected identities, then 133 with prepared correspondence and
cache-publication controls
(`72920dbda42e40a09af3355eca8e5267`, `62c7d552a88048769497b046e12c872f`). D2 still needs
complete determining initialization and library custody. Serving now passes the captured
model's Decimal bound into the pure value codec and uses finite cursor and page envelope
policies. These changes passed 292 targeted controls (`6dc85d72a8864eb6b5013c37148d90fa`).
The six page consumers now pass an immutable refusal projection from acquisition into
pagination. The refusal and hidden handles remain part of exact byte accounting. An
independent exact-bound control passed (`183e45cfdd864fcebabdc97dcbefde4c`).
**Tested and interface-checked, 2026-11-20 UTC.** Finite authenticated codec
acquisition closed native demand's eager imports. Its actual callable slice
still has 127 required facts, including row-source provenance and the operations
on values and containers used in pagination. Rich and contribution retain eager
requirements in model preparation, typed validation and index or graph
reconstruction. [Installed workload diagnostics](../../design_review/evidence/2026-11-20_udm10-workload-custody/README.md)

The strict D2 check now derives the predecessor and independent object count
from the frozen state. On N36 both offline processes returned
`no_native_change` for 620 objects. Both rendered and neither hydrated
(`937bc65220fc4409ad917fdb58d9d29e`). The actual N37 repetition also matched
620 objects while both invocations rendered and neither hydrated
(`b5b7e6980a13441fac4861000fb5c456`). D2 remains open.

The direct entity witness calculation is a declared rich workload root and the acquired
body retains its native tagged encoding into derivation. An eligible hit must preserve
diagnostics, continuation interpretation and byte accounting.

The authored entity recipe now merges equal captures under canonical logical member names,
retaining acquired origins separately. The private smoke advanced past the merge and reached
prepared execution (`fc8658e5d8f144a488f6d6d366509882`). That attempt exposed use of an archive
member name as a live factory path. Prepared execution now uses the acquired runtime location
map and verifies the declared required sources at that location. The next attempt reached
native completion and refused the unapproved rich-admission effect (`a512912cf7b14aca95d379f526e5ae6d`).
The fixture now admits `rich.admit` through the exact released effect grant. Native publication
and read passed on the private target (`afbb02c6446445f7bd63aad0704dedb0`). The smoke rerun with
the exact tagged rich-body boundary also passed (`f41efa461e9a468d9fdeed434e0372cf`). The
continuation harness covers demand, rich and contribution CLI invocations and shares the
subprocess observer with T14. The private N37 strict run
(`22e9264223d5421a926100019a598578`) returned a fresh native-demand page with
`incomplete_code_identity` and no continuation. The authored-entity case derived again
in its second fresh process. Those two cases failed their reuse assertions. Strict rich
and contribution continuations remain `not_run` for this increment.
[Readiness evidence](../../design_review/evidence/2026-11-20_udm-closure-provider-readiness/README.md)

**2026-11-20 typed boundary integration.** The native-demand reader admits the generated demand
records with strict validation and preserves exact recursive values and original tagged member
bodies. Rich frontier acquisition uses the same validator, then passes an owned witness to the
query. The prepared rich indexes copy query-local state explicitly, and contribution derivation
uses a typed selection. The native renderer builds its physical model privately from captured
inputs on a miss. The renderer's source bindings cover the actual composition and PDF selection.
The installed source scan still finds required determinants in all four workloads. The strict
private demand run against the pre-change N37 kernel stopped during setup because the compiled
release required the changed kernel (`11124e3760124d2099ec92cbe20b5b3c`). The fixture stopped before
it could exercise continuation. The successor migration supplies the required kernel.

**Tested, 2026-11-20 UTC.** The guarded stage migration verified N38. Both strict D2 processes
reported `no_native_change` for all 620 N38 objects with unavailable database endpoints.
Each rendered once and hydrated zero entries, so D2 still failed (`e3ebe5d11b1b411cb16d5200f0ef7f1e`).
The stage migration and the strict D2 parity observations establish their respective native
boundaries. Complete renderer custody remains the prerequisite for persistent reuse.

**Tested, 2026-11-20 UTC.** The three strict T4 variants reached fresh authorized pages on
private N38. Native demand withheld continuation at recursive JSON encoding ownership.
Rich and contributions withheld continuation at required initialization facts, first
attributed to the `json` import in `core.canonical`. All three failed their reuse assertion
(`8c30e7bd5a7742f4a4e6c6429ef99740`). The strict direct entity T14 read reached both requests and
the second derived again (`24f0726e0fdf4e22bdb0622b105e1ab8`). The additional PDF-backed fixture
in the T4 campaign failed setup at its live source root. Its callers now explicitly select
the package source directory for application-only captures. The mixed publication fixture
retry exposed a captured evaluator module under the test tree (`91bab099beb649d39af6a8337c0e931e`).
Those mixed journeys use the existing fixture executor that verifies and maps each captured
module to its actual source. Both earlier failures remain in their managed receipts.
The next retry reached native publication and exposed a missing exact `rich.admit` grant in
the broader fixture (`93f34428c3d24739ba3135173968c61c`). Both publication fixtures now declare
that grant through their shared recipe. The fixture uses normal release admission and checks
the released operation definition on clone readback.
The private N38 publication control then passed (`1319925a435841b48ead42d88c2dbeb6`).
It verified the authored entity qualifications and replay with zero new receipts. Cross-process
serving reuse remains open under T4 and T14.

**Implemented and scoped Tested, 2026-11-20 UTC.** Native demand and rich frontier
consume recursively detached snapshots. The renderer now authenticates its finite native
codec profiles. Strict D2 still rendered in both processes with zero hydrations and
verified parity across all 620 frozen N38 objects (`b825ca9e4cb64f1f8489146c7a8b19bd`).
Private strict T4 again withheld all three continuations, and T14 derived the second
entity acquisition (`9e29dff341a04b8ab1d3143a482ac59e`).
The working source subsequently added the snapshot preparers to their installed
workload roots. The current native-demand scan reaches the actual generated TypedDict
and Pydantic validator initialization. These are determining effects alongside the
recursive codec and pagination work. The current demand adapter inspection found finite
Pydantic core schema nodes and 69 generated TypedDict class references. Authentication
of the compiled validator and its actual bindings is still required.
Rich and contribution still require graph and validator custody.
Offline `ci schema native-candidate` on `b3c4256e3` returned `no_native_change`
for all 620 N38 objects (`ecb1a9a1842b43a985d5c79c75abd323`).
Real provider inventory collection selected 24 identities
(`5c35b6bdb4b949f0b075bb8e0cf6256e`), with functional outcome `not_run`.
The updated identity, decoder, row storage and reader selection passed all 237
controls (`580ce7aab0754bc89f9ef165591a738f`). Pyrefly and Ruff passed through
`ci check` (`2b80e8c80cba4f28af28e607e6bd0506` and
`89290ab123cd45cfbb09599f78016d25`).

**Tested, 2026-11-20 UTC.** The captured native schema validator matched the
generated adapter on the native fixture and the shape refusals. The rich reader
and contribution checks passed with explicit captured numeric policy
(`0f75123c745b43b2bf2323c806c3bd2a`). The settled offline candidate reported
`no_native_change` for all 620 N38 objects (`ad5aed17cce94e1ba1894947a794a7a7`).
The final schema and reader selection passed all 62 controls
(`f87f9c206b1d41a6a5e12ca2a9153b12`), including refusal of in-place changes to
numeric material. The broader selection recorded a stale compiler-version assertion
and the strict D2 skip (`e1d92b1303a7494f900de357b1725426`). The guard assertion
now checks the current ABI, and passed in the focused retry
(`ebc2047c3d684c60a0d3717d61931701`). Pyrefly passed
(`e6bd203264eb49609121c9dce2a33908`).
The installed-root scan still reported required generated-module initialization
for demand, graph and validator initialization for rich and contribution, and
compiler and model initialization for the renderer. The strict reuse journeys
remain open, and final qualification and adoption remain `not_run`.

The focused serving and CLI controls passed 233 selected identities
(`53e183166ea54effa89e64324c14fcda`). The final tagged-body and custody selection passed 30
(`26d3c234872c4457b302b1966eb54588`). The catalog privilege regression exercises the full
`ci release check --native-proof` route required by UDM-12. It passed on private N34, including
refusal with the altered ACL and successful proof after restoration (`ff6745d56dcd4e3c9ac23ae72f7234c2`).

**Shared negative controls.** Include eager initialization, relative aliases and re-exports,
rebound import names, runtime guards versus type-only imports, indirect loads, receiver dispatch,
annotation evaluation, copied provenance and authenticated dynamic operations. Expectations
come from authored inputs and independently specified effects. A successful inference alone
cannot establish imported-code custody. A missing serving context cannot grant production
reuse. Retain targeted codec, corruption, publication and prune controls alongside these actual
entry-point journeys. Their final-source identities join UDM-22's existing selection.

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
reproduced at bounded scale* (with the largest scale tried). New bounded reproductions run on
explicitly acquired owned stage: `18/corpus`, port `5434`, database
`corpus_structure_ddo_stage`, OID `130661481`, recording its actual accepted native head rather
than assuming the historical N29 baseline. They do not mutate canonical development or start a
whole-book run. The original book receipt belongs to canonical OID `131763263`; reading stage
cannot establish that original intent's standing.

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
Before anything else, hold and retain run `1dd5d45ded4b4ea38399fb121a44d28c`, discovery refusal
`3fed447a2a5649538c80ac05c1ed7c47`, and interrupted fixture retry
`82ba77a0731148faa0bd827ead1373cb`. Use `ci evidence retain` and record original outcomes. Read three facts from them and
from stage: which nine regions timed out and how large each was (pages, sentence occurrences,
completion payload size); what the "nested physical-join uncertainty" in the settled result
refers to, by reading the classification that N29 added for nested uncertainty in execution error
groups; and the state of the one unresolved completion intent. If the records have already
expired, the package says so and proceeds with the existing scoped evidence and bounded controls.

<a id="retained-book-diagnosis"></a>

### Retained diagnosis and bounded control state — 2026-11-19

**Partial.** Preservation, the historical failure-boundary diagnosis and the native binding
repair are verified. Actual regional workload and final composition confirmation remain open. The
[retained diagnosis](../../design_review/evidence/2026-11-19_udm20-retained-diagnosis/README.md)
and record `udm20.retained-diagnosis` distinguish recorded facts from unavailable current
standing. The rest of this package's reproduction and instrumentation protocol remains work to
perform, not an account of measurements already taken.

The [N35 audit closure](../../design_review/evidence/2026-11-19_udm-audit-closure/README.md)
establishes fresh selected-source export, native completion recovery and compatible PDF checkpoint
uptake in the bounded private controls. N35 activated on the bounded stage at generation 32
with exact retained identity and selected demand readback. Regional confirmation still owns
actual resume, unchanged repeat, and timing on the selected workload.

The three originals still exist, are held with no expiry, and their retained artifacts match
the managed bytes: book run `1dd5d45ded4b4ea38399fb121a44d28c` is `failed` with cleanup
`established`; discovery fixture `3fed447a2a5649538c80ac05c1ed7c47` is `failed`; retry
`82ba77a0731148faa0bd827ead1373cb` is `interrupted` with its private children settled. Their
original outcomes are preserved. The sealed book journal is now retained with its exact
manifest hash, in addition to the already-retained native result.

**Measured from retained operational observations, reread 2026-11-19.** Nine producer attempts
reported SQLSTATE `57014`, explicitly a statement timeout, while retaining the completion
intent. Their server contexts name `canonical_json`, `ddo_digest`, the intent insertion and its
validation seal. A completed serialized answer had reached this call; the failed statement did
not add a committed intake. This establishes the failure boundary more strongly than the old
narration, but does not establish that no earlier intent or other durable producer copy existed.
It supplies neither per-statement duration/cost attribution nor a post-repair margin against
the recorded 120-second policy. No unknown network commit is proved by a server statement
cancellation.

The journal also records 23 exact-release reconstruction refusals, seven runtime-slice drift
refusals and one positioned-construction source refusal. Its 40 individually recorded
failures do not expose all 41 sub-exceptions named by the aggregate: nested group detail is
explicitly omitted. The narrated nested physical-join uncertainty therefore remains
unclassified from these artifacts. The native artifact is explicitly `last-pinned`: it has 58
receipt acknowledgments, a complete 29-member discovery population and 20 committed intent
inspections, with no noncommitted inspection. It does not identify the narrated unresolved
intent or provide a fresh final-state census. Only four of the nine failed region scopes can
be joined to that snapshot; all nine task/request/obligation identities are preserved in the
diagnosis, with missing extents, sentence counts and exact payload bytes left unknown.

The original composition fixture failed at discovery closure with `population lacks admitted
declared discovery output`. Its interrupted retry produced no completed call report, so it
does not establish successful final fan-in. **Tested** replacement controls establish narrower
properties:

- The recorded N31 stage observation `949abc3179834a57aea9598b7da470b9` passed its explicit
  owned-stage OID, port, revision and source-custody assertions and the current-use discovery
  reuse/refusal controls. Private current-native receipt `fac1de3a567d40999ee4c0d8e0b2ccdf`
  establishes selective changed-member computation, unchanged child episodes, an actual
  aggregate of 16, and preservation of historical/current support scope. These close the
  discovery/selection cases they exercise, not the original full-view compositor or its
  withheld-region and scaling obligations.
- Private native recovery `bd79f9aa68bf4915a7df0d1aa9e7b360` establishes ACK survival through
  explicit retain rollback, generic cross-generation consume/publication with original
  producer and current adopter, exact replay, and refusal of stale or lease-only takeover.
  Its genuine PDF contributor transfer is cross-build/later-attempt within one task;
  cross-generation PDF publication is not established by that case.
- Private native recovery `fdd3cb361f0f406690339d723151e630` establishes that, after consume
  commits and private ACK/body are removed, a new claim reconciles the mapped retained intent,
  refuses replacement computation and publishes the original once. No unknown-network-commit
  fault was injected, and neither recovery receipt reproduces the original book failures.

These controls establish a durable answer/intent boundary before later settlement failure.
They do not establish cheaper validation or book-scale completion. Exact retirement proof is
still required for transfer; a database outage preventing that proof leaves private bytes
preserved and transfer refused. See the diagnosis for durable receipt links and the
[recovery owner](operation-reuse-and-recovery.md#udm-25) for implementation and acceptance scope.

**Tested, 2026-11-19, canonical readback.** All nine timed-out sentence tasks were joined to
their retained scopes and each had zero retained intents and no live lease. The separate
unpublished formal-evidence intent was reconciled exactly. Native publication preserved task
24 attempt 1 as the original producer. [Canonical readback](../../design_review/evidence/2026-11-19_udm20-21-canonical/README.md)

**Tested and Measured, 2026-11-19, N35 stage.** The application principals have zero configured
session statement and lock deadlines. Binding now installs a finite transaction-local deadline
and preserves a stricter caller deadline. Independent required roles now select each population
before checking cardinality and coverage. The actual stage probe for eight independent roles
with 2, 4 and 8 rows per role took 5.063 ms, 982.714 ms and more than 30 s before the change.
Afterward the plans executed in 0.840 ms, 0.737 ms and 0.754 ms and retained all 16, 32 and 64
role occurrences. Withholding one role preserved the seven peers and reported the missing
cardinality. The experiment used required roles. The organized compositor uses optional
alternatives and has its own workload acceptance. The 88 native binding,
deadline and claim controls passed together (`d661ac29d9b049288ca16ced6f671936`), including
exact epoch custody, revocation fencing and lost acknowledgment recovery. [Stage evidence](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/README.md)

**Tested and Measured, 2026-11-19, regional workload.** The 28-page successful control
completed with actual Docling and spaCy on the frozen N35 Standard application
(`4933fc555e14453394770dbdbccf4007`). Its two manifests retained 676 sentences and
8,918 tokens. Its larger sentence completion payload was
35,127,356 bytes as JSONB text. One publication took 66.266 seconds with no lock wait.
Nested plans recorded normalization and body identity work. Earlier attempts preserved
their committed capture, organization and discovery, and refused mismatched source or
runtime custody. The later spaCy transport refresh preserved the release and inference
identity. Capture still received a separate producer request under the refreshed runtime
because the incomplete PDF lowering identity requires demand-scoped execution.

**Tested and Measured, 2026-11-19, canonicalization candidate.** A generated temporary
routine on N35 produced the same 21,875,525 output bytes and SHA-256 for the exact retained
23,241,498-byte JSONB body. The paired size-and-digest projection took 2.67 seconds with the
generated routine and 32.96 seconds with the installed recursive routine in the preceding
probe. The routines' native escaped-text, Unicode, numeric and nested-object controls passed
(`c5ee75b900da4bf09ff7cc8cf475b551`). Object-free arrays use JSONB scalar formatting and
quote-preserving whitespace compaction. Object-bearing values retain ordered key traversal.
The typed generator uses PostgreSQL `jsonb_path_exists` in strict mode and
`regexp_replace` to preserve complete quoted strings.
[SQL/JSON paths](https://www.postgresql.org/docs/18/functions-json.html)
· [POSIX replacement](https://www.postgresql.org/docs/18/functions-matching.html)

The offline delta changes `data.canonical_json(jsonb)` and its generated descriptors.
[Emitted routine readback](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/candidate-canonical-json.json)

The 66-page control reproduced SQLSTATE `57014` at the original 120-second retention
bound after actual capture and spaCy. The cancellation occurred while assigning the intent
digest in `retain_data_completion_intent`. Cleanup settled and the exact 92,292,593-byte
completion draft remains acknowledged. N36's guarded deployment on stage passed
(`ee47785f8326495ba80c5e5e7a391311`). The candidate changed one routine and two descriptors.
[Deployment readback](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/n36-stage-readback.json)

The first exact `ci run resume --result` on N36 (`8c64955052214e73b71827fa48132f78`)
reached the original demand and refused its stale release facts before claiming work.
The same draft bytes remain in custody. The accepted kernel boundary requires preparation
of an application for N36, followed by current input and material-compatibility checks
before consuming the original draft.

**Measured, 2026-11-19, actual N36 intake digest.** The installed routine computed
the digest at the N35 cancellation site in 15.26 seconds on the exact acknowledged
92,292,593-byte request. The read-only probe used the retained producer fence and
completion and establishes the time of the digest step. The new application has
different material definition facts and the original answer is attempt-scoped.
The native draft admission guard requires the original task, attempt and claim for
that basis. The acknowledged draft remains held.
[Intake timing](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/n36-retained-intake-digest.json)
· [Material comparison](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/n36-old-draft-material-comparison.json)

**Tested, 2026-11-19, prepared source correspondence.** A fresh N36 full-family
request (`e081ef271b3942b983586e220fbc34d1`) failed before capture or inference.
During eager port acquisition, the canonical sentence port checked the loaded
`project_product_members` callable against its original source subset. The
canonical execution-custody artifact retained its bytes, but the explicit subset
omitted the callable's module. The canonical source collection now includes the
module and authenticates the original callable through the existing guard.
All 18 sentence and prepared product correspondence controls passed on the
repaired source, including shared CPU execution and actual CUDA spaCy
(`297b66ec2c2345df93c79fdfbb3d3e2e`).
Offline candidate comparison reproduced all 620 installed N36 objects
(`a6711853e6024c48bb55da8b8ff24348`).

A read-only preflight acquired each of the 11 selected ports individually from
the first N36 application. Nine passed. Canonical sentence projection and HanLP
failed their original source-subset checks. HanLP's subset now includes the
declaring modules for its native-head selector, dependency graph and constituency
projection. The 19 HanLP and primary-operation controls passed, including actual
CUDA inference and the independent native-head expectations
(`fdfe4d14f4334393b86492bae8cae3ae`). The offline comparison still reported
no change across all 620 installed objects (`6354c2b504c945c6950005120b70a6ee`).
The repaired frozen N36 application admitted all 11 prepared ports in the
same read-only preflight on 2026-11-19.
[Selected-port readback](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/n36-selected-port-preflight.json)

**Tested, 2026-11-19, complete-family composition.** The one-page Standard
application on N36 passed through `ci run` (`bc94c35adc3e438b8e4eb771d4ccb155`).
A fresh native readback found all 11 obligations fulfilled, including canonical
sentences, HanLP, contextual evaluation and the organized full-family compositor.
The bounded run took 381.88 seconds across startup, inference and settlement.
The live `ci results watch` over the exact stage observed the active demand
and exited while execution continued. Its interim snapshot recorded
`not-applicable` for the compositor with five `binding-covers` reasons while
upstream families were pending. The compositor fulfilled once they were available.
Diagnostic role settings were restored.
[Live CLI readback](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/n36-full-family-live-watch.json)

The private PostgreSQL two-region control now publishes capture and discovery
inside one demand and stops after the two source sweeps. It carries the exact
capture runtime custody while the analytical families remain pending. Its
selected population contains two regions, and native composition records
`not-applicable` with `binding-covers` reasons only. The exact
`ci test retry` passed (`93ea314121b5436c8820d0856460020f`). The original path,
runtime custody and duplicate fixture artifact failures remain in the managed
chain (`6344becd690648acb612ffcf7e2543e3`, `62ea8781ecf64203bddb7a749e4660c8`,
`d40a868e77104636ba747359600af638`). The private fixture establishes native
binding against independently authored regions.

**Tested, 2026-11-19, 60-page regional contrast.** A separate excerpt from the
historical failed region with the most source records passed on the corrected N36
application (`f3bb4c777c2d42aa8acc0b8567e8b44b`). All five native obligations fulfilled,
including two regional sentence products. The complete demand took 755.96 seconds.
Its two manifests retain 1,924 sentences, 23,013 tokens and 1,128 annotation blocks.
The largest completion intent was 91,103,526 bytes as JSONB text. PostgreSQL logged
60.62 seconds for the large intake and 85.03 seconds for publication. Publication
finished 34.97 seconds inside the unchanged 120-second statement bound.
Cleanup settled, no leases remained and the diagnostic settings were restored.
[Member census and settlement timing](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/README.md)

**Tested, 2026-11-20 UTC, fresh 66-page repeat on N36.** The operator chose a
fresh run for the same registered original. The N35 demand was cancelled
(`f9af833c148a4e14a03c63699bcf1711`). The exact draft retirement check
returned `retained` with reason `unpublished` (`330a1288ee1d43099a871a9f51548c8e`).
The replacement uses the same selected original, sentence target and execution
policy with the corrected N36 release and runtime. The run passed in 801.50
seconds and a fresh native read confirmed all five publications, including both
regional sentence products. Managed cleanup was established.
[Replacement run](../../design_review/evidence/2026-11-20_cli-f00e167923f74c0d837b60f6bd1cc6e0/README.md)

**Tested, 2026-11-20 UTC, actual withheld-region stage compositor.** The N36
demand acquired two named regions from an independently authored original.
One exact sentence claim was held before physical submission. The sibling
region published its sentence and downstream products. Native binding took
2.51 seconds and the compositor returned only `binding-covers` while the
other region was pending. After releasing the held claim through native
attempt failure, execution resumed the same demand, published seven new
receipts and fulfilled all 18 obligations. [Withheld-region evidence](../../design_review/evidence/2026-11-20_udm20-live-withheld/README.md)

**Early diagnosis and later confirmation.** In the regional reproduction record the last durable
boundary for the timed-out attempts. Inspect the exact native intent and publication standing
after rollback or acknowledgment loss, and identify the output that existed only in its producer.
Use bounded failure injection to compare a short independently committing intake and the private
spool when one of them cannot survive the relevant failure. Supply that result to
[UDM-25](operation-reuse-and-recovery.md#udm-25) before the transition freezes. Reproduce the
equivalent-discovery attachment/closure mismatch with the existing two-region fixture and route its
current-use proof to UDM-05/07 before freezing its revision. This early slice can use UDM-26's
passive reports when available. Later, confirm the bounded controls after the relevant fixes are
deployed on stage. UDM-21 consumes the early diagnosis; UDM-22/23 consume stage confirmation.

**Reproduction 1: settlement at the 120-second limit.** The smallest scope is one region. The
package takes the largest of the nine regions that timed out, as an excerpt of the book's
original registered in the stage project (or by whatever narrower scoping of a demand the product
offers, chosen at entry), and runs the sentence work for that region alone on the recorded
current stage head. Historical N29 comparisons use preserved evidence or an explicitly isolated
test context, without downgrading stage. For contrast it
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

**Prerequisites.** None for preservation and diagnosis. Confirmation needs the owning fixes and
their stage deployment. Diagnosis supplies input to those packages before confirmation.

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

**Tested, 2026-11-19.** Version-matched canonical checks and the authenticated reader verified
all 29 originals and 28 local paths. Exact replay settled the one pending formal-evidence
intent and an independent census found no live book leases. Compare-and-set activation
advanced the book to N29 at generation 5. [First adoption](../../design_review/evidence/2026-11-19_udm20-21-canonical/README.md)

**Tested, 2026-11-19.** The cold Integrated run on N35 and its matching application source
at `22935afbf` completed two actual Nemotron requests and five native publications for one
physical page (`31b3a333ee6043a4bc2df36b6e04b529`). The launcher completed sleep and wake.
The generation response and awake state matched before and after the invocation. This closes
the bounded Integrated check. [Stage receipt and provider readback](../../design_review/evidence/2026-11-19_udm21-integrated-stage/README.md)

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

**What must be regenerated, and when.** Inventory retained work without starting the book at
N29. The N23/N29 recorded capture, organization, discovery and construction recipe changes
are candidates for material comparison under UDM-10. The sentence and formal-evidence recipes
match, but the resolved inputs, current support and eligible use still determine adoption.
Encoder vectors are regenerated under the current numerical policy; the old vectors lack a current
reader. Keep the current inadmissible and changed-recipe results distinct from the equivalent
discovery fixture. UDM-23 records a final-head census and does the fresh work that remains.

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

### First campaign and completion guard repair

**Tested, 2026-11-20 UTC.** The first unnarrowed `ci test --workers 12` campaign
`cf42805e194d4af7b9169db8ee3d993a` found 58 ordinary failures before a supervised stop
for a native repair. Its eight exclusive fault identities passed. The concurrently selected
24 real-provider identities also stopped at this repair boundary. Eight GLiNER cases and
three E5 cases passed before the stop (`54ea347a1f214c13acb6077949ffb99e`). The explicit
GLiNER Base boundary diagnostic passed separately with `CORPUS_GLINER_DIAGNOSTIC=1`
(`c4de9043fbd74920a77f39371b9f66de`). Earlier-source observations retain their original scope.

The actual grade, empty-carrier and rich-admission journeys exposed the same native failure.
The shared completion scope function interpreted ordinary `question` roles as event frame
selectors before it checked validity family. The generated repair checks the admitted
`operation-event` family first. The preview and rollback-only candidate changed one function
and two descriptors, with zero physical and privilege changes (`ce58bdc31cf240cab5119ab52cb13558`,
`055805a98f9247d09617ab572eb58608`). Registration `7b1cc70f8cb348ffbb0e11b88640fdd1` froze
N39. Guarded deployment `66e3db21b43f4a8b90f759276a784e1b` advanced stage OID 130661481 from
N38 to N39. Canonical adoption follows final qualification.

The same campaign exposed stale fixtures. Repairs preserve the current custody and authority
checks for regeneration, math, PDF, in-transaction source acquisition, admitted rule input,
predicate selectors, GLiNER loader binding, PM2 restart behavior, and inline input
correspondence. The historic local-semantic pgTAP family calls `data.local_semantic_case_matches`,
retired by DDO at `d6ee43480`. Its 19 cases move together when accounting for the failed campaign.
The older M1 PDF preflight depends on retired `ops.run` storage. The superseded SQL test family
and uncalled PDF preflight are retired along with their mechanism-specific fixtures. Their failed
receipts remain available. Current independent source ownership and wrong-original controls cover
the declared-source route.

### Historical authorization and stage provider readback

**Tested, 2026-11-20 UTC.** `ci ingest --source-root "$PWD/python/corpus-structure/src"`
ran a new physical-page excerpt on the N39 stage. Nemotron completed two actual requests,
five native receipts published, and the generation document and launcher sleep state matched
before and after (`29e657d7566648dfac3e2e795ded68bf`). The first invocation used the repository
root, refused source acquisition before inference, and restored the launcher
(`8df1fc11db1d4f3788fca7e751a0b392`). Stage release
`release:ceae8abb899786942fe1e47dcf08e380d5a95671564fe723d135646d8c74dab2` passed `ci db check`
and `ci release check --native-proof` on OID 130661481 after deployment
`4329fc1c4b804c32a757af2d84d89272`.

The N39 private retries passed the generated event family and empty-carrier cases. The grade and
fit journey passed after its fixture admitted the exact independent policy effect. Rich admission
as a writer then exposed historical revalidation requiring the original evaluator's purpose from
the current consumer (`e70832fe6a474a19a7862445c924d0d8`, recovered). The generated correction uses
the admitted release grant and actual receipt linkage for material correspondence. Live retain,
draft adoption, publication and publication replay still enforce current effect authority.

The three operation-event cases repeated native source production in parallel and reached the
15-minute watchdog in SQL claim, read or retain calls (`4b6cff104db5461dbc50c51b89691e10`). They
now share one module-scoped preparation, with a distinct source and report for the counterfeit
test. The watchdog stays at its existing bound. Native event qualification remains open until
the shared setup and its independent assertions settle.

**Tested, 2026-11-20 UTC.** The private generated-program selection passed three controls
(`ea7f512a0c744fcfb7c1dc60367e7b24`). Historical grant verification accepted the reader and
rejected a substituted definition or effect contract. The same reader was refused by live
authorization. The combined preview `b0479b94f1e549cab38f097203f86779` identified 622 native
objects with no physical or existing privilege changes. The rollback-only candidate
`0192328720894bad89979b7d9fbb1a18` passed. Registration `4df076ebc9c14f799f6adb577becf2c2` froze
N40. Guarded deployment `816636325a2648c481a12157b0baf290` migrated stage OID 130661481 from
N39 to N40 and admitted Integrated release
`release:5dd3a504a1b0fd91f822d1e194c3be00252a0175bc395e4f53aa380d9933660d`.
`ci db check --target deployment` and `ci release check --target deployment --native-proof`
independently accepted that release on the same stage database.

### Retained fit custody and rich producer authority

**Tested, 2026-11-20 UTC.** The N40 grouped operation-event cases again reached the
15-minute watchdog, during PostgreSQL retention of the fit (`84d6a55459bf4757b84e7c0608ce2ab5`).
Source inspection found duplicate authentication of the same episode during same-release
validity. After original correspondence succeeds, the consuming bridge has no changed
validator identities to apply on the same release. N41 skips this repeat and keeps the
bridge on cross-release and distinct consuming-request paths.

N40 rich admission also reached the protected presentation check while verifying a retained
fit under its original boundary (`50757742720b4fcba376a7da64100cbc`). The N41 material path
verifies its exact selection, disclosure and historical access universes. Fresh live fit,
grade and event presentation retain current caller authorization. The current validity and
disclosure controls and the actual grade and fit journey passed on private N41
(`eec85e184dd040b1a13946c95c029761`). The event cases in that checkout stopped at the provider
environment lock check. The actual rich writer then reached a distinct failure. The shared
producer check demanded the rich validity family from the issued public evaluator policy.
N42 scopes the family requirement to rich-owned producers and retains exact output,
receipt, effect and CPU checks for all inputs.

The N41 preview `3d7ee89cfc5e4fada38a9d825550c5b5`, rollback candidate
`f21976707a8c476da650a1b73640bc42` and registration
`673d78aa8cda4606b853e63b9ac424f9` passed. Guarded deployment
`8896b915a1ae403a8143653bf4b413de` migrated stage OID 130661481 from N40 to N41 and
admitted Integrated release
`release:fb0ebd3b9d1be5cf501a932785c04b490c622d3bb4fb7e414782072cbf94bf6b`.
Both stage application checks passed. Two fresh offline renders matched 624 frozen
objects. The N42 preview `e404b3620de64a1b940374f736158bfc` stages the existing
[Standard configuration](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/n36-standard-regional-inputs.yaml)
for the book.

The N40 provider campaign selected 24 cases. It passed 23, including two-region
exact resume, PDF spool recovery, combined provider execution, Lark-backed parsing,
and DiPO and D1 custody. One M1 case used a logical archive path as the physical
module path (`1e0a55beca9b43e3be696f74eb6f422a`). The fixture now uses the shared captured-source
executor. The exact retry and the final-source campaign are pending.

**Tested, 2026-11-20 UTC.** N42 retired the earlier internal rich producer signature and
registered the explicit family-aware signature (`b0c6d1035ed34caeb94ec598577840c0`).
The rollback-only candidate `5191bfad6b504224a099ae05b63cd560` and guarded Standard deployment
`5cb34f8319ca4c71aaa504eccda86df1` passed. `ci db check --target deployment` and
`ci release check --target deployment --native-proof` independently verified stage OID
130661481 and release
`release:0c8c3c797e70c30ee2c9125642a512feee29f18c7703354d8b4e4fa503374dc1`.
Two fresh renders matched all 624 frozen objects.

All 18 rich native controls passed (`f1e49e25216340e0a46fb638f9ecc9fb`). The controlled
definitions now carry current validity and parameter fields. The actual rich-admission
journey also passed on N42 (`a145dbfebc9f4fc991ef7c511bb1cba2`), including the refused
mutations, the ordinary readback and the independent policy authority.

The M1 retry then reached a missing producer dependency in the admitted source subset
(`42a03041b83a404a838264f3104835a0`). The candidate planner is now captured as an original
source alongside its governing producer, preserving the existing callable verification.
Main reproduced the exact N42 native programs after this correction. The real GLiNER retry
published the native M1 result and reached the bounded readback. The test requested the
products of the whole upstream demand and exceeded its 8 MiB limit
(`8fefb2735f17470aaf9d8df805600379`). The readback now selects the M1 operation within
the same limit. Its final provider receipt is pending.

**Tested, 2026-11-20 UTC.** The event retry spent at least 835 seconds preparing the
sources, structural products and disclosure controls, then hit the existing 900-second
watchdog while reading support for the event frame (`8f33fea76bfa47ca9c1ca874ea151412`).
Frame preparation now shares one authenticated support index across identical cuts in one
transaction and still runs both role checks. The fixture limits discovery to its two exact
descendant sections before generating structural products, and scopes its individual result
reads to their producing operations. The bounded retry
`4fad3ac113214a0e87d4d94cd679da1e` published both structural reports and all three native
event stages for frame, fit and authorization. It entered scorer assertions after approximately
838 seconds of fixture setup. The same watchdog expired during scorer request attachment.
The two following cases were unrun. Scorer attachment and the remaining authority assertions
stay open. The test supervisor and its private database exited.

**Tested, 2026-11-20 UTC.** Integrated deployment `aa866a00932f49129fb709da4ce09ad1`
and its independent native release check passed on stage N42. The one-page cold demand
`cfbf7d53d411497b85442167f7d2b70e` refused the Integrated transform during port
acquisition, before inference. The captured transform asset matched its authoring checkout.
Main reproduced its parameters, execution files and reuse status, and produced a different
observed-code fingerprint. Main also produced a different observed-code fingerprint for the
worktree-built Standard organization asset. Prepare and admit both applications from the
main checkout used for execution. Confirm their exact asset custody, run the cold
Integrated check, and use the resulting Standard release and runtime for canonical
re-adoption. The failed demand and the cold excerpt remain available. The local provider
launcher exited and released its GPU allocation.

**Bounded provider evidence, 2026-11-20 UTC.** The actual CUDA GLiNER
production pack tests and the actual HanLP, Maverick and DiPO native
publication and exact-resume test passed in a ten-case managed selection
(`24dcecbab46c435f865578ab7c8eefd8`). Its GLiNER definition case reached
native publication and then tried to inspect the retired task `run_id`
column. The retry passed the definition case using the native request and
generation (`386a8512dff148fc867fc0cf94ff8057`).
The earlier N35 one-page Nemotron receipt retains its original scope.

The CPU E5 and Qwen encoder panel passed its two cases
(`05db4889f63e4361a4522d6099372204`). The three actual E5 selected-context
cases reached native retrieval preparation after the test source paths were
repaired. The installed guard refused the retained query and inventory
producers under the retrieval family (`1ba7efc4d2a4407b92b4f5251927289c`).
They require the admitted frozen-source role contract while local producer
checks and common publication proof remain enforced.
The typed guard repair passed 19 focused PostgreSQL controls
(`38a3cef5842f4840bd7a90c60b2f1d2e`), including exact named-source refusal,
generated routine checks and no-encoder composition. N37 installed on the
registered stage and the new Standard application passed native checks.
All three actual E5 context cases then passed native publication and
retrieval on private N37 (`313d571742cd47b9920c6e430421c980`).
[Native repair and provider evidence](../../design_review/evidence/2026-11-20_udm22-contextual-frozen-producers/README.md)

**Scoped readiness, 2026-11-20 UTC.** Private native selections exercised real
PDF spool resume, the D1 refusal, literal and limitation cases, concurrent
six-provider publication, and DiPO stale-holder reclaim. All six identities
have passing observations across the original selection and its two exact
retries. Those attempts preserve their own source and context. Final-source
provider qualification remains in this package.
The actual two-language source-discovery case reached native publication and
failed composition on the eight sequence inputs (`efd614f9181e419c9afa7cc5f8fc00fd`).
It reproduced the ordinal refusal with both regions available. Full
composition now declares sets for independently published regional inputs.
It shares deterministic source-coordinate presentation and execution with
captured composition. Focused input, binding and N37 native parity checks
passed. The first retry fulfilled both regions and repeated the same demand
with zero new receipts, then failed a stale observation of the publication
receipt (`632bd4dae1e44cfabcf3e12bc1c86662`). Its successor checks execution
evidence on the actual native intents that published both HanLP episodes.
The exact real successor passed on `6e24b62af`
(`d15eaeb9de574888b7cbd42e5ae13fa2`). It fulfilled both regions and full
composition, retained two real HanLP host executions, left PDF capture
counts equal and repeated the same demand with zero new receipts.
[Readiness receipts](../../design_review/evidence/2026-11-20_udm-closure-provider-readiness/README.md)

The Lark grammar, formal product and construction selection accounted for
295 passed identities across its original run and exact retry
(`5f8b8ca73e9a4876bbcf14c593d21e3b`, `350bed8fbae145aba761f8796df1deb4`).
The sole original failure expected a superseded message for the same
rejection of a replaced callable. These scoped provider and grammar
observations precede the final-source union.

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
class with a named owner, and no identity is unaccounted for. The target obligations T1 to T22
(T14 for the variants UDM-15 adopted) and every restated obligation must have passing receipts: a
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

**Prerequisites.** The functional packages UDM-01 to UDM-19 supply final source, including the
[continuation amendment](#continuation-compatibility-amendment), native authoring parity, and
the revised T4/T14 journeys. UDM-15 supplies entity reading correctness under fresh authority.
Persistent generator/page reuse and cross-request entity hit counts are deferred.
UDM-25–27 supply recovery and operational controls. UDM-20
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

### Expected adoption before the final run

**Tested, 2026-11-20 UTC.** A read-only census found the original canonical database at
N29 and book generation 5, with zero live book leases and zero unpublished book intents.
Every historical book request family had a different recipe from its counterpart in the
N42 Standard application. The recipe change requires new native request identities.
PDF spool adoption also requires matching producer recipe and implementation. Expect new
native capture and regional work on the first head demand, and check acknowledged
checkpoint reuse within that same demand during the controlled resumes.

For the final retained comparison, expect the current constrained parser and the independent
regex oracle to agree on the same retained native inputs. The changed recipe identities
supply no specific semantic disagreement to accept. Any disagreement needs a determination
against its retained input and production artifact.

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
endpoint. Independently census retained products, acknowledgments and valid intents and state
expected adoption, revalidation, and fresh work for each relevant scope before execution. Use the
original source, actual snapshot and current authority for this comparison.

**The run.**

1. *Start* the book under the stated memory policy: the 16 GiB policy recorded in
   `whole-book-host-execution-policy.json` (owned state 17,179,869,184 bytes, packet 603,979,776,
   reply 201,326,592, one million rows). The policy file used is retained with the run. If UDM-20
   showed that a bound must change, the changed policy is a new file with the reason recorded and
   not an edit of the old one.
2. *Interrupt during capture* after a recorded number of pages have been acknowledged, using
   `ci results stop`. Confirm cleanup independently: no live lease, no orphaned process, and
   the provider's GPU memory released. If all capture work already qualifies for adoption,
   validate interruption and replay on a bounded actual-provider capture on final source and
   record the complete reuse at book scale.
3. *Resume* the same demand from the managed result through `ci run resume --result ID`. Compare
   its effective policy and target against the recorded binding. Reuse acknowledged pages whose
   basis still qualifies and prepare only the missing work.
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
- The first final-head demand accounts for prior and new work independently, including current
  validation, checkpoint reuse, settlement and actual producer execution. Use T18–T22's bounded
  cases to distinguish valid adoption across releases and after eviction from a warm cache hit
  or a deliberately new observation. Preserve real provider evidence and full book coverage.
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

UDM-20 preservation and diagnosis start at once. UDM-21 follows the diagnosis and is the first
adoption. UDM-20 confirmation follows the affected design fixes on stage. When confirmation
and all functional packages are complete, the source is frozen. UDM-22 runs on stage and the
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
| Composition under a missing regional family | UDM-20's live N36 withholding case observed only `binding-covers`. The same demand fulfilled after the missing region settled | Bounded stage confirmation passed |
| No server-side statement timeout bounds the binding path | `SHOW statement_timeout` and `pg_db_role_setting` on stage and canonical development | The binding deadline decision in UDM-20 |
| Acquisition for the new PE-S33 demand | The successor separates executable source from the repository/test root and supplies the relocated factory sources. Help and compilation passed | The comparison still needs the final admitted book population. [Successor](../../design_review/evidence/2026-11-20_udm20-live-withheld/compare_retained_book_construction.py) |
| The failed run's records are still in the result store | Step 0 of UDM-20 | How much of the diagnosis starts from records and how much from narration |
| A demand can be scoped to one region of the book without registering an excerpt | Reading the demand's scoping at entry to UDM-20 | The construction of the bounded cases only |
| Retained sentence and formal-evidence products have eligible exact inputs under the final capture | UDM-23 census and equal-content cutoff | Which downstream work the first final-head demand must execute |
| The fault lane can have the native host to itself | Arrangement with the operator before UDM-22 | When UDM-22's step 3 runs |
| One full run can serve both this series and TDM-18 | The test series' own judgment of applicability | Whether the test series repeats the run |
| A supported content witness exists for a served-result variant (DA-075) | UDM-15 supplies the direct entity witness. Each additional variant needs its own argument | T14 remains required for direct entity reuse. Additional variants join when adopted and are recorded as not adopted only when their premise is declined |

## State

| Package | State |
|---|---|
| UDM-20 | Complete for the bounded stage. N36 passed 60- and 66-page regional settlement, complete-family composition, and actual two-region withholding and refill. The cancelled N35 demand and unpublished draft retain their recorded custody. [Diagnosis and evidence](#retained-book-diagnosis) |
| UDM-21 | Complete. Original custody, exact intent reconciliation and book generation 5 at N29 verified. The actual one-page Integrated provider run and launcher restoration passed on N35. |
| UDM-22 | In progress. Continuation, bounded stage confirmation, actual CUDA stop and N42 rich admission passed. Final application preparation on main, event scoring, M1 readback and final-source coverage remain open. [N42 evidence](#retained-fit-custody-and-rich-producer-authority) |
| UDM-23 | `not_run`. The second canonical adoption and whole-book run await UDM-22. |
