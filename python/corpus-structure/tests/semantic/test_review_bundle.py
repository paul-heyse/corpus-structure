"""Detached review integrity and publication, independently specified records."""

import json

import pytest

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    inspect_review_bundle,
    verify_review_bundle,
    write_review_bundle,
)


def selection(**values):
    return ReviewSelection(
        selections=(ContributionRequest(run_id=1),), completeness="inventory", **values
    )


def test_round_trip_equivalent_serializations_and_preserved_values(tmp_path):
    rows = (
        (
            "contributions",
            {
                "value": "3.00",
                "score": None,
                "direction": "reverse",
                "qualifiers": ["not necessarily"],
                "index": i,
            },
        )
        for i in range(300)
    )
    manifest = write_review_bundle(selection(), tmp_path / "review", rows)
    assert manifest["relations"]["contributions"]["rows"] == 300
    assert verify_review_bundle(tmp_path / "review") == manifest
    summary = inspect_review_bundle(tmp_path / "review")
    assert summary["relations"] == {"contributions": 300}
    first = json.loads((tmp_path / "review" / "contributions.jsonl").read_text().splitlines()[0])
    assert json.loads(first["payload_json"]) == {
        "value": "3.00",
        "score": None,
        "direction": "reverse",
        "qualifiers": ["not necessarily"],
        "index": 0,
    }
    assert manifest["original_source_completeness"] == "not_established"


@pytest.mark.parametrize("member", ["contributions.jsonl", "contributions.parquet", "README.md"])
def test_tampering_is_detected(tmp_path, member):
    root = tmp_path / "review"
    write_review_bundle(selection(), root, iter([("contributions", {"id": "a"})]))
    with (root / member).open("ab") as sink:
        sink.write(b"tampered")
    with pytest.raises(ValueError, match="differs"):
        verify_review_bundle(root)


def test_missing_member_and_undeclared_extra_are_detected(tmp_path):
    root = tmp_path / "review"
    write_review_bundle(selection(), root, iter([("source", {"text": "known"})]))
    (root / "unlisted.json").write_text("{}")
    with pytest.raises(ValueError, match="undeclared"):
        verify_review_bundle(root)
    (root / "unlisted.json").unlink()
    (root / "source.parquet").unlink()
    with pytest.raises(ValueError, match="missing"):
        verify_review_bundle(root)


def test_rejects_directory_substituted_for_regular_member(tmp_path):
    root = tmp_path / "review"
    write_review_bundle(selection(), root, [("source", {"text": "known"})])
    member = root / "source.parquet"
    member.unlink()
    member.mkdir()
    with pytest.raises(ValueError, match="ordinary file"):
        verify_review_bundle(root)


def test_existing_empty_destination_and_racing_destination_survive(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        write_review_bundle(selection(), existing, iter([]))
    target = tmp_path / "raced"

    def racing_rows():
        yield "inventory", {"population": "contribution", "row": {"value": 1}}
        target.mkdir()
        (target / "owner").write_text("unrelated")

    with pytest.raises(FileExistsError):
        write_review_bundle(selection(), target, racing_rows())
    assert (target / "owner").read_text() == "unrelated"


def test_cancelled_stream_settles_without_successful_package(tmp_path):
    cancellation = OperationCancellation()
    settled = []

    def rows():
        try:
            yield "inventory", {"index": 0}
            cancellation.request_cancel()
            yield "inventory", {"index": 1}
        finally:
            settled.append(True)

    with pytest.raises(DatabaseOperationCancelled):
        write_review_bundle(selection(), tmp_path / "review", rows(), cancellation=cancellation)
    assert settled == [True]
    assert not (tmp_path / "review").exists()
    assert list(tmp_path.iterdir()) == []


def test_oversized_stream_settles_and_no_destination(tmp_path):
    settled = []

    def rows():
        try:
            yield "inventory", {"payload": "x" * 1000}
        finally:
            settled.append(True)

    with pytest.raises(SemanticRefusal, match="budget"):
        write_review_bundle(selection(max_bytes=50), tmp_path / "review", rows())
    assert settled == [True]
    assert list(tmp_path.iterdir()) == []


def test_aggregate_serialized_bytes_are_bounded(tmp_path):
    with pytest.raises(SemanticRefusal, match="total byte budget"):
        write_review_bundle(
            selection(max_bytes=500), tmp_path / "review", iter([("source", {"a": 1})])
        )
    assert not (tmp_path / "review").exists()


def test_symlink_member_is_rejected(tmp_path):
    root = tmp_path / "review"
    write_review_bundle(selection(), root, iter([("source", {"text": "actual"})]))
    content = (root / "source.jsonl").read_bytes()
    outside = tmp_path / "outside"
    outside.write_bytes(content)
    (root / "source.jsonl").unlink()
    (root / "source.jsonl").symlink_to(outside)
    with pytest.raises(ValueError, match="ordinary file"):
        verify_review_bundle(root)


def test_no_continuation_or_duplicate_selection():
    with pytest.raises(ValueError, match="continuation"):
        ReviewSelection(selections=(ContributionRequest(run_id=1, cursor="cursor"),))
    with pytest.raises(ValueError, match="distinct"):
        ReviewSelection(selections=(ContributionRequest(run_id=1), ContributionRequest(run_id=1)))


def test_invalid_relation_path_is_refused(tmp_path):
    with pytest.raises(ValueError, match="relation name"):
        write_review_bundle(selection(), tmp_path / "review", iter([("../escape", {"a": 1})]))
    assert list(tmp_path.iterdir()) == []


def source_row(text="qq"):
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes

    projection = {
        "text": text,
        "pieces": [{"start": 0, "end": len(text), "item_ref": "#/texts/0"}],
        "items": ["#/texts/0"],
        "ancestors": [],
        "health": {"state": "unknown"},
    }
    return {
        "source_view_id": 1,
        "ref": {
            "id": 1,
            "key": "known",
            "document_id": 1,
            "native_product": {"task_id": 1, "product_key": "native", "content_digest": "a" * 64},
            "section_pointer": "#/texts/0",
            "membership": "direct",
            "projection_digest": sha256(canonical_bytes(projection)).hexdigest(),
            "recipe_digest": "b" * 64,
            "analysis_eligible": True,
        },
        "text": projection["text"],
        "context": {**projection, "items": [{"self_ref": "#/texts/0", "text": text}]},
    }


@pytest.fixture
def synthetic_source_projection(monkeypatch):
    # These controls use hand-written structural scopes and opaque product IDs.
    # The native fold and its mandatory bundle boundary are exercised separately.
    from corpus_structure.serve import review_bundle

    monkeypatch.setattr(review_bundle, "_verify_source_projections", lambda *_: set())


def test_source_projection_and_membership_closure(tmp_path, synthetic_source_projection):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [
        ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
        ("inventory", {"population": "contribution", "row": {"source_view_id": 1}}),
        ("sources", source_row()),
    ]
    write_review_bundle(request, tmp_path / "complete", iter(rows))
    assert inspect_review_bundle(tmp_path / "complete")["relations"]["sources"] == 1
    with pytest.raises(ValueError, match="source members"):
        write_review_bundle(request, tmp_path / "missing", iter(rows[:-1]))
    assert not (tmp_path / "missing").exists()


def test_opaque_raw_diagnostic_identifier_is_not_source_custody(
    tmp_path, synthetic_source_projection
):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [
        ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
        ("inventory", {"population": "report", "row": {"source_view_id": 1, "origin_task_id": 42}}),
        (
            "reports",
            {
                "origin_task_id": 42,
                "unit_type": "source_view",
                "origin_unit_id": 1,
                "body": {"parse_detail": {"raw": {"source_view_id": 999}}},
            },
        ),
        ("sources", source_row()),
    ]
    manifest = write_review_bundle(request, tmp_path / "diagnostic", iter(rows))
    assert verify_review_bundle(tmp_path / "diagnostic") == manifest


def test_assessment_requires_its_actual_producer_run_unit_scope(
    tmp_path, synthetic_source_projection
):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [
        ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
        ("sources", source_row()),
        (
            "assessment_history",
            {"kind": "unit", "value": {"id": 18, "source_view_id": 1, "context": []}},
        ),
        (
            "assessment_history",
            {
                "kind": "evaluation",
                "value": {
                    "id": 26,
                    "run_id": 43,
                    "result": {
                        "protocol": "source-operation-evaluation-1",
                        "units": [{"unit_id": 18, "producer_reports": [{"origin_task_id": 128}]}],
                    },
                },
            },
        ),
    ]
    with pytest.raises(ValueError, match="assessment producer closure missing"):
        write_review_bundle(request, tmp_path / "missing-producer", iter(rows))
    assert not (tmp_path / "missing-producer").exists()
    complete = ReviewSelection(
        selections=(ContributionRequest(run_id=1), ContributionRequest(run_id=43, source_view_id=1))
    )
    rows.append(("selections", {"selection_index": 1, "run_id": 43, "cut_id": 4}))
    rows.append(
        (
            "inventory",
            {
                "selection_index": 1,
                "population": "report",
                "row": {"source_view_id": 1, "origin_task_id": 128},
            },
        )
    )
    with pytest.raises(ValueError, match="report members"):
        write_review_bundle(complete, tmp_path / "missing-raw", iter(rows))
    rows.append(("reports", {"origin_task_id": 128, "body": {}}))
    write_review_bundle(complete, tmp_path / "assessment", iter(rows))
    assert (
        verify_review_bundle(tmp_path / "assessment")["completeness"] == "selected_source_closure"
    )


def test_piece_map_alteration_refuses_publication_even_with_new_file_hashes(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    source = source_row()
    source["context"]["pieces"][0]["end"] = 1
    with pytest.raises(ValueError, match="pieces do not cover"):
        write_review_bundle(
            request,
            tmp_path / "invalid",
            iter(
                [
                    ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
                    ("sources", source),
                ]
            ),
        )
    assert not (tmp_path / "invalid").exists()


def test_complete_scope_requires_bound_snapshot_and_report(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    with pytest.raises(ValueError, match="snapshot members"):
        write_review_bundle(request, tmp_path / "unbound", iter([]))
    with pytest.raises(ValueError, match="report members"):
        write_review_bundle(
            request,
            tmp_path / "missing",
            iter(
                [
                    ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
                    ("inventory", {"population": "report", "row": {"origin_task_id": 99}}),
                ]
            ),
        )


def structural_rows(text="qq"):
    from corpus_structure.semantic.structural_products import (
        DefinitionComponentsProduct,
        ExternalSourceRef,
        StructuralInput,
        StructuralPassage,
        StructuralProductReport,
    )

    source = source_row(text)
    ref = ExternalSourceRef(
        project_id="original",
        run_id=1,
        cut_id=2,
        release_id="release:old",
        result_revision=0,
        source_view_id=1,
        native_task_id=1,
        native_product_key="native",
        native_content_digest="a" * 64,
        projection_digest=source["ref"]["projection_digest"],
        recipe_digest="b" * 64,
        coordinate_version=3,
    )
    inputs = StructuralInput(
        question="scope dossier",
        scope="statistics",
        inventory_id="inventory:1",
        policy_id="policy:1",
        sources=(ref,),
        passages=(
            StructuralPassage(
                passage_id="p1",
                source_ref=ref.identity,
                start=0,
                end=len(text),
                text=text,
                scope="statistics",
            ),
        ),
        dependencies=("source-view:1",),
    )
    report = StructuralProductReport(
        kind="definition_components",
        inputs=inputs,
        definition_components=DefinitionComponentsProduct(components=(), stages=()),
    )
    return [
        (
            "structural_selections",
            {"selection_index": 0, "run_id": 2, "cut_id": 3, "release_id": "release:structural"},
        ),
        (
            "structural_products",
            {
                "selection_index": 0,
                "selected_task_id": 100,
                "origin_task_id": 100,
                "product_id": report.product_id,
                "report": report.model_dump(mode="json"),
            },
        ),
        (
            "reports",
            {"origin_task_id": 100, "body": {"structural_product": report.model_dump(mode="json")}},
        ),
        ("sources", source),
        ("contracts", {"release_id": "release:structural", "definitions": [], "registry_rows": []}),
        ("contracts", {"release_id": "release:old", "definitions": [], "registry_rows": []}),
    ]


def test_structural_only_bundle_retains_original_source_pin_and_passage(
    tmp_path, synthetic_source_projection
):
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2),))
    write_review_bundle(request, tmp_path / "structural", iter(structural_rows()))
    assert inspect_review_bundle(tmp_path / "structural")["relations"]["structural_products"] == 1


def test_full_structural_bundle_requires_its_release_contracts(tmp_path):
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2),))
    rows = [row for row in structural_rows() if row[0] != "contracts"]
    with pytest.raises(ValueError, match="structural release contracts are missing"):
        write_review_bundle(request, tmp_path / "missing-contracts", iter(rows))
    assert not (tmp_path / "missing-contracts").exists()


def test_full_structural_bundle_requires_original_source_release_contracts(tmp_path):
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2),))
    rows = [
        row
        for row in structural_rows()
        if not (row[0] == "contracts" and row[1]["release_id"] == "release:old")
    ]
    with pytest.raises(ValueError, match="structural release contracts are missing"):
        write_review_bundle(request, tmp_path / "missing-source-contracts", iter(rows))
    assert not (tmp_path / "missing-source-contracts").exists()


def test_full_dossier_bundle_refuses_missing_selected_predecessor(tmp_path):
    from corpus_structure.semantic.structural_products import StructuralProductReport
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2, kind="dossier"),))
    rows = structural_rows()
    value = rows[1][1]["report"]
    from corpus_structure.methods.structural_products import select_dossier
    from corpus_structure.semantic.structural_products import DossierMember, LocatedDefinitionSpan

    original = StructuralProductReport.model_validate(value)
    passage = original.inputs.passages[0]
    member = DossierMember(
        member_id="m1",
        passage_id=passage.passage_id,
        citation=LocatedDefinitionSpan(
            passage_id=passage.passage_id, start=passage.start, end=passage.end, text=passage.text
        ),
        role="usage",
        sense="sense:1",
        scope="statistics",
        relation_product_id="structural:missing",
        qualification="proposed",
    )
    changed = select_dossier(original.inputs, root_id="sense:1", members=(member,))
    rows[1][1]["report"] = changed.model_dump(mode="json")
    rows[1][1]["product_id"] = changed.product_id
    with pytest.raises(ValueError, match="dossier predecessor closure missing"):
        write_review_bundle(request, tmp_path / "missing-predecessor", iter(rows))
    assert not (tmp_path / "missing-predecessor").exists()


def test_structural_passage_that_does_not_match_exported_source_is_refused(
    tmp_path, synthetic_source_projection
):
    from corpus_structure.semantic.structural_products import StructuralProductReport
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2),))
    rows = structural_rows()
    report_value = rows[1][1]["report"]
    report_value["inputs"]["passages"][0]["text"] = "xx"
    rows[1][1]["product_id"] = StructuralProductReport.model_validate(report_value).product_id
    with pytest.raises(ValueError, match="passage differs from exported source"):
        write_review_bundle(request, tmp_path / "wrong-text", iter(rows))
    assert not (tmp_path / "wrong-text").exists()


def test_nested_assessment_iterator_settles_when_export_budget_refuses(tmp_path):
    from corpus_structure.serve.review_bundle import _named_rows

    settled = []

    def assessment_rows():
        try:
            yield {"authored": "x" * 1000}
        finally:
            settled.append(True)

    with pytest.raises(SemanticRefusal, match="budget"):
        write_review_bundle(
            selection(max_bytes=100),
            tmp_path / "review",
            _named_rows("assessment_history", assessment_rows()),
        )
    assert settled == [True]
    assert not (tmp_path / "review").exists()


def cross_cut_dossier_rows():
    """Detached/native-contract custody control; not an ordinary cross-project reuse journey."""
    from corpus_structure.methods.structural_products import derive_dossier_members, select_dossier
    from corpus_structure.semantic.structural_admission import (
        structural_claim_id,
        structural_statement,
    )
    from corpus_structure.semantic.structural_products import (
        DefinitionComponentsProduct,
        LocatedDefinitionSpan,
        RetainedComponentRef,
        RetainedStructuralRef,
        StructuralProductReport,
        definition_component,
    )
    from corpus_structure.serve.structural_products import StructuralRequest

    rows = structural_rows("X is a value.")
    inputs = StructuralProductReport.model_validate(rows[1][1]["report"]).inputs
    component = definition_component(
        term=LocatedDefinitionSpan(passage_id="p1", start=0, end=1, text="X"),
        content=LocatedDefinitionSpan(passage_id="p1", start=5, end=12, text="a value"),
        interpretation="definition",
        basis="matched_cue",
        scope="statistics",
        evidence=("p1",),
        reason="Literal is-a definition in the retained source.",
    )
    predecessor = StructuralProductReport(
        kind="definition_components",
        inputs=inputs,
        definition_components=DefinitionComponentsProduct(components=(component,), stages=()),
    )
    reference = RetainedStructuralRef(
        product_id=predecessor.product_id,
        project_id="current-project",
        run_id=11,
        cut_id=21,
        release_id="release:structural",
        result_revision=7,
        selected_task_id=310,
        origin_task_id=300,
        runtime_fingerprint="runtime:original",
    )
    assertion = dict(
        selection_index=0,
        product_id=predecessor.product_id,
        assessment_id="protected-meaning",
        assertion_id="protected-meaning",
        cut_id=21,
        selected_task_id=310,
        origin_task_id=300,
        statement=structural_statement(predecessor, component.component_id),
    )
    assertion["claim_id"] = structural_claim_id(assertion["statement"])
    root = RetainedComponentRef(
        **reference.model_dump(),
        component_id=component.component_id,
        operation_id="structure.definition_components",
        operation_version="5",
        dependencies=predecessor.inputs.dependencies,
    )
    inputs = inputs.model_copy(
        update=dict(dependencies=(*inputs.dependencies, predecessor.product_id))
    )
    members, facets = derive_dossier_members(
        inputs,
        (
            (
                reference,
                dict(report=predecessor.model_dump(mode="json"), public_assertions=[assertion]),
            ),
        ),
        root=component,
    )
    dossier = select_dossier(
        inputs,
        root_id=root.component_id,
        root_component=root,
        members=members,
        supported_facets=facets,
        predecessors=(reference,),
        member_budget=1,
    )
    result = []
    for index, run, cut, revision, selected, origin, origin_run, runtime, report in (
        (0, 11, 21, 7, 310, 300, 10, "runtime:original", predecessor),
        (1, 12, 22, 8, 400, 400, 12, "runtime:dossier", dossier),
    ):
        result.extend(
            [
                (
                    "structural_selections",
                    dict(
                        selection_index=index,
                        project_id="current-project",
                        run_id=run,
                        cut_id=cut,
                        release_id="release:structural",
                        binding=dict(release_id="release:structural", data_revision=revision),
                    ),
                ),
                (
                    "structural_products",
                    dict(
                        selection_index=index,
                        selected_task_id=selected,
                        origin_task_id=origin,
                        origin_run_id=origin_run,
                        origin_project_id="producer-project" if index == 0 else "current-project",
                        runtime_fingerprint=runtime,
                        product_id=report.product_id,
                        report=report.model_dump(mode="json"),
                    ),
                ),
                (
                    "reports",
                    dict(
                        origin_task_id=origin,
                        origin_run_id=origin_run,
                        project_id="producer-project" if index == 0 else "current-project",
                        runtime_fingerprint=runtime,
                        body=dict(
                            release_id="release:structural",
                            method="structure.definition_components"
                            if index == 0
                            else "structure.dossier",
                            operation_version="5" if index == 0 else "2",
                            structural_product=report.model_dump(mode="json"),
                        ),
                    ),
                ),
            ]
        )
    result.extend([("structural_public_assertions", assertion), *rows[3:]])
    selection = ReviewSelection(
        structural_selections=(
            StructuralRequest(run_id=11, include_publication=True),
            StructuralRequest(run_id=12, kind="dossier"),
        )
    )
    return selection, result


def test_cross_cut_dossier_authenticates_declared_reused_predecessor(
    tmp_path, synthetic_source_projection
):
    selection, rows = cross_cut_dossier_rows()
    dossier = next(
        v["report"]["dossier"]
        for name, v in rows
        if name == "structural_products" and v["selection_index"] == 1
    )
    assert {(m["role"], m["citation"]["text"]) for m in dossier["members"]} == {
        ("terminology", "X"),
        ("definition", "a value"),
    }
    assert len(dossier["supported_facets"]) == 2
    assert {m["assessment_id"] for m in dossier["members"]} == {"protected-meaning"}
    assert len(dossier["representation"]["omitted"]) == 1
    manifest = write_review_bundle(selection, tmp_path / "cross-cut", iter(rows))
    assert verify_review_bundle(tmp_path / "cross-cut") == manifest


@pytest.mark.parametrize(
    "corruption",
    [
        "project",
        "run",
        "cut",
        "release",
        "revision",
        "selected_task",
        "origin_task",
        "runtime",
        "producer_run",
        "producer_project",
        "producer_runtime",
        "raw_report",
        "missing_predecessor",
        "same_product_wrong_cut",
        "member_role",
        "borrowed_support",
    ],
)
def test_cross_cut_dossier_refuses_substituted_custody_or_meaning(
    tmp_path, corruption, synthetic_source_projection
):
    from corpus_structure.semantic.structural_products import StructuralProductReport

    selection, rows = cross_cut_dossier_rows()
    scope = next(
        v for name, v in rows if name == "structural_selections" and v["selection_index"] == 0
    )
    product = next(
        v for name, v in rows if name == "structural_products" and v["selection_index"] == 0
    )
    raw = next(v for name, v in rows if name == "reports" and v["origin_task_id"] == 300)
    if corruption == "project":
        scope["project_id"] = "another-project"
    elif corruption == "run":
        scope["run_id"] = 99
        selection = selection.model_copy(
            update=dict(
                structural_selections=(
                    selection.structural_selections[0].model_copy(update=dict(run_id=99)),
                    selection.structural_selections[1],
                )
            )
        )
    elif corruption == "cut":
        scope["cut_id"] = 99
    elif corruption == "release":
        scope["release_id"] = "release:old"
    elif corruption == "revision":
        scope["binding"]["data_revision"] = 99
    elif corruption == "selected_task":
        product["selected_task_id"] = 99
    elif corruption == "origin_task":
        product["origin_task_id"] = 99
    elif corruption == "runtime":
        product["runtime_fingerprint"] = "runtime:other"
    elif corruption == "producer_run":
        raw["origin_run_id"] = 99
    elif corruption == "producer_project":
        raw["project_id"] = "another-project"
    elif corruption == "producer_runtime":
        raw["runtime_fingerprint"] = "runtime:other"
    elif corruption == "raw_report":
        raw["body"]["structural_product"] = rows[1][1]["report"].copy()
        raw["body"]["structural_product"]["inputs"] = {}
    elif corruption == "missing_predecessor":
        rows.remove(("structural_products", product))
    elif corruption == "same_product_wrong_cut":
        product["selection_index"] = 1
    elif corruption == "borrowed_support":
        next(v for name, v in rows if name == "structural_public_assertions")["assessment_id"] = (
            "other-assessment"
        )
    else:
        from corpus_structure.methods.structural_products import select_dossier

        selected = next(
            v for name, v in rows if name == "structural_products" and v["selection_index"] == 1
        )
        original = StructuralProductReport.model_validate(selected["report"])
        assert original.dossier is not None
        members = list(original.dossier.members)
        members[0] = members[0].model_copy(update=dict(role="usage"))
        changed = select_dossier(
            original.inputs,
            root_id=original.dossier.root_id,
            members=members,
            supported_facets=original.dossier.supported_facets,
            predecessors=original.dossier.predecessors,
            member_budget=1,
        )
        selected["report"] = changed.model_dump(mode="json")
        selected["product_id"] = changed.product_id
        next(v for name, v in rows if name == "reports" and v["origin_task_id"] == 400)["body"][
            "structural_product"
        ] = changed.model_dump(mode="json")
    with pytest.raises(ValueError):
        write_review_bundle(selection, tmp_path / corruption, iter(rows))
    assert not (tmp_path / corruption).exists()


@pytest.mark.parametrize("publication_scope", ["selected", "other_cut", "unrelated_extra"])
def test_published_capture_keeps_selected_revision_after_reading_original_sources(
    monkeypatch, publication_scope
):
    """Control-flow regression only: original source context cannot replace selected custody."""
    from types import SimpleNamespace

    from corpus_structure.semantic.structural_products import StructuralProductReport
    from corpus_structure.serve import review_bundle as module
    from corpus_structure.serve.structural_products import StructuralRequest

    _, fixture = cross_cut_dossier_rows()
    predecessor = StructuralProductReport.model_validate(
        next(
            v["report"]
            for name, v in fixture
            if name == "structural_products" and v["selection_index"] == 0
        )
    )
    assertion = next(v for name, v in fixture if name == "structural_public_assertions").copy()
    statement = assertion.pop("statement")
    assertion.pop("assessment_id")
    assertion.pop("selection_index")
    assertion.update(selected_task_id=311, origin_task_id=301)
    if publication_scope == "other_cut":
        assertion["cut_id"] = 99
    assertions = [assertion]
    if publication_scope == "unrelated_extra":
        assertions.append(
            {
                **assertion,
                "assertion_id": "unrelated-protected",
                "cut_id": 99,
                "selected_task_id": 999,
                "origin_task_id": 998,
            }
        )
    selected = SimpleNamespace(
        binding=SimpleNamespace(release_id="release:structural", data_revision=7),
        prepared="selected-prepared",
        completed_cut_id=21,
    )
    source = SimpleNamespace(
        binding=SimpleNamespace(release_id="release:old", data_revision=0),
        prepared="original-source-prepared",
        completed_cut_id=2,
    )
    monkeypatch.setattr(
        module, "bind_completed_result", lambda conn, run: selected if run == 11 else source
    )
    monkeypatch.setattr(module, "_contract_row", lambda _conn, prepared: dict(release_id=prepared))
    page = SimpleNamespace(
        reports=(predecessor, predecessor),
        task_ids=(310, 311),
        public_assertions=tuple(assertions),
        next_after_task_id=None,
        cut_id=21,
        release_id="release:structural",
        model_dump=lambda **kw: dict(run_id=11, cut_id=21, release_id="release:structural"),
    )
    monkeypatch.setattr(module, "read_structural_export_page", lambda *args: page)
    original = predecessor.inputs.sources[0]
    view = SimpleNamespace(
        id=original.source_view_id,
        native_product=SimpleNamespace(
            task_id=original.native_task_id,
            product_key=original.native_product_key,
            content_digest=original.native_content_digest,
        ),
        projection_digest=original.projection_digest,
        recipe_digest=original.recipe_digest,
    )
    monkeypatch.setattr(module, "selected_source_views", lambda *args: (view,))

    def capture_sources(*args, coordinate_versions, **kwargs):
        coordinate_versions[original.source_view_id] = original.coordinate_version
        return iter(())

    monkeypatch.setattr(module, "_capture_sources", capture_sources)
    monkeypatch.setattr(
        module,
        "PublishedReadBudget",
        lambda *args: SimpleNamespace(preflight=lambda *args: None, value=lambda *args: None),
    )
    captured = []

    class Reader:
        def __init__(self, conn, run, prepared, **kwargs):
            self.prepared = prepared

        def retained_structural_report(self, reference):
            assert self.prepared == "selected-prepared"
            assert reference.result_revision == 7
            assert (reference.selected_task_id, reference.origin_task_id) == (311, 301)
            captured.append(reference)
            return dict(
                report=predecessor.model_dump(mode="json"),
                public_assertions=[
                    dict(assessment_id=assertion["assertion_id"], statement=statement)
                ],
            )

    monkeypatch.setattr("corpus_structure.semantic.operations.BoundReader", Reader)

    class Connection:
        def scalar(self, statement):
            return "current-project" if statement.compile().params["id_1"] == 11 else "original"

        def execute(self, statement):
            params = statement.compile().params
            task = params.get("id_1", params.get("task_id_1"))
            origin = task - 10 if task in (310, 311) else task
            values = dict(
                origin_task_id=origin,
                origin_run_id=10,
                origin_project_id="producer-project",
                runtime_fingerprint="runtime:original",
                project_id="producer-project",
                input_hash="input",
                configuration={},
                config_hash="config",
                body=dict(
                    release_id="release:structural",
                    structural_product=predecessor.model_dump(mode="json"),
                ),
            )
            row = {column.key: values[column.key] for column in statement.selected_columns}
            return SimpleNamespace(mappings=lambda: SimpleNamespace(one=lambda: row))

    selection = ReviewSelection(
        structural_selections=(StructuralRequest(run_id=11, include_publication=True),)
    )
    result = list(module.capture_review_relations(Connection(), selection, OperationCancellation()))
    if publication_scope == "other_cut":
        assert captured == []
        witnesses = [v for name, v in result if name == "structural_public_assertions"]
        assert witnesses == [dict(selection_index=0, **assertion)]
        assert "statement" not in witnesses[0] and "assessment_id" not in witnesses[0]
        return
    assert len(captured) == 1
    assert sum(name == "structural_public_assertions" for name, _ in result) == len(assertions)
    witness = next(v for name, v in result if name == "structural_public_assertions")
    assert witness["statement"] == statement
    if publication_scope == "unrelated_extra":
        unrelated = next(
            v
            for name, v in result
            if name == "structural_public_assertions" and v["assertion_id"] == "unrelated-protected"
        )
        assert unrelated == dict(selection_index=0, **assertions[1])
        assert "statement" not in unrelated and "assessment_id" not in unrelated
    assert witness["assessment_id"] == "protected-meaning"


def artifact_nomination_rows(*, relation_kind="artifact_reference_target", distinct_codes=False):
    from copy import deepcopy
    from hashlib import sha256
    from types import SimpleNamespace

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.artifact_identity import (
        ArtifactIdentityConfig,
        ArtifactIdentityMethod,
    )
    from corpus_structure.methods.scoped_relations import SourceWorkBinding, discover_relations
    from corpus_structure.semantic.artifact_identity import ArtifactScoringPolicy
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef
    from corpus_structure.semantic.structural_products import StructuralProductReport
    from corpus_structure.serve.review_bundle import _retained_review_source_view
    from corpus_structure.serve.structural_products import StructuralRequest

    mention = (
        "See Figure 1 (also published as Figure 2 in numbering namespace Chapter2)."
        if distinct_codes
        else "See Figure 1."
    )
    caption = (
        "Figure 2 (numbering namespace: Chapter2) shows a known comparison."
        if distinct_codes
        else "Figure 1 shows a known comparison."
    )
    literal = mention + "\n" + caption
    rows = structural_rows(literal)
    inputs = StructuralProductReport.model_validate(rows[1][1]["report"]).inputs
    source = rows[3][1]
    source["context"]["pieces"] = [
        dict(
            kind="native_text", source_field="text", item_ref="#/texts/0", start=0, end=len(mention)
        ),
        dict(kind="synthetic_separator", start=len(mention), end=len(mention) + 1),
        dict(
            kind="native_text",
            source_field="text",
            item_ref="#/texts/1",
            start=len(mention) + 1,
            end=len(literal),
        ),
    ]
    source["context"]["items"] = [
        dict(self_ref="#/texts/0", label="text", text=mention),
        dict(self_ref="#/texts/1", label="caption", text=caption, parent={"$ref": "#/pictures/0"}),
        dict(self_ref="#/pictures/0", label="picture"),
    ]
    projection = {**source["context"], "items": ["#/texts/0", "#/texts/1", "#/pictures/0"]}
    digest = sha256(canonical_bytes(projection)).hexdigest()
    source["ref"]["projection_digest"] = digest
    source_ref = inputs.sources[0].model_copy(update=dict(projection_digest=digest))
    references = ()
    endpoints = []
    reference_row = relation = None
    if not distinct_codes:
        frame = native_source_frame(_retained_review_source_view(source), ())
        contributed = discover_relations(frame, source_work="controlled-work")["contributions"]
        relation = next(
            row for row in contributed if row["item_key"].startswith("artifact_reference_target:")
        )
        endpoint_ids = {e["contribution_id"] for e in relation["endpoints"]}
        endpoints = [row for row in contributed if row["contribution_id"] in endpoint_ids]
        reference_row = relation
        if relation_kind != "artifact_reference_target":
            relation = {**relation, "value": source_value({"relation": relation_kind})}
        references = (
            RetainedContributionRef(
                contribution_id=reference_row["contribution_id"],
                project_id="selected-project",
                run_id=5,
                cut_id=6,
                release_id="release:structural",
                result_revision=2,
                selected_task_id=75,
                origin_task_id=70,
                runtime_fingerprint="runtime:source",
            ),
        )
    # Two overlapping selected views share physical coordinates. The retained relation
    # originates in a third view and its own completed cut.
    selected_rows = {}
    selected_refs = []
    passages = []
    for view_id in (2, 3):
        selected = deepcopy(source)
        selected["source_view_id"] = selected["ref"]["id"] = view_id
        if distinct_codes:
            piece = selected["context"]["pieces"][0 if view_id == 2 else 2]
            raw = mention if view_id == 2 else caption
            piece.update(start=0, end=len(raw))
            selected["text"] = selected["context"]["text"] = raw
            selected["context"]["pieces"] = [piece]
            selected_projection = {
                **selected["context"],
                "items": [item["self_ref"] for item in selected["context"]["items"]],
            }
            selected["ref"]["projection_digest"] = sha256(
                canonical_bytes(selected_projection)
            ).hexdigest()
        selected_ref = source_ref.model_copy(
            update={
                "source_view_id": view_id,
                "projection_digest": selected["ref"]["projection_digest"],
            }
        )
        selected_refs.append(selected_ref)
        selected_rows[selected_ref.identity] = selected
        passages.append(
            inputs.passages[0].model_copy(
                update={
                    "passage_id": f"p{view_id}",
                    "source_ref": selected_ref.identity,
                    "text": selected["text"],
                    "end": len(selected["text"]),
                }
            )
        )
    inputs = inputs.model_copy(
        update=dict(
            sources=tuple(selected_refs),
            passages=tuple(passages),
            dependencies=(*inputs.dependencies, *(ref.contribution_id for ref in references)),
        )
    )
    configuration = ArtifactIdentityConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        work_bindings=(
            SourceWorkBinding(
                native_content_digest="a" * 64,
                source_work="controlled-work",
                provenance="controlled native fixture",
            ),
        ),
        policy=ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05),
        external_nomination_refs=references,
    )

    def retained_source(_):
        assert reference_row is not None
        return {
            "contributions": [*endpoints, reference_row],
            "sources": [dict(source_view_id=1, pin=reference_row["pin"], projection=projection)],
        }

    context = SimpleNamespace(
        check_active=lambda: None,
        reader=SimpleNamespace(
            structural_source_frame=lambda _inputs, ref: native_source_frame(
                _retained_review_source_view(selected_rows[ref]), ()
            ),
            retained_source_contribution=retained_source,
        ),
    )
    (result,) = ArtifactIdentityMethod().run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key=inputs.identity)),),
        configuration,
        context,
    )
    report = StructuralProductReport.model_validate(result.structural_product)
    structural = dict(
        selection_index=0,
        selected_task_id=100,
        origin_task_id=100,
        origin_run_id=2,
        origin_project_id="selected-project",
        runtime_fingerprint="runtime:artifact",
        product_id=report.product_id,
        report=report.model_dump(mode="json"),
    )
    raw = dict(
        origin_task_id=100,
        origin_run_id=2,
        project_id="selected-project",
        runtime_fingerprint="runtime:artifact",
        configuration=configuration.model_dump(mode="json"),
        body=dict(
            release_id="release:structural",
            method="structure.artifact_identity",
            operation_version=ArtifactIdentityMethod.version,
            structural_product=report.model_dump(mode="json"),
        ),
    )
    if distinct_codes:
        return ReviewSelection(
            structural_selections=(StructuralRequest(run_id=2, kind="artifact_identity"),)
        ), [
            rows[0],
            ("structural_products", structural),
            ("reports", raw),
            *(("sources", selected) for selected in selected_rows.values()),
            *rows[4:],
        ]

    assert relation is not None
    member_rows = [*endpoints, relation]
    scoped = dict(
        origin_task_id=70,
        origin_run_id=4,
        project_id="source-project",
        runtime_fingerprint="runtime:source",
        unit_type="source_view",
        origin_unit_id=1,
        body=dict(release_id="release:structural", contributions=member_rows),
    )
    captures = [
        (
            "selections",
            dict(
                selection_index=0,
                run_id=5,
                cut_id=6,
                project_id="selected-project",
                binding=dict(release_id="release:structural", data_revision=2),
            ),
        ),
        *(
            (
                "inventory",
                dict(
                    selection_index=0,
                    population="contribution",
                    row=dict(
                        selected_task_id=75,
                        origin_task_id=70,
                        origin_project_id="source-project",
                        origin_run_id=4,
                        runtime_fingerprint="runtime:source",
                        source_view_id=1,
                        contribution_id=row["contribution_id"],
                    ),
                ),
            )
            for row in member_rows
        ),
        ("reports", scoped),
        rows[0],
        ("structural_products", structural),
        ("reports", raw),
        *(("sources", selected) for selected in selected_rows.values()),
        *rows[3:],
    ]
    return ReviewSelection(
        selections=(ContributionRequest(run_id=5),),
        structural_selections=(StructuralRequest(run_id=2, kind="artifact_identity"),),
    ), captures


def test_artifact_nomination_replays_exact_retained_cross_cut_source(
    tmp_path, synthetic_source_projection
):
    request, rows = artifact_nomination_rows()
    root = tmp_path / "artifact"
    write_review_bundle(request, root, iter(rows))
    assert inspect_review_bundle(root)["relations"]["inventory"] == 3
    report = next(row["report"] for name, row in rows if name == "structural_products")
    product = report["artifact_identity"]
    assert len(product["records"]) == 2
    assert [len(r["citations"]) for r in product["records"]] == [2, 2]
    nomination = product["external_nominations"][0]
    assert nomination["origin_cue"]["text"] == "See"
    assert [e["origin_source_view_id"] for e in nomination["endpoints"]] == [1, 1]
    assert [e["role"] for e in nomination["endpoints"]] == ["attachment", "target"]


def test_artifact_nomination_adds_a_different_code_pair_without_a_score(
    tmp_path, synthetic_source_projection
):
    request, rows = artifact_nomination_rows(distinct_codes=True)
    root = tmp_path / "artifact-distinct-codes"
    write_review_bundle(request, root, iter(rows))
    assert inspect_review_bundle(root)["relations"]["sources"] == 2
    report = next(row["report"] for name, row in rows if name == "structural_products")
    product = report["artifact_identity"]
    (reference,) = product["explicit_references"]
    assert reference["outcome"] == "witnessed_candidate"
    (target,) = reference["targets"]
    records = {r["contribution_id"]: r for r in product["records"]}
    attachment = records[reference["attachment"]]
    assert attachment["artifact"]["controlled_code"] == "1"
    assert records[target]["artifact"]["controlled_code"] == "2"
    assert attachment["explicit_reference"]["cue"]["text"] == (
        "See Figure 1 (also published as Figure 2 in numbering namespace Chapter2)"
    )
    assert attachment["citations"][0]["source_ref"] != records[target]["citations"][0]["source_ref"]
    (pair,) = [p for p in product["pairs"] if "explicit_reference" in p["candidate_routes"]]
    assert pair["candidate_routes"] == ["explicit_reference"]
    assert pair["score_status"] == "reference_only"
    assert pair["model_probability"] is None


@pytest.mark.parametrize("broken", ["selected_endpoint", "other_relation", "omitted_ref"])
def test_artifact_nomination_refuses_incomplete_or_substituted_source_closure(tmp_path, broken):
    request, rows = artifact_nomination_rows(
        relation_kind="uses_artifact" if broken == "other_relation" else "artifact_reference_target"
    )
    if broken == "selected_endpoint":
        next(value["row"] for name, value in rows if name == "inventory")["selected_task_id"] = 80
        error = "selected endpoint inventory missing"
    elif broken == "other_relation":
        error = "identity differs from original content"
    else:
        raw = next(
            value for name, value in rows if name == "reports" and value["origin_task_id"] == 100
        )
        raw["configuration"]["external_nomination_refs"] = []
        error = "differs from its registered producer and nomination configuration"
    root = tmp_path / "artifact"
    with pytest.raises(ValueError, match=error):
        write_review_bundle(request, root, iter(rows))
    assert not root.exists()


def comparison_rows(variant):
    from corpus_structure.core.evidence import config_key
    from corpus_structure.methods.structural_products import compare_clauses
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef
    from corpus_structure.semantic.structural_products import (
        DIMENSIONS,
        ClauseFieldGroup,
        ClauseReading,
        StructuralProductReport,
    )
    from corpus_structure.serve.structural_products import StructuralRequest

    rows = structural_rows("abcd")
    base = StructuralProductReport.model_validate(rows[1][1]["report"]).inputs
    original = base.passages[0]
    left = original.model_copy(update={"passage_id": "left", "text": "ab", "end": 2})
    right = original.model_copy(update={"passage_id": "right", "text": "cd", "start": 2})
    refs = [
        RetainedContributionRef(
            contribution_id="source-contribution:" + digit * 64,
            project_id="test",
            run_id=7,
            cut_id=8,
            release_id="release:old",
            result_revision=1,
            selected_task_id=71,
            origin_task_id=71,
            runtime_fingerprint="runtime:scope",
        )
        for digit in ("a", "b", "c")
    ]
    inputs = base.model_copy(
        update={"passages": (left, right), "dependencies": tuple(r.contribution_id for r in refs)}
    )
    legacy = compare_clauses(
        inputs,
        left=ClauseReading(passage_id=left.passage_id),
        right=ClauseReading(passage_id=right.passage_id),
    )
    groups = {dimension: ClauseFieldGroup(state="absent") for dimension in DIMENSIONS}
    current = compare_clauses(
        inputs,
        left=ClauseReading(passage_id=left.passage_id, groups=groups),
        right=ClauseReading(passage_id=right.passage_id, groups=groups),
        left_reading=refs[0],
        right_reading=refs[1],
    )
    assert current.comparison is not None
    alternate = current.model_copy(
        update={"comparison": current.comparison.model_copy(update={"left_reading": refs[2]})}
    )
    registered_version = "2" if variant == "archive" else "3"
    claimed_version = "2" if variant == "downgrade" else registered_version
    config = {
        "inputs": inputs.model_dump(mode="json"),
        "structural_input_digest": inputs.identity,
        "left_id": left.passage_id,
        "right_id": right.passage_id,
    }
    if registered_version == "3":
        config.update(
            left_reading=refs[0].model_dump(mode="json"),
            right_reading=refs[1].model_dump(mode="json"),
        )
    registered_hash = config_key("structure.compare", registered_version, config)
    selected = {"alternate": alternate, "drop": legacy, "archive": legacy, "downgrade": legacy}[
        variant
    ]
    origin = {"alternate": alternate, "drop": current, "archive": legacy, "downgrade": legacy}[
        variant
    ]
    rows[1][1].update(
        origin_run_id=2,
        origin_project_id="test",
        runtime_fingerprint="runtime:comparison",
        product_id=selected.product_id,
        report=selected.model_dump(mode="json"),
    )
    rows[2][1].update(
        origin_run_id=2,
        project_id="test",
        runtime_fingerprint="runtime:comparison",
        config_hash=registered_hash,
        input_hash="comparison-input",
        configuration=config,
        body=dict(
            method="structure.compare",
            operation_version=claimed_version,
            release_id="release:structural",
            outcome="produced",
            configuration_hash=registered_hash,
            input_hash="comparison-input",
            structural_product=origin.model_dump(mode="json"),
        ),
    )
    return ReviewSelection(
        structural_selections=(StructuralRequest(run_id=2, kind="qualified_comparison"),),
    ), rows


def test_detached_archive_requires_registered_singleton_comparison(
    tmp_path, synthetic_source_projection
):
    request, rows = comparison_rows("archive")
    write_review_bundle(request, tmp_path / "archive", iter(rows))
    verify_review_bundle(tmp_path / "archive")


@pytest.mark.parametrize(
    "variant, reason",
    [
        ("drop", "registered producer result"),
        ("alternate", "registered predicate readings"),
        ("downgrade", "registered producer result"),
    ],
)
def test_detached_comparison_refuses_resealed_reading_substitution(tmp_path, variant, reason):
    request, rows = comparison_rows(variant)
    with pytest.raises(ValueError, match=reason):
        write_review_bundle(request, tmp_path / "comparison", iter(rows))
    assert not (tmp_path / "comparison").exists()


def _equal_vector_neighborhood():
    from itertools import combinations

    ids = "abcdefg"
    inventory = {
        "inventory_id": "inventory",
        "targets": [
            {"target_id": key, "representation_digest": key, "source_binding": key} for key in ids
        ],
        "semantic_groups": [
            {"target_id": f"group-{key}", "member_target_ids": [key]} for key in ids
        ],
    }
    report = {
        "inventories": [inventory],
        "profiles": [{"profile_id": "profile", "dimension": 2}],
        "vectors": [
            {
                "object_id": key,
                "profile_id": "profile",
                "representation_digest": key,
                "source_binding": key,
                "values": [1.0, 0.0],
            }
            for key in ids
        ],
        "neighborhood": {
            "inventory_id": "inventory",
            "profile_id": "profile",
            "policy": "mutual-exact-cosine-top5-2",
            "status": "completed",
            "directed_ranks": [
                {"from_id": key, "to_id": peer, "rank": rank, "distance": 0.0}
                for key in ids
                for rank, peer in enumerate(ids.replace(key, "")[:5], 1)
            ],
            "edges": [
                {
                    "left_id": left,
                    "right_id": right,
                    "left_group": f"group-{left}",
                    "right_group": f"group-{right}",
                    "left_digest": left,
                    "right_digest": right,
                    "left_rank": ord(right) - ord("a"),
                    "right_rank": ord(left) - ord("a") + 1,
                    "distance": 0.0,
                }
                for left, right in combinations(ids[:6], 2)
            ],
        },
    }
    return report


def test_detached_native_neighborhood_requires_the_exact_mutual_intersection():
    from corpus_structure.serve.contextual_navigation import verify_detached_neighborhood

    report = _equal_vector_neighborhood()
    verify_detached_neighborhood(report, native_ranks=True)
    report["neighborhood"]["edges"] = []
    with pytest.raises(ValueError, match="exact directed-rank intersection"):
        verify_detached_neighborhood(report, native_ranks=True)

    report = _equal_vector_neighborhood()
    first_source = report["neighborhood"]["directed_ranks"][:5]
    for row, peer in zip(first_source, "cdefg", strict=True):
        row["to_id"] = peer
    report["neighborhood"]["edges"] = []
    with pytest.raises(ValueError, match="exact equal-vector ID order"):
        verify_detached_neighborhood(report, native_ranks=True)


def test_native_neighborhood_retains_all_directed_ranks_at_the_cutoff(semantic_db_engine):
    from sqlalchemy import text

    report = _equal_vector_neighborhood()
    with semantic_db_engine.connect() as conn:
        actual = conn.scalar(
            text(
                "SELECT ops.contextual_mutual_neighbors("
                "CAST(:inventory AS jsonb),CAST(:profile AS jsonb),CAST(:vectors AS jsonb))"
            ),
            {
                "inventory": json.dumps(report["inventories"][0]),
                "profile": json.dumps(report["profiles"][0]),
                "vectors": json.dumps(report["vectors"]),
            },
        )
    assert actual == report["neighborhood"]


def test_source_decision_keeps_the_witness_kind_under_its_delivery_kind():
    from corpus_structure.serve.contextual_navigation import (
        SourceDecisionParams,
        diagnose_source_decision,
    )

    artifact = {
        "records": [
            {
                "contribution_id": "reference",
                "occurrence_id": "source",
                "citations": [],
                "artifact": {"occurrence_role": "reference"},
            },
        ],
        "pairs": [],
        "external_nominations": [
            {"left": "caption", "right": "reference", "kind": "reference_target"},
        ],
    }
    answer = diagnose_source_decision(
        SourceDecisionParams(task_id=1, occurrence_id="source"),
        1,
        {"artifact_identity": artifact},
        [],
        [],
    )
    assert answer.decisions == (
        {
            "left": "caption",
            "right": "reference",
            "kind": "directed_artifact_nomination",
            "witness_kind": "reference_target",
        },
    )
