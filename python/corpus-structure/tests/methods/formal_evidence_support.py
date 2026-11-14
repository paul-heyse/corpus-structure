"""Controlled inputs and builders shared by the formal evidence consumers."""

import logging
from pathlib import Path
from types import SimpleNamespace

from semantic.primary_formal_fixture import operation, source
from semantic.primary_formal_fixture import prepared as prepared

from corpus_structure.core.method import MethodContext, MethodSettings, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.formal_evidence import FormalEvidenceConfig


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
