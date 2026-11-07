"""Source-conditioned table requests are authored and enforced by the same native policy."""

from copy import deepcopy
from dataclasses import asdict, replace
from math import exp
from threading import Event

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods.scoped_relations import (
    ScopedRelationsConfig,
    ScopedRelationsMethod,
    discover_relations,
)
from corpus_structure.methods.table_interpretation import execute_table_correspondence
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import bind_result, source_python, source_value
from corpus_structure.semantic.operations import (
    BoundReader,
    claim_tasks,
    complete_task,
    create_task,
    record_method,
    seal_cut,
)
from corpus_structure.semantic.proposals import native_source_frame

from .native_record_fixtures import private_source as private_source
from .native_record_fixtures import private_source_options as private_source_options


def _wire(value):
    return canonical_bytes(value).decode()


def _band_fixture(conn):
    def edge(key, axis, *, disjoint=False):
        return dict(
            id=key,
            axis=axis,
            role="value_role",
            disjoint=disjoint,
            direct=False,
            evidence=["source", key],
        )

    def premise(key, candidates):
        return dict(
            identity=key,
            standing="alternative",
            source_revision="native1",
            source_view_id=1,
            source_projection="view1",
            source_recipe="recipe1",
            observed_table="#/tables/0",
            schematic_table="#/tables/" + key[-1],
            observed_caption="#/texts/0",
            schematic_caption="#/texts/" + key[-1],
            declaration_pointer="#/texts/3",
            bindings={
                candidate: dict(
                    alignment="exact",
                    dependencies=["source", candidate],
                    observed_anchor="observed",
                    schematic_anchor="schematic",
                    declaration_anchor="declaration",
                )
                for candidate in candidates
            },
        )

    edges = [
        edge("a1", "A"),
        edge("a2", "A"),
        edge("a3", "A", disjoint=True),
        edge("b1", "B"),
        edge("b2", "B"),
    ]
    premises = [premise("M1", ("a1", "b1")), premise("M2", ("a2",))]
    dependencies = ["source", "a1", "a2", "a3", "b1", "b2"]
    from corpus_structure.methods.local_interpretation import local_constraint_id

    products = [{"contribution_id": "retained"}]
    scope = local_constraint_id("test correspondence", products, dependencies)
    request = conn.scalar(
        text("""
            SELECT ops.table_correspondence_band(CAST(:edges AS jsonb), CAST(:premises AS jsonb),
                CAST(:dependencies AS jsonb), 'native1', 'view1', :scope, 1)
        """),
        dict(
            edges=_wire(edges),
            premises=_wire(premises),
            dependencies=_wire(dependencies),
            scope=scope,
        ),
    )
    return products, dict(
        scope_id=scope,
        question="test correspondence",
        contribution_ids=["retained"],
        dependencies=dependencies,
        reason=None,
        request=request,
    )


def test_native_ambiguous_correspondence_keeps_local_choices_and_counts_event_union_once(
    semantic_db_engine,
):
    with semantic_db_engine.connect() as conn:
        products, prepared = _band_fixture(conn)

    def execute(request=prepared, **kwargs):
        (operation,) = execute_table_correspondence(products, (request,), **kwargs)
        report = operation["local_interpretation"]
        return source_python(report["request"]), source_python(report["result"])

    request, result = execute()
    assert request == prepared["request"]
    assert request["correspondence_status"] == "ambiguous"
    assert [d["key"] for d in request["decisions"]] == ["M", "A", "B"]
    assert [[c["key"] for c in d["candidates"]] for d in request["decisions"]] == [
        ["unresolved", "M1", "M2"],
        ["unresolved", "a1", "a2", "a3"],
        ["unresolved", "b1", "b2"],
    ]
    assert request["constraints"][0]["allowed"] == [True, True, True, False]
    assert result["outcome"] == "completed"
    # The three M rows contribute 9, 2*4*4, and 2*4*3 respectively.
    assert exp(result["log_partition"]) == pytest.approx(65)
    assert result["search"]["positive_states"] == 27
    marginals = {(m["decision"], m["candidate"]): m["probability"] for m in result["marginals"]}
    assert marginals["M", "unresolved"] == pytest.approx(9 / 65)
    assert marginals["A", "a3"] == 0
    assert marginals["B", "b2"] == pytest.approx(19 / 65)
    assert marginals["B", "unresolved"] == pytest.approx(19 / 65)
    assert result["event_probabilities"] == [
        {"event": "any-value_role", "probability": pytest.approx(60 / 65)}
    ]
    assert [tuple(c["candidate"] for c in a["choices"]) for a in result["alternatives"]] == [
        ("M1", "a1", "b1"),
        ("M1", "unresolved", "b1"),
        ("M1", "a1", "unresolved"),
        ("M1", "a1", "b2"),
        ("M1", "a2", "b1"),
    ]
    assert result["omitted_candidate_mass"] == "unknown"

    cancellation = Event()
    cancellation.set()
    assert execute(cancellation=cancellation)[1]["outcome"] == "cancelled"

    class LeaseLost(Exception):
        pass

    polls = 0

    def check_active():
        nonlocal polls
        polls += 1
        if polls == 3:
            raise LeaseLost

    with pytest.raises(LeaseLost):
        execute(check_active=check_active)
    for key, value in (("max_states", 1), ("max_workspace_bytes", 1), ("max_seconds", 0)):
        constrained = deepcopy(prepared)
        constrained["request"]["limits"][key] = value
        _, limited = execute(constrained)
        assert limited["outcome"] == "resource_limit"
        assert limited["alternatives"] == limited["marginals"] == []


def test_native_admission_refuses_resealed_factor_mask_and_missing_policy(private_source):
    case = private_source
    method = ScopedRelationsMethod()
    config = ScopedRelationsConfig(interpretation_mode="correspondence")
    selected = MethodRegistry(
        (method,), MethodsFile(configs={method.name: {"correspondence": config.model_dump()}})
    ).resolve(method.name, "correspondence")
    configuration_hash = selected.config_hash
    with case.writer.begin() as conn:
        registered = record_method(
            conn,
            method,
            "correspondence",
            selected.params,
            configuration_hash,
            prepared=case.prepared,
        )
        key = case.view_row["key"]
        task_id = create_task(
            conn,
            run_id=case.run,
            config_id=registered,
            stage="resolve",
            unit_type="source_view",
            unit_id=case.view,
            unit_key=key,
            input_hash="native-correspondence-test",
        )
        (claim,) = claim_tasks(conn, run_id=case.run, config_id=registered, holder="table-worker")
        reader = BoundReader(conn, case.run, case.prepared)
        view = reader.source_view(case.view)
        (unavailable,) = execute_table_correspondence(
            (), reader.prepare_table_correspondence(case.view, (), 1)
        )
        assert unavailable["outcome"] == "not_run"
        assert unavailable["question"] == f"source correspondence availability for view {case.view}"
        assert "request" not in unavailable["local_interpretation"]
        frame = native_source_frame(view, ())
        output = discover_relations(frame)
        subject, original_target = output["contributions"]
        target = deepcopy(original_target)
        target["value"] = source_value({**source_python(target["value"]), "role": "header"})
        target["contribution_id"] = contribution_identity(target)
        subject_id, target_id = subject["contribution_id"], target["contribution_id"]
        deps = (subject_id, target_id, *subject["computation_dependencies"])
        operation = {**output["operation"], "emitted_count": 3}
        # This controlled candidate proposes a header in a disjoint exact native column.
        relation = dict(
            contract=subject["contract"],
            kind="relation",
            semantic_type="structural.scoped_attachment",
            operation_key=operation["operation_key"],
            item_key="disjoint-column-control",
            pin=subject["pin"],
            anchors=(),
            endpoints=(
                dict(role="attachment", contribution_id=subject_id),
                dict(role="target", contribution_id=target_id),
            ),
            members=deps[:2],
            disposition="scoped_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=deps,
            component=dict(
                protocol="witnessed-component-1",
                kind="scoped_attachment",
                question=operation["question"],
                question_version=operation["operation_version"],
                scope=case.table,
                interpretation="unassessed",
                bases=(dict(kind="native_geometry", dependencies=deps[2:]),),
                dependencies=deps,
                attachment_contribution_id=subject_id,
                target_contribution_id=target_id,
                attachment_kind="header",
            ),
            value=source_value(
                dict(
                    protocol="scoped-attachment-1",
                    subject_id=subject_id,
                    target_id=target_id,
                    relation="header",
                    region=case.table,
                    scope=case.table,
                    basis="native_geometry",
                    interpretation="unassessed",
                    dependencies=deps,
                    reason="Controlled disjoint exact column candidate.",
                )
            ),
        )
        relation["contribution_id"] = contribution_identity(relation)
        contributions = (subject, target, relation)
        prepared = reader.prepare_table_correspondence(case.view, contributions, 1)
        assert prepared == reader.prepare_table_correspondence(
            case.view, tuple(reversed(contributions)), 1
        )
        (question,) = prepared
        assert question["request"]["constraints"][0]["allowed"] == [True, False]
        invocation = conn.scalar(
            text("SELECT invocation_key FROM ops.task WHERE id=:task"), {"task": task_id}
        )

    result = UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, key),
        outcome=ObservationOutcome.PRODUCED,
        contributions=contributions,
        contribution_operations=(operation,),
        contribution_coordinate_texts=output["coordinates"],
    )

    def envelope(questions):
        interpretations = execute_table_correspondence(contributions, questions)
        return bind_result(
            case.prepared,
            source=key,
            method=method.name,
            operation_version=method.version,
            configuration_hash=configuration_hash,
            input_hash="native-correspondence-test",
            invocation_key=invocation,
            result=replace(result, contribution_operations=(operation, *interpretations)),
        ).model_dump(mode="json", exclude={"observations"}, exclude_none=True)

    def complete(conn, report):
        return complete_task(
            conn,
            task_id=task_id,
            attempt=claim.attempt,
            holder="table-worker",
            prepared=case.prepared,
            observations=(),
            outcome="done",
            envelope=report,
        )

    from corpus_structure.serve.table_correspondence_replay import verify_table_correspondence

    source = dict(
        source_view_id=view.ref.id, ref=asdict(view.ref), text=view.text, context=view.context()
    )
    verify_table_correspondence(
        dict(body=envelope(prepared), configuration=config.model_dump()), source
    )
    with case.writer.begin() as conn:
        for field, subfield, index, value in (
            ("potentials", "values", 0, 0.125),
            ("constraints", "allowed", 1, True),
        ):
            forged = deepcopy(prepared)
            forged[0]["request"][field][0][subfield][index] = value
            with pytest.raises(ValueError, match="differs from source-conditioned replay"):
                verify_table_correspondence(
                    dict(body=envelope(forged), configuration=config.model_dump()), source
                )
            with (
                pytest.raises(DBAPIError, match="authoritative source-conditioned request"),
                conn.begin_nested(),
            ):
                complete(conn, envelope(forged))
        with (
            pytest.raises(DBAPIError, match="authoritative source-conditioned request"),
            conn.begin_nested(),
        ):
            complete(conn, envelope(()))
        complete(conn, envelope(prepared))
        cut = seal_cut(conn, case.run, "table-correspondence", final=False)
    with case.writer.connect() as conn:
        retained = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            cut_id=cut,
            source_view_id=case.view,
            method=method.name,
            include_details=True,
        )
    (interpretation,) = [
        item["local_interpretation"]
        for item in retained.operations
        if item.get("local_interpretation")
    ]
    assert source_python(interpretation["request"]) == question["request"]
    assert interpretation["policy_version"] == "source-correspondence-1"
