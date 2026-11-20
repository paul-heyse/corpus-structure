# UDM-20 bounded regional confirmation

**Bounded observations complete, 2026-11-19.** The assigned target is the dedicated stage, database
`corpus_structure_ddo_stage`, OID `130661481`, PostgreSQL 18/corpus on port 5434.
The inquiry observes regional settlement, actual composition and recovery without project activation.

The retained original is the 518-page Grinstead and Snell probability book,
`doc:38d5d93379c3320aa88457511d38fc25`, SHA-256
`763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.
`prepare_excerpts.py` authenticates that content and copies exact physical pages.
It does not recapture the whole book. The independent excerpt originals retain
their original document, hash, physical page range and historical group pointer
in `excerpt-descriptors.json`.

| Case | Original pages | Historical group | Retained selected source records |
|---|---|---|---|
| Largest failed region by pages | 413–478 | `#/groups/614` | 1,038 |
| Failed region with most source records | 233–292 | `#/groups/489` | 1,105 |
| Successful historical control | 479–506 | `#/groups/653` | 488 |

These record counts describe the retained original capture's selection. A new
capture over an excerpt may produce different section boundaries and source
records. Annotation member counts also include roles other than sentences, so a
raw total of manifest members is not a sentence count.

The regional requests select only `segment.sentences/source-native`, standard
Docling capture, organized source discovery, and the declared spaCy profile. They
exclude Chandra and Nemotron. The full statistics Standard release is admitted
through `prepare_standard_release.py`, retaining all declaration and kind
contracts needed by this populated stage. `raw/standard-release.json` identifies
the admitted source and runtime. The project generation stays zero and there is
no project activation.

`run_regional.py` scopes PostgreSQL nested-statement diagnostics to the stage
writer role, samples live query and blocker state, captures that database's log
records, and restores its exact prior absence of overrides in `finally`. It uses
one provider job and a 16 GiB owned-byte bound, with a 40-minute wall ceiling for
each bounded excerpt. Every managed outcome, including failures, remains in the
managed result store.

The first control attempt, `5dc458c9a68d4c1da60fffb614cbdc4c`, failed during
execution preparation because the supplied source root was the repository root.
The explicit source root was corrected to `python/corpus-structure/src`. The
second control attempt, `38b201ed42b64cdb8f8c3974985b0dde`, correctly refused
stale captured factory bytes after concurrent source integration moved imports
from `data_operation_identity` to `data_operation_values`. Both failures happened
before inference, established cleanup, and restored all diagnostic overrides.
The Standard application is recaptured against the stable main source rather
than weakening source custody.

Subsequent attempt `99f112174d534c2585fe36949e22c9e9` performed and durably
published the actual Docling capture, then detected a concurrent change to
`semantic/code_identity.py` before organization. Exact managed recovery
`a725a0505d5a455a8fd7f78386805186` reused that capture and correctly refused
the stale sentence parser/runtime custody. The app was prepared again against
the settled source, then acquired through an immutable source copy.

`raw/frozen-runtime.zip` and its per-file inventory retain that source and the
exact N35 migration contracts. A private environment overlay keeps installed
third-party packages while independently installing the three frozen workspace
editables. An isolated `python -I` imports the frozen package, and the exact
locked offline environment check passed. The shared environment was untouched.
`verify_frozen_runtime.py` checks every captured factory path/content plus the
exact sentence profile and execution assets. The initial source-only archive
omitted `target_alembic`; result `ba0edfae47054d2e8e4463bdf3744843` validly
refused native deployment admission before inference. The missing immutable
contracts were added to the archive.

Actual attempt `b0188cdd562147adb80e2a7ea09b09d7` completed capture and source
organization/discovery, then refused the stale declared tokenizer runtime. The
isolated installed distribution RECORD inventory differs from the retained old
profile. `refresh_sentence_runtime.py` acquires that actual environment into the
existing sentence runtime transport contract, proves its inference identity is
unchanged, and admits a new exact runtime without changing the release. Its
receipt is `raw/sentence-runtime-refresh.json`.

The final successful-control attempt `4933fc555e14453394770dbdbccf4007`
**passed on 2026-11-19**, using release `0f6352f5…` and runtime `7e33fb14…`.
It ran actual Docling and spaCy, retained native publication receipts, established
cleanup, and restored all diagnostic overrides. Total observed wall time was
538.012 seconds, including preparation, capture, inference and native settlement.
The two sentence products contain 676 native sentence members, 8,918 native token
members, 440 native block members and two source-annotation manifests. These are
separately typed counts, rather than an undifferentiated member total. The largest
sentence completion intent is 35,127,356 bytes as JSONB text, including a
23,241,498-byte main body. `raw/active-control-intents.json` and
`raw/successful-control-member-counts.json` retain the bounded native census.

Nested PostgreSQL observations isolate meaningful settlement cost without lock
blocking. One `publish_data_derivation` call took 66.266 seconds; nested work
included repeated `ddo_normalize` and `canonical_json`, with a 17.26-second
canonicalization and a 20.54-second body identity calculation. The 120-second
actual completion deadline was unchanged. This observation concerns the tested
28-page excerpt, rather than a whole-book performance estimate.

The rollback-only `canonical_json_probe.py` compares the existing function with
whitespace compaction that preserves complete quoted strings. The retained
23,241,498-byte body contains no JSON objects, so existing JSONB text already
supplies the same scalar encoding and array order. Both paths produced
21,875,525 bytes with the same SHA-256, `136bafe6391ec099e94a357da17ac44e745f5ef3cfffa48bc64538966817b629`.
Independent controls cover escaped quotes, backslashes, whitespace within
strings, Unicode, nested arrays, scalars and object-bearing inputs. Objects need
the existing ordered-object path. The paired length-and-digest projection took
32.958 seconds through current recursion and 2.198 seconds through compaction.
These timings describe this bounded comparison during another capture; they are
not a general benchmark. No installed function was changed.

The observed repeated capture across runtime bindings has an explicit current
guard. The capture implementation slice is complete, but
`pdf-capture/profile-assets.reuse_eligible` is false because
`pdf_lowering.lowering_code_complete()` remains false. Native request attachment
therefore requires an `execution_scope` equal to the demand ID. A changed runtime
created a new demand and a distinct guarded request even with the same recipe.
This is incomplete material identity, rather than evidence of a whole-runtime
eligibility filter. The guard remains intact. Same-demand recovery retained the
durably published capture.

The separate `binding_probe.py` uses the actual production compiler and N35
server over independently authored relational rows in a rollback-only
transaction. It is a binder experiment, with no provider or whole-book
composition claim. Before the repair, eight independent required roles generated
a Cartesian relation. Two input rows per role took 5.063 ms, four took
982.714 ms, and eight reached the explicit 30-second statement timeout. A missing
required role also erased the available peer-role members. The repaired compiler
keeps independent role populations separate and retains the missing role's
unavailability. `raw/role-binding-before.json` and the saved SQL retain the
bounded failure. `raw/role-binding.json` retains the repaired plans and exact
results. Every authored database row was rolled back.

The binding execution deadline now uses an owned savepoint and bounded statement
and lock settings, preserving stricter caller bounds and restoring caller
settings. Native tests exercised actual PostgreSQL cancellation and subsequent
transaction usability. Managed result `dc553ecfd39c4285b5a6b0c4e304ca70` passed
84 targeted binding, deadline and primary-operation tests. Result
`e93e97e932d943c680eab86f6f9b6083` passed typing. These receipts belong to the
isolated implementation worktree and are integrated by the coordinator.

The earlier `stage_composition.py` source-only experiment failed at admission
because a narrow core recipe conflicts with this stage's already admitted
statistics kind contracts. `raw/stage-composition.json` preserves that valid
refusal and confirms diagnostic restoration. It establishes no composition or
provider outcome. The full statistics Standard release supplies the appropriate
current route for the remaining actual composition observation.

The 66-page original region then reproduced the historical intake failure on
N35. Managed result `0bb1f7e9a9b245b8b7ec4b15c8933096` **failed on
2026-11-19** with SQLSTATE `57014` at the unchanged 120-second completion
statement bound. The stack locates the cancellation inside
`canonical_json` / `ddo_digest`, at the retain-intent assignment. The run took
729.634 seconds, including genuine capture and spaCy. Its diagnostic settings
were restored and resources drained. The saved N35 log and observation have the
`n35-failed-largest-failed-pages-` prefix.

The private acknowledged answer is 92,292,593 bytes with request SHA-256
`b34d5a3756b869f30207964d8b543337778a7f53cba62811f02fdca8f4143bb9`.
`largest-failed-private-draft.json` retains the actual draft identity, original
producer fence and runtime digests. Production draft opening and native
origin/fence comparison succeeded. A diagnostic assumption that pending tasks
must erase `claimed_by` was incorrect; the native task retains that history with
`lease_until = NULL`. Independent reads found zero retained intents and zero
draft consumptions after the known SQL cancellation. Native adoption was not
inferred from local custody.

The coordinator separately authored, registered and deployed the bounded N36
canonicalization repair. Its four exact generated files were supplied through
`native-n36-contract-overlay.json`. Exact managed recovery
`8c64955052214e73b71827fa48132f78` validly refused the N35 application before
inference because its release facts need current authenticated re-lowering.
The accepted plan requires a newly prepared application after this kernel
change. The current-versus-producing material comparison also shows changed
implementation and support contracts, with both definitions reuse-ineligible.
The old answer stays held and its guards are preserved. No 66-page provider
rerun was started after that refusal.

Fresh N36 application preparation exposed two callable-owner omissions before
any provider execution. The selected preflight acquired nine ports, while
canonical projection omitted the exact `data_operation_ports` callable source,
and HanLP omitted `methods.native_evidence` and `methods.pm2_hanlp_products`.
The source-subset guard correctly refused these cases. The earlier managed
one-page attempt `e081ef271b3942b983586e220fbc34d1` attributed the failure to
the capture obligation, while its structured frames correctly identify eager
downstream canonical preparation. The exact baseline preflight and failed
attempt are preserved under `n36-before-callable-owner-repairs-`.

The coordinator repaired the source collections, keeping the guard, and the
separate frozen source at commit `64187fb64` now admits release `33f357ab…`
with runtime `88739590…`. Exact native readback and all eleven selected prepared
ports **passed on 2026-11-19**, without claiming work, declaring GPU hosts or
performing inference. `n36-corrected-source.zip` retains the current package,
acquisition inputs and new N36 contract files; its inventory explains reuse of
the unchanged predecessor contracts from the original source archive. Installed
provider runtimes and actual artifact custody were freshly acquired in the
private workspace, with no change to the shared environment.

The full-family positive uses an independently authored, real one-page PDF with
two simple sentences. Its 1,047 exact bytes are retained in
`raw/originals/complete-family-prose.pdf` and independently extracted text was
checked before registration. This keeps the compositor/provider check bounded
and gives every analytical family a genuine small source.

Actual managed result `bc94c35adc3e438b8e4eb771d4ccb155` **passed on
2026-11-19**, in 381.875 seconds on the corrected N36 application. All eleven
native obligations fulfilled: capture, organization, discovery, sentence
annotation, canonical projection, HanLP, formal evidence, constructions,
declaration syntax, contextual evaluation and organized full composition. The
resulting `full_characterization` product retains one exact source coordinate
and seven characterization product references. Cleanup was established and all
diagnostic role overrides were removed. No project activation occurred.
`raw/n36-full-family-fates.json` and `raw/n36-full-family-view.json` retain those
independent native readbacks. The coordinator's live watcher also observed an
interim compositor `not-applicable` fate with only `binding-covers` reasons,
then its eventual fulfilled fate after the required family products settled.
That is an actual native incomplete-family observation; it does not isolate a
single withheld region in a multi-region population.

The separate 60-page contrast remains the exact physical pages 233–292 from
the original largest-by-record-count failure. Actual managed
result `f3bb4c777c2d42aa8acc0b8567e8b44b` **passed on 2026-11-19** in
755.959 seconds, using the same immutable corrected N36 application and
unchanged bounds. All five obligations fulfilled, including two sentence
products containing 1,924 native sentences, 23,013 native tokens, 1,128 blocks
and two source-annotation manifests. The larger retained intent is 91,103,526
bytes as JSONB text. Direct large intake took 60.616 seconds and publication
85.033 seconds; both stayed inside the unchanged 120-second statement bound.
These are observations for this contrast, not a same-input speed comparison
against the distinct 66-page N35 failure. The native fates, typed counts and
phase observations are retained in the `raw/n36-contrast-` files.

`raw/final-stage-restoration.json` confirms zero live stage leases, no writer
diagnostic overrides and all four regional projects unactivated at generation
zero after the runs. GPU provider resources drained; only the pre-existing
Sunshine desktop process remained. No 66-page producer rerun or old-draft
adoption was performed after the kernel cutover refusal. The original
acknowledged answer remains held. The coordinator separately owns the actual
independently authored two-region native fixture test for deliberately withheld
producer-family coverage and the installed CLI recovery/repetition checks.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 10 current, 0 superseded.


**Other**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Actual object-free body canonical-byte parity](records/udm20.canonical-json-parity.json) | UDM-20 | passed | UDM-20, UDM-23 | 2026-11-19 |
| [Required canonical callable source subset refusal](records/udm20.canonical-source-subset.json) | UDM-20 | failed | UDM-20, UDM-23 | 2026-11-19 |
| [Required HanLP callable source subset refusal](records/udm20.hanlp-source-subset.json) | UDM-20 | failed | UDM-20, UDM-23 | 2026-11-19 |
| [Actual bounded N36 complete-family composition](records/udm20.n36-full-family.json) | UDM-20 | passed | UDM-20, UDM-23 | 2026-11-19 |
| [Actual 60-page N36 regional settlement contrast](records/udm20.n36-regional-contrast.json) | UDM-20 | passed | UDM-20, UDM-23 | 2026-11-19 |
| [Installed N36 digest of the original 66-page completion request](records/udm20.n36-retained-digest.json) | UDM-20 | passed | UDM-20, UDM-23 | 2026-11-19 |
| [Exact old application refused after N36 cut](records/udm20.n36-stale-release-refusal.json) | UDM-20 | blocked | UDM-20, UDM-23 | 2026-11-19 |
| [Bounded independent-role binding and restored deadlines](records/udm20.regional-binding.json) | UDM-20 | passed | UDM-20, UDM-23 | 2026-11-19 |
| [Actual 66-page N35 intake cancellation](records/udm20.regional-largest-n35.json) | UDM-20 | failed | UDM-20, UDM-23 | 2026-11-19 |
| [Exact managed repeat of the N36 full-family stage demand](records/udm20.n36-managed-repeat.json) | UDM-26 | passed | UDM-26, UDM-23 | 2026-11-19 |
<!-- evidence-index:end -->
