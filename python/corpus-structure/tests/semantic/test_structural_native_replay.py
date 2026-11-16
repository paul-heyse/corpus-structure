"""Current structural kernels and genuine native consumer criteria.

The fixed formal/grouping controls are unadmitted domain values, not native
publication or provider evidence. Actual native comparisons consume genuine
source/primary/predicate products; no lexical-only RPC or run snapshot is used.
"""

import pytest

from corpus_structure.semantic.identity import canonical_bytes
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import selected

_COMPARISON_LITERALS = (
    ("Date: 2024-02-29", {"kind": "date", "value": "2024-02-29"}),
    ("Date: 2026-02-29", None),
    ("Identifier: Rule.R3", {"kind": "identifier", "value": "Rule.R3"}),
    ("Quantity: +2.50e1 kg", {"kind": "quantity", "value": "25", "unit": "kg"}),
    (
        "Range: [1, 2) kg",
        dict(kind="range", lower="1", upper="2", lower_closed=True, upper_closed=False, unit="kg"),
    ),
    (
        "Range: (1, 2] kg",
        dict(kind="range", lower="1", upper="2", lower_closed=False, upper_closed=True, unit="kg"),
    ),
    ("Range: (1, 1] kg", None),
    ("Report dated 2024-02-29", None),
    ("Quantity: 1e1000 kg", None),
    ("Quantity: 1e1000000 kg", None),
    ("Quantity: 1e100 kg", dict(kind="quantity", value="1" + "0" * 100, unit="kg")),
    ("Quantity: 1e101 kg", None),
    ("Quantity: 1e-100 kg", dict(kind="quantity", value="0." + "0" * 99 + "1", unit="kg")),
    ("Quantity: 1e-101 kg", None),
    ("Quantity: 1e-1000000 kg", None),
    ("Quantity: -0e1000 kg", dict(kind="quantity", value="0", unit="kg")),
    (
        "Range: [1e-100, 1e100] kg",
        dict(
            kind="range",
            lower="0." + "0" * 99 + "1",
            upper="1" + "0" * 100,
            lower_closed=True,
            upper_closed=True,
            unit="kg",
        ),
    ),
    ("Range: [1e-101, 1] kg", None),
    ("Range: [0, 1e101] kg", None),
    ("Identifier: " + "A" * 244, dict(kind="identifier", value="A" * 244)),
    ("Identifier: " + "A" * 245, None),
)


def _formal_case(profile, text):
    from corpus_structure.semantic.data_operation_model import SubjectContext, json_context_meaning
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.formal_products import FormalEvidenceOptions
    from corpus_structure.semantic.formal_readings import FormalSourceReadings
    from corpus_structure.semantic.source_products import source_subject

    native = selected(profile, text)
    coordinate = native.value["source"]
    scope = canonical_bytes({"source": coordinate, "selectors": native.value["selectors"]})
    context = SubjectContext(
        "unadmitted:project",
        source_subject(coordinate),
        coordinate["document"],
        scope,
        subject_definition="original-source-view",
    )
    assert context.original_source is not None
    product = profile.run(native, FormalEvidenceOptions(), subject_context=context)
    address = DeclaredStructuralSource(
        source='["unadmitted:source",null]',
        source_product="unadmitted:source",
        kind_contract="unadmitted:source-kind",
        project_id=context.project_id,
        subject=context.subject,
        subject_definition=context.subject_definition,
        original_source=context.original_source,
        analyzed_scope_meaning=json_context_meaning(scope).decode(),
        document=coordinate["document"],
        projection_digest=coordinate["projection"],
        section_pointer=coordinate["section_pointer"],
        membership=coordinate["membership"],
    )
    return native, address, product, FormalSourceReadings.from_products((product,), native)


@pytest.mark.parametrize("spelling,expected", _COMPARISON_LITERALS)
def test_current_comparison_literal_has_independent_bounded_meaning(profile, spelling, expected):
    from corpus_structure.methods.structural_products import _literal_reading
    from corpus_structure.semantic.structural_products import (
        DeclaredPrimaryReference,
        LocatedDefinitionSpan,
    )

    _, source, product, primary = _formal_case(profile, spelling)
    span = LocatedDefinitionSpan(passage_id="literal", start=0, end=len(spelling), text=spelling)
    literal, reference = _literal_reading(span, source, primary)
    assert (literal.model_dump(mode="json", exclude_none=True) if literal else None) == expected
    if expected is not None:
        assert isinstance(reference, DeclaredPrimaryReference)
        assert reference.product_id == product.semantic_id
        assert reference.member_id in {member.member_id for member in product.members}


@pytest.mark.parametrize(
    "connector,grouping",
    [("and", "conjunction"), ("or", "disjunction"), ("as well as", "unresolved")],
)
def test_current_retained_clause_keeps_repeated_exact_occurrences_and_empty_exception(
    profile, connector, grouping
):
    from corpus_structure.methods.structural_products import read_retained_clause
    from corpus_structure.semantic.declared_structural_references import DeclaredContributionRef
    from corpus_structure.semantic.structural_products import StructuralPassage

    text = f"Clerk must file Form {connector} Form. No exceptions."
    _, source, formal, primary = _formal_case(profile, text)
    passage = StructuralPassage(
        passage_id="left",
        source_ref=source.identity,
        start=0,
        end=len(text),
        text=text,
        scope="selected",
    )
    reference = DeclaredContributionRef(
        product_id="unadmitted:predicate-report",
        member_id=None,
        kind_contract="unadmitted:predicate-kind",
        contribution_id="source-contribution:" + "a" * 64,
        **source.model_dump(
            include={
                "project_id",
                "subject",
                "subject_definition",
                "original_source",
                "analyzed_scope_meaning",
            }
        ),
    )

    def extent(word, start=0):
        at = text.index(word, start)
        return dict(start=at, end=at + len(word))

    first = extent("Form")
    second = extent("Form", first["end"])
    pin = source.model_dump(mode="json", exclude_none=True)
    rows = [
        dict(
            contribution_id=reference.contribution_id,
            pin=pin,
            component=dict(kind="predicate_reading", frame="frame", scope="selected"),
        ),
        dict(
            contribution_id="frame",
            pin=pin,
            component=dict(
                kind="predicate_frame",
                scope="selected",
                frame_members=[
                    dict(
                        role=role,
                        contribution=role + str(index),
                        outcome="complete",
                        extents=[location],
                    )
                    for index, (role, location) in enumerate(
                        (
                            ("actor", extent("Clerk")),
                            ("predicate", extent("file")),
                            ("object", first),
                            ("object", second),
                        )
                    )
                ],
            ),
        ),
        dict(
            contribution_id="exception",
            component=dict(
                kind="predicate_qualifier",
                host_contribution_id="frame",
                qualifier_contribution_id="exception-cue",
                qualifier_kind="exception",
            ),
        ),
        dict(
            contribution_id="exception-cue",
            pin=pin,
            component=dict(extents=[extent("No exceptions.")]),
        ),
    ]
    reading = read_retained_clause(
        passage, source, reference, {"contributions": rows}, primary_layers=primary
    )
    groups = reading.groups
    assert groups is not None
    group = groups["object"]
    assert group.grouping == grouping
    assert [member.lexical_value for member in group.members] == ["Form", "Form"]
    positions = []
    for member in group.members:
        assert member.spans is not None
        positions.append(member.spans[0].start)
    assert positions == [first["start"], second["start"]]
    assert groups["exception"].state == "empty"
    (witness,) = groups["exception"].witnesses
    assert (witness.start, witness.end, witness.text) == (
        text.index("No exceptions"),
        text.index("No exceptions") + 13,
        "No exceptions",
    )
    from corpus_structure.semantic.structural_products import DeclaredPrimaryReference

    reference = groups["exception"].primary_witnesses[0]
    assert isinstance(reference, DeclaredPrimaryReference)
    assert reference.product_id == formal.semantic_id
    assert groups["condition"].state == "absent"


@pytest.mark.parametrize("prefix", ["", "Do not apply the following statement. "])
def test_current_navigation_uses_the_whole_original_note(profile, prefix):
    from corpus_structure.semantic.constructions.layers import ConstructionLayer, ConstructionSource
    from corpus_structure.semantic.constructions.navigation import (
        FAMILY,
        populate_navigation_products,
    )

    text = prefix + "Only the Heads row uses percentages."
    native, _, _, _ = _formal_case(profile, text)
    layer = ConstructionLayer(
        native.value["source"],
        {"selectors": native.value["selectors"]},
        {"key": "text.constructions/source-native"},
        families=(FAMILY,),
    )
    populate_navigation_products(layer, ConstructionSource.from_native(native), native, None)
    notes = [
        row
        for row in layer.facts()["annotations"]
        if row.get("navigation", {}).get("kind") == "note_scope"
    ]
    assert len(notes) == (0 if prefix else 1)


def test_current_dossier_page_excludes_unselected_member_source_closure():
    from corpus_structure.methods.structural_products import produce_structural_dossier
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.structural_products import StructuralPassage
    from corpus_structure.serve.structural_products import dossier_member_page
    from semantic.test_dossier_products import _predecessor

    component, root, predecessor, report, inputs = _predecessor()
    other = DeclaredStructuralSource.model_validate(
        {
            **inputs.sources[0].model_dump(),
            "source": '["source:unrelated","member:unrelated"]',
            "source_product": "source:unrelated",
            "source_member": "member:unrelated",
            "document": "document:unrelated",
            "original_source": "document:unrelated",
            "subject": "subject:unrelated",
        }
    )
    unused = StructuralPassage(
        passage_id="unrelated",
        source_ref=other.identity,
        start=0,
        end=14,
        text="uncited source",
        scope="unrelated",
    )
    inputs = inputs.model_copy(
        update={"sources": (*inputs.sources, other), "passages": (*inputs.passages, unused)}
    )
    dossier = produce_structural_dossier(
        inputs,
        root_component=root,
        root=component,
        retained=((predecessor, {"report": report}),),
        relationships={},
    )
    assert dossier.dossier is not None
    before = dossier.model_dump(mode="json")
    page = dossier_member_page(dossier, population="membership", offset=1, limit=1)
    assert len(page["members"]) == len(page["citations"]) == 1
    assert page["members"][0]["member_id"] == dossier.dossier.members[1].member_id
    assert page["citations"][0]["source"] == inputs.sources[0].model_dump(mode="json")
    assert b"source:unrelated" not in canonical_bytes(page)
    assert dossier.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "left,right,actor_outcome",
    [
        (
            "Manager must approve Table 5.1 if revenue > 25000 USD.",
            "Manager must approve Table 5.1 if revenue > 50000 USD.",
            "same_lexical_value",
        ),
        (
            "Table 5.1 must be approved by Manager if revenue > 25000 USD.",
            "Table 5.1 must be approved by Analyst if revenue > 25000 USD.",
            "different_lexical_value",
        ),
    ],
    ids=("threshold", "passive-actor"),
)
def test_current_native_comparison_consumes_actual_predicate_and_formal_source_products(
    current_pdf_source_factory, tmp_path, left, right, actor_outcome
):
    from corpus_structure.semantic.data_operation_service import DemandOperationSelection
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from semantic.current_pdf_source_support import admit_current_target
    from semantic.structural_admission_native_support import COMPARE, execute, request
    from semantic.structural_admission_native_support import selected as selected_products
    from semantic.structural_production_native_support import (
        PREDICATES,
        produce_source_reports,
        recipe,
        selected_for_source,
    )

    literals = (left, right)
    with current_pdf_source_factory(
        tuple(("text", value, value, None) for value in literals)
    ) as source:
        kernel = admit_current_target(source, recipe(tmp_path / "recipe"), tmp_path / "consumer")
        _, _, products, _ = produce_source_reports(source, kernel, PREDICATES, text=left)
        source_kind = kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
            "kind",
        ]
        originals = tuple(
            next(
                value
                for value in products
                if value.row["kind_contract"] == source_kind
                and value.body["source"]["section_pointer"] == f"#/groups/{index}"
                and value.body["source"]["membership"] == "descendants"
            )
            for index in range(2)
        )
        reports, formal, readings = [], [], []
        for original in originals:
            (report,) = selected_for_source(
                kernel,
                products,
                "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
                original,
            )
            reports.append(report)
            formal.extend(
                selected_for_source(
                    kernel,
                    products,
                    "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                    original,
                )
            )
            rows = {
                packet["body"]["contribution_id"]: packet["body"]
                for packet in report.body["members"]
            }
            matching = []
            for row in rows.values():
                component = row.get("component", {})
                if component.get("kind") != "predicate_reading":
                    continue
                frame = rows[component["frame"]]["component"]
                if any(
                    member["role"] == "predicate"
                    and any(
                        original.body["text"][extent["start"] : extent["end"]]
                        in {"approve", "approved"}
                        for extent in member["extents"]
                    )
                    for member in frame["frame_members"]
                ):
                    matching.append(row["contribution_id"])
            assert len(matching) == 1
            readings.append(matching[0])
        parameters = dict(
            question="Compare genuine selected predicate roles.",
            scope="selected",
            inventory_id="current-native-comparison",
            policy_id="exact-private-predicate-comparison-1",
            left_passage_id="left",
            right_passage_id="right",
            left_start=0,
            left_end=len(left),
            right_start=0,
            right_end=len(right),
            left_reading=readings[0],
            right_reading=readings[1],
            left_source_reference=canonical_bytes(
                [originals[0].row["product_id"], originals[0].row["member_id"]]
            ).decode(),
            right_source_reference=canonical_bytes(
                [originals[1].row["product_id"], originals[1].row["member_id"]]
            ).decode(),
            left_report_reference=canonical_bytes([reports[0].row["product_id"], None]).decode(),
            right_report_reference=canonical_bytes([reports[1].row["product_id"], None]).decode(),
        )
        demand, execution = execute(
            kernel,
            request(
                kernel,
                (COMPARE,),
                originals[0].context,
                selections=(DemandOperationSelection(operation=COMPARE, parameters=parameters),),
                source_sets=(
                    FrozenSourceSet(
                        "structural-sources", tuple(value.entry() for value in originals)
                    ),
                    FrozenSourceSet(
                        "structural-reports", tuple(value.entry() for value in reports)
                    ),
                    FrozenSourceSet("structural-formal", tuple(value.entry() for value in formal)),
                ),
                inference="current-real-source-comparison:" + actor_outcome,
            ),
        )
        assert execution.receipt_count == 1
        (product,) = selected_products(
            kernel, demand["demand_id"], kind="urn:corpus:structural:DeclaredComparisonReport"
        )
        comparison = product.body["comparison"]
        assert len(comparison["dimensions"]) == 10
        assert comparison["dimensions"][0]["outcome"] == actor_outcome
        assert comparison["equivalence"] == comparison["identity_standing"] == "not_asserted"
        if actor_outcome == "same_lexical_value":
            threshold = comparison["dimensions"][5]
            assert threshold["left_group"]["members"][0]["typed"]["value"] == "25000"
            assert threshold["right_group"]["members"][0]["typed"]["value"] == "50000"
            assert threshold["typed_outcome"] == "unknown"
        assert [comparison[key]["product_id"] for key in ("left_reading", "right_reading")] == [
            value.row["product_id"] for value in reports
        ]
        assert [value["product_id"] for value in product.body["sources_input"]] == [
            value.row["product_id"] for value in originals
        ]
