"""Restricted semantic reference-set, split, pass and status commands."""

from __future__ import annotations

import json as jsonlib
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, state

golden_app = typer.Typer(
    help="Independent references on an immutable semantic release.", no_args_is_help=True
)
InputFile = Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)]


@contextmanager
def reference_session(ctx, project=None, *, json=False):
    from sqlalchemy import select

    from corpus_structure.evaluate import semantic as references
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.runtime import open_runtime_engine

    with failure_boundary(json, expected=(references.ReferenceError,)):
        settings = state(ctx).settings()
        with (
            open_runtime_engine(
                settings, application_name="ci-reference", purpose="evaluate"
            ) as engine,
            engine.begin() as conn,
        ):
            project = project or settings.runtime.default_project
            if project is None:
                candidates = list(
                    conn.execute(select(table("data.project").c.project_id)).scalars()
                )
                if len(candidates) != 1:
                    raise references.ReferenceError("select --project explicitly")
                project = candidates[0]
            if not conn.scalar(
                select(table("data.project").c.project_id).where(
                    table("data.project").c.project_id == project
                )
            ):
                raise references.ReferenceError("unknown semantic project")
            yield conn, project


def output(result, json):
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    if json:
        from corpus_structure.cli.output import write_report_text

        write_report_text(
            jsonlib.dumps(result, ensure_ascii=False, allow_nan=False, default=str) + "\n"
        )
    else:
        from rich.pretty import Pretty

        from corpus_structure.cli.output import stdout_console

        stdout_console().print(Pretty(result))


def reference_protocol(conn, set_id, project_id):
    """Route only from a stored, project-bound reference-set declaration."""
    from sqlalchemy import select

    from corpus_structure.evaluate import operation_assessment, record_references, semantic
    from corpus_structure.semantic.metadata import table

    sets = table("eval.reference_set")
    definition = conn.execute(select(sets).where(sets.c.id == set_id)).mappings().one_or_none()
    if definition is None:
        raise semantic.ReferenceError(f"unknown reference set {set_id}")
    if definition["project_id"] != project_id:
        raise semantic.ReferenceError("reference set belongs to another project")
    protocol = definition["sampling"].get("operation_protocol") or definition["sampling"].get(
        "record_protocol"
    )
    if protocol not in (None, record_references.PROTOCOL, operation_assessment.PROTOCOL):
        raise semantic.ReferenceError("unsupported stored reference protocol")
    return protocol


def read_object(path):
    """Translate malformed caller JSON without masking implementation failures."""
    from corpus_structure.evaluate.semantic import ReferenceError

    try:
        value = jsonlib.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, jsonlib.JSONDecodeError) as error:
        raise ReferenceError(f"invalid JSON input: {path}") from error
    if not isinstance(value, dict):
        raise ReferenceError(f"JSON input must be an object: {path}")
    return value


def decode_record_frame(value):
    """Check the existing dataclass shape before its unchecked decoder reaches services."""
    from pydantic import TypeAdapter, ValidationError

    from corpus_structure.evaluate import record_references as references
    from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame

    if not isinstance(value, dict):
        raise references.ReferenceError("record frame must be a JSON object")
    try:
        TypeAdapter(RecordEvaluationFrame).validate_python(value.get("evaluation_frame"))
    except ValidationError as error:
        raise references.ReferenceError(f"invalid record evaluation_frame: {error}") from error
    try:
        return references.decode_frame(value)
    except (KeyError, TypeError, ValueError) as error:
        raise references.ReferenceError("invalid record reference frame") from error


def validate_record_sample_shape(payload):
    """Validate CLI containers; the existing service/native owners enforce their meaning."""
    from typing import Any

    from pydantic import TypeAdapter, ValidationError

    from corpus_structure.evaluate.semantic import ReferenceError

    shapes = {
        "unit_keys": list[str],
        "sampling": dict[str, Any],
        "frames": dict[str, dict[str, Any]],
        "captured_coordinates": dict[str, list[dict[str, Any]]] | None,
        "context_dependency_digests": dict[str, str] | None,
    }
    for key, shape in shapes.items():
        if key in payload:
            try:
                TypeAdapter(shape).validate_python(payload[key], strict=True)
            except ValidationError as error:
                raise ReferenceError(f"invalid sample {key}: {error}") from error
    sampling = payload["sampling"]
    for key in ("strata", "inclusion_probabilities", "provenance"):
        if key in sampling and not isinstance(sampling[key], dict):
            raise ReferenceError(f"sample sampling.{key} must be a JSON object")


@golden_app.command("record-origin")
def record_origin_command(
    ctx: typer.Context,
    origin_group: Annotated[str, typer.Option()],
    partition: Annotated[str, typer.Option()],
    source_uri: Annotated[list[str], typer.Option("--source-uri")],
    provenance: InputFile,
    project: str | None = None,
    json: JsonOpt = False,
):
    """Assign explicitly attested common source origins to a record partition."""
    from corpus_structure.evaluate import record_references as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        references.assign_origin(
            conn,
            project_id=pid,
            origin_group=origin_group,
            partition=partition,
            source_uris=source_uri,
            provenance=read_object(provenance),
        )
    output({"origin_group": origin_group, "partition": partition, "source_uris": source_uri}, json)


@golden_app.command("record-create")
def record_create_command(
    ctx: typer.Context,
    from_run: Annotated[int, typer.Option()],
    source_cut: Annotated[int, typer.Option()],
    label: Annotated[str, typer.Option()],
    split: Annotated[str, typer.Option()],
    guideline: Annotated[str, typer.Option()],
    guideline_text: InputFile,
    partition: Annotated[str, typer.Option()],
    reference_policy: Annotated[str, typer.Option()],
    prediction_policy: Annotated[str, typer.Option()],
    sample: InputFile,
    project: str | None = None,
    json: JsonOpt = False,
):
    """Freeze source-only unit_keys, sampling and encoded frames from --sample JSON."""
    from corpus_structure.evaluate import record_references as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        payload = read_object(sample)
        required = {"unit_keys", "sampling", "frames"}
        optional = {"captured_coordinates", "context_dependency_digests"}
        if not required <= payload.keys() or payload.keys() - required - optional:
            raise references.ReferenceError(
                "sample requires unit_keys, sampling, frames; optional captured_coordinates "
                "and context_dependency_digests"
            )
        validate_record_sample_shape(payload)
        frames = {key: decode_record_frame(value) for key, value in payload["frames"].items()}
        try:
            text = guideline_text.read_text(encoding="utf-8")
        except (ValueError, OSError) as error:
            raise references.ReferenceError("invalid record guideline text") from error
        result = references.create_reference_set(
            conn,
            project_id=pid,
            source_run_id=from_run,
            source_cut_id=source_cut,
            label=label,
            legacy_split=split,
            guideline=guideline,
            guideline_text=text,
            partition=partition,
            unit_keys=payload["unit_keys"],
            sampling=payload["sampling"],
            frames=frames,
            reference_policy_version=reference_policy,
            prediction_policy_version=prediction_policy,
            captured_coordinates=payload.get("captured_coordinates"),
            context_dependency_digests=payload.get("context_dependency_digests"),
        )
    output(result, json)


@golden_app.command("record-packet")
def record_packet_command(
    ctx: typer.Context,
    unit: Annotated[int, typer.Option()],
    pass_kind: Annotated[str, typer.Option("--pass")],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Read source-only A/B inputs or the separate retained A/B adjudication packet for C."""
    from corpus_structure.evaluate import record_references as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        bound = references._unit(conn, unit)
        if bound["project_id"] != pid:
            raise references.ReferenceError("reference unit belongs to another project")
        if reference_protocol(conn, bound["set_id"], pid) != references.PROTOCOL:
            raise references.ReferenceError("reference set does not declare the record protocol")
        if pass_kind in {"A", "B"}:
            result = references.author_packet(conn, unit)
        elif pass_kind == "C":
            result = references.adjudication_packet(conn, unit)
            result = dict(
                result,
                authors=[
                    dict(author, authored=author["authored"].decode("utf-8"))
                    for author in result["authors"]
                ],
            )
        else:
            raise references.ReferenceError("record packet --pass must be A, B or C")
    output(result, json)


@golden_app.command("split")
def split_command(
    ctx: typer.Context, seed: int | None = None, project: str | None = None, json: JsonOpt = False
):
    """Assign registered source documents immutably to development/test splits."""
    from corpus_structure.evaluate import semantic as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        result = references.split_documents(conn, pid, seed=seed)
    output(result, json)


@golden_app.command("operation-create")
def operation_create_command(
    ctx: typer.Context,
    from_run: Annotated[int, typer.Option()],
    source_cut: Annotated[int, typer.Option()],
    label: Annotated[str, typer.Option()],
    split: Annotated[str, typer.Option()],
    guideline: Annotated[str, typer.Option()],
    guideline_text: InputFile,
    partition: Annotated[str, typer.Option()],
    sample: InputFile,
    project: str | None = None,
    json: JsonOpt = False,
):
    """Freeze operation source/output frames before independent A/B authoring."""
    from corpus_structure.evaluate import operation_assessment as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        payload = read_object(sample)
        if set(payload) != {"sampling", "frames"}:
            raise references.ReferenceError("operation sample requires exactly sampling and frames")
        try:
            frames = {
                key: references.decode_frame(value) for key, value in payload["frames"].items()
            }
            text = guideline_text.read_text(encoding="utf-8")
        except (ValueError, OSError, TypeError, AttributeError) as error:
            raise references.ReferenceError("invalid operation sample or guideline") from error
        result = references.create_reference_set(
            conn,
            project_id=pid,
            source_run_id=from_run,
            source_cut_id=source_cut,
            label=label,
            legacy_split=split,
            guideline=guideline,
            guideline_text=text,
            partition=partition,
            sampling=payload["sampling"],
            frames=frames,
        )
    output(result, json)


@golden_app.command("operation-packet")
def operation_packet_command(
    ctx: typer.Context,
    unit: Annotated[int, typer.Option()],
    pass_kind: Annotated[str, typer.Option("--pass")],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Read independent source-only A/B input or retained A/B adjudication input for C."""
    from corpus_structure.evaluate import operation_assessment as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        bound = references._unit(conn, unit)
        if (
            bound["project_id"] != pid
            or reference_protocol(conn, bound["set_id"], pid) != references.PROTOCOL
        ):
            raise references.ReferenceError("unit is outside selected operation reference project")
        if pass_kind in {"A", "B"}:
            result = references.author_packet(conn, unit)
        elif pass_kind == "C":
            result = references.adjudication_packet(conn, unit)
        else:
            raise references.ReferenceError("operation packet --pass must be A, B or C")
    output(result, json)


@golden_app.command("create")
def create_command(
    ctx: typer.Context,
    split: Annotated[str, typer.Option()],
    label: Annotated[str, typer.Option()],
    size: int | None = None,
    seed: int | None = None,
    from_run: int | None = None,
    force_unit: Annotated[list[str] | None, typer.Option("--force-unit")] = None,
    project: str | None = None,
    json: JsonOpt = False,
):
    """Sample independent reference units from a completed result's frozen source cut."""
    from sqlalchemy import select

    from corpus_structure.evaluate import semantic as references
    from corpus_structure.semantic.metadata import table

    with reference_session(ctx, project, json=json) as (conn, pid):
        run = from_run or conn.scalar(
            select(table("data.project").c.selected_result_run_id).where(
                table("data.project").c.project_id == pid
            )
        )
        if run is None:
            raise references.ReferenceError("choose --from-run or select a completed result")
        result = references.create_reference_set(
            conn,
            project_id=pid,
            source_run_id=run,
            label=label,
            split=split,
            size=size,
            seed=seed,
            forced=tuple(force_unit or ()),
        )
    output(result, json)


@golden_app.command("status")
def status_command(
    ctx: typer.Context, label: str | None = None, project: str | None = None, json: JsonOpt = False
):
    """Show counts and bindings, without exposing reference answers."""
    from sqlalchemy import select

    from corpus_structure.evaluate import semantic as references
    from corpus_structure.semantic.metadata import table

    with reference_session(ctx, project, json=json) as (conn, pid):
        provenance = references.split_provenance_summary(conn, pid)
        s = table("eval.reference_set")
        q = select(s).where(s.c.project_id == pid)
        if label is not None:
            q = q.where(s.c.label == label)
        result = [
            {
                **references.golden_set_status(conn, row.id),
                "split_provenance": provenance,
                "label": row.label,
                "split": row.split,
                "release_id": row.release_id,
                "source_run_id": row.source_run_id,
            }
            for row in conn.execute(q.order_by(s.c.id))
        ]
        if label is not None and not result:
            raise references.ReferenceError(f"no reference set {label!r}")
    output(result, json)


@golden_app.command("submit")
def submit_command(
    ctx: typer.Context,
    unit: Annotated[int, typer.Option()],
    pass_kind: Annotated[str, typer.Option("--pass")],
    actor: Annotated[str, typer.Option()],
    authored: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    frame: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Store an automated independent pass and its exact source citation frame."""
    from corpus_structure.evaluate import operation_assessment, record_references
    from corpus_structure.evaluate import semantic as references
    from corpus_structure.semantic.proposals import (
        ProposalFrame,
        ProposalSentence,
        native_frame_from_dict,
    )

    with reference_session(ctx, project, json=json) as (conn, pid):
        bound = references._unit(conn, unit)
        if bound["project_id"] != pid:
            raise references.ReferenceError("reference unit belongs to another project")
        protocol = reference_protocol(conn, bound["set_id"], pid)
        if protocol == operation_assessment.PROTOCOL:
            operation_frame = operation_assessment.decode_frame(read_object(frame))
            identity = operation_assessment.record_pass(
                conn,
                unit_id=unit,
                pass_kind=pass_kind,
                actor=actor,
                authored=authored.read_bytes(),
                frame=operation_frame,
            )
        elif protocol == record_references.PROTOCOL:
            record_frame = decode_record_frame(read_object(frame))
            identity = record_references.record_pass(
                conn,
                unit_id=unit,
                pass_kind=pass_kind,
                actor=actor,
                authored=authored.read_bytes(),
                frame=record_frame,
            )
        else:
            try:
                raw = jsonlib.loads(frame.read_bytes())
                coordinates = tuple(ProposalSentence(**sentence) for sentence in raw["sentences"])
                if "source_view_id" in raw:
                    source = native_frame_from_dict(raw)
                else:
                    source = ProposalFrame(raw["unit_ref"], raw["text"], coordinates)
            except (jsonlib.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise references.ReferenceError("invalid authored citation frame") from error
            identity = references.record_pass(
                conn,
                unit_id=unit,
                pass_kind=pass_kind,
                actor=actor,
                authored=authored.read_bytes(),
                frame=source,
            )
    output({"pass_id": identity, "unit_id": unit, "pass_kind": pass_kind}, json)


def register(app):
    app.add_typer(golden_app, name="golden")
