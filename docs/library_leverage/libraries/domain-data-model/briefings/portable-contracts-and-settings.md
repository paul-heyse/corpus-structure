# Portable schema contracts and process acquisition

**Source-inspected discovery, 2026-11-10; benefits Proposed.** [Baseline](../briefing.md).
References: [jsonschema](../../../../libraries/data_model/jsonschema.md),
[pydantic-settings](../../../../libraries/data_model/pydantic-settings.md) and
[prior boundary assessment](../../unified-model-boundaries_2026-11-01.md).

<a id="ddm-09"></a>

## DDM-09 — Broaden retained contract composition and useful error views

**Status:** substantial adoption with conditional broader resource/error consumption.
[pdf_payloads.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/pdf_payloads.py)
and [pdf_records.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/pdf_records.py)
prepare checked cached validators and explicit local registries. PDF record mapping uses `evolve`
to select supported union branches and preserve definition addresses.
[pdf_contracts.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/pdf_contracts.py)
retains schema bytes and rejects nonlocal references before validation.
[conditional_rules.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/conditional_rules.py)
checks generated Draft2019-09 fragments; report validation consumes derived report schemas.
It would be inaccurate to recommend reusable validators or local resolution as wholly new adoption.

**Mechanisms and broader use:** `Registry`, `Resource`, explicit specifications/dialects, resource
identifiers and anchors can package independently meaningful shared schemas without flattening
or copying their definitions. Pydantic shared definitions and input/output schema modes can serve
the same portable package where they derive from the owned executable contract.
`iter_errors` retains structured instance/schema paths, causes and nested union context; an
operator correction view could use multiple relevant failures rather than a generic first error.

**Concrete seams:** payload validation sorts yielded errors but selects the first; record
mapping takes the first error; conditional validation preserves a selected error's keyword and
paths; operation reporting converts one JSON error into an observation. These choices are
appropriate for refusal but may underserve a correction workflow needing several independent
errors or a nested oneOf explanation. Such a workflow can inspect the original errors once,
without adding another validator.

**Installed-source checks, 2026-11-10:** jsonschema4.26.0 `validators.py` carries unspecified
initialization settings through `evolve`; referencing0.37.0 `_core.py` adds resources immutably
and refuses conflicting retrieval callbacks when combining registries. Default jsonschema
resolution still has deprecated automatic remote retrieval; explicit registries avoid that route.
Local-reference admission in PDF contracts is a different sufficient boundary for its selected
profile. `validator_for` can fall back for an unknown dialect; selection alone is not proof of
recognized semantics. `ErrorTree` overwrites same-location/same-keyword errors, so it is not a
lossless replacement for the original error collection/context.

**Value:** preserve portable identity, offline custody and diagnostic fidelity across more
consumers, while retaining one semantic source and existing preparation lifetimes.

**Defeater and retain case:** shared schemas may only look similar while owning different
semantics. Native mapping deliberately supports a narrower reference grammar than general JSON
Schema; adding registered resources must not silently broaden it or rewrite definition paths.
Formats/defaults/content annotations are not automatic transformation or domain enforcement.
Existing first-failure reporting can remain the clearest contract where only refusal is needed.

**Next questions:** which actual repeated definition should evolve under one owner, and can
its consumers accept a registered resource with explicit dialect and immutable source bytes?
Separately, which correction operation needs error multiplicity or subsidiary union causes?
Use that consumer's bounded view rather than storing every diagnostic everywhere.

<a id="ddm-10"></a>

## DDM-10 — Improve acquisition explanation only where the configuration grows

**Status:** mature snapshot/source adoption; conditional diagnostics/introspection extension.
[settings.py](../../../../../python/corpus-structure/src/corpus_structure/settings.py)
constructs one root with nested plain models at entry points, uses constructor/environment
sources in explicit order and passes a snapshot down. Direnv owns environment acquisition;
dotenv/secrets providers are deliberately excluded. Origin reporting infers source from explicit
constructor values and field-set state. `known_env_names` enumerates the root and one nested
level, while rendering masks credentials and reports unknown names.

**Mechanism and broader use:** source wrappers can observe actual source contributions and
native source state; introspection could follow deeper nesting/aliases if those become real
configuration needs. Settings CLI environment-name introspection is another available route
when native CLI composition itself has value, rather than a required parser replacement.

**Installed-source check:** settings2.16.1 invokes every configured source and merges their
contributions; precedence does not prevent lower-priority source execution. `CliSettingsSource`
can construct its own fallback environment source, so its names need not describe an instance
with different acquisition settings. The native default-instance cache shares class-level state;
current entry-point snapshot construction already provides a bounded lifecycle.

**Value:** make a future nested/aliased configuration's actual acquisition understandable
without an independent approximation of names or merge provenance.

**Defeater and retain case:** existing configuration is mostly one nested level and has no
established need for cloud providers, refresh or a second CLI. Raw source contributions are not
validated values or complete final-field provenance. Logging them can expose secrets. A generic
provenance/cache/provider framework could cost more than the current small implementation.

**Next question:** is deeper nesting, aliasing or instance-specific source policy needed by an
actual operation? If so, can that source expose the necessary explanation under current masking
rules? Otherwise retain the current snapshot and audit the particular propagation path only
when a consumer fails to receive selected resources.

## Conditional territory

JSON Schema dynamic references, unevaluated properties, extension protocols, type/format checkers,
compound documents and property-based input generation deserve investigation for a concrete
contract the current profile cannot express. They do not supply complete standardized evaluation
output or validate factual support. Generated test inputs require independent expectations.

Settings structured files, filesystem/cloud secrets, decoding controls, nested-default updates,
CLI subcommands, async/reload integration and native caches remain in the coverage account.
They become useful when acquisition or operator needs warrant them. Settings continues to select
process resources; admitted releases and owned operations supply semantic defaults and policy.
