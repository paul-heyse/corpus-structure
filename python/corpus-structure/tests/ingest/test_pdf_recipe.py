"""Complete retained recipe reconstruction, independent of native PDF initialization."""

import json
import math
import subprocess
import sys
from dataclasses import dataclass
from hashlib import sha256

import pytest

from corpus_structure.ingest.pdf import PdfRecipe, _recipe_adapter

WIRE = (
    b'{"device":"cuda","formula_revision":"'
    + b"b" * 40
    + b'","layout_revision":"'
    + b"a" * 40
    + b'","model_artifacts":[],"model_revisions":[],"ocr_device":"cpu",'
    b'"parser_threads":8,"recipe_id":"docling-standard-pdf-v3",'
    b'"stage_batch_size":4,"timeout_seconds":null}'
)


def test_canonical_recipe_vector_and_strict_nested_tuples():
    recipe = PdfRecipe.from_bytes(WIRE)
    assert recipe.to_bytes() == WIRE
    assert recipe.digest == sha256(WIRE).hexdigest()
    assert recipe.parser_threads == 8 and recipe.timeout_seconds is None
    body = json.loads(WIRE)
    body["model_artifacts"] = [["layout", "c" * 64]]
    body["model_revisions"] = [["repo/model", "d" * 40]]
    restored = PdfRecipe.from_bytes(json.dumps(body, indent=2).encode())
    assert restored.model_artifacts == (("layout", "c" * 64),)
    assert restored.model_revisions == (("repo/model", "d" * 40),)


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda b: b.pop("parser_threads"), "missing=.*parser_threads"),
        (lambda b: b.update(secret="not echoed"), "extra=.*secret"),
        (lambda b: b.update(parser_threads="8"), "valid integer"),
        (lambda b: b.update(parser_threads=0), "positive"),
        (lambda b: b.update(layout_revision="main"), "immutable commit"),
        (lambda b: b.update(model_artifacts=[["x", "c" * 64], ["x", "d" * 64]]), "unique names"),
        (
            lambda b: b.update(model_revisions=[["x", "c" * 40], ["x", "d" * 40]]),
            "unique immutable",
        ),
    ],
)
def test_complete_fields_types_and_constructor_invariants(change, match):
    body = json.loads(WIRE)
    change(body)
    with pytest.raises(ValueError, match=match) as error:
        PdfRecipe.from_bytes(json.dumps(body).encode())
    if "secret" in body:
        assert "not echoed" not in str(error.value)


def test_nonobject_and_malformed_json_are_distinct():
    with pytest.raises(ValueError, match="must be an object"):
        PdfRecipe.from_bytes(b"[]")
    with pytest.raises(json.JSONDecodeError):
        PdfRecipe.from_bytes(b"{")


@pytest.mark.parametrize("timeout", [None, 1, float("inf"), float("nan")])
def test_existing_timeout_acceptance_is_preserved(timeout):
    body = json.loads(WIRE)
    body["timeout_seconds"] = timeout
    value = PdfRecipe.from_bytes(json.dumps(body).encode()).timeout_seconds
    if isinstance(timeout, float) and math.isnan(timeout):
        assert value is not None and math.isnan(value)
    else:
        assert value == timeout


def test_cached_adapter_is_actual_class_scoped():
    @dataclass(frozen=True, slots=True)
    class Extended(PdfRecipe):
        extra: str = "default"

    body = json.loads(WIRE)
    body["extra"] = "retained"
    child = Extended.from_bytes(json.dumps(body).encode())
    assert type(child) is Extended and child.extra == "retained"
    assert _recipe_adapter(PdfRecipe) is _recipe_adapter(PdfRecipe)
    assert _recipe_adapter(Extended) is _recipe_adapter(Extended)
    assert _recipe_adapter(PdfRecipe) is not _recipe_adapter(Extended)
    with pytest.raises(ValueError, match="extra"):
        Extended.from_bytes(WIRE)
    with pytest.raises(ValueError, match="extra"):
        PdfRecipe.from_bytes(json.dumps(body).encode())


def test_reconstruction_does_not_import_native_options():
    code = (
        "import sys; from corpus_structure.ingest.pdf import PdfRecipe; "
        f"PdfRecipe.from_bytes({WIRE!r}); "
        'assert "docling.datamodel.pipeline_options" not in sys.modules; '
        'assert "docling.document_converter" not in sys.modules'
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
