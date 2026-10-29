"""Stage B (model and projections §3.3; P0-M-5): the declarations the shape generator reads.

The generated shapes themselves are tested where they are used (`tests/core`, `tests/ingest`,
`tests/validate`, …) and their files by the drift test (`test_model.py`); the committed JSON
Schemas by `tests/core/test_shapes.py`. Here: Stage B's declarations are checked like every
other (a malformed hook or Python expression is refused), a hook that names no hand-written
function fails generation, a shape-changing edit generates and checks clean in one pass, and the
`parse_detail` payload has its registry entry.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from corpus_structure.schema import generate, model, stage_b
from corpus_structure.schema.model import CORE, SYSTEM, ModelError


def edited_model(tmp_path: Path, edit: Callable[[dict], None]) -> model.Model:
    """The model with `edit` applied to the parsed core module."""
    data = yaml.safe_load(CORE.read_text(encoding="utf-8"))
    edit(data)
    (tmp_path / "core.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    (tmp_path / "system.yaml").write_text(SYSTEM.read_text(encoding="utf-8"), encoding="utf-8")
    return model.load(tmp_path / "core.yaml", tmp_path / "system.yaml")


def _annotate(cls: str, attribute: str, tag: str, value: str) -> Callable[[dict], None]:
    def edit(data: dict) -> None:
        attr = data["classes"][cls]["attributes"][attribute]
        attr.setdefault("annotations", {})[tag] = value

    return edit


@pytest.mark.parametrize(
    ("tag", "value", "expected"),
    [
        ("ci:validator", "core.shape_support canonical_number", "not a validator hook"),
        ("ci:validator", "sideways core.shape_support:canonical_number", "not a validator hook"),
        ("ci:py_type", "tuple[str,", "not a Python expression"),
        ("ci:py_default", "MISSING =", "not a Python expression"),
    ],
)
def test_a_malformed_stage_b_declaration_is_refused(
    tmp_path: Path, tag: str, value: str, expected: str
) -> None:
    loaded = edited_model(tmp_path, _annotate("TextValue", "v", tag, value))
    problems = model.check(loaded)
    assert any("core.classes.TextValue.v" in p and expected in p for p in problems), problems


def test_a_hook_without_its_function_fails_generation(tmp_path: Path) -> None:
    edit = _annotate("TextValue", "v", "ci:validator", "core.shape_support:no_such_hook")
    loaded = edited_model(tmp_path, edit)
    assert model.check(loaded) == []  # well-formed; the reference is what fails
    with pytest.raises(ModelError, match="defines no no_such_hook"):
        stage_b.render(loaded)


def test_a_shape_changing_edit_generates_and_checks_clean_in_one_pass(tmp_path: Path) -> None:
    """The JSON Schemas are rendered from the shapes just generated, not the ones imported: one
    `generate` reflects a new field, and the check that follows finds no drift."""

    def add_lang(data: dict) -> None:
        data["classes"]["TextValue"]["attributes"]["lang"] = {"description": "The language."}

    loaded = edited_model(tmp_path, add_lang)
    files = generate.render(loaded)
    assert "    lang: str | MISSING = MISSING" in files["core/_model/shapes.py"]
    schema = json.loads(files["core/schemas/value.authored.json"])
    assert "lang" in schema["$defs"]["TextValue"]["properties"]  # in the same run
    out = tmp_path / "package"
    generate.write(files, out)
    assert generate.drift(generate.render(loaded), out) == []  # check: clean after one generate


def test_the_parse_detail_payload_has_a_registry_entry() -> None:
    """O1's rendition write looks the payload schema up by kind and refuses without one."""
    from corpus_structure.schema import registry

    loaded = model.load()
    assert "parse_detail" not in registry.without_schema(loaded)
    (entry,) = [e for e in registry.payload_schema_entries(loaded) if e.kind == "parse_detail"]
    assert entry.class_ == "sys:ParseDetail"
