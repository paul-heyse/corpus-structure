"""Seeded faults Stage A refuses (P0-F-2d's generator changes): a qualifier range with no canonical
form, a core qualifier without a key role, a default outside its enum, and members whose Python
names would collide without their titles."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from corpus_structure.core import vocab
from corpus_structure.schema import generate, model

MODEL = model.MODEL_DIR


def seeded(tmp_path: Path, edit) -> model.Model:
    for name in ("core.yaml", "system.yaml"):
        data = yaml.safe_load((MODEL / name).read_text(encoding="utf-8"))
        if name == "core.yaml":
            edit(data)
        (tmp_path / name).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return model.load(tmp_path / "core.yaml", tmp_path / "system.yaml")


def test_the_model_generates_its_canonical_forms_by_ancestry() -> None:
    forms = {s["name"]: s["canonical"] for s in generate.qualifier_specs(model.load().core)}
    assert forms["core:hedge"] == "text_form" and forms["core:valid_time"] == "interval"
    assert forms["core:attribution"] == "entity_key" and forms["core:modality"] == "member"


def test_a_qualifier_range_without_a_canonical_form_is_refused(tmp_path: Path) -> None:
    def edit(d: dict) -> None:
        d["slots"]["hedge"]["range"] = "EntityRef"  # a shape class, no value range

    with pytest.raises(model.ModelError, match="range 'EntityRef' has no canonical form"):
        generate.qualifier_specs(seeded(tmp_path, edit).core)


def test_a_core_qualifier_without_a_key_role_is_refused(tmp_path: Path) -> None:
    def edit(d: dict) -> None:
        d["slots"]["hedge"]["annotations"].pop("ci:key_role")

    loaded = seeded(tmp_path, edit)
    assert "core.slots.hedge: a core qualifier declares ci:key_role" in model.check(loaded)
    with pytest.raises(model.ModelError, match="declares ci:key_role"):
        generate.qualifier_specs(loaded.core)


def test_a_default_outside_its_enum_is_refused(tmp_path: Path) -> None:
    def edit(d: dict) -> None:
        d["slots"]["polarity"]["ifabsent"] = "string(sideways)"

    with pytest.raises(model.ModelError, match="'sideways' is not a Polarity member"):
        generate.qualifier_specs(seeded(tmp_path, edit).core)


def test_titles_name_members_whose_text_would_collide(tmp_path: Path) -> None:
    assert [m.name for m in vocab.Relation] == ["LT", "LE", "EQ", "NE", "GT", "GE"]

    def edit(d: dict) -> None:
        for member in d["enums"]["Relation"]["permissible_values"].values():
            member.pop("title")

    with pytest.raises(model.ModelError, match="both name"):
        generate._vocab(seeded(tmp_path, edit))
