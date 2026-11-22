"""Set hydration over independent admitted rows; native custody has separate controls."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic_core import to_jsonable_python
from sqlalchemy import cast, event, values

from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_consumers import (
    BoundConsumerSelection,
    hydrate_consumer_selection,
)
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.data_operation_jsonb import json_context_value
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_projections import binding_columns
from corpus_structure.semantic.data_operation_storage import AdmittedDataRead
from corpus_structure.semantic.data_operation_support import (
    ComputationalSupportReference,
    support_reference_records,
)
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_operation_version import MODEL_VERSION


def _member(**changes):
    return replace(
        BoundRoleMember(
            "product:shared",
            "kind:accepted",
            "subject:shared",
            "original:one",
            b'{"page":1}',
            b"{}",
            ("episode:one",),
            b'{"use_id":"use:one"}',
            member="member:shared",
            subject_definition="document",
            support_references=(
                ComputationalSupportReference(
                    derivation_id="episode:one", admission_use_id="use:one"
                ),
            ),
        ),
        **changes,
    )


def _admitted_rows(records):
    columns = binding_columns(decoder=True)
    rows = []
    for member, body in records:
        row = {
            "product": member.product,
            "kind_contract": member.kind_contract,
            "subject": member.subject,
            "subject_definition": member.subject_definition,
            "original_source": member.original_source,
            "analyzed_scope": json_context_value(json_loads(member.analyzed_scope)),
            "coverage": json_loads(member.coverage),
            "support_episodes": list(member.support_episodes),
            "support_references": support_reference_records(member.support_references),
            "support_evidence": json_context_value(json_loads(member.support_evidence)),
            "position": member.position,
            "multiplicity": member.multiplicity,
            "member": member.member,
            "provider_identity": member.provider_identity,
            "alternative_identity": member.alternative_identity,
            "body": to_jsonable_python(body),
            "meaning_body": semantic_value(body),
        }
        rows.append(
            tuple(
                cast(row[item.name], item.type) if item.name == "position" else row[item.name]
                for item in columns
            )
        )
    return values(*columns, name="independent_admitted_rows").data(rows)


@pytest.fixture
def hydration_case(monkeypatch, native_rollback):
    connection = native_rollback.connection
    model = SimpleNamespace(
        version=MODEL_VERSION,
        identities=(
            SimpleNamespace(owner="operation", domain="definition", key="definition"),
            SimpleNamespace(owner="operation", domain="eligibility", key="eligibility"),
        ),
        operation=lambda _: SimpleNamespace(
            subject="document",
            roles=tuple(
                SimpleNamespace(name=name, kind="kind") for name in ("left", "right", "empty")
            ),
        ),
    )
    statements = []

    def record(_, __, statement, ___, ____, _____):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", record)

    def hydrate(records, roles, *, capacity=1024 * 1024):
        read = AdmittedDataRead(
            _admitted_rows(records), {"kind": ("kind:accepted", "kind:other")}, b"admission"
        )
        monkeypatch.setattr(
            "corpus_structure.semantic.data_operation_storage.admitted_data_read",
            lambda *args, **kwargs: read,
        )
        binding = BindingResult(
            "operation",
            "root",
            roles,
            "ready",
            (),
            b"{}",
            b"{}",
            MODEL_VERSION,
            "definition",
            "eligibility",
            (b"admission",),
            subject_context=SubjectContext(
                "project", "root", "original:one", b"{}", subject_definition="document"
            ),
            replicate=None,
        )
        return hydrate_consumer_selection(
            connection,
            model,
            BoundConsumerSelection(binding),
            demand_id="demand",
            read_id="read",
            trust_snapshot={},
            max_bytes=capacity,
        )

    try:
        yield hydrate, statements
    finally:
        event.remove(connection, "before_cursor_execute", record)


@pytest.mark.parametrize("original_source", ["original:one", None])
def test_hydration_preserves_repeated_pins_scopes_multiplicity_and_absence(
    hydration_case, original_source
):
    hydrate, statements = hydration_case
    first = _member(multiplicity=2, original_source=original_source)
    second = _member(analyzed_scope=b'{"page":2}')
    result = hydrate(
        [(first, {"text": "one"}), (second, {"text": "two"})],
        (
            ResolvedRoleBinding("left", "present", (second, first)),
            ResolvedRoleBinding("right", "present", (first,)),
            ResolvedRoleBinding("empty", "known-absent"),
        ),
    )
    assert [value.value() for value in result.role("left")] == [
        {"text": "two"},
        {"text": "one"},
        {"text": "one"},
    ]
    assert [value.member for value in result.role("right")] == [first, first]
    assert result.role("empty") == ()
    assert len(statements) == 1
    assert "consumer_pins" in statements[0]


@pytest.mark.parametrize("count,queries", [(1, 1), (1024, 1), (1025, 2)])
def test_hydration_uses_one_body_query_per_bounded_values_page(hydration_case, count, queries):
    hydrate, statements = hydration_case
    member = _member()
    result = hydrate([(member, 7)], (ResolvedRoleBinding("left", "present", (member,) * count),))
    assert len(result.role("left")) == count
    assert all(value.value() == 7 for value in result.role("left"))
    assert len(statements) == queries


@pytest.mark.parametrize(
    "changes",
    [
        {"product": "other"},
        {"member": "other"},
        {"kind_contract": "kind:other"},
        {"subject": "other"},
        {"subject_definition": "other-kind"},
        {"original_source": "other"},
        {"original_source": None},
        {"analyzed_scope": b"null"},
        {"support_evidence": b"{}"},
        {
            "support_episodes": ("episode:other",),
            "support_references": (
                ComputationalSupportReference(
                    derivation_id="episode:other", admission_use_id="use:one"
                ),
            ),
        },
        {
            "support_references": (
                ComputationalSupportReference(
                    derivation_id="episode:one", admission_use_id="use:other"
                ),
            )
        },
        {"position": 1},
        {"multiplicity": 2},
    ],
    ids=[
        "product",
        "member",
        "kind",
        "subject",
        "subject-definition",
        "original",
        "source-free",
        "scope",
        "support",
        "episodes",
        "references",
        "position",
        "multiplicity",
    ],
)
def test_hydration_requires_every_retained_pin(hydration_case, changes):
    hydrate, _ = hydration_case
    with pytest.raises(ValueError, match="one admitted body"):
        hydrate(
            [(_member(), "body")],
            (ResolvedRoleBinding("left", "present", (_member(**changes),)),),
        )


def test_hydration_refuses_duplicate_admitted_bodies(hydration_case):
    hydrate, _ = hydration_case
    member = _member()
    with pytest.raises(ValueError, match="one admitted body"):
        hydrate(
            [(member, "one"), (member, "two")],
            (ResolvedRoleBinding("left", "present", (member,)),),
        )


def test_hydration_packet_limit_applies_across_values_pages(hydration_case):
    hydrate, statements = hydration_case
    member = _member()
    # Both stored buffers count. The second page must not reset ownership.
    with pytest.raises(ValueError, match="packet capacity"):
        hydrate(
            [(member, 7)],
            (ResolvedRoleBinding("left", "present", (member,) * 1025),),
            capacity=1024 * (len(b"7") + len(b'["integer","7"]')),
        )
    assert len(statements) == 2


def test_hydration_refuses_kind_outside_declared_input_family(hydration_case):
    hydrate, statements = hydration_case
    member = _member(kind_contract="kind:unadmitted")
    with pytest.raises(ValueError, match="one admitted body"):
        hydrate([(member, "body")], (ResolvedRoleBinding("left", "present", (member,)),))
    assert statements == []


def test_hydration_keeps_typed_values_and_accounts_for_received_buffers(hydration_case):
    from datetime import date

    from corpus_structure.semantic.data_operation_values import CollectionValue, OptionalValue
    from corpus_structure.semantic.identity import canonical_bytes

    hydrate, _ = hydration_case
    member = _member()
    body = {
        "when": date(2026, 11, 21),
        "choice": OptionalValue("unknown"),
        "values": CollectionValue("set", (2, 7)),
    }
    result = hydrate([(member, body)], (ResolvedRoleBinding("left", "present", (member,)),))
    (value,) = result.role("left")
    assert value.value() == body
    assert value.content == b'{"choice":null,"values":[2,7],"when":"2026-11-21"}'
    assert value.meaning == canonical_bytes(semantic_value(body))
    assert result.measured_bytes == len(value.content) + len(value.meaning)
    with pytest.raises(ValueError, match="packet capacity"):
        hydrate(
            [(member, body)],
            (ResolvedRoleBinding("left", "present", (member,)),),
            capacity=result.measured_bytes - 1,
        )
