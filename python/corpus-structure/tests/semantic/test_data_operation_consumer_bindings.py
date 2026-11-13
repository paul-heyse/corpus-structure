"""Actual colocated consumer contracts execute over flat qualified domain facts.

The relational fixture is an independent admitted-input seam, not native admission
or a replacement publisher. Closed population membership is explicit in each case.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import JSON, Boolean, Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.types import TypeEngine

from corpus_structure.semantic.data_operation_bindings import (
    PopulationBinding,
    ProjectionBinding,
    ProjectionField,
    compile_binding,
    execute_binding,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_consumers import consumer_selection_declarations
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
from corpus_structure.semantic.python_operation_sources import PythonSource
from corpus_structure.semantic.structural_products import ExternalSourceRef
from corpus_structure.semantic.types import SourceArtifact, SourceBundle

PREFIX = "https://corpus-structure.dev/semantic/data-operation-consumers/"
FIELDS = {
    "DdoSourceViewBinding": [
        "document_subject",
        "base_product",
        "view_key",
        "projection_digest",
        "source_recipe",
        "analysis_eligible",
    ],
    "DdoPassageBinding": ["input_subject", "passage_id", "source_ref", "start", "end"],
    "DdoReadingBinding": [
        "input_subject",
        "passage_id",
        "contribution_id",
        "source_ref",
        "producer_operation",
    ],
    "DdoOccurrenceBinding": [
        "view_subject",
        "occurrence_id",
        "contribution_id",
        "semantic_type",
        "contribution_kind",
        "anchors_valid",
        "exact_context",
    ],
}
BOOLEANS = {"analysis_eligible", "anchors_valid", "exact_context"}
INTEGERS = {"start", "end"}


def native_type(name: str) -> TypeEngine[Any]:
    return Boolean() if name in BOOLEANS else Integer() if name in INTEGERS else String()


@pytest.fixture(scope="module")
def consumer_model():
    root = Path(__file__).resolve().parents[2] / "src/corpus_structure"
    sources = tuple(
        PythonSource(name, (root / "methods" / (name + ".py")).read_bytes(), name + ".py")
        for name in ("native_evidence", "m1_source", "structural_products", "contextual_candidates")
    )
    return compile_data_operations(
        SourceBundle(
            "data_operation_consumers",
            (
                SourceArtifact(
                    "data_operation_consumers",
                    (root / "model/semantic/data-operation-consumers.yaml").read_bytes(),
                ),
            ),
        ),
        declarations=consumer_selection_declarations(sources),
    )


@contextmanager
def admitted(model, groups):
    engine = create_engine("sqlite://")
    metadata = MetaData()
    tables = {}
    for kind in groups:
        tables[kind] = Table(
            kind,
            metadata,
            *(
                Column(name, String)
                for name in (
                    "product",
                    "kind_contract",
                    "subject",
                    "original_source",
                    "member",
                    "provider_identity",
                    "alternative_identity",
                )
            ),
            *(
                Column(name, JSON)
                for name in ("analyzed_scope", "coverage", "support_episodes", "support_evidence")
            ),
            Column("position", Integer),
            Column("multiplicity", Integer),
            *(Column(name, native_type(name)) for name in FIELDS[kind]),
        )
    metadata.create_all(engine)
    identities = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    projections = []
    with engine.begin() as connection:
        for kind, rows in groups.items():
            table = tables[kind]
            for row in rows:
                value = dict(
                    product="product:" + row["id"],
                    kind_contract=identities[PREFIX + kind, "kind"],
                    subject=row["subject"],
                    original_source=row.get("source", "original"),
                    member=row["id"],
                    provider_identity=None,
                    alternative_identity=None,
                    analyzed_scope={},
                    coverage={},
                    support_episodes=["episode:" + row["id"]],
                    support_evidence={"native": "fixture"},
                    position=0,
                    multiplicity=1,
                )
                value.update({field: row.get(field) for field in FIELDS[kind]})
                connection.execute(table.insert(), value)
            projections.append(
                ProjectionBinding(
                    PREFIX + kind,
                    table,
                    tuple(
                        ProjectionField(
                            name,
                            name,
                            "boolean"
                            if name in BOOLEANS
                            else "integer"
                            if name in INTEGERS
                            else "string",
                        )
                        for name in FIELDS[kind]
                    ),
                    b'{"native":"fixture"}',
                )
            )
        yield connection, tuple(projections)
    engine.dispose()


def population(name, *members):
    return PopulationBinding(
        name, "closed:" + name, True, members, b'{"derivation_id":"closure:fixture"}'
    )


def hydrated_component_selection(method, binding, records):
    """Independent body fixtures exercise consumer algorithms, not native custody."""
    from corpus_structure.semantic.data_operation_consumers import (
        HydratedConsumerSelection, SelectedConsumerValue,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    selected = method.select_bound(binding)
    return HydratedConsumerSelection(selected, tuple(
        (role.role, tuple(SelectedConsumerValue(member, canonical_bytes(records[member.member]))
                         for member in role.members for _ in range(member.multiplicity)))
        for role in selected.roles
    ))


def test_native_consumer_resolves_shared_base_document_views(consumer_model):
    rows = [
        dict(
            id="view:one",
            subject="view:one",
            document_subject="document",
            base_product="base",
            projection_digest="projection",
        ),
        dict(
            id="view:other", subject="view:other", document_subject="document", base_product="other"
        ),
    ]
    with admitted(consumer_model, {"DdoSourceViewBinding": rows}) as (connection, projections):
        result = execute_binding(
            connection,
            compile_binding(
                consumer_model,
                "text.native_evidence/selection",
                projections,
                subject="document",
                parameters={"base_product": "base"},
                populations=(population("selected-source-views", "view:one"),),
            ),
        )
        assert result.status == "ready"
        assert [member.subject for member in result.roles[0].members] == ["view:one"]
        from corpus_structure.methods.native_evidence import NativeEvidenceMethod
        method = NativeEvidenceMethod()
        inputs = hydrated_component_selection(method, result, {row["id"]: row for row in rows})
        document, views = method.select_hydrated(inputs)
        assert document == "document"
        assert [view.member.member for view in views] == ["view:one"]


def test_m1_consumer_optional_projection_is_exact_one_eligible_view(consumer_model):
    rows = [
        dict(
            id=name,
            subject=name,
            document_subject="document",
            projection_digest=digest,
            analysis_eligible=eligible,
        )
        for name, digest, eligible in (
            ("one", "selected", True),
            ("two", "other", True),
            ("ineligible", "selected", False),
        )
    ]
    with admitted(consumer_model, {"DdoSourceViewBinding": rows}) as (connection, projections):
        base = dict(
            subject="document",
            choices={"source_selection": "views"},
            populations=(population("eligible-source-views", "one", "two"),),
        )
        result = execute_binding(
            connection,
            compile_binding(consumer_model, "extract.m1_candidates/selection", projections, **base),
        )
        assert result.status == "ready"
        assert {member.member for member in result.roles[0].members} == {"one", "two"}
        result = execute_binding(
            connection,
            compile_binding(
                consumer_model,
                "extract.m1_candidates/selection",
                projections,
                subject="document",
                choices={"source_selection": "projection"},
                parameters={"projection_digest": "selected"},
                populations=(population("selected-projection-views", "one"),),
            ),
        )
        assert result.status == "ready"
        assert [
            member.member
            for role in result.roles
            if role.role == "projection"
            for member in role.members
        ] == ["one"]
        from corpus_structure.methods.m1_source import M1Candidates
        method = M1Candidates()
        inputs = hydrated_component_selection(method, result, {row["id"]: row for row in rows})
        assert [view.member.member for view in method.select_hydrated(inputs)] == ["one"]
        result = execute_binding(
            connection,
            compile_binding(
                consumer_model,
                "extract.m1_candidates/selection",
                projections,
                subject="document",
                choices={"source_selection": "projection"},
                parameters={"projection_digest": "missing"},
                populations=(population("selected-projection-views"),),
            ),
        )
        assert result.status == "not-applicable"


def test_contextual_consumer_requires_every_requested_occurrence_id(consumer_model):
    rows = [
        dict(
            id="occurrence:one",
            subject="occurrence:one",
            view_subject="view",
            occurrence_id="one",
            semantic_type="definition",
            anchors_valid=True,
            exact_context=True,
        ),
        dict(
            id="occurrence:other",
            subject="occurrence:other",
            view_subject="view",
            occurrence_id="other",
            semantic_type="other",
            anchors_valid=True,
            exact_context=True,
        ),
    ]
    groups = {
        "DdoSourceViewBinding": [
            dict(id="view", subject="view", base_product="base", projection_digest="projection")
        ],
        "DdoOccurrenceBinding": rows,
    }
    with admitted(consumer_model, groups) as (connection, projections):
        for required, status in ((("one",), "ready"), (("one", "missing"), "not-applicable")):
            result = execute_binding(
                connection,
                compile_binding(
                    consumer_model,
                    "retrieve.contextual/selection",
                    projections,
                    subject="view",
                    parameters={
                        "source_product": "base",
                        "source_projection": "projection",
                        "semantic_types": ("definition",),
                        "required_occurrence_ids": required,
                    },
                    populations=(population("selected-retained-occurrences", "occurrence:one"),),
                ),
            )
            assert result.status == status
            if status == "ready":
                from corpus_structure.methods.contextual_candidates import ContextualCandidates
                method = ContextualCandidates()
                records = {row["id"]: row for values in groups.values() for row in values}
                inputs = hydrated_component_selection(method, result, records)
                view, occurrences = method.select_hydrated(inputs)
                assert view.member.subject == "view"
                assert [row.value()["occurrence_id"] for row in occurrences] == ["one"]


def test_structural_consumer_keeps_two_original_sources_and_reading_associations(consumer_model):
    references = [
        ExternalSourceRef(
            project_id="project",
            run_id=1,
            cut_id=2,
            release_id="release",
            result_revision=0,
            source_view_id=index,
            native_task_id=index,
            native_product_key="native:" + str(index),
            native_content_digest="a" * 64,
            projection_digest="b" * 64,
            recipe_digest="c" * 64,
            coordinate_version=3,
        )
        for index in (1, 2)
    ]
    passages, readings, entries = [], [], []
    for side, source in zip(("left", "right"), references, strict=True):
        actual_source = "original:" + side
        passage: dict[str, Any] = dict(
            id="passage:" + side,
            subject="passage:" + side,
            source=actual_source,
            input_subject="input",
            passage_id=side,
            source_ref=source.identity,
            start=0,
            end=5,
        )
        reading: dict[str, Any] = dict(
            id="reading:" + side,
            subject="reading:" + side,
            source=actual_source,
            input_subject="input",
            passage_id=side,
            contribution_id="contribution:" + side,
            source_ref=source.identity,
            producer_operation="read",
        )
        passages.append(passage)
        readings.append(reading)
        for row in (passage, reading):
            entries.append(
                SourceSetEntry.from_structural_source(
                    source,
                    original_source=actual_source,
                    subject=row["subject"],
                    analyzed_scope=b"{}",
                    product="product:" + row["id"],
                    member=row["id"],
                )
            )
    populations = tuple(
        population("selected-" + side + "-" + kind, kind + ":" + side)
        for side in ("left", "right")
        for kind in ("passage", "reading")
    )
    parameters = {
        "left_passage_id": "left",
        "right_passage_id": "right",
        "left_reading_id": "contribution:left",
        "right_reading_id": "contribution:right",
    }
    with admitted(
        consumer_model, {"DdoPassageBinding": passages, "DdoReadingBinding": readings}
    ) as (connection, projections):
        result = execute_binding(
            connection,
            compile_binding(
                consumer_model,
                "structure.compare/selection",
                projections,
                subject="input",
                original_source="original:left",
                parameters=parameters,
                populations=populations,
                source_sets=(FrozenSourceSet("structural-input-sources", tuple(entries)),),
            ),
        )
        assert result.status == "ready"
        from corpus_structure.methods.structural_products import StructuralComparisonMethod
        method = StructuralComparisonMethod()
        records = {row["id"]: row for row in (*passages, *readings)}
        inputs = hydrated_component_selection(method, result, records)
        left, right = method.select_hydrated(inputs)
        assert (left[0].value()["passage_id"], right[0].value()["passage_id"]) == ("left", "right")
        assert {member.original_source for role in result.roles for member in role.members} == {
            "original:left",
            "original:right",
        }
        assert {member.subject for role in result.roles for member in role.members} == {
            "passage:left",
            "passage:right",
            "reading:left",
            "reading:right",
        }
