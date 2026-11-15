"""Detached structural review using the existing authenticated selected-result archive."""

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_results import CutSelection

from .demand_export import export_demand_result, verified_demand_export
from .rich_queries import installed_read_implementation
from .selected_structural import STRUCTURAL_READ_SOURCES, StructuralScope
from .source_decision_journey import (
    SelectedSourceDecisionJourneyRequest,
    inspect_selected_source_journey,
)
from .structural_gaps import SelectedGapRequest, inspect_selected_gap
from .structural_products import (
    SelectedDossierRequest,
    SelectedStructuralRequest,
    inspect_selected_dossier,
    inspect_selected_structures,
)


class SelectedStructuralReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    selection: (
        SelectedStructuralRequest
        | SelectedDossierRequest
        | SelectedGapRequest
        | SelectedSourceDecisionJourneyRequest
    )


def _roots(request):
    if isinstance(request, SelectedStructuralRequest):
        return request.roots, ()
    if isinstance(request, SelectedSourceDecisionJourneyRequest):
        return tuple(layer.root for layer in request.layers), (
            request.opportunity.source.source_product,
        )
    if isinstance(request, SelectedGapRequest):
        return tuple(
            root for root in (request.root, request.binding, request.admission) if root is not None
        ), ()
    return (request.root,), ()


def _project(scope, request):
    if isinstance(request, SelectedStructuralRequest):
        return inspect_selected_structures(scope, request)
    if isinstance(request, SelectedDossierRequest):
        return inspect_selected_dossier(scope, request)
    if isinstance(request, SelectedGapRequest):
        return inspect_selected_gap(scope, request)
    return inspect_selected_source_journey(scope, request)


def _replay(root, selection, native_digest):
    request = selection.selection
    with verified_demand_export(root / "native", manifest_digest=native_digest) as (
        manifest,
        prepared,
        models,
        index,
    ):
        cut = CutSelection.from_native(manifest["cut"])
        release = cut.record["release_id"]
        with installed_read_implementation(
            type(request), sources=STRUCTURAL_READ_SOURCES, profile="selected-structural-read-v1"
        ) as implementation:
            scope = StructuralScope(
                cut,
                index,
                prepared[release],
                models[release],
                cut.record["scope"],
                request.max_support_edges,
                implementation,
            )
            return _project(scope, request)


def export_selected_structural_review(
    connection, selection: SelectedStructuralReviewRequest, *, destination: Path
):
    """Export selected custody and a bounded page, then verify and replay that page.

    The caller retains one native snapshot for acquisition. The detached reader uses
    captured schemas and original bytes, and makes no claim about current trust.
    """
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    request = selection.selection
    if getattr(request, "cursor", None) is not None:
        raise ValueError("structural review must begin at its declared population start")
    roots, sources = _roots(request)
    scope = {"product_ids": sorted({root.product_id for root in roots} | set(sources))}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".structural-review-", dir=destination.parent) as temporary:
        root = Path(temporary) / "review"
        root.mkdir()
        native = export_demand_result(
            connection,
            request.demand_id,
            project_id=request.project_id,
            destination=root / "native",
            format="jsonl",
            scope=scope,
            read_id=request.read_id,
            expected_cut=request.expected_cut,
            page_bytes=request.max_graph_bytes,
        )
        pinned = request.model_copy(
            update=dict(read_id=native["cut"]["read_id"], expected_cut=native["cut_id"])
        )
        selection = selection.model_copy(update={"selection": pinned})
        response = _replay(root, selection, native["manifest_digest"])
        pinned = pinned.model_copy(update={"implementation": response["implementation"]})
        selection = selection.model_copy(update={"selection": pinned})
        files = {
            "selection.json": json_bytes(selection.model_dump(mode="python")),
            "response.json": json_bytes(response),
        }
        for name, content in files.items():
            (root / name).write_bytes(content)
        manifest = dict(
            format="selected-structural-review-v1",
            cut_id=native["cut_id"],
            native_manifest_digest=native["manifest_digest"],
            files={name: sha256(content).hexdigest() for name, content in files.items()},
            completeness="declared_selected_closure",
            current_trust="not_assessed",
            public_admission="not-established",
        )
        content = json_bytes(manifest)
        (root / "manifest.json").write_bytes(content)
        root.rename(destination)
        return dict(manifest, manifest_digest=sha256(content).hexdigest(), path=str(destination))


def verify_selected_structural_review(root: Path, *, manifest_digest: str):
    content = (root / "manifest.json").read_bytes()
    if sha256(content).hexdigest() != manifest_digest:
        raise ValueError("structural review differs from its trusted manifest digest")
    manifest = json_loads(content)
    if manifest["format"] != "selected-structural-review-v1" or set(manifest["files"]) != {
        "selection.json",
        "response.json",
    }:
        raise ValueError("unsupported structural review format or file population")
    for name, digest in manifest["files"].items():
        if sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("structural review file differs from its trusted manifest")
    selection = SelectedStructuralReviewRequest.model_validate(
        json_loads((root / "selection.json").read_bytes())
    )
    actual = _replay(root, selection, manifest["native_manifest_digest"])
    if (
        actual["cut_id"] != manifest["cut_id"]
        or json_bytes(actual) != (root / "response.json").read_bytes()
    ):
        raise ValueError("detached structural reading differs from authenticated selected meaning")
    return dict(
        outcome="passed",
        cut_id=manifest["cut_id"],
        current_trust="not_assessed",
        completeness="declared_selected_closure",
        inference="not_run",
        public_admission="not-established",
    )
