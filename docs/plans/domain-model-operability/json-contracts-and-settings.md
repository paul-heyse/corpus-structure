# JSON contracts and settings

**Status:** Partial implementation and N44 stage admission. **Created:** 2026-11-20.

This companion owns DMO-05 and DMO-06. The [coordinator](../domain-model-operability_2026-11-20.md)
owns package state, source dispositions, rule decisions and completion. This target is **Proposed**.
The original source baseline is `d4d606247`. The N43 amendment consumes the
[plan-improvement review](../../plan_improvement_reviews/domain-model-operability_2026-11-20.md)
at `7c17b403a`, including its inspected source `65db7f674`. Its I01, I03 and I09 changes below
are scheduled work. The 2026-11-21 amendment consumes the [N44 review][n44] at `c73a9e958`,
including its inspected source `6a445d6b6`. N44 I02, I05 and I06 refine host grouping, complete
JSON consumer migrations and the staged facade trial below. The existing package pins are Pydantic 2.14.1,
pydantic-settings 2.16.1, jsonschema 4.26.0, Psycopg 3.3.6 and python-rapidjson 1.25.
The retained comparison used referencing 0.37.0 and pg_jsonschema 0.3.4. Execution must compare
those selections with the current lock and installed extension before relying on the results.
[Integrated review O05–O09](../../functional_reviews/udm-operability-and-json_2026-11-20.md#O05)
[Retained library contracts](../../design_review/evidence/2026-11-20_json-boundary-contracts/README.md)

**Execution checkpoint · 2026-11-20.** Settings source reporting uses the public native source
composition and carries redacted leaf origins. The flat execution-policy override files use a
shared strict reader that preserves explicit override precedence and refuses missing or malformed
files. [ADR-0142](../../adr/0142-structured-selected-result-delivery.md) governs the structured
MCP delivery cutover. Selected CLI and MCP results use finite presentation numbers. Native scope
and original-byte custody keep their existing semantics. The remaining contextual transport
classification and RapidJSON consumers stay open in DMO-05.
Typed wire ingress now validates numerical constraints before projecting fractions to binary
floats. The prepared schema evaluator uses a temporary exact arithmetic view through stock
jsonschema, while PostgreSQL and the delivered values retain their declared numeric roles.
The managed selection passed 90 checks, including 11 independent PostgreSQL integer vectors
(`3bb6c2dd6e334439b15863bc1df4fd0c`).

The managed `ci model change capture PREVIEW_ID` route consumes an exact applied preview and
retains its connection to the original source preview. Candidate authoring consumes its captured
result. Local resource-aware schema preparation, one Pydantic-native lowering and receipt-owned
constraints are implemented. Routing controls `6d5b730421a0484cb03a5cfacc905200` and the
selected-source regression `4bc6857498514f19acfbdb7a21015486` passed. The native-only N44
preview and apply passed, and rollback-only candidate `783c6d12155742c88314cbd2a20cb5f1` froze
the successor. Registration `41191f5e359f4dfe8f82850ab53298be` and guarded deployment
`703ec35909e946cf94441cd844cb24f4` passed on the dedicated stage, with N43 as predecessor.
The change retires the superseded binding-row signature and two rich helper signatures.
The generated-only migration had no Python facade effects. The routing and drift controls
exercised staged application capture separately. Standard (`99efbb79896545149a94276e841ce20b`)
and Integrated (`711ac13a919d473fabe8fa36ea3db5e6`) passed guarded stage admission on source
`0ed2825f9`. A real change that generates a Python facade and the remaining native differential
controls retain their own acceptance obligations.

## Responsibilities and contracts

The operator chose consistent PostgreSQL-native numeric behavior. Whole-number fields use the
appropriate PostgreSQL integer type and Python `int`. Approximate calculations use PostgreSQL
`double precision` and Python `float`. Interchange carries ordinary finite JSON numbers. PostgreSQL
`jsonb` represents these numbers using its native `numeric` domain. An existing SQL field that needs
`numeric` retains its declared adaptation and comparison rule. The common transport domain carries finite numbers under the declared field policy.
Exact archived bytes retain their own custody.
[PostgreSQL JSON primitive mapping](https://www.postgresql.org/docs/18/datatype-json.html)
[PostgreSQL numeric types](https://www.postgresql.org/docs/18/datatype-numeric.html)

DMO-05 supplies the typed numeric domain, codec entry points, owned payload and failure types.
DMO-02 consumes those definitions for identity and retained-work eligibility. Identity encoding owns
stable determinant spelling. CLI presentation owns human output. Stored source bytes and archived
producer replies keep their original byte custody. DMO-06 owns schema preparation, engine agreement
and residual validation placement. DMO-04 owns event support work and consumes the same payload
and established-guarantee boundaries. DMO-07 presents the resulting facts through the existing CLI.

Resolve model constraints at the owning model or authored schema. One schema generator handles the
Pydantic-derived branch. Authored native wire schemas, LinkML projections and external schemas retain
their own declaration authority and explicit dialect. Each boundary either enforces a property or
consumes a property established under matching custody and premises. Current authorization,
revocation, publication and detached export checks have their existing enforcement points.
[Schema authority recommendation](../../functional_reviews/udm-operability-and-json_2026-11-20.md#O07)
[Validation placement](../../adr/0128-wire-contract-boundary-validation.md)

<a id="dmo-05"></a>
## DMO-05 — Consistent numeric interchange and settings

### Entry and resulting behavior

DMO-00 confirmed the PostgreSQL-native direction. ADR-0100 gives analyzed-scope numbers
canonical decimal equivalence. ADR-0142 now governs versioned structured MCP results, finite
presentation numbers, native cut identity and complete SDK response bounds. The selected cutover
and scoped checks are implemented. DMO-05 still owns the remaining numeric consumers, detached
representations and integrated delivery checks. Preserve D1 scope equality while migrating field
policies. Use independently specified Python/native vectors to identify any proposed convergence
of scope keys and obtain the specific decision before a versioned identity transition. The settings
slice and identity-independent consumers can proceed with the existing identity contract.
[Entry contract disposition](../domain-model-operability_2026-11-20.md#dmo-00) ·
[Structured delivery decision](../../adr/0142-structured-selected-result-delivery.md)

Begin with an inventory of actual numeric and JSON consumers in native request/result transport,
Psycopg adapters, `NativeRowResult`, execution-evidence leaves, scope values, kind bodies, prepared
pack models, continuations, exports, CLI/MCP and worker frames. For each typed numeric field record
its SQL type, supported range, comparison or rounding rule where meaningful, and current durable
representation. Include dynamic prepared packs. Classify hashes as source-byte custody, domain value
identity or incidental encoding so a transport replacement cannot silently move a producer basis.
This is a bounded migration inventory held in the package's implementation notes.

Use one stdlib `json` adapter for trusted owned JSON and text ingress. `json.loads` with
`object_pairs_hook` detects duplicate keys at every depth before PostgreSQL JSONB normalization.
`parse_constant` refuses `NaN` and infinity tokens. Check decoded float finiteness, including
fractional overflow such as `1e9999`. `json.dumps(..., allow_nan=False)` refuses non-finite output.
Keep the owned-value walk where it enforces inert JSON values and detaches caller-owned mutable
containers. Normalize decode, Unicode, unsupported-value and nesting failures to one public boundary
error. Retain existing byte budgets and reject unsupported PostgreSQL strings such as embedded
zero characters before insertion where the contract requires JSONB compatibility.
[Python 3.14 JSON hooks and limits](https://docs.python.org/3.14/library/json.html)
[Current codec](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_json.py)

Field validation supplies integer range and fractional semantics. Booleans remain distinct from
integer fields. Reject a fractional input at an integer boundary before conversion can round it to
an integer. During implementation settle the accepted integral spellings against both original text
and JSONB round trips, then generate the equivalent field checks for native requests. This boundary
classification may inspect the original numeric token. It creates no requirement to propagate an
exact decimal object through the product. Approximate fields accept the declared finite domain,
including a documented rule for signed zero where comparisons or identity depend on it. A database
value outside the supported transport domain receives an explicit refusal or typed conversion at
its owner. It must never silently become infinity or an unrelated integer.

Pydantic `TypeAdapter.validate_python(strict=True)` and model `model_validate(..., strict=True)`
validate already decoded values under the field's actual Python domain. Prepare reusable
`TypeAdapter` instances once for fixed types. Use `ConfigDict(allow_inf_nan=False)` or equivalent
field constraints for finite numeric models. Preserve tuple/date/enum conversion semantics at the
few JSON-shaped consumers that need them through one explicit ingress adapter, with tests for
that field's supported representation. `model_dump_json` serves typed presentation after the new
scalar policy is in place. Its bytes never define material identity. Module-level adapters retain
only immutable type preparation and need no independent runtime registry.
[Pydantic strict-mode contract](https://docs.pydantic.dev/latest/concepts/strict_mode/)
[Pydantic TypeAdapter](https://docs.pydantic.dev/latest/concepts/type_adapter/)
[Repository Pydantic overview](../../libraries/data_model/pydantic.md)

Configure Psycopg's public JSON adaptation through `set_json_loads` and `set_json_dumps` at the
owning connection/adapter context where JSONB is actually used. Native scalar SQL fields use the
library's normal type adaptation. The current storage call returns a text envelope, so migrate its
explicit decode route as well as connection loaders. Make the same numeric domain reach native
rows, cursors, detached exports and structured agent results. Worker modules retain their stdlib
boundary and finite-only contract. Share the required behavior without forcing them to import the
production package.
[Psycopg JSON adaptation](https://www.psycopg.org/psycopg3/docs/basic/adapt.html#json-adaptation)
[Current connection adapter](../../../python/corpus-structure/src/corpus_structure/core/db/store.py)
[Current native storage call](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_storage.py)

### Consumer transition and retirement

Deliver the migration by complete consumer boundary. The execution-evidence finite codec is an
implemented foundation. The first remaining N44 I05 slice is detached-export manifest framing and
metadata, with its writer and reader changed together. Give that metadata an explicit structural
contract. Authenticate the manifest bytes before interpreting its metadata, then verify the listed
content bytes against that manifest before use. Compare actual emitted bytes and use the archive's
versioned format when the transition changes required bytes. Keep content hashes and original
payload custody with the archive owner. Faithfully convert
useful retained data or regenerate incompatible derived data through the current route.

Follow with one native result read and its continuation, replacing recursive key-name detection
with the explicit field meaning of that contract. Then complete the actual consumer inventory across
native requests/results, rows, workers, exports, prepared packs and agent delivery. The illustrative
read is the first integrated delivery and leaves the remaining consumers visible in the inventory.
LinkML slot declarations and the existing generated Pydantic or native wire shapes own field meaning.
Use `SchemaView.induced_slot` or `class_induced_slots` where effective class-level declarations are
needed. An ordinary nested user field named `analyzed_scope` receives its ordinary value meaning.
Scope-bearing fields retain D1 equality and their independent Python/PostgreSQL vectors before
conversion. Keep the separate finite presentation projection. Retire each superseded decoder,
value alias and external-runtime dependency when its consumers move and retained-data disposition
is usable. This first metadata slice can proceed independently. Complete the staged facade trial
before a later slice changes both generated native and Python contract bytes.
[N44 I05][n44-i05] · [N43 review I09](../../plan_improvement_reviews/domain-model-operability_2026-11-20.md#I09) ·
[Detached export owner](../../../python/corpus-structure/src/corpus_structure/serve/demand_export.py#L435) ·
[LinkML effective slots](../../libraries/data_model/linkml.md#5-python-runtime-and-programmatic-schema-manipulation)

Migrate wire and row aliases, execution evidence and exports with their owning contracts, then
remove the superseded branch in `wire_json_loads`. Replace encode-to-validate paths with the
appropriate model or adapter call. Move target fingerprints and genuine value hashes to DMO-02's identity
owner. Measure response bytes with the actual delivery serializer once. Parse each selected-source
event once at its ingress and carry the owned result through its consumers. Consolidate SQL JSONB
literal spelling at its existing generated-SQL owner, preserving frozen bytes or scheduling a
forward native transition when they change.

Use ADR-0142's implemented structured MCP route for affected consumers and resource replay.
FastMCP 4.1.3 `ToolResult` and MCP 2.3.0 `CallToolResult` carry one structured payload through the
shared delivery owner. Its complete SDK serialization includes delivery metadata before checking
the byte limit. Confirm that machine and human consumers use supplied native IDs and handles for
identity-sensitive operations. Retire remaining Decimal string/tag bridges that serve only
transport as their consumers migrate. Typed scientific values and archived bytes retain their
own interpretation and conversion obligations. Preserve partial and unknown standing, bounded
output and current live authority during the remaining delivery qualification.
[D8 agent interface](../../design/D8-agent-and-query-interfaces.md) ·
[Structured delivery](../../adr/0142-structured-selected-result-delivery.md) ·
[Complete MCP response owner](../../../python/corpus-structure/src/corpus_structure/intervene/mcp_results.py) ·
[FastMCP result reference](../../libraries/python_introspection/fastmcp.md) ·
[DMO-02 identity and recovery](execution-identity-and-recovery.md)

When the caller inventory is complete, remove unused RapidJSON adapters, dependency declarations
and external-runtime custody surfaces. The selected stdlib path removes the need for a routine
RapidJSON upgrade. If a surviving byte-sensitive consumer still requires RapidJSON, establish its
bounded role and compare 1.25/1.26 vectors and acquired callable custody before using the 1.26
embedded-NUL fix. `Decoder.start_object`/`end_object` can expose pairs for duplicate checking in that
conditional route. The 1.26 claim is release-note evidence. The current runtime contract also
covers distribution, interpreter and native extension provenance, so updating an adapter alone
cannot establish execution correspondence.
[Current runtime profile](../../../python/corpus-structure/src/corpus_structure/semantic/external_runtime.py)
[RapidJSON 1.26 changes](https://github.com/python-rapidjson/python-rapidjson/blob/v1.26/CHANGES.rst)
[Decoder hooks](https://python-rapidjson.readthedocs.io/en/latest/decoder.html)

<a id="dmo-05-settings"></a>
### Independently viable settings slice

**Scoped implementation · 2026-11-20.** Private PostgreSQL workers use the actual
`EnvSettingsSource` naming policy and `known_env_names` to clear both modeled database profiles
before installing the acquired private settings. The existing Nemotron environment selection is
preserved. A regression covers nested and case-insensitive deployment overrides. Full settings
source and provider factory consolidation remains open.

The N43 Standard regional attempts found stale spaCy and HanLP shared-host inventory despite
equal provider inference identity. The stage runtime was reacquired through the existing runtime
owner. Acquire and compare the selected host residents together at preparation so a stale sibling
cannot surface after PDF publication. Keep inference identity and runtime inventory distinct. The
selected-host preparation result belongs to DMO-01 and is consumed by the worker and its DMO-07 explanation. This settings slice
supplies the effective validated sections and redacted origins used to acquire that result.
[Selected-host preparation](execution-identity-and-recovery.md#selected-host-preparation) ·
[Regional observations](../../design_review/evidence/2026-11-20_dmo01-02/README.md#bounded-regional-stage-recovery)

Resolve settings once and pass validated sections to acquisition, workers and provider factories.
Use the existing `known_env_names` and native environment policy to derive private-cohort scrubbing,
including nested prefixes. Preserve constructor-over-environment precedence unless a confirmed
policy changes it. Add an origin-reporting `PydanticBaseSettingsSource` after value sources and read
its public `current_state`/`settings_sources_data`, retaining redaction. A source that only reports
origins must contribute no settings values. Use `settings_customise_sources` to compose that source
and `JsonConfigSettingsSource` for the execution-policy file after verifying its merge and precedence
against current behavior. Validate profile/credential/authoring-target reconstruction through the
owning models. Catch `SettingsError` at the common accessor and translate it through the CLI's
existing error path.
[Pydantic Settings custom sources](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#customise-settings-sources)
[Earlier source results](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#accessing-the-result-of-previous-sources)
[JSON file source](../../libraries/data_model/pydantic-settings.md#52-json-yaml-toml-and-pyprojecttoml)
[Current settings owner](../../../python/corpus-structure/src/corpus_structure/settings.py)

Derive preparation and guarded reacquisition from the same selected-host grouping rule over
project, interpreter and script. DMO-01 owns the supported-population check. If releases are
intentionally single-group, enforce that invariant at declaration and both entry points.
Otherwise observe each supported group independently and report an unsupported provider on its
actual binding. Supply each group its validated settings and redacted origins. Observe once per
group, with provider-specific model resources still checked by their owners. Retire the
first-resident environment shortcut when the shared rule serves both paths. Check mixed groups
or their explicit declaration refusal, a stale selected resident, an unavailable unselected
resident, a wrong target OID and a resource changed after preparation.
[N44 I02][n44-i02] · [Selected-host owner](execution-identity-and-recovery.md#selected-host-preparation)

Use the existing preflight to establish environment correspondence. The existing
`preflight_pm2_runtime` selects the project and interpreter and runs
`uv sync --locked --check --offline`, followed by the worker's preflight. A lock check establishes
environment correspondence under its declared options. `importlib.metadata` supplies installed
distribution metadata for the existing authenticated RECORD inventory. Compare that execution
inventory separately from `NativeProfile.identity_projections()` and the provider's inference
attestation. The guarded reacquisition operation binds the exact release and acquired target,
records both identity projections and feeds the normal runtime binding owner. A transport-only
change can retain inference meaning while changing execution custody. Provider startup verifies
premises that may have changed since preparation. [Runtime preflight](../../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py#L23) ·
[uv environment checks](https://docs.astral.sh/uv/concepts/projects/sync/) ·
[Python distribution metadata](https://docs.python.org/3.14/library/importlib.metadata.html) ·
[N43 review I01](../../plan_improvement_reviews/domain-model-operability_2026-11-20.md#I01)

Retire bare construction of nested settings sections, hand-kept environment scrub prefixes, private
origin extraction and unchecked `model_copy(update=...)` paths as each actual consumer moves.
`MethodSettings` derives defaults from the same validated route. Product environment variables
become fields while CI lane controls stay with `ci`. Removal of `llm` and `gpu` sections receives a
separate consumer assessment if selected, independent of the historical SET-01 disposition.
Migrate provider factories and private-cohort launch inputs in the same slice that supplies their
validated settings. Retire ambient provider reads, duplicate resident lists and the evidence-only
`refresh-host-runtime.py` operational reconstruction as the normal guarded acquisition route
serves their consumers.

### DMO-05 completion

Run targeted checks for ordinary finite fractions, signed/unsigned zero, integer boundaries,
null/omitted fields and typed out-of-range values across PostgreSQL, wire, cursors, exports, CLI/MCP
and worker readers. Independently assert integer/fraction classification before coercion. Reject
duplicates, NUL/trailing data, invalid Unicode, non-finite input/output, overflow and excessive depth
with the documented boundary error. Check that mutating the caller's original nested object leaves
the owned snapshot stable. Retain comparison vectors for archived bytes and generated native SQL.

For the first manifest slice, independently verify the original trusted manifest hash before
metadata decoding, changed content refusal, valid old-format interpretation under its recorded
contract, and actual new bytes when a format transition is needed. For the native read and
continuation slice, compare neighboring contextual fractional values, large integral decimal
tokens and ordinary nested objects containing a field named `analyzed_scope`. Assert that the
declared scope retains D1 equality while the ordinary object follows its own field policy.
Check the actual structured MCP result and SDK metadata against the complete response budget.
The display projection may approximate fractions while supplied IDs and handles retain the
authenticated native basis. These cases establish the slice and leave the remaining inventory
as explicit DMO-05 work.

Verify `CORPUS_DEPLOYMENT__URL` is absent from private-cohort child environments, every selected
Nemotron consumer receives `CORPUS_NEMOTRON__ENDPOINT`, invalid settings yield one bounded error,
and redacted origin reports match the effective precedence. Product provider qualification belongs
to DMO-08. DMO-05 completes when every inventoried consumer uses the target route, superseded
transport code is removed and required durable representations have a usable conversion or fresh
regeneration route. For the shared-host prerequisite, cover valid spaCy with stale HanLP and the
reverse pairing, an unavailable unselected provider, conflicting cache roots or thread policy,
and an interpreter or resource changed after preparation. Confirm the early mismatch is reported
before upstream PDF computation or a native claim, with the selected operation and corrective
route. Verify redaction and constructor/environment precedence through the existing CLI output.

<a id="dmo-06"></a>
## DMO-06 — One schema per authority and deliberate validation placement

**N43 groundwork · 2026-11-20.** Wire and execution evidence use the shared prepared
validator. Draft 7 lowering now validates the provider receipt member tuple. The global wire
digest changed. The four cases that refused on N42 passed on matching N43 in a private
PostgreSQL cohort. N43 was deployed and the Standard archive verified on stage. DMO-05's strict
finite codec is used for execution-evidence receipts. Scope normalization retains D1 meaning.
The D8 delivery change followed this groundwork under ADR-0142. [Selected evidence and wire digest](../../design_review/evidence/2026-11-20_dmo01-02/README.md)

### Entry and schema realization

Consume DMO-05's settled numeric domain and the DMO-00 decision on moved native wire contracts.
Explicit registry and dialect hardening can start on the current domain while affected consumer
migration proceeds. Use jsonschema 4.26.0 `validators.validator_for` only after checking that `$schema`
is present and names a supported dialect. Run the selected class's `check_schema` once during
preparation. Supply an explicit immutable `referencing.Registry` containing captured resources,
with no automatic network retrieval. Cache prepared validators by schema digest, dialect and trusted
resource-context identity through the existing bounded preparation mechanism. A changed registry
basis requires a different prepared result. Translate `ValidationError` paths and context into the
existing structured correction-detail representation, without exporting sensitive instance values
or depending on `best_match` message ordering.
[jsonschema dialect selection](https://python-jsonschema.readthedocs.io/en/v4.26.0/api/jsonschema/validators/)
[Referencing registry](https://python-jsonschema.readthedocs.io/en/v4.26.0/referencing/)
[Repository validator overview](../../libraries/data_model/jsonschema.md)

Use one Pydantic `GenerateJsonSchema` subclass for Pydantic-derived schema generation, explicitly
selecting validation or serialization mode at the consuming contract. Put closed-object, minimum
length and tuple-member constraints in their owning model. The generator handles the selected
project dialect, including Draft 7 lowering of `prefixItems`. Use `WithJsonSchema` for scalar schema
contributions that are deliberately stable. That annotation alone cannot pin the whole generated
schema, so compare contract vectors and trigger the declared native transition when bytes move.
Keep authored wire YAML, LinkML-derived kind schemas and external contracts authoritative for their
branches. Remove the execution-evidence `close()` rewrite and other duplicate lowering once all
consumers use the common generator. Replace detached readback's hard-coded Draft 7 validator with
the explicit dialect of the body schema.
[Pydantic schema customization](https://docs.pydantic.dev/latest/concepts/json_schema/#customizing-the-json-schema-generation-process)
[Current wire generator](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_wire.py)
[Execution-evidence generation](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_execution_evidence.py)
[Detached kind readback](../../../python/corpus-structure/src/corpus_structure/semantic/demand_results.py)

Keep Draft 7 explicit for the current authored wire. Require explicit dialects on every generated
SQL schema and classify LinkML/external body keywords in their actual dialects. Establish a portable
profile at Python/PostgreSQL shared boundaries using the retained differential cases. Fixed digests
use explicit length and an ASCII hex pattern. Variable-length patterns require strict end-of-input
semantics. Keep `format` advisory in this profile and move consequential comparisons to typed domain
checks where shared engine behavior differs. Test narrow numeric bounds against the actual native
`pg_jsonschema` functions and Python values. Matching schema bytes and engine-family names each
leave version, options, numeric adapters and interpreted behavior to establish.
[Retained comparison and limits](../../design_review/evidence/2026-11-20_json-boundary-contracts/README.md)
[pg_jsonschema 0.3.4 source](https://github.com/supabase/pg_jsonschema/tree/v0.3.4)

If the portable profile cannot express an actually required pattern, investigate an ECMA regex
implementation with `validators.extend` at the factory. If profile maintenance proves unsuitable,
compare a pinned Python `jsonschema-rs` backend using the same real schema/instance cases and numeric
adapter policy. Select either alternative only on the identified contract need and test its actual
version. Keep its decision and dependent changes in this package. An empty schema search or a
passing sample does not establish compatibility across an entire contract population.

### Validation, generation and cutover

The current native storage frontdoor already encodes requests, lets SQL validate before effects,
authenticates the installed contract digest and validates client results before commit. Preserve
that behavior and the SQL result check for internally committing calls. Inventory residual nested
walks, model validation, field copying and schema checks. Make one owned snapshot and one structural
check at each true ingress. Pydantic-owned structures use the model as their authority. Native kind
bodies checked on immutable write may carry that guarantee to trusted readers while the effective
contract and custody still establish it. Detached exports retain their independent Python check.
Live disclosure, domain rules, effect authority and revocation continue to run at their actual
boundaries. Remove `_validate_wire_value` encode/decode/encode cycles and repeated field deep copies
only when the replacement establishes equivalent ownership, including nested mutable values.
[Current frontdoor](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_storage.py)
[Wire-value ownership](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_ports.py)
[ADR-0128 placement](../../adr/0128-wire-contract-boundary-validation.md)

Use the existing per-family validator identities and receipt confirmations to decide whether
retained completion needs a family check. `ddo_require_episode_identity` still verifies original
intent/producer correspondence and payload digest on every use. The missing-family computation
can reuse a matching confirmation when an unrelated family changes. Check that an affected family
is revalidated and that a forged payload refuses even when every family identity matches. Retain
broad validation where a global premise actually changed. This also informs DMO-02's historical
draft reopening and DMO-04's per-intent inspection, without changing their native effect fences.
[N44 I05][n44-i05] ·
[Family validation owner](../../../python/corpus-structure/src/corpus_structure/semantic/completion_validation_native.py#L27) ·
[Unconditional identity checks](../../../python/corpus-structure/src/corpus_structure/semantic/data_completion_settlement_native.py#L685)

Reconcile generated source and installed SQL catalogs for validation sites, explicit dialects and
schema provenance before retiring checks. The prior raw counts of 55 calls in 42 functions versus
108 or 506 source matches count different material and remain un-reconciled. List the actual target
functions instead of adopting a historical count. Capture the fanout of the global wire digest to
all wrappers, generated call descriptors, frozen native artifacts, stored execution evidence and
continuations. Author the needed forward revision through existing typed generation and admission,
with preview of the actual affected bytes. Coordinate its client/consumer migration with DMO-05,
DMO-02 identity transition and DMO-08 stage qualification. Never hand-edit generated SQL to repair
contract mismatch.
[Global wrapper and descriptor generation](../../../python/corpus-structure/src/corpus_structure/semantic/native_protocol_authoring.py)
[Native call generation](../../../python/corpus-structure/src/corpus_structure/semantic/native_call_generation.py)

Draft 2020-12 remains conditional on another justified wire transition and a demonstrated reduction
of lowering machinery. Its selection requires the coordinator's decision route for ADR-0128's
Draft 7 clause and the complete artifact fanout above. The current design can finish with explicit
Draft 7 and common lowering. Persistent program/page cache codecs have no obligation here because
those tiers were retired. Preserve authored constraints and useful independent verification when
removing obsolete generator and codec tests.

<a id="prospective-source-cutover"></a>
### Prospective source and coordinated cutover

The N43 forward revision corrected receipt tuple validation and moved the global wire digest.
The first candidate refused after generated facade apply changed an indirectly captured dependency.
Its retry prepared the application from the applied bytes and passed. DMO-06 establishes the
exact source basis for the next affected application through staged capture.
[N43 transition evidence](../../design_review/evidence/2026-11-20_dmo01-02/README.md#native-transition) ·
[N43 review I03](../../plan_improvement_reviews/domain-model-operability_2026-11-20.md#I03)

Use the explicit staged route for the first representative generated-facade trial, before the
next consumer migration that moves both native and Python contract bytes. Derive the generated
population through the existing `native_facades()` registry. `ci model change preview` retains
the approved source/model basis and after-bytes. `apply` verifies and writes those bytes, and
`ci model change capture PREVIEW_ID` authenticates the applied after-state and its relationship
to that original preview before application/runtime acquisition. Candidate refuses a preview whose
application capture is still deferred. The CLI carries source identities, acquired target,
predecessor, settled effects and the next incomplete effect through interruption and same-ID
reopen. The generated source prerequisite alone leaves native/application qualification with
their owning stages.
[N44 I06][n44-i06] ·
[Facade output registry](../../../python/corpus-structure/src/corpus_structure/schema/code_generation.py#L81) ·
[Capture command](../../../python/corpus-structure/src/corpus_structure/cli/model.py#L1897) ·
[Deferred-capture guard](../../../python/corpus-structure/src/corpus_structure/cli/model.py#L2070)

In a controlled qualification source and target, add a small optional fixed-tuple field to the
provider receipt logical-member packet or another narrow nominal packet emitted through a native
facade. Select the packet only after preview demonstrates changed generated Python and native
contract bytes. Independently specify valid, wrong-position and wrong-arity values. The wire
renderer emits `list[...]` with an element union for tuple arrays, so its annotation leaves
positional meaning and arity to the prepared validator and native counterpart. Verify those checks
through both owners and compare actual after-bytes independently of the emitter's reported digest.
Interrupt after apply, reopen capture from the original preview, change an indirectly captured
facade and require an attributed refusal, restore approved bytes, and reopen between native
deployment and admission. Verify exact effect custody and Standard/Integrated application
continuity. Use a forward generated revision for the trial's native change.
[Tuple annotation renderer](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_wire.py#L959) ·
[Draft 7 tuple lowering](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_wire.py#L456)

Keep full prospective capture as a conditional alternative. Inventory affected constructors,
direct imports and `Path.read_bytes()` consumers. The existing
`acquire_data_operation_inputs(..., proposed=...)` seam may provide an immutable overlay only when
all affected consumers acquire that same view for runtime, capsule, compilation fingerprint,
inspection and patch generation. Reopen this alternative when the concrete inventory establishes
coherent acquisition and shows an operational hurdle it removes. Record the selected normal route
and retire its superseded capture path as consumers move. The initial trial uses staged capture.
[Compilation inputs](../../../python/corpus-structure/src/corpus_structure/schema/model_change.py#L347) ·
[Application input acquisition](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_preparation.py#L146)

Registration freezes the exact generated migration. Deployment, release/runtime admission and
project activation remain separate recorded effects with their own expected bindings. Reopen after
apply and after deployment to verify the supported same-ID recovery routes and known effects.
Use a forward revision for any later generated change. Retire superseded capture and generation
paths as their actual consumers adopt the single source basis. Both Standard and Integrated must
have legitimate acquisition under the applicable native revision. [Model deployment owner](../../../python/corpus-structure/src/corpus_structure/schema/model_deployment.py) ·
[DMO-08 qualification](qualification-and-adoption.md#dmo-08)

Alembic 1.20.1 `Config.attributes` passes the owning SQLAlchemy connection into the migration
environment. `MigrationContext.configure(connection)` and `Operations` execute the prepared
operations through that connection. Retain repository predecessor, target and effect custody around
those calls. pglast 8.7 `parse_sql` and `Visitor` attribute generated syntax and statement kinds.
Native catalog and admission readback establish installation. Pydantic `GenerateJsonSchema` mode,
explicit dialect selection and captured `referencing.Registry` resources supply the schema inputs
already described above. [Alembic connection sharing](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-across-one-or-more-programmatic-migration-commands) ·
[Alembic programmatic control](../../libraries/postgresql/alembic.md#8-programmatic-control-migration-state-inspection-and-validation) ·
[pglast reference](../../libraries/postgresql/pglast.md)

The global wire contract remains the selected boundary for this work. Investigate narrower versioning
only if the consumer census identifies independently deployable contracts and a lower total
migration and verification burden. Record the proposed version boundary, affected stored evidence,
continuations and clients, and the coordinator's rule decision before dependent authoring. Draft 7
and current SQL-request/client-result validation placement remain governed by ADR-0128. A dialect
or public result-shape change follows that owner's decision route with its actual consumers.

### DMO-06 completion

Run Python/PostgreSQL differential controls over the supported schema profile. Cover explicit and
wrong dialect, local and unresolved references without retrieval, tuple element rejection, digest
newline refusal, variable-width patterns and numeric boundary agreement. Check generated schemas
against independent expected shapes, and verify that DMO-05 type conversion cannot change the
property being validated. Test contract mismatch and off-contract result rollback through the
native frontdoor. A schema derived from the same faulty transformation cannot supply the sole
expected answer.

Use independent retained completions to show that an unrelated validator-family change can reuse
matching confirmations, an affected family requires its current check, and forged payload bytes
refuse even with current confirmations. Preserve these cases when retiring aggregate-kernel
expectations and duplicate residual validation. Revalidation retirement must identify the
unchanged premises that supply the retained guarantee.

Use a bounded call-count check or trace on affected routes to confirm one structural check at the
actual request/result boundary and the separate detached-export check. Verify stable owned values
under caller mutation. Reacquire the current cut, epochs and principal before new protected reads.
Check native artifact parity and legitimate client acquisition after the coordinated transition.
Exercise a tuple-schema change that also changes a generated facade and a derived profile that
reads that facade indirectly. Verify the selected staged route and any subsequently justified prospective route,
interrupted apply, reopen before candidate, a real authored or generated input mutation, reopen
between deployment and admission, and the application-only companion admission. Each input
mutation refusal names the changed source or contract basis. Confirm facade bytes, native digest,
archive and runtime correspondence through their independent owners.
Final source, provider and book evidence belong to DMO-08 and DMO-09. No numeric speedup claim is a
completion condition.

## Source coverage and unresolved questions

| Source item | Delivery or decision |
| --- | --- |
| Integrated O05, JSON O01/O02/O08, D4/D7/D8/D11 | DMO-05 numeric domain and one bounded strict codec, worker refusals, owned typed payloads and agent consumer transition |
| Integrated O06, JSON O03 | DMO-02 owns identity profiles and literal Decimal-tag collision assessment. DMO-05 supplies numeric semantics and migrates incidental encoders |
| Integrated O07, JSON O04/O05/O06, D2/D3/D5/D6 | DMO-06 validator factory, generator, declared dialects, differential profile and native transition |
| Integrated O08, JSON O07 | DMO-06 residual JSON validation and copying. DMO-04 owns event support acquisition and its bounded physical diagnostic |
| Integrated O09, JSON O10, D1/D9/D10 | Independently executable DMO-05 settings slice |
| JSON O09 | Consumer-owned shape families under DMO-03. This companion supplies shared Pydantic generation |
| JSON O11 | Explicit dialect delivered in DMO-06. 2020-12 remains conditional on a justified wire transition |
| N43 I01 | DMO-01 owns selected-host preparation. DMO-05 supplies validated settings, origins and guarded runtime reacquisition, including retirement of evidence-only refresh routes |
| N43 I03 | DMO-06 prospective-source investigation, generated facade capture, exact staged recovery and coordinated native/application admission |
| N43 I09 | DMO-05 consumer-boundary JSON migration, DMO-02 scope-identity decision and DMO-06 affected schema/native transition |
| [N44 I02][n44-i02] | DMO-01 owns shared host grouping. DMO-05 supplies group-specific validated settings, origins and same-inference transport refresh |
| [N44 I05][n44-i05] | DMO-05 starts with detached manifest metadata, then one native read/continuation and the remaining consumer inventory. DMO-06 uses existing validator-family currency while preserving unconditional integrity |
| [N44 I06][n44-i06] | DMO-06 runs a real staged facade/native change with independent tuple vectors, drift refusal, same-ID recovery and both application admissions before dependent migrations |
| Earlier codec opportunities | DMO-05 measures emitted size once, parses events once and consolidates SQL literal ownership. Alternate codecs retain their source-review triggers |

The retained review's unresolved non-scope float consumers and dynamically prepared Decimal fields
become the DMO-05 typed-boundary inventory. DMO-02 settles actual legacy tag collisions and affected
semantic identities. DMO-06 settles supported `body_schema` keywords, portable regex behavior,
installed validation inventory and wire-digest fanout. RapidJSON version-vector checks remain
conditional on a surviving actual consumer. These investigations supply concrete branch decisions
inside the packages.
[JSON review open checks](../../functional_reviews/json-boundaries_2026-11-20.md#open-checks)

[n44]: ../../plan_improvement_reviews/domain-model-operability-after-n44_2026-11-20.md
[n44-i02]: ../../plan_improvement_reviews/domain-model-operability-after-n44_2026-11-20.md#I02
[n44-i05]: ../../plan_improvement_reviews/domain-model-operability-after-n44_2026-11-20.md#I05
[n44-i06]: ../../plan_improvement_reviews/domain-model-operability-after-n44_2026-11-20.md#I06
