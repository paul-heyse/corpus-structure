"""Shared controlled inputs and builders for characterization native support."""

from hashlib import sha256
from types import SimpleNamespace

from pydantic import create_model

from corpus_structure.semantic.operations import claim_tasks, create_task, record_method


def make_task(conn, source, *, compose=False, layers=()):
    name = "text.compose_view" if compose else "native-binding"
    if compose:
        from corpus_structure.methods.characterization import ComposeViewMethod

        method = ComposeViewMethod()
    else:
        method = SimpleNamespace(
            name=name,
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("CharacterizationNativeFixture"),
        )
    params = dict(
        characterization_base_document=source.base.values(),
        characterization_source_scope=source.scope,
        characterization_layers=[p.values() for p in layers],
    )
    if compose:
        params["characterization_profile"] = "selected_layers" if layers else "source_only"
    else:
        params.update(
            model=getattr(source, "model", "native-retained"),
            grammar=getattr(source, "grammar", "no-grammar"),
            context="exact-source",
        )
    config_hash = sha256(str(params).encode()).hexdigest()
    config = record_method(conn, method, "default", params, config_hash, prepared=source.prepared)
    task = create_task(
        conn,
        run_id=source.task["run_id"],
        config_id=config,
        stage="ingest",
        unit_type="document",
        unit_id=source.task["unit_id"],
        unit_key=name,
        input_hash="fixture-input",
        fresh=True,
    )
    claim = claim_tasks(
        conn, run_id=source.task["run_id"], config_id=config, holder="characterization-fixture"
    )[0]
    return task, claim, config_hash
