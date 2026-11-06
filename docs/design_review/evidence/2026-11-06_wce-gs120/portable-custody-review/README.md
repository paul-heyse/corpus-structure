# Portable dossier custody correction review

**Source-inspected,2026-11-06. No remaining material finding in the bounded final patch.**
This independently reviews WCE-R12's Python capture/detached-verification correction, not full WCE
acceptance, a design audit or corpus-quality assessment. The root owns integration, final-source
qualification and actual export replay.

The examined tree is HEAD `a441f3b7e80c1ccbfd304681e20f69afc0e8068b` plus the three named dirty files.
Their combined `git diff --` SHA256 is
`fbb5723034352e256b4d9c4dfaf39758ff2719ddcd98e09c01126547d27c24ca`.

| File | SHA256 |
|---|---|
| `python/corpus-structure/src/corpus_structure/serve/review_bundle.py` | `f473bf0f5ac181147f910087873710e003536bb29a4b6f6a1717a8927bf59928` |
| `python/corpus-structure/tests/semantic/test_review_bundle.py` | `ba5abe30aee8553819a6b6509d2a7aa9b6b9c9de48858a96d29383161c8700ab` |
| `python/corpus-structure/tests/semantic/test_dossier_contributions.py` | `44a36a0b84b1ac395aa2ca4dd67c4897c41c7857b0c046c77fd5beb5c7ef2cfe` |

## Contract and inspected correction

The original failure substituted a dossier selection's run/cut when checking its structural
predecessors. The final `_verify_dossier_structural_closure` helper instead matches each entire declared
`RetainedStructuralRef`: selected project/run/cut/release/revision, selected/origin task IDs,
producer runtime and product ID. Captured original run/project/runtime and raw retained report
must then agree independently with that matched selection. A matching product ID alone supplies
no closure. Source-contribution closure similarly distinguishes selected project from captured
original producer metadata and retains its exact endpoint inventory/source replay checks.

The authority for predecessor support is the existing native
`ops.resolve_retained_structural_report`, `semantic/sql/structural_products.sql:109–113`. It selects
published assertions by the reference's exact release, realization, cut, selected/origin task and
product. `derive_dossier_members` subsequently requires exact statement equality and the native
assertion ID, exposed there as `assessment_id`. Public structural page metadata has a broader
release/realization/product selection and may legitimately mention another cut/task. The patch
therefore filters that metadata for support in the exact candidate context while preserving all
unrelated Page metadata unchanged. Unrelated publication supplies zero predecessor support and
does not poison the whole export. Enrichment reads actual statements
through the existing native owner and checks their claim hashes. Offline replay rederives original
members and supported facets rather than accepting producer flags or borrowing another assessment.

Capture retains one stable `selected_session` through a structural selection. Reading original
physical sources uses a separate `source_session`; their revision/prepared context cannot replace
the selected publication context. Exact predecessor readers are reused per immutable run/cut,
while every retained contribution still goes through the established native resolver. The patch
adds no historical semantic decoder, provider, writable store or new publication authority.

## Issues corrected during review

1. A source-session overwrite could bind a later published report in a multi-report export to an
   original source's revision/prepared context. The final source separates the sessions. The new
   capture control deliberately uses selected revision7 and original-source revision0 and asserts
   that the later published report still uses the selected context.
2. An intermediate whole-page foreign-cut refusal imposed an invariant absent from the public
   page contract. The final source filters exact candidate assertions instead. Controls use the actual metadata-only Page shape and cover a
   selected publication, only another-cut publication, and unrelated extra publication without
   granting its support or rejecting a legitimate page. Unrelated metadata remains unchanged.

These are resolved in the file hash above; they are not remaining findings or new plan items.

## Test-source coverage and limits

Inspected tests have literal expected term/content role spans, supported facet counts, assessment
IDs and omitted-member counts. They include exact-custody substitutions for project/run/cut/release/
revision/tasks/runtime, altered original raw report/producer identity, missing or wrong-cut
predecessors, changed member role and borrowed support. Adjacent source-contribution controls cover
selected/original project, run and runtime metadata. The control-flow capture test is explicitly
mocked and establishes that control flow only; no mocked provider is presented as an actual route.

The synthetic cross-project fixtures distinguish detached selected/reference custody from original
producer metadata. They are not evidence of an ordinary cross-project task-reuse journey:
`ops.valid_reuse` currently also requires equal previous/current project IDs. Actual GS120's
cross-cut lineage remains same-project. No new runtime reuse permission follows from these fixtures.

**passed**,2026-11-06: `git diff --check --` over the three named files and stdlib SHA256 snapshot
inspection. These establish clean patch text and the exact reviewed baseline only.

**not_run by this reviewer:** pytest, native/database mutations, providers, full GS120 export,
model generation, broad hygiene/qualification or commits. Writer/root focused tests and actual
corrected export are required. In particular, this review does not turn accepted native184,
Reader/MCP delivery or its failed earlier portable attempt into a passing corrected detached export.
No extraction recall, calibrated probability, complete knowledge or scientific-truth claim follows.
