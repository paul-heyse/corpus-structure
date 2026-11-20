# JSON contracts and settings

**Status:** Prerequisite slices implemented. **Created:** 2026-11-20.

This companion owns DMO-05 and DMO-06. The [coordinator](../domain-model-operability_2026-11-20.md)
owns package state, source dispositions, rule decisions and completion. This target is **Proposed**.
The original source baseline is `d4d606247`. The N43 amendment consumes the
[plan-improvement review](../../plan_improvement_reviews/domain-model-operability_2026-11-20.md)
at `7c17b403a`, including its inspected source `65db7f674`. Its I01, I03 and I09 changes below
are scheduled work. The existing package pins are Pydantic 2.14.1,
pydantic-settings 2.16.1, jsonschema 4.26.0, Psycopg 3.3.6 and python-rapidjson 1.25.
The retained comparison used referencing 0.37.0 and pg_jsonschema 0.3.4. Execution must compare
those selections with the current lock and installed extension before relying on the results.
[Integrated review O05–O09](../../functional_reviews/udm-operability-and-json_2026-11-20.md#O05)
[Retained library contracts](../../design_review/evidence/2026-11-20_json-boundary-contracts/README.md)

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

DMO-00 confirmed the PostgreSQL-native direction and preserved the existing binding contracts.
ADR-0100 currently gives analyzed-scope numbers canonical decimal equivalence. D8 currently exposes
`selected-source-search-exact-json-v1` with `exact_json`, the native cut identity and a byte bound.
Use independently specified Python/native vectors to find any converging scope keys. Name the
actual D8 consumers and the field/version change before removing that public field. Preserve the
established rule in each case until the applicable change is decided. The settings slice and
typed consumer inventory can proceed independently. The settled numeric domain lets DMO-02 design
any needed identity transition while codec consumers migrate.
[Entry contract disposition](../domain-model-operability_2026-11-20.md#dmo-00)

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
implemented foundation. First move remaining identity-independent payload families where one
owned finite JSON value and prepared validator can serve the actual readers. Native request/result
transport, workers, rows, exports and agent results each migrate with their producers and consumers.
For scope-bearing boundaries, specify field numeric semantics and independent Python/PostgreSQL
vectors before removing the existing interpretation. A converging identity class requires the
DMO-02/05 decision route for ADR-0100. The bounded Standard cross-demand reuse case can retain its
current accepted D1 meaning while these consumer migrations proceed. [N43 review I09](../../plan_improvement_reviews/domain-model-operability_2026-11-20.md#I09)

Move the wire and row aliases to the declared finite domain with their consuming contracts.
Replace `wire_json_loads`'s `analyzed_scope` key-name branch with the explicit field policy at the
scope boundary, then remove the superseded branch and interchangeable JSON-value aliases.
Migrate execution evidence and exports to the same typed numbers, and replace encode-to-validate paths with the appropriate
model or adapter call. Move target fingerprints and genuine value hashes to DMO-02's identity
owner. Measure response bytes with the actual delivery serializer once. Parse each selected-source
event once at its ingress and carry the owned result through its consumers. Consolidate SQL JSONB
literal spelling at its existing generated-SQL owner, preserving frozen bytes or scheduling a
forward native transition when they change.

Move MCP typed structured results and their actual MCP and CLI consumers together. Keep the native
cut identity, bounded delivered bytes and explicit partial/unknown standing in the typed result,
then retire `exact_json` double transmission and Decimal string/tag bridges serving only transport.
D8's current interface and ADR-0100's analyzed-scope meaning need the coordinator's explicit decision route before this changes
their binding contracts. Typed scientific value representations or exact original-byte archives
have their own consumers and must be assessed before removing a tag. Preserve best-effort decoding
or migration where useful custody requires it. Regenerate incompatible derived data under the new
basis through the adopted execution route. Authenticate old exact-byte archives under their
recorded contract and convert useful values at that boundary or regenerate derived data.
[D8 agent interface](../../design/D8-agent-and-query-interfaces.md)
[Contextual identity decision](../../adr/0100-ddo-contextual-identities.md)
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

Use one acquired environment observation for all required residents of the selected host, with
provider-specific model resources still checked by their owners. The existing
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

**Scoped implementation · 2026-11-20.** Wire and execution evidence use the shared prepared
validator. Draft 7 lowering now validates the provider receipt member tuple. The global wire
digest changed. The four cases that refused on N42 passed on matching N43 in a private
PostgreSQL cohort. N43 was deployed and the Standard archive verified on stage. DMO-05's strict
finite codec is used for execution-evidence receipts. Current scope normalization and the public
D8 field retain their established semantics. [Selected evidence and wire digest](../../design_review/evidence/2026-11-20_dmo01-02/README.md)

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
Its retry prepared the application from the applied bytes and passed. DMO-06 must acquire a coherent
prospective source basis before preparing the next affected application. [N43 transition evidence](../../design_review/evidence/2026-11-20_dmo01-02/README.md#native-transition) ·
[N43 review I03](../../plan_improvement_reviews/domain-model-operability_2026-11-20.md#I03)

Derive generated facade outputs from the approved physical and logical model together with explicit
source migrations. Form one immutable prospective source view used for application preparation,
runtime capture, compilation fingerprint, inspection capsule, SQL explanation and exact patch.
The existing `native_facades()` output registry owns the generated population. The
`acquire_data_operation_inputs(..., proposed=...)` seam can supply overlay bytes to acquisition.
Trace derived profile constructors, direct imports and `Path.read_bytes()` consumers because their
actual dependency capture must see the same view. The bounded investigation ends with an identified
capture route for each affected facade and a choice between full prospective capture and the
explicit staged route below. [Facade output registry](../../../python/corpus-structure/src/corpus_structure/schema/code_generation.py#L81) ·
[Compilation inputs](../../../python/corpus-structure/src/corpus_structure/schema/model_change.py#L347) ·
[Application input acquisition](../../../python/corpus-structure/src/corpus_structure/semantic/data_operation_preparation.py#L146)

Use full prospective capture where all affected constructors can consume the view. Apply verifies
and writes the reviewed after-bytes, and candidate acquisition verifies those bytes against its
retained source and model basis. If a required constructor cannot consume a coherent overlay,
make generated-source apply an explicit first effect and capture the application from those exact
applied bytes as the second stage. The CLI retains the reviewed source identities, acquired target,
predecessor and next action so an interrupted invocation resumes at the recorded stage. A material
input change still produces an attributed refusal. A successful apply alone supplies the generated
source prerequisite and leaves application/native qualification with its own stage.

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

Use a bounded call-count check or trace on affected routes to confirm one structural check at the
actual request/result boundary and the separate detached-export check. Verify stable owned values
under caller mutation. Reacquire the current cut, epochs and principal before new protected reads.
Check native artifact parity and legitimate client acquisition after the coordinated transition.
Exercise a tuple-schema change that also changes a generated facade and a derived profile that
reads that facade indirectly. Verify the selected prospective capture or explicit staged route,
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
| Earlier codec opportunities | DMO-05 measures emitted size once, parses events once and consolidates SQL literal ownership. Alternate codecs retain their source-review triggers |

The retained review's unresolved non-scope float consumers and dynamically prepared Decimal fields
become the DMO-05 typed-boundary inventory. DMO-02 settles actual legacy tag collisions and affected
semantic identities. DMO-06 settles supported `body_schema` keywords, portable regex behavior,
installed validation inventory and wire-digest fanout. RapidJSON version-vector checks remain
conditional on a surviving actual consumer. These investigations supply concrete branch decisions
inside the packages.
[JSON review open checks](../../functional_reviews/json-boundaries_2026-11-20.md#open-checks)
