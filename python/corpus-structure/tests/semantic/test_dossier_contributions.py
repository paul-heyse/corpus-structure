"""Retained source joins supply assessable private membership with full endpoint custody."""

import copy
import json
from pathlib import Path

import pytest
from methods.test_m1_source_preparation import native_table_source, table_cell
from methods.test_scoped_relations import complete_native_fields
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.dossier_contributions import derive_contribution_members
from corpus_structure.methods.scoped_relations import discover_relations
from corpus_structure.methods.structural_products import StructuralDossierConfig, select_dossier
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)

from .test_review_bundle import synthetic_source_projection as synthetic_source_projection


def source_fixture():
    frame = native_source_frame(
        complete_native_fields(
            native_table_source(
                (
                    table_cell("Probability %", 0, 1, column_header=True),
                    table_cell("50", 1, 1),
                )
            )
        ),
        (),
    )
    rows = discover_relations(frame)["contributions"]
    relation = next(
        r
        for r in rows
        if r["kind"] == "relation" and source_python(r["value"])["relation"] == "unit"
    )
    ids = set(relation["members"]) | {relation["contribution_id"]}
    closure = [r for r in rows if r["contribution_id"] in ids]
    pin = record_source_pin(frame)
    source = ExternalSourceRef(
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        source_view_id=pin["source_view_id"],
        native_task_id=pin["native_product_task_id"],
        native_product_key=pin["product_key"],
        native_content_digest=pin["product_digest"],
        projection_digest=pin["projection_digest"],
        recipe_digest=pin["recipe_digest"],
        coordinate_version=3,
    )
    inputs = StructuralInput(
        question="Structure corpus",
        scope="corpus",
        inventory_id="i",
        policy_id="p",
        sources=(source,),
        passages=(
            StructuralPassage(
                passage_id="table",
                source_ref=source.identity,
                start=0,
                end=len(frame.text),
                text=frame.text,
                scope="table",
            ),
        ),
        dependencies=(relation["contribution_id"],),
    )
    ref = RetainedContributionRef(
        contribution_id=relation["contribution_id"],
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
    )
    native = json.loads(frame.native_context)
    payload = dict(
        contributions=closure,
        sources=[
            dict(
                source_view_id=frame.source_view_id,
                pin=pin,
                projection=dict(text=frame.text, pieces=native["pieces"]),
            )
        ],
    )
    return inputs, ref, payload


def test_source_join_enters_dossier_with_both_endpoint_citations_and_no_borrowed_support():
    inputs, ref, payload = source_fixture()
    payload["public_assertions"] = [
        dict(assessment_id="source-geometry-is-not-meaning", statement="quote")
    ]
    members = derive_contribution_members(inputs, ref, payload)
    assert len(members) == 1
    member = members[0]
    assert member.role == "relationship" and member.qualification == "proposed"
    assert member.assessment_id is None and member.scope.startswith(
        inputs.sources[0].identity + ":"
    )
    assert member.contribution_citations is not None
    assert member.computation_dependencies is not None
    assert {c.span.text for c in member.contribution_citations} == {"50", "Probability %"}
    assert set(member.computation_dependencies) >= {
        r["contribution_id"] for r in payload["contributions"]
    }
    with pytest.raises(ValidationError, match="retained predecessors"):
        StructuralDossierConfig(
            inputs=inputs,
            structural_input_digest=inputs.identity,
            contribution_predecessors=(ref,),
        )
    report = select_dossier(
        inputs,
        root_id="corpus",
        members=members,
        contribution_predecessors=(ref,),
        member_budget=1,
    )
    assert report.dossier is not None
    assert len(report.dossier.members) == 1 and report.dossier.supported_facets == ()
    assert "definition" in report.dossier.missing_sections


@pytest.mark.parametrize("field", ["run_id", "origin_task_id", "selected_task_id"])
def test_reference_forbids_loose_identifiers(field):
    _, ref, _ = source_fixture()
    with pytest.raises(ValidationError):
        RetainedContributionRef.model_validate({**ref.model_dump(), field: "1"})
    with pytest.raises(ValidationError):
        RetainedContributionRef.model_validate({**ref.model_dump(), "supported": True})


@pytest.mark.parametrize("corruption", ["identity", "endpoint", "source", "citation", "passage"])
def test_source_membership_rejects_forged_closure(corruption):
    inputs, ref, payload = source_fixture()
    payload = copy.deepcopy(payload)
    if corruption == "identity":
        payload["contributions"][0]["disposition"] = "forged"
    elif corruption == "endpoint":
        payload["contributions"] = [
            r for r in payload["contributions"] if r["contribution_id"] == ref.contribution_id
        ]
    elif corruption == "source":
        inputs = inputs.model_copy(
            update=dict(
                sources=(inputs.sources[0].model_copy(update=dict(native_content_digest="d" * 64)),)
            )
        )
    elif corruption == "citation":
        payload["sources"][0]["projection"]["text"] = "!" * len(
            payload["sources"][0]["projection"]["text"]
        )
    else:
        inputs = inputs.model_copy(
            update=dict(
                passages=(
                    inputs.passages[0].model_copy(
                        update=dict(text="!" * len(inputs.passages[0].text))
                    ),
                )
            )
        )
    with pytest.raises(ValueError):
        derive_contribution_members(inputs, ref, payload)


def replay_aliases(inputs, reference, member):
    """Same physical evidence through a different execution and detached naming."""
    source = inputs.sources[0].model_copy(
        update=dict(
            run_id=901,
            cut_id=902,
            release_id="replay-release",
            result_revision=903,
            source_view_id=904,
            native_task_id=905,
        )
    )
    passage = inputs.passages[0].model_copy(
        update=dict(
            passage_id="replay-passage",
            source_ref=source.identity,
        )
    )
    changed_inputs = inputs.model_copy(update=dict(sources=(source,), passages=(passage,)))
    changed_ref = reference.model_copy(
        update=dict(
            contribution_id="source-contribution:" + "f" * 64,
            run_id=906,
            cut_id=907,
            release_id="replay-release",
            result_revision=908,
            selected_task_id=909,
            origin_task_id=910,
            runtime_fingerprint="replay-runtime",
        )
    )
    citations = tuple(
        c.model_copy(
            update=dict(
                source_ref=source.identity,
                contribution_id="source-contribution:" + str(i) * 64,
                span=c.span.model_copy(update=dict(passage_id=passage.passage_id)),
            )
        )
        for i, c in enumerate(member.contribution_citations)
    )
    changed_member = type(member).model_validate(
        {
            **member.model_dump(),
            "member_id": "replay-member",
            "contribution_ref": changed_ref,
            "relation_product_id": changed_ref.contribution_id,
            "citation": citations[0].span,
            "passage_id": passage.passage_id,
            "contribution_citations": citations,
            "computation_dependencies": (
                changed_ref.contribution_id,
                *(c.contribution_id for c in citations),
            ),
            "scope": source.identity + ":" + member.scope.split(":", 1)[-1],
        }
    )
    return changed_inputs, changed_ref, changed_member


def test_public_source_membership_identity_excludes_execution_custody_aliases():
    from corpus_structure.semantic.structural_admission import (
        structural_claim_id,
        structural_statement,
    )

    inputs, reference, payload = source_fixture()
    member = derive_contribution_members(inputs, reference, payload)[0]
    assert member.contribution_citations is not None
    original = select_dossier(
        inputs, root_id="corpus", members=(member,), contribution_predecessors=(reference,)
    )
    changed_inputs, changed_ref, changed_member = replay_aliases(inputs, reference, member)
    changed = select_dossier(
        changed_inputs,
        root_id="corpus",
        members=(changed_member,),
        contribution_predecessors=(changed_ref,),
    )
    before, after = structural_statement(original), structural_statement(changed)
    assert original.product_id != changed.product_id
    assert before == after and structural_claim_id(before) == structural_claim_id(after)
    public_member = before["dossier"]["members"][0]
    assert not {"contribution_ref", "computation_dependencies"} & public_member.keys()
    assert all(set(c) == {"source_pointer", "passage"} for c in public_member["endpoint_citations"])
    # Physical/source scope remains material after execution aliases are removed.
    moved = changed_member.model_copy(update=dict(scope=changed_member.scope + "/other-region"))
    different = select_dossier(
        changed_inputs, root_id="corpus", members=(moved,), contribution_predecessors=(changed_ref,)
    )
    assert structural_claim_id(structural_statement(different)) != structural_claim_id(before)


def test_native_source_member_replay_preserves_all_endpoint_citations(semantic_db_engine):
    """Composition parity after owned-reader boundary; no claim of custody qualification."""
    inputs, ref, payload = source_fixture()
    expected = derive_contribution_members(inputs, ref, payload)[0]
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(
            (sql / "dossier_contributions.sql").read_text(),
            execution_options={"no_parameters": True},
        )
        # Real native resolver rejects nonexistent exact origin before a report can be supplied.
        with (
            pytest.raises(Exception, match="cannot resolve exact selected origin"),
            conn.begin_nested(),
        ):
            conn.scalar(
                text("SELECT ops.resolve_retained_source_contribution(CAST(:r AS jsonb))"),
                dict(r=ref.model_dump_json()),
            )
        conn.execute(
            text("SELECT set_config('test.source_contribution_payload',:p,true)"),
            dict(p=json.dumps(payload)),
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.resolve_retained_source_contributions(refs jsonb) "
            "RETURNS TABLE(reference jsonb,contributions jsonb,sources jsonb) "
            "LANGUAGE sql STABLE AS $$ SELECT refs->0, "
            "current_setting('test.source_contribution_payload')::jsonb->'contributions', "
            "current_setting('test.source_contribution_payload')::jsonb->'sources' $$"
        )
        actual = conn.scalar(
            text("SELECT ops.dossier_contribution_member(CAST(:i AS jsonb),CAST(:r AS jsonb))"),
            dict(i=inputs.model_dump_json(), r=ref.model_dump_json()),
        )
        assert actual == expected.model_dump(mode="json", exclude_none=True)
        conn.exec_driver_sql(
            (sql / "structural_products.sql").read_text(), execution_options={"no_parameters": True}
        )
        with pytest.raises(DBAPIError, match="exact root component"), conn.begin_nested():
            conn.scalar(
                text("SELECT ops.structural_dossier(CAST(:i AS jsonb),CAST(:c AS jsonb))"),
                dict(i=inputs.model_dump_json(), c='{"root_id":"corpus","member_budget":12}'),
            )
        report = select_dossier(
            inputs, root_id="corpus", members=(expected,), contribution_predecessors=(ref,)
        )
        assert report.dossier is not None
        from corpus_structure.semantic.structural_admission import structural_statement

        conn.exec_driver_sql(
            (sql / "structural_publication.sql").read_text(),
            execution_options={"no_parameters": True},
        )
        public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:r AS jsonb),NULL)"),
            dict(r=report.model_dump_json(exclude_none=True)),
        )
        assert public == structural_statement(report)
        replay_inputs, replay_ref, replay_member = replay_aliases(inputs, ref, expected)
        replay = select_dossier(
            replay_inputs,
            root_id="corpus",
            members=(replay_member,),
            contribution_predecessors=(replay_ref,),
        )
        replay_public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:r AS jsonb),NULL)"),
            dict(r=replay.model_dump_json(exclude_none=True)),
        )
        assert replay_public == public == structural_statement(replay)
        assert len(public["dossier"]["members"][0]["endpoint_citations"]) == 2
        assert public["dossier"]["admission_scope"] == "membership_assembly_not_member_truth"
        from corpus_structure.serve.structural_products import _DOSSIER_SLICE_SQL

        page_sql = _DOSSIER_SLICE_SQL.replace(
            "SELECT body->'structural_product' report FROM ops.task_result "
            "WHERE task_id=:origin_id",
            "SELECT CAST(:report AS jsonb) report",
        ).replace("{projection}", "body")
        page = conn.scalar(
            text(page_sql), dict(report=report.model_dump_json(), offset=0, end_offset=1)
        )
        assert len(page["citations"]) == 2
        assert {c["citation"]["text"] for c in page["citations"]} == {"50", "Probability %"}


def detached_source_dossier_rows():
    from dataclasses import asdict

    from corpus_structure.methods.structural_products import derive_dossier_members
    from corpus_structure.semantic.structural_products import (
        DefinitionComponentsProduct,
        RetainedComponentRef,
        RetainedStructuralRef,
        StructuralProductReport,
        definition_component,
    )
    from corpus_structure.serve.contributions import ContributionRequest
    from corpus_structure.serve.review_bundle import ReviewSelection
    from corpus_structure.serve.structural_products import StructuralRequest

    inputs, reference, payload = source_fixture()
    member = derive_contribution_members(inputs, reference, payload)[0]
    assert member.contribution_citations is not None
    by_text = {c.span.text: c.span for c in member.contribution_citations}
    component = definition_component(
        term=by_text["Probability %"],
        content=by_text["50"],
        scope=inputs.passages[0].scope,
        interpretation="definition",
        basis="matched_cue",
        evidence=(inputs.passages[0].passage_id,),
        reason="Controlled fixture.",
    )
    predecessor = StructuralProductReport(
        kind="definition_components",
        inputs=inputs,
        definition_components=DefinitionComponentsProduct(components=(component,), stages=()),
    )
    predecessor_ref = RetainedStructuralRef(
        product_id=predecessor.product_id,
        project_id="fixture-project",
        run_id=8,
        cut_id=9,
        release_id=reference.release_id,
        result_revision=1,
        selected_task_id=71,
        origin_task_id=70,
        runtime_fingerprint="fixture-definition-runtime",
    )
    root = RetainedComponentRef(
        **predecessor_ref.model_dump(),
        operation_id="structure.definition_components",
        operation_version="5",
        component_id=component.component_id,
        dependencies=inputs.dependencies,
    )
    inputs = inputs.model_copy(
        update={"dependencies": (*inputs.dependencies, predecessor.product_id)}
    )
    structural, _ = derive_dossier_members(
        inputs,
        ((predecessor_ref, {"report": predecessor.model_dump(mode="json")}),),
        root=component,
    )
    member = derive_contribution_members(inputs, reference, payload, root=component)[0]
    report = select_dossier(
        inputs,
        root_id=root.component_id,
        root_component=root,
        members=(member, *structural),
        contribution_predecessors=(reference,),
        predecessors=(predecessor_ref,),
    )
    view = complete_native_fields(
        native_table_source(
            (
                table_cell("Probability %", 0, 1, column_header=True),
                table_cell("50", 1, 1),
            )
        )
    )
    selection = ReviewSelection(
        selections=(ContributionRequest(run_id=reference.run_id),),
        structural_selections=(
            StructuralRequest(run_id=2, kind="dossier"),
            StructuralRequest(run_id=8, kind="definition_components"),
        ),
    )
    rows = [
        (
            "selections",
            dict(
                selection_index=0,
                project_id=reference.project_id,
                run_id=reference.run_id,
                cut_id=reference.cut_id,
                binding=dict(
                    release_id=reference.release_id, data_revision=reference.result_revision
                ),
            ),
        ),
        (
            "structural_selections",
            dict(selection_index=0, run_id=2, cut_id=3, release_id=reference.release_id),
        ),
        (
            "structural_products",
            dict(
                selection_index=0,
                selected_task_id=100,
                origin_task_id=100,
                product_id=report.product_id,
                report=report.model_dump(mode="json"),
            ),
        ),
        (
            "reports",
            dict(origin_task_id=100, body=dict(structural_product=report.model_dump(mode="json"))),
        ),
        (
            "reports",
            dict(
                origin_task_id=reference.origin_task_id,
                origin_run_id=reference.run_id,
                unit_type="source_view",
                origin_unit_id=view.ref.id,
                project_id=reference.project_id,
                runtime_fingerprint=reference.runtime_fingerprint,
                body=dict(release_id=reference.release_id, contributions=payload["contributions"]),
            ),
        ),
        (
            "sources",
            dict(
                source_view_id=view.ref.id,
                ref=asdict(view.ref),
                text=view.text,
                context=view.context(),
            ),
        ),
        ("contracts", dict(release_id=reference.release_id, definitions=[], registry_rows=[])),
        (
            "structural_selections",
            dict(
                selection_index=1,
                project_id=predecessor_ref.project_id,
                run_id=predecessor_ref.run_id,
                cut_id=predecessor_ref.cut_id,
                release_id=predecessor_ref.release_id,
                binding=dict(
                    release_id=predecessor_ref.release_id,
                    data_revision=predecessor_ref.result_revision,
                ),
            ),
        ),
        (
            "structural_products",
            dict(
                selection_index=1,
                selected_task_id=71,
                origin_task_id=70,
                origin_run_id=7,
                origin_project_id="fixture-original",
                runtime_fingerprint=predecessor_ref.runtime_fingerprint,
                product_id=predecessor.product_id,
                report=predecessor.model_dump(mode="json"),
            ),
        ),
        (
            "reports",
            dict(
                origin_task_id=70,
                origin_run_id=7,
                project_id="fixture-original",
                runtime_fingerprint=predecessor_ref.runtime_fingerprint,
                body=dict(
                    release_id=predecessor_ref.release_id,
                    method=root.operation_id,
                    operation_version=root.operation_version,
                    structural_product=predecessor.model_dump(mode="json"),
                ),
            ),
        ),
    ]
    rows.extend(
        (
            "inventory",
            dict(
                selection_index=0,
                population="contribution",
                row=dict(
                    contribution_id=row["contribution_id"],
                    source_view_id=view.ref.id,
                    selected_task_id=reference.selected_task_id,
                    origin_task_id=reference.origin_task_id,
                    origin_run_id=reference.run_id,
                    origin_project_id=reference.project_id,
                    runtime_fingerprint=reference.runtime_fingerprint,
                ),
            ),
        )
        for row in payload["contributions"]
    )
    return selection, rows


def test_detached_dossier_replays_selected_raw_contribution_and_endpoint_custody(
    tmp_path, synthetic_source_projection
):
    from corpus_structure.serve.review_bundle import verify_review_bundle, write_review_bundle

    selection, rows = detached_source_dossier_rows()
    manifest = write_review_bundle(selection, tmp_path / "complete", iter(rows))
    assert verify_review_bundle(tmp_path / "complete") == manifest


@pytest.mark.parametrize(
    "corruption",
    [
        "runtime",
        "cut",
        "selected_task",
        "endpoint_inventory",
        "raw_endpoint",
        "source_pin",
        "member",
    ],
)
def test_detached_dossier_refuses_missing_or_forged_contribution_closure(
    tmp_path, corruption, synthetic_source_projection
):
    from corpus_structure.serve.review_bundle import write_review_bundle

    selection, rows = detached_source_dossier_rows()
    rows = copy.deepcopy(rows)
    if corruption == "runtime":
        rows[4][1]["runtime_fingerprint"] = "forged"
    elif corruption == "cut":
        rows[0][1]["cut_id"] += 1
    elif corruption == "selected_task":
        for name, value in rows:
            if name == "inventory":
                value["row"]["selected_task_id"] += 1
    elif corruption == "endpoint_inventory":
        rows.pop()
    elif corruption == "raw_endpoint":
        rows[4][1]["body"]["contributions"] = rows[4][1]["body"]["contributions"][:1]
    elif corruption == "source_pin":
        rows[5][1]["ref"]["native_product"]["task_id"] += 1
    else:
        value = rows[2][1]["report"]
        value["dossier"]["members"][0]["role"] = "definition"
        from corpus_structure.semantic.structural_products import DossierMember

        forged = DossierMember.model_validate(value["dossier"]["members"][0])
        inputs, reference, _ = source_fixture()
        report = select_dossier(
            inputs, root_id="corpus", members=(forged,), contribution_predecessors=(reference,)
        )
        rows[2][1]["report"] = report.model_dump(mode="json")
        rows[2][1]["product_id"] = report.product_id
        rows[3][1]["body"]["structural_product"] = report.model_dump(mode="json")
    with pytest.raises(ValueError):
        write_review_bundle(selection, tmp_path / "forged", iter(rows))


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("run_id", "1"),
        ("cut_id", 0),
        ("origin_task_id", -1),
        ("selected_task_id", True),
        ("result_revision", "1"),
        ("runtime_fingerprint", ""),
        ("contribution_id", "invented"),
    ],
)
def test_batch_and_single_resolver_reject_same_malformed_reference(
    semantic_db_engine, field, replacement
):
    """Both entry points exercise one real native owner; no substituted resolver."""
    _, reference, _ = source_fixture()
    reference = {**reference.model_dump(mode="json"), field: replacement}
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/dossier_contributions.sql"
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(sql.read_text(), execution_options={"no_parameters": True})
        for call, payload in (
            ("ops.resolve_retained_source_contribution", reference),
            ("ops.resolve_retained_source_contributions", [reference]),
        ):
            with pytest.raises(DBAPIError) as error, conn.begin_nested():
                conn.execute(
                    text("SELECT * FROM " + call + "(CAST(:r AS jsonb))"),
                    {"r": json.dumps(payload)},
                )
            assert getattr(error.value.orig, "sqlstate", None) == "23514"


def test_batch_projection_keeps_endpoint_meaning_and_private_authority(semantic_db_engine):
    """Projection-only parity is separate from custody and actual completion qualification."""
    inputs, reference, payload = source_fixture()
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/dossier_contributions.sql"
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(sql.read_text(), execution_options={"no_parameters": True})
        # The private projection cannot be called by application roles with fabricated rows.
        for role in ("corpus_sem_reader", "corpus_sem_writer"):
            for signature in (
                "ops.resolve_retained_source_contributions(jsonb)",
                "ops.dossier_contribution_member_from_retained(jsonb,jsonb,jsonb,jsonb,jsonb)",
                "ops.dossier_contribution_members(jsonb,jsonb,jsonb)",
            ):
                assert not conn.scalar(
                    text("SELECT has_function_privilege(:role,:sig,'EXECUTE')"),
                    {"role": role, "sig": signature},
                )
        actual = conn.scalar(
            text("""
            SELECT ops.dossier_contribution_member_from_retained(
                CAST(:i AS jsonb),CAST(:r AS jsonb),CAST(:rows AS jsonb),
                CAST(:sources AS jsonb),CAST(:dependencies AS jsonb))
        """),
            {
                "i": inputs.model_dump_json(),
                "r": reference.model_dump_json(),
                "rows": json.dumps(payload["contributions"]),
                "sources": json.dumps(payload["sources"]),
                "dependencies": json.dumps({reference.contribution_id: True}),
            },
        )
        assert actual["role"] == "relationship"
        assert actual["qualification"] == "proposed"
        assert "assessment_id" not in actual
        assert {c["span"]["text"] for c in actual["contribution_citations"]} == {
            "50",
            "Probability %",
        }
        assert len(actual["contribution_citations"]) == 2
        assert set(actual["computation_dependencies"]) >= {
            r["contribution_id"] for r in payload["contributions"]
        }
        assert actual == derive_contribution_members(inputs, reference, payload)[0].model_dump(
            mode="json", exclude_none=True
        )


def test_detached_source_dossier_preserves_cross_project_original_producer(
    tmp_path, synthetic_source_projection
):
    """Detached/native-contract control; ordinary valid_reuse currently stays within a project."""
    from corpus_structure.serve.review_bundle import verify_review_bundle, write_review_bundle

    selection, rows = detached_source_dossier_rows()
    raw = next(v for name, v in rows if name == "reports" and v["origin_task_id"] == 1)
    raw["project_id"] = "original-producer-project"
    raw["origin_run_id"] = 99
    for name, value in rows:
        if name == "inventory":
            value["row"]["origin_project_id"] = "original-producer-project"
            value["row"]["origin_run_id"] = 99
    # The selected completed run still belongs to p; original execution is distinct.
    assert next(v for name, v in rows if name == "selections")["project_id"] == "p"
    manifest = write_review_bundle(selection, tmp_path / "cross-project", iter(rows))
    assert verify_review_bundle(tmp_path / "cross-project") == manifest


@pytest.mark.parametrize(
    "corruption", ["selected_project", "origin_project", "origin_run", "inventory_runtime"]
)
def test_detached_source_dossier_refuses_selected_or_original_custody_substitution(
    tmp_path, corruption, synthetic_source_projection
):
    from corpus_structure.serve.review_bundle import write_review_bundle

    selection, rows = detached_source_dossier_rows()
    if corruption == "selected_project":
        next(v for name, v in rows if name == "selections")["project_id"] = "other-project"
    elif corruption == "origin_project":
        next(v for name, v in rows if name == "reports" and v["origin_task_id"] == 1)[
            "project_id"
        ] = "other-project"
    elif corruption == "origin_run":
        next(v for name, v in rows if name == "reports" and v["origin_task_id"] == 1)[
            "origin_run_id"
        ] = 99
    else:
        for name, value in rows:
            if name == "inventory":
                value["row"]["runtime_fingerprint"] = "another-runtime"
    with pytest.raises(ValueError):
        write_review_bundle(selection, tmp_path / corruption, iter(rows))
