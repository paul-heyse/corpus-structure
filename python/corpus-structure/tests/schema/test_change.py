"""The schema-change model (P0-M-4): the diff, the classifier and routes, the registry content.

Each seeded change edits a copy of the model files; its expected class is written from the
compatibility table of model and projections §3.6 (ADR-0022), not from the classifier.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.core.vocab import ChangeKind, CompatibilityClass
from corpus_structure.schema import change, model, registry

MODEL = Path(model.__file__).resolve().parents[1] / "model"
C = CompatibilityClass


@pytest.fixture(scope="module")
def base() -> model.Model:
    return model.load()


def seeded(
    tmp_path: Path,
    system: Sequence[tuple[str, str]] = (),
    core: Sequence[tuple[str, str]] = (),
) -> model.Model:
    for name, edits in (("system.yaml", system), ("core.yaml", core)):
        text = (MODEL / name).read_text(encoding="utf-8")
        for old, new in edits:
            assert text.count(old) == 1, old
            text = text.replace(old, new)
        (tmp_path / name).write_text(text, encoding="utf-8")
    return model.load(tmp_path / "core.yaml", tmp_path / "system.yaml")


def record(changes: list[dict[str, Any]], **kw: Any) -> change.ChangeRecord:
    full = [{"reason": "seeded", "authorized_by": "test", **c} for c in changes]
    return change.ChangeRecord.model_validate(
        {"from_revision": "a", "to_revision": "b", "changes": full, **kw}
    )


MENTION_TEXT = "      text: {required: true, description: The mention text.}\n"
NOTE = "      note: {description: A seeded optional field.}\n"
CLAIM_CONFIDENCE = """      confidence:
        range: Real
        description: The confidence.
      completeness:"""

SEEDS: dict[str, dict[str, Any]] = {
    "descriptive": {
        "system": [
            (MENTION_TEXT, "      text: {required: true, description: The surface text.}\n")
        ],
        "element": "sys:MentionPayload.text",
        "change": "changed",
        "aspect": "description",
    },
    "nested-additive": {
        "system": [(MENTION_TEXT, MENTION_TEXT + NOTE)],
        "element": "sys:MentionPayload.note",
        "change": "added",
        "upcaster": "absent",
    },
    "relational-additive": {
        "system": [
            (
                CLAIM_CONFIDENCE,
                CLAIM_CONFIDENCE.replace(
                    "      completeness:",
                    "      note:\n        description: A seeded column.\n      completeness:",
                ),
            )
        ],
        "element": "sys:Claim.note",
        "change": "added",
        "record": {"alembic_revision": "0002"},
    },
    "version-scoped-additive": {
        "core": [
            (
                "      definition: {description: Stipulates what a term means.",
                "      axiom: {description: A seeded kind.}\n"
                "      definition: {description: Stipulates what a term means.",
            )
        ],
        "element": "core:StatementKind#axiom",
        "change": "added",
    },
    "key-bearing": {
        "core": [
            (
                '("usually", "in some settings").\n    annotations: {ci:role: qualifier, '
                "ci:key_role: meaning}",
                '("usually", "in some settings").\n    annotations: {ci:role: qualifier, '
                "ci:key_role: identity}",
            )
        ],
        "element": "core:hedge",
        "change": "changed",
        "aspect": "ci:key_role",
        "record": {"key_consequences": {"scheme": 2}},
    },
    "breaking": {
        "system": [("      reserved: {}\n", "")],
        "element": "sys:DocumentSplit#reserved",
        "change": "removed",
        "decision": "operator, test",
    },
}


def _seed(tmp_path: Path, name: str) -> tuple[model.Model, dict[str, Any]]:
    seed = SEEDS[name]
    return seeded(tmp_path, seed.get("system", []), seed.get("core", [])), seed


@pytest.mark.parametrize("name", sorted(SEEDS))
def test_each_class_is_derived_routed_and_accepted(
    base: model.Model, tmp_path: Path, name: str
) -> None:
    new, seed = _seed(tmp_path, name)
    found = change.diff(base, new)
    assert found, name
    relevant = [c for c in found if seed["element"] is None or c.element == seed["element"]]
    assert relevant, [c.element for c in found]
    for c in found:
        assert change.required_class(c, base, new) == C(name), c
    declared = [
        {
            "element": c.element,
            "change": c.change,
            "aspect": c.aspect,
            "compatibility_class": name,
            **({"upcaster": seed["upcaster"]} if "upcaster" in seed else {}),
            **({"decision": seed["decision"]} if "decision" in seed else {}),
        }
        for c in found
    ]
    rec = record(declared, **seed.get("record", {}))
    assert change.check(rec, base, new) == []
    assert set(change.routes(rec)) == {C(name)}
    assert change.route(name) == change.ROUTES[C(name)]


def test_a_rename_is_mapped_through_the_name_map(base: model.Model, tmp_path: Path) -> None:
    new = seeded(
        tmp_path,
        [(MENTION_TEXT, "      surface: {required: true, description: The mention text.}\n")],
    )
    pairs = [
        ("sys:MentionPayload.text", ChangeKind.REMOVED),
        ("sys:MentionPayload.surface", ChangeKind.ADDED),
    ]
    assert {(c.element, c.change) for c in change.diff(base, new)} == set(pairs)
    declared = [{"element": e, "change": k, "compatibility_class": "mapped"} for e, k in pairs]
    mapped = record(declared, name_map={"sys:MentionPayload.text": "sys:MentionPayload.surface"})
    assert change.check(mapped, base, new) == []
    unmapped = change.check(record(declared), base, new)
    assert any("a rename is declared in the name map" in p for p in unmapped)
    assert any("but the change is breaking" in p for p in unmapped)
    stray = record(
        declared,
        name_map={
            "sys:MentionPayload.text": "sys:MentionPayload.surface",
            "sys:MentionPayload.label": "sys:MentionPayload.tag",
        },
    )
    assert any("not a removal and an addition" in p for p in change.check(stray, base, new))


def test_breaking_without_a_decision_is_refused(base: model.Model, tmp_path: Path) -> None:
    new, seed = _seed(tmp_path, "breaking")
    declared = [
        {"element": seed["element"], "change": "removed", "compatibility_class": "breaking"}
    ]
    assert change.check(record(declared), base, new) == [
        "sys:DocumentSplit#reserved removed: breaking is refused unless a decision is recorded "
        "(DP-24)"
    ]
    as_additive = [{**declared[0], "compatibility_class": "relational-additive"}]
    assert "but the change is breaking" in change.check(record(as_additive), base, new)[0]


def test_nested_additive_touching_an_sql_visible_path_is_refused(
    base: model.Model, tmp_path: Path
) -> None:
    attrs = "      classes: {multivalued: true, description: The block's classes.}\n"
    new = seeded(
        tmp_path,
        [
            (
                "annotations: {ci:store: nested, ci:sql_visible: id}",
                "annotations: {ci:store: nested, ci:sql_visible: id lang}",
            ),
            (attrs, attrs + "      lang: {description: A seeded field a query reads.}\n"),
        ],
    )
    found = change.diff(base, new)
    assert {c.element for c in found} == {"sys:SegmentAttrs", "sys:SegmentAttrs.lang"}
    declared = [
        {
            "element": c.element,
            "change": c.change,
            "aspect": c.aspect,
            "compatibility_class": "nested-additive",
            "upcaster": "absent",
        }
        for c in found
    ]
    problems = change.check(record(declared), base, new)
    assert len(problems) == 2
    assert all(
        "nested-additive is refused: the change touches what PostgreSQL reads" in p
        for p in problems
    )
    relational = [{**d, "compatibility_class": "relational-additive"} for d in declared]
    assert change.check(record(relational, alembic_revision="0002"), base, new) == []


def test_nested_additive_touching_a_key_bearing_path_is_refused(
    base: model.Model, tmp_path: Path
) -> None:
    new, _ = _seed(tmp_path, "key-bearing")
    declared = [
        {
            "element": c.element,
            "change": c.change,
            "aspect": c.aspect,
            "compatibility_class": "nested-additive",
            "upcaster": "absent",
        }
        for c in change.diff(base, new)
    ]
    problems = change.check(record(declared), base, new)
    assert problems and all("touches a key-bearing path" in p for p in problems)


def test_a_record_must_match_the_diff_exactly(base: model.Model, tmp_path: Path) -> None:
    new, _ = _seed(tmp_path, "relational-additive")
    assert change.check(record([]), base, new) == [
        "sys:Claim.note added: not declared (the diff gives relational-additive)"
    ]
    extra = [
        {
            "element": "sys:Claim.note",
            "change": "added",
            "compatibility_class": "relational-additive",
        },
        {
            "element": "sys:Claim.key",
            "change": "removed",
            "compatibility_class": "breaking",
            "decision": "x",
        },
    ]
    problems = change.check(record(extra, alembic_revision="0002"), base, new)
    assert problems == ["sys:Claim.key removed: declared but not in the diff"]
    no_alembic = change.check(record(extra[:1]), base, new)
    assert no_alembic == [
        "sys:Claim.note added: a relational-additive change needs the record's Alembic revision"
    ]


def test_the_shapes_mirror_the_model_classes(base: model.Model) -> None:
    for shape, cls in (
        (change.ChangeRecord, "ChangeRecord"),
        (change.ElementChange, "ElementChange"),
    ):
        slots = {str(s.name) for s in base.system.class_induced_slots(cls)}
        assert set(shape.model_fields) == slots, cls


# --- The registry content -------------------------------------------------------------------


def test_the_registry_holds_each_payload_class_at_its_version(
    base: model.Model, tmp_path: Path
) -> None:
    entries = {e.class_: e for e in registry.payload_schema_entries(base, model.read_log())}
    assert registry.without_schema(base) == []
    assert len(entries) == 22
    mention = entries["sys:MentionPayload"]
    assert (mention.version, mention.parent_version, mention.compatibility_class) == (
        1,
        None,
        C.INITIAL,
    )
    assert mention.json_schema_id.endswith("/payload.mention.json")
    assert entries["sys:VerificationPayload"].sql_visible_paths == ()
    assert entries["sys:TaskCost"].json_schema_id.endswith("/cost.json")
    assert entries["sys:ClaimProposalPayload"].kind == "claim_proposal"
    # a nested-additive step to the mention payload adds version 2 with its upcaster
    new, seed = _seed(tmp_path, "nested-additive")
    step = record(
        [
            {
                "element": seed["element"],
                "change": "added",
                "compatibility_class": "nested-additive",
                "upcaster": "absent",
                "reason": "M05 reports a note",
                "authorized_by": "method_version:mention/2",
            }
        ]
    )
    log = [*model.read_log(), {"change_record": step.model_dump(mode="json")}]
    after = {e.class_: e for e in registry.payload_schema_entries(new, log)}
    v2 = after["sys:MentionPayload"]
    assert (v2.version, v2.parent_version, v2.compatibility_class, v2.upcaster) == (
        2,
        1,
        C.NESTED_ADDITIVE,
        "absent",
    )
    assert v2.authorized_by == "method_version:mention/2"
    assert v2.arrow_schema != mention.arrow_schema
    assert after["sys:TaskCost"].version == 1
    assert set(v2.row()) == {
        "class",
        "kind",
        "version",
        "compatibility_class",
        "json_schema_id",
        "arrow_schema",
        "sql_visible_paths",
        "upcaster",
        "reason",
        "authorized_by",
    }
