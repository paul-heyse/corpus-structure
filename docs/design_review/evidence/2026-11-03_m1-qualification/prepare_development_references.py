"""Owned development-reference session over the retained Siegrist paragraph.

Run --check-inputs without database access. Root GO authorizes --execute. The execute
session owns one disposable logical copy until stdin EOF or {"action":"close"}.
JSON stdin: {"action":"submit","pass":"A","actor":"...","path":"/abs/A.json"},
then B; {"action":"packet-c"}; submit C; {"action":"agreement"}; close.
This helper invokes existing production operations; it authors no expected readings.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import pwd
import subprocess
import sys
import tempfile
import traceback
from dataclasses import asdict, is_dataclass, replace
from hashlib import file_digest, sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
EVIDENCE = Path(__file__).resolve().parent
POPULATION = EVIDENCE.parent / "2026-11-03_m1-population"
SOURCE_DATABASE = "corpus_pdf_20261102"
PROJECT = "pdf-docling-adoption"
NATIVE_TARGET = "semantic_m1_records_20261103"
PRODUCT = {
    "task_id": 6,
    "product_key": "integrated",
    "content_digest": "1882a372985949584bc3c15a3df8b2c6a9f21a1b610dd2b583cea70dc44975ac",
}
GUIDELINE = "m1-statistics-development-reading-1"
REFERENCE_POLICY = "m1-statistics-independent-reading-1"
PREDICTION_POLICY = "m1-canonical-same-view-candidates-1"


def serializable(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=serializable)
        + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def local_inputs(guideline_path: Path):
    from corpus_structure.semantic.identity import canonical_bytes

    manifest = POPULATION / "sources.json.gz"
    paragraph_path = POPULATION / "cpu-source-paragraph.json"
    sources = json.loads(gzip.decompress(manifest.read_bytes()))
    paragraph = json.loads(paragraph_path.read_bytes())
    if len(sources) != 5 or any(source["pin"]["native_product"] != PRODUCT for source in sources):
        raise ValueError("retained manifest does not identify the five exact source sections")
    source = next(item for item in sources if item["pin"]["id"] == 5)
    if (
        paragraph["pin"] != source["pin"]
        or sha256(canonical_bytes(source)).hexdigest() != paragraph["source_snapshot_sha256"]
        or (paragraph["start"], paragraph["end"]) != (29, 468)
        or source["text"][29:468] != paragraph["text"]
    ):
        raise ValueError("retained view5 paragraph differs from its exact source snapshot")
    guideline_text = guideline_path.read_text(encoding="utf-8")
    if not all(
        value in guideline_text for value in (GUIDELINE, REFERENCE_POLICY, PREDICTION_POLICY)
    ):
        raise ValueError("root guideline does not declare the frozen guideline/policy identities")
    return (
        source,
        paragraph,
        guideline_text,
        {
            str(path.relative_to(ROOT)): digest(path)
            for path in (manifest, paragraph_path, guideline_path)
        },
    )


def command(argv: list[str], output: Path, name: str, *, stdin=None, stdout=None) -> None:
    write_json(output / f"{name}-command.json", argv)
    with (output / f"{name}-stderr.log").open("wb") as errors:
        if stdout is not None:
            subprocess.run(argv, stdin=stdin, stdout=stdout, stderr=errors, check=True, cwd=ROOT)
        else:
            with (output / f"{name}-stdout.log").open("wb") as result:
                subprocess.run(
                    argv, stdin=stdin, stdout=result, stderr=errors, check=True, cwd=ROOT
                )


def settings_for(database: str):
    from sqlalchemy.engine import URL

    from corpus_structure.settings import Settings

    def url(role, name=None):
        return URL.create(
            "postgresql",
            username=role,
            database=name,
            query={"host": "/var/run/postgresql", "port": "5434"} if name else {},
        ).render_as_string(hide_password=False)

    return Settings(
        database={
            "url": url("corpus_sem_writer", database),
            "maintenance_url": url(pwd.getpwuid(os.getuid()).pw_name),
            "reader_url": url("corpus_sem_reader"),
            "admission_url": url("corpus_sem_admitter"),
            "evaluator_url": url("corpus_sem_evaluator"),
            "fitter_url": url("corpus_sem_fitter"),
            "template": "cs_template",
        }
    )


def archive_witness(connection, *, open_archives=False):
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.releases import open_release

    releases = table("sem.release")
    result = {}
    for row in connection.execute(
        select(
            releases.c.release_id,
            releases.c.content_digest,
            releases.c.prepared_bytes,
            releases.c.manifest_bytes,
        )
    ).mappings():
        raw = bytes(row["prepared_bytes"])
        actual = sha256(raw).hexdigest()
        if actual != row["content_digest"]:
            raise ValueError("copied archive bytes differ from retained content digest")
        result[row["release_id"]] = {
            "content_digest": actual,
            "manifest_digest": sha256(bytes(row["manifest_bytes"])).hexdigest(),
            "compiler": json.loads(bytes(row["manifest_bytes"]))["profile"]["compiler_version"],
        }
        if open_archives:
            opened = open_release(connection, row["release_id"])
            if opened.release_id != row["release_id"]:
                raise ValueError("archive reader returned another release")
    return result


def prepare_source(settings, output: Path, source, guideline_text: str):
    from sqlalchemy import select

    from corpus_structure.core.method import MethodSettings
    from corpus_structure.core.vocab import RunKind
    from corpus_structure.orchestrate import m1
    from corpus_structure.orchestrate.phase0 import bind_pdf_source
    from corpus_structure.orchestrate.registry import MethodRegistry
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.semantic._operation_calls import initialize_source_project
    from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
    from corpus_structure.semantic.authored_sql import (
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationBinding
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.regeneration import prepare_pack
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.source_views import load_source_view, selected_source_views

    pack = ROOT / "domains/statistics"
    bundle, dependencies, profile, prepared = prepare_pack(pack)
    with open_runtime_engine(settings, "m1-dev-archive", purpose="admit") as engine:
        with engine.begin() as conn:
            persist_release(conn, bundle, dependencies, profile, prepared)
            if not has_authored_sql(prepared):
                admit_release(prepared, connection=conn)
        if has_authored_sql(prepared):
            with (
                open_runtime_engine(settings, "m1-dev-sql", purpose="read") as reader,
                reader.connect() as conn,
            ):
                analyzed = analyze_archived_sql(conn, prepared.release_id)
            with engine.begin() as conn:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
                admit_release(prepared, connection=conn)

    reference = ProductReference(**PRODUCT)
    realization = f"source:m1-development:{uuid4().hex}"
    with open_runtime_engine(settings, "m1-dev-source", purpose="write") as engine:
        with engine.begin() as conn:
            documents = list(
                conn.execute(
                    select(table("kb.document")).where(table("kb.document").c.project_id == PROJECT)
                ).mappings()
            )
            document = m1.retained_document(
                conn,
                reference,
                prepared=prepared,
                project_id=PROJECT,
                documents=documents,
            )
            initialize_source_project(
                conn,
                project_id=ProjectId(PROJECT),
                release_id=ReleaseId(prepared.release_id),
                realization_id=RealizationId(realization),
                projection_context=prepared,
            )
            revision = conn.scalar(
                select(table("data.realization").c.data_revision).where(
                    table("data.realization").c.realization_id == realization,
                )
            )
        registry = m1.bind_retained_document(
            bind_pdf_source(m1.registry(pack), reference, input_role="integrated"),
            document,
        )
        configs = dict(registry.file.configs)
        named = dict(configs["ingest.pdf_integrated"])
        named["default"] = dict(named["default"], sections=(source["pin"]["section_pointer"],))
        configs["ingest.pdf_integrated"] = named
        registry = MethodRegistry(
            registry.methods(),
            replace(registry.file, configs=configs),
            registry.sources,
            prepared=registry.prepared,
        )
        report = run_source_methods(
            engine,
            project_id=PROJECT,
            prepared=prepared,
            binding=OperationBinding(
                prepared.release_id,
                realization,
                revision,
                canonical_bytes({"domain": "statistics", "release": prepared.release_id}),
            ),
            registry=registry,
            graph=m1.source_graph().for_kind(RunKind.INGEST),
            method_settings=MethodSettings(
                data_dir=settings.paths.data_dir,
                model_cache=settings.paths.model_cache,
            ),
            domain="statistics",
            kind="ingest",
            corpus_record={"documents": [document.key]},
            scope_record=None,
            policy_source=None,
            guideline=guideline_text,
            extraction_policy="m1-candidate",
            extraction_policy_config=(pack / "m1-methods.yaml").read_text(),
            fresh=("ingest.pdf_integrated",),
        )
        if report.status != "source_ready" or report.cut_id is None:
            raise ValueError("source-only execution did not produce its sealed source-ready cut")
        with engine.connect() as conn:
            selected = selected_source_views(conn, report.run_id)
            if (
                len(selected) != 1
                or selected[0].section_pointer != source["pin"]["section_pointer"]
            ):
                raise ValueError("source run selected another section or broadened the source cut")
            view = load_source_view(conn, selected[0].id, analysis=False)
            if view.text != source["text"] or list(view.pieces) != source["pieces"]:
                raise ValueError(
                    "fresh source projection differs from retained development snapshot"
                )
            if view.ref.native_product != reference:
                raise ValueError("fresh source view changed the retained integrated input")
    write_json(output / "source-run.json", report)
    return prepared, report, view, document


def create_references(
    settings, output: Path, prepared, report, view, document, paragraph, guideline_text
):
    from sqlalchemy import select, text

    from corpus_structure.evaluate import record_references as references
    from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.runtime import open_runtime_engine

    with (
        open_runtime_engine(settings, "m1-dev-references", purpose="evaluate") as engine,
        engine.begin() as conn,
    ):
        references.assign_origin(
            conn,
            project_id=PROJECT,
            origin_group="siegrist-development",
            partition="development",
            source_uris=(document.source_uri,),
            provenance={
                "origin": "Siegrist retained original",
                "independence_claim": "none",
                "cohort": "purposive development paragraph",
            },
        )
        conn.execute(
            text("SELECT eval.assign_document_split(:p,:u,'dev')"),
            {"p": PROJECT, "u": document.source_uri},
        )
        pin = {
            "source": references.source_binding(
                conn,
                source_run_id=report.run_id,
                source_view_id=view.ref.id,
                source_cut_id=report.cut_id,
            ),
            "native_product_task_id": PRODUCT["task_id"],
            "product_key": PRODUCT["product_key"],
            "product_digest": PRODUCT["content_digest"],
            "source_view_id": view.ref.id,
            "projection_digest": view.ref.projection_digest,
            "recipe_digest": view.ref.recipe_digest,
        }
        scopes = [
            {
                "pin": pin,
                "space": "native",
                "pointer": view.ref.section_pointer,
                "precision": "item",
            }
        ]
        items = {item["self_ref"]: item for item in view.items}
        targets = []
        for piece in paragraph["pieces"]:
            pointer = piece["item_ref"]
            if piece not in view.pieces or piece["kind"] != "native_text":
                raise ValueError("paragraph citation piece differs from actual selected view")
            native_text = items[pointer]["text"]
            if native_text != view.text[piece["start"] : piece["end"]]:
                raise ValueError("paragraph piece is not its exact retained native text")
            scopes.extend(
                (
                    {
                        "pin": pin,
                        "space": "selected_projection",
                        "pointer": pointer,
                        "precision": "exact",
                        "start": piece["start"],
                        "end": piece["end"],
                    },
                    {
                        "pin": pin,
                        "space": "native",
                        "pointer": pointer,
                        "precision": "exact",
                        "start": 0,
                        "end": len(native_text),
                    },
                    {"pin": pin, "space": "native", "pointer": pointer, "precision": "item"},
                )
            )
            targets.append(
                {
                    "pointer": pointer,
                    "projection_start": piece["start"],
                    "projection_end": piece["end"],
                    "native_text": native_text,
                }
            )
        frame = RecordEvaluationFrame(
            view.ref.key,
            prepared.release_id,
            GUIDELINE,
            REFERENCE_POLICY,
            PREDICTION_POLICY,
            pin,
            frozenset(),
            anchor_scopes=tuple(scopes),
        )
        created = references.create_reference_set(
            conn,
            project_id=PROJECT,
            source_run_id=report.run_id,
            source_cut_id=report.cut_id,
            label=f"m1-development-paragraph-{report.run_id}",
            legacy_split="dev",
            guideline=GUIDELINE,
            guideline_text=guideline_text,
            partition="development",
            unit_keys=(view.ref.key,),
            frames={view.ref.key: frame},
            reference_policy_version=REFERENCE_POLICY,
            prediction_policy_version=PREDICTION_POLICY,
            sampling={
                "seed": 0,
                "strata": {view.ref.key: "purposive-development-paragraph"},
                "inclusion_probabilities": {view.ref.key: 1},
                "provenance": {
                    "selection": "operator selected retained view5 paragraph[29:468)",
                    "population_claim": "development target only; no random sample",
                },
                "cohort": "Siegrist development paragraph",
            },
        )
        units = table("eval.reference_unit")
        unit_id = conn.scalar(select(units.c.id).where(units.c.set_id == created["set_id"]))
        packet = references.author_packet(conn, unit_id)
    write_json(output / "reference-set.json", created)
    write_json(output / "author-packet.json", packet)
    write_json(output / "response-schema.json", packet["authored_schema"])
    write_json(output / "frozen-frame.json", packet["source_frame"])
    write_json(
        output / "target-paragraph.json",
        {
            "purpose": "all supported source readings wholly within this development paragraph",
            "source_view_id": view.ref.id,
            "unit_ref": view.ref.key,
            "coordinate_space": "selected_projection",
            "start": 29,
            "end": 468,
            "text": view.text[29:468],
            "citation_targets": targets,
            "context_outside_target": "context only; cannot enlarge denominator",
            "families": ["definition", "assertion", "measurement", "table", "formula_context"],
            "empty_families": "author determines from source; no nonempty output requirement",
        },
    )
    (output / "guideline.md").write_text(guideline_text, encoding="utf-8")
    return unit_id, frame


def author_session(settings, output: Path, unit_id: int, frame) -> None:
    from corpus_structure.evaluate import record_references as references
    from corpus_structure.semantic.runtime import open_runtime_engine

    print(json.dumps({"status": "ready", "unit_id": unit_id, "output": str(output)}), flush=True)
    with open_runtime_engine(settings, "m1-dev-author-passes", purpose="evaluate") as engine:
        for line in sys.stdin:
            request = json.loads(line)
            action = request["action"]
            if action == "close":
                return
            with engine.begin() as conn:
                if action == "submit":
                    if set(request) != {"action", "pass", "actor", "path"} or request[
                        "pass"
                    ] not in {"A", "B", "C"}:
                        raise ValueError(
                            "submit requires action, pass A/B/C, actor and authored path"
                        )
                    authored = Path(request["path"]).resolve().read_bytes()
                    with (output / f"pass-{request['pass']}-authored.json").open("xb") as retained:
                        retained.write(authored)
                    identity = references.record_pass(
                        conn,
                        unit_id=unit_id,
                        pass_kind=request["pass"],
                        actor=request["actor"],
                        authored=authored,
                        frame=frame,
                    )
                    result = {
                        "pass_id": identity,
                        "unit_id": unit_id,
                        "pass": request["pass"],
                        "actor": request["actor"],
                        "authored_sha256": sha256(authored).hexdigest(),
                    }
                    filename = f"pass-{request['pass']}-receipt.json"
                elif action == "packet-c":
                    result = references.adjudication_packet(conn, unit_id)
                    filename = "adjudication-packet.json"
                elif action == "agreement":
                    result = references.agreement(conn, unit_id)
                    filename = "agreement.json"
                else:
                    raise ValueError("action must be submit, packet-c, agreement or close")
            write_json(output / filename, result)
            print(json.dumps({"status": "stored", "artifact": str(output / filename)}), flush=True)


def execute(args, source, paragraph, guideline_text, inputs):
    from corpus_structure.semantic.migrations import current_revision, head_revision, upgrade
    from native_test_support import PgAdmin, server_url

    if head_revision() != NATIVE_TARGET:
        raise ValueError("helper requires settled native101 as the sole current migration head")
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("evidence output must be a new directory")
    output.mkdir(parents=True)
    name = "cs_sem_m1dev_" + uuid4().hex[:20]
    settings = settings_for(name)
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    receipt: dict[str, Any] = {
        "source_database": SOURCE_DATABASE,
        "owned_database": name,
        "project": PROJECT,
        "status": "preparing",
        "input_sha256": inputs,
        "helper_sha256": digest(Path(__file__)),
        "native_target": NATIVE_TARGET,
        "claim": "purposive development reference preparation only",
    }
    receipt_path = output / "session-receipt.json"
    write_json(receipt_path, receipt)
    try:
        policy = server.policy(SOURCE_DATABASE)
        if policy.owner != pwd.getpwuid(os.getuid()).pw_name:
            raise ValueError("source policy owner differs from owned-database maintenance identity")
        write_json(output / "database-policy.json", policy)
        (ROOT / "build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="m1-dev-reference-", dir=ROOT / "build") as scratch:
            archive = Path(scratch) / "native99.dump"
            with archive.open("xb") as dump:
                command(
                    [
                        "sudo",
                        "-n",
                        "-u",
                        "postgres",
                        "env",
                        "PGAPPNAME=m1-dev-source-dump",
                        "/usr/lib/postgresql/18/bin/pg_dump",
                        "--host=/var/run/postgresql",
                        "--port=5434",
                    "--username=postgres",
                        f"--dbname={SOURCE_DATABASE}",
                        "--format=custom",
                        "--no-password",
                        "--lock-wait-timeout=5s",
                    ],
                    output,
                    "dump",
                    stdout=dump,
                )
            receipt["dump"] = {"sha256": digest(archive), "bytes": archive.stat().st_size}
            write_json(receipt_path, receipt)
            with server.database(name, "template0") as maintenance:
                with archive.open("rb") as dump:
                    command(
                        [
                            "sudo",
                            "-n",
                            "-u",
                            "postgres",
                            "env",
                            "PGAPPNAME=m1-dev-owned-restore",
                            "/usr/lib/postgresql/18/bin/pg_restore",
                            "--host=/var/run/postgresql",
                            "--port=5434",
                        "--username=postgres",
                            f"--dbname={name}",
                            "--no-password",
                            "--exit-on-error",
                        ],
                        output,
                        "restore",
                        stdin=dump,
                    )
                server.replay_policy(name, policy)
                with maintenance.begin() as conn:
                    before = archive_witness(conn)
                    receipt["source_native_revision"] = current_revision(conn)
                    upgrade(conn, NATIVE_TARGET)
                    receipt["owned_native_revision"] = current_revision(conn)
                    after = archive_witness(conn, open_archives=True)
                if before != after:
                    raise ValueError("copy upgrade changed existing immutable archive bytes")
                write_json(output / "preserved-archives.json", after)
                receipt["preserved_archives"] = len(after)
                receipt["status"] = "source_preparation"
                write_json(receipt_path, receipt)
                prepared, report, view, document = prepare_source(
                    settings, output, source, guideline_text
                )
                unit_id, frame = create_references(
                    settings,
                    output,
                    prepared,
                    report,
                    view,
                    document,
                    paragraph,
                    guideline_text,
                )
                receipt.update(
                    status="authoring",
                    run_id=int(report.run_id),
                    cut_id=report.cut_id,
                    release_id=prepared.release_id,
                    unit_id=unit_id,
                )
                write_json(receipt_path, receipt)
                author_session(settings, output, unit_id, frame)
            receipt["status"] = "closed"
        receipt["dump_removed"] = True
        receipt["owned_database_disposed"] = True
    except BaseException as error:
        receipt.update(status="failed", error_type=type(error).__name__, error=str(error))
        (output / "failure.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        write_json(receipt_path, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--guideline", type=Path, default=EVIDENCE / "development-reference-guideline.md"
    )
    parser.add_argument("--output", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-inputs", action="store_true", help="read local artifacts only")
    mode.add_argument(
        "--execute", action="store_true", help="root GO: own disposable DB until stdin EOF"
    )
    args = parser.parse_args()
    source, paragraph, guideline_text, inputs = local_inputs(args.guideline.resolve())
    if args.check_inputs:
        print(
            json.dumps(
                {
                    "status": "local_inputs_passed",
                    "input_sha256": inputs,
                    "source_product": PRODUCT,
                    "section": source["pin"]["section_pointer"],
                    "paragraph": [paragraph["start"], paragraph["end"]],
                },
                indent=2,
            )
        )
        return
    if args.output is None:
        parser.error("--execute requires a new --output evidence directory")
    execute(args, source, paragraph, guideline_text, inputs)


if __name__ == "__main__":
    main()
