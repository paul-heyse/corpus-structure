"""Inspect structural products through one explicit selected native read."""

from pathlib import Path

import typer

from corpus_structure.cli.output import JsonOpt, read_request_model, state, write_report_text
from corpus_structure.semantic.data_operation_json import json_bytes

app = typer.Typer(help="Inspect selected structural reports, dossiers, gaps and source journeys.")


def _read(ctx, path, contract, operation, json, *, owns_read=False):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    with failure_boundary(json, expected=(ValueError, KeyError)):
        request = read_request_model(path, contract)
        with open_runtime_engine(
            state(ctx).settings(), "ci-selected-structure", purpose="read"
        ) as engine:
            if owns_read:
                result = operation(lambda: selected_read_snapshot(engine), request)
            else:
                with selected_read_snapshot(engine) as connection:
                    result = operation(connection, request)
        write_report_text(json_bytes(result).decode() + "\n")


@app.command("list")
def structures(ctx: typer.Context, request: Path, json: JsonOpt = False):
    """Inspect exact product/member/use/derivation roots from request JSON."""
    from corpus_structure.serve.structural_products import (
        SelectedStructuralRequest,
        inspect_selected_structures,
    )

    _read(ctx, request, SelectedStructuralRequest, inspect_selected_structures, json)


@app.command("dossier-page")
def dossier_page(ctx: typer.Context, request: Path, json: JsonOpt = False):
    """Page immutable membership or its selected display, retaining exact citations."""
    from corpus_structure.serve.structural_products import (
        SelectedDossierRequest,
        inspect_selected_dossier,
    )

    _read(ctx, request, SelectedDossierRequest, inspect_selected_dossier, json, owns_read=True)


@app.command("gap")
def structural_gap(ctx: typer.Context, request: Path, json: JsonOpt = False):
    """Inspect recorded relationship decisions or applicability premises."""
    from corpus_structure.serve.structural_gaps import SelectedGapRequest, inspect_selected_gap

    _read(ctx, request, SelectedGapRequest, inspect_selected_gap, json)


@app.command("journey")
def source_journey(ctx: typer.Context, request: Path, json: JsonOpt = False):
    """Follow an original-relative opportunity through explicit selected layer roots."""
    from corpus_structure.serve.source_decision_journey import (
        SelectedSourceDecisionJourneyRequest,
        inspect_selected_source_journey,
    )

    _read(ctx, request, SelectedSourceDecisionJourneyRequest, inspect_selected_source_journey, json)


@app.command("export")
def export_review(ctx: typer.Context, request: Path, out: Path, json: JsonOpt = False):
    """Export an exact selected structural reading with authenticated native closure."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.selected_structural_review import (
        SelectedStructuralReviewRequest,
        export_selected_structural_review,
    )

    with failure_boundary(json, expected=(ValueError, KeyError, OSError)):
        selection = read_request_model(request, SelectedStructuralReviewRequest)
        with open_runtime_engine(
            state(ctx).settings(), "ci-structural-review", purpose="read"
        ) as engine:
            result = export_selected_structural_review(
                lambda: selected_read_snapshot(engine), selection, destination=out
            )
        write_report_text(json_bytes(result).decode() + "\n")


@app.command("verify")
def verify_review(artifact: Path, manifest_digest: str, json: JsonOpt = False):
    """Verify and replay a detached structural reading against a trusted digest."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.selected_structural_review import verify_selected_structural_review

    with failure_boundary(json, expected=(ValueError, KeyError, OSError)):
        result = verify_selected_structural_review(artifact, manifest_digest=manifest_digest)
        write_report_text(json_bytes(result).decode() + "\n")


def register(root: typer.Typer):
    root.add_typer(app, name="structure")
