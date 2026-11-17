# Current domain model map

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline and limits](README.md#baseline)). This is a diagnostic map of the model found in
source; the architectural owners keep authority. Paths omit
`python/corpus-structure/src/corpus_structure/`; `domains/` is at the repository root. It
replaces the map of 2026-11-05, whose owners (`contracts.yaml`, `contracts.py`,
`domain_operations.py`, `operations.py`, `publication.py`) were removed with the legacy
execution compiler on 2026-11-16.

<a id="current-model"></a>

## Where meaning is declared, compiled and realized

| Context | Declared in | Compiled or generated into | Realized by |
|---|---|---|---|
| Semantic definitions | LinkML `model/semantic/*.yaml`; pack `domains/<pack>/semantic.yaml` with terminology and ontology sources | `PreparedRelease` (`semantic/prepare.py:825–1060`; `semantic/types.py:236`): definitions, boundary recipe, effective bindings, vocabularies | Boundary adapters, statement types, rule views |
| Qualified relationships | LinkML slots; operation roles (kind, direction, cardinality, collection, presence, support) | `OperationRole` with input and output kind edges (`semantic/data_operation_compilation.py:1823–1829`); relational binding expressions | Native binding SQL |
| Operations | `__data_operation__` literals in 85 Python modules; declaration documents built in code; native operations from the protocol | `compile_data_operations` (`data_operation_compilation.py:806`) → `EffectiveDataOperationModel` (`semantic/data_operation_model.py:877`), archived as `data_operations.json`; generated calls, ids and ports | `orchestrate/data_operations.py`; `semantic/sql/data_operations.sql` |
| Which operations a release contains | Flags in the acquisition manifest, interpreted by hand-written composition ([DA-073](semantic-model-and-authority.md#da-073)) | Bundle and dependency composition | — |
| Products and kinds | LinkML product classes (`data-operation-*.yaml`); nominal kinds from schema; wire kinds from `data-operation-native.yaml`; physical tables in `data-operation-physical.yaml` | `EffectiveKind` with kind fingerprints; physical and relational generation | Native tables |
| States and transitions | `data-operation-native.yaml` lifecycle; per-operation state dimensions and transitions | Generated fates module carrying the protocol digest | Native guards |
| Policy and invariants | `EnforcementClaim` entries typed as documentation or checked (`data_operation_model.py:374–425`); LinkML conditional rules; policy YAML | Enforcement-claim resolution; boundary fragments | Implementation code and native SQL |
| Identity | Per-operation definition, eligibility and recipe identities; kind and implementation-slice fingerprints (`data_operation_compilation.py:2138–2233`) | `EffectiveIdentity` rows; `release_id` is the digest of the whole input manifest (`prepare.py:963–985`) | The native request key, which excludes release and runtime (`sql/data_operations.sql:1036–1042`) |
| Dependencies and support | Explicit `dependencies` and `potential_dependencies` id lists; role support (provenance, source, coverage, identity requirements) | Dependency edges; compiled `potential-producers` and `selected-dependencies` projections (`data_operation_model.py:705–731`) | Demand freeze; native consumed-producer closure |
| Validity family | **Not declared**; a hand list in SQL ([DA-070](semantic-model-and-authority.md#da-070)) | Lowered `validity_family` column | Native validity dispatch |
| Support-edge meaning and trust-scope key | **Not declared**; three encodings ([DA-071](semantic-model-and-authority.md#da-071)) | — | Validity, locks and scopes, change impact |
| Native authorization and guard membership | **Not declared**; code lists ([DA-074](native-integrity.md#da-074)) | — | Installation and admission |
| Contributions, publication, serving | `observations.yaml`, `read-projections.yaml`, `companion-projections.yaml` | Prepared contribution and record projections | Native SQL; one native read entry point validated through generated wire types |

## One model, and what sits around it

Inside the declared-data-operations target there is one compiled model per release. Four
declaration media feed it (Python literals, LinkML kinds, the protocol, schema-derived kinds),
their origins are tracked, and conflicting owners and unresolved references are refused
(`data_operation_compilation.py:823–830, 955–960, 1836–1838`). Semantic identity (recipe, kind
and slice fingerprints) is kept apart from build provenance (`release_id`), and the native
request key uses the semantic identity. That separation is what lets a result survive a new
release.

Around that model sit further inventories that it does not govern:

- the earlier core and system model, with its own generated code, revision log and pack
  schemas ([DA-072](semantic-model-and-authority.md#da-072));
- the hand-written release composition ([DA-073](semantic-model-and-authority.md#da-073));
- the hand lists inside the native kernel and its installation
  ([DA-070](semantic-model-and-authority.md#da-070), [DA-074](native-integrity.md#da-074));
- the three encodings of the support graph ([DA-071](semantic-model-and-authority.md#da-071));
- the hand-kept file lists that stand for "the code that produced this answer"
  ([DA-076](served-claims.md#da-076)) and the hand-written description of the scientific
  kernel ([DA-077](served-claims.md#da-077)).

The model therefore covers operations, kinds, roles, states and identities well. What it does
not yet hold are several facts about how those operations are *governed at run time*: which
validity rules apply, what a support edge means, what must be guarded, and which code an
answer depends on.

## How a change becomes recomputation

Traced through source for this refresh:

- **Source bytes.** Product ids are content-addressed, so new source gives new inputs and new
  request keys.
- **A changed recipe, kind or result-affecting binding.** The recipe identity changes, the
  request key changes, and that operation recomputes. Binding nodes that only affect
  eligibility are dropped from the recipe (`data_operation_compilation.py:2114–2135`).
- **A changed implementation.** It enters through the implementation-slice fingerprint in the
  recipe. Where the operation declares an opaque boundary, the fingerprint is much coarser
  ([DA-069](execution-fit.md#da-069)).
- **Dependents.** They recompute only if their content-addressed inputs change, unless a role
  declares an episode identity requirement.
- **Runtime and execution profile.** Excluded from the request key. Distrust is applied by
  explicit revocation, evaluated when results are read.
- **Native kernel source.** Any change invalidates admission, reads and carried assurance at
  once ([DA-068](execution-fit.md#da-068)).

The unit of recomputation is the request generation. The unit of scheduling is the whole
demand, swept once per round.

## Strengths to preserve

- Operation facts are extracted statically without importing the target, acquisition is closed
  and workspace-relative, and a file that changes during acquisition is refused
  (`semantic/python_operation_sources.py:585–645`; `semantic/data_operation_preparation.py:145–155`).
- Enforcement claims separate documentation from checked enforcement and keep documentation
  out of the recipe.
- Generated fates, wire types and physical value sets derive from the one protocol file.
- Revocation is by selector with scoped epochs, validity is relative to the read boundary, and
  a directly revoked producer cannot be rehabilitated (`sql/data_operations.sql:1080–1085`).
- Unknown is kept distinct from absent in served reports
  (`serve/contribution_facets.py:150–187, 331–341`).

## Limits

The bodies of most model YAML files, the generators (`typed_generation.py`,
`native_call_generation.py`, `schema/generate.py`, `schema/stage_b.py`), `ontology.py` and
`conditional_rules.py` were not read. The library inquiry recorded on 2026-11-05 (LinkML,
Pydantic, RDFLib, pySHACL and others) was not repeated; it is in Git at `fbd3f2a98`.
