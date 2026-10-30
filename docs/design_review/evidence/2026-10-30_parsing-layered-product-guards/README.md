# Layered product reference custody and historical source preservation

**State:** Tested within the scope below, 2026-10-30. The parsing coordinator owns package
acceptance and assembled qualification. No whole-pipeline or performance qualification is claimed.

## Historical source journey

`test_populated_abi10_source_survives_forward_guards` exports the real source at
`abd387838cfc05fdf0a1387481dec3d32df4ec68` with `git archive`. A separate Python process uses that
export ahead of the installed package, asserts the imported contract module belongs to the export
and reports execution compiler **10**. It uses the current shared dependency environment; it does
not relabel a current execution product or create another environment.

The historical code compiles and archives its release against an owned database at `semantic_0042`.
Its actual HTML producer captures `<p>A &amp; B <em>retained</em> source.</p>`. The dedicated writer
publishes the source product, completes the source task and captures the final source cut. This
seals source production; it does not claim a finished graded run.

The current process applies the forward migrations through `semantic_0044`. It compares the
original `ops.parsing_product` payload, product digest and contract digest byte for byte. The
current dedicated reader then opens the archived release, confirms its recorded ABI is still 10,
reads the original bytes and product, and uses both the qualified source reference and the
`BoundReader` source shim/common selector. All passed. The raw
[source receipt](raw/abi10-source-receipt.json) retains exact payload/original bytes and source-export,
manifest, release and product identities.

Historical reading does not confer current execution authority. The test separately confirms that
current pure binding refuses `start_run`, a dedicated writer cannot create a new run for that
already-admitted historical realization, and the dedicated admitter refuses current admission.
These checks execute against the real old release, rather than a compiler-number fixture.

## Shared semantic reference custody

The shared preparation boundary resolves interpretation `occurrence_ids` to local components or
nodes and requires the interpretation's structural occurrence. Assessment `evidence_ids` resolve
to local nodes; each interpretation input has a qualified dependency endpoint through the existing
`derived_from` relationship. Preparation cannot inspect an external immutable product, so the
native boundary additionally resolves that endpoint to an actual interpretation record under its
exact task, product key and content digest. A same-named structural node in a text product is
insufficient. Native references remain stable because products and their projections are immutable.

Independent missing-occurrence, missing-evidence and missing-interpretation examples fail both
preparation and direct restricted native publication. A forged input pointing to a real text node
passes the local shape/dependency check and fails actual native interpretation custody. The valid
interpretation and assessment publish and read back successfully. Scalar reference arrays also
receive the model's native string and cardinality checks.

`0041`, `0042` and `0043` are unchanged by this work. `0044` replaces the operation/publication guards
and admission descriptor. It extends the existing finite historical-reader profile and existing
shared product consumers; it adds no independent mathematical store or policy language.

## Commands and outcomes

The worker used the coordinator-authorized main environment with `PYTHONPATH` selecting this
checkout. Every database came from the existing owned native fixture routes; no operational
database was changed.

- **passed:** `PYTHONPATH=python/corpus-structure/src /home/paul/corpus-structure/.venv/bin/python -m pytest python/corpus-structure/tests/semantic/test_layered_parsing_products.py python/corpus-structure/tests/semantic/test_parsing_migration_preservation.py -x -q` — 14 cases, including the explicit historical write refusals. [Raw result](raw/passed-0044-native-guards.log).
- **passed:** the same interpreter and source selection with `pytest` over `test_parsing_products.py`, `test_layered_parsing_products.py`, `test_parsing_contracts.py`, `test_parsing_migration_preservation.py`, `tests/math/test_products.py`, and `test_native_closure.py::test_model_products_match_frozen_forward_revision` — 45 cases. [Raw result](raw/passed-focused-products.log).
- **passed:** scoped Ruff checks of the changed contract, publication, operation and test files. [Raw result](raw/passed-lint.log).
- **passed:** scoped Pyrefly checks of the changed contract/publication/operation modules and current test callers, with `--site-packages-path /home/paul/corpus-structure/.venv/lib/python3.14/site-packages`. [Raw result](raw/passed-types.log).
- **not_run:** global qualification, turn-end maintenance and operational migration deployment; these remain coordinator responsibilities.

The failed attempts are retained: using the maintenance principal for restricted publication
([receipt](raw/failed-abi10-maintenance-publication.log)), an incorrect fixture cut call
([receipt](raw/failed-abi10-fixture-cut-call.log)), using maintenance for a restricted read
([receipt](raw/failed-abi10-maintenance-read.log)), and an initial 0044 descriptor whose changed source
kernel had not yet been deployed ([receipt](raw/failed-0044-incomplete-kernel-deployment.log)). They carry
no passing credit. The final tests correct those concrete fixture/deployment defects.
