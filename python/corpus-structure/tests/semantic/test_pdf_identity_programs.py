"""Typed identity producers retain their current native ABI and capture ACLs."""

import pytest

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_inventory import update_function_inventory
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.pdf_binary_identity_native import (
    pdf_artifact_identity_programs,
    pdf_artifact_identity_sql,
    pdf_binary_identity_programs,
    pdf_binary_identity_sql,
)
from corpus_structure.semantic.pdf_descriptor_native import (
    pdf_descriptor_programs,
    pdf_descriptor_sql,
)


def _artifact_programs():
    return pdf_artifact_identity_programs(get_metadata())


def _artifact_sql():
    return pdf_artifact_identity_sql(get_metadata())


@pytest.mark.parametrize(
    ("produce", "capture", "expected", "source", "strict", "volatility"),
    (
        (
            pdf_descriptor_programs,
            pdf_descriptor_sql,
            (("pdf_product_descriptor", ("bytea",)),),
            "target-current:PDF descriptor CHECK prerequisite",
            True,
            "immutable",
        ),
        (
            pdf_binary_identity_programs,
            pdf_binary_identity_sql,
            (
                ("pdf_identity_frame", ("bytea", "bytea")),
                ("pdf_identity_fold_start", ("text",)),
                ("pdf_identity_fold_step", ("bytea", "bigint", "bytea")),
                ("pdf_identity_fold_finish", ("bytea", "bigint", "bigint")),
                ("pdf_identity_byte_root", ("bytea",)),
                ("pdf_identity_utf8", ("bytea",)),
                ("pdf_identity_scalar", ("text", "bytea")),
                ("pdf_identity_record_frame", ("text", "text", "text", "text[]", "bytea[]")),
            ),
            "target-current:PDF publication",
            True,
            "immutable",
        ),
        (
            _artifact_programs,
            _artifact_sql,
            (("pdf_identity_verify_artifact", ("text", "text", "text")),),
            "target-current:PDF publication",
            False,
            "stable",
        ),
    ),
)
def test_identity_declarations_preserve_capture_metadata(
    produce, capture, expected, source, strict, volatility
):
    declarations = produce()
    assert tuple((item.identity.name, item.identity.arguments) for item in declarations) == expected
    inventory = {}
    update_function_inventory(inventory, capture())
    for declaration in declarations:
        assert declaration.owner == role_name("publisher")
        assert declaration.source == source
        assert declaration.access == INTERNAL_PROGRAM
        assert declaration.routine.strict is strict
        assert declaration.routine.volatility == volatility
        assert declaration.routine.search_path == ("pg_catalog", "pg_temp")
        assert declaration.routine.security_definer is False
        signature = (
            "ops."
            + declaration.identity.name
            + "("
            + ",".join(declaration.identity.arguments)
            + ")"
        )
        observed = inventory.pop(signature)
        assert observed["owner"] == declaration.owner
        assert observed["execute_roles"] == []
        assert observed["strict"] is strict
        assert observed["volatility"] == {"immutable": "i", "stable": "s"}[volatility]
    assert inventory == {}


def test_identity_producers_hold_structured_programs_until_render(monkeypatch):
    def refuse_render(self):
        raise AssertionError("producer eagerly rendered its routine")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    declarations = (
        *pdf_descriptor_programs(),
        *pdf_binary_identity_programs(),
        *_artifact_programs(),
    )
    assert len(declarations) == 10
    artifact = declarations[-1].routine
    assert artifact.returns.setof is True
    assert tuple(name for name, _ in artifact.table_columns) == (
        "actual_length",
        "actual_byte_root",
    )
