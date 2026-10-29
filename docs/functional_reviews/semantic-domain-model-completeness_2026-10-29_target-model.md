# Target: a complete connected semantic domain model

**Proposed · 2026-10-29.** Companion to the
[functional-extension review](semantic-domain-model-completeness_2026-10-29.md). This is a
recommended target specification for already-transitioned behavior, not implemented schema,
accepted scope or a qualification receipt. Names below identify semantic types and contracts;
subsequent implementation planning determines module placement and physical migration details.

## 1. Completeness and authority

The model is complete for the transitioned responsibilities when every behavior-relevant
concept, relationship, state distinction, operation and invariant below has an authoritative
definition and an executable realization, and every affected current consumer uses it.
Completeness concerns this declared domain. It does not mean arbitrary LinkML/OWL expressiveness,
automatic scientific decidability, universal workflow execution or unfinished legacy migration.

### 1.1 One composed model, with scoped ownership

| Definition scope | Authoritative content | Change and execution rule |
|---|---|---|
| Trusted execution model | Operational/evidence types, lifecycle definitions, privilege-sensitive invariants, implementation contracts and physical projection mapping | Authored with application code; versioned and deployed deliberately. Candidate corpus/domain data cannot replace it. |
| Semantic release | Domain classes/relations, values, qualification, identity, vocabulary/ontology snapshots, supported domain rules, scientific and analytical policy | Immutable admission products; a changed meaning produces a new release. |
| Bound execution | Selected semantic release, compatible execution-model revision, source/configuration dependencies, input realization/revision, operation versions | Construct once; immutable during a run or operation. Never consult latest definitions midway. |
| Instance state | Documents, reports, tasks, cuts, facts, assessments, receipts and published results | PostgreSQL remains authoritative; transitions use the protected applicable boundary. |
| Projections | Python boundary types, Core descriptors, SQL enforcement, RDF validation views, Arrow/DuckDB relations and explanations | Derived from the composed definition and identified inputs. They do not become independent writable semantic sources. |

Use LinkML modules for the logical types and a small LinkML-defined companion model for
behavioral contracts. Instances of that companion describe the finite trusted lifecycle and
the existing release-authored policy. They are typed data, not a new free-form YAML language.
Operational meanings that need not vary independently remain code-versioned; their presence in
the model does not make them user-replaceable workflows.

Ordinary domain functions own source placement, canonical identity, scientific algorithms and
grounding algorithms. Each has one linked operation contract and explicit implementation
identity/dependencies. A reference must resolve to that typed contract and its enforcing
implementation at preparation/deployment. Merely recording a callback name is insufficient.

### 1.2 Definition vocabulary

These are connected modeling types, not a requirement for one registry/table/object per row.

| Type | Required meaning and fields |
|---|---|
| ModelRevision | Stable identity, semantic scope, source/dependency identities and compatible execution/projection versions |
| ConceptDefinition | IRI, owned meaning, identity/equality contract, contextual scope, attributes and applicable relationships |
| RelationshipDefinition | Kind/IRI, typed endpoint roles, direction, cardinality scope, identity, qualification, ordering/multiplicity, permitted unresolved endpoints and authorization invariant references |
| LifecycleDefinition | Subject concept, finite independent state dimensions, initial construction, terminal predicates, valid combinations and owned transitions |
| TransitionDefinition | Subject/event type, allowed prior and resulting states, immutable bindings, guard/invariant references, effects, ownership and typed outcomes |
| OperationContract | Typed inputs/results, applicability, declared universe, effects, outcome alternatives, dependencies, determinism/precision where relevant, transition/projection references |
| InvariantDefinition | Owned semantic predicate, affected concepts/relations, evaluation scope, failure code and enforcing realization; local, relational, lifecycle or scientific responsibility |
| ImplementationBinding | Resolved owned implementation and version, input/result contract, supported features and execution placement; external effects and authority explicit |
| ProjectionContract | Source definitions/binding, selected relation kinds and universe, preserved distinctions, permitted omissions, precision/collection rules, completeness and lifetime |

Local constraints use supported LinkML metamodel expressions. Specialized predicates use
typed domain functions or Core expressions, rather than an invented general Boolean/SQL DSL.
Mechanical lowerings are shared. No two independently maintained predicates may define the same
invariant in the same scope.

## 2. Connected conceptual model

### 2.1 Interpretation, project and execution concepts

| Family | Concepts and required connections |
|---|---|
| Interpretation | SourceBundle contains named immutable SourceArtifacts; ResolvedDependencies names ontology artifacts and vocabulary snapshots; PreparationProfile selects supported semantics. PreparationResult is a prepared binding or structured diagnostics. |
| Release | SemanticRelease binds exact source inputs, products, compiler/library identities, execution-model compatibility and applicable policy/projection definitions. Archived release and project selection are distinct relationships. |
| Project and realization | Project has a generation-checked optional active-release selection. Realization belongs to one project and one immutable release, has a monotone data revision and a separate writability/completion predicate. |
| Method | MethodDefinition identifies implementation/version, input unit kinds, output report families, effects and resource needs. MethodConfiguration binds validated parameters and a configuration identity. |
| Source run | RunBinding fixes project, release, input realization/revision, source selection, method/configuration and all result-affecting dependencies. Run carries lifecycle, sealing and optional completed-result relationships. |
| Work | TaskInvocation belongs to one run, method/configuration, stage and typed unit/packet binding. Attempt identifies current holder and reclaim lease. Fresh work is a new invocation; retry/reclaim changes the attempt. |
| Agent work | WorkPacket binds source frame, readable evidence, proposal schema, known-input references and obligations. SubmissionResult has disposition and diagnostics; HeldSubmission is durable progress tied to the invocation, submitted attempt and packet. |
| Input cut | InputCut belongs to one run/release/input revision and captures effective completed task origins. FinalCut additionally seals source production; a nonfinal cut does not authorize final evaluation. |
| Result | TaskResultEnvelope records protocol completion and source outputs. EvaluationResult links final cut, operation/policy identity, output realization, source/proof receipts and finished run. |

### 2.2 Source, knowledge and decision concepts

| Family | Concepts and required connections |
|---|---|
| Source custody | Document identifies original bytes/content identity and source URI. RenditionBuild connects document, provider/configuration, task and normalized Rendition. Rendition contains typed Segments/Spans and source coordinate/macro context. |
| Source reports | SourceObservation belongs to the producing invocation/result envelope, report family/schema, provider and source unit. ObservationInput is a typed-role reference to an immutable prior report. Read/parse/measurement success does not itself assert knowledge. |
| Coverage and measurement | SourceCoverage and SemanticCoverage each bind family, declared scope, outcome and structured reason. Measurement binds metric definition, subject scope, typed value and producing operation. |
| Entities | Entity has scoped semantic identity and independent class Memberships. Display names, aliases, declared identity keys, external/source references and unresolved reference descriptors have distinct meanings. |
| Values and context | TypedValue variants preserve exact numbers/lexical reporting, units/basis, dates/instants, expressions, records, sequences and keyed maps. RoleBinding retains named endpoints/positions. Qualification binds modality, polarity, attribution, semantic scope, conditions and source-stated validity. |
| Propositions | SemanticFact identifies subject, property, canonical object and qualification within release/realization. AssertionOccurrence identifies an independent source item and its report object/context in that same scope; it points to its fact without losing occurrence identity. |
| Evidence and authorization | Evidence records source placement/provider. OccurrenceEvidence and EvidenceRole connect source spans to occurrences. Support, MembershipSupport, EntitySource, EntityInput and FactInput identify distinct authorizing relationships. |
| Decisions | Selection denotes the accepted projection within an evaluated context. Assessment targets a fact/occurrence/group or comparison, records rule/operation/version, outcome and uncertainty. AlternativeGroup has typed distinct fact members and a source-authored or evaluated reason. |
| Inference | InferenceRule describes admitted positive relation semantics. Derivation connects a conclusion to a rule/version and direct premise roles. Grounding traces to eligible source support or verified permitted input authorization. |

### 2.3 Existing read and analytical concepts

| Family | Concepts and required connections |
|---|---|
| Read | SnapshotBinding identifies release, realization and data revision. QueryDefinition/Selection specifies projection, universe and output filter. Handles/continuations bind that meaning for their declared lifetime. |
| Explanation | Explanation joins facts/occurrences with source custody, input lineage, assessments, groups and direct derivations in the same bound context. |
| Captured analytical input | CapturedPacket contains normalized relations from one captured PostgreSQL snapshot, projection and arithmetic profile. Capture identity is not an arbitrary label attached to an unrelated table. |
| Candidate analytical input | CandidateInput contains release-bound source/decision candidates supplied by consolidation. It states its cut/source provenance without claiming to be a captured database packet. |
| Local execution | AnalysisScope owns one selected DuckDB connection and borrowed readers/registrations/scratch. AnalysisResult is either a scope-borrowed handle or a detached materialized result. |
| Publication intent | AppendPublication and SnapshotDerivedPublication are distinct contracts. The latter requires exact source binding/revision; both use the protected publication route. |

These families cover the delivered semantic types, physical sem/data/ops/kb relations,
current producer/task/source contracts, consolidation/inference and query/analytical primitives.
Evaluation goldens and remaining legacy serving/intervention migration are outside this model's
implementation baseline.

## 3. Relationship semantics

Every relationship definition states cardinality over its declared context, not an unqualified
global count. Ownership, evidence support, inference premises, equivalence, control dependency
and analytical similarity remain different relation kinds.

Persisted entity references, fact identity, occurrence identity and alternative-group identity
are qualified by release and realization. Similar or reused local keys do not authorize
cross-realization joins or global identity collapse. Explicit EntityInput/FactInput lineage
connects authorized identities across generations without copying their old source occurrences.

| Relationship | Roles, scope and multiplicity | Meaning/authorization |
|---|---|---|
| Project selects release | Project → zero/one current release, with generation | Default for new work; neither retargets existing realizations nor rewrites runs |
| Realization interprets release | Realization → exactly one project/release; many revisions | Interpretation immutable; publication changes data revision, not release |
| Run consumes snapshot | Run → one exact input realization/revision and release | Frozen dependency/source/configuration binding |
| Task belongs to run | Invocation → one run/configuration/typed unit/packet | Unit is in the bound project/run; stage applicability follows method contract |
| Task reuses origin | Reused invocation → one completed non-reused origin | Complete binding equality, permitted done/empty origin; no fabricated new source occurrence |
| Attempt owns execution | Invocation → current attempt/holder/reclaim deadline | Atomic claim/reclaim; deadline permits reclaim, which changes attempt ownership |
| Result owns reports | Terminal result → ordered reports and coverage | Report identity/ordinal stable; protocol outcome separate from semantic outcome |
| Report uses report | Observation → typed-role input observations | Same admitted release/context and eligible completed source; ordered where input roles require it |
| Run captures rendition | Run/document → selected rendition/build | Preserves original bytes, normalization and provider/configuration provenance |
| Cut captures effective origin | Cut → selected invocation plus resolved result owner | Immutable selection; repeated reuse does not duplicate source assertion identity |
| Entity has membership | Scoped entity → class with establishment/support | Membership distinct from source assertion truth and display identity |
| Value has role/member | Parent value → typed child, role/key/position | Records/maps/sequences preserve their distinct semantics; no unordered-set coercion |
| Fact denotes relation | Subject + predicate + object + qualification | Canonical qualified meaning within release/realization; a binary relation can have several legitimate targets |
| Occurrence reports fact | Occurrence → one fact, source/item/report values/context | Repeated independent source items remain distinct; fact grouping does not replace them |
| Occurrence has evidence | Occurrence → evidence with explicit role | Valid source coordinates and cut membership, not merely existing foreign keys |
| Fact has support | Fact → occurrence(s) | Support agrees with fact meaning and preserves source multiplicity |
| Fact is selected | Contextual selection → one fact | Accepted projection; does not mutate fact identity or delete rejected source material |
| Assessment concerns subjects | Assessment → typed subjects/counterparts/context | Operation/rule/version and uncertainty explicit; display reason is not a hidden reference format |
| Group has alternative | Group → distinct fact members | Group identity is the unordered set of distinct fact members within release/realization. Reasons are provenance/assessments outside identity; occurrences are not deduplicated by it |
| Derivation uses premises | Conclusion/rule → direct role-identified premise facts | Admitted eligibility, exact compatible context and source-grounded proof required |
| Output carries input lineage | Output entity/fact → exact input entity/fact and authorized run | Preserves identity/context facts without attributing old occurrences to the new source |
| Run publishes result | Finished run/final cut → one output and immutable receipts | Source, proof, result pointer and completion visible atomically |
| Analysis uses projection | Operation → declared relations/universe and snapshot or candidate provenance | Output filtering cannot remove needed intermediate elements |

N-ary facts are represented by typed association/record values with named roles. Ordered
collections retain positions; bags retain member occurrences; keyed maps retain keys. Unresolved
endpoints are typed descriptors with scope/reason, never silently dropped or invented identities.
Ontology mappings do not imply unconditional entity merging.

Logical relationships drive boundary references and relational descriptors. The physical model
retains storage names, indexes, grants and fixed implementation choices. A required foreign key,
authorization guard or lifecycle constraint cannot survive only as an unenforced annotation.

## 4. Composed state and transitions

### 4.1 State dimensions and valid combinations

| Subject | State model |
|---|---|
| Interpretation preparation | Candidate input produces Prepared or Diagnostic result. Failed preparation does not create an admitted release. Archived/admissible are conditions of the immutable product. Project activation is a separate relationship, not one global release status. |
| Run | created, running, consolidating, finished, failed, cancelled; sealing/final-cut/result relationships are explicit associated dimensions |
| Task | pending, awaiting_agent, running, done, empty, failed, reused, skipped, cancelled; attempt ownership and submission progress are separate dimensions |
| Submission | NoHeldResult or HeldUncertainResult plus a checked current submission disposition. Held does not change task status to a new invented value. |
| Cut | Immutable nonfinal or final captured selection. Final implies the run's sealing predicate and no live source tasks. |
| Realization | Storage availability and writability are separate. Writable means the declared publication conditions hold; SealedEvaluationResult means an immutable completed-result relationship exists. |
| Knowledge | Occurrence establishment, source support, selection, assessment and derivation status remain separate contextual dimensions |
| Analysis | Input is captured or candidate; scope is open or closed; result is borrowed or detached. Computational completeness is independent of resource lifetime. |

Run invariants:

- created/running are unsealed and accept only applicable work.
- consolidating is sealed, has an immutable final cut and has no committed completed result yet.
- finished is sealed and has exactly its completed output and publication receipts.
- failed/cancelled are terminal; any already captured cut/diagnostics remain historical facts.
  They do not masquerade as finished scientific output.
- A terminal run cannot reopen. Starting another run is an explicit new identity.

Task invariants:

- pending/awaiting_agent have no current running attempt owner; running has a positive attempt,
  holder and reclaim deadline.
- Reclaim changes attempt/holder atomically. Deadline expiry alone does not manufacture a new
  owner; ownership fencing is the current attempt and holder.
- done/empty have protected terminal result envelopes consistent with their outcome.
  failed has explicit failure; reused has a valid completed origin; skipped has a reason.
- Terminal task content is immutable. An invocation's input binding is immutable throughout.
- Held progress records the submitting attempt and packet. Reclaim preserves durable progress
  without allowing the old attempt to authorize completion.

The existing physical availability strings building/active/retired/failed do not by themselves
define retirement or recovery capabilities. Do not invent such operations here. Model existing
completed-output sealing through its immutable EvaluationResult relationship and a shared
writability predicate; avoid a second independently mutable seal flag.

### 4.2 Allowed operation edges

| Transition/event | Prior applicability | Result and atomic effects |
|---|---|---|
| Construct project | Unused project identity, or an exact idempotent repeat | Project at generation zero with no selected release; conflicting initialization refuses |
| Prepare | Explicit immutable source/dependency inputs; supported profile | Prepared binding or structured invalid/unsupported/unresolved diagnostics; no database activation |
| Persist/reload | Prepared or archived exact release | Idempotent exact archive/reconstruction; content conflict refuses |
| Activate | Admissible archived release; expected parent and generation | Project pointer and generation advance together; old bindings unchanged |
| Construct writable realization | Existing project and compatible admitted release; unused identity or exact repeat | Project/release-bound empty realization at revision zero; no completed-result seal |
| Start run | Exact project/release/input revision/dependencies | New created run with immutable binding |
| Start source execution | created, unsealed | running; no semantic fact assertion implied |
| Schedule | created/running, unsealed, applicable method/unit/configuration | New pending/awaiting_agent task; or reused/skipped with the required origin/reason |
| Claim | Eligible pending/awaiting_agent; run accepts work | running; increment attempt, set holder/deadline atomically |
| Reclaim | running and reclaim deadline expired; run accepts work | running with a new attempt/holder/deadline, same invocation binding |
| Hold uncertain submission | Current running agent attempt/holder/packet; first uncertain checked result | Remains running; durable held result and deadline renewal |
| Complete producer/submission | Current authorized attempt; checked result contract | done/empty/failed as appropriate; source reports, result envelope and diagnostics committed together |
| Capture nonfinal cut | Bound open run and eligible effective results | Immutable cut; run remains open; no final-evaluation authority |
| Capture final cut | created/running; every source task terminal | Immutable final cut plus sealed/consolidating run in one transition |
| Evaluate | Sealed final cut; input revision unchanged; admitted policy | Compute candidates, decisions and finite proofs privately; no partial completed result visible |
| Finish evaluation | Valid source/proof publication and unchanged binding | Output receipts, completed-result relationship and finished run commit together |
| Publish ordinary batch | Writable realization; exact immutable batch and applicable expected revision | Native validated content, receipt and monotone data revision commit together; no run-finished claim |
| Replay | Matching prior operation identity/content and completed receipt | Return original receipt/result; no state mutation or reinterpretation |
| Fail/cancel run | Any nonterminal run under coordinated locking | failed/cancelled run; active tasks cancelled; existing held/diagnostic material preserved |
| Capture analytical input | Exact bound repeatable PostgreSQL snapshot and declared projection/universe | Materialized captured packet/profile; imported readers use that same snapshot before source resources close |
| Open analysis | Valid captured packet or typed candidate input/profile | Open scope owns engine/readers/registrations/scratch |
| Materialize/close | Open scope; result contract established | Detached materialized result may survive; close drains/releases owned resources and refuses later borrowed use |

A clean first agent submission may complete immediately. The first uncertain checked result
is held; a subsequent submission completes with its retained source report and explicit coverage,
including when semantic content is refused. This is automated behavior without human grading.
Packet/read obligations and source location checks remain required.

Unlisted operational edges are unsupported, not implicitly allowed by string membership.
Existing metadata-only changes and idempotent repeats are specified by their owning operations,
not permission to reopen terminal subjects.

## 5. Outcome domains and operation contracts

### 5.1 Distinct outcomes and their translations

Use discriminated result types per operation. There is no global success Boolean or global
status enumeration.

| Domain | Meaning |
|---|---|
| Protocol task outcome | Work completed, empty, failed, reused, skipped or cancelled; governs task lifecycle |
| Submission disposition | Held, completed with accepted structure, completed with refused/uncertain content, or refused for stale/invalid operation context |
| Source coverage | complete, partial, unknown, unsupported, failed, always for a report family and declared scope |
| Semantic coverage | complete, partial, unanalysed, failed, with originating source outcome/reason retained |
| Scientific assessment | Accepted/rejected/candidate/ambiguous and operation-specific equivalent/different/undecided; warning/refutation/unsupported interpretation remain explicit |
| Query knowledge | observed, absent or unknown relative to declared coverage/projection; response-page completeness is separate |
| Transaction result | Applied, exact replay, conflict/stale binding, run closed or recompute required; infrastructure failure remains distinguishable |

The owned coverage lowering is:

| Source coverage | Semantic coverage | Additional retained meaning |
|---|---|---|
| complete | complete | Only for the same family/scope after required transformation obligations are satisfied |
| partial | partial | Covered and uncovered/uncertain scope and reason |
| unknown | unanalysed | Originating unknown outcome and reason |
| unsupported | unanalysed | Unsupported operation/construct and its required capability |
| failed | failed | Typed source failure and affected scope |

A narrower/uncertain lowering cannot upgrade complete source coverage into complete semantic
coverage. An empty result establishes absence only when the relevant complete coverage and
operation contract authorize that conclusion. A done task can legitimately contain a refused
proposal report; this does not establish accepted claims.

### 5.2 Material operation contracts

Each row consumes the definition and state relations above; implementations do not independently
reconstruct their applicability.

| Operation family | Inputs, outputs and preservation |
|---|---|
| Interpretation preparation | Exact bundles, vocabularies, ontology artifacts, trusted compatibility/profile → immutable definitions/adapters/projections and diagnostics. Pure preparation does not persist or activate. |
| Release archive/activation | Exact manifest/products and activation token → archive/selected pointer or content/generation conflict. Replay does not reinterpret under current defaults. |
| Source registration/reading | Original bytes, source profile, provider/configuration and unit → rendition/segments/spans/report. Preserve original versus normalized representations and read versus assertion success. |
| Method scheduling/execution | Bound method configuration, typed unit and run context → invocation/attempt/result envelope. Resource configuration is explicit; meaning-bearing parameters are frozen dependencies. |
| Agent packet/submission | Exact source frame/schema/known references, packet/read obligations and attempt token → located/refused/held/terminal source report. No arbitrary proposal bypass. |
| Assembly and identity | Cut source universe, declared keys, typed values/context and exact input identities → canonical facts/occurrences/support/input lineage. No occurrence loss or heuristic unconditional merging. |
| Scientific policy | Release-owned rules, typed candidates, frozen math context/constants and comparison domain → selection/assessment/alternatives. Unsupported readings and undecided comparisons remain visible. |
| Positive inference | Bound eligible fact projection, admitted rules and exact compatible qualification → finite conclusions and direct proofs. Negative/hypothetical facts do not become positive premises. |
| Publication/evaluation | Immutable exact candidate bytes, native authorization and binding/revision → receipts and atomic result visibility. Whole-transaction retry has one owner; stale computed input requires recomputation. |
| Query/explanation | Correct release handles/snapshot, projection and universe/filter → typed rows, context, coverage, lineage/proofs and continuation. No cross-snapshot reference mixing. |
| Analytics/interchange | Captured or candidate input, projection/arithmetic profile, explicit conversions → borrowed or detached results. Preserve identities/collections/null semantics and label rounding/unsupported operations. |

Scientific algorithms remain explicit, independently understandable operations. Declaring a
relation functional selects the relevant accepted-value constraint and comparison domain; it
does not make every multivalued relationship single-valued. Distinct conditions and source
macro environments retain their meaning.

## 6. Executable realization and library composition

### 6.1 Preparation and constraint lowering

Resolve the combined definitions through LinkML SchemaView and strict typed companion instances.
The prepared binding contains the normalized concept/relationship descriptors, result adapters,
supported lifecycle/operation references and required enforcing implementations.

For a required invariant, preparation establishes an enforcing route appropriate to its scope:

| Invariant class | Authoritative definition and enforcing realization |
|---|---|
| Local shape | Supported LinkML type/slot/class expressions → strict Pydantic/boundary validation and faithful required native/graph checks |
| Local conditional rule | Deliberately admitted LinkML pre/postcondition subset → an actually enforcing validator/lowering; unsupported branches refuse |
| Relational consistency | Typed relationship/invariant definition → shared Core predicate/constraint/native guard; SHACL may validate a faithful selected projection |
| State transition | Transition contract and owned guard/effect implementation → Core guarded DML and native all-writer enforcement |
| Scientific assessment | Release policy plus typed domain algorithm contract → ordinary scientific/rule-engine operation and explicit uncertainty |
| Proof authorization | Admitted rule/eligibility/grounding contract → existing native proof validation and atomic publication |

Do not simply remove the compiler's unsupported-feature list. An upstream generator may omit a
construct that another generator supports. Required meaning is either implemented faithfully,
handled by an explicitly owned alternative, or refused. A diagnostic explaining absent support
does not itself deliver the requested modeled behavior.

Reuse existing prepared products and stable immutable validity. Represent supported-feature
information within current prepared/admission products, not a new alignment-lint system,
independent proof register or recurring audit gate.

### 6.2 PostgreSQL, Core and transaction enforcement

Retain shared SQLAlchemy Core metadata compiled from the trusted physical model. Logical
definitions supply semantic references and predicates; physical annotations retain names,
layout/index/grant choices. Trusted model changes use new frozen Alembic revisions. Candidate
domain releases do not install privileged functions or change physical tables.

Use guarded UPDATE/INSERT/RETURNING and existing locking to distinguish applied from conflict.
Native triggers/protected functions enforce allowed transitions and cross-object invariants
for every supported writer. Python preflight consumes the same owned definitions; it cannot
authorize a transition the native boundary would reject.

Preserve run/task lock coordination, immutable input bindings, current-attempt ownership,
final-cut barriers, source evidence authorization, native proof grounding, exact batch replay,
revision increments and finished-output immutability. SERIALIZABLE publication, receipt lookup
after uncertain commit and whole-transaction retry remain with the existing owner.

psycopg and pgpq lend bulk encoding/COPY to that transaction. The connection pool remains the
single process-level connection owner. pglast analyzes bounded authored SQL syntax/dependencies;
restricted PostgreSQL analysis establishes actual type/catalog/access binding. These mechanisms
do not become alternative domain authorities.

### 6.3 Graph validation and ontologies

Keep RDFLib generation/interoperability and LinkML/PyOxigraph native canonicalization.
Use SHACL Core/property paths and selected SPARQL constraints over a declared projection.
Default conformance remains inference none, external imports disabled and no implicit graph
mutation. Any entailment/rule expansion is an explicitly named derived projection.

Validate transition data as typed records with before/after references and captured state
versions when cross-state validation is useful. This does not require a persisted event ledger
or copying entire old/new corpora. Concurrent ownership and commit remain native obligations.

Occurrence, fact, qualification, evidence and proof nodes remain explicit. A qualified
rdf:Statement projection does not assert its bare triple. Named graphs label declared contexts;
they do not intrinsically establish provenance, valid time or a transaction.
SHACL cardinality counts distinct RDF values, so duplicate reports and ordered/bag members need
explicit identity/position records.

Direct PySHACL/PyOxigraph Store execution is an optional backend of this contract, to be
qualified before selection. Keep RDFLib as the baseline where this equivalence is unsettled.
No mandatory Oxrdflib layer or persistent graph authority is introduced.
Exact scientific arithmetic remains in the declared PostgreSQL/Python/analytical operation;
successful RDF literal transport does not establish an unlimited native decimal computation.

### 6.4 Analytical representations and transformations

Derive Arrow relation descriptors from the same logical/physical projection contract. Metadata
identifies the contract; validation of identities, scope, rows and actual source binding
establishes that a packet conforms. Capture uses one PostgreSQL snapshot; candidate inputs
identify their cut and decision universe separately.

Keep exact canonical/source lexical numbers separate from the existing DECIMAL(38,scale),
HALF_EVEN analytical projection and its rounding/overflow outcomes. PyArrow decimal256 support
alone does not authorize a wider DuckDB/pgpq arithmetic contract.

AnalysisScope owns local DuckDB state. Borrowed readers/relations cannot survive close;
materialized results can. Close is idempotent, attempts every owned teardown and preserves
individual failures/cancellation. Output limits do not narrow the required computation universe.

AppendPublication has no claimed source-snapshot derivation. SnapshotDerivedPublication requires
the exact input revision and operation/projection identity; changed input yields recompute-required.
Both preserve exact bytes/content replay through protected staging.

linkml-map remains a candidate for a specific supported shape transformation, with typed source
and target schemas, explicit joins/defaults/units/collection behavior and strict target validation.
The target does not depend on its incomplete SQL lowering. Keep existing finite qualified
SQL inference rather than adopt linkml-datalog's unqualified/datatyping/provenance assumptions.

## 7. Evolution, consumers and delivery boundary

Changing domain meanings, relationship constraints, vocabulary membership, scientific rules or
analytical interpretation creates a new semantic release. Changing the trusted lifecycle,
physical projection or privileged guard changes the execution model and, where needed,
its deployment migration. Existing bindings retain their versions and exact archived products;
old data is never silently interpreted under a new contract.

Current CLI/MCP source adapters, operation APIs, query/explain primitives and analytical kernels
consume the typed results and definition references relevant to their behavior. No new generic
introspection endpoint is required. A response may expose applicable transition/refusal
information where the operator or agent uses it; internal mechanics need not become product UI.

Delivery of the complete model requires all of the following, within the transitioned scope:

1. Every concept/relationship/state family in §§2–5 resolves to an authoritative executable
   definition. No decision-relevant string, payload interior or nullable-field combination has
   an independently reconstructed meaning.
2. Every material operation consumes that model and preserves its declared relationships,
   context, effects and outcomes through its actual current consumers.
3. Required invariants have honest local/relational/native/graph enforcement and observable
   refusal. Unsupported required semantics cannot pass admission by omission.
4. Source multiplicity, exact context, input lineage, scientific uncertainty, finite proof
   grounding, atomic publication and immutable replay remain intact.
5. The review's representative scenarios challenge the semantic definitions and lowerings with
   independent expectations at the boundaries that could be wrong.

These are functional delivery properties, not a new checklist runner or proof framework.
Existing passing checks remain passing; this document supplies a proposed stronger target,
not a new qualification result. The active pivot plans, accepted ADRs and remaining legacy
migration are unchanged by publication of this review.
