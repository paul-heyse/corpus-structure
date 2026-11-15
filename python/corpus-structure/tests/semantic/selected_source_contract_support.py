"""Independent detached-format inputs; these fixtures claim no native admission."""

from corpus_structure.semantic.pdf_publication import PublishedPdfDocumentRef
from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference


def selection(*, release="retained-release", producer_release="source-production-release", task=70, digest="1" * 64, key="integrated"):
    pin = SelectedPdfSourceReference(
        project_id="p", demand_id="demand:fixture", read_id="read:fixture",
        use_id="use:fixture", product_id=f"semantic-product:{task}", derivation_id=f"episode:{task}",
    )
    cut = dict(
        project_id="p", demand_id=pin.demand_id, read_id=pin.read_id,
        release_id=release, runtime_id="runtime:fixture", selection={}, trust_snapshot={},
        read_snapshot="1:2:", frontier_at="2026-11-15T00:00:00Z", scope={},
    )
    publication = PublishedPdfDocumentRef(
        build_id=f"build:{task}", task_id=task, product_key=key, logical_digest=digest,
        release_id=producer_release, source_digest="a" * 64, schema_digest="b" * 64,
        recipe_digest="c" * 64, frozen_digest="d" * 64, kind="integrated",
    )
    return pin, cut, publication
