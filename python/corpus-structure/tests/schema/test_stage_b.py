"""Stage B (model and projections §3.3; P0-M-5): the declarations the shape generator reads.

The generated shapes themselves are tested where they are used (`tests/core`, `tests/ingest`,
`tests/validate`, …) and their files by the drift test (`test_model.py`); the committed JSON
Schemas by `tests/core/test_shapes.py`. Here: Stage B's declarations are checked like every
other (a malformed hook or Python expression is refused), a hook that names no hand-written
function fails generation, and the `parse_detail` payload has its registry entry.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from corpus_structure.schema import model, stage_b
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


def test_the_parse_detail_payload_has_a_registry_entry() -> None:
    """O1's rendition write looks the payload schema up by kind and refuses without one."""
    from corpus_structure.schema import registry

    loaded = model.load()
    assert "parse_detail" not in registry.without_schema(loaded)
    (entry,) = [e for e in registry.payload_schema_entries(loaded) if e.kind == "parse_detail"]
    assert entry.class_ == "sys:ParseDetail"
