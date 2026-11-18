"""Independent capture, closed-import and projection-isolation expectations."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import BigInteger, Boolean, Double, Numeric, Text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TIMESTAMP

from corpus_structure.model.compiled import (
    annotation_values,
    boolean_annotation,
    compiled_model,
    running_model,
)


def schema(member: str) -> bytes:
    return (
        "id: urn:example\nname: example\nprefixes: {ex: 'urn:ex:'}\n"
        "default_prefix: ex\nenums:\n  Choice:\n    permissible_values:\n"
        f"      {member}: {{}}\n"
    ).encode()


def members(view):
    enum = view.get_enum("Choice")
    assert enum is not None
    values = enum.permissible_values
    assert isinstance(values, dict)
    return values


def test_running_and_candidate_captures_keep_independent_members():
    running = compiled_model({"root": schema("old")})
    candidate = compiled_model({"root": schema("new")})
    assert set(members(running.view("root"))) == {"old"}
    assert set(members(candidate.view("root"))) == {"new"}
    assert compiled_model({"root": schema("old")}) is running
    assert running.identity != candidate.identity
    assert compiled_model({"root": schema("old") + b"# comment\n"}).identity != running.identity


def test_root_and_private_projection_do_not_mutate_other_views():
    model = compiled_model({"a": schema("a"), "b": schema("b")})
    private = model.private_view("a")
    members(private).clear()
    assert set(members(model.view("a"))) == {"a"}
    assert set(members(model.view("b"))) == {"b"}
    members(model.view("a")).clear()
    assert set(members(model.view("a"))) == {"a"}


def test_unsupplied_import_never_falls_through_to_linkml_or_disk():
    model = compiled_model({"root": b"id: urn:x\nname: x\nimports: [linkml:types]\n"})
    with pytest.raises(ValueError, match="not supplied: linkml:types"):
        model.view("root")


def test_imported_annotations_preserve_empty_lists_and_source_relative_names():
    model = compiled_model(
        {
            "root": b"id: urn:root\nname: root\nimports: [child]\n",
            "child": (
                b"id: urn:child\nname: child\nprefixes: {c: 'urn:child:'}\ndefault_prefix: c\n"
                b"classes:\n  Thing:\n    annotations:\n      cs:case: casefold\n"
                b"      cs:enabled: false\n      ph:read_roles: {tag: 'ph:read_roles', value: []}\n"
                b"    attributes:\n      value:\n        annotations: {cs:case: preserve}\n"
            ),
            "catalog.yaml": b"- an instance\n- another instance\n",
        }
    )
    view = model.private_view("root", normalize=True)
    thing = view.get_class("Thing")
    assert thing is not None
    assert thing.class_uri == "c:Thing"
    assert annotation_values(thing)["ph:read_roles"] == []
    assert annotation_values(thing)["cs:case"] == "casefold"
    assert boolean_annotation(thing, "cs:enabled") is False
    slot = view.class_induced_slots("Thing")[0]
    assert slot.slot_uri == "c:value"
    assert annotation_values(slot)["cs:case"] == "preserve"


def test_projection_failure_is_retained_for_its_capture_only():
    calls = []

    def fail():
        calls.append(1)
        raise ValueError("broken declaration")

    model = compiled_model({"root": schema("failure")})
    for _ in range(2):
        with pytest.raises(ValueError, match="broken declaration"):
            model.projection("validation", fail)
    assert calls == [1]
    assert compiled_model({"root": schema("corrected")}).projection("validation", lambda: 7) == 7


def test_concurrent_capture_consumers_build_their_projection_once():
    rendezvous = Barrier(8)
    builds = []
    sources = {"root": schema("concurrent") + b"#" + b"x" * 2_000_000 + b"\n"}

    def build():
        builds.append(1)
        return "one artifact"

    def consume(_):
        rendezvous.wait()
        return compiled_model(sources).projection("artifact", build)

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(consume, range(8))) == ["one artifact"] * 8
    assert builds == [1]


def test_field_kind_types_have_one_declared_resolution():
    fields = running_model().field_kinds()
    expected = {
        "integer": ("int", "int8", BigInteger),
        "string": ("str", "text", Text),
        "boolean": ("bool", "bool", Boolean),
        "timestamp": ("datetime", "timestamptz", TIMESTAMP),
        "json_payload": ("JsonValue", "jsonb", JSONB),
        "bytes": ("bytes", "bytea", BYTEA),
        "decimal": ("Decimal", "numeric", Numeric),
        "float": ("float", "float8", Double),
    }
    assert set(fields) == set(expected)
    for name, (python, postgres, kind) in expected.items():
        assert (fields[name].python, fields[name].postgres) == (python, postgres)
        assert isinstance(fields[name].sqlalchemy, kind)
    timestamp = fields["timestamp"].sqlalchemy
    assert isinstance(timestamp, TIMESTAMP)
    assert timestamp.timezone


def test_companion_columns_follow_declared_roles_and_inventory_dimensions():
    columns = running_model().companion_columns()
    assert {name: spec.group for name, spec in columns.items()} == {
        "input": "input_role",
        "relation": "relation_kind",
        "coverage": "outcome",
        "mapping_report": "outcome",
    }
    assert columns["relation"].distinct == "relation_id"
    assert set(columns["input"].values) == {
        "input_ordinal",
        "input_role",
        "input_task_id",
        "input_product_key",
        "input_content_digest",
    }
    assert {"producer_release_id", "task_id", "projection_id"} <= set(columns["input"].provenance)
    sources = dict(running_model().sources)
    sources["companion-projections.yaml"] = sources["companion-projections.yaml"].replace(
        b"cp:group_by: input_role", b"cp:group_by: input_ordinal"
    )
    assert compiled_model(sources).companion_columns()["input"].group == "input_ordinal"
    assert columns["input"].group == "input_role"
