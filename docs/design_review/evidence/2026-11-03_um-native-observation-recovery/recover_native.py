"""Qualify and derive one retained native observation through current protected APIs.

No organized/enriched content or historical runtime is imported. Verification is the
read-only default. Execution requires an explicit owned target/OID and frozen head.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from hashlib import file_digest, sha256
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from typing import Any

NATIVE_SHA = "ca05561954ebf2318e2f020590d74cd87ecac6917e2e992a7b24b679cb6ce504"
PRODUCER_SHA = "f89813cf6ce20c9dd3105838674766862211742629ec6d3a44f706064efe7cba"
SOURCE_SHA = "e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9"
WITNESSES = Path("docs/design_review/evidence/2026-11-01_pdf-current-rebuild/runtime/raw")
ORIGINAL = Path("docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf")
PROJECT = "pdf-docling-adoption"


@dataclass(frozen=True)
class NativeWitness:
    envelope: Path
    binding: dict[str, Any]
    recipe: bytes
    producer_witness_sha: str
    source_sha: str
    schema_sha: str
    health: dict[str, Any]
    producer_options: dict[str, Any]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def checked_envelope(path: Path, binding: dict[str, Any]) -> dict[str, Any]:
    if path.stat().st_size != binding["byte_length"] or digest(path) != binding["content_digest"]:
        raise ValueError("retained envelope byte identity differs")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("retained envelope is not a mapping")
    return value


def verify_native(witnesses: Path, original: Path) -> NativeWitness:
    """Validate immutable witnesses before any database acquisition or effect."""
    binding = json.loads((witnesses / "retained-2-native.binding.json").read_bytes())
    if (binding["task_id"], binding["product_key"], binding["content_digest"]) != (
        2, "native", NATIVE_SHA
    ):
        raise ValueError("native binding differs from the accepted observation witness")
    envelope = witnesses / "retained-2-native.json"
    native = checked_envelope(envelope, binding)
    recipe = (witnesses / "retained-2.recipe.json").read_bytes()
    if sha256(recipe).hexdigest() != binding["recipe_digest"]:
        raise ValueError("retained native recipe identity differs")
    with original.open("rb") as stream:
        pdf_header = stream.read(5)
    if digest(original) != SOURCE_SHA or pdf_header != b"%PDF-":
        raise ValueError("retained original identity differs")
    parent_fields = ("parent_task_id", "parent_product_key", "parent_digest")
    if any(binding[k] is not None for k in parent_fields):
        raise ValueError("native-only derivation cannot import an organized structural parent")
    schema = files("corpus_structure").joinpath("model/semantic/docling-validation.schema.json")
    schema_sha = sha256(schema.read_bytes()).hexdigest()
    doc = native["document"]
    if (
        native["recipe_digest"] != binding["recipe_digest"]
        or native["recipe"] != "pdf-native-v1"
        or native["artifact_digest"] != SOURCE_SHA
        or native["source_scope"] != "whole_document"
        or native["schema_digest"] != schema_sha
        or native["native_schema_version"] != "1.10.0"
        or doc["schema_name"] != "DoclingDocument"
        or doc["version"] != "1.10.0"
        or len(doc["pages"]) != 1589
    ):
        raise ValueError("retained native source/schema/scope differs")
    if native["health"]["conversion"] != "success":
        raise ValueError("retained native conversion is not qualified")
    # This descendant supplies ONLY producer runtime metadata. Its document, math and
    # organization are never passed to the derivation. The exact parent binds that metadata.
    producer_binding = json.loads(
        (witnesses / "retained-2-organized.binding.json").read_bytes()
    )
    if producer_binding["content_digest"] != PRODUCER_SHA:
        raise ValueError("producer runtime witness differs from the accepted observation")
    producer = checked_envelope(witnesses / "retained-2-organized.json", producer_binding)
    expected_parent = (binding["task_id"], binding["product_key"], binding["content_digest"])
    if (
        tuple(producer_binding[k] for k in parent_fields)
        != expected_parent
        or producer_binding["task_id"] != binding["task_id"]
        or producer_binding["recipe_digest"] != binding["recipe_digest"]
        or producer["artifact_digest"] != SOURCE_SHA
    ):
        raise ValueError("producer metadata does not belong to this native observation")
    runtime = producer["runtime_report"]
    packages = {item["name"]: item["version"] for item in runtime["packages"]}
    for package in ("docling", "docling-core", "rapidocr"):
        if packages.get(package) != version(package):
            raise ValueError("retained native producer package differs: " + package)
    options = runtime["effective_options"]
    options = json.loads(options) if isinstance(options, str) else options
    ocr = options["ocr_options"]
    formula = options["code_formula_options"]
    recipe_value = json.loads(recipe)
    artifacts = dict(recipe_value["model_artifacts"])
    # None means delegate to the pinned RapidOCR defaults, not disabled detection.
    # Qualify that default against both its package and observed detector/recognizer bindings.
    import yaml

    defaults = yaml.safe_load(files("rapidocr").joinpath("config.yaml").read_bytes())["Global"]
    native_bindings = {item["name"]: item["value"] for item in runtime["bindings"]}
    rapid_params = ocr.get("rapidocr_params", {})
    enabled = {
        key: ocr[key] if ocr[key] is not None
        else rapid_params.get("Global." + key, defaults[key])
        for key in ("use_det", "use_rec")
    }
    if (
        not options["do_ocr"] or not options["do_formula_enrichment"]
        or not options["do_table_structure"] or ocr["backend"] != "onnxruntime"
        or ocr["mode"] != "pdf_aware_layout_regions" or enabled["use_det"] is not True
        or enabled["use_rec"] is not True or not formula["extract_formulas"]
        or not native_bindings.get("ocr.det.providers")
        or not native_bindings.get("ocr.rec.providers")
        or "RapidOcr/PP-OCRv6_det_small.onnx" not in artifacts
        or "RapidOcr/PP-OCRv6_rec_small.onnx" not in artifacts
        or "docling-project--CodeFormulaV2/model.safetensors" not in artifacts
    ):
        raise ValueError("required RapidOCR/CodeFormula producer capabilities unavailable")
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_methods import PdfRuntimeConfig

    parsed = PdfRecipe.from_bytes(recipe)
    selected = PdfRuntimeConfig()
    if (
        parsed.layout_revision != selected.layout_revision
        or parsed.formula_revision != selected.formula_revision
    ):
        raise ValueError("native producer model revisions differ")
    return NativeWitness(
        envelope, binding, recipe, producer_binding["content_digest"], SOURCE_SHA,
        schema_sha, native["health"], {
            "do_ocr": True, "ocr_backend": ocr["backend"], "ocr_mode": ocr["mode"],
            "do_formula_enrichment": True, "do_table_structure": True,
            "ocr_optional_flags": {k: ocr[k] for k in ("use_det", "use_rec")},
            "ocr_pinned_default_flags": enabled,
            "native_bindings": native_bindings,
            "packages": {k: packages[k] for k in ("docling", "docling-core", "rapidocr")},
            "native_ocr_region_inventory": "not_retained_in_original_observation",
        },
    )


def retain(path: Path, value: Any) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write("\n")


def verify_terminated_product(conn, witness, args, task, run, prepared, published) -> None:
    """Check one immutable native pin after its auxiliary container has terminated."""
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.pdf_storage import _record_product_identity
    from corpus_structure.semantic.product_reference import ProductReference

    reference = ProductReference(task, "native", published.logical_digest)
    reader = published_record_reader(conn, reference, projection_context=prepared)
    if reader is None:
        raise ValueError("published native pin unavailable after container termination")
    identity = _record_product_identity(
        conn, task, "native", published.logical_digest, reader,
    )
    reader._native_schema_mapping()
    wrappers = [row for row in reader.iter_companions("health") if "source_scope" in row]
    if wrappers != [{**{k: v for k, v in witness.health.items() if k != "formula_outcomes"},
                     "source_scope": "whole_document"}]:
        raise ValueError("published native health differs after container termination")
    outcomes = list(reader.native_metadata("formula_outcomes"))
    if outcomes != witness.health.get("formula_outcomes", []):
        raise ValueError("published native formula outcomes differ after termination")
    tasks, runs = table("ops.task"), table("ops.run")
    task_status = conn.scalar(select(tasks.c.status).where(tasks.c.id == task))
    run_status = conn.scalar(select(runs.c.status).where(runs.c.id == run))
    unfinished = conn.execute(select(tasks.c.id).where(
        tasks.c.run_id == run,
        tasks.c.status.in_(("pending", "running", "awaiting_intervention")),
    )).all()
    if task_status != "empty" or run_status != "cancelled" or unfinished:
        raise ValueError("auxiliary storage-container termination differs")
    retain(args.output / "post-termination-read.json", {
        "status": "passed", "product_kind": identity["kind"],
        "reference": reference.values(), "native_schema": "readable",
        "health": wrappers[0], "formula_outcome_count": len(outcomes),
        "formula_outcome_sha256": sha256(json.dumps(outcomes, sort_keys=True).encode()).hexdigest(),
        "producer_task_finished": True,
        "task_status": task_status, "container_status": run_status,
        "unfinished_tasks": [], "knowledge": "not_run", "source_views": "not_run",
    })


def execute(witness: NativeWitness, args: argparse.Namespace) -> None:
    from sqlalchemy import create_engine, select, text

    from corpus_structure.core.evidence import config_key
    from corpus_structure.core.provenance import code_commit
    from corpus_structure.ingest.pdf_methods import IngestPdf, PdfIngestConfig
    from corpus_structure.orchestrate.pdf_streaming import migrate_retained_pdf_envelope
    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.authored_sql import (
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import (
        OperationBinding,
        claim_tasks,
        complete_task,
        create_run,
        create_task,
        end_source_run,
        record_method,
        start_run,
    )
    from corpus_structure.semantic.pdf_contracts import store_pdf_original
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.regeneration import prepare_pack
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine
    from corpus_structure.settings import Settings

    settings = Settings()
    probe = create_engine(connection_settings(settings, "maintenance").database.sqlalchemy_url)
    try:
        with probe.connect() as conn:
            actual = conn.execute(text(
                "SELECT current_database(), (SELECT oid FROM pg_database "
                "WHERE datname=current_database())"
            )).one()
            head = conn.scalar(text("SELECT version_num FROM public.semantic_alembic_version"))
            if tuple(actual) != (args.database, args.database_oid) or head != args.head:
                raise ValueError("owned recovery target/head differs; no writes authorized")
    finally:
        probe.dispose()
    if args.read_published is not None:
        from corpus_structure.semantic.pdf_publication import PublishedPdfDocumentRef
        from corpus_structure.semantic.releases import open_release

        task_info = json.loads((args.read_published / "task.json").read_bytes())
        published = PublishedPdfDocumentRef(**json.loads(
            (args.read_published / "published.json").read_bytes()
        ))
        with (
            open_runtime_engine(settings, "um-native-recovery-read", purpose="read") as engine,
            engine.connect() as conn,
        ):
            prepared = open_release(conn, task_info["release_id"])
            verify_terminated_product(
                conn, witness, args, task_info["task_id"], task_info["run_id"], prepared, published,
            )
        return
    bundle, dependencies, profile, prepared = prepare_pack(DOMAINS / "statistics")
    with (
        open_runtime_engine(settings, "um-native-recovery-archive", purpose="admit") as engine,
        engine.begin() as conn,
    ):
        persist_release(conn, bundle, dependencies, profile, prepared)
    analyzed = {}
    if has_authored_sql(prepared):
        with (
            open_runtime_engine(settings, "um-native-recovery-analysis", purpose="read") as engine,
            engine.connect() as conn,
        ):
            analyzed = analyze_archived_sql(conn, prepared.release_id)
    with (
        open_runtime_engine(settings, "um-native-recovery-admit", purpose="admit") as engine,
        engine.begin() as conn,
    ):
        if analyzed:
            admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
        admit_release(prepared, connection=conn)
    source_id = f"source:{PROJECT}:{prepared.release_id}"
    method = IngestPdf()
    params = PdfIngestConfig().model_dump(mode="json")
    source = canonical_bytes({
        "purpose": "retained-native-observation-derivation",
        "source_pin": witness.binding,
        "producer_runtime_witness_sha256": witness.producer_witness_sha,
        "original_sha256": witness.source_sha,
        "current_native_schema_sha256": witness.schema_sha,
    })
    with open_runtime_engine(settings, "um-native-recovery-write", purpose="write") as engine:
        with engine.begin() as conn:
            init_bound_project(
                conn, domain="statistics", corpus=args.corpus.resolve(), name=PROJECT,
                release_id=prepared.release_id, realization_id=source_id,
            )
            realization = table("data.realization")
            revision = conn.scalar(select(realization.c.data_revision).where(
                realization.c.realization_id == source_id
            ))
            if revision is None:
                raise ValueError("current source realization unavailable")
            run = create_run(
                conn, project_id=PROJECT,
                binding=OperationBinding(prepared.release_id, source_id, revision, source),
                kind="ingest", options={"purpose": "retained-native-observation-derivation"},
                code_commit=code_commit(),
            )
            start_run(conn, run)
            config = record_method(
                conn, method, "retained-native-observation", params,
                config_key(method.name, method.version, params), prepared=prepared,
            )
            docs = table("kb.document")
            document = conn.execute(select(docs.c.id, docs.c.key).where(
                docs.c.project_id == PROJECT, docs.c.content_hash == SOURCE_SHA,
                docs.c.source_uri == "siegrist_random/Full_PDF/Full.pdf",
            )).one()
            task = create_task(
                conn, run_id=run, config_id=config, stage="ingest", unit_type="document",
                unit_id=document.id, unit_key=document.key, input_hash=sha256(source).hexdigest(),
                fresh=True,
            )
        holder = f"um-native-recovery:{task}"
        retain(args.output / "task.json", {
            "run_id": run, "task_id": task, "release_id": prepared.release_id,
            "purpose": "storage derivation only; no new inference or knowledge",
        })
        with engine.begin() as conn:
            claims = claim_tasks(
                conn, run_id=run, config_id=config, holder=holder, prepared=prepared,
            )
            if len(claims) != 1 or claims[0].task_id != task:
                raise ValueError("recovery claim selected another task")
            claim = claims[0]
            store_pdf_original(
                conn, task_id=task, attempt=claim.attempt, holder=holder,
                original=args.original.read_bytes(), recipe_bytes=witness.recipe,
            )
        published = migrate_retained_pdf_envelope(
            engine, claim, holder, path=witness.envelope,
            expected_sha256=witness.binding["content_digest"],
            original=args.original.read_bytes(),
            schema_bytes=files("corpus_structure").joinpath(
                "model/semantic/docling-validation.schema.json"
            ).read_bytes(),
            recipe_bytes=witness.recipe, directory=args.output / "private", kind="native",
            product_key="native",
        )
        retain(args.output / "published.json", asdict(published))
        retain(args.output / "native.pin.json", {
            "task_id": published.task_id, "product_key": "native",
            "content_digest": published.logical_digest,
        })
        with engine.begin() as conn:
            complete_task(
                conn, task_id=task, attempt=claim.attempt, holder=holder,
                prepared=prepared, observations=[], outcome="empty",
            )
            # This cancels the source-only container; it is not knowledge finalization.
            end_source_run(conn, run, prepared=prepared)
        with engine.connect() as conn:
            verify_terminated_product(conn, witness, args, task, run, prepared, published)
        retain(args.output / "completion.json", {
            "status": "passed", "scope": "current protected native observation derivation only",
            "run_id": run, "task_id": task, "release_id": prepared.release_id,
            "run_status": "cancelled", "native_task_status": "empty",
            "producer_task_finished": True, "derivation": "passed",
            "inference": "not_run", "knowledge": "not_run", "original_health": witness.health,
        })
    method.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--witnesses", type=Path, default=WITNESSES)
    parser.add_argument("--original", type=Path, default=ORIGINAL)
    parser.add_argument("--corpus", type=Path, default=Path("docs/statistics_corpus/corpus"))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--read-published", type=Path,
                        help="Read-only recheck of a retained published/task receipt directory.")
    parser.add_argument("--database", default="corpus_pdf_20261102")
    parser.add_argument("--database-oid", type=int, default=16934542)
    parser.add_argument("--head", help="Exact frozen target revision; mandatory for execution.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.execute or args.read_published is not None) and not args.head:
        parser.error("database operations require the exact admitted --head")
    if args.execute and args.read_published is not None:
        parser.error("--execute and --read-published are mutually exclusive")
    witness = verify_native(args.witnesses, args.original)
    args.output.mkdir(parents=True, exist_ok=False)
    retain(args.output / "qualification.json", {
        "status": "passed", "scope": "local native observation witness compatibility",
        "binding": witness.binding, "original_sha256": witness.source_sha,
        "schema_sha256": witness.schema_sha, "producer_options": witness.producer_options,
        "producer_runtime_witness_sha256": witness.producer_witness_sha,
        "health": witness.health, "database_effects": "not_run",
        "native_graph_validation": "owned by current protected derivation",
    })
    if args.execute or args.read_published is not None:
        try:
            execute(witness, args)
        except BaseException as error:
            retain(args.output / "failure.json", {
                "status": "failed", "error_type": type(error).__name__, "message": str(error),
                "scope": "protected native observation derivation; inspect retained task identity",
            })
            raise


if __name__ == "__main__":
    main()
