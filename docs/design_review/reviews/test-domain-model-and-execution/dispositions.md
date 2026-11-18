# Dispositions — test domain model and execution review, 2026-11-17

Supporting document of the [principal review](../design_review_test-domain-model-and-execution_2026-11-17.md).
Its role is narrower: one row per finding with its disposition, the correction the review selects,
and the evidence that would close it. Every judgment and argument lives in the principal review;
section references (§) point there. Baseline `1afa63f88`; audit consumed at `aca50eeea`.

## Who owns status

The binding gives each finding one disposition owner: the active plan's findings table when
scheduled, otherwise a Deferred row in the source review. At `1afa63f88`:

- DTA-037…048 are unscheduled. The rows below are their Deferred rows until plan creation selects
  them.
- DTA-001…036 have recorded dispositions in the
  [test-system target design plan](../../../plans/test-system-target-design_2026-11-13.md), whose
  implementation is closed with TS-21 (DTA-035) and TS-22 (DTA-036) gated on the
  declared-data-operations plan. Where the test audit reads a current-source manifestation of one of
  those findings (changed footprint or regression), the row below is a Deferred row for **that
  manifestation**, as the 2026-11-13 review did for earlier findings. The plan's own rows are not
  amended by this document.
- F06 and F07 are this review's findings. F01–F05 of the 2026-11-13 review are closed in the plan
  (§11).

Reopening event for every Deferred row, unless the row names an earlier one: plan creation from this
review.

**Disposition vocabulary.** *Corrected by the target* — the selected design removes the cause.
*Changed* — the diagnosis is refined and the target addresses the refined form. *Retained* — the
finding stands and the target leaves it as is, with a reason. *Deferred* — no correction now, with a
trigger. "Re-inspected" says whether the reviewer opened the decisive source at `1afa63f88`; "audit"
means carried on the audit's reading.

## Open test findings

| Finding | Re-inspected | Disposition | Selected correction (§) | Closure evidence | Earlier trigger |
|---|---|---|---|---|---|
| DTA-041 converter copies | Yes | Corrected by the target | One controlled-converter owner for all nine sites; in-body copies and `test_current_pdf_source_inputs.py`'s direct call re-pointed; contract control against the real child with a scripted converter (§4.3, §5.3) | No `PdfStreamReply` built by hand outside the owner; the contract control and the former consumers pass setup | The conversion's step 3 fixture move — do as one change |
| DTA-037 hand-kept fixture lists | Yes (lists, dead names, dangling request) | Corrected by the target | `db` mark derived from the native root; worker groups declared at fixture definitions; `record_source_*` fixtures and the four unimported support modules removed; `test_source_routing.py` rewritten or removed with a transfer note (§4.5, §4.6) | No hand list of fixture names; collection of the package marks every native item `db` | Any new preparation fixture |
| DTA-033 vector inputs (regressed) | Yes | Corrected by the target | Vector records carry their authored input; native and Python consumers use it; request-identity vector; `subject_definition` varied (§5.1) | Native vector cases pass; a framing change made on both sides fails a vector | — |
| DTA-047 per-case databases, spliced SQL, path readers | Yes (one splicing test, the stale reader, the fixture) | Corrected by the target | Installed functions in the read class on the head; programs obtained from generators where a temporary function is needed; no text slicing or path reading of production SQL; stale reader fixed now (§4.6, §5.2) | No test reads `semantic/sql/*.sql` by path; expression checks create no database per case | Each SQL retirement moves its readers in its commit |
| DTA-045 invented host refusal | Yes | Corrected by the target | Per-field perturbation of the parent profile comparison; real-peer reach control; the resources test reduced to propagation (§4.3, §4.4) | Removing a field from the parent comparison fails a test | — |
| DTA-044 reuse tested only where correct | Partly (oracle skip outcome, cache support) | Corrected by the target | Perturbation tables: safety cases now, precision cases with the production identity decisions (§4.4) | Each listed mechanism has a case where reuse must not happen, asserted by literal outcome | DA-068/069 decisions add precision cases |
| DTA-042 composition restated; model and release mismatched | Yes (grading support, record contracts, pack support) | Corrected by the target | Production acquisition for scenarios; the model bound from the release; one PDF recipe composer; one recipe-extension helper (§5.1) | No support module types the statistics bundle; the grading scenario's model is the release's | DA-073 moves composition into the model |
| DTA-038 head key coverage | Yes (key function; closure analysis) | Corrected by the target | Executed native bodies as closure sources; artifacts by content (RC07) (§4.2) | Adding an import to an executed body changes the key; touching an artifact without changing it does not | Step 5 provisioning builders: confirm they are reached from the construction entry |
| DTA-040 per-test directory in PDF identity | Yes | Changed | Refined: the directory is production's spool workspace. Recipe and binding split; per-consumer recipes built in the consumer's clone, never sealed; bounded memo (RC08) (§4.2) | No seed sealed for a per-consumer recipe; memo bounded | Production moves the workspace into a runtime binding (then recipes become seedable) |
| F06 PDF capture per consumer | Yes | New; corrected by the target | Completed-source seed stage for consumers whose claims start after capture (§4.2) | Those consumers clone the stage; capture-claim consumers still build | Depends on DTA-040's binding |
| DTA-043 executor from private fields | Yes | Corrected by the target | Public constructor with a prepared kernel recipe; native I/O replaced only; formula pinned once by literals; builder in a support module (§4.3) | No `__new__` of the executor in tests; reservation read from the executor | A production native-I/O seam, if added, replaces the method replacement |
| DTA-046 encoder realignment | Audit | Corrected by the target | Identity-bearing fake; multi-survivor drop case (§4.3) | An off-by-one realignment fails a controlled test | — |
| DTA-048 real GPU lock | Yes | Corrected by the target | Ordinary test asserts retirement inside `external_gpu` without the real slot (§4.7) | No ordinary-lane test opens the host lock | — |
| DTA-039 chain replay and repeated verification | Yes (lifecycle, publication) | Retained in part; deferred in part | Doubled role-script spawn and policy comparison removed; per-process verification and per-clone replay kept as required; incremental head deferred (§4.2) | One spawn and one comparison per clone | Incremental head: after the conversion settles, stored results show head builds on appended-only changes |
| DTA-034 remaining substitutes (manifestation) | Partly (`control_frontier`) | Corrected by the target | `_page` validated against the generated wire type and moved to support; `control_frontier` raises production's refusals; claim and population doubles wire-checked (§4.3) | Each substitute passes the wire validator on both sides | — |
| DTA-001 new refusal sites (manifestation) | Audit | Retained (existing contract applies) | The refusal contract helper applied to the listed sites (§5.4) | Each listed site pins SQLSTATE plus message or constraint after a positive control | A listed guard changes |
| DTA-009 test modules as support (manifestation) | Audit, partly checked through DTA-043 and DTA-034 sites | Changed | Sharp cases move to support with the boundary corrections; cohesive public builders move when touched (§5.5) | No private name imported across test modules; no relative import from a non-package directory | — |
| F07 renderer spelling in generated-SQL tests | Yes (two sites) | New; corrected by the target | Meaning asserted through pglast or PostgreSQL behaviour; authored expected tuple in place of production-to-production equality (§5.1) | A renderer change that keeps meaning passes | — |
| DTA-026 private executor state (manifestation) | Audit | Deferred | One remaining test writes interpreter-private state (§5.6) | — | An interpreter change |
| DTA-036 DDO-12 union | Audit | Retained with the plan | Plan-owned by TS-22 at DDO-12; expression-level checks are recorded as such in its mapping | As the plan states | DDO-12 |

## Findings that are not open

For completeness; no action is selected.

| Findings | State at `aca50eeea` | This review |
|---|---|---|
| DTA-024, 027, 028, 030, 031, 032, 006 | Corrected | No action; DTA-030's and DTA-029's cause recurs as DTA-037 and DTA-041, corrected above |
| DTA-008, 018, 025, 029, 035 | No longer applicable at cited sites | DTA-018's surviving observation about `current_pdf_source_factory` is F06; DTA-035's transfer obligation stays with TS-21 and the retirement rule (§4.6) |
| DTA-002, 003, 005, 007, 012, 016, 017, 021, 022 | Standing or held (mostly descriptions of sound evidence) | Preserved; DTA-005's narrowing is the cause of DTA-042 |
| DTA-004, 010, 011, 013, 014, 015, 019, 020, 023 | Not re-examined by the audit | Not examined here |

## Production findings the target depends on

The review selects no production remedy. These DA findings bear on the test design; their homes are
in the [broad account](../../audit/README.md).

| Finding | How the target depends on it |
|---|---|
| [DA-068](../../audit/execution-fit.md#da-068), [DA-069](../../audit/execution-fit.md#da-069) | The grain of kernel and implementation identity decides when precision cases of perturbation tables can be written (§4.4) |
| [DA-070](../../audit/semantic-model-and-authority.md#da-070) | The undeclared-member case for validity families is written with the production change, because it fails today (§3.1, §4.8) |
| [DA-071](../../audit/semantic-model-and-authority.md#da-071), [DA-076](../../audit/served-claims.md#da-076) | Hand-authored expected support closures and read identities stay independent of whichever encoding production keeps |
| [DA-073](../../audit/semantic-model-and-authority.md#da-073), [DA-074](../../audit/native-integrity.md#da-074) | Scenarios bind to production acquisition; posture tests keep hand-authored expected relations and roles |
| [DA-075](../../audit/execution-fit.md#da-075) | The cache-scope fixture owns isolation whether the key stays per instance or becomes content-based and shared |
| [DA-080](../../audit/boundaries-and-composition.md#da-080) | Production kept alive only by tests retires with those tests (§4.6) |
| [DA-033](../../audit/execution-fit.md#da-033) | A production release-admission operation would replace `admit_kernel`'s restated sequence (§4.8) |

## Rule impacts

RC07–RC10 are stated in the principal review (§12) and go to plan creation for confirmation.
RC01–RC04 of the 2026-11-13 review are accepted and carried (§11).
