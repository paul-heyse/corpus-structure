# Controlled boundaries and production seams

**Status:** Proposed design companion; not started. The
[coordinator](../test-domain-model-and-execution_2026-11-17.md) owns the series' combined target,
the package queue, package state, finding dispositions, shared contracts, rejected options and
handovers. **Created:** 2026-11-17. **Revised:** 2026-11-18. Writing this plan authorizes no
implementation.

This companion owns the detailed design of four packages:

- **TDM-09**, the production function that owns the PDF stream protocol (seam 1), completed on
  top of the emitter the conversion delivered, the one controlled converter built on it, and the
  removal of every hand-written preparation entry and copy of request assembly
  ([DTA-041](../../design_review/test-audit/support-structure.md#dta-041));
- **TDM-10**, the demand executor's native-I/O collaborator (seam 2) and the move of its tests
  to the public constructor ([DTA-043](../../design_review/test-audit/support-structure.md#dta-043)),
  with the claim double of DTA-034 and the `controlled_executor` case of DTA-009;
- **TDM-11**, the public comparison of a native host's startup profile (seam 3), its per-field
  evidence and the removal of an invented refusal
  ([DTA-045](../../design_review/test-audit/evidence-and-discrimination.md#dta-045));
- **TDM-12**, the remaining substitutes: wire-checked, owned by support modules, and an encoder
  fake whose output identifies its input
  ([DTA-034](../../design_review/test-audit/support-structure.md#dta-034),
  [DTA-046](../../design_review/test-audit/evidence-and-discrimination.md#dta-046),
  [DTA-009](../../design_review/test-audit/support-structure.md#dta-009)).

**Baseline and evidence.** Section references such as §4.3 mean the
[source review](../../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md),
which read source at `1afa63f88`. The series was authored at `50827eb9f` and revised at
`12f57dc4d`, 2026-11-18, after the model-owned SQL conversion
([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)) was complete and while its
validation was running. Every design statement here is **Proposed**. Every statement about current
source was re-read at `12f57dc4d` and is **Interface-checked by source inspection, 2026-11-18**,
with line citations as of that commit; the one fact not re-read is marked and keeps its
2026-11-17 label. Nothing was run: where the text says a test cannot set up or pass, that is by
reading, not run. No speed claim is made. The investigation reports this companion draws on are
in the evidence folder `docs/design_review/evidence/2026-11-17_test-plan-authoring/`, chiefly the
[seam advice](../../design_review/evidence/2026-11-17_test-plan-authoring/seams.md), the
[current-state map](../../design_review/evidence/2026-11-17_test-plan-authoring/state.md) and, for
the revision, the
[boundaries re-baseline](../../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-boundaries.md).
`tests/…` and `src/…` are relative to `python/corpus-structure/`; root paths are written as root
`scripts/…`.

**Two local terms.** A **seam** is a place in production code where one collaborator can be
replaced through a public parameter or function, so that a test replaces that collaborator and
nothing else. A **contract control** is one test that sends the same authored input through a
double and through the real boundary and compares what each produced. All other shared terms are
the coordinator's [shared contracts](../test-domain-model-and-execution_2026-11-17.md#shared-contracts).

## Why this work exists

A test that needs a PDF converted, a database claimed or a model started cannot run the real
thing in the ordinary lanes: the real converter needs model assets and a child process, the real
executor needs PostgreSQL, and the real host needs a GPU. Each such test therefore replaces
something. The review's finding across these four packages is that the tests replace too much,
and that what they replace is restated by hand.

Nine converter doubles each rebuild the stream request and write a preparation entry that is
not a preparation report. One executor double assigns
about eighteen private attributes on an object that never ran its constructor, and copies the
formula it is supposed to test. One host double refuses for a reason production does not have.
A read-result page that eleven modules share has never been checked against the wire type it
imitates. In every case a protocol or rule lives in production, and a second, drifting copy
lives in a test.

The operator decided on 2026-11-17 that three production seams are in scope. That changes the
remedy from the review's §4.3. The review designed test-side owners that would delegate to a
production function "when it exists". This plan creates those production functions, so the
test-side owner has nothing to restate: it supplies the external computation's output and
production does the rest.

**What this companion consumes.** The production emitter the conversion delivered
(`StreamingPdfResult.certified_reply`); TDM-00's re-read of changes after `12f57dc4d`; TDM-07's
bounded memo of prepared kernels, which TDM-10 uses; and the model-binding rule from TDM-02,
which governs how each acceptance expectation below is authored.

**What it produces.** Three production seams with their production callers migrated; one
controlled converter whose content is recipe data, which TDM-08's seed builder consumes; a
declared field set for the host profile comparison, which TDM-13's perturbation-table contract
consumes; and an extended wire-checked storage double that TDM-12 reuses.

**Where its responsibility ends.** No other production change is in scope. This companion does
not decide where the capture workspace is bound (that is TDM-07 and TDM-08, and behind them a
production owner's decision). It does not own the general contract of a perturbation table
(TDM-13) or the refusal contract (TDM-14). It does not move tests off hand-built substitute
schemas (DTA-034's fourth item, which is DTA-047 and belongs to TDM-16).

## The common shape of a controlled boundary

The coordinator's contract *controlled boundary* gives the shape every package here follows: the
double replaces one external computation, its output carries the identity of its input, the
boundary has one support owner, and one contract control compares it with the real boundary.

Two existing doubles already have this shape and are the model for the rest. `WireCheckedStorage`
(`tests/semantic/data_operation_binding_support.py:240–262`) subclasses the generated
`DataOperationCalls` and validates every call's input and reply with production's
`validate_native_wire`. The host peer (`tests/methods/native_host_cases.py`) is a real process
that speaks the real protocol and replaces only the model inside it.

A contract control has a limit that every package below respects: it can show that the double
and the real route agree, but it cannot find a defect in code that both routes share. Each seam
therefore also has direct cases against the seam itself, with expectations written by hand.

---

## TDM-09 — The PDF stream protocol and the controlled converter

### Baseline

**Delivered by the conversion.** Two commits changed where this package starts. `1d22c41cb`
moved the seven five-field converter doubles onto a certifying helper. `8a5c074f0` added a
production emitter, `StreamingPdfResult.certified_reply(request, *, on_replay)`
(`src/corpus_structure/ingest/pdf_streaming.py:573–603`), and deleted the fixture-only occurrence
writer `write_native_occurrence_batches`, which now has no reference in `src/` or `tests/`. The
emitter takes a finished result, writes the record batches, acknowledges the completion entry,
calls `certify_native_stream` and returns the nine-field `PdfStreamReply`. It has exactly three
callers: the worker child (`src/corpus_structure/ingest/pdf_worker.py:105`) and two test helpers,
`certify_controlled_pdf_stream` (`tests/pdf_acceptance_support.py:34–71`) and
`_certified_controlled_reply` (`tests/semantic/current_pdf_source_support.py:198–209`). All nine
controlled converter doubles reach it through one of those helpers, so every controlled reply now
passes production encoding and certification, and by reading, not run, their consumers set up.
This package therefore no longer restores setup, replaces five-field replies or deletes the
writer. What remains is the half of the protocol before conversion, which tests still restate,
and the form of the controlled content.

**The first half of the protocol is still inline in the worker child.** When the child receives a
stream request, `_native_child` (`pdf_worker.py:88–106`) prepares the payload family from
`request.payload_schema`, builds a `PdfStreamSpool` over the request's spool root with the
acknowledgement callback and the recovery pages, runs `StreamingPdfProducer.run`, and only then
calls `certified_reply`. No function owns that sequence, so it is not callable without a
connection and a child process.

**Preparation is acknowledged before conversion, inside the producer.** `StreamingPdfProducer.run`
(`pdf_streaming.py:612–659`) writes `native-preparation.json` from the converter's preparation
report, derives an identity from it, refuses if the spool's recovered pages were produced under a
different identity, and acknowledges the entry (`:626–637`). Only then does it call the
converter. Resuming a spool depends on that order, because recovery derives page identity from
the preparation entry (`src/corpus_structure/ingest/pdf_build_spool.py:304–312`). This is why the
emitter the conversion added cannot own the whole protocol: it receives a finished result, and
the first acknowledged step happens before there is one.

**The reply's options and the preparation file are the same bytes in production.** Both come
from `converter.prepared_options_report` (`pdf_streaming.py:628`, `:654`). The result carries them
as its `effective_options` field (`:386`), which the emitter reads (`:558`, `:599`).

**The controlled path writes its preparation entry by hand, and the entry is not a preparation
report.** Both test helpers write the result's `effective_options` as the preparation entry
before calling the emitter (`pdf_acceptance_support.py:64–69`,
`current_pdf_source_support.py:202–208`). Those bytes are `b'{"fixture":"controlled-source-search"}'`
(`current_pdf_source_support.py:251`), `b'{"fixture":"controlled-source-search-sections"}'`
(`:440`), or the dataclass default `b"{}"` for the seven former five-field doubles, which
construct the result from six positional arguments. A third site, the child double in
`tests/orchestrate/test_pdf_private_execution.py:144–178`, writes `b'{"fixture":"prepared-native"}'`.
None is a report production would accept: `native_preparation_identity`
(`pdf_build_spool.py:211–216`) reads a `_preparation` key. The identity is computed only when a
spool is resumed (`:304–312`, and `verify_spool_recovery`, `:423`), so the defect is silent until
a controlled path recovers. The controlled spools are also built without the acknowledgement
callback, the request's payload family or its recovery pages
(`PdfStreamSpool(spool_root, check_active=…)`, `current_pdf_source_support.py:246`, `:435`).

**Request assembly is copied.** `PdfWorker.stream` takes ten keywords and builds the
`PdfStreamRequest` itself (`pdf_worker.py:253–268`); its one production caller is
`src/corpus_structure/orchestrate/pdf_streaming.py:421–433`. Because every double replaces
`stream`, each receives the keywords and rebuilds the request: `certify_controlled_pdf_stream`
(`pdf_acceptance_support.py:52–63`), `_controlled_stream` (`current_pdf_source_support.py:255`)
and `_section_stream` (`:444`). The first of these is new since the authoring baseline and is the
most widely shared copy: 23 test files import its module.

**Tests import the producer's private helpers.** `_atomic_bytes` is imported at
`pdf_acceptance_support.py:50`, `current_pdf_source_support.py:200` and
`test_pdf_private_execution.py:144`, which also imports `_ref`.
`tests/semantic/test_pdf_shared_streams.py:449` imports `_ref` to build one reference for a
replay-batch reader.

**The controlled content is a function installed with `monkeypatch`.** Nine doubles exist. Seven
call `certify_controlled_pdf_stream`: `tests/semantic/current_pdf_integration_support.py:286–302`,
`current_artifact_support.py:120–135`, `rich_domain_native_support.py:132–146` (and
`decimal_source_stream`, `:93`), `tests/evaluate/declared_record_native_support.py:191–243`,
`tests/semantic/test_pdf_materialization_native.py:60–79`,
`test_pdf_transform_demand_native.py:90–170` and `test_nce02_native_scope.py:231–245`. Two call
`_certified_controlled_reply`: `_controlled_stream` (`current_pdf_source_support.py:212`) and
`_section_stream` (`:388`). Each authors its document inside a function that closes over its rows,
and each is installed by `monkeypatch.setattr(pdf_worker.PdfWorker, "stream", …)` or passed as
`stream=` to the source factory, which takes the `monkeypatch` fixture
(`current_pdf_source_support.py:270–292`). A function cannot enter a recipe's identity, and a seed
builder has no `monkeypatch`. The support modules among the nine are imported by about 70 test
modules (source 43, integration 8, artifact 2, rich 3, declared-record 14).

**One direct caller of a helper is broken.** `tests/semantic/test_current_pdf_source_inputs.py:58–68`
is unchanged. It calls `_section_stream` without the `validation_contract`, `lowering_identity`
and `payload_schema` keywords that the helper reads (`current_pdf_source_support.py:450–452`). By
reading, not run, it raises `KeyError` before its first assertion.

**The real-child control exists; no contract control does.**
`tests/orchestrate/test_pdf_streaming_integration.py:21–95` replaces only Docling's
`DocumentConverter` with a scripted provider inside the real child, so application preparation,
the spool, the pipe exchange and certification are all real (the test starts at `:106`). The same
module shows the scripted provider running in-process without model assets (`:212`). The provider
reaches into Docling internals (it builds a pipeline with `object.__new__`, `:28` and `:33`, and
calls `_release_page_resources`, `:66`), which is a reason to keep it in one place. Nothing
compares the controlled route with the real child.

### Target design

**One production function owns the sequence, and `certified_reply` is its last step.** It takes
the stream request, a producer and the acknowledgement callback, and returns the reply. It does
four things in order.

1. It prepares the payload family from `request.payload_schema` and builds the spool from the
   request, including its recovery pages.
2. It asks the producer for its preparation report, checks the report with
   `native_preparation_identity` (which refuses a malformed one), writes it atomically, refuses
   if the recovered pages carry a different identity, and acknowledges the entry.
3. It asks the producer to convert. The producer returns the document, the conversion status,
   the errors and the formula outcomes, and may acknowledge pages through the spool while it
   runs.
4. It emits the reply through the existing `certified_reply`, handing it the report from step 2.
   The reply's `effective_options` is that report and is never a separate value.

**The producer is a two-step protocol.** A producer supplies its recipe bytes, a preparation
step that returns the report, and a conversion step. The only production implementation is
`StreamingPdfProducer`, whose `run` is split at the point where it acknowledges preparation
today. The exact signatures are the implementer's; what is fixed is that preparation returns
before conversion starts and that the function, not the producer, writes and acknowledges the
report.

One small correction belongs to the same change because it removes the remaining way a second
party can disagree with the function. `StreamingPdfResult` stops carrying its own
`effective_options` field (`pdf_streaming.py:386`), since the report now has one holder; a test
can then no longer choose the preparation bytes by constructing a result. The other correction
the authoring baseline listed, a completion reference recomputed in a second module, was
delivered by `8a5c074f0`: the writer and the reference are now in one class (`:535`, `:589`).

**The process boundary stays entirely outside the function.** The function knows nothing about
pipes. It receives the acknowledgement as a callback.

- In the child, the callback is today's exchange: send `PdfReplayReady`, wait for `True`
  (`pdf_worker.py:90–93`). `_native_child`'s stream branch reduces to one call.
- In the parent, `PdfWorker._exchange` (`pdf_worker.py:178–238`) is unchanged: it verifies each
  replay, checks the reply type and stops the child on a result that is not a success.
- `PdfWorker.stream` takes a `PdfStreamRequest` instead of ten keywords. Its single production
  caller (`orchestrate/pdf_streaming.py:421–433`) already holds every field. This is what stops a
  test double from restating how a request is assembled.

**The controlled converter is a producer plus a replacement for `PdfWorker.stream`.** The
replacement receives the request the parent built and the parent's own callback, and calls the
production function in the same process with a controlled producer. It builds no request, no
spool and no reply. The controlled producer supplies three things: the authored document with
its status, errors and formula outcomes; the recipe bytes of the worker it stands in for; and a
preparation report.

**The preparation report comes from production.** The support owner obtains it by running the
production producer's preparation step once, in-process, with the scripted Docling provider, and
keeps the bytes. The report is then valid by construction and equal to the contract control's
report in every field that determines identity. The report includes the asset path
(`artifacts_path`, which `native_preparation_identity` excludes from identity,
`pdf_build_spool.py:230–233`), so the kept bytes depend on a location. Under the coordinator's
rule for anything that depends on a binding, the memo is keyed by the recipe and the asset
binding together. A hand-written report is the fallback if in-process preparation proves
unworkable; it is legal because the function's identity check refuses a malformed one, but it
restates an eight-key shape and would drift, so it is a fallback and not the design.

**The controlled converter acknowledges no pages.** That is today's behaviour of every double. A
consumer that needs page, candidate-payload or raster custody uses the real child with the
scripted provider.

**What the parent still verifies, for both routes.** Because the replacement passes the parent's
own callback, none of these checks is bypassed: the family allow-list and confinement of each
replay to the spool root (`orchestrate/pdf_streaming.py:339–360`, `pdf_build_spool.py:704–731`);
`spool.complete`, which requires exactly one preparation and one completion entry, a recipe
digest equal to the build's premises and every replay of the reply acknowledged
(`pdf_build_spool.py:741–788`); the presence, verification, kind and lowering identity of the
certification (`orchestrate/pdf_streaming.py:457–476`); verification again at adoption
(`:378–382`); and, on recovery, the completion header and the preparation identity
(`pdf_build_spool.py:347–406`, `:304–312`). The in-process route skips only the pipe loop in
`_exchange`, which the real-child tests cover.

### The contract with TDM-08: content is recipe data

TDM-08 seals a seed after a completed capture. Its builder runs outside any test, so it has no
`monkeypatch` fixture, and the scenario's identity is its recipe. Three requirements follow, and
TDM-09 delivers them. The conversion delivered none of them: certifying the doubles left their
content and installation as they were.

1. **The controlled converter's content is a value, not a function.** Today a consumer chooses
   its document by passing a function (`stream=…`, defaulted at
   `tests/semantic/current_pdf_source_support.py:292`). A function cannot enter a recipe's
   identity. The owner instead defines a frozen, hashable content value built from plain data:
   the kind of controlled converter, the page, and an ordered list of authored elements with
   their label, text, original text, grouping and formula outcome. The owner builds the
   `DoclingDocument` from that value. Two contents that would produce different published state
   are different values, and the value is part of the recipe (the coordinator's rule that
   scenario content which changes produced state is recipe content).
2. **Installation needs no pytest fixture.** The owner offers one context manager that installs
   the replacement for the duration of a block and restores the original on exit. A test may
   enter it through `monkeypatch`'s context or directly; a seed builder enters it directly.
   Replacing a class attribute is process-wide, so the block must not overlap another capture in
   the same process; a seed build is synchronous within one worker, which satisfies that.
3. **The content carries no location.** Spool and record roots arrive in the request. The asset
   binding reaches only the report memo's key.

The vocabulary of authored elements must cover every document the current doubles build. By
reading, these include a heading with one paragraph, section groups with text and formulas, a
list and a table. Enumerating them is the package's first step; an element the vocabulary cannot
express is added to the vocabulary, not smuggled in as a callable.

### Alternatives rejected

- **Stopping at `certified_reply`, the function for the half after conversion.** It leaves
  preparation, the spool and request assembly with the doubles, which is the state at the
  revision baseline: three hand-written preparation entries and three copies of request assembly.
- **An in-process mode inside `PdfWorker`.** That would be a production path that exists only
  for tests.
- **The scripted Docling provider in every consumer.** It couples each consumer to Docling
  internals. The coupling stays with one support owner, used by the contract control and by the
  derivation of the report.
- The coordinator records two further rejections that apply here: every PDF test through the
  real worker child (kept for the contract control and for consumers that need page custody),
  and repairing the copies in place.

**What would reopen the design.** If in-process preparation needs model assets after all, the
report falls back to the hand-written form and the contract control's comparison of preparation
identity becomes the only guard on it. If a second real producer appears, the two-step protocol
is where it is expressed, and nothing else changes.

### Implementation vision

The package is one change in three movements, and they should land together, because between
them the tree would hold two protocol owners.

*Production.* Extract the function, with `certified_reply` as its final step; split
`StreamingPdfProducer.run`; make `PdfWorker.stream` take a request; migrate `_native_child` and
`orchestrate/pdf_streaming.py:421`; remove `StreamingPdfResult.effective_options`. Failure
behaviour is preserved: a malformed report refuses before anything is acknowledged; a changed
preparation identity on resume refuses before the entry is acknowledged; a conversion failure
raises as today.

*Test support.* One support module owns the content value, the controlled producer, the
installer and the report memo. The scripted Docling provider moves out of
`test_pdf_streaming_integration.py` into a support owner beside it.

*Consumers.* Every double is replaced by a content value passed to the owner.

**Complete consumer scope.** This is the whole scope at `12f57dc4d`, not a sample; TDM-00's
re-read confirms it against any later change.

- The two certifying helpers, `certify_controlled_pdf_stream` (`pdf_acceptance_support.py:34–71`)
  and `_certified_controlled_reply`, both removed, with `_controlled_stream` and `_section_stream`
  (`current_pdf_source_support.py:212–268`, `:388–455`).
- The seven doubles that call `certify_controlled_pdf_stream`, listed in the baseline, and their
  installation sites (`current_pdf_integration_support.py:426`, `current_artifact_support.py:215`,
  `declared_record_native_support.py:354`, `test_pdf_materialization_native.py:79`,
  `test_pdf_transform_demand_native.py:170`, and the `stream=` arguments at
  `test_nce02_native_scope.py:266` and `current_pm2_native_support.py:80`).
- Every caller that passes a function as `stream=` to the source factory:
  `test_current_contextual_native.py:83`, `test_actual_e5_selected_context_native.py:152`,
  `test_artifact_identity_registered_native.py:70`, `test_contextual_workflow_native.py:133`,
  and the factory's own section route at `current_pdf_source_support.py:373–380` and the default
  at `:292`. Two modules also replace `controlled_table_stream` on its support module to vary the
  document (`test_rich_domain_preservation_native.py:235`, `test_rich_domain_external_native.py:56`);
  they pass a different content value instead.
- `test_current_pdf_source_inputs.py:58–68`, rewritten to drive the owner with a content value
  and a real request. TDM-01 leaves this test to TDM-09, since TDM-09 rewrites it.
- Direct callers of `PdfWorker.stream` by keyword, which move to the request form:
  `tests/semantic/test_actual_pdf_spool_resume.py:87, 101, 119` and
  `tests/ingest/test_pdf_streaming.py:324, 374`.
- Other constructions of `PdfStreamReply` that are not converter doubles and stay: the
  child-protocol replies in `tests/pdf_process_support.py:83, 100`, the spool unit case at
  `tests/ingest/test_pdf_build_spool.py:308`, and the child double in
  `tests/orchestrate/test_pdf_private_execution.py:144–178`. The last replaces the whole worker
  to test the parent's lifecycle, so it keeps its scripted reply; it takes its preparation bytes
  from the owner's report and builds its replay references through a public route in place of
  `_atomic_bytes` and `_ref`. `test_pdf_shared_streams.py:449` drops its `_ref` import the same
  way. Whether production gives the two helpers public names or the tests build the public
  reference type directly is the implementer's.
- Two staging helpers construct a `StreamingPdfResult`, write record batches and adopt them
  directly, without a stream reply (`pdf_acceptance_support.py:74–100`, `stage_pdf_document`;
  `tests/semantic/selected_source_native_support.py:139`). They are not replacements for
  `PdfWorker.stream` and stay, adjusted only for the removed field.

**Superseded machinery removed.** `certify_controlled_pdf_stream` and
`_certified_controlled_reply`; the nine stream doubles; every hand-written preparation entry;
the test imports of `_atomic_bytes` and `_ref`; the `effective_options` field of
`StreamingPdfResult`; the keyword form of `PdfWorker.stream`.

### Acceptance evidence

Each item names what a wrong implementation would do to it.

- **No second protocol owner.** A search of `tests/` finds no construction of `PdfStreamReply`
  outside the three surviving non-converter sites, no construction of `PdfStreamRequest` outside
  direct callers of the request-form `PdfWorker.stream`, no import of `_atomic_bytes` or `_ref`,
  and no preparation entry whose bytes a test authored. This fails if a copy survives.
- **Malformed report.** A direct case gives the function a producer whose report lacks the
  preparation section and expects the identity refusal with an empty acknowledgement log. It
  fails if the function acknowledges before checking, or if a double is again allowed to supply
  arbitrary bytes.
- **Payload schema.** A direct case perturbs the request's payload schema from the default and
  expects the encoding to follow the request. The contract control cannot see this, because both
  of its routes pass the same request. The observable is an open question below.
- **Contract control.** One authored document goes through the real child with the scripted
  provider and through the controlled route. The test compares the ordered sequence of
  acknowledged families after removing the page-capture families (`page`, `candidate_payload`,
  `native-raster`); the preparation identity, which must be equal; a projection of the published
  records that does not depend on the build; and the parent's acceptance of the certification in
  both routes. It fails if the controlled producer drops or reorders a step or mishandles the
  document, the formula outcomes or the report. It cannot catch a defect in the function, which
  both routes share; the direct cases, the existing real-child integration test,
  `test_actual_pdf_spool_resume.py` and the parent's refusals cover that.
- **Consumers keep passing, and the broken one passes.** The package's first step runs the
  modules that consume the nine doubles under `uv run ci test -- PATH` and records the result,
  because their setup at the revision baseline is established only by reading. The same modules
  pass after the change, and `test_current_pdf_source_inputs.py` passes for the first time. A
  consumer that fails before the change for a reason unrelated to the converter is recorded for
  its owner and is not this package's defect.
- **Expectations are independent.** The authored document's expected records are written in the
  test from the document's text, not read back from the function's output.

---

## TDM-10 — The demand executor's native I/O

### Baseline

`NativeDemandExecutor` has a public constructor (`src/corpus_structure/orchestrate/data_operations.py:634–693`).
It checks that the runtime belongs to the release, derives the worker count from the database
capacity, computes `self.reservation = 2 * max_packet_bytes + 3 * max_reply_bytes` (`:689`) and
refuses when the reservation exceeds owned capacity (`:690–691`).

Tests do not call it. Seven sites build the object with `__new__` and assign private state:
`tests/orchestrate/test_data_operation_byte_admission.py:71`,
`test_data_operation_execution_basis.py:47, 109, 396, 465`,
`tests/semantic/test_d1_limitation.py:292` and `test_data_operation_capabilities.py:428`. The
largest, `controlled_executor` (`test_data_operation_byte_admission.py:69–181`), assigns about
eighteen attributes, replaces four private methods, and copies the reservation formula twice
(in `policy_for`, `:53`, and at `:79`). It is imported by two other test modules
(`test_data_operation_execution_basis.py:12`, `tests/orchestrate/test_execution_host.py:163, 238, 369`).
Its native replies are plain dictionaries returned from module names that the test replaces
(`DataOperationStorage` and `DemandPlanner`, at `test_data_operation_byte_admission.py:136, 174`
and `test_data_operation_execution_basis.py:82, 140–142, 413, 493`), so no reply is checked
against the wire contract. The helper's own docstring states the intent correctly: "Replace
native I/O only". The executor gives it no way to do that.

One further site has the same coupling without `__new__`.
`tests/semantic/test_data_operation_consumers.py:117–142` casts a `SimpleNamespace` holding
`engine`, `model`, `demand` and `policy` to the executor type and calls the unbound
`NativeDemandExecutor._hydrate` on it.

The executor reaches native state at eight kinds of site, all through `self.engine` or
`self.admission_engine`:

| # | Interaction | Site in `data_operations.py` | Nature |
|---|---|---|---|
| 1 | Demand page resume and obligations; final resume | `:1966–2000`, `:2062` | Planner over storage |
| 2 | Ready set for a page | `:1663–1683` | Planner; runs compiled binding SQL on the storage connection |
| 3 | Rebuilding the original generation | `:844–888` | Wire read plus planner |
| 4 | Claim set with hydration in the same transaction, one savepoint per member | `:1125–1225` | Wire claim; `begin_nested`; relational hydration |
| 5 | Lease renewal | `:1956`, `:912–919` | Claim owner on the engine |
| 6 | Settlement through claim-owner callbacks that receive a connection | `:1081`, `:1259`, `:1277`, `:1356`, `:1399` | Wire calls |
| 7 | Port admission and the cached recheck | `:720`, `:766`, `:808` on the admission engine | Pure identity plus native inspection |
| 8 | Acquiring the basis for another release or runtime | `:823` | Already behind the public `execution_host` parameter |

Port execution owners also receive the engine (`:299`); that I/O belongs to the ports and is
outside this seam.

**Delivered by the conversion:** nothing. `orchestrate/data_operations.py` and the three
executor test modules are unchanged since the authoring baseline, so every citation above holds
at `12f57dc4d`. The conversion rewrote the bodies of the production storage calls
(`semantic/data_operation_storage.py`) without moving the executor's call surface, and the
dictionaries the tests return for those calls are unchanged and still unvalidated.

### Target design

**One collaborator becomes the executor's only route to native state.** It is a constructor
parameter. Its default is built from `engine` and `admission_engine` and preserves today's
behaviour exactly. It has three surfaces.

- **Unit of work.** A transaction context that offers the wire calls as a `DataOperationCalls`,
  a savepoint, hydration, and a planner bound to that unit (rows 1 to 4). Every
  `with self.engine.begin(): DataOperationStorage(connection)` site moves onto it. This surface
  preserves the grouping that `test_data_operation_execution_basis.py:390–465` asserts today:
  begin, claim, savepoint, hydrate, release or roll back the savepoint, commit, and only then
  renew.
- **Claim lifetime.** The claim owner and renewal (row 5). Settlement callbacks (row 6) receive
  the unit's `DataOperationCalls` instead of a raw connection, so a double runs the same
  callbacks unchanged.
- **Admission.** The three admission calls return the admission record (row 7). The preferred
  split keeps production's pure identity computation outside the collaborator and places only
  the native inspection behind it. A double then authorizes the identity production computed
  and invents no refusal of its own, which is the same discipline TDM-11 applies to the host.

**What a test supplies to the constructor.**

- `prepared`, `runtime` and `sources` come from a prepared-kernel recipe held in TDM-07's
  bounded memo. Preparing a kernel is pure and touches no database. The recipe declares the
  test's operations: one scalar and one batch Python operation whose source is the admission
  kernel. The runtime binding lists those sources, so production's pure admission checks run on
  real values.
- `database_capacity` is given explicitly. `_database_capacity` accepts any engine without a
  managed pool when the capacity is declared (`:614–628`).
- `policy` is authored; `execution_host` and `host_run` are existing public parameters
  (`:651–653`).
- `engine` is a sentinel without a managed store, so that `_database_capacity`, which reads
  `getattr(engine, "_corpus_store", None)`, takes the declared capacity, and whose `connect`,
  `begin` and `raw_connection` fail the test. Any I/O that bypasses the collaborator then fails
  the test, which makes the seam's completeness something every test checks.

**What the double is.** For wire calls it is `WireCheckedStorage`, extended once: a reply may be
a function of the validated request, or a sequence consumed in order, because a claim reply
echoes the request's ids. For the planner, hydration and admission, which are relational reads
or inspections and not wire calls, replies are authored typed values: ready items, page
dictionaries, hydrated selections, and admissions built from production's pure identity. The
double keeps an event log so that the transaction-order test reads the same sequence it reads
today.

**Tests drive public entry points.** They call `advance` or `run` (`:1885`, `:1907`) with one
authored page instead of assigning `executor._physical` and calling `_drive_sweep`, and they
read `executor.reservation`.

**The formula is pinned once, with literals.** One case states: a packet limit of 65536 and a
reply limit of 4096 give a reservation of 143360, and an owned capacity of 143359 raises the
"exceed owned capacity" refusal. No other test computes the formula.

**Preserved guarantees.** The default collaborator performs the same statements in the same
transactions as today, so the native suites are the regression evidence. The claim and its
hydration stay in one transaction. Settlement stays under the claim owner.

**Deliberate change.** Tests that replaced private methods to script a race, a refusal or a
capacity window now script it through authored replies; a test that depended on reaching into
`_physical` is rewritten against observable behaviour.

### Alternatives rejected

- **Keep `__new__` and import the formula from production.** The copy goes and eighteen private
  assignments remain.
- **Keep replacing the module names `DataOperationStorage` and `DemandPlanner`.** It is the same
  private coupling, and replies stay unchecked.
- **A fake SQLAlchemy engine.** It couples tests to call shapes, and the planner and hydration
  still need the meaning of SQL.
- **Real PostgreSQL for these tests.** The native suites already do that, and they cannot script
  races, refusals or capacity windows.
- **A per-call factory for `DataOperationCalls` only.** The planner, hydration and admission
  would stay private stubs, so `__new__` would remain.

**What would reopen the design.** If splitting pure identity from native inspection in admission
proves to cut across a production invariant, the admission surface returns whole admission
records and the double authors them; the cost is that the double then holds identity values a
change could invalidate, which TDM-13's table for the execution-basis key would have to cover.

### Implementation vision

The production change comes first and is verified on the default collaborator by the native
suites before any unit test moves. A test builder in a support module then constructs executors
through the public constructor from the memoized recipe. Because the builder is not a test
module, this package closes the two parts of neighbouring findings that the coordinator assigns
to it: DTA-009's `controlled_executor` case and DTA-034's claim double.

**Complete consumer scope.** The seven `__new__` sites above; the `SimpleNamespace` executor in
`test_data_operation_consumers.py:117–142`, which becomes an executor built through the public
constructor or a direct test of the hydration it exercises; the twelve calls of
`controlled_executor` in `test_data_operation_byte_admission.py`; its callers in
`test_data_operation_execution_basis.py:183` and `test_execution_host.py:203, 244, 374`. Three
native modules inject faults on a real database by replacing `_publish`
or `_retain_answer` (`tests/semantic/test_prepared_authority_batch_native.py:98`,
`test_pm2_parser_stage_native.py:174–195`, `current_pdf_integration_support.py:441–507`). They
may move to wrapping the default collaborator's calls. That move is optional, is taken only when
it simplifies the test, and is not a completion condition.

**Superseded machinery removed.** `controlled_executor` and `policy_for`'s copied formula; every
`__new__` construction; every replacement of `data_operations.DataOperationStorage` and
`data_operations.DemandPlanner` in tests.

**Prerequisite.** TDM-07 supplies a prepared kernel that is cheap to obtain repeatedly and whose
memo key includes the binding. The need is economy and correctness of reuse, not capability: the
production seam and the native-suite check do not depend on TDM-07 and may proceed first.

The conversion converted the binding, acquisition and completion kernels without renaming or
regrouping the wire operations the executor calls, so the interaction table stands as written.

### Acceptance evidence

- A search finds no `__new__` construction of `NativeDemandExecutor`, no object cast to it, and
  no replacement of the two module names in tests. This fails if a bypass survives.
- The sentinel engine's `connect`, `begin` and `raw_connection` are never called in a test built
  through the seam, and constructing the executor with the sentinel succeeds. The first fails if
  any executor path still opens its own transaction; the second fails if the sentinel breaks the
  constructor's capacity read.
- The literal reservation pin fails if the formula changes, and no other test would.
- An authored claim reply with `lease_until` removed fails with the wire validation error. This
  proves the double checks replies; without it, a double that silently stopped validating would
  pass every other case.
- The transaction-order test passes against the unit double's event log with the order written
  in the test.
- The native suites pass on the default collaborator (`test_data_operation_external_native`,
  `test_prepared_authority_batch_native`, `test_characterization_native`). They are the evidence
  that the default preserves behaviour.

---

## TDM-11 — The native host's startup profile comparison

### Baseline

After a host reports ready, `NativeHost` checks that the reported set of residents equals the
declared set (`src/corpus_structure/methods/native_host.py:181–183`) and then calls a private
static method on each observation (`:184–185`). `_validate_startup` (`:196–213`) compares eleven
fields of the observation with the selection's profile and raises
`Pm2WorkerError("native host executed a different frozen provider profile")` on any difference:

- six by plain equality: `provider`, `profile` (the fingerprint, which covers the whole profile
  content), `runtime_identity`, `assets`, `backend`, `matmul_precision`;
- `device`, compared on the part before the colon, so `cuda:1` matches `cuda`;
- `dtype`, compared with `"torch."` prefixed to the profile's value;
- `cudnn_allow_tf32`, compared by identity, so a value that is not the same boolean mismatches;
- `native_threads.intra_op` and `native_threads.inter_op`, read under a nested key.

On failure the host closes with no grace period and raises `NativeRetirementUncertain` only if
that cleanup itself fails (`:187–194`).

No test makes any field differ. The peer process echoes the declared profile exactly
(`tests/methods/native_host_cases.py:23–40`), and the refusal's message appears in no test. The
only test that claims to cover a mismatch asserts a refusal the test double invented:
`Group.startup` raises `Pm2WorkerRefused("native artifacts differ from frozen selection")`
(`tests/methods/test_characterization_resources.py:59–61`), matched at `:243–252`. Production
has no check before start that produces such a refusal. The real child adapters do refuse
several mismatches before reporting (`src/corpus_structure/methods/native_host_adapters.py:17–74`),
but the peer runs none of them.

**Delivered by the conversion:** nothing. No conversion commit touched `methods/native_host.py`,
`methods/native_profiles.py`, the peer or these tests, so every citation above holds at
`12f57dc4d`.

One detail matters to the design. An observation whose `native_threads` is present but is not a
dictionary would, by reading, raise `AttributeError` from the chained `.get` (`:209–210`) and
not the profile refusal. The surrounding handler still closes the host.

### Target design

**One public production comparison** takes a selection and an observation and reports which
declared fields mismatch, by name. Its compared fields are declared as data: for each field, the
path into the observation and the projection of the profile it is compared with. The three
projections that are not plain equality (the device prefix, the dtype prefix and the boolean
identity) are kept exactly. `NativeHost` calls the comparison and raises `Pm2WorkerError` naming
the field; the private static method is removed.

**Preserved.** An observation that is not a dictionary refuses. An absent key is a mismatch.
`cuda:N` matches `cuda`. A `cudnn_allow_tf32` that is not a boolean mismatches. The population
check and the retirement path are unchanged.

**Deliberately changed.** The refusal names the field. A `native_threads` value that is not a
dictionary is reported as a mismatch of the thread fields instead of raising `AttributeError`.

**Two kinds of evidence, because they answer different questions.**

*Which fields are compared* is a property of a pure function, so it is tested without a process.
The test authors a profile and its matching observation by hand, without calling the projection.
It parametrizes over a hand-written list of the eleven fields; each case perturbs one value and
expects a refusal that names that field. It adds one matching case, the absence cases and
`device="cuda:1"` accepted. One completeness case asserts that the hand-written list equals the
declared field set. The operator accepted the completeness case on 2026-11-17 as a test of one
mechanism and not a lint. Its purpose is narrow: a field added to production's declaration
without a perturbation row fails here.

*Whether the host calls the comparison on what the peer really reported* needs a real process.
The peer gains a mode, selected by its arguments in the way `startup-hang` already is
(`native_host_cases.py:11`), in which it reports one named field perturbed, for example
`backend`. A real `NativeHost` started with that command must raise `Pm2WorkerError` naming the
field, must not raise `NativeRetirementUncertain`, must leave `host.startup` empty and must have
retired the process. The existing echoing peer remains the matching case.

**The invented refusal goes.** The `Group.startup` double stops refusing on artifacts. The test
at `test_characterization_resources.py:243–252` either becomes a test that `ProviderExecution`
propagates a refusal the group raises, with a scripted refusal and a name that says so, or it is
deleted. Which one is decided by reading whether another test already covers propagation.

**Relation to TDM-13.** The coordinator fixes the split: this package writes the comparison, the
declaration, the per-field cases and the reach control, and TDM-13 only checks their form against
the perturbation-table contract. Nothing in this package waits for TDM-13.

### Alternatives rejected

- **Testing the private method directly.** That is the coupling being removed.
- **A peer that reads the expected profile back and compares.** The expectation would come from
  the code under test.
- **A peer that runs the real adapters.** That needs GPU assets and belongs to the
  provider-backed tests.

### Implementation vision and scope

The production change is small: the comparison, its field declaration, the call site, the
removal of `_validate_startup`. The complete consumer scope is one production caller
(`native_host.py:185`), the peer (`native_host_cases.py`), the new unit cases beside the
existing host tests in `tests/methods/test_native_host.py`, and the one resources test and its
double. Nothing else references the private method or its message. The package has no
prerequisite and is independent of the conversion, which did not touch the host. One neighbouring
site is noted and left alone: `tests/methods/test_native_host.py:57` builds a `NativeHost` with
`__new__` and assigns private fields for a reader-routing test, which is not on the profile path;
it moves to the public constructor only if this package's edits to that module make that easy.

**Superseded machinery removed.** `NativeHost._validate_startup`; the artifact refusal in the
`Group.startup` double; the test name that claims a production refusal.

### Acceptance evidence

- Removing any one comparison from production fails exactly that field's row and the
  completeness case.
- Changing the device prefix rule fails the `cuda:1` row.
- The reach control fails if `NativeHost` stops calling the comparison, or calls it on anything
  other than the parsed ready metadata.
- The profile and observation in the unit cases are literals in the test. A helper that derives
  the observation from the profile would make every row pass by construction and is not used.

### Not in scope: `admitted_startup_matches`

`admitted_startup_matches` (`src/corpus_structure/methods/native_profiles.py:165–198`) compares
an observed startup record with an admitted one. A search of `src/` at `12f57dc4d` finds no
caller; its only users are `tests/methods/test_native_host.py:617–677`. It is a different
contract from the comparison in this package (observed against admitted records, not observation
against profile). Whether a consumer is pending or the function is superseded is the production
owner's question; it is a row of the coordinator's [handover table](../test-domain-model-and-execution_2026-11-17.md#handovers).

---

## TDM-12 — Remaining substitutes

### Baseline

Four substitutes remain below the boundary they claim, and one fake cannot show misattribution.

**The read-result page.** `_page` (`tests/semantic/test_demand_results.py:20–91`) hand-writes
the native read-result page. Eleven modules import it from that test module
(`test_selected_references`, `test_selected_contribution_scope`, `test_contextual_witnesses`,
`test_record_support`, `test_record_diagnostic_selection`, `test_record_consumers`,
`test_demand_context`, `test_contextual_query_selection`, `test_selected_structural_review`,
`test_data_operation_test_support` and `tests/evaluate/test_selected_operation_events`). The
result reader loads it raw, and nothing validates it against the wire type, although production
has the validator for exactly this record
(`validate_native_wire("read_demand_result", "output", …)`,
`src/corpus_structure/semantic/demand_results.py:502`; this one citation was not re-read at
`12f57dc4d` and keeps its 2026-11-17 label).

**The frontier recheck.** `control_frontier`
(`tests/semantic/selected_query_cache_support.py:27–43`) replaces
`demand_results.recheck_selected_frontier` and raises three refusals of its own wording
("selected native scope differs", "selected native read differs", "selected native cut/trust
assessment differs"). Four modules use it.

**The population-close double.** A local class in
`tests/semantic/test_data_operation_demands.py:635–650` subclasses `DataOperationCalls` and
returns an unvalidated dictionary for `close_data_population`, in a file that already uses
`WireCheckedStorage` elsewhere (`:243`, `:326`).

**The claim double** is the one inside `controlled_executor`; TDM-10 replaces it, and DTA-034
closes only when both packages have delivered.

**The encoder fake.** `_model` (`tests/semantic/test_contextual_encoder_batch.py:104–128`)
returns the vector `(1.0, 0.0)` for every text, with one invalid vector at index 1 on request. A
second fake does the same (`tests/semantic/test_contextual_owned_encoder.py:23–31`). When a
member is dropped from a batch and several survive, the batch form must realign outputs to
members. With identical vectors an off-by-one in that realignment passes.

**Support code in test modules (DTA-009's sharp cases).** At `12f57dc4d` 67 import statements
take a private name from a non-production module, by a scan of every import; four of them arrived
with tests the conversion added. The cases the review names are `_page` (11 importers),
`_complete_ready` from `test_data_operation_population_native.py:145`, which has four importers
and not the two first recorded (`test_data_operation_context_fanin_native.py:18`,
`test_selected_source_acquisition_native.py:29`, `test_data_operation_pinned_reuse_native.py:29`
and `test_data_operation_transitive_read_native.py:27`), and `controlled_executor`.

**Test modules imported from another test directory.** The review's §5.5 also names
cross-directory imports. `tests/` itself is not a package; `tests/semantic/` and `tests/methods/`
are, and test modules import support modules of other directories by the absolute form
(`from semantic.x_support import …`), which is the tree's convention and not a defect. The sharp
case is a *test module* used as support from another directory. By a scan of every import at
`12f57dc4d`, ten importing files do this, in seventeen import statements, the same as at the
authoring baseline, whose search missed one file: for example
`tests/evaluate/test_selected_operation_events.py` imports from `semantic.test_demand_results`
and `semantic.test_sentence_products`, `tests/methods/test_construction_named.py` from
`semantic.test_construction_products` and `semantic.test_source_annotations`,
`tests/semantic/test_cpu_authority_reply_native.py` and `test_record_fit_native.py` from
`evaluate.test_declared_record_policy`, `tests/semantic/test_demand_context.py` from
`methods.test_declared_contextual_query`, `tests/evaluate/test_selected_native_question.py` from
`semantic.test_selected_references`, `tests/semantic/test_record_support_native.py` from
`evaluate.test_declared_rich_native_journey`, and `tests/semantic/test_native_fixtures.py` from
the root-level `test_prerequisites`. The three relative imports in the tree (in
`test_pdf_payload_validation.py`, `test_pdf_stream_reconciliation.py` and
`test_native_child_edge_guard.py` under `tests/semantic/`) are inside a package; no relative
import sits in a directory that is not a package.

**Delivered by the conversion:** nothing. Every site above is unchanged since the authoring
baseline; the count corrections are corrections of the first reading, not changes in source.

### Target design

**The page becomes a support builder whose product is validated.** `_page` moves to a support
module under a public name. The builder passes its result through production's validator for
the read-result output before returning it, so a page the wire forbids fails in the builder and
not silently in eleven consumers. The eleven importers move to the support module. If validation
shows today's page is not a legal record, which is plausible given that it has never been
checked, the page is corrected to a legal one and each consumer whose assertion depended on the
illegal shape is examined individually.

**The recheck double raises only what production raises.** `control_frontier` keeps its role
(supplying a cut and frontier for a demand without a database, and recording calls). Its three
invented refusals are replaced by the conditions and exception types of the production recheck
(`demand_results.py:289–329`), obtained by sharing production's own checks where they are
callable on a cut and options, and otherwise by removing the refusal from the double and leaving
refusal cases to tests that run the real recheck. A double must not be the only place a refusal
is exercised.

**The population-close double becomes `WireCheckedStorage`** with an authored reply, using the
extension TDM-10 adds. If the authored reply is not a legal `close_data_population` result, it
is corrected.

**The encoder fake carries identity.** The fake derives each vector from its input text by a
rule written in the support module and independent of production, for example a small fixed
mapping from the authored texts to distinct unit vectors. A new controlled case uses a batch of
at least three members, drops one that is not the last, and asserts that each survivor's
published vector is the one derived from that survivor's own text. The invalid-vector option
stays. Both fakes are replaced by the one owner.

**Sharp support cases move with the boundary corrections.** `_page` moves as part of its
correction above, and `controlled_executor` as part of TDM-10's. `_complete_ready` moves to a
support module under a public name.

**A test module is not imported from another test directory.** For each of the cross-directory
imports listed in the baseline, the imported names move to a support module in the directory of
the test module that defined them, under public names, and both the defining module and its
importers import from there. The package's first step repeats the search at entry and also lists
any relative import in a test directory that is not a package; such an import is rewritten to the
tree's absolute form. Imports of support modules across directories are unchanged.

**What stays for later.** Cohesive public builders and private names imported between test
modules of the *same* directory move when a package touches the importing module and not
otherwise, since no assertion depends on where they live (§5.5). This package does not undertake
a general sweep of the 67 private-name imports; the coordinator's disposition of DTA-009 records
that remainder with its trigger.

**Not in scope here.** Tests named `_native` that run on a hand-built substitute schema
(DTA-034's fourth item) are DTA-047 and belong to TDM-16.

### Alternatives rejected

- **Validating `_page` in each consumer.** Eleven places to forget; the builder is the one
  place.
- **Keeping the invented refusals with production's wording copied in.** The wording would
  match and the conditions could still drift.
- **Using the small real encoder from `tests/semantic/current_contextual_support.py:12–52` in
  the batch tests.** It gives distinct vectors but ties a unit test of realignment to a real
  model's vocabulary and makes the expected vector something only the model can compute. A fake
  with a stated rule keeps the expectation independent.

### Implementation vision and scope

**Complete consumer scope:** the eleven importers of `_page`; the four users of
`control_frontier` (`test_current_candidate_facets`, `test_selected_structural_readers`,
`test_current_composite_delivery`, `test_grouped_record_interpretations`); the one
population-close double; the two encoder fakes and the batch tests that use them; the four
importers of `_complete_ready`; the ten files that import a test module from another test
directory, with the modules they import from.

**Superseded machinery removed.** `_page` in the test module; the three invented refusals; the
local `Storage` class; the constant-vector fakes.

**Prerequisite.** TDM-10 supplies the storage double's reply extension, which the
population-close replacement uses. Everything else in this package is independent of TDM-10 and
may proceed before it.

**The generated wire types.** The conversion regenerated wire types, and whether the read-result
record changed shape was not re-read. The builder validates against the generated type as it
stands, which is the point of validating. If the record changed shape, the builder's correction
and its consumers' adjustments are larger, and are still this package.

### Acceptance evidence

- The page builder's product passes the production validator; a deliberately illegal variant
  (one required field removed) raises the wire validation error from the builder. Without the
  second half, a builder that stopped validating would pass.
- No test imports `_page` or `_complete_ready` from a test module (`controlled_executor` is
  TDM-10's acceptance). A search finds no import of a `test_` module by a module in another test
  directory, and no relative import in a test directory that is not a package. These searches are
  closure evidence and are not added as a check.
- No refusal message in `control_frontier` is absent from production. Each refusal the double
  used to invent is exercised by a test that runs the production recheck.
- The multi-survivor case fails when the realignment is shifted by one. One local wrong edit of
  the realignment (a shift by one) is tried once and the case is seen to fail; the edit is not
  committed and no mutation tool is added, as in TDM-13.
- The expected vectors are computed in the test from the stated rule, not read from the batch
  reply.

---

## Open questions

Each question names the evidence that settles it and the work it constrains. The first four are
the unverified premises carried from the [seam advice](../../design_review/evidence/2026-11-17_test-plan-authoring/seams.md) (its cross-cutting
notes); each is the first step of its owning package, or of TDM-08 where noted.

1. **Is the publication's logical digest independent of the build?** (TDM-09, first step.) The
   contract control compares a projection of published records that must not depend on the
   build, and record rows carry the build identity as their product identity. *Settled by*
   reading what the logical digest covers. *If it excludes build identity*, the control compares
   digests. *If not*, the control compares record rows with the build columns removed. Only the
   form of one comparison changes.
2. **Where does the payload schema become observable?** (TDM-09, first step.) The direct case
   for a perturbed schema needs something to assert. Candidates are the header of the companion
   encoding and the certification's contract. *Settled by* reading the encoding path from the
   payload family to the written batches. *If no output differs under a perturbed schema*, the
   schema's only effect is refusal, and the case asserts a refusal for an authored value the
   perturbed schema forbids.
3. **Do today's authored claim replies pass wire validation?** (TDM-10, first step.) The current
   replies include `trust_snapshot={}` in claim results
   (`test_data_operation_execution_basis.py:73, 373, 477`). *Settled by* running the authored replies
   through `validate_native_wire` once the double is in place. Replies that fail are corrected;
   the count affects effort, not design.
4. **Does demand reuse avoid a capture claim?** (TDM-08, first step; recorded here because
   TDM-09's converter is what a mistaken claim would invoke.) If a consumer registers a new
   demand over a seeded completed capture and production claims capture again, the frozen
   workspace refuses the write and the consumer fails loudly. It cannot pass wrongly. *Settled
   by* reading demand reuse, or by the first consumer TDM-08 moves.
5. **Does in-process preparation run without model assets for every recipe the doubles stand in
   for?** (TDM-09.) The integration module shows it for one streaming recipe. *Settled by* the
   package's first run of the report derivation. The fallback is stated in the design.
6. **Does every current double's document fit a data vocabulary?** (TDM-09, and it bounds
   TDM-08.) *Settled by* enumerating the nine doubles' documents at entry. A document that needs
   a new element extends the vocabulary.
7. **Can the production recheck's conditions be shared with `control_frontier`?** (TDM-12.)
   *Settled by* reading `recheck_selected_frontier`. If its checks are entangled with the native
   read, the double drops its refusals.
8. **Is `Group.startup`'s propagation already covered?** (TDM-11.) *Settled by* reading the
   resources tests. It decides between renaming and deleting one test.

## Deferred and gated items

- **No precision case is pending for the profile comparison.** Its one stated tolerance (`cuda:N`
  matches `cuda`) is written now. A further tolerance is a production decision about the profile
  contract and would arrive with that change.
- **Hypothesis state machines** for the executor's claim lifecycle are a candidate only, under the
  coordinator's [candidate](../test-domain-model-and-execution_2026-11-17.md#candidates-and-deferrals). The seam makes them possible,
  since the double is a scriptable collaborator; nothing here depends on them.
- **Moving the native fault-injection sites onto the default collaborator** is optional, as
  stated in TDM-10.

Handovers and options rejected for the whole series are the coordinator's. One note belongs to
this design: TDM-09's report memo is keyed by the asset binding because the capture workspace and
asset root are part of release custody (the first row of the
[handover table](../test-domain-model-and-execution_2026-11-17.md#handovers)); if production later binds those locations at run time,
the key simplifies.

## Order within this companion

The coordinator's queue binds. Within this companion: TDM-11 shares no files with the others;
TDM-09 should run early, because TDM-08 consumes its converter and because it removes the
hand-written preparation entries before a controlled path first resumes a spool; it no longer
restores setup for any test other than `test_current_pdf_source_inputs.py`. TDM-10's production change can precede
TDM-07 and its test migration follows TDM-07; TDM-12 shares `data_operation_binding_support.py`
with TDM-10, so its population-close item follows TDM-10 and the rest is free.

## State

| Package | State |
|---|---|
| TDM-09 | Not started; partly delivered by the conversion (`1d22c41cb`, `8a5c074f0`), remaining scope above |
| TDM-10 | Not started |
| TDM-11 | Not started |
| TDM-12 | Not started |
