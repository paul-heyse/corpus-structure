"""Independent review regressions for native hierarchy and configured pack policy."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.methods.m1_source import M1Config, _structural_groups
from corpus_structure.semantic.identity import canonical_bytes

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("axis", ["column", "row"])
@pytest.mark.parametrize(
    "geometry,expected",
    [
        ("nested", "present"),
        ("crossing", "unresolved"),
        ("overlapping_levels", "unresolved"),
    ],
)
def test_only_nested_nonoverlapping_native_header_paths_are_readings(
    monkeypatch, axis, geometry, expected
):
    from corpus_structure.methods import record_assembly

    rectangles = [(0, 1, 0, 2), (1, 2, 1, 2), (2, 3, 1, 2)]
    if geometry == "crossing":
        rectangles[1] = (1, 2, 1, 3)
    if geometry == "overlapping_levels":
        rectangles[0] = (0, 2, 0, 2)
    cells = []
    for index, (ra, rb, ca, cb) in enumerate(rectangles):
        if axis == "row":
            ra, rb, ca, cb = ca, cb, ra, rb
        cells.append(
            dict(
                text=("parent", "child", "value")[index],
                start_row_offset_idx=ra,
                end_row_offset_idx=rb,
                start_col_offset_idx=ca,
                end_col_offset_idx=cb,
                **(
                    {"column_header" if axis == "column" else "row_header": True}
                    if index < 2
                    else {}
                ),
            )
        )
    captured = {}

    def capture(context, **kwargs):
        captured.update(kwargs)
        return ()

    monkeypatch.setattr(record_assembly, "native_table_groups", capture)
    _structural_groups(
        SimpleNamespace(items=(dict(self_ref="#/tables/1", data=dict(table_cells=cells)),)),
        SimpleNamespace(region="#/tables/1", families=("table",)),
        object(),
    )
    key = "header_paths" if axis == "column" else "row_paths"
    assert captured[key].get(2, ()) == ((0, 1) if expected == "present" else ())


def test_configured_descriptions_change_pack_conditioning_without_changing_released_roles():
    from corpus_structure.methods.m1_source import configured_packs
    from methods.domain_configuration import candidate_configuration
    from methods.m1_producer_support import release

    cfg = candidate_configuration(ROOT / "domains/statistics", "described")
    assert isinstance(cfg, M1Config)
    described = configured_packs(release(), cfg)
    plain = configured_packs(release(), cfg.model_copy(update={"pack_descriptions": {}}))
    assert set(described) == {"definition", "assertion", "measurement", "table", "formula_context"}
    for family, pack in described.items():
        actual = json.loads(pack.declaration_json)["structures"][family]
        old = json.loads(plain[family].declaration_json)["structures"][family]
        assert pack.fingerprint != plain[family].fingerprint
        for field in actual["fields"]:
            assert field["description"] == cfg.pack_descriptions[family][field["name"]]
            del field["description"]
        assert actual == old


def test_default_policy_is_baseline_and_described_is_explicit_experimental_selection():
    from methods.domain_configuration import candidate_configuration

    baseline = candidate_configuration(ROOT / "domains/statistics", "default")
    experimental = candidate_configuration(ROOT / "domains/statistics", "described")
    assert isinstance(baseline, M1Config) and isinstance(experimental, M1Config)
    assert baseline.pack_descriptions == {}
    assert experimental.pack_descriptions
    assert baseline.model_dump(exclude={"pack_descriptions"}) == experimental.model_dump(
        exclude={"pack_descriptions"}
    )
    assert canonical_bytes(baseline.model_dump(mode="json")) != canonical_bytes(
        experimental.model_dump(mode="json")
    )


@pytest.mark.parametrize(
    "descriptions,match",
    [
        ({"invented_family": {"term": "instruction"}}, "unsupported M1 family"),
        ({"definition": {"term": " "}}, "must be nonempty"),
        ({"definition": {"invented_role": "instruction"}}, "unreleased family role"),
    ],
)
def test_description_policy_rejects_unknown_families_empty_instructions_and_unreleased_roles(
    descriptions, match
):
    from corpus_structure.methods.m1_source import configured_packs
    from methods.domain_configuration import candidate_configuration
    from methods.m1_producer_support import release

    cfg = candidate_configuration(ROOT / "domains/statistics", "described")
    with pytest.raises(ValueError, match=match):
        changed = type(cfg).model_validate(
            dict(cfg.model_dump(mode="python"), pack_descriptions=descriptions)
        )
        configured_packs(release(), changed)
