"""Finite first-party revision data builders, resolved only during authoring."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from sqlalchemy import BigInteger, cast, column, func, select, true

DataStep = Literal["pdf-visual-mapping", "characterization-source-scope"]


def build_data_step(name: DataStep, metadata):
    if name == "pdf-visual-mapping":
        product = metadata.tables["ops.pdf_product_body"]
        digest = product.c.descriptor["observation"]["mapped_evidence_digest"].astext
        return (
            select(
                func.ops.index_pdf_visual_mapping(product.c.task_id, product.c.product_key, digest)
            )
            .where(digest.is_not(None))
            .order_by(product.c.task_id, product.c.product_key)
        )
    if name == "characterization-source-scope":
        product = metadata.tables["ops.characterization_product"]
        scope = metadata.tables["kb.characterization_source_scope"]
        pin = (
            func.jsonb_array_elements(product.c.payload["source_scope"]["source_views"])
            .table_valued(column("value", product.c.payload.type))
            .alias("pin")
        )
        view = cast(pin.c.value["source_view_id"].astext, BigInteger)
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        return (
            pg_insert(scope)
            .from_select(
                ["task_id", "product_key", "content_digest", "source_view_id", "body"],
                select(
                    product.c.task_id,
                    product.c.product_key,
                    product.c.content_digest,
                    view,
                    pin.c.value,
                )
                .select_from(product.join(pin, true()))
                .order_by(product.c.task_id, product.c.product_key, view),
            )
            .on_conflict_do_nothing()
        )
    raise ValueError("unsupported first-party data step")


def builder_inputs(root, package):
    # Keep this finite builder self-contained; it uses only shared SQLAlchemy and metadata.
    path = Path(package) / "semantic/native_data_steps.py"
    return path, (root / path).read_bytes()


def require_frozen_data_prerequisites(existing, target_metadata):
    required = {"ops.pdf_visual_index", "kb.characterization_source_scope"}
    missing = required.intersection(target_metadata.tables).difference(existing)
    if missing:
        raise ValueError(
            "historical derived-data prerequisites require registered frozen forward-base replay: "
            + ", ".join(sorted(missing))
        )
