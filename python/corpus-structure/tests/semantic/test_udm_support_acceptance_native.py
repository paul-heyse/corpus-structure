"""Actual protected traversal and PDF guards independent of validity-family claims."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import Boolean, cast, func, literal, select, text, true, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from semantic.current_pdf_source_support import (
    admit_current_target,
)
from semantic.current_pdf_source_support import (
    published_pdf_source as published_pdf_source,
)
from semantic.current_pdf_source_support import (
    published_pdf_source_factory as published_pdf_source_factory,
)
from semantic.data_operation_kernel_support import split_captured_operations
from semantic.structural_admission_native_support import (
    ISSUER,
    PROJECT,
    execute,
    request,
    selected,
)
from semantic.test_structural_admission_native import (
    structural_native_journey as structural_native_journey,
)


def test_protected_authority_is_a_public_leaf_and_keeps_private_scope(structural_native_journey):
    from corpus_structure.semantic.demand_results import read_demand_result, selected_record_index
    from corpus_structure.semantic.effect_policy import ApprovedEffect, admit_effect_grants
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.support_edges import support_edge_queries

    case = structural_native_journey
    kernel, comparison = case["kernel"], case["comparison"]
    with kernel.purpose("admit").begin() as connection:
        admit_effect_grants(
            connection,
            kernel.prepared,
            kernel.model,
            (ApprovedEffect(ISSUER, "native-evaluator-structural-admission"),),
        )
    retained, result = execute(
        kernel,
        request(
            kernel,
            (ISSUER,),
            comparison.context,
            admission_report=comparison,
            originals=case["original_passes"],
            inference="authority-traversal-control",
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
    scope = {"product_ids": [admission.row["product_id"]]}
    with kernel.purpose("read").begin() as connection:
        page = read_demand_result(
            connection, retained["demand_id"], project_id=PROJECT, scope=scope
        )
    metadata = get_metadata()
    reads = metadata.tables["ops.data_demand_read"]
    root_use, root_episode = admission.row["use_id"], admission.row["derivation_id"]

    def walk(profile):
        nodes = select(literal("use").label("kind"), literal(root_use).label("id")).cte(
            "authority_fixture_nodes", recursive=True
        )
        boundary = (
            select(reads.table_valued())
            .where(reads.c.id == page.cut.record["read_id"])
            .scalar_subquery()
        )
        edges = union_all(
            *(
                edge.correlate(nodes)
                for edge in support_edge_queries(
                    metadata,
                    nodes.c.kind,
                    nodes.c.id,
                    profile,
                    authority=(
                        lambda identity: func.ops.ddo_policy_authority_leaf(
                            identity, type_=Boolean()
                        )
                    )
                    if profile == "public"
                    else None,
                    boundary=boundary,
                    product_ids=cast(literal(json.dumps(scope["product_ids"])), JSONB()),
                )
            )
        ).lateral("authority_fixture_edges")
        return nodes.union(
            select(edges.c.child_kind, edges.c.child_id)
            .select_from(nodes.join(edges, true()))
            .where(edges.c.child_id.is_not(None))
        )

    with kernel.engine.connect() as connection:
        private = set(connection.execute(select(walk("scope"))))
        public = set(connection.execute(select(walk("public"))))
        protected = set(
            connection.scalars(
                text(
                    "SELECT original.admission_id FROM ops.data_derivation_original_support original "
                    "WHERE original.derivation_id=:episode"
                ),
                {"episode": root_episode},
            )
        )
        assert len(protected) == 3  # the genuine A, B and parent-attributed C admissions
        assert protected == {entry["admission_id"] for entry in retained["authored_admissions"]}
        assert {("original", identity) for identity in protected} <= private
        assert not ({("original", identity) for identity in protected} & public)
        assert ("episode", root_episode) in private
        assert ("authority", root_episode) in public
        assert ("episode", root_episode) not in public
        assert public == {("use", root_use), ("authority", root_episode)}
        assert len(public) < len(private)
    with (
        kernel.purpose("read").begin() as connection,
        selected_record_index(
            connection, retained["demand_id"], project_id=PROJECT, scope=scope
        ) as (_, index),
    ):
        (leaf,) = tuple(index.rows("ops.data_authority_leaf"))
        assert leaf["derivation_id"] == root_episode
        assert leaf["use_id"] == root_use
        assert leaf["protected_dependencies"] == "undisclosed"
        assert not protected.intersection(
            row["id"] for row in index.rows("ops.original_source_admission")
        )


def test_undetermined_pdf_still_requires_actual_publication_receipt(published_pdf_source, tmp_path):
    from hashlib import sha256
    from typing import cast as typing_cast

    from corpus_structure.core.evidence import document_key
    from corpus_structure.semantic._data_operation_wire import WireRetainDataCompletionIntentRequest
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_demands import DemandPlanner
    from corpus_structure.semantic.data_operation_execution_evidence import bind_execution_evidence
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.original_documents import register_original_document
    from semantic.current_pdf_source_support import PROJECT as SOURCE_PROJECT
    from semantic.data_operation_demand_support import claim

    source = published_pdf_source
    recipe = source.kernel.recipe
    captured = recipe.captured_inputs
    assert captured is not None
    dependencies, declarations, sources = split_captured_operations(captured)
    module = "corpus_structure.ingest.pdf_capture"
    original = next(item for item in sources.sources if item.module == module)
    assert original.content.count(b'"validity_family": ["none"]') == 1
    changed = replace(
        original,
        filename="undetermined/pdf_capture.py",
        content=original.content.replace(
            b'"validity_family": ["none"]', b'"validity_family": ["undetermined"]'
        ),
    )
    sources = replace(
        sources,
        sources=tuple(changed if item.module == module else item for item in sources.sources),
    )
    updated = replace(
        recipe,
        captured_inputs=replace(
            captured, dependencies=data_operation_dependencies(dependencies, declarations, sources)
        ),
    )
    kernel = admit_current_target(source, updated, tmp_path / "undetermined-pdf")
    original_path = tmp_path / "undetermined-original.pdf"
    original_path.write_bytes(source.original)
    document = document_key(SOURCE_PROJECT, original_path.name, sha256(source.original).hexdigest())
    writable = replace(source, kernel=kernel, document_key=document, published_only=False)
    with kernel.purpose("write").begin() as connection:
        register_original_document(
            connection,
            prepared=kernel.prepared,
            project_id=SOURCE_PROJECT,
            source_uri=original_path.name,
            original_path=str(original_path),
            original=source.original,
            mime="application/pdf",
        )
        demand = writable.register(connection, "source.pdf/capture")
    with kernel.engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT validity_families,validity_conservative,command_class FROM sem.data_operation_definition WHERE release_id=:release AND operation_id='source.pdf/capture'"
            ),
            {"release": kernel.prepared.release_id},
        ).one()
        assert tuple(definition) == ([], True, "pdf")
    with kernel.purpose("write").begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        snapshot = planner.resume(demand)
    with kernel.purpose("write").begin() as connection:
        ready = DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
            snapshot, authorization=b"{}"
        )
    (capture,) = ready
    fence = claim(kernel, json.loads(capture.native))
    with kernel.engine.begin() as connection:
        with (
            pytest.raises(
                IntegrityError,
                match="sealed PDF completion requires only its actual publication receipt",
            ) as refusal,
            connection.begin_nested(),
        ):
            connection.execute(
                text(
                    "SELECT ops.ddo_require_pdf_completion(CAST(:completion AS jsonb),:task,:attempt,:holder,:release,'source.pdf/capture')"
                ),
                dict(
                    completion=json.dumps(
                        dict(outcome="success", outputs=[], execution_evidence={})
                    ),
                    task=fence["task_id"],
                    attempt=fence["attempt"],
                    holder=fence["holder"],
                    release=kernel.prepared.release_id,
                ),
            )
        assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
        # Exercise the completion consumer too. Its input/output shape is valid;
        # only the independently authenticated native publication proof is absent.
        kind = kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfCapture", "kind"
        ]
        body = connection.scalar(
            text(
                "SELECT data.ddo_json(canonical_body) FROM kb.data_product WHERE kind_contract=:kind AND original_source=:source LIMIT 1"
            ),
            {"kind": kind, "source": source.document_key},
        )
        assert isinstance(body, dict)
        body = {**body, "document": document}
        implementation = connection.scalar(
            text(
                "SELECT implementation_revision FROM sem.data_operation_definition WHERE release_id=:release AND operation_id='source.pdf/capture'"
            ),
            {"release": kernel.prepared.release_id},
        )
        binding = json.loads(capture.binding)
        completion = dict(
            outcome="success",
            implementation_revision=implementation,
            inputs=binding["inputs"],
            support=binding["support"],
            outputs=[
                dict(
                    role="result",
                    position=0,
                    multiplicity=1,
                    product=dict(kind_contract=kind, body=semantic_value(body), members=[]),
                )
            ],
            execution_evidence=bind_execution_evidence(
                None, fence=fence, runtime_id=kernel.runtime
            ),
        )
        with (
            pytest.raises(
                IntegrityError,
                match="sealed PDF completion requires only its actual publication receipt",
            ) as retained_refusal,
            connection.begin_nested(),
        ):
            DataOperationStorage(connection).retain_data_completion_intent(
                typing_cast(
                    WireRetainDataCompletionIntentRequest,
                    {**fence, "runtime_id": kernel.runtime, "completion": completion},
                )
            )
        assert getattr(retained_refusal.value.orig, "sqlstate", None) == "23514"
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_derivation WHERE release_id=:release"),
                {"release": kernel.prepared.release_id},
            )
            == 0
        )


def test_historical_pdf_raw_lineage_rejects_equal_value_from_another_real_episode(
    scenario_seeds, tmp_path, monkeypatch, native_settings
):
    from pydantic import TypeAdapter

    from corpus_structure.semantic.data_operation_service import (
        DemandOriginalSelection,
        DemandRoot,
        NativeDemandRequest,
        create_native_demand,
        execute_data_demand,
        read_data_demand,
    )
    from corpus_structure.semantic.original_documents import acquire_original_document_selection
    from corpus_structure.semantic.pdf_publication import PdfExecutionReceipt
    from corpus_structure.serve.selected_pdf import acquire_selected_pdf_source
    from semantic.current_pdf_integration_support import ROOT, current_integration_journey
    from semantic.test_current_pdf_integration_native import selected_reference

    with current_integration_journey(
        scenario_seeds, tmp_path, monkeypatch, native_settings
    ) as case:
        first_reference = selected_reference(case, "source.pdf/capture")
        with case.reader().begin() as connection:
            first = acquire_selected_pdf_source(connection, first_reference)
        with case.kernel.purpose("write").begin() as connection:
            original = acquire_original_document_selection(
                connection,
                project_id=case.original.project_id,
                document_key=case.original.document_key,
            )
            root = original.root
            retained = create_native_demand(
                connection,
                NativeDemandRequest(
                    project_id=case.original.project_id,
                    release_id=case.prepared.release_id,
                    runtime_id=case.kernel.runtime,
                    roots=(
                        DemandRoot(
                            subject=root.subject,
                            original_source=root.original_source,
                            analyzed_scope=json.loads(root.analyzed_scope),
                        ),
                    ),
                    targets=("source.pdf/capture",),
                    original_sources={
                        original.name: DemandOriginalSelection(
                            reference=original.reference.model_dump(mode="python"),
                            selectors=[{"scope": "whole-document"}],
                        )
                    },
                    inference="historical-raw-lineage-independent-policy-control",
                    execution_profile="source-native",
                ),
                prepared=case.prepared,
            )
        execution = execute_data_demand(
            case.kernel.purpose("write"),
            retained["demand_id"],
            source_root=ROOT,
            admission_engine=case.kernel.purpose("admit"),
            database_capacity=6,
            project_id=case.original.project_id,
        )
        assert execution.receipt_count == 1
        with case.reader().begin() as connection:
            snapshot = read_data_demand(connection, retained["demand_id"], view="products")
            second = acquire_selected_pdf_source(
                connection, selected_reference(case, "source.pdf/capture", snapshot)
            )
        assert second.reference.product_id == first.reference.product_id
        assert second.reference.derivation_id != first.reference.derivation_id
        assert second.physical.task_id != first.physical.task_id
        assert case.calls.count("capture") == 2
        with case.clone.admin.begin() as connection:
            query = text(
                "SELECT ops.ddo_pdf_capture_source_for_request(ops.ddo_pdf_producing_request(:observation),:project,:product,:raw)"
            )
            values = dict(
                observation=case.observation_source.reference.derivation_id,
                project=case.original.project_id,
                product=first.reference.product_id,
                raw=first.reference.derivation_id,
            )
            expected = TypeAdapter(PdfExecutionReceipt).dump_python(first.receipt, mode="json")
            assert connection.scalar(query, values) == expected
            with (
                pytest.raises(
                    IntegrityError,
                    match="PDF source is outside exact selected computational support",
                ) as refusal,
                connection.begin_nested(),
            ):
                connection.scalar(query, {**values, "raw": second.reference.derivation_id})
            assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
            assert connection.scalar(query, values) == expected
