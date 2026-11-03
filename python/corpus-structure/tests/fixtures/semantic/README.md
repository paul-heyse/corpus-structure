# Historical archive controls

These are immutable test inputs, not operational runs or admission evidence.
`reader-v10.json` and `reader-v10-analytics.json` are the genuine pre-change compiler-10
archives already retained for SP-I04. Their recorded aliases, scalar recipes and libraries
remain authoritative for reading.

`reader-v11.json` was produced on 2026-10-29 by the unmodified source at
`c98046a` (full commit in `historical_producer_commit`), using its real
`prepare_release` and `PreparationProfile`, from `reader-v10.json`'s source bytes.
`reader-v12.json` was produced identically from unmodified `b1e23ed` source.
Generation extracted `git archive <commit> python/corpus-structure/src` into a temporary
directory, launched the pinned Python with that directory as `PYTHONPATH`, and serialized
its returned manifest, profile, products and artifacts. No dependency installation or
compiler/profile relabelling was used. Both manifests retain the producing runtime tuple.

The current-only compatibility contract exercised by
`tests/semantic/test_release_compatibility.py` reads compilers 14, 15 and 16 with boundary ABI 12; execution requires compiler 16 with and its
recorded compatible runtime tuple. Compilers 10–13 and unknown future compilers refuse even
when their dependency versions happen to equal today's. The retained older files document
producer lineage and refusal inputs; their presence does not select a legacy runtime. Opening a
compiler-14 or compiler-15 archive remains distinct from rederivation, admission and execution.

Corrected alias execution requires the released `class-iri-aliases-1` product derived from
`class-alias-input-1` source bytes. Compiler-14 archives remain readable without rewriting frozen
products; an old nonempty unversioned alias policy refuses alias execution and requires forward
regeneration/admission. An absent or empty policy explicitly declares neutral normalization.

Historical reading is not admission. Cache controls additionally distinguish database identity,
current archive bytes, runtime changes, failed verification and finalized immutable projections.
Equal exported JSON Schema is explicitly insufficient for acceptance compatibility.

A hypothetical intentional boundary change starts with an independent acceptance vector and
its intended meaning, the proposed before/after difference and affected reader/runtime consumers.
Current compiler output is candidate evidence; it cannot authorize changing a historical archive.
Select a new product/profile and reference through the current release contract, retain these
originals and their producer revisions, and test explicit refusal where the runtime is unsupported.

`reader-v14.json` and `reader-v15.json` were generated on 2026-11-03 from the unmodified
source closures at `0046d5ceab5f2fd10c7f86c918c27af67c94e7ff` and
`1240f9b74c67cfded6a5dd09d53694a2f06174c8`, respectively. The generator used the same
`git archive` and explicit `PYTHONPATH` route described above, calling their actual
`prepare_release` and serializing original products without compiler relabelling. Their
independent Quote/decimal vectors and ComparisonProjection compiler identity are checked
by `test_genuine_supported_archive_retains_exact_boundary_and_comparison_meaning`.
