"""Current producer support rejects unsupported native/text/math adapter revisions."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.native_adapter_contracts import validate_native_adapters
from corpus_structure.semantic.types import PreparationError


def test_current_native_adapters_and_kernels_are_bound():
    model = compile_execution_model(trusted_execution_inputs())
    for name in (
        "prepare_parsing_text",
        "interpret_parsing_math",
        "assess_parsing_math",
        "map_pdf_observation",
        "compare_pdf_occurrences",
        "select_pdf_integration",
    ):
        assert model.require_operation(name).implementation == name
    assert not {o.id for o in model.operations} & {
        "prepare_parsing_product",
        "publish_parsing_product",
        "read_parsing_product",
        "recognize_html",
    }
    assert not any(
        c.id in {"ParsingProduct", "ParsingRepresentation", "ParsingNode"} for c in model.concepts
    )


def test_unsupported_native_adapter_revision_refuses():
    model = compile_execution_model(trusted_execution_inputs())
    with pytest.raises(PreparationError, match=r"qualify.*producer profile"):
        validate_native_adapters(
            replace(
                model,
                parsing_adapters=(
                    replace(model.parsing_adapters[0], frontend_revision="unsupported"),
                ),
            )
        )
