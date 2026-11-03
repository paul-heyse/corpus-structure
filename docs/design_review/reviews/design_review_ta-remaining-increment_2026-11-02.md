# Remaining test-architecture increment

## 1. Review contract and conclusion

**Design / target; combined focus; 2026-11-02.** Review TA-00 and TA-05–11 plus their integration
boundaries against core3.3, heuristics1.0, test-assessment1.2, the applicable evidence/fidelity
parts of CI1.4 and the repository binding. The functional target remains structured,
evidence-backed document knowledge exposed through typed questions and exports (DESIGN §1.1).
This is the test-architecture engagement, not a new whole-production audit.

Consume the test-audit publication `2d450cdd`, audited `2495baae` reconciled through `25a23118`.
Reconcile intervening current-only UM contracts and TA-01–04 at `af567228`, then the task-owned
dirty remaining implementation. Preserve the closed native increment and DTA-008/014/020's
corrected dispositions. The [coordinator](../../plans/test-architecture-and-evidence_2026-11-02.md)
owns execution state and all scheduled DTA dispositions. This review does not duplicate them.

**Decision: Accept scoped, Implemented/source-inspected strength.** The source implements coherent
owners for scenario preparation, released alias meaning, independently authored expectations and
actual interface observations. Five correction defects found during review were repaired in the
owning source before this conclusion (§7). No remaining material architectural finding is identified
in the inspected scope. This is not TA-12 required-union, operational product/provider or full-PDF
acceptance. The root reconciles subsequent changes and records the operator-selected final
verification boundary before claiming execution closure; the latest boundary is stated in §10.

Initial and correction source snapshots (SHA256); final refinements are separately reconciled
in §10:

| Source | Hash |
|---|---|
| `semantic/alias_policy.py` | `60f86692ce7671a78e0bafdfb99320fec16eba5c7ef0e2430419675ba22bc47a` |
| `semantic/prepare.py` | `59ccf95eba3c216aafee167d8e6088bc0383361992d2970912604e3a2a75c55f` |
| `semantic/regeneration.py` | `5c3800d823f2eb3fbff13c3198e7a020f2ae167cc275c9c3a3cc243c20e4df5f` |
| `tests/semantic/serving_scenarios.py` | `e7ee9d9b4cb245c08c14751d394910cd8e536d97fc88680478a08da4d72e3b66` |
| `tests/semantic/test_runtime_entrypoints.py` | `7a2781fdc15d072ec299bf374241f27c93cd1d27962f1e862cacae6b851107f1` |
| `tests/semantic/test_pdf_record_reader.py` | `065f0b53dba112470fa2fb3361dc464a23608c013344bb8313d446e77db64f56` |
| `semantic/query.py` (F03 follow-up) | `083a35f9927f2a83c8b4b8ecd8b4736ca5f46fb184fccb060cf32f7c1438a32a` |
| `tests/semantic/test_reference_counterparts.py` (F03 follow-up) | `5d5439a4429bd59e895c600b7ed4633778519c4bddc54bf64599a5318ae26ecc` |
| `semantic/rule_views.py` (F04 follow-up) | `416c6de03b7e66f5392ed9eb22d573740a500ef3f807b5bca2766471e27f1152` |
| `tests/semantic/test_scientific_rule_views.py` (F04 follow-up) | `4f01b61299357bbda9e2aad89597ba260872df3b1d0d441a613ab73799f28208` |

Paths above are relative to `python/corpus-structure/src/corpus_structure/` for production modules
and `python/corpus-structure/` for tests. The inspected breadth includes adjacent policy consumers,
archive hydration/compatibility, native ownership, source custody, serving and reference builders.
No native probes or product tests were run by this reviewer. Focused pure validation/accessor
diagnostics informed the T1 investigation and F04 follow-up below.

## 2. Responsibilities and fact fidelity

Pack acquisition and composition retain immutable inputs and one root preparation. The prepared
alias artifact owns resolved class meaning; consolidation and reference alignment both consume
`label_normalizer`. The pure core normalizer receives a selected class key and policy and does not
infer another spelling authority. Model declarations continue to own compared versus contextual
qualification. The toy model's compared `share` amendment is therefore a model correction, not an
exception hidden in its test scorer; filing reference remains provenance and attribution meaning-bearing.

Ordinary support modules now own agent source/task creation, domain cases, operation cases,
PDF staging and serving setup. Cases retain exact expected meanings. Independent hand-authored
semantic key bytes/digests challenge production encoding; the current reference helpers only
supply preparation/custody/effect mechanics. PgAdmin retains one resource lifecycle and TA-04
retains one receipt stream.

| Fact or claim family | Authority/fidelity | Identity and coverage | Consumer |
|---|---|---|---|
| Alias rules | Authored pack input, resolved once through compiled model authority | Per-class full IRI; versioned input/product and origin; ambiguity refuses | Consolidation and semantic alignment |
| Scenario population | Derived setup through current composed execution/MCP publication | Sealed session seed; recipe/preparation identity separate from fresh clone OID | Named serving readers only |
| Semantic key vectors | Independently authored bytes and literal digests | Complete scoped fact/occurrence tuple, including value/qualification distinctions | Python key functions and a native/read journey |
| Toy/trace expected outcomes | Authored controlled source and proposal meaning | Current release/run/source views; negatives refer to known controlled populations | Actual served queries/explanations |
| Native acquisition | Observed resource/purpose connection | Server lifetime, actual database/OID, principal and policy/deployment references | Existing qualification events/classifier |
| Historical references | Frozen witnesses with provenance | Deliberate selection/adjudication; successful reading is not current recognition | Kernel, coordinate and archive/refusal controls |

CI graph-analysis gates are not applicable as program-graph gates: no code graph, dominance or
reachability-as-dataflow claim is introduced. CI-04/10–13 apply by analogy to unknown validity,
hermetic preparation, pinned evidence and independent evaluation. A synthetic serving scenario
is not relabelled as a whole Statistics product or actual-provider extraction claim.

## 3. Contracts and constraints

The versioned `class-alias-input-1` declaration contributes release-affecting bytes and compiles to
`operation/alias-policy.json` / `class-iri-aliases-1`. Source-relative declaration IRIs and prefix
collision checks precede alias resolution. Each selected pack contributes its global articles and
ordered rewrites over its explicit import closure, with resolved per-class head words. Equal
policies coalesce; conflicting shared/imported-class policies refuse with origins. Neutral behavior
is explicit empty/absent policy, not a new imported-core default. Pseudo-statement matching selects
the released source-statement class.

Compatible canonical rule inputs coalesce. Incompatible non-alias policy refuses instead of
silently losing namespaced operation artifacts or choosing a pack-order winner. This deliberately
stops short of a general multi-pack operation dispatcher. Compiler14 archive reading remains
separate from executing an old nonempty unversioned alias interpretation. New alias meaning
requires regenerated/admitted current-profile input; no frozen artifact or migration is rewritten.

The session-local serving seed remains inside the existing leased `PgAdmin.database` context
through fixture yield. Population completes through real purpose publication; engines settle,
policy is compared and the source sealed/client-free. Before cloning, the fixture rechecks source
OID, policy and recipe/prepared source identity. Each consumer gets a new database OID, replayed
policy and authenticated reader. Returned population references do not authorize reading the
source directly. Varied query-pack/coverage and deployment/publication/write lifecycle cases stay
independent. ADR-0048 records the selected extension without replacing ADR-0032.

## 4. Composition and execution fit

FP-01/03/06 benefit from removing imports from test-host modules while preserving one maintained
implementation for each setup responsibility. Extraction is useful here because current consumers
have real shared mechanics; relocating every local fixture or defining a universal scenario
registry would not improve that boundary. Report count and Person identity scope are explicit
independent inputs rather than coupled defaults.

The prepared compiler cache and archived-reader cache remain distinct contracts. Fresh-interpreter
compilation observes one uncached construction and compares authored field/type/identity-group
obligations, not only self-consistent load/prepare hashes. Warm tests observe reuse and changed
source/profile/compiler-stack misses. This protects cold evidence while retaining legitimate reuse.

The concrete A4 premise is repeated native read setup, focused semantic feedback and assembled
qualification on one shared PostgreSQL deployment. A named session seed removes repeated
publication for three matching consumers; physical clones retain isolation. Source inspection
establishes that work removal, not a timing or capacity improvement. Hashing a bounded scenario
recipe and retaining one source lifetime are proportionate to the selected consumers; no persistent
lookup service, new janitor or test scheduler is added. One coordinated cold-deployment lane
addresses the observed shared lock envelope without assuming more parallelism is faster.

The formatter test observes production emitted bytes incrementally and uses real ordered-event
SQL/result objects. The large authored scalar exceeds the ceiling before encoding, so a regression
that joins the whole scalar into one output chunk is revealing. Scalar replay is normalized into
real production artifact parts in the adapter; the test is formatter evidence, not separate native
artifact-admission proof. Existing independent PDF scalar/record/fold controls retain that role.

## 5. Change and failure scenarios

| Scenario | Owner and preserved behavior |
|---|---|
| Add a class or change head-word/rewrite policy | Source-relative model preparation creates a new released policy/identity; both consumers share it |
| Compose disjoint/equal policies, then conflicting shared-core globals | Equal meaning coalesces; differing meaning refuses with origin; no insertion-order winner |
| Change model/profile/population recipe | Seed identity refuses reuse; cold routes retain their own preparation and effects |
| Failure before seed yield or abandoned consumer | Existing PgAdmin owner disposes only authenticated resources; clone consumers do not share mutable state |
| Reorder catalog declarations | Stable IDs retain mutation subjects; expected diagnostic correspondence remains authored |
| Give an invalid identity linked to a valid batch | Intended guard is reached with coherent support links; rollback preserves prior committed state |
| Close/cancel stdio or formatter output early | Existing transport/reader owner settles process, native session or actual result before database disposal |
| Change independent reference meaning | Adjudicate source-backed difference, retain original, explicitly select new version and affected consumers |

The domain-extension case is a new class/policy or compared qualifier; it changes model-owned
semantics rather than adding a branch to a query scorer. The mechanism-substitution case is
FastMCP/MCP subprocess handling or PgAdmin clone provision: consumers rely on explicit lifetimes
and identities, while independent expected results remain outside the mechanism.

## 6. Correctness, fidelity and architectural gates

| Gate | Source judgment | Basis and limit |
|---|---|---|
| G1 Authority | pass, scoped | Model/released policy owns semantics; source references and coordinator keep their separate roles |
| G2 Fidelity | pass, scoped | Full class keys, qualification roles, provenance and current/historical meanings remain distinct |
| G3 Validity | pass, scoped | Strict operation input parsing, explicit policy conflict and seed identity/sealing checks |
| G4 Hidden behavior | pass, scoped | Explicit input/purpose targeting remains; test-host imports are removed without ambient runtime defaults |
| G5 Consistency/lifecycle | pass by inspected structure | Seed owner context encloses clients/clones; real result and transport settlement controls exist; final native qualification remains root-owned |
| G6 Transformation/reuse | pass, scoped | One root compilation, complete recipe identity, immutable reuse and fresh committed effects |
| G7 Truthful claims | pass with stated limits | Source, targeted outputs and assembled qualification are distinct; no speed/provider claim follows |
| G8 Library fit | pass | Existing pytest/PgAdmin/preparation and FastMCP/MCP capabilities compose without a second framework |
| CI-G1 | pass by analogy | Declared meaning/unknown validity are retained; no code-graph inference claim |
| CI-G2 | pass by analogy | Current source/citation/run/release context is retained through the scoped served journey |
| CI-G3 | pass by analogy | Authored expected bytes/meanings remain independent of the output producer; controlled proposals are not provider-accuracy evidence |

## 7. Corrections identified during review

<a id="F01"></a>
**F01 — strict operation-input parsing before alias compilation (resolved by inspected source).**
The initial alias stage used `yaml.safe_load(...).get(...)` before the existing strict mapping
check. A null/list/scalar RULE_INPUT would leak AttributeError instead of structured preparation
failure, and duplicate keys entered a weaker parser first (FP-02/05; G3). `prepare.py` now parses
operation inputs once with `_SchemaYamlLoader`, checks mappings and reuses those values at alias
compilation. The coordinator owns its regression/qualification evidence.

<a id="F02"></a>
**F02 — preserve an already committed valid baseline after refusal (resolved by inspected source).**
An initial TA-07 assertion required zero rows/revision after its own successful publication.
That would confuse atomic refusal with erasure of valid state (DTA-001; FP-02/06; G6).
`test_native_copy_atomic_idempotent_distinct_occurrences` now captures committed rows/revision,
uses a distinct invalid batch ID, checks the intended membership FK and compares the prior state.
This is a correction to test evidence, not a demonstrated production data-loss defect.

<a id="F03"></a>
**F03 — lower validated structured filter operands to plain semantic values (resolved by
inspected source, 2026-11-02).** The new current toy inspection counterpart revealed that the
existing exact-object filter validated structured JSON into a release-generated `InspectionValue`
and passed that `BaseModel` directly to `value_codec.value_meaning`, which accepts plain values.
The valid request therefore became an unsupported-operand refusal (FP-02/05; G2/G3). This is an
existing filter-path correctness defect, not a newly selected query capability.

`ReadSession.object_predicate` now calls `value_meaning(plain(parsed))`, reusing
`consolidation.plain`. That converter recursively retains only explicitly set model fields and
preserves Python Decimal/date values; it agrees with the same converter used by
`FactValueLowerer.lower`. JSON serialization or indiscriminate default expansion would change
that boundary. Native `data.value_meaning` represents nested entity references as identifier
strings, consistent with the plain operand. Existing scalar/reference resolution, ambiguous
property interpretation and invalid-operand refusals remain in place.

The maintained inspection regression at `test_reference_counterparts.py` exercises original
independent quotes in a new controlled PDF paragraph, registry-based endpoint distinctions,
swapped/changed role identities, independently authored exact single-fact object filtering for
each distinct object,
dated qualification, evidence roles and original decimal spelling in the source observation.
The deliberately wrong role reports establish distinct representation, not source-truth
adjudication. This is not original HTML replay. Source inspection supports the fix; the root
owns its native regression result and final-source qualification.

<a id="F04"></a>
**F04 — project nested declared semantic Values at the rule-view boundary (resolved by inspected
source and a pure current-pack accessor diagnostic, 2026-11-02).** The T1 counterpart reached
finalization with a formula-valued `param_symbols` qualifier and exposed an accessor failure
reported by the rule engine as missing `claim.qualifiers`. The archived logical view and the
runtime claim both declare `qualifiers`; renaming the DSL field or adding a compatibility alias
would conceal the actual mismatch (FP-02/05; G2/G3).

The current statistics model declares `param_symbols` as a keyed `ParamValue` entry map, whose
`value` is an inlined Formula. The actual pure `_reference` projection retains each entry's
`key` and formula-valued `value`. Unlike the explicitly selected compact parameter-map view,
this map projects through `Semantic_ParamValue`. Previously `_value_projection` ran only for
direct `Qualifiers` fields; the nested semantic Formula then reached logical Value projection
without logical fields such as `t`. This is recursive projection locality, not a missing source
formula or a compact string map.

`build_rule_language.field_value` now projects declared semantic properties with logical range
`Value` wherever they occur, using their compiled `source_class` marker. Already logical fields
have no such marker. The selected compact parameter-map handling and ordinary keyed entry shape
remain intact; no hardcoded statistics property, altered source schema or rule ABI is added.
The independent minimal Entry-to-Formula regression observes both the authored key and logical
formula fields, then changes `a` to `b` and requires the rule to become false.

A focused pure diagnostic using the current statistics preparation and actual `_reference`
output successfully read `Claim.qualifiers`: `base_variable` retained its resolved identifier,
and both keyed entries yielded nested logical Values with the authored formula kind and `a`/`b`
expressions. This validates that boundary only. The root owns the pure suite, actual native T1
finalization, affected rule consumers and final-source qualification.

<a id="F05"></a>
**F05 — close the selected staging hub's orchestration consumers (resolved by inspected source,
2026-11-02).** Final TA-05 closure inspection found two maintained consumers of the explicitly
selected `test_pdf_staging.private_build` hub still importing the test host:
`orchestrate/test_pdf_cancellation_native.py` and `test_pdf_streaming_integration.py`. Moving the
fixture alone left their shared `native_batch` mechanic owned by the host (FP-01/03; A1).
`native_batch` now lives beside `private_build` in `pdf_staging_support.py`; the staging tests and
both orchestration consumers import ordinary support directly. Inspection of Python imports
under `tests/` found no remaining imports from the five selected initial test-host hubs. This is
selected-consumer closure, not a claim that all unrelated test-host imports were removed.

None of these corrections changes a repository architecture rule. Their current execution
disposition belongs to TA-08/07/09 and TA-12 in the coordinator, not a second review task ledger.

## 8. Library fit and enabling mechanisms

FastMCP4.1.3 `Client(StdioTransport(command,args,env,cwd,keep_alive=False,log_file=...))` makes the
real CLI tool exchange and failure/closure path observable. The installed transport disconnects
on context exit; MCP2.3.0 supplies a process kill scope and shielded tree shutdown. Public AnyIO
process observation retains actual process identity without a private SDK dependency or new
manager. The tests assert the process/native sessions really settle rather than treating an async
context shape as proof. [Tagged FastMCP transport documentation](https://github.com/prefecthq/fastmcp/blob/v4.1.3/docs/clients/transports.mdx)
was checked through Context7, together with the installed transport and MCP shutdown source.

SQLAlchemy's real cursor/result context is the formatter lifecycle boundary. Psycopg SQLSTATE,
primary diagnostic and named constraint are used through `DBAPIError.orig` to distinguish native
refusals. Pytest fixture dependencies retain source-before-clone teardown. The existing compiler
and archive cache mechanisms retain distinct validity scopes. None requires adopting pgTAP,
pytest-postgresql or a new JSON formatter; TA-01's disposition remains intact.

## 9. Alternatives and tradeoffs

A raw local/prefixed fallback in the normalizer would leave two consumers interpreting class keys;
compilation under one released profile localizes that decision. Global concatenation of pack
articles/rewrites would leak one policy into another; explicit effective-policy equality/refusal
preserves meaning without implementing an unneeded dispatcher. A blanket compiler bump would
reject current archives unnecessarily; release-affecting alias input/profile bytes are the scoped
transition. Empty historical policy remains explicitly neutral.

Repeated setup is valid but redundant for named read consumers; shared mutable DB or rollback-only
state weakens the real committed boundary. The selected source/clone composition pays one bounded
lifetime while retaining cold producer tests. Handwritten stdio exchanges and fixture formatters
remain useful only for narrower reference roles; they do not substitute for the actual interface.

## 10. Verification and limits

**Interface/source checked, 2026-11-02:** current owners, implementation and selected tagged library
surface were read. This reviewer executed no native tests, probes or database operations. Focused
pure validation and an actual prepared statistics rule-view accessor diagnostic were run during
the T1 investigation, with the bounded outcomes stated under F04. Targeted
implementation outputs inspected include `build/ta08-alias-pure-final.log` (8 passing controls),
`build/ta09-current-native-rerun.log` (two passing alias/toy controls),
`build/ta10-feedback-3.log` (three passing stdio modes), `build/ta10-cancel-feedback.log`
(one passing cancellation mode) and
`build/ta11-cancel-feedback.log` (two passing real SQL formatter cases). These are attributed
intermediate outputs, not a final-source required union or counts to add together. Later enlarged
formatter inputs and final mutations require the root's relevant rerun/adjudication.

The synthetic old compiler14 alias hydration test calls `reconstruct_release` on constructed
products. It proves hydration does not execute aliases; it is not a newly qualified genuine
pre-change archive through full custody/admission. Existing archive/open compatibility controls
retain that obligation. Trace and negative publication integration were still receiving native
feedback during this review; absence of a current result is not a pass. No actual-provider,
full-corpus, throughput or memory qualification is established here.

**F03 follow-up source checked, 2026-11-02:** inspected the exact-object filter, its existing
typed-to-plain converter, native semantic-value encoding and the maintained toy inspection
regression at the snapshot hashes above. No native check was run by this reviewer. The source
correction retains scoped acceptance; its final native execution result remains separate.

**Final refinement source checked, 2026-11-02:** the `pdf13_db` mechanism and retained PDF examples
now live in `pdf_integration_support.py`; eight importing consumer modules use it, with the
case-owned assertions remaining at their tests. F05 closes the selected staging consumers.
The alias-alignment kernel control declares its incompatible class and explicit current released
policy, then independently challenges class compatibility; it is not a preparation/archive test.
Trace assertions now name literal construction/parameter formulas and domains instead of only
requiring rows to exist. The stdio completion path additionally requires zero rejected items,
one accepted claim and its exact release-bound stored Alice payload. The formatter reconstructs
native logical identity from emitted JSON and compares it with the authored input, alongside
explicit JSON/float checks; independent scalar/fold controls carry identity-kernel correctness.
It remains formatter/SQL-cursor evidence, not native artifact-admission or provider evidence.

| Final refinement source | SHA256 |
|---|---|
| `tests/semantic/pdf_integration_support.py` | `ed8e7f4f974b20280c8f1f4f54d21ea0cdd32b1174f1b71dafd2ec8d9e1bf3b3` |
| `tests/semantic/pdf_staging_support.py` | `ac46fc7912070a3827eb0aca8b450967b70a84444abadfadca778cd961aa89c3` |
| `tests/semantic/test_pdf_staging.py` | `3245c26d200e4e13594b9161cb03758c6e3495b05c4b844fdb2cebc47891925e` |
| `tests/orchestrate/test_pdf_cancellation_native.py` | `c999159569b7a8c38eb16d24ba4c1eb8ffad893d4f6d60aad9f5566139a834dd` |
| `tests/orchestrate/test_pdf_streaming_integration.py` | `ee933cf96c08459b27733b08fef6e5c859dcfa4c52dc0bcbd7b322c2c5980baa` |
| `tests/evaluate/test_semantic_alignment.py` | `34cc83113abc9b68c6b5fff76e31b8306d1607e7fbdc98a5d5dbe4e1953674d4` |
| `tests/semantic/test_trace_counterparts.py` | `d240d3885c71996ea27cea6b2708ce868cb12e46c27f21bebe18740e67793cd8` |
| `tests/semantic/test_runtime_entrypoints.py` | `0be99971219ea82d25756180dc91724b3efab87846e10b8bf71fe4275b182914` |
| `tests/semantic/test_pdf_record_reader.py` | `a570643e467bb3b451374f08968073064cc62c4c354763768601b5992863d51a` |
| `tests/semantic/test_reference_counterparts.py` | `f4d05f413b35a35e3f630fc285abc8ec22b83640c9b0ac31d3c91cbc72f5d187` |
| `tests/semantic/test_scientific_rule_views.py` | `bc34db78e64c5a89f9c9539d2f227bd014b6a19462889860728909a19cf2c854` |
| `tests/semantic/serving_scenarios.py` | `83e1bcae02eee7e5a5565575a271797389048a70cab62f11216a77810a5c97b9` |
| `semantic/alias_policy.py` | `04160d0684f35a08ca44cb9c3b5d4ad61283481d3889f78321d3be2ca7c8cdd5` |
| `semantic/prepare.py` | `197bada67b364bca06e5696f56537cce62f1c8b5aa3e8b2f6757671b8f3b0247` |
| `semantic/regeneration.py` | `1d3e292a6f6bd1b1cc8e9535976feb58433beced106e41a95b863842cd4a6102` |
| `semantic/query.py` | `e46f1c67f8da58679b21cfb4d297c37951105c3685f83330b2efadd39bf30bb0` |
| `semantic/rule_views.py` | `416c6de03b7e66f5392ed9eb22d573740a500ef3f807b5bca2766471e27f1152` |

These hashes reconcile the root's integrated `turn-end` maintenance snapshot
(`build/ta-remaining-turn-end-integrated-source.log`); initial/correction hashes above retain
their earlier inspection context. These source refinements retain scoped acceptance. No tests or native operations were run by
the reviewer for this reconciliation. The root's earlier full-run capture does not automatically
qualify changed sources.

**Frozen provenance successor source checked, 2026-11-02.** The broad run exposed that the
TA alignment implementation changed an execution-model determinant. The append-only
`0095_test_architecture_source.py` successor declares frozen94 as predecessor and sets its
revision to `semantic_test_arch_20261102`. Direct artifact inspection found one non-recreating
transition, solely `data.execution_contract_descriptor()`. Its before state exactly equals the
corresponding frozen94 desired object; its after state exactly equals frozen95's desired object.
The 85-object desired inventory has no additions/removals or other changed object. Only the
descriptor body changes; owner, privileges, function signature and enforcement policy remain
unchanged. Parsed descriptor changes are exactly `inputs` and `model_id`, with the sole input
change `execution/implementation/alignment/semantic_alignment.py`; its new SHA256 matches the
current implementation bytes. The resulting model is
`execution:2097fec07ede65141a095dd85db49a6de65d485a76c38540bd9082401fb550f3`.

Frozen JSON/admission bytes equal the retained author output and wrapper pins. The descriptor
body hash `9b0df48c393060a8c30b4e02ece11dca798ac36cf475997fe7fc2c5a8984e314`
matches `execution_admission.py`; the other enforcement pins remain unchanged. The authoring
script now admits the predecessor catalog after outer rollback, addressing the earlier limit
of checking the unchanged Alembic revision alone. The retained author result reports one native
and zero ordinary operations; this is attributed execution evidence, not a test run performed
by this reviewer. The failed initial freeze-utility attempt is retained in
`build/ta-native95-freeze.log`; no predecessor was rewritten to conceal it.

| Frozen successor source | SHA256 |
|---|---|
| `semantic_alembic/versions/0095_test_architecture_source.py` | `ce87e0d7f199d4122ed88ced2cf1a983799256e1f6bf47154c4c6391d6024147` |
| `semantic_alembic/versions/semantic_test_arch_20261102_native.json` | `5c4c0ac8696f7362d573dc066986d9334c8ea678dd3570170d1852b858f835a8` |
| `semantic_alembic/versions/semantic_test_arch_20261102_admission.sql` | `dec2c8f01ccb1ce80eba2491adb88a750684e6128b8b57fdcf8b302343f7f6d8` |
| `semantic/execution_admission.py` | `90831c55dfa5dd65af304d41082d3f09f37ec44de800e8578b9746d15857b6c9` |
| `docs/design_review/evidence/2026-11-02_ta-native-policy-provenance/author.py` | `1de946f3baa367f54c2c87aee706c56ca95a5c92a1650756985d187b70344795` |

The first three paths are relative to `python/corpus-structure/`; the execution-admission path
is relative to its `src/corpus_structure/`, and the evidence path is repository-relative.
The evidence owner retains author/freeze/replay results under
`docs/design_review/evidence/2026-11-02_ta-native-policy-provenance/`.

**Latest operator-selected verification boundary, 2026-11-02:** fix the failing tests and rerun
those cases; do not rerun all tests. The root will retain the full frozen94 run and its four
failures, then record successor replay and only the four failed-case reruns. Scoped source
acceptance includes the reviewed successor, but neither that acceptance nor these selected
reruns establishes a complete required union or all-native qualification on frozen95. No such
claim or additional all-tests prerequisite is imposed by this review.

## 11. Authority and rule impacts

**Rule impacts: none.** ADR-0048 records the selected populated-source extension and preserves
ADR-0032. The alias correction realizes the current name/meaning authority under a new explicit
release profile; the toy compared-qualification amendment uses the current model's mechanism.
No blanket historical execution or new provider assurance is selected. Broader X2-01 and UM/PDF
acceptance remain at their existing owners. Review evidence does not close them.

## 12. Architectural decision

| Judgment | Verdict | Evidence |
|---|---|---|
| A1 Localize change | satisfied, scoped | Released alias owner and ordinary scenario support isolate consequential shared choices |
| A2 Encode meaning | satisfied, scoped | Class policy and qualifier roles govern both implementation consumers and current queries |
| A3 Compose capabilities | satisfied | Existing preparation, native lifecycle, pytest, SDK transport and result lifetimes compose |
| A4 Execution fit | satisfied, scoped | Named repeated work is removed while fresh committed effects and independent cold evidence remain; no quantitative claim |

**Accept scoped at the inspected source strength.** This does not certify the enclosing product,
all reference semantics or TA-12 completion. The root reconciles final source, consumer migrations,
required-union/reporting health and external blockers under the accepted execution boundary.
