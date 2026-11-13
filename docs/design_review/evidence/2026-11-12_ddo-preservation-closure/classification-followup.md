# Preservation classification reconciliation

**Observed / Assessed2026-11-12 local (2026-11-13UTC).** The DDO-00 metadata-selection
and preservation-classification subobligation is complete for the acquired database and declared
local owner universe. No concrete metadata-inventory blocker remains in that scope. This does not
complete the other DDO-00 responsibilities or DDO-11 adoption/freeze/recovery verification.

This follow-up preserves the finalized [original inventory](records/ddo.preservation-root-inventory.json)
and all its outputs. Its partial outcome remains historically accurate for the original inquiry;
the [new dispositions](raw/classification-reconciled.json) settle the classification questions
without rewriting that evidence. The [reconciliation source](reconcile_classification.py) opens
only the finalized metadata, selected manifests and metadata states of declared members. It has
no database connection or provider import. No protected answer, source, result or archived contract
body was opened. Only source code was consulted to establish the reader contracts below.

## All 417 previously pending manifests have a preservation action

| Metadata kind | Count | Reader/custodian and disposition |
|---|---:|---|
| `contribution-selection-export-1` | 365 | [`export_contribution_selection`](../../../../python/corpus-structure/src/corpus_structure/serve/contributions.py) writes the exact bounded selected inventory, binding and `items.jsonl` digest. Preserve manifest, member and original selection as sealed retained output. The owner expressly says this is not a self-contained PCE09 review bundle; preserving it does not require importing its old identity into the active database. |
| Visual campaign metadata | 16 | [`group_shadow_compare.py`](../2026-11-08_chandra-execution/group_shadow_compare.py) consumes exact visual pins, source release, selections and archive overlay. Preserve original campaign directories and declared outbound custody. No provider execution or reinterpretation was requested. |
| Native output capture accounts | 7 | [`characterize_outputs.py`](../2026-11-06_wce-gs120/assessment/characterize_outputs.py) consumes the capture manifest and its explicitly named task-envelope files. Preserve their original capture scope, including partial checkpoints; do not promote them to complete results. |
| Independent reference custody | 8 | [`register_passes.py`](../2026-11-04_m1-independent-references/register_passes.py), freeze/adjudication helpers and retained author accounts own frozen unit/contract inputs, exact original submissions and registration receipts. Preserve whole evidence custody and declared input/output files; no protected file contents were read. |
| Protected panel custody | 8 | The TC/BEP assessment evidence owner and its [`prepare_choice_supplement.py`](../2026-11-12_bep-tc-qualification/helpers/prepare_choice_supplement.py) retain the original source-only/panel scope. Preserve whole panel directories and explicitly declared private/protected custody directories. No reading or automatic rewrite of answers follows. |
| Frozen source-only author packets | 4 | [`author_source_references.py`](../2026-11-01_pdf-current-consumers/author_source_references.py) writes `input_digests` for every frozen source/schema input. Preserve those exact packet files and original release provenance. |
| Prepared release manifests | 2 | [`prepare.py`](../../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py) owns the dependencies/sources/libraries/profile shape. Preserve the original manifest and containing prepared-output directory; no recompilation using current source is implied. |
| Retained source fixture manifests | 2 | The [child-OCR source preparation](../2026-10-31_pdf-child-ocr/prepare_sources.py) and its evidence custodian own these fixtures. Preserve their source/evidence scope. |
| Archived runtime manifest | 1 | [`validate_runtime_binding`](../../../../python/corpus-structure/src/corpus_structure/semantic/runtime_bindings.py) owns the implementation/semantic-input/compiler metadata shape. Preserve the original runtime archive interpretation and containing directory. |
| Portable interpretation contract | 1 | [`export_interpretation_contract`](../../../../python/corpus-structure/src/corpus_structure/semantic/portable_interpretation.py) names the exact local schema entry and digest. Preserve schema plus manifest in the original validation-only scope. |
| Whole-book review account | 1 | [`review_packets.py`](../2026-11-08_nce-full-book/review_packets.py) owns `pages.jsonl`, `comparison.jsonl` and original source pins. Preserve its exact 518-page historical account; no new recognition or quality claim follows. |
| Source population account | 1 | The [M1 population inventory](../2026-11-03_m1-population/inventory.py) and retained evidence reader consume this census. Preserve original directory and scope. |
| Printer evidence metadata | 1 | The containing retained evidence directory and its cited record own the frozen source/receipt/caller-impact account. Preserve it sealed; no executable replay capability is invented. |

All 417 manifest hashes still match the finalized census. They now have an explicit conservative
`preserve_sealed` action. A fully identified executable reader is unnecessary for conservative
retention of the single legacy evidence account: its actual evidence custodian is named, and no
disposal or address migration is proposed. Nothing in this follow-up moves an unknown root to
disposable regeneration or chooses a protected-reference correspondence.

The reconciliation made 870 additional metadata checks of identified declared members and outbound
directories. Of those, 868 exist. The two absent paths are
`build/chandra-execution/archive-overlay/artifacts` and its `final/artifacts` counterpart.
The [freeze owner](../2026-11-08_chandra-execution/freeze_book_shadow.py) records the `artifacts`
argument before branching; when `archive_study` is present, it deliberately skips the
`ChandraRuntime(args.artifacts)` recipe branch. The retained comparison reader does not consume
that field. Both manifests take that archive-overlay branch and have no runtime recipe. These
are inactive provider-model location hints, not missing retained source/archive members.
The earlier [literal-path observation](raw/classification-followup.json) remains intact;
the reconciled output records this source-based disposition. No absent declared member required
by the selected retained reader was found.

## The 73 historical identifiers are retained provenance

The 73 occurrences appear in 69 manifests:

| Occurrences | Interpretation and preserved custody |
|---:|---|
| 60 | `semantic-export-1/2` tabular release provenance. The [export owner](../../../../python/corpus-structure/src/corpus_structure/serve/export.py) writes captured relation files with explicit schemas, identity and member digests. Original tabular inspection consumes that captured file scope. Active-database release membership is not an external file dependency. |
| 9 | Run47/51/52 selections across five historical `selected_source_closure` review bundles. Preserve the original format, selections and all declared relations. [Detached verification](../../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py) takes a directory/manifest and retained relations; retaining those bundles does not require a live row for the old run ID. Earlier bundle formats retain their original declared scope; no current-reader compatibility or byte/replay pass is asserted. |
| 4 | Frozen source-only author packet release provenance. The export producer already captured the original source/schema inputs named by `input_digests`; all those declared files exist by metadata. Preserve the original packet and provenance rather than guessing a new release mapping. |

The original inventory found no missing nonfixture parsed bundle member or evidence-record path.
Together with the added member checks, the metadata contains no discovered missing required source
or archive root. This is a scoped existence/classification conclusion. It does not prove that
every historical reader still executes, that bytes match declared hashes, or that any preserved
artifact has stronger semantic/source completeness than its original declared scope.

## DDO-00 versus DDO-11

DDO-00 now has exact database IDs/digests/revisions, native FK and selected artifact/product links,
declared managed/evidence/review/export references, and conservative preservation actions with
named readers or evidence custodians. Every incomplete run and the four unpublished native builds
can remain sealed/quarantined. Unknown recovery intent does not prevent selecting that preservation
action; it would prevent a later disposal claim. The old unsettled `0a78…` result remains protected.

There are **no remaining DDO-00 metadata-classification blockers in the declared scope**.
The scope is the acquired database, configured local manifest/evidence owners and recognized
declared outbound custody. Arbitrary unrecorded external deliveries are outside that declaration;
an impossible filesystem-wide absence proof is not a completion requirement. Any subsequently
identified required external custody joins the adoption inventory before its affected effect.

DDO-11 still owns reacquiring and freezing the actual target/source, fencing writers, preparing
and testing compatible original/archive/evidence recovery material, checking required bytes and
historical readers at the frozen predecessor, accounting for unsettled work, and reviewing actual
correspondence where addresses change. Those future operational checks do not make the completed
metadata inventory incomplete. They remain required before their corresponding adoption effects.

`uv run python docs/design_review/evidence/2026-11-12_ddo-preservation-closure/reconcile_classification.py`
**passed** for the reported metadata classification. The original seven finalized output hashes
were checked unchanged. Product/provider tests, byte-integrity verification, detached replay,
database writes, restore and settlement are **not_run** for this metadata-only follow-up.
