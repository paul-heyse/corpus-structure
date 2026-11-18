"""Every retained PDF lowering input remains an authenticated captured artifact."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_lowering import LOWERING_CONTRACT, require_lowering_identity


def test_every_retained_lowering_input_refuses_altered_captured_bytes():
    context = trusted_pdf_context()
    domain = context.domain
    retained = domain.source(LOWERING_CONTRACT)
    assert require_lowering_identity(context) == retained.digest
    declared = json.loads(retained.content)["inputs"]
    assert declared

    for item in declared:
        altered_name = item["name"].removeprefix("pdf-domain/")
        artifact = domain.source(altered_name)
        altered = replace(artifact, content=artifact.content + b"\nchanged")

        def source(name, altered_name=altered_name, altered=altered):
            return altered if name == altered_name else domain.source(name)

        captured = SimpleNamespace(domain=SimpleNamespace(source=source))
        try:
            require_lowering_identity(captured)
        except ValueError as failure:
            assert str(failure) == "captured PDF lowering source differs from its contract", (
                altered_name
            )
        else:
            pytest.fail(f"altered retained input was accepted: {altered_name}")

    assert require_lowering_identity(context) == retained.digest
