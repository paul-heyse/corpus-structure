"""The formal operation consumes the execution owner's exact immutable determinants."""

import logging
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from semantic.test_formal_evidence import operation, source
from semantic.test_formal_evidence import prepared as prepared

from corpus_structure.core.method import MethodContext, MethodSettings, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.formal_evidence import FormalEvidenceConfig, FormalEvidenceMethod


def inputs(prepared):
    view = source(("x≥2", "text", "", ""))
    reader = SimpleNamespace(
        prepared=prepared,
        source_view=lambda identity: view,
        source_views=lambda: (view.ref,),
        source_view_ref={view.ref.id: view.ref}.__getitem__,
    )
    run = SimpleNamespace(reader=reader)
    unit = UnitView(UnitRef(TaskUnitType.DOCUMENT, view.ref.document_id), run)
    selected_scope = dict(
        source_view_ids=[view.ref.id],
        source_views=[
            dict(
                source_view_id=view.ref.id,
                key=view.ref.key,
                base_document=view.ref.native_product.values(),
                section_pointer=view.ref.section_pointer,
                membership=view.ref.membership,
                projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest,
            )
        ],
        profile="selected",
        selectors=[
            dict(projection=view.ref.projection_digest, native_pointer="#/texts/0", start=0, end=3)
        ],
    )
    cfg = FormalEvidenceConfig(
        characterization_base_document=view.ref.native_product.values(),
        characterization_source_scope=selected_scope,
    )
    identity = {**operation(), "grammar": cfg.grammar, "context": cfg.context, "model": cfg.model}
    ctx = MethodContext(
        run,
        reader,
        MethodSettings(data_dir=Path("."), model_cache=Path(".")),
        logging.getLogger(__name__),
        characterization_operation=lambda ref: identity,
    )
    return unit, cfg, ctx, identity


def test_method_publishes_detached_layer_with_actual_task_provenance(prepared):
    unit, cfg, ctx, identity = inputs(prepared)
    method = FormalEvidenceMethod()
    assert tuple(method.select(unit.run, cfg)) == (unit.ref,)
    (result,) = method.run([unit], cfg, ctx)
    layer = result.characterization_layer
    assert layer is not None
    assert all(layer.payload["operation"][key] == value for key, value in identity.items())
    changed = cfg.model_copy(update={"math_start": "formula"})
    assert method.input_digest(unit, cfg).bytes != method.input_digest(unit, changed).bytes


def test_stale_grammar_and_mismatched_task_determinants_refuse(prepared):
    with pytest.raises(ValueError, match="effective grammar"):
        FormalEvidenceConfig(grammar="obsolete")
    unit, cfg, ctx, identity = inputs(prepared)
    identity["configuration"] = "actual-frozen-config"
    identity["grammar"] = "wrong-grammar"
    with pytest.raises(ValueError, match="determinants"):
        FormalEvidenceMethod().run([unit], cfg, ctx)


def test_cancellation_prevents_a_terminal_complete_layer(prepared):
    unit, cfg, ctx, _identity = inputs(prepared)

    def cancel():
        raise RuntimeError("operation cancelled")

    ctx = replace(ctx, check_active=cancel)
    with pytest.raises(RuntimeError, match="cancelled"):
        FormalEvidenceMethod().run([unit], cfg, ctx)


def test_exact_frozen_source_selection_is_required_and_limits_discovery(prepared):
    unit, cfg, ctx, _identity = inputs(prepared)
    method = FormalEvidenceMethod()
    with pytest.raises(ValueError, match="exact frozen"):
        method.select(unit.run, FormalEvidenceConfig())
    assert cfg.characterization_source_scope is not None
    selected = {
        **cfg.characterization_source_scope,
        "selectors": [dict(projection="b" * 64, native_pointer="#/texts/0", start=2, end=3)],
    }
    cfg = cfg.model_copy(update={"characterization_source_scope": selected})
    (result,) = method.run([unit], cfg, ctx)
    assert result.characterization_layer is not None
    payload = result.characterization_layer.payload
    assert payload["source_scope"] == selected
    assert not any(
        annotation["family"] == "formal.threshold" for annotation in payload["annotations"]
    )
    assert {
        extent["text"] for occurrence in payload["occurrences"] for extent in occurrence["extents"]
    } == {"2"}


def test_multiple_selected_projections_keep_distinct_formal_forest_identities(prepared):
    unit, cfg, ctx, _identity = inputs(prepared)
    first = source(("x+y=1", "formula", "x+y=1", "succeeded"))
    second = replace(first, ref=replace(first.ref, id=12, key="second", projection_digest="d" * 64))
    views = {view.ref.id: view for view in (first, second)}
    scope = dict(
        source_view_ids=list(views),
        source_views=[
            dict(
                source_view_id=view.ref.id,
                key=view.ref.key,
                base_document=view.ref.native_product.values(),
                section_pointer=view.ref.section_pointer,
                membership=view.ref.membership,
                projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest,
            )
            for view in views.values()
        ],
        profile="multiple-selected",
        selectors=[
            dict(projection=view.ref.projection_digest, start=0, end=len(view.text))
            for view in views.values()
        ],
    )
    cfg = cfg.model_copy(update=dict(characterization_source_scope=scope, math_start="formula"))
    reader = SimpleNamespace(
        prepared=prepared,
        source_view=views.__getitem__,
        source_view_ref={identity: view.ref for identity, view in views.items()}.__getitem__,
        source_views=lambda: tuple(view.ref for view in views.values()),
    )
    run = SimpleNamespace(reader=reader)
    unit = replace(unit, run=run)
    ctx = replace(ctx, run=run, reader=reader)
    (result,) = FormalEvidenceMethod().run([unit], cfg, ctx)
    assert result.characterization_layer is not None
    body = result.characterization_layer.payload
    roots = {
        row["local_id"]
        for row in body["annotations"]
        if row["family"] == "formal.math" and "formal_input" in row
    }
    assert len(roots) == 4
    symbols = [row for row in body["annotations"] if row["kind"] == "formal.symbol"]
    assert {row["formal"]["input_id"] for row in symbols} == roots
    assert len({row["local_id"] for row in symbols}) == len(symbols) == 8
