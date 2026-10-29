# Installed LinkML native RDF canonicalization

**Interface-checked, 2026-10-29.** Context7 was queried first for `/rdflib/rdflib` and
`/linkml/linkml`, then the installed pinned implementations were inspected. No production
files were changed and no full schema generation was repeated.

## Selected capability

Use `linkml_runtime.utils.rdf_canonicalize.canonicalize_rdf_graph(graph, output_format="nt")`.
The installed LinkML runtime already transfers the graph through N-Triples to PyOxigraph,
uses `Dataset.canonicalize(CanonicalizationAlgorithm.RDFC_1_0)`, explicitly sorts triples,
and serializes deterministic N-Triples. Both installed generators use this helper themselves:

- `.venv/lib/python3.14/site-packages/linkml/generators/owlgen.py:347–356`
- `.venv/lib/python3.14/site-packages/linkml/generators/shaclgen.py:196–199`
- `.venv/lib/python3.14/site-packages/linkml_runtime/utils/rdf_canonicalize.py:287–352`

`pyoxigraph==0.5.13` is already locked through LinkML runtime; invoking the LinkML runtime
API needs no new direct dependency. It replaces an avoidable Python graph-isomorphism path
with the library's supported native implementation. It preserves OWL/SHACL axioms and blank
node anonymity rather than inventing globally meaningful skolem IRIs.

## Exact limits

The helper implements RDF 1.1 string semantics: explicit `xsd:string` becomes a simple literal.
These have the same RDF meaning, but RDFLib distinguishes their Python `Literal.datatype`
representations. Numerical literal lexical forms such as `"01"^^xsd:integer` and
`"1.2300"^^xsd:decimal` remain present in N-Triples output. The probe disables RDFLib's own
parse-time literal normalization while checking this property.

The canonical blank node labels and artifact bytes differ from the old RDFLib algorithm.
This is a compiler/product-version change; exact archive checks should stay intact and newly
prepared releases should receive the updated compiler identity.

Relative IRIs or literal predicates trigger `RDFCanonicalizationWarning` **before** the helper
calls its RDFLib fallback. If the admitted schema profile requires standard RDF, convert that
warning to an exception to refuse the unsupported graph instead of silently restoring the
slow path. Preserve a separate explicit fallback only for a concrete nonstandard RDF consumer.
Generator options such as disabling abstract-class covering axioms or metaclass metadata
change graph content and are not equivalent performance replacements. SHACL's
`use_class_uri_names=False` changes shape naming/merging semantics, not the anonymous
property/restriction canonicalization problem.

## Bounded probe

Run:

```sh
uv run --no-sync python docs/design_review/evidence/2026-10-29_sp06-execution-fit/library/canonicalization_probe.py
```

`../raw/canonicalization_probe.json` records the installed versions and passed observations:
repeat output is byte-identical; the graph is isomorphic after RDF 1.1 string normalization;
numerical lexical forms remain exact; nonstandard relative IRIs emit the named fallback warning.
The tiny graph timing is not a representative performance claim or a substitute for the root's
same-test before/after measurement.

The initial default-parser observation is retained in `../raw/canonicalization_probe_parse_default.json`;
its failed isomorphism check led to the explicit parse-time-normalization separation above.
