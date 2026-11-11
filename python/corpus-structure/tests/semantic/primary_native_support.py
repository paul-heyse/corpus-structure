"""Real primary staging for native analytical-consumer scenarios."""

from typing import Any

from sqlalchemy import select

from corpus_structure.core.vocab import Stage
from corpus_structure.methods.construction_characterization import (
    ConstructionCharacterizationMethod,
)
from corpus_structure.methods.formal_evidence import FormalEvidenceMethod
from corpus_structure.methods.native_evidence import NativeEvidenceMethod
from corpus_structure.semantic.characterization_store import read_inventory
from corpus_structure.semantic.metadata import table


def stage_primary_layers(case, run, sources):
    """Use the ordinary producer path, retaining its actual published product pins."""
    views = table("kb.source_view")
    ids = tuple(dict.fromkeys(source.source_view_id for source in sources))
    with case.writer.connect() as conn:
        rows = conn.execute(select(views).where(views.c.id.in_(ids))).mappings().all()
    assert len(rows) == len(ids)
    base = dict(
        task_id=rows[0]["native_task_id"],
        product_key=rows[0]["native_product_key"],
        content_digest=rows[0]["native_content_digest"],
    )
    scope = dict(
        source_view_ids=list(ids),
        source_views=[
            dict(
                source_view_id=row["id"],
                key=row["key"],
                base_document=base,
                section_pointer=row["section_pointer"],
                membership=row["membership"],
                projection_digest=row["projection_digest"],
                recipe_digest=row["recipe_digest"],
            )
            for row in rows
        ],
        profile="native-consumer-scenario",
        selectors=[
            dict(projection=row["projection_digest"], start=0, end=len(row["projection"]["text"]))
            for row in rows
        ],
    )
    selection = dict(
        characterization_base_document=base,
        characterization_source_scope=scope,
    )
    pins = []
    for method, cfg in (
        (NativeEvidenceMethod(), dict(selection, characterization_profile="spacy_only")),
        (FormalEvidenceMethod(), selection),
        (ConstructionCharacterizationMethod(), selection),
    ):
        cfg = dict(cfg, characterization_layers=list(pins))
        result = run(method, Stage.EXTRACT, sources, cfg, "primary-" + method.name)
        run_id = result if isinstance(result, int) else result["run_id"]
        with case.writer.connect() as conn:
            (product,) = [
                row for row in read_inventory(conn, run_id)["products"] if row["kind"] == "layer"
            ]
        assert product["method"] == method.name
        pins.append(product["reference"])
    return pins


def publish_primary_layers(conn, run, prepared, identities, *, formal=False):
    """Run real primary producers and publish their products under owned claims."""
    from logging import getLogger
    from pathlib import Path
    from types import SimpleNamespace

    from pydantic import BaseModel
    from sqlalchemy import text

    from corpus_structure.core.method import Method, MethodContext, MethodSettings, UnitView
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
    from corpus_structure.semantic.operations import (
        BoundReader,
        claim_tasks,
        complete_unit_result,
        create_task,
        record_method,
    )

    reader = BoundReader(conn, run, prepared)
    views = [reader.source_view(identity) for identity in identities]
    base = views[0].ref.native_product
    assert all(view.ref.native_product == base for view in views)
    scope = dict(
        source_view_ids=list(identities),
        source_views=[
            dict(
                source_view_id=view.ref.id,
                key=view.ref.key,
                base_document=base.values(),
                section_pointer=view.ref.section_pointer,
                membership=view.ref.membership,
                projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest,
            )
            for view in views
        ],
        profile="test-primary-consumer",
        selectors=[
            dict(projection=view.ref.projection_digest, start=0, end=len(view.text))
            for view in views
        ],
    )
    pins = []

    def publish[C: BaseModel](method: Method[C], options):
        params = dict(
            characterization_base_document=base.values(),
            characterization_source_scope=scope,
            characterization_layers=[pin.values() for pin in pins],
            **options,
        )
        selected = MethodRegistry(
            (method,), MethodsFile(configs={method.name: {"primary-control": params}})
        ).resolve(method.name, "primary-control")
        config_id = record_method(
            conn, method, selected.name, selected.params, selected.config_hash, prepared=prepared
        )
        config = method.Config.model_validate(selected.params)
        run_view = SimpleNamespace(reader=reader)
        (ref,) = method.select(run_view, config)
        input_hash = "primary-control:" + method.name
        task_id = create_task(
            conn,
            run_id=run,
            config_id=config_id,
            stage="extract",
            unit_type=str(ref.unit_type),
            unit_id=ref.unit_id,
            unit_key=ref.unit_key,
            input_hash=input_hash,
            fresh=True,
        )
        (claim,) = claim_tasks(conn, run_id=run, config_id=config_id, holder="primary-control")
        runtime = conn.scalar(text("SELECT runtime_id FROM ops.run WHERE id=:run"), {"run": run})
        operation = dict(
            key=method.name,
            version=method.version,
            runtime=runtime,
            configuration=selected.config_hash,
            input=input_hash,
            **{key: selected.params[key] for key in ("model", "grammar", "context")},
        )
        assert all(isinstance(value, str) and value for value in operation.values())
        frozen_operation = {key: str(value) for key, value in operation.items()}
        reader.characterization_selection = tuple(pins)
        (result,) = method.run(
            (UnitView(ref, run_view, document_id=ref.unit_id),),
            config,
            MethodContext(
                run=run_view,
                reader=reader,
                settings=MethodSettings(data_dir=Path("."), model_cache=Path(".")),
                logger=getLogger("test-primary-publication"),
                check_active=lambda: None,
                characterization_operation=lambda _ref: frozen_operation,
            ),
        )
        assert result.characterization_layer is not None
        complete_unit_result(
            conn,
            task_id=task_id,
            attempt=claim.attempt,
            holder="primary-control",
            prepared=prepared,
            result=result,
            method=method,
            configuration_hash=selected.config_hash,
            source=views[0].ref.key,
        )
        pins.append(result.characterization_layer.reference(task_id))

    publish(NativeEvidenceMethod(), dict(characterization_profile="spacy_only"))
    if formal:
        publish(FormalEvidenceMethod(), {})
    publish(ConstructionCharacterizationMethod(), {})
    reader.characterization_selection = tuple(pins)
    return tuple(pins)


def bind_primary_agent_run(
    conn, capture_run, prepared, identities, configuration: dict[str, Any], *, method="agent.opus"
):
    """Freeze real primary pins before authoring an agent run over the original views."""
    import json

    from corpus_structure.semantic._operation_calls import select_source_view
    from corpus_structure.semantic._operation_ids import SourceViewId
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operation_results import RunId
    from corpus_structure.semantic.operations import OperationBinding, create_run

    runs = table("ops.run")
    original = conn.execute(select(runs).where(runs.c.id == capture_run)).mappings().one()
    pins = publish_primary_layers(conn, capture_run, prepared, identities, formal=True)
    configuration = dict(configuration, characterization_layers=[pin.values() for pin in pins])
    key = method + "/" + configuration["mode"]
    options = dict(original["options"])
    options["agent_configs"] = {**options.get("agent_configs", {}), key: configuration}
    dependencies = json.loads(original["dependencies"])
    dependencies["agent_configurations"] = dict(options["agent_configs"])
    run = create_run(
        conn,
        project_id=original["project_id"],
        binding=OperationBinding(
            prepared.release_id,
            original["input_realization_id"],
            original["input_revision"],
            canonical_bytes(dependencies),
        ),
        kind=original["kind"],
        options=options,
        code_commit="primary-agent-scenario",
        guideline=original["guideline"],
    )
    for identity in identities:
        select_source_view(
            conn,
            run_id=run,
            source_run_id=RunId(capture_run),
            source_view_id=SourceViewId(identity),
            projection_context=prepared,
        )
    return run, configuration
