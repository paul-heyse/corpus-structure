"""Independent source/attachment expectations for retained definition location."""

from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.methods.contextual_candidates import retained_occurrences
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.definition_location_products import (
    definition_location_inputs,
    definition_location_values,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_products import FrozenNativeSource
from corpus_structure.semantic.structural_products import (
    DeclaredDefinitionComponentsProduct,
    DeclaredDefinitionComponentsReport,
    DeclaredStructuralInput,
    DeclaredStructuralInputPin,
    DefinitionRoleCandidate,
    StructuralPassage,
    declared_definition_component,
)


@pytest.fixture(scope="module")
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        definition_location_inputs(
            SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
        )
    )


def population(prepared):
    text = "term def other"
    source = FrozenNativeSource.from_projection(
        prepared,
        document="original:doc",
        section_pointer="#/groups/0",
        membership="descendants",
        text=text,
        pieces=[
            dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=14)
        ],
        items=[dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[])],
    )
    member = BoundRoleMember(
        "product:source",
        "kind:source",
        "subject:section",
        "original:doc",
        b'{"scope":"selected"}',
        b"{}",
        (),
        b"{}",
        member="member:section",
        subject_definition="original-source-view",
        support_references=(),
    )
    frame = DeclaredNativeFrameSource.acquire(
        prepared, source.value, member, project="outside-statistics"
    )
    source_ref = DeclaredStructuralSource(**frame.pin.values())
    passage = StructuralPassage(
        passage_id="definition",
        source_ref=source_ref.identity,
        start=0,
        end=14,
        text=text,
        scope="selected",
    )
    component = declared_definition_component(
        term=dict(passage_id="definition", start=0, end=4, text="term"),
        content=dict(passage_id="definition", start=5, end=8, text="def"),
        interpretation="unresolved",
        basis="unqualified",
        scope="selected",
        evidence=("definition",),
        reason="Retained unresolved candidate.",
    )
    report = DeclaredDefinitionComponentsReport(
        inputs=DeclaredStructuralInput(
            question="Retain the selected definition.",
            scope="selected",
            inventory_id="inventory",
            policy_id="policy",
            sources=(source_ref,),
            passages=(passage,),
            dependencies=("native:upstream",),
        ),
        definition_components=DeclaredDefinitionComponentsProduct(
            components=(component,),
            stages=(),
            role_candidates=(
                DefinitionRoleCandidate(
                    role="content",
                    span=component.content,
                    window_start=0,
                    window_end=14,
                    envelope="native:actual-model-reply",
                    index=2,
                ),
            ),
        ),
        sources_input=(
            DeclaredStructuralInputPin.from_bound(member, project="outside-statistics"),
        ),
    )
    reference = dict(
        product_id="native:component-report",
        kind_contract="kind:components",
        project_id="outside-statistics",
        subject=member.subject,
        original_source=member.original_source,
        analyzed_scope_meaning=source_ref.analyzed_scope_meaning,
    )
    return frame, report, component, reference


def test_declared_definition_location_keeps_exact_native_occurrence_and_attachment(prepared):
    frame, report, component, reference = population(prepared)
    products, operations, coordinates = definition_location_values(
        frame, report, reference, {"component_ids": [component.component_id], "roles": []}
    )
    (product,) = products
    (anchor,) = product["anchors"]
    assert (anchor["pointer"], anchor["start"], anchor["end"], anchor["source_piece"]) == (
        "#/texts/0",
        0,
        4,
        "term",
    )
    assert anchor["pin"]["source_product"] == "product:source"
    assert anchor["pin"]["source_member"] == "member:section"
    assert "task_id" not in anchor["pin"] and "source_view_id" not in anchor["pin"]
    meaning = source_python(product["value"])
    assert meaning["component_reference"]["product_id"] == reference["product_id"]
    assert meaning["component_reference"]["component_id"] == component.component_id
    assert meaning["attachment"]["term"]["text"] == "term"
    assert meaning["attachment"]["content"]["text"] == "def"
    assert product["kind"] == "occurrence" and product["standing"] == "retained_private"
    assert operations[0]["inspected_count"] == operations[0]["emitted_count"] == 1
    assert coordinates[0]["text"] == "term def other"
    prepared.validate_python(
        "DdoCandidateSourceContribution", {**product, "candidate_type": "contribution"}
    )
    # The actual immediate contextual projection accepts these original native
    # anchors; no definition recognizer or task-shaped carrier is involved.
    nodes = {"#/texts/0": {"text": frame.text}}
    contextual, contexts, _ = retained_occurrences(
        {"contributions": products},
        nodes,
        frame.pin.values(),
        "contextual-operation",
        required_occurrence_ids=(product["occurrence_id"],),
    )
    assert len(contextual) == 1
    assert contexts[product["occurrence_id"]] == (frame.text, 0, 4, "term")


def test_independent_content_role_stays_proposal_and_changed_attachment_stays_distinct(prepared):
    frame, report, component, reference = population(prepared)
    roles, _, _ = definition_location_values(
        frame,
        report,
        reference,
        {
            "component_ids": [],
            "roles": [{"role": "content", "envelope": "native:actual-model-reply", "index": 2}],
        },
    )
    assert (
        roles[0]["kind"] == "proposal" and roles[0]["semantic_type"] == "definition.defining_text"
    )
    meaning = source_python(roles[0]["value"])
    assert meaning["role_reference"]["index"] == 2 and "component_reference" not in meaning
    assert roles[0]["anchors"][0]["source_piece"] == "def"
    first, _, _ = definition_location_values(
        frame, report, reference, {"component_ids": [component.component_id], "roles": []}
    )
    changed = declared_definition_component(
        **{
            **component.model_dump(exclude={"component_id"}),
            "content": dict(passage_id="definition", start=9, end=14, text="other"),
        }
    )
    other = report.model_copy(
        update={
            "definition_components": report.definition_components.model_copy(
                update={"components": (changed,)}
            )
        }
    )
    second, _, _ = definition_location_values(
        frame,
        other,
        {**reference, "product_id": "native:changed-component-report"},
        {"component_ids": [changed.component_id], "roles": []},
    )
    assert first[0]["occurrence_id"] == second[0]["occurrence_id"]
    assert first[0]["contribution_id"] != second[0]["contribution_id"]
    assert source_python(second[0]["value"])["attachment"]["content"]["text"] == "other"


@pytest.mark.parametrize(
    "change", ["foreign-source", "wrong-span", "unknown-component", "duplicate", "mixed"]
)
def test_declared_definition_location_refuses_unbound_source_span_or_selection(prepared, change):
    frame, report, component, reference = population(prepared)
    selection: dict = {"component_ids": [component.component_id], "roles": []}
    if change == "foreign-source":
        pin = frame.pin.values()
        pin["source_product"] = "native:another-source"
        pin["source"] = '["native:another-source","member:section"]'
        from corpus_structure.semantic.identity import canonical_bytes

        frame = replace(frame, pin_content=canonical_bytes(pin).decode())
    elif change == "wrong-span":
        body = report.model_dump(mode="json")
        body["inputs"]["passages"][0]["text"] = "torm def other"
        report = body
    elif change == "unknown-component":
        selection["component_ids"] = ["0" * 64]
    elif change == "duplicate":
        selection["component_ids"] *= 2
    else:
        selection["roles"] = [
            {"role": "content", "envelope": "native:actual-model-reply", "index": 2}
        ]
    with pytest.raises(ValueError):
        definition_location_values(frame, report, reference, selection)
