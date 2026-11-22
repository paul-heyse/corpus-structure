"""Actual structural issuer/dossier custody; controlled upstream extraction only.

Authored actor identities are attribution assertions. This journey supplies no
evidence of external provider execution, provider accuracy or accepted science.
"""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import body_identity
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from semantic.current_pdf_source_support import admit_current_target
from semantic.structural_admission_native_support import (
    COMPARE,
    DOSSIER,
    ISSUER,
    PROJECT,
    authored,
    build_inventory,
    compare_selection,
    comparison_sources,
    execute,
    expected_statement,
    recipe,
    request,
    selected,
    source_products,
)
from semantic.structural_native_fixture import TEXT
from semantic.test_sentence_partition_chain_native import _private_source


def test_controlled_structural_fixture_has_complete_checked_source_and_independent_expectation(
    tmp_path,
):
    from types import SimpleNamespace

    from corpus_structure.methods.structural_products import produce_structural_comparison
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.declared_structural_references import (
        DeclaredContributionRef,
        DeclaredStructuralSource,
    )
    from corpus_structure.semantic.native_source_view import thaw_native
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import (
        DeclaredStructuralInput,
        DeclaredStructuralInputPin,
    )
    from semantic.data_operation_kernel_support import prepare_kernel
    from semantic.structural_native_fixture import source_values

    directory = tmp_path / "prepared"
    directory.mkdir()
    prepared = prepare_kernel(recipe(tmp_path), directory=directory)
    assert all(item.complete for item in prepared.model.implementation_slices)
    refs, predicates, retained, passages, sources = [], [], [], [], []
    for side in ("left", "right"):
        value = FrozenNativeSource.from_projection(
            prepared.prepared,
            document="pure:" + side,
            section_pointer="#/groups/0",
            membership="descendants",
            text=TEXT,
            pieces=[
                dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=9)
            ],
            items=[dict(self_ref="#/texts/0", label="text", text=TEXT, orig=TEXT, prov=[])],
        )
        analyzed_scope = thaw_native(
            dict(source=value.value["source"], selectors=value.value["selectors"])
        )
        context = dict(
            project_id=PROJECT,
            subject="pure:" + side,
            subject_definition="original-source-view",
            original_source="pure:" + side,
            analyzed_scope=analyzed_scope,
        )
        member = BoundRoleMember(
            "pure:source:" + side,
            "pure:source-kind",
            context["subject"],
            context["original_source"],
            json_bytes(analyzed_scope),
            b"{}",
            (),
            b"{}",
            subject_definition=context["subject_definition"],
            support_references=(),
        )
        frame = DeclaredNativeFrameSource.acquire(prepared.prepared, value, member, project=PROJECT)
        values = source_values(
            prepared.prepared,
            prepared.model,
            value.value,
            frame.pin.values(),
            context,
            DeclaredStructuralInputPin.from_bound(member, project=PROJECT).model_dump(
                mode="python"
            ),
        )
        report = values["predicates"]
        reading = next(
            packet["body"]["contribution_id"]
            for packet in report["members"]
            if packet["body"].get("component", {}).get("kind") == "predicate_reading"
        )
        reference = DeclaredContributionRef(
            product_id="pure:predicate:" + side,
            member_id=None,
            kind_contract="pure:predicate-kind",
            contribution_id=reading,
            **{
                key: context[key]
                for key in ("project_id", "subject", "subject_definition", "original_source")
            },
            analyzed_scope_meaning=frame.pin.values()["analyzed_scope_meaning"],
        )
        refs.append(reference)
        predicates.append(SimpleNamespace(body=report))
        from corpus_structure.semantic.declared_candidate_products import candidate_member_values

        retained.append(
            dict(contributions=candidate_member_values(report, candidate_type="contribution"))
        )
        source = DeclaredStructuralSource.model_validate(frame.pin.values())
        sources.append(source)
        passages.append(
            dict(
                passage_id=side,
                source_ref=source.identity,
                start=0,
                end=9,
                text=TEXT,
                scope="selected",
            )
        )
    inputs = DeclaredStructuralInput(
        question="Compare exact source-qualified controlled roles",
        scope="selected",
        inventory_id="independent-native-structural-inputs",
        policy_id="exact-native-structural-control-1",
        sources=sources,
        passages=passages,
        dependencies=[ref.contribution_id for ref in refs],
        coverage_limits=[
            "Only retained predicate coverage is used; unavailable formal characterization remains unresolved."
        ],
    )
    report = produce_structural_comparison(
        inputs,
        left_id="left",
        right_id="right",
        left_reading=refs[0],
        right_reading=refs[1],
        left_retained=retained[0],
        right_retained=retained[1],
        primary_layers=None,
    )
    assert structural_statement(report) == expected_statement(*predicates)


def _passes(kernel, report, expected):
    frame = dict(
        report=report.reference.model_dump(mode="python"),
        inputs=report.body["inputs"],
        question="Compare exact source-qualified controlled roles",
        case_id="whole",
        operation="qualified_comparison",
        component_id=None,
        rubric_version="independent-structural-comparison-1",
        direction="source_first",
        exposed_outputs=[],
    )
    meaning = canonical_bytes(semantic_value(expected)).decode()
    return [
        dict(
            version="structural-reference-pass-1",
            frame=deepcopy(frame),
            pass_kind=kind,
            actor=dict(
                principal="protected-structural-author:" + kind,
                session_id="authored-session:" + kind,
                basis="authored_attribution",
            ),
            author_assertion="protected-structural-author:" + kind,
            parents=[],
            cases=[
                dict(
                    case_id="whole",
                    facet="public_statement",
                    path=["public_statement"],
                    judgment="supported",
                    expected_meaning_json=meaning,
                    source_passages=["left", "right"],
                )
            ],
        )
        for kind in ("A", "B", "C")
    ]


@pytest.fixture
def structural_native_journey(semantic_bare_engine, native_settings, tmp_path, monkeypatch):
    from corpus_structure.ingest.pdf_worker import PdfWorker
    from corpus_structure.semantic.effect_policy import ApprovedEffect
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    def unexpected_conversion(*_args, **_kwargs):
        raise AssertionError("structural admission consumer reached its captured PDF converter")

    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, TEXT, TEXT
    ) as source:
        monkeypatch.setattr(PdfWorker, "stream", unexpected_conversion)
        target = recipe(tmp_path)
        target = replace(
            target,
            effect_approvals=(
                *target.effect_approvals,
                ApprovedEffect(ISSUER, "native-evaluator-structural-admission"),
            ),
        )
        kernel = admit_current_target(source, target, tmp_path / "consumer")
        originals = source_products(source)
        inventories = tuple(build_inventory(kernel, item) for item in originals)
        predicates = tuple(item[0] for item in inventories)
        component = inventories[0][1]
        selection = compare_selection(originals, predicates)
        source_sets = comparison_sources(originals, predicates)
        retained, result = execute(
            kernel,
            request(
                kernel,
                (COMPARE,),
                originals[0].context,
                source_sets=source_sets,
                selections=(selection,),
                inference="actual-structural-comparison",
            ),
        )
        assert result.receipt_count == 1
        (comparison,) = selected(
            kernel, retained["demand_id"], kind="urn:corpus:structural:DeclaredComparisonReport"
        )
        expected = expected_statement(*predicates)
        # These expectations were specified from the exact source/finite grammar,
        # before any protected pass exists; output agreement does not author labels.
        from corpus_structure.semantic.structural_admission import structural_statement
        from corpus_structure.semantic.structural_products import DeclaredComparisonReport

        assert (
            structural_statement(DeclaredComparisonReport.model_validate(comparison.body))
            == expected
        )
        passes = _passes(kernel, comparison, expected)
        independent = tuple(
            authored(
                kernel,
                comparison.context,
                "pass:" + value["pass_kind"],
                value,
                author=value["author_assertion"],
            )
            for value in passes[:2]
        )
        staged = author_interpretations(
            kernel.purpose("evaluate"),
            kernel.prepared,
            request=request(
                kernel,
                (ISSUER,),
                comparison.context,
                admission_report=comparison,
                originals=independent,
                inference="actual-original-structural-A-B",
            ),
        )
        # Actual admissions precede C. Its parents are their actual native product
        # addresses and bodies, rather than predicted product IDs or receipts.
        parents = []
        from corpus_structure.evaluate.declared_record_policy import _selected_body
        from corpus_structure.semantic.declared_structural_references import DeclaredProductRef
        from corpus_structure.semantic.demand_results import selected_record_index

        with (
            kernel.purpose("evaluate").begin() as connection,
            selected_record_index(
                connection, staged["demand_id"], project_id=PROJECT, scope={}, capture_frontier=True
            ) as (_, index),
        ):
            for admitted in staged["authored_admissions"]:
                _, body = _selected_body(index, admitted["product_id"])
                product = next(
                    row
                    for row in index.rows("kb.data_product")
                    if row["id"] == admitted["product_id"]
                )
                reference = DeclaredProductRef(
                    product_id=product["id"],
                    member_id=None,
                    kind_contract=product["kind_contract"],
                    project_id=PROJECT,
                    subject=product["subject"],
                    subject_definition=product["subject_definition"],
                    original_source=product["original_source"],
                    analyzed_scope_meaning=comparison.reference.analyzed_scope_meaning,
                )
                parents.append(
                    dict(
                        reference=reference.model_dump(mode="python"),
                        body_digest=body_identity(body).key,
                    )
                )
        assert len(parents) == 2
        passes[2]["parents"] = parents
        originals_passes = (
            *independent,
            authored(
                kernel,
                comparison.context,
                "pass:C",
                passes[2],
                author=passes[2]["author_assertion"],
            ),
        )
        yield dict(
            kernel=kernel,
            source=source,
            originals=originals,
            predicates=predicates,
            component=component,
            comparison=comparison,
            comparison_selection=selection,
            source_sets=source_sets,
            passes=passes,
            original_passes=originals_passes,
            expected=expected,
            tmp_path=tmp_path,
        )


def test_actual_structural_authorship_issuer_dossier_selected_gap_and_detached_export(
    structural_native_journey, monkeypatch
):
    from corpus_structure.semantic.data_operation_service import DemandOperationSelection
    from corpus_structure.serve.selected_structural_review import (
        SelectedStructuralReviewRequest,
        export_selected_structural_review,
        verify_selected_structural_review,
    )
    from corpus_structure.serve.structural_gaps import SelectedGapRequest, inspect_selected_gap
    from corpus_structure.serve.structural_products import (
        SelectedDossierRequest,
        inspect_selected_dossier,
    )

    case = structural_native_journey
    kernel, comparison = case["kernel"], case["comparison"]
    retained, result = execute(
        kernel,
        request(
            kernel,
            (ISSUER,),
            comparison.context,
            admission_report=comparison,
            originals=case["original_passes"],
            inference="actual-structural-independent-issuer",
        ),
        purpose="evaluate",
        author=True,
    )
    assert result.receipt_count == 1
    (admission,) = selected(
        kernel,
        retained["demand_id"],
        kind="urn:corpus:structural-admission:DdoStructuralAdmission",
        purpose="evaluate",
    )
    assert admission.body["assessment_basis"] == "independently_attributed_authored_judgments"
    assert admission.body["scientific_truth"] == "not_established"
    assert admission.body["member_truth"] == "not_established_by_assembly_admission"
    assert (
        admission.body["statement_meaning_json"]
        == canonical_bytes(semantic_value(case["expected"])).decode()
    )
    from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry
    from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support
    from corpus_structure.serve.structural_products import (
        SelectedStructuralAdmissionBinding,
        inspect_selected_structures,
    )
    from semantic.structural_production_native_support import read_statement

    with kernel.purpose("read").begin() as connection:
        public = read_demand_result(
            connection,
            retained["demand_id"],
            project_id=PROJECT,
            scope={"product_ids": [admission.row["product_id"]]},
            view="frontier",
        ).record
        assert public["selection"]["version"] == "data-demand-public-selection-v1"
        assert public["intent"] == public["selection"]
        assert public["selection"]["intent_digest"]
        assert (
            "original_sources" not in public["selection"]
            and "source_sets" not in public["selection"]
        )
        assert public["original_source_admissions"] == []
        (public_use,) = public["uses"]
        assert public_use["selection"] == {
            "kind": "native-authority",
            "protected_dependencies": "undisclosed",
        }
        assert public_use["request_id"] is None and public_use["generation"] is None
        assert b"protected-structural-author:" not in json_bytes(public)
        public_admission_page = read_demand_result(
            connection,
            retained["demand_id"],
            project_id=PROJECT,
            scope={"product_ids": [admission.row["product_id"]]},
            view="products",
        )
        (public_admission_header,) = [
            row
            for row in public_admission_page.members()
            if (row["product_id"], row["member_id"])
            == (admission.row["product_id"], admission.row["member_id"])
        ]
        assert public_admission_header["body"] == admission.body
        public_admission = SelectedSourceSetEntry.from_selected_header(
            public_admission_header, public_admission_page.cut
        )
        assert public_admission.entry == admission.entry().entry
        assert public_admission.proof == admission.entry().proof
        assert public_admission.read.read_id != admission.read.read_id
        assert public_admission_page.cut.record["scope"] == {
            "product_ids": [admission.row["product_id"]]
        }
        assert (
            public_admission_page.cut.record["selection"]["version"]
            == "data-demand-public-selection-v1"
        )
        with pytest.raises(DBAPIError, match="evaluator"), connection.begin_nested():
            read_demand_result(
                connection, retained["demand_id"], project_id=PROJECT, view="frontier"
            )
        private_product = retained["authored_admissions"][0]["product_id"]
        with pytest.raises(DBAPIError, match="evaluator"), connection.begin_nested():
            read_demand_result(
                connection,
                retained["demand_id"],
                project_id=PROJECT,
                scope={"product_ids": [private_product]},
                view="products",
            )
    with kernel.purpose("evaluate").begin() as connection:
        private = read_demand_result(
            connection,
            retained["demand_id"],
            project_id=PROJECT,
            scope={"product_ids": [admission.row["product_id"]]},
            view="frontier",
        ).record
        assert private["selection"]["version"] == "data-demand-intent-v2"
        assert "original_sources" in private["selection"]
    support_request, support_page = read_statement(
        kernel, retained["demand_id"], comparison, admission
    )
    assert support_page["reports"][0]["availability"] == "observed"
    assert support_page["reports"][0]["selection_basis"] == "native_structural_report_support"
    assert support_page["reports"][0]["public_assertions"][0]["admission"] == admission.body
    assert support_page["reports"][0]["producer"]["use_id"] == comparison.row["use_id"]
    with kernel.purpose("read").begin() as connection:
        without_issuer = inspect_selected_structures(
            connection, support_request.model_copy(update={"admissions": ()})
        )
        assert without_issuer["reports"][0]["availability"] == "outside_selection"
        unrelated = case["component"].root
        wrong_binding = inspect_selected_structures(
            connection,
            support_request.model_copy(
                update={
                    "roots": (unrelated,),
                    "admissions": (
                        SelectedStructuralAdmissionBinding(
                            report=unrelated, admission=admission.root
                        ),
                    ),
                }
            ),
        )
        assert wrong_binding["reports"][0]["availability"] == "outside_selection"
        support_archive = export_selected_structural_review(
            connection,
            SelectedStructuralReviewRequest(selection=support_request),
            destination=case["tmp_path"] / "ordinary-report-support-review",
        )
    support_archive_path, support_archive_digest = (
        support_archive["path"],
        support_archive["manifest_digest"],
    )
    assert isinstance(support_archive_path, str) and isinstance(support_archive_digest, str)
    assert (
        verify_selected_structural_review(
            Path(support_archive_path), manifest_digest=support_archive_digest
        )["cut_id"]
        == support_archive["cut_id"]
    )
    support_delivered = b"".join(
        path.read_bytes() for path in Path(support_archive_path).rglob("*") if path.is_file()
    )
    assert (
        b"protected-structural-author:" not in support_delivered
        and b"authored-session:" not in support_delivered
    )
    pinned_support = support_request.model_copy(
        update=dict(
            read_id=support_page["cut"]["read_id"],
            expected_cut=support_page["cut_id"],
            implementation=support_page["implementation"],
        )
    )
    component = case["component"]
    component_id = component.body["members"][0]["body"]["component_id"]
    dossier_selection = DemandOperationSelection(
        operation=DOSSIER,
        parameters=dict(
            component_id=component_id,
            question="Assemble the actual selected comparison and unresolved root",
            scope="selected",
        ),
    )
    sources = (
        FrozenSourceSet.from_selected(
            "dossier-sources", tuple(value.entry() for value in case["originals"])
        ),
        FrozenSourceSet.from_selected("dossier-components", (component.entry(),)),
        FrozenSourceSet.from_selected("dossier-definitions", ()),
        FrozenSourceSet.from_selected("dossier-comparisons", (comparison.entry(),)),
        FrozenSourceSet.from_selected("dossier-candidates", ()),
        FrozenSourceSet.from_selected("dossier-relationships", ()),
        FrozenSourceSet.from_selected("dossier-admissions", (public_admission,)),
    )
    # Ordinary execution consumes the bounded conclusion. The writer does not
    # receive evaluator inputs or a capability to issue another conclusion.
    ordinary, ordinary_result = execute(
        kernel,
        request(
            kernel,
            (DOSSIER,),
            comparison.context,
            source_sets=sources,
            selections=(dossier_selection,),
            inference="actual-writer-dossier-consumer",
        ),
    )
    assert ordinary_result.receipt_count == 1
    (ordinary_dossier,) = selected(
        kernel, ordinary["demand_id"], kind="urn:corpus:structural:DeclaredDossierReport"
    )
    complete, _ = execute(
        kernel,
        request(
            kernel,
            (COMPARE, ISSUER, DOSSIER),
            comparison.context,
            admission_report=comparison,
            originals=case["original_passes"],
            source_sets=(*case["source_sets"], *sources),
            selections=(case["comparison_selection"], dossier_selection),
            inference="actual-ordinary-structural-dossier",
        ),
        purpose="evaluate",
        author=True,
    )
    (actual_comparison,) = selected(
        kernel,
        complete["demand_id"],
        kind="urn:corpus:structural:DeclaredComparisonReport",
        purpose="evaluate",
    )
    (actual_admission,) = selected(
        kernel,
        complete["demand_id"],
        kind="urn:corpus:structural-admission:DdoStructuralAdmission",
        purpose="evaluate",
    )
    (dossier,) = selected(
        kernel,
        complete["demand_id"],
        kind="urn:corpus:structural:DeclaredDossierReport",
        purpose="evaluate",
    )
    assert actual_comparison.row["product_id"] == comparison.row["product_id"]
    assert dossier.row["product_id"] == ordinary_dossier.row["product_id"]

    with kernel.purpose("read").begin() as connection:
        dossier_page = read_demand_result(
            connection,
            complete["demand_id"],
            project_id=PROJECT,
            scope={"product_ids": [dossier.row["product_id"]]},
        )
        (admission_input,) = (
            edge["record"]
            for edge in stream_selected_support(connection, dossier_page, whole_read=True)
            if edge["relation"] == "ops.data_derivation_input"
            and edge["record"]["derivation_id"] == dossier.row["derivation_id"]
            and edge["record"]["role"] == "admissions"
        )
    assert admission_input["product_id"] == actual_admission.row["product_id"]
    assert admission_input["member_id"] is None and admission_input["multiplicity"] == 1
    assert "admissions_input" not in dossier.body
    assert dossier.body["dossier"]["members"]
    assert all(value["qualification"] == "proposed" for value in dossier.body["dossier"]["members"])
    gap = SelectedGapRequest(
        demand_id=complete["demand_id"],
        project_id=PROJECT,
        report="unconnected_supported_comparison",
        root=actual_comparison.root,
        binding=dossier.root,
        admission=actual_admission.root,
    )
    with kernel.purpose("read").begin() as connection:
        page = inspect_selected_gap(connection, gap)
        membership = inspect_selected_dossier(
            connection,
            SelectedDossierRequest(
                demand_id=complete["demand_id"],
                project_id=PROJECT,
                root=dossier.root,
                population="membership",
            ),
        )
        archive = export_selected_structural_review(
            connection,
            SelectedStructuralReviewRequest(selection=gap),
            destination=case["tmp_path"] / "ordinary-structural-review",
        )
    assert page["availability"] == "observed"
    (row,) = page["rows"]
    assert row["reason"] == "no_qualifying_root_binding" and set(row["evidence"]["sides"]) == {
        "left",
        "right",
    }
    assert row["evidence"]["scientific_truth"] == "not_established"
    assert row["evidence"]["sides"]["left"]["source"] != row["evidence"]["sides"]["right"]["source"]
    with kernel.purpose("read").begin() as connection, pytest.raises(ValueError, match="scope"):
        inspect_selected_gap(connection, gap.model_copy(update={"scope": "foreign-scope"}))
    assert membership["availability"] == "observed"
    archive_path, archive_digest = archive["path"], archive["manifest_digest"]
    assert isinstance(archive_path, str) and isinstance(archive_digest, str)
    verified = verify_selected_structural_review(Path(archive_path), manifest_digest=archive_digest)
    assert verified["cut_id"] == archive["cut_id"]
    # Every delivered ordinary byte is inspected, including native support closure.
    ordinary = b"".join(
        path.read_bytes() for path in Path(archive_path).rglob("*") if path.is_file()
    )
    assert b"protected-structural-author:" not in ordinary and b"authored-session:" not in ordinary
    # Captured schemas may describe the protected kind. Actual protected products
    # and original pass bodies are not ordinary disclosed provenance.
    native = Path(archive_path) / "native"
    native_manifest = json_loads((native / "manifest.json").read_bytes())
    closure_name = native_manifest["closure"]
    assert isinstance(closure_name, str)
    closure = [json_loads(line) for line in (native / closure_name).read_bytes().splitlines()]
    protected_kind = kernel.identities[
        "urn:corpus:structural-admission:protected:DdoStructuralReferencePass", "kind"
    ]
    assert not any(
        value["relation"] == "kb.data_product"
        and value["record"]["kind_contract"] == protected_kind
        for value in closure
    )
    assert any(
        value["relation"] == "ops.data_authority_leaf"
        and value["record"]["product_id"] == actual_admission.row["product_id"]
        and value["record"]["protected_dependencies"] == "undisclosed"
        for value in closure
    )

    # Same-shaped authored content has no issuer standing. Give the copied fact
    # its actual different subject so semantic-product deduplication cannot turn
    # this into possession of the already genuinely issued product.
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    copy_context = replace(
        comparison.context, subject="authored-copy:" + comparison.context.subject
    )
    copied = authored(
        kernel,
        copy_context,
        "ordinary-admission-copy",
        admission.body,
        author="ordinary authored-copy control",
        kind="urn:corpus:structural-admission:DdoStructuralAdmission",
    )
    copy_report = author_interpretations(
        kernel.purpose("write"),
        kernel.prepared,
        request=request(
            kernel,
            (DOSSIER,),
            copy_context,
            originals=(copied,),
            source_sets=sources,
            selections=(dossier_selection,),
            inference="same-kind-authored-content-is-not-native-authority",
        ),
    )
    (copy_header,) = copy_report["authored_admissions"]
    assert copy_header["evidence"]["standing"] == "authored"
    from corpus_structure.semantic.demand_results import selected_record_index

    with (
        kernel.purpose("read").begin() as connection,
        selected_record_index(
            connection,
            copy_report["demand_id"],
            project_id=PROJECT,
            scope={"product_ids": [copy_header["product_id"]]},
            capture_frontier=True,
        ) as (_, index),
    ):
        assert copy_header["admission_id"] in {
            value["admission_id"] for value in index.frontier_rows("original_source_admissions")
        }
        assert not tuple(index.rows("ops.data_authority_leaf"))
    with kernel.engine.begin() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_derivation_output WHERE product_id=:product"),
                {"product": copy_header["product_id"]},
            )
            == 0
        )
    # This address is an adversarial caller claim, never a fabricated receipt.
    # It cannot borrow the other exact product's real issuer proof.
    claimed_root = actual_admission.root.model_copy(
        update={"product_id": copy_header["product_id"]}
    )
    with kernel.purpose("read").begin() as connection:
        refused = inspect_selected_gap(
            connection, gap.model_copy(update={"admission": claimed_root})
        )
    assert [row["status"] for row in refused["rows"]] == ["unavailable"]
    assert refused["rows"][0]["reason"] == "authorized_comparison_support_unavailable"
    with kernel.purpose("read").begin() as connection:
        copied_support = inspect_selected_structures(
            connection,
            support_request.model_copy(
                update={
                    "admissions": (
                        SelectedStructuralAdmissionBinding(
                            report=comparison.root, admission=claimed_root
                        ),
                    )
                }
            ),
        )
    assert copied_support["reports"][0]["availability"] == "outside_selection"

    for failure in ("original-author", "ordinary-output"):
        changed = deepcopy(case["passes"][2])
        changed["actor"]["session_id"] += ":" + failure
        author = (
            "different-original-author"
            if failure == "original-author"
            else changed["author_assertion"]
        )
        c = authored(kernel, comparison.context, "refusal:C:" + failure, changed, author=author)
        pending = request(
            kernel,
            (ISSUER,),
            comparison.context,
            admission_report=comparison,
            originals=(*case["original_passes"][:2], c),
            inference="native-structural-refusal:" + failure,
        )
        _assert_native_issuer_refusal(
            kernel, pending, monkeypatch, exchange_output=failure == "ordinary-output"
        )

    # Each authored demand has its own admission of C, even for equal content.
    # Revoke the later issuer's exact pin, then the earlier issuer pin explicitly
    # selected by the dossier and ordinary report-support source set.
    from typing import cast

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.metadata import table

    (original_c,) = [
        value for value in complete["authored_admissions"] if value["selection_name"] == "pass:C"
    ]
    (earlier_c,) = [
        value for value in retained["authored_admissions"] if value["selection_name"] == "pass:C"
    ]
    assert original_c["admission_id"] != earlier_c["admission_id"]
    original_support = table("ops.data_derivation_original_support")
    with kernel.engine.begin() as connection:
        later_support = set(
            connection.scalars(
                select(original_support.c.admission_id).where(
                    original_support.c.derivation_id == actual_admission.row["derivation_id"]
                )
            )
        )
        earlier_support = set(
            connection.scalars(
                select(original_support.c.admission_id).where(
                    original_support.c.derivation_id == admission.row["derivation_id"]
                )
            )
        )
        assert original_c["admission_id"] in later_support
        assert earlier_c["admission_id"] not in later_support
        assert earlier_c["admission_id"] in earlier_support
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"),
                {"episode": actual_admission.row["derivation_id"]},
            )
            is True
        )
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"),
                {"episode": dossier.row["derivation_id"]},
            )
            is True
        )
    import psycopg

    withdrawal = cast(
        WireRevokeDataSupportRequest,
        dict(
            project_id=PROJECT,
            original_source=comparison.context.original_source,
            selector_kind="original-admission",
            selector=original_c["admission_id"],
            reason="controlled actual structural C revocation",
        ),
    )
    # The original C is protected evaluator data. Ordinary write capability
    # authorizes ordinary withdrawals, without granting this protected effect.
    with (
        pytest.raises(DBAPIError, match="evaluator data requires evaluator purpose") as refusal,
        kernel.purpose("write").begin() as connection,
    ):
        DataOperationStorage(connection).revoke_data_support(withdrawal)
    assert isinstance(refusal.value.orig, psycopg.errors.InsufficientPrivilege)
    with kernel.purpose("evaluate").begin() as connection:
        DataOperationStorage(connection).revoke_data_support(withdrawal)
    with kernel.engine.begin() as connection:
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"),
                {"episode": actual_admission.row["derivation_id"]},
            )
            is False
        )
    with kernel.purpose("evaluate").begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    **withdrawal,
                    "selector": earlier_c["admission_id"],
                    "reason": "controlled exact earlier structural C dossier support revocation",
                },
            )
        )
    with kernel.engine.begin() as connection:
        assert (
            connection.scalar(
                text("SELECT ops.ddo_node_valid('episode',:episode)"),
                {"episode": dossier.row["derivation_id"]},
            )
            is False
        )
    with kernel.purpose("read").begin() as connection:
        current = inspect_selected_gap(connection, gap)
    assert current["rows"] and all(row["status"] == "unavailable" for row in current["rows"])
    with kernel.purpose("read").begin() as connection:
        withdrawn = inspect_selected_structures(connection, support_request)
    assert withdrawn["reports"][0]["availability"] == "outside_selection"
    with (
        pytest.raises(DBAPIError, match="read trust changed; reacquire demand read") as stale,
        kernel.purpose("read").begin() as connection,
    ):
        inspect_selected_structures(connection, pinned_support)
    assert isinstance(stale.value.orig, psycopg.errors.CheckViolation)
    assert (
        verify_selected_structural_review(
            Path(support_archive_path), manifest_digest=support_archive_digest
        )["cut_id"]
        == support_archive["cut_id"]
    )
    # The held historic transfer remains verifiable; it grants no current trust.
    assert (
        verify_selected_structural_review(Path(archive_path), manifest_digest=archive_digest)[
            "cut_id"
        ]
        == archive["cut_id"]
    )


def _assert_native_issuer_refusal(kernel, pending, monkeypatch, *, exchange_output):
    import psycopg

    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.data_operation_values import decode_semantic_value

    actual = DataOperationStorage.retain_data_completion_intent
    observed = []

    def guarded(storage, payload):
        if (
            payload["completion"]["outputs"]
            and payload["completion"]["outputs"][0]["role"] == "admission"
        ):
            if exchange_output:
                exchanged = deepcopy(payload)
                output = exchanged["completion"]["outputs"][0]["product"]
                value = decode_semantic_value(output["body"])
                import json

                statement = decode_semantic_value(json.loads(value["statement_meaning_json"]))
                statement["scope"] = "forged-native-output-scope"
                value["statement_meaning_json"] = canonical_bytes(
                    semantic_value(statement)
                ).decode()
                altered = semantic_value(value)
                output["body"] = payload["completion"]["outputs"][0]["product"]["body"]
                assert exchanged == payload
                output["body"] = altered
                payload = exchanged
            try:
                return actual(storage, payload)
            except DBAPIError as error:
                observed.append(error)
                raise
        return actual(storage, payload)

    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, "retain_data_completion_intent", guarded)
        with pytest.raises(NativeDemandExecutionError):
            execute(kernel, pending, purpose="evaluate", author=True)
    assert len(observed) == 1
    error = observed[0].orig
    assert isinstance(error, psycopg.errors.CheckViolation) and error.sqlstate == "23514"
    expected = (
        "ordinary conclusion differs"
        if exchange_output
        else "original submitted author attribution"
    )
    assert expected in (error.diag.message_primary or "")


def test_definition_admission_refuses_same_shaped_controlled_fixture_producer(
    structural_native_journey, monkeypatch
):
    """A genuine fixture CPU receipt does not become a released definition producer."""
    import psycopg

    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import DeclaredDefinitionComponentsReport
    from semantic.structural_reference_native_support import original_passes

    case = structural_native_journey
    kernel, component = case["kernel"], case["component"]
    report = DeclaredDefinitionComponentsReport.model_validate(component.body)
    selector = report.components[0].component_id
    expected = structural_statement(report, selector)
    originals, _ = original_passes(
        kernel,
        component,
        expected,
        component_id=selector,
        inference="controlled-component-is-not-production-definition",
    )
    pending = request(
        kernel,
        (ISSUER,),
        component.context,
        originals=originals,
        admission_report=component,
        admission_variant="definition",
        inference="refuse-wrong-definition-producer",
    )
    actual = DataOperationStorage.retain_data_completion_intent
    observed = []

    def inspect(storage, payload):
        try:
            return actual(storage, payload)
        except DBAPIError as error:
            observed.append(error.orig)
            raise

    monkeypatch.setattr(DataOperationStorage, "retain_data_completion_intent", inspect)
    with pytest.raises(NativeDemandExecutionError):
        execute(kernel, pending, purpose="evaluate", author=True)
    assert len(observed) == 1
    assert isinstance(observed[0], psycopg.errors.CheckViolation)
    assert (
        observed[0].diag.message_primary
        == "structural report lacks its one actual captured producer for the selected variant"
    )
