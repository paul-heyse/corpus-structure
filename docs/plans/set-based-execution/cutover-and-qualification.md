# Cutover and qualification

**Status:** The early producer chain passed in a private target. The cold-root rehearsal
registered and installed the replacement on an empty database. Integrated acceptance remains open.
Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns how the series lands: the native revisions, regeneration, retirement and the
assembled evidence. It owns SBX-20 to SBX-22 and the shared early integration and change scenarios
used by the preceding packages. Source observations below are **Inspected** at `d36e07594`.
Design and acceptance statements are **Proposed**. The [coordinator](../set-based-execution_2026-11-21.md)
owns current package state and review dispositions.

## Cutover policy

The operator authorized an empty development database for the hard cutover through SBX-09
on 2026-11-21. Discard the old development data, including source and derived rows. Work on
clean native targets with new fixtures and delete superseded runtime paths as their replacements
land. Development acceptance requires no backup, migration, restore, backfill or regeneration.
All originals, selections and derived rows in development are disposable. Managed evidence
keeps its recorded standing.
Stage installation belongs to [SBX-20](#sbx-20).

**Testing during development** uses compile checks and targeted functional tests for the
scope just implemented. Verify final source against the registered cold root. If captured
native artifacts change, author its replacement against an empty authoring target on the
dedicated PostgreSQL cluster.

**Stage predecessor · Inspected · 2026-11-22.** The stage transition starts from
`semantic_ddo_pe_n47`. Commit `65c6da048` registered and verified that revision with the stage
guard. The checkout immediately before this implementation was `83ab2996d`. SBX-20 uses the
stage revision and its Git-held native inventory when it prepares the stage transition.

### Development reset through SBX-09

1. Integrate the remaining consumers of the [selected immutable carrier](common-analytical-basis.md#pilot-implementation-and-evidence)
   and finish the functional changes through SBX-09, including the
   [live-page handoff](validated-values-and-handoff.md#sbx-live-page-handoff) and
   [summary correction](owner-resolved-reads.md#sbx-live-summary-correction). Apply the
   [efficiency qualification setup](#sbx-efficiency-qualification) before attribution and
   targeted checks. Verify the already registered sole root against final source. When
   captured native artifacts change, use an empty authoring database on `18/corpus`
   created with `uv run ci db init --creation-only` and bind the reader and maintenance
   settings to it. Run `uv run ci model change preview`, `candidate` and
   `inspect-candidate` for `semantic_sbx_current_root` with a null predecessor and zero data
   steps. Confirm captured source, descriptor, objects, grants and rollback. Register the
   inspected candidate with `uv run ci model change register` and install it with
   `uv run ci db init` on a separate fresh qualification target. Confirm the sole head,
   exact descriptor, and intended purpose-role admission and refusal for final source.
   The retired development chain has a recorded Git baseline for SBX-20.
2. Run `just turn-end` before final-source qualification. Run `uv run ci test` and
   `uv run ci check` for the applicable ordinary and shared fault scope. Use
   `uv run ci test --providers-only` for changed real annotation and canonical, HanLP
   declaration, construction, learned definition, contextual, protected reference and PDF
   provider paths. Use the existing verified native deployment template and per-test commit clones
   for ordinary provider and sentence-chain fixtures. Point their preparation at the registered
   root. Replace fixture-local authorship and installation in those journeys. Keep independent
   cold authoring and rollback controls, and use the dedicated shared host for shared
   authentication, faults and durability.
   [Verified test deployments](../../adr/0101-verified-test-deployments.md) ·
   [Commit clone fixtures](../../../python/corpus-structure/tests/conftest.py#L377)
   Run the ordinary executor against fresh
   fixtures through the committed propagation, binding, recovery, memo and hand-off scenarios.
   Exercise the chosen annotation fork through publication and exact selected readback, including
   the relevant occurrence, support, provider and worker controls. Keep one authentic finite and
   rich publication-to-export replay. Record managed IDs,
   selected identities, exact source, revision and context. Use the
   [bounded cohorts and coverage reconciliation](#sbx-efficiency-qualification).
   Complete required acceptance before resetting.
3. Recheck the dedicated cluster and the exact `corpus_structure_dev` maintenance identity
   with `ci host status` and `ci db status --maintenance`. Drain its writers and sessions.
   Drop only that database from the verified cluster's maintenance database without force.
   Recreate with `uv run ci db init`. After interruption, reread acquired state and resume
   initialization on the same target. Verify the new database identity, installed native
   revision, descriptor, roles, and empty project, source, demand and product relations.
   Keep qualification fixture data on qualification targets. Stage installation belongs to
   SBX-20. Record the acceptance and reset in the coordinator and status checkpoint.

<a id="sbx-efficiency-qualification"></a>
#### Efficiency qualification and native attribution

**Scheduled · 2026-11-22.** Start with a stable checkout, installed descriptor, intended
purpose roles and fixed generated metadata. Regenerate companion data before the run.
Separate candidate and release preparation, installation or clone, native statement
and transfer work, worker or provider execution, and assertions. A pytest setup phase can
include actual publication and fitting. Reuse verified deployment templates and immutable
preparation within their exact release, runtime and source premises. Reuse an authenticated
producer fixture for downstream assertions only while its producing and interpretation
premises apply. Give tests with native effects their own commit clones. Keep independent
cold authoring and rollback, shared authentication/fault/durability, real provider and
authentic publication-to-replay journeys. [Review I07](../../plan_improvement_reviews/set-based-execution-validation-and-postgresql_2026-11-22.md#I07)

Use existing timeouts, role constraints and data limits for representative comparisons.
Start serialized on a seeded qualification target. Use database-, role- and query-scoped
`pg_stat_statements` deltas and wait observations. For a material unresolved branch,
collect targeted nested `auto_explain` on the isolated target with parameter logging
suppressed. Verify effective settings before fixture execution. Keep a separate ordinary
baseline, match the acquired cut and workload where compared, and report server elapsed
and client phases separately. Keep private effects within owned fixture commits or
rollback-only probes. The earlier outer logs and small late capture leave event internals
open. Read attribution belongs to [SBX-11](owner-resolved-reads.md#sbx-native-read-attribution);
attachment and completion attribution belong to [SBX-06](references-and-projection-keys.md#sbx-native-attachment-and-completion).
[Native timing evidence](../../design_review/evidence/2026-11-22_python-postgresql-efficiency/postgresql/README.md)

Advance a bounded correction before broad qualification when source inspection or representative
evidence shows that it removes material repeated work, contention or preparation from a
required journey while preserving its contract. This includes required journeys that
already finish within their watchdog. Use a bounded comparison when attribution or lifecycle
cost could change the choice. For an early scalar read, use the additional
[SBX-11 selection criteria](owner-resolved-reads.md#sbx-native-read-attribution).
Inconclusive attribution leaves any required failing identity open while independent work
continues. Record any remaining conditional optimization and its revisit trigger with the
owner. Broader SBX-11/12 work and the SBX-18/19 placement decision keep their
sequence. A changed authority, custody or architectural rule follows the
[existing decision route](common-analytical-basis.md#decision-routes) before adoption.

Once scoped read corrections pass, run heavyweight native cases and lighter cases as
disjoint, bounded cohorts with exact selected identities and affinity groups preserved.
Use measured host headroom for worker budgets and avoid concurrent changes to captured
source or metadata. Reconcile managed results with `uv run ci test coverage` against the
original required selection, retaining failed and interrupted evidence. Assess applicability
by exact source and context and repeat affected identities as needed. An inconclusive
optimization comparison creates no additional acceptance gate. Existing required
identities retain their acceptance obligations.

**Efficiency execution checkpoint · 2026-11-22.** Stable ordinary collection passed for
9,589 selected identities (`3fb72541bec64efb951a761dac0181c8`). Provider collection passed
for 38 (`0b72efacd0a14406b7935cbe42244b15`). The isolated ordinary event baseline
(`7330a209f8874d8ebad47cf9d7a7172c`) failed its three cases in the shared setup.
PostgreSQL canceled two evaluator calls to `renew_data_request` at the existing 10-second
renewal limit. The private log reaches historical definition correspondence and repeated
nominal child schemas through witness and output-reference body access. A setup stack
also sampled duplicate schema copying during static port correspondence. These
observations identify specific repeated work and do not establish end-to-end timings.

The selected changes retain one private LinkML schema copy, reuse the admitted live result
and witness meaning, stage per-item attachment scopes once, and use one canonical
completion encoding with separate framed and payload digests. Stored products and members
already passed strict native admission. Renewals and live reads reuse that admission
for nominal shape while checking current purpose, support and exact occurrence. The stored
body route can use current evaluator membership for all admitted universes; ordinary
purpose still walks the actual member kind closure. Incoming packets keep the recursive
schema checks. Preview `4775d29ebf7747f2b3787c24618955ab`, rollback-only candidate
`410ff9ab575940938887f5f95fe14109` and registration `892e4269383644b9be4539b9c9562a4a`
passed. Installed acceptance and development reset remain separate obligations.

**Refreshed root acceptance by selected identity · 2026-11-22.** On `9c8378632`,
`uv run ci db init` installed the refreshed sole root on the empty
`corpus_structure_sbx09_eff_final` qualification database. The descriptor matched the
frozen program. Reader disclosure, writer and evaluator resume, and the private helper
refusals matched their purpose grants. The project, document, original source, demand and
product relations were empty. `uv run ci check` passed (`d50cc41e3a354944b18af19191665002`)
and `uv run ci test --lane fault` passed all eight shared controls
(`cb20140df66a427fa487ef4545de69c7`). The model projections were current.

The guarded public read passed, including the warm-cache lower-budget refusal. Its
48.3-second call followed 253.1 seconds of fixture setup. The summary, protected nested
body controls and authentic finite/rich producer-to-replay identity passed in the same
private selection (`94119172d7894e12bbcc122c8f945798`). Its initial seven witness
failures were in fixture preparation and expectations. The corrected fixture passed
publication and all six refusal cases in `e27900def706432085cf219d74a4d0c4` and
`f5c97a83b4b94b6e806918ee7f221e46`. Managed cleanup recovered the original
selection after preserving the worker's synthetic recipe scratch, and coverage accounted
for all 17 identities. The fixture now uses pytest's own temporary path
(`ba9b1d985c2942819628a010de0a7bbb`, passed).

The renewed private event selection passed its full three-case journey without changing
the 10-second native renewal limit (`09725b2de1be4bd6ac7252911b2b74bc`). The corrected
scorer fixture uses the same named-definition variant reader as production. The actual
two-report construction provider passed with both independent outputs at position zero
(`7419fb37fb0c4adda31fe20a3085be5b`). Runner self-tests passed all 443 identities on
their shared-host route (`f488b4f4fa524d8d9a42649e9b0c38db`). Broader ordinary and
provider campaigns remain in progress.

**Remaining campaign · 2026-11-22.** Recovered ordinary attempt
`013397a8e6d648669ff746608782bbc7` retains completed identities from the prior
filename split. The current inventory's native requirements and affinity groups
partition the remainder into 5,609 release-independent identities
(`358928b66cda470d8b78bb0b5a738be1`) and 1,316 native identities
(`5e94f0ab204e4be79766996b0c34a44c`). The original heavy receipt
`1551b539323c4b10914abf8706465757` passed 55 of 58 selected identities.
Its three failed identities have separate dispositions:

- The formal test's old reuse assertion is superseded by
  `test_native_current_new_rule_release_keeps_formal_attempt_and_original_source_custody`.
  The corrected real test and both deterministic cross-release controls passed
  (`1dfb94c337354531a037676fbde21a30`).
  [Formal execution scope](references-and-projection-keys.md#sbx-06)
- Private authored admission and grouped read passed on the isolated
  `2912c7971` correction (`8d23c87657914690a6f71f1bde179b6d`), including
  no-match terminology, both exact authored kinds, unrelated-kind refusal and revocation.
  All 19 projection controls passed (`b00967c597854314853078f486077084`).
  The patch awaits integration after the active captured-source campaigns.
- The structural dossier worker failed in Python/RDFLib model preparation before an
  assertion. The exact one-worker private retry passed the structural authorship,
  issuer, selected-gap and detached-export identity (`fd7cfde2b5b4446b99eea9d745b2e07e`).

The additional provider scope reproduced the inherited T4 keyed mapping and toy
decimal defects (`5bbc1046da8f48588bae0f8fbb9e07d0`). The result preserves these
as failed; they are separate from the named changed-provider and authentic replay
requirements of this cutover. The affected provider selection is also retrying the
identities that originally lacked the installed PM2 asset directory setting
(`d8565b34e13d47468b6065d1304732e8`).

**Ordinary and provider follow-through · 2026-11-22.** Three shared-authentication
controls passed on the shared host (`994ab77b344f47b0810912910d38f3b6`). The
one-worker CPU lifecycle retry passed all nine tests (`5faf3d3701104c8cb9065c3cad10b383`).
Current observation, declaration, protected reads and exact binding fixtures passed
their scoped retries (`cf406ff3b59c460e8d0539f7a609cb89`,
`9cdfd9d3d27744719f9bc594dbd8b0e7`, `742f867d911446658c713fd3aac49918`,
`e34f673b490f4d4ab1fd86a247cefe41`). The active same-release source cohort retains
the earlier failures and subsequent scoped passes.

The real two-language-region journey passed its call in the active PM2 retry, including
exact native resume. The isolated test database's top-level `pg_stat_statements` rows
reported one attachment group with 7 calls and 94.35 cumulative server seconds, one
publication group with 16 calls and 89.22 seconds, and one completion-intent group
with 16 calls and 27.14 seconds. Maximum calls were 41.72, 28.43 and 8.21 seconds
respectively. These are one fixture's per-statement groups. Nested costs and earlier
release preparation are outside that observation. A concurrent annotation-fork
worker waited for the same physical GPU lease held by the PM2 worker. Keep that wait
separate from the cost of either worker's PostgreSQL transactions.

**Cold authoring checkpoint · 2026-11-21.** `uv run ci db init --creation-only` created
`corpus_structure_sbx09_author` on the dedicated cluster. Managed preview
`038a531859e443c19f46429255d4876f` and rollback-only candidate
`9d52c84a67124150a960535150fd60e5` passed for a null predecessor and zero data steps. Candidate
inspection identified the active N47 migration head as the remaining registration conflict for
this preliminary source. The exact integrated source needs its own candidate and cold install.

The follow-up `uv run ci model change candidate` passed rollback-only authoring on the same
empty target after native pending discovery, indexed adoption and construction source proofs
(`ac0c58dfeee945d587966c7c69c29bda`, preview `aa4c26a371534e2990b1eb911fc221e3`).

**Cold installation rehearsal · 2026-11-21.** The isolated checkout retired 256
frozen predecessor files, five revision data-step builders, and the native re-lowering entry
point used by the old data steps. Generic native successor authoring remains available.
`uv run ci model change candidate` passed (`8fa321fb099d4a5b9175279ba5dac76f`,
preview `42df5b1b7dd541d397f522020c8e2db2`).
`uv run ci model change register` registered the sole null-predecessor root in that
checkout (`3c8d0725d0b34912b5f2860699486a0d`).
`uv run ci db init` installed `semantic_sbx_current_root` on the empty
`corpus_structure_sbx09_cold` database. This rehearsal predates the remaining SBX-06
and SBX-08/09 integration. Main registration and the development reset stay open.

The next isolated build compared the native stored empty-collection default in online
inspection and detached export. Candidate `0b87567e253a4cb699ee9d3b22f1fdfc` and
registration `54656b69aedd4bfb9afa2fd20750778e` passed. `uv run ci db init`
installed the refreshed root on a second empty rehearsal database. The targeted native
run `037643e85d0a48daad9cfb3b0c35d2dc` passed 36 cases, including installed reader
correspondence, detached export replay and changed-child population reuse. One controlled
composition case reached an analytical provider before it could check the selected source
population. Its fixture now stops at the actual source-view publication boundary. Retry
that case against the next integrated root.

A subsequent isolated checkout containing the newer native demand and proof changes passed
preview `b7ee66f404f44834b5976bc30bb12768`, null-predecessor candidate
`7e1e964fbc534356b5bd6bf70b640d5a` and registration `3ae875080cb74428bb24e1ce1e21fa68`.
It retained one active root. The installed ordinary scope and later source changes still need
integrated evidence before replacing development.

**Integrated authoring checkpoint · Tested by selected scope · 2026-11-22.** A private
checkout captured the writer-only resume, bounded publication reconciliation and exact discovery
use changes. `uv run ci model change candidate` first refused a changed generated file
(`5ad8bb7041854e7ab53a356c7924f92a`) and then identified a `bigint` argument to an `integer`
receipt limit (`d2fbb15fc0da45269be9454ad06505dc`). Applying the generated files and passing the
bounded count as the declared type produced a passing rollback-only candidate with a null
predecessor (`a486325d0a4341e2b565d568d39814ec`, preview `ffde9beb25294a73b6f6b126b4791c81`).
Registration passed in the isolated checkout (`5ef35305ba1d40bcbcf6d02a69936bb1`). Fresh clone
replay exposed a private resume envelope decoding defect before native stream, finite and
canonical execution (`dfdf3fe832ca48dd829efcc96816c0fd`, `df99fea6fd7f4e42be67bc84c5c41d69`,
`97b145b8bc8a43e0b7897bfef3a78f27`). The stored response carries the frontier under `payload`.
This checkpoint predates the remaining settlement and contextual integration.

**Checkpoint replay · Tested by selected identity · 2026-11-22.** With the private response
unwrapped in the isolated checkout, the actual finite candidate advanced through rich publication,
native export and verified detached replay (`uv run ci test --native-host private`,
`06edf263c5b3425188466cb1c316eb80`). That mixed result's dossier setup lacked the declared
admission input kind. Four native stream cases passed in `b83d32374d714e5190d93e7694a036eb`.
The cancellation case passed after its fixture acquired the read and attached in separate
transactions (`uv run ci test retry`, `426c687fff2b4ca28a51088099b9d575`). Final-source
qualification repeats both selections with the registered wire contract.

The next registered-root provider and dossier attempts reached discovery settlement. The
population-close routine rejected the added `admission_use_id` before the affected native
binding (`7a63e15235544a4c8ebea14c9382194a`, `1cecafeeb4584e4e8076db020e5213d1`). The routine
now treats that field as an exact optional pin. The next checkpoint exercises its native
type guard and admitted-use match.

**Registered wire checkpoint · Tested by selected identity · 2026-11-22.** The next isolated
root passed managed preview `b4a92f8cc67a40a297592dc3e420309a`, rollback-only candidate
`f747ad5c23934802aff41ce9f3e0d715`, and registration `1b165ce82c6544178978e513f7d68b74`.
All five native stream cases then passed through the registered wire, including read fencing
and cancellation (`uv run ci test --native-host private`, `5edb009f93ad4e94b4442b6c0899374f`).
That mixed attempt reached published applicability in the dossier before a test assertion
mistook a canonical report identity for a body field. The publication-delivery control also
found a mismatch between the accepted original input use and the reported current
recipient. Final qualification includes corrected dossier and exact-use replay controls.
The same registered source passed the two governed CUDA cases by identity (`uv run ci test
--native-host private --providers-only`, `9075a3dfe31c4452879cc4db607fb897`). One verified
adoption after a different real annotation capture produced equal canonical semantics without
a new canonical generation. The other verified moved, renamed, repeated, split and merged
block placements at named selection generations. The other two identities refused at producer
custody before assertion of contextual or multi-report construction outcomes. Both remain required.

**Readiness and dossier checkpoint · Tested by selected identity · 2026-11-22.** The dossier
retry passed actual applicability publication followed by selected membership and verified detached
replay (`uv run ci test --native-host private`, `30c93385c75e4c139db653e38939c6ab`). The next
main-checkout provisional native root passed rollback-only authoring with 802 registered operations
(`3ac4c95a62a748f6ab406e8618f4967f`) and registration (`d7865aa5f6264091ada397a7c793495a`).
In its installed clone, the full publication-delivery module passed along with scalar and
collection coverage, exact-pinned readiness and original and selected population wakes. Two new
overlap cases in the same result stopped at a fixture's direct internal table read under the
writer role (`c861a4f958fb4b97b12f60da07f07dd2`). The corrected retry acquired the obligation
through ordinary writer resume and checked the sparse pointer under maintenance authority.
Both commit orders passed (`6e6c6f7ee85540109ef0c782c04a4402`). The origin committed without a
visible recipient. Native resume recovered the exact cross-demand pin, left it idle on the next
unchanged read, and bound it after a third distinct producing episode completed the input set.

The same provisional root passed the ordinary finite-to-rich detached replay and native
comparison by selected identity (`uv run ci test --native-host private`,
`6bcae026e28447829c4fe7a978d84a95`). Cross-work artifact publication completed. Its live
inspection reached the default 8 MiB examined-closure limit. That fixture now requests the
existing 32 MiB caller budget to exercise the complete selected graph and its archived member
references. The retry passed both exact cross-work artifact and formal comparison references
through the registered checkpoint (`e2b1b670a5274bff9fc931ebf9b2ef8e`). SBX-11 owns the keyed
read. The patched provider checkpoint passed contextual
publication (`4dd80f50071c4096a2f95292c779a806`), and the two-report construction case reached
publication before a fixture compared the local current request IDs to those of the original
independent reports. Its corrected check uses the exact producing derivations and admitted uses.

**First assembled root installation · Tested · 2026-11-22.** Managed model preview
`a850d08e091b4912868483c935ca0162`, apply `d70bcfa5b6874e71b5d4ddaa1d02602b`, and rollback-only
candidate `13c1631f45dc4a8e9ef1b494cfe26754` passed. Candidate inspection confirmed a null
predecessor. `uv run ci model change register` installed the sole revision file set in the
checkout (`99ea673ffb5d4f7384b0a61798a2ef80`). `uv run ci db init` applied
`semantic_sbx_current_root` on the empty `corpus_structure_sbx09_qualification` database.
Maintenance readback matched the installed native descriptor to the registered one, verified
reader, writer and evaluator grants, refused reader scheduling and direct writer publication,
and found zero projects, documents, originals, demands and products. The development reset
follows integrated functional and provider acceptance.

**Assembled campaign correction · Tested by selected scope · 2026-11-22.** Repository
checks passed on the first assembled root (`uv run ci check`, `7360d586ec654eae947a5cf485afa29e`).
The ordinary campaign exposed an unsupported dictionary call in the formal-premise attestation
checker and was interrupted so it could be repaired (`5adddd3b9f9845a1a47a6b4ede822cca`).
The replacement uses the existing compiler-supported inventory accessor. Actual operation
compilation and 12 other focused cases passed (`f6b311166e7a4cb2b18bd96087fed54a`). The
native readiness result passed the incomplete, complete-empty, filtered-empty and
complete-insufficient cases (`9b8d01f321f84eada5bed8399075b014`). The minimum-zero case required
an optional role in its fixture. Read, publication and evaluation fixtures now use their
current native contracts. Focused claim renewal and affinity diagnostics passed after the
test race and collection reporting were corrected (`8b88ef0c82d54a7c87ba4549a1ff9e16`).
The construction fix changes captured source, so the corrected root is recaptured and
qualified from its own registered revision artifact.

**Corrected root installation · Tested · 2026-11-22.** Preview `3fa54691c2ff44d298193069b6be47e0`,
rollback-only candidate `f5b28c5b5ac240d69fb9eb857dd531ea`, and registration
`8aa866c625664aefb97a3c12a4f052da` passed. `uv run ci db init` installed the corrected root on
`corpus_structure_sbx09_final_qualification`. Maintenance readback verified the exact native
descriptor, purpose-role grants and empty project, source, demand and product state.

The installed-root scheduler selection passed all 12 cases (`uv run ci test`,
`74537a95e42147058e034e91c03fd2da`). It covered pending incomplete populations, unavailable
complete empty, filtered-empty and insufficient populations, optional minimum-zero settlement,
and both commit orders for the cross-demand recipient.

**Interrupted integrated qualification · 2026-11-22.** A development-environment interruption stopped the
ordinary campaign (`uv run ci test`, `a8841a637e3e452b8a7ae2cb3c2e41fc`) and the actual
provider campaign (`uv run ci test --native-host private --providers-only`,
`eecc4da197e94c058d05cd75a270779b`). `uv run ci results recover` refused both because the
supervisor settlement records had not been written. Their partial logs identify contextual
manifest and dossier compiler defects and assertions targeting superseded carrier shapes.
Fresh managed runs qualify the repaired source. Maintenance reinspection after the interruption found
the original development database at native revision `semantic_ddo_pe_n29`.

**Restart checkpoint · Tested by selected scope · 2026-11-22.** The contextual manifest
and construction fixes passed the 20 selected `uv run ci test` controls
(`9ad1e7e5f37841a883205dc8bb948a0a`). The dossier retains its comparison reference, side and
citations. Its existing compiler and downstream-profile controls passed in
`4af576145aab4a90b568f1d25e187bfa`. The draft regression failed on fixture coverage and its
replacement with a real formal witness passed (`b3b6c7a852164f488a16f44edbb63884`).
The carrier and contribution assertions passed across their initial selection and one exact
retry (`284bcf9ce7264e8a8ac36aecd57f8a9a`, `d0660fecc37c4d069667b90f1717af64`).
Preview `6c069fbc7d864ce084952fcc4a7725ee`, rollback-only candidate
`cf56a1d5cb314651913ae594c2656f0c` and registration `c4ac4de7a5c9491c8da780505cf9f550`
passed. Only authoring provenance changed in the native artifact. The installed qualification
target has the same SQL and descriptor. The final root follows the remaining roster retirement.

The restored checkpoint passed real GLiNER definition and exact component-source readback,
HanLP declaration and Docling missing-page recovery (`uv run ci test --native-host private
--providers-only`, `c5fcfd2775ef4eb5802e94ca937a6f35`). An ordinary mixed selection passed
the native streams and authentic finite and rich detached replay. Two controlled workflow
fixtures failed preparation because their predicate reports lacked current reference-target
declarations (`fc97df6c943343e388064c9686866fe1`). The corrected fixtures passed both focused
preparation identities (`94509dece2884063aa60939927b0fba8`).

**Terminal discovery · Tested by selected scope · 2026-11-22.** Preview
`35ebb2b12b5f48a28505dafd23c11da6`, rollback-only candidate
`f9aa96e4d84a4969a67915a51f31b84b` and registration `aba2ef5d3ee84bb89b5909a434f983f7`
pass for the new model. All 11 selected `uv run ci test --native-host private` publication,
readiness and closed-population cases passed (`6866d4acc9fb4179a67c200c9ac8d6d2`). The native
terminal-empty controls verified publication with zero outputs, unchanged pending state before
publication, a pending failed producer and loss of settlement when empty-result authority is
revoked. Complete original input disclosure is qualified with the final recapture.

**Complete original input authority · Tested by selected scope · 2026-11-22.** Native
PostgreSQL controls distinguished an authorized empty closure from one with a hidden original
input, while retaining exact partial citation resolution (`uv run ci test`,
`f9cf6e2f06904c2880b5f253c1dac6ad`). The final-source contextual selection passed 16
cases (`a6540965d78045908677ce65586e5745`), including real profile capture, a spawned
contextual-native reply and refusal of an encoder input with a missing original parent.
Typed construction, declaration and graph fixtures also passed their corrected selections
(`e532e9d7d5014c1aa92f7416f06b7c48`, `348898273233417ca5cb6b2183bbd1a9`).
The native workflow retries then exposed unbound callable parameters in their controlled
producers (`4aa58fa265b3472c97ae579b810a9db3`). The fixtures now map their unused optional
roles to explicit empty arguments and retain independent source-only assertions.

**Integrated root installation · Tested · 2026-11-22.** Preview
`7fdede4ea3a34c61920c05c45e3b8732`, rollback-only candidate
`a1379f192094467c9eb2c2d5e6688866` and registration `ffec9f6246d843fcb68dbe691b944db0`
passed. `uv run ci db init` installed the sole native root on
`corpus_structure_sbx09_integrated_qualification` (OID `136240545`). Maintenance readback
verified the exact frozen descriptor, reader/writer/evaluator grants and five empty project,
document, original, demand and product relations. The integrated type check passed
(`uv run ci check --only types`, `a980311531fc4f1686b0abe829daa1c7`). Broader functional,
provider and repository qualification follows.

**Integrated qualification checkpoint · Tested by selected scope · 2026-11-22.**
`just model check` and `uv run ci check` passed (`73e3b6a7631d4da98591e4b7c3b48670`).
Both native dossier identities passed on the integrated root
(`uv run ci test --native-host private`, `30639a627c184863a4cdad0dd38ec05d`).
They exercised populated applicability, selected membership and verified detached replay.
The integrated ordinary campaign and provider campaign ran concurrently
(`ab9513b363b24a98b47a874bdfb53416`, `2f85ad9fefa54e029cfc8d9f10e93a10`).
The provider lane lost two workers to their test watchdogs. The host ran out of memory while
both campaigns were active. The managed supervisors drained on request and retained incomplete
ordinary and provider results. The shared fault lane then passed all eight cases.
The assessment fixtures now pass all 33 selected cases with the carried construction inputs
(`b0de9837d0794da8ad1f6f7a402a7f83`). Reconcile unresolved ordinary and provider identities
using smaller cohorts. The development database still awaits integrated acceptance.

**Repaired root installation · Tested by selected scope · 2026-11-22.** The event frame
resolves its definition component through the admitted nominal member of the authenticated
report. All nine private event-program checks passed (`11f685287b2a4fedb73879ccfd90af70`).
Composition sends canonical acquired source bytes in the authenticated worker packet and
restores each source carrier in the child. The spawned-worker control matched synchronous
composition on two independently placed source regions.

Native rule settlement now shares output premises by the projection the rule reads and
shares original input observations within the producing episode. The two private rule
establishment cases passed (`d9732b15b9964b3481a49245bc94af42`). They checked exact
fingerprints, independent checker identities and refusal after a change to an observed
input. The actual M1 publication retry owns acceptance of the prior timeout.

Managed preview `c68950dfbc0d462d93a476e7830ec868`, apply
`baf8221c0f8048f7927dc349aef2b10b`, rollback-only candidate
`7438679df46c47c2b3828bf64890f519` and registration
`59df3f1e7be7414fa35d5f26ea41c5cd` passed in the assembly checkout. Inspection confirmed
the null predecessor and absence of data steps. `uv run ci db init` installed the sole root
on `corpus_structure_sbx09_repaired_qualification` (OID `136314657`). Its native descriptor
matched the registered body. Maintenance readback confirmed purpose-role grants and five
empty project, document, original, demand and product relations. `just model check` passed.
The registered-root event and provider selections continue in managed results
`c1bc745541c246ee8184a53541707d2f` and `ecb00e443c4d4e68a867d9f5dafb0352`.

The earlier narrower ordinary retry `bb88c40af25747379252b2200d868f52` and provider
retry `ecc12c5ea60343d6a61e19362b24d20c` drained before the refreshed root landed on
main. They retain 790 ordinary and eight provider-lane passes, together with their failed
and incomplete cases. The two provider attempts cover 25 of 38 selected identities by
managed coverage comparison. Assess that evidence against the changed executable root.
The fresh provider selection addresses the ten outstanding identities outside the three
journeys already running on the refreshed root.

The broad ordinary run also exposed an inherited private authored-judgment defect. The
baseline terminology declaration combines a required collection with a zero minimum, which
the existing compiler lowers to a minimum of one. This refuses the empty candidates of a
no-match decision. An isolated declaration correction advanced the actual journey to native
admission (`b9aafa2fe6eb458d92f54cccb9a1440b`), where the exact release-kind lookup refused the
authored measurement judgment. Preparation confirms both private authored-judgment kinds
are absent from that release's native kind projection despite having semantic identities.
The terminology declaration, compiler behavior and native kind dependency roots predate
this cutover. This result remains a failed ordinary identity.

The controlled external statistics selection `a6bafcb7e0e34f219ba5fa99a7a7b9f3` also
exposed two inherited typed-admission gaps. Both generated JSON body schemas accept their
case. T4's typed schema expects a sequence for the keyed parameter mapping. The toy case
projects a nested decimal to a float before checking its decimal kind. The keyed description
predates this work (`6020b5273` and `5eabc9e35`), as does the ordinary numeric projection
(`41bbb1ac7`). The native refusals and independent scientific expectations remain intact.

**Native replay and premise follow-through · Tested by selected scope · 2026-11-22.**
All 26 cases in `15c732e51b524bca82e59a6b14d0574f` passed their assertions. This includes
stream fencing and cancellation, scoped readiness and wake delivery, the exact finite and rich
detached replay, and dossier publication with selected applicability. The original invocation
failed teardown on a retained multiprocessing socket. Focused cleanup and custody tests passed
all 54 cases (`ee29bfa07f924fd08940369199e56ddd`). Managed recovery established the stopped
host's cleanup. `uv run ci test coverage` reports all 26 identities covered and preserves the
original invocation outcome.

The real two-region composition case passed on the refreshed root. The M1 case in the same
provider result (`ecb00e443c4d4e68a867d9f5dafb0352`) still hit the default publication timeout
inside the recursive JSON-to-meaning traversal. A diagnostic shared-host run with a
300-second completion window reached the second normalization pass in the same premise
calculation before timing out (`5ec6ed6dccae4b9e9be19e9178dd306b`). The isolated codec repair
converts nested object-free arrays in one ordered pass and uses the existing proof identity envelope
with those canonical observations. Independent native controls passed for exact proof bytes
and changed-input refusal (`28a1116ea3e0420792292b06533557d9`), including a follow-up with
4,096 member records under a local 60-second statement bound
(`ed253bec603441ed8e995466a572d4ed`).

Managed codec preview `51fd211ec98b4079aa21c7129601dc35`, rollback-only candidate
`eeb083631e6f4fbf87d456b174f84767`, and registration `69e6a4d8b90b4671856d9b7207a32e07`
passed in the isolated assembly. `uv run ci db init` installed that sole root on
`corpus_structure_sbx09_proof_qualification` (OID `136473031`). Maintenance readback matched
the registered descriptor and verified the purpose grants and empty data. All 16 native
identity and rule tests and `uv run ci check` passed
(`3e0fbdcc3dae4c3db3a5331402ca892a`, `604f40cb0e5143fe88903e794503c92f`).
The actual M1 GLiNER candidate inspection and cohort custody case passed at the normal
120-second statement limit (`7c1659f02d00483a83953d1b9b5b24bd`).

**Bounded proof codec · Tested by selected identity · 2026-11-22.** The native tokenizer
uses one stored JSON rendering for object-free arrays of up to 32 MiB. Larger arrays continue
through the exact recursive codec. The limit selects an execution path and accepts the same
input domain. Focused controls passed at and above the rendered-byte boundary with multibyte
and escaped strings, and matched the prior typed and 4,096-member proof checks
(`e09bdb1a003d44fca1b773681e2b5d93`). Managed preview `d9bf16bb174e4631bc56a70c53f77343`,
candidate `ea88a122693c4800a3048959b62c61a6` and registration
`40883fd5f5974869918110ccaf5635d2` passed in the isolated assembly. The installed empty
`corpus_structure_sbx09_bounded_qualification` (OID `136550030`) reports the sole root. Its
native descriptor matches the registered bytes. Reader disclosure, writer and evaluator
resume, reader resume refusal and writer direct-publication refusal match the declared grants.
All five project, document, original, demand and product relations are empty. On this source,
all 17 native identity and rule controls passed (`e7b639a211174f3b99f4a1e6ba0a4a89`),
along with `uv run ci check` (`13508dc2ef1b4d72bbcb3699aebda485`) and `uv run ci test --lane fault`
(`c309c66fa38b4428976223ab9a2c6992`).

The refreshed event suite (`c1bc745541c246ee8184a53541707d2f`) passed 85 independent worker,
source and migration controls. Its native journey published the corrected event frame and
reached fitter and issuer execution before the 40-minute test watchdog stopped the worker.
The codec-root event selection starts with the independently acquired restricted-frame check,
then runs the fitter, issuer and scorer controls in the same module fixture.

Regenerating the packaged report artifact refreshed its source identity for the four current
report schemas. Their bodies matched the previous generated output. The replacement
invalidated the serving snapshots of earlier workers. Their managed receipts retain the
drain and completed identities (`bf30fdd0217546aeb8727bf7db6df3a4` and
`a6bafcb7e0e34f219ba5fa99a7a7b9f3`). A fresh private run passed all 98 selected report,
contract inspection, contribution delivery and diagnostic controls
(`e0edd69594b44670aa39074a43cbba75`).

**Current main qualification · Tested by selected scope · 2026-11-22.**
Main integrates the registered codec root (`dd9971966`) and regenerated report schema product.
`just turn-end` and `uv run ci check` passed, including types, docs, dependency pins and
Clippy (`6b1970f98ed0481e8489afb6acc12406`). The ordinary retry and lighter cohort were
interrupted and retain their completed identities (`f02c6b33e0d14cd4b77b97c5a3394854`,
`de02b2d9873e4edd9d91884cf761c379`). All six selected actual annotation and canonical
provider cases passed (`267e776231a74518b001f5d387fbb0dd`). The independent characterization
read failed at its 30-minute watchdog in generated Python validation
(`9a40ecca090e424ba4bb0f52a238975f`). Its later isolated corrective draft passed the exact
case and wire/cut controls, with scope recorded under the [handoff owner](validated-values-and-handoff.md#sbx-live-page-handoff).
Real two-language composition and the real construction
that binds two independently produced formal reports both passed in `ecb00e443c4d4e68a867d9f5dafb0352`.
The structural dossier and detached export passed by selected identity in
`1a1f7a3b8abc4d989d0d77f6b678cead`. Its finite and rich replay worker crashed during Python
model preparation; the exact private retry passed (`93e9997f5d61466e9201c87390e15671`).
The second dossier case passed on its private retry (`5a3b93c2ec84469aa8ea086df087f1a6`).
The full event journey remains open following its interrupted retry
(`d274226692ff45f8a015118f50269d8e`). Development readback still identifies the original N29
database.

Keep one authentic cross-boundary producer, publication and export journey. Reader-only checks
can consume its authenticated artifacts while their producer, prepared release, wire and authority
premises remain applicable. Give these checks independent expected meaning, malformed-input and
current-authority controls. A changed producer or publication contract requires affected production
evidence again. The retained finite and rich result `55f6b07f94bb4ff1ab1ea376e9a4dbef`
establishes that attempt's journey and artifact reuse. It supplies neither final-source qualification
nor a general timing claim. This test allocation applies in SBX-11/12 and SBX-20/22.
[Review I09](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I09)

**Former finite replay refusal · Tested by selected identity · 2026-11-22.** The earlier
private fixture fulfilled the candidate producer and left `interpret.finite_candidates` awaiting
inputs before export (`uv run ci test --native-host private`, `20cb15b07fd9491cb263a742723d1871`
and `29ea050ed99640ed8a7bfaa2d29b8824`). Ordinary resume produced zero further receipts. The
diagnostic current native binding projection returned both the computed candidate report and
the authored finite policy while the waiter retained the same binding read and its earlier
candidate-cardinality refusal (`0d4efd2171c64d8ca8e08da153278db3`). The current SBX-06
implementation delivers the late computed candidate to the dependency-free operation. The
successful finite and rich replay above exercises ordinary wake, publication and detached readback.
[Readiness](references-and-projection-keys.md#readiness-delivery)

<a id="early-revision-a-integration"></a>
## Early Revision A integration

Use the installed real annotation-to-canonical chain as the successor journey for SBX-03/05/06/07.
Exercise ordinary admission, execution, publication, settlement and selected readback on the
target partition, proof and role-relative reference contracts. Admit actual producer partitions,
require the declared proof at binding, and resolve an actual construction item through the owning
disclosure boundary. Use this caller for the [conditional SBX-11 keyed slice](owner-resolved-reads.md#sbx-native-read-attribution).
Later reference family conversions consume the same contracts.

Compare with independent expected annotation meaning, occurrence provenance and attachment
identities. Extend the unchanged-pilot fork with the governed changes in the
[shared change](#change-scenarios) and [propagation](#propagation-scenarios) scenarios.
Distinguish the unchanged repeat, an unread edit, and an actual producer attempt whose downstream
projection settles equal. Verify local computation and proof reuse independently from the exact
current attachment. Include missing proof and dangling-address refusals. Retain the actual
prepared contracts, installed descriptor and managed result for applicable reader checks.
[Post-pilot review I01](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I01)

**Entry evidence.** The initial rollback candidate
`4867ee4d101a4c9c86cd2209e2c5cb40` and 36-case result
`a28f4c6e5c8d44328a780193e99d20ce` covered authoring and synthetic partition behavior.

**Implementation checkpoint · 2026-11-21.** The generated N47 successor passed rollback-only
authoring (`c9a513040006422ebcb309693bc15ce5`). The owned source-to-canonical journey installed
the target schema and exercised initial source execution. Target release admission then refused a
shape constraint on an unowned graph class (`8772530274a94525bf9211e712cc4393`). Sentence
partition rows and their carrier now belong to private record products, so their constraints are
enforced by product and partition admission. `uv run ci test --providers-only` then passed the
real CUDA spaCy-to-canonical demand on the owned PostgreSQL target
(`e31433142bf1414ead8712101131dccd`). The proof-requiring canonical role consumed the admitted
annotation partitions. The test read both outputs through selected support disclosure and checked
the literal sentences, projected token offsets, and the role-relative addresses. An unchanged
repeat of the same demand produced zero new receipts. Focused native controls separately refuse a
missing or forged required proof and a dangling partition item
(`85e9b6137e904489b262743b66ceb23c`). Cross-selection reuse and complete family migration
remain separate obligations.

The chain passed again after adding current-use producing input metadata
(`c285558d8dc04e8a9256fe399e655bfb`). The successor candidate for that scope passed rollback-only
authoring against N47 (`27c37c0e9aaa403ebbb53817d6cee671`).
The extended real spaCy, canonical, HanLP and declaration syntax chain verified complete HanLP
output and admitted syntax coverage. The same demand repeated with zero new receipts
(`ce9ecaff99cb4d2c9ce00cfdd29fdc05`).
The extended chain passed again after retiring the annotation packet types and moving the source
witness to the actual block layout path (`b487ae1c0fc340c983cff21339a58c1c`).
The successor with grouped ordinal admission, scoped construction proofs, and clause and condition
references passed preview and rollback-only authoring against N47
(`87857b59d542418f862b1636429cac00`, `345c61ef93b247d09e166540a72d6191`).
Rollback-only authoring after the construction reference and annotation packet changes passed
against N47 (`eafcec5626fc4f11a652f2cc835b8714`). Maintenance readback reported development N29 and
stage N47.
The successor with disclosure-aware support export passed preview and rollback-only authoring
(`1df6637ca17049f492bfbac36b011a44`, `d36ce26f134c4fa3b08001c29f9ee61b`).
The candidate also passed with formal roster and member-address attestations and the new
construction input requirements (`d27bda9ca1db47f7891adf4964bef7a4`,
`6ef50175ca1b4243b1621a6f78cf06c7`).
The successor with the regenerated report schemas and selected rich read authority passed
preview and rollback-only authoring (`e144d0867344411ab6fe1b96eef1c015`,
`31a8c3350bfa478da58f8a4caf3bab85`).

**SBX-03–05 candidate checkpoint · 2026-11-22.** The occurrence, construction proof, native
reference and contextual witness slice passed managed rollback-only authoring
(`uv run ci model change candidate`, `114f6356ffab42c584b84c8470bf62ca`, preview
`b4261c2f46234ed886c4e2b3ae9d3c18`). The accepted preview bound development N29 and the
registered N47 predecessor. The candidate declares the observed five obsolete projection
triggers and two validation routines explicitly. Prior attempts refused the missing retirement
list (`dd633436419e4308927b68c71ac097fc`) and an overlength candidate identifier
(`82097ccf3dd540e98d357b9c107935b1`). This evidence covers the named captured source.
The updated candidate includes admitted definition components, exact applicability and dossier
origins and the scalar contextual graph roles. Preview passed (`bdc5e54bc5b74ed48d2afa6b3ca76d0b`)
and rollback-only authoring passed (`e9dbb5ca18a54b99b038ef688cdc11f5`). The output records
development N29 as the authoring boundary and registered N47 as the candidate predecessor.
Registration and the development reset belong to final-root acceptance.

The combined primary formal set, witnessed relationship and grouped premise changes also passed
preview (`2b8471426f4a4a2989e1fafd9a36d83a`) and rollback-only candidate authoring
(`5ab684b05d734307b343c92a7e808849`). The named predecessor remains N47. The focused
integrated selection passed all 78 native and ordinary cases (`uv run ci test --native-host private`,
`f8bc830c6e92439f9b4619d574d302c3`).

**Projection and activation checkpoint · 2026-11-21.** The partial integrated source at
`2375de39b` passed managed rollback-only authoring against the exact N47 predecessor
(`uv run ci model change candidate`, `359a2c8ce289405cb53ee328fa894b38`). The authoring
database was the dedicated development target at N29. The earlier attempt
(`f93d402290d84b2e89575bb2235725f6`) refused the missing explicit retirement list.
The retry named only the recorded immutability triggers on the five retired projection
families. The result describes the captured source and authoring boundary. Later program
and schema changes require their own candidate comparison.

The next checkpoint at `38c12391d` passed rollback-only candidate authoring with immutable
canonical computation bases and the exact named publication and reconciliation relations
(`uv run ci model change preview` `ec360bd003474cae84c83ad42a6eea0e` and
`uv run ci model change candidate` `e8564e0d615340cdb66544dca5d7492a`).
`uv run ci model change inspect-candidate` confirmed N47 as the predecessor. Maintenance
readback confirmed the stage remains at N47.

The source at `3f413bbac` also passed rollback-only authoring with the native one-hop
recipient routine and its writer grant, the role-relative clause anchor and broader
formal rule consumers (`uv run ci model change preview` `110674f50a8241f59d5f02d2e00e4bae`,
`uv run ci model change candidate` `8db1a135ce6b41c48ada8895b0b00d2e`).
The inspected candidate retained the exact N47 predecessor.

The authorized source-universe routing correction at `fadf20e0f` passed rollback-only
authoring (`uv run ci model change candidate` `d7916674edf74a5d97a9c293f47eb49d`) and
both exact canonical and HanLP provider cases on private PostgreSQL
(`uv run ci test --providers-only` `0828f95372a34af7ab77c094850c6768`).
The exact selected-output validity correction at `ba5a17c10` passed rollback-only
authoring against N47 (`uv run ci model change preview` `e02b3da039824e3d83598f94d8751a46`,
`uv run ci model change candidate` `2b9add969deb46b08cc02aa638337831`).
The same source passed all 13 selected native source-proof, publication, computation-key and
executor controls (`uv run ci test`, `ada90cfedcbe4a878b1e7563c80d4415`).
The live canonical and HanLP cases passed on that source
(`uv run ci test --providers-only`, `cee750ab2b274d66bed4bf20f3ee3cff`).
Maintenance readback reported development N29 and stage N47.

The consolidated CPU and executor selection passed 39 tests (`uv run ci test`,
`8dee86b4b0ba425aaf2b3aa418cae2ac`). Some earlier isolated receipts stopped being
queryable when their worktrees were removed. Current retained results supply new verification
for the covered slices. The 45-case private run `924a287626da4b85b8f4243e181ec265` retained
its failed outcome when a synthetic fixture left temporary source files. Recovery settled
process custody and `uv run ci test coverage` found all 45 selected tests passed. The fixture
lifetime repair passed all five private executor controls with clean teardown
(`6a67b97f41344d459afeed333fd7972d`). The wider fixture run also cleaned up and reported
two executor collaborator failures against fixtures that use the older preparation interface
(`59f7534a27d848d88e07b031de4bb3b9`).

These results establish the early partition, proof and reference path for the tested chain.
The development reset above establishes the fresh SBX-09 baseline. SBX-20 owns stage installation
and SBX-22 owns the assembled required union.
[Review I05](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I05)

**Next early slice · Proposed.** Extend the same annotation-to-canonical chain after the
relevant SBX-03–05 contracts are runnable. On a fresh target, drive a governed commit through native
delivery, current binding and settlement. Check that an unread lexical edit preserves canonical
computation and that a materially changed producer can settle an equal declared output with no
downstream attempt. Contrast the local-geometry case with a moved block whose observed placement
changes the assembled canonical projection. Use native coverage and selected readback for this
slice. Revision B supplies the public freshness read. Establish the publication-to-consumer
stopping behavior before broad propagation adoption. The recorded unchanged repeats exercise
the same frozen demand and leave these change and recovery cases open.
[SBX-06](references-and-projection-keys.md#sbx-06) · [Propagation scenarios](#propagation-scenarios)

## Native revisions

A revision is needed when installed programs, the physical model, privileges or descriptors
change. A change to the model and Python alone needs the release re-prepared, not a revision.
The current generator embeds a global wire digest in wrappers and descriptors, and application
storage checks that digest. Treat this as part of the deployed boundary when authoring and
comparing candidates.

| Revision | Carries | Why together |
|---|---|---|
| A, identity and propagation | Partition table and admission; rule and proof tables, form evaluators, establish routine and required proofs in binding; reference carrier; projection digests in binding and attachment; durable change delivery, readiness and scoped settlement coverage; retirement of the projection family tables, their checks and readers | Land material product and request identity effects once. Carry the native owner of settlement coverage with the transition it governs. |
| B, reads | The outputs, partitions, derivation-facts and proofs programs; the public freshness observation for a governed selection; the support export's relation list and read closure membership | Group read and export changes. Check their producer identity and receipt effects separately from shared wire and descriptor changes. |
| C, PDF | The paged row read for the rebuild; access derivation and the reduced checker; staging without build columns and the adopt program; typed capture reads | Lowering identity and the standard producer contract move once. |

A, B and C are development strands. A and C can be developed independently. B consumes A's
partition and proof contracts. Its freshness slice also consumes A's native settlement coverage.
Other read design can proceed while coverage is under development. Author each candidate against
its exact predecessor snapshot and register the resulting chain in dependency order. Candidate
effects, including shared descriptor admission, determine whether a development strand can be
installed independently.
[Coverage contract](references-and-projection-keys.md#settlement-coverage) ·
[Public read](owner-resolved-reads.md#sbx-11)

Attribute candidate differences to direct SQL or physical changes, shared wire and descriptor
changes, privileges, application admission, and material producer changes. One digest change can
alter otherwise unrelated wrappers. An object diff alone does not establish a need to regenerate
their products. Explain which effects require capture, deployment, admission, or regeneration
through the existing candidate inspection views. Extend those views only if they cannot supply
that answer.

Retain the global digest unless an actual comparison exposes avoidable admission or receipt
invalidation and a narrower contract can independently preserve the required checks. Resolve such
a change through the existing decision route before dependent installation. Compare a read-only
wire change and a material lowering change against their actual predecessors, checking producer
and request identity effects in each case.
[Review I06](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I06)

*Alternative rejected.* A revision per package: each identity-changing package would regenerate
and re-key everything downstream again, and outstanding receipts would be invalidated repeatedly.

<a id="sbx-20"></a>
## SBX-20 — Register the revisions and install stage

Attribute installed effects from the selected [population and analytical routes](common-analytical-basis.md#decision-routes)
and the [replay contract](owner-resolved-reads.md#sbx-12) to the revisions that carry them.
Use the existing exact predecessor, candidate and stage checks for changes to native types,
programs, descriptors, grants or wire contracts.

**Order for fresh qualification inputs.** Start with PDF capture and publication under
revision C, then exercise the operation chains under A in dependency order, each product admitted
with its partitions and proofs. Exercise reads and exports under B. Establish coverage for the
newly governed selection from those facts. A newly selected scope needs an established position
before a current read can report it as settled.

**Checks at each registration.** The repository's native candidate comparison accounts for direct
and shared changes against the exact predecessor. The release prepares under the new kernel,
application admission accepts the intended descriptor, and a fresh target installs from the chain.
Use the existing managed commands to reopen an interrupted transition on the same target. Keep
rollback cleanup and stage receipts within the scope they actually establish.

**Evidence.** For each revision, retain the managed candidate and comparison with attributed
effects, installation on a fresh target, and one run of the smallest
real unit the revision affects (one source view through one chain for A; one selected read and
one export with verification for B; one document's capture, publication, validation and a
recovery for C). Reuse applicable authentic artifacts for reader-only checks under the testing
policy above. Establish same-target interruption recovery for the registered transition. A
rollback-only candidate establishes its captured authoring and validation scope.
Registration, application admission and fresh production results require their own managed
receipts.

For A, retain the registered singleton and the governed successor acceptance established by the
[development cutover](#development-reset-through-sbx-09). Account for the exact stage predecessor
separately. Include a committed change and a native settlement or recoverable pending outcome on
the registered stage chain. For B, exercise the authorized freshness read against A's scope and
coverage, including a pending upstream change and subsequent unchanged settlement. Retain the
separate selected-read and export evidence. Attribute any producer, admission or receipt effects
of the new read wire through the existing predecessor comparison.

<a id="sbx-21"></a>
## SBX-21 — Retirement sweep

Each package removes what it supersedes. SBX-06 retired the recursive watermark and repeated
scheduler scans in source. SBX-21 checks retirement and removes what no single package owns.
Follow the last live production or test consumer of each
retired surface. Migrate independent semantic checks to the replacement before deleting tests
specific to the old mechanism.

- Code with no production caller that the review recorded: `evaluate/record_statistics.py`;
  `evaluate/alignment_preparation.py` and `semantic_values.py` with the parts of
  `semantic_alignment.py` that only they reach; the per-frame identity read; the unused parts of
  `semantic/record_projection.py`, after a reader search at the execution head. The
  `select_pdf_integration` path stays while the streaming reconciliation tests use it as their
  independent check.
- Smaller items: the recognition replay's duplicated sort-key column; the stale duplicate of the
  duckdb hold in `docs/pins.md`; the served-row codec's reference to a disk tier.
- A search, made once and not added to the repository checks, for each retired name: the member
  packet classes, the reference classes, the SQLite read index, the receipt format, the
  projection family tables.
- Design sections and decision records that describe the retired mechanisms are updated in the
  commits that retire them; this package confirms the collection reads true.
- SQLite and JSONL replay controls move to the typed relations in SBX-11/12. SBX-13 keeps
  independent evaluator coordinates and protected-reference controls as duplicate preflight is
  removed. Preserve malformed input, interpretation and current-authority expectations through
  the corresponding replacements.
- Confirm that adopted population and scoped-relations routes removed the repeated preparation,
  conversions and validation they replaced. Follow their worker, publication and selected-reader
  consumers. Confirm the frozen archive no longer rebuilds its covered JSONL/SQLite closure.
  Preserve independent refusal and semantic tests in the respective owners.
- Confirm retirement of covered recursive readiness watermarks, stored wait hashes and repeated
  discovery sweeps after SBX-06 validates their replacement. Follow consumers in the planner,
  execution, demand reads, record grading and retained evidence. Preserve ordinary pinned reads,
  bounded scheduling and waiting-owner reports. Keep any unresolved coverage with SBX-06 until
  its owner migrates. A covered recursive path with a remaining caller is an open retirement
  obligation. [Readiness delivery](references-and-projection-keys.md#readiness-delivery)

**Evidence.** Importing every production module succeeds. The searches find no reference to a
retired name outside history. The documentation check passes.

<a id="sbx-22"></a>
## SBX-22 — Assembled qualification

Qualification establishes that the assembled system works and that the design does what it was
built to do. The assembled campaign runs on final source after the revisions are registered.
Targeted development results and reused authentic artifacts contribute only for their applicable
scope and premises.

**Functional.** The repository's functional and check routes on final source, with results
accounted for by identity as the repository requires. Real providers are exercised where the
changed paths reach them: spaCy and HanLP for the first populations, Docling for the PDF path.
Record managed result identities, selected scope, source and context. Account for the required
union through the existing result facilities. Keep failed and interrupted results, and reassess
affected results when source, harness, environment or shared configuration changes. The final
provider and whole-book claims belong to their actual managed runs.
Apply the applicable [stable-source, preparation reuse and bounded cohort rules](#sbx-efficiency-qualification).

**The whole book.** The retained book is processed end to end through the new path, with a
controlled interruption and an unchanged repeat that produces no new work.

Use the shared [change scenarios](#change-scenarios) throughout implementation and retain their
applicable results for assembled qualification. Derive expected effects from the declarations
and observed checker or consumer boundary before executing a case. Preserve independent
expectations when testing the rule or projection mechanism itself.

On final source, include the adopted population route, the scoped-relations producer through
exact artifact nomination, and live and detached selected structural replay. Reuse independent
expectations from the owning packages. Include interruption and recovery where the chosen
worker or archive lifecycle changes. The historical DuckDB and Arrow fixture results establish
their recorded library behavior. Use managed final-source results for installed qualification.

Qualify the native stopping cases, readiness-only wake, join, supersession, recovery and read
visibility on the registered source and appropriate targets. Keep the textbook MCP closure
timeout as an open structural read obligation under SBX-11/12. Digest-only freshness work and
structural body or replay acquisition establish separate acceptance claims.
[Textbook condition evidence](references-and-projection-keys.md#sbx-05)

<a id="change-scenarios"></a>
### Shared change scenarios

SBX-02 and SBX-06 use this table to select premises before compiling proof and projection
behavior. SBX-03 and SBX-05 supply actual partitions, occurrence acquisition and references.
SBX-07 uses the locality cases to decide host eligibility. SBX-11/12 exercise relation membership,
authority and cache applicability. SBX-20/22 integrate applicable results. The table preserves the
original four scenarios and adds the review's occurrence, population, negative-read and operator
controls. It specifies expected semantic effects rather than a mandatory test per row.
[Review I01–I04](../../plan_improvement_reviews/set-based-execution-after-sbx01_2026-11-21.md#I02)

| Scenario | Expectation |
|---|---|
| A rule's parameter is edited and the release re-prepared | That rule's fingerprint changes and no other. The establish routine evaluates that rule on each partition once. No product id, request key or other proof moves. No operation re-runs. |
| A model field declaration read by one rule and no consumer is edited | The affected rule's fingerprint changes. Consumer projection identities and request keys remain stable, and no operation re-runs. |
| An upstream product changes only in a field group a consumer does not read | The consumer's request key is unchanged and its existing derivation attaches with no new attempt. A consumer that reads the group re-runs. |
| One block of a source document changes, with other blocks independently matched | Its content digest changes and the matched unchanged blocks retain their content digests. An eligible block-local producer runs for that block when SBX-07 is adopted. Proofs whose complete premises remain stable still match. A consumer that observes the changed whole-collection content re-runs. |
| A block moves under a known key or is renamed with independently established correspondence | Content and relative-only premises stay stable. Placement changes on a move. Absolute-position consumers and placement-sensitive proofs observe it. When local projected bytes and effective parameters agree, the canonical memo can hit. Readback resolves the current occurrence, exact attachment and absolute spans. |
| A reference's body-relative span changes within an unchanged text body | Full-text-only keys stay stable. Consumers of the chosen span get a different key because its position in the body changed. Page-coordinate premises stay stable when page placement is unchanged. |
| Unchanged blocks are reordered | The key-sorted content root stays stable. Placement and order commitments change, along with affected adjacency and ordered-read premises. |
| A block is added or removed, including the empty-population boundary | Existing content digests stay stable. Population membership and affected completeness, absence and neighbourhood premises change. |
| A field-group value changes, including omitted versus explicit null | The affected group changes when its declared meaning observes the distinction. Independent consumer and proof identities stay stable. |
| The first matching proof is attached after a negative read | Rule and content identities can stay stable while proof relation membership changes. A reader of absence or completeness obtains current membership on a cache hit, or that read shape is excluded from answer reuse. Current authority is checked for every call. |
| An equal complete material projection is acquired from another source occurrence | Computation reuse follows the declared operation, parameters, execution policy and read projection. Fresh attachment and publication bind exact current inputs, occurrence and project authority. Check request attachment, computation reuse and proof reuse separately. |
| Reconversion renumbers pointers, with repeated text or split and merged blocks as controls | Equal declared projections can permit computation reuse. A specific occurrence correspondence requires independent evidence. Fresh acquisition supplies current occurrence addresses when correspondence is unavailable. Readback follows the current occurrence without guessing a historical mapping. |
| One role-relative body is consumed through different selections and a transitive input from another demand | Interpretation uses original derivation bindings. Current support checks use the selected use's authority. Exercise revoked original support with valid equivalent current support, revoked current support, an attestation lacking an admissible establishment, revocation between live pages, and protected issuer refusal. Detached verification establishes captured custody. |
| The same block is run with different batch peers and order | Compare independently expected bodies, observations and receipts for the actual host and numerical policy. Keep any observed batch determinant in its key. Unsettled locality retains the whole-collection execution premise. |
| A read-only wire change is compared with a material lowering change | Attribute direct and shared candidate changes, then establish actual producer identity, request identity, admission and receipt effects. Regeneration follows material effects and the registered dependency chain. |
| An installed transition or book run is interrupted and resumed unchanged | Reopen through the existing managed route on the same target. Retain completed applicable work, complete required recovery, and establish that an unchanged repeat creates no new computation work. |

Inspect actual keys, binding decisions and attempts alongside independently expected results. For
proofs, include observed order, placement, membership, source and attestation premises as needed
by the checker. For consumers, include only premises read at the declared boundary. A metadata
projection can serve both paths while each hashes its own observations. Prepare or retain an
immutable whole-collection group root only for an actual repeated consumer whose avoided reads
justify its write and retention responsibility.

<a id="propagation-scenarios"></a>
### Propagation scenarios

Use the existing placement, order, membership, pointer, proof and authority scenarios above
through the delivery path. For the additional cases below, assert native decisions, selected
bindings, attempts or receipts and the read outcome as applicable. A small controlled fixture
can distinguish execution paths. Use the actual native boundary for durability and authority.
[Push review I01–I04](../../plan_improvement_reviews/set-based-execution-push-propagation_2026-11-21.md#I01)

| Scenario | Independent expectation |
|---|---|
| Register unrelated original bytes, then explicitly replace the evidence for a named selection | Registration leaves the existing selection's computation and coverage alone. Replacement affects the selected scope and preserves previously frozen demands. A newly acquired all-inventory selection can observe its own membership change. |
| Add or remove the first eligible population member, including return to empty; route a change to parallel roles that observe different fields | Declared selectors wake the affected bindings even when there was no prior selected address. Role identity and observed field groups determine which computations change. Confirm closure and distinguish an authorized empty result from unresolved coverage. |
| Activate a release with a material producer edit and a descriptive edit | The material determinant puts its operation in scope. The descriptive edit preserves computation identity. Eligibility edits can affect binding or discovery. An activation alone leaves the release pinned by an existing frozen demand intact. |
| Change an unread annotation field, then separately change the producer recipe and settle equal canonical input projections | An unread field leaves the consumer computation reusable. The material recipe change creates a producer attempt. Equal declared output projection creates no downstream attempt once the owner settles it. Compare with a changed observed span or placement, and verify the exact current attachment independently. |
| Publish another usable episode for the same exact pinned product; exercise late discovery, original admission, proof establishment and support revocation | An unrelated episode leaves the waiter waiting. Applicable support can wake the exact waiter with a stable computational digest. Native binding establishes its decision and revocation can refuse unchanged content. Revisit settled work and check that a covered request avoids the recursive watermark scan. |
| Settle a same-generation diamond with a changed and an unchanged arm, then with one unavailable arm | The join sees both current arms before comparing its combined key. The unchanged arm contributes settlement without another downstream provider attempt. An unavailable arm leaves the dependent scope unavailable or uncovered under its declared contract. An independently covered scope stays available. |
| Overlap publication and enrollment in both commit orders, including a gap after both commit | Ordinary resume or drain finds exact committed fulfillment and delivers once to the enrolled current generation. Repeat resume to verify idempotence. A stale generation cannot advance current coverage. |
| Re-admit a discovery witness under the same semantic key after its exact prior support is revoked | A historical closure cannot hide the newly admissible exact use. Exercise incomplete, valid complete-empty, first member, and loss of the last eligible witness. Verify exact closure and affected recipients independently. |
| Supersede a selection during execution; lose acknowledgement after a native commit | A late valid publication retains its historical meaning but cannot advance the superseding selection. Replay recovers committed change delivery and settles it without duplicate attempts or publication. |
| Pause delivery between edges after the upstream commit, while the immediate read target has no queued work | The authorized freshness-aware read reports pending for the affected scope, the pinned read retains its selected cut subject to current authority, and an independently covered scope stays available. After unchanged settlement, the governed scope advances without a new provider attempt. Check unavailable or unknown where coverage cannot be established, and confirm digest acquisition stays body-free alongside explicit body and export requests. |

**The point check.** A partition-local rule and a single addressed-item lookup each decode at
most one body. Acquire needed metadata and authority through scoped keys. A rule that observes
multiple partitions follows its declared scope. Assert decodes or examined rows where needed to
establish the intended bound. Preserve the full required closure for genuine replay.

**Benefit claims.** Timing and capacity statements require measurements with their conditions.
Functional scenarios can establish avoided operations, evaluations and decodes. Qualitative
execution-fit reasoning is sufficient for expected gains unless a consequential uncertainty needs
a comparison.

After retiring scheduler state from shared reads, recheck the pinned public result and grading's
exact obligations, uses and completion against the same cut. Run authentic detached export and
replay. A previously sealed page keeps its original reader schema and byte identity.
[Post-pilot review I04](../../plan_improvement_reviews/set-based-execution-through-sbx09_2026-11-22.md#I04)

**Completion.** The series is complete when the evidence above is recorded, the kernel trial's
decision is recorded, and the owning design sections and decision records describe the
implemented state.
