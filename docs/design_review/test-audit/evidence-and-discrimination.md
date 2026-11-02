# Evidence and discrimination

**Interface-checked by source inspection, 2026-11-02.** See the [baseline](README.md#baseline).
Positive evidence includes hand-authored exact native tuples, malformed inputs, explicit
SQL-null/JSON-null/absence distinctions, graph closure and report failures, scientific uncertainty
and definedness controls, independent geometric expectations and actual owned-child cancellation.
Sharing production validators for downstream setup does not invalidate those tests; independently
judging the validator itself requires a separate expected result.

<a id="dta-001"></a>

## DTA-001 — Some negative assertions do not distinguish the intended rejection

**FP-05, DP-03/23; H20; companion §1/4.** Current examples include `test_publication.py:234–275`,
`test_arrow_publication.py:176–195` and `test_pdf_record_native.py:195–204`. They accept any
DBAPIError, so the assertion cannot distinguish the guard named by the scenario from a foreign
key, privilege, lifecycle or unrelated preparation rejection. In the record case, multiple
binding fields are varied on a header naming a different product; no reason is observed.
The source-established weakness is limited to assertion discrimination, not a demonstrated
bypass of each guard. The previous count of32 bare catches and guard-message coverage estimates
are withdrawn. A bare catch alone does not establish that an alternative cause actually fires.

Counterevidence includes successful sibling baselines, one-field perturbations and reason-specific
matches in `test_pdf_record_native.py:218–233` and `test_native_closure.py:83–131`. The current child
graph cases now explicitly distinguish construction IndexError from hierarchy ValidationError;
they claim preparation, not native publication. This audit does not infer native correctness
from matching deployment bytes or parser acceptance, nor demand a test for every guard.

<a id="dta-006"></a>

## DTA-006 — Some assembled evidence assertions establish presence, not preservation

**FP-04/05, DP-23; companion §4.** `test_composed_journey.py:72–78` checks nonempty support,
evidence and source observations. It now checks exactly one Alice fact, so the former broader
row-cardinality criticism is removed for that case. `test_serving.py:254–262,501–523` and
`test_domain_operations.py:550–557,581–583,623–625,920` retain presence or lower-bound assertions
on particular preservation claims. Extra or wrong supporting rows can satisfy those predicates.
This is not an objection to presence checks where existence is the whole contract.

Exact fact/occurrence sets, qualifications, alternatives, source addresses and CLI continuation
checks in the same modules provide substantial contrary evidence. No suite-wide assertion
weakness or complete set-equivalence failure is inferred.

<a id="dta-007"></a>

## DTA-007 — Some load/prepare comparisons share the preparation cache

**FP-06, DP-09/23; H14/19/20; companion §1/3/5/6.** `prepare.py:529–536` keeps an eight-entry
cache; full verification calls it (`releases.py:558–560`). Comparisons of `load_release(...)`
with already prepared products in `test_execution_release.py:118,179,220`, `test_releases.py:167,
434,460` and `test_inference.py:426` can agree without independently recompiling cold inputs.
They establish the comparison/read path; alone they do not establish cold compiler determinism.

The old proposal-boundary cache allegation is removed: proposal_inputs now uses preview_schema.
Archive/current/lazy/runtime-refusal controls and fresh-interpreter checks in
`test_statistics_model.py:100–125` provide independent coverage. `test_pack_acquisition.py` also
positively counts composed preparation and forbids reacquisition. No stale-correctness defect,
cache thrashing or measured performance claim follows from these self-comparison sites.

<a id="dta-010"></a>

## DTA-010 — Positional mutations and generic diagnostics weaken catalog refusal claims

**FP-02/06, DP-24; companion §4/5.** `test_contracts.py:213–241` retains fourteen positional
catalog mutations and observes the first diagnostic code. Reordering a declaration can retarget
an invalid case while preserving that generic code. `test_execution_projection.py:106–123`
accepts any of five codes across different mutations, then checks diagnostic-field truthiness;
`test_effective_bindings.py:105` accepts statement-or-locator for several defects. These predicates
cannot establish the particular diagnostic correspondence implied by each case.
The complete expected diagnostic in `test_effective_bindings.py:145–155` is counterevidence and
shows the stronger contract can be tested without another validation framework.

<a id="dta-011"></a>

## DTA-011 — Semantic fact/occurrence key assembly lacks independent full-key vectors

**FP-04, DP-04/23; CI-12 by analogy; companion §1.** A search of semantic tests finds no literal
fact:/occ: digest vector establishing the complete semantic key assembly independently. Current
value meanings are hand-pinned (`test_value_codec.py`), and alternative groups assemble canonical
bytes independently. Those controls constrain components without fixing every full assembly
contract. Producer/native agreement alone can preserve a shared assembly mistake.

The footprint excludes PDF identity: `test_pdf_record_identity.py:34–95,239–279` has independent
bytes, fixed scalar/record/fold digests and native parity. Do not describe identity generally as
unexamined or impose a second implementation for every key.

<a id="dta-013"></a>

## DTA-013 — Some universal or work-observation assertions can pass vacuously

**FP-05, DP-23; companion §4/6.** `tests/math/test_property.py:125–144` returns for generated
strings yielding no tree, suppresses all health checks and finally requires only one read.
A shrink in the exercised generated cases is therefore not discriminated. The module explicitly
claims equivalence only for values the grammar reads; no parser-admission floor is inferred or
required here. This is an evidence limit, not by itself a demonstrated violation of that claim.
`test_statistics_model.py:57–66` retains all over a filtered generator without establishing that
the intended subset is nonempty. The hydration spy in `test_domain_operations.py:1224–1233`
lacks a positive loaded assertion. Later checks correctly establish lineage and omission of a
note, but not that the observed hydration route was exercised.

The 78-page coverage test explicitly reports parse-status rather than promising a status floor;
timeout jitter is documented. That policy alone is not a current defect. Independent fixed math
cases, a spike-page read floor, exact semantic outputs and explicit demand-forbidden-call tests
are strengths. The retired legacy parity assertion and old runtime shares are not current evidence.

<a id="dta-015"></a>

## DTA-015 — Product aliases and the normalizer still disagree on class-key spelling

**FP-02/04, DP-01/23; CI-12 by analogy; companion §1/4.** `regeneration.py:106` passes aliases
unchanged; `domain_operations.py:781` validates them and `:855,927` passes compact prefixed class
names. `domains/statistics/methods.yaml:35–36` keys head_words by local DistributionFamily, while
`core/keys.py:205` performs exact lookup. Thus the selected product head-word rule is not found
for that class. Semantic test searches found no head_words control. The independent core vector
instead supplies a prefixed key, so it does not challenge this composition mismatch.

This production cause is reported only to explain an evidential blind spot; repairs are outside
the audit. No current corpus merge count or newly executed normalization result is claimed.
Identity-slot mapping and declared rewrite behavior retain their independent protection.

<a id="dta-019"></a>

## DTA-019 — Frozen reference provenance is stronger, but deliberate update ownership is incomplete

**FP-04/05, DP-22/24; companion §4/6/7.** The math, LLM, ingest and locator builders now cite
frozen source paths and, for math/LLM/ingest, evidence record IDs
(`tests/{math,llm,ingest}/data/build.py` and `tests/data/locators/build.py`). The earlier origin ambiguity is corrected. They still describe
committed outputs as authority and scripts as provenance without a general adjudication rule for
a deliberate changed reference. `fixtures/tex/README.md` does name D1 §6.2 as its disagreement
owner. Exact manifest pins prevent accidental movement; parity-oracle holds and revisit reasons
in docs/pins.md do not cover all sentence-model/offset dependencies.

Whether each retained fixture is a lasting oracle or a completed port comparison remains material;
absence of a hold is not itself a semantic correctness failure. The current compiler14 boundary
explicitly refuses old compiler formats. Removed compiler10–13 support is not a missing current
reader. `tests/fixtures/semantic/README.md` still promises historical opening/answer journeys that
current tests removed; it is stale evidence guidance, not proof of runtime support.

<a id="dta-020"></a>

## DTA-020 — Historical producer/decoder premises superseded by current-only support

**FP-04/05, DP-23/24; companion §1/4/6.** The old compiler7/8 capture acceptance and historical
fact reconstruction cases are removed; `test_release_compatibility.py:38–47` explicitly refuses
retired compilers10–13/future. Current capture and archive tests use current prepared products;
synthetic obsolete products test rejection. ADR-0047 changes the obligation, so the earlier
historical-success diagnosis is withdrawn rather than pretending those readers were repaired.

Empty-predecessor upgrade controls do not alone establish populated current migration behavior;
actual frozen forward replay has its own evidence and UM owner. This audit neither rewrites
frozen artifacts nor upgrades retained receipts to fresh qualification. DTA-019 separately
records the stale fixture README support promise.
