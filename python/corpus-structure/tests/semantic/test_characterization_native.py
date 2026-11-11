"""Real protected characterization publication, exact pins and indexed memberships."""

from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import create_model
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_section_views import published_section_drafts
from corpus_structure.semantic.characterization import occurrence_id, validate_layer, validate_view
from corpus_structure.semantic.characterization_store import (
    compose_view,
    publish_layer,
    read_layer,
    read_memberships,
    read_view,
)
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.operations import claim_tasks, create_task, record_method
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.source_views import store_source_view

from .pdf_staging_support import private_build as private_build
from .test_selected_source_native import publish_selected


@pytest.fixture
def characterization_source(private_build, semantic_writer_engine, tmp_path):
    publication = publish_selected(
        semantic_writer_engine, private_build, tmp_path / "source", characterization_pages=True
    )
    base = ProductReference(private_build.task_id, "selected", publication.logical_digest)
    with semantic_writer_engine.begin() as conn:
        prepared = open_release(conn, private_build.release_id)
        task = (
            conn.execute(
                text(
                    "SELECT t.*,r.runtime_id FROM ops.task t "
                    "JOIN ops.run r ON r.id=t.run_id WHERE t.id=:id"
                ),
                {"id": private_build.task_id},
            )
            .mappings()
            .one()
        )
        reader = published_record_reader(conn, base, projection_context=prepared)
        assert reader is not None
        (draft,) = published_section_drafts(
            reader,
            document_id=task["unit_id"],
            selections=("Nested selected section",),
            membership="direct",
            scope=None,
            consumer_release=prepared.release_id,
        )
        identity = store_source_view(
            conn,
            run_id=task["run_id"],
            task_id=task["id"],
            attempt=task["attempt"],
            holder=task["claimed_by"],
            draft=draft,
            position=0,
        )
        source = (
            conn.execute(text("SELECT * FROM kb.source_view WHERE id=:id"), {"id": identity})
            .mappings()
            .one()
        )
        scope = dict(
            source_view_ids=[identity],
            source_views=[
                dict(
                    source_view_id=identity,
                    key=source["key"],
                    base_document=base.values(),
                    section_pointer=source["section_pointer"],
                    membership=source["membership"],
                    projection_digest=source["projection_digest"],
                    recipe_digest=source["recipe_digest"],
                )
            ],
            profile="test_scope",
            selectors=[dict(projection=source["projection_digest"], start=0, end=7)],
        )
    return SimpleNamespace(base=base, prepared=prepared, task=dict(task), scope=scope)


def make_task(conn, source, *, compose=False, layers=()):
    name = "text.compose_view" if compose else "native-binding"
    if compose:
        from corpus_structure.methods.characterization import ComposeViewMethod

        method = ComposeViewMethod()
    else:
        method = SimpleNamespace(
            name=name,
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("CharacterizationNativeFixture"),
        )
    params = dict(
        characterization_base_document=source.base.values(),
        characterization_source_scope=source.scope,
        characterization_layers=[p.values() for p in layers],
    )
    if compose:
        params["characterization_profile"] = "selected_layers" if layers else "source_only"
    else:
        params.update(
            model=getattr(source, "model", "native-retained"),
            grammar=getattr(source, "grammar", "no-grammar"),
            context="exact-source",
        )
    config_hash = sha256(str(params).encode()).hexdigest()
    config = record_method(conn, method, "default", params, config_hash, prepared=source.prepared)
    task = create_task(
        conn,
        run_id=source.task["run_id"],
        config_id=config,
        stage="ingest",
        unit_type="document",
        unit_id=source.task["unit_id"],
        unit_key=name,
        input_hash="fixture-input",
        fresh=True,
    )
    claim = claim_tasks(
        conn, run_id=source.task["run_id"], config_id=config, holder="characterization-fixture"
    )[0]
    return task, claim, config_hash


def layer_payload(source, config_hash) -> dict[str, Any]:
    projection = source.scope["source_views"][0]["projection_digest"]
    view = source.scope["source_view_ids"][0]
    occurrences = []
    for start in (0, 4):
        extents = [
            dict(
                projection=projection,
                source_view_id=view,
                native_pointer=f"#/texts/{1 if start == 0 else 2}",
                page=3 if start == 0 else 4,
                start=start,
                end=start + 3,
                text="x=1",
                synthetic=False,
            )
        ]
        occurrences.append(dict(local_id=occurrence_id(source.base, extents), extents=extents))
    coverage = [
        dict(
            family="syntax",
            operation="native-binding",
            eligible=source.scope["selectors"],
            examined=source.scope["selectors"],
            availability="available",
            outcome="complete",
            profile="test_scope",
        )
    ]
    return dict(
        format="characterization-layer-v1",
        base_document=source.base.values(),
        release_id=source.prepared.release_id,
        operation=dict(
            key="native-binding",
            version="1",
            runtime=source.task["runtime_id"],
            model=getattr(source, "model", "native-retained"),
            grammar=getattr(source, "grammar", "no-grammar"),
            configuration=config_hash,
            input="fixture-input",
            context="exact-source",
            produced_families=["syntax"],
            outcomes=["complete", "partial", "failed"],
            result_determinants=["retained-source"],
        ),
        source_scope=source.scope,
        outcome="complete",
        occurrences=occurrences,
        annotations=[
            dict(
                local_id=f"a{i}",
                kind="native",
                family="syntax",
                vocabulary="test",
                occurrences=[o["local_id"]],
                status="native_evidence",
                scores=[dict(scheme="native", meaning="retained score", value=source_value(-0.0))],
            )
            for i, o in enumerate(occurrences)
        ],
        memberships=[
            dict(
                local_id=f"m{i}",
                group="a0",
                member=f"a{i}",
                family="syntax",
                role="fragment",
                order=i,
                occurrences=[o["local_id"]],
                scope="document",
                structural=False,
            )
            for i, o in enumerate(occurrences)
        ],
        terms=[
            dict(
                local_id="predicate",
                kind="predicate",
                family="syntax",
                vocabulary="test",
                value="equals",
                status="interpreted",
                occurrences=[occurrences[0]["local_id"]],
                children=[dict(role="participant", target="participant", structural=True)],
            ),
            dict(
                local_id="participant",
                kind="participant",
                family="syntax",
                vocabulary="test",
                value="x",
                status="interpreted",
            ),
        ],
        roles=[
            dict(
                local_id="role",
                owner="predicate",
                member="participant",
                family="syntax",
                role="subject",
                scheme="native-test",
                occurrences=[occurrences[0]["local_id"]],
                basis=dict(
                    kind="native_prediction",
                    status="recorded",
                    native_scheme="test",
                    native_label="subject",
                ),
            )
        ],
        choices=[
            dict(
                local_id="alternatives",
                family="syntax",
                compatibility="exclusive",
                members=[dict(local_id="reading", root="predicate")],
            )
        ],
        coverage=coverage,
    )


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_publication_replay_partial_family_and_pin_read(
    characterization_source, semantic_writer_engine, semantic_reader_engine, semantic_db_engine
):
    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        wire = layer_payload(source, config_hash)
        wire["outcome"] = "partial"
        wire["operation"]["produced_families"].append("roles")
        boundary = [
            dict(
                projection=source.scope["source_views"][0]["projection_digest"],
                source_view_id=source.scope["source_view_ids"][0],
                native_pointer="#/texts/1",
                start=3,
                end=3,
                text="<boundary>",
                synthetic=True,
            )
        ]
        wire["occurrences"].append(
            dict(local_id=occurrence_id(source.base, boundary), extents=boundary)
        )
        wire["coverage"].append(
            dict(
                family="roles",
                operation="native-binding",
                eligible=source.scope["selectors"],
                availability="unavailable",
                outcome="failed",
                reason="native provider unavailable",
                profile="test_scope",
            )
        )
        wire["terms"] = [
            dict(
                local_id="predicate",
                kind="predicate",
                family="syntax",
                vocabulary="test",
                value="equals",
                status="interpreted",
                occurrences=[wire["occurrences"][0]["local_id"]],
                children=[dict(role="participant", target="participant", structural=True)],
            ),
            dict(
                local_id="participant",
                kind="participant",
                family="syntax",
                vocabulary="test",
                value="x",
                status="interpreted",
            ),
        ]
        report = validate_layer(source.prepared, wire)
        arguments = dict(
            task_id=task, attempt=claim.attempt, holder="characterization-fixture", layer=report
        )
        pin = publish_layer(conn, **arguments)
        assert publish_layer(conn, **arguments) == pin
        # Task seal is sufficient: source/run completion is intentionally unrelated.
        assert (
            conn.scalar(
                text("SELECT status FROM ops.run WHERE id=:id"), {"id": source.task["run_id"]}
            )
            != "finished"
        )
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM kb.characterization_membership WHERE task_id=:id"),
                {"id": task},
            )
            == 2
        )
    with semantic_reader_engine.connect() as conn:
        assert read_layer(conn, pin, run_id=source.task["run_id"]).content == report.content
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_layer(conn, pin, max_bytes=len(report.content) - 1)
        with pytest.raises(DBAPIError):
            read_view(conn, pin)
    # Conflicting retries and canceled holders cannot change the immutable seal.
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError), conn.begin_nested():
        altered = deepcopy(report.payload)
        altered["operation"]["context"] = "different"
        from corpus_structure.semantic._operation_calls import publish_characterization

        publish_characterization(
            conn,
            cost=None,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=altered,
            view=None,
        )


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_refuses_dangling_and_unreleased_witness_without_new_seal(
    characterization_source, semantic_writer_engine, semantic_db_engine
):
    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        wire = validate_layer(source.prepared, layer_payload(source, config_hash)).payload
        failed = deepcopy(wire)
        failed["outcome"] = "failed"
        from corpus_structure.semantic._operation_calls import publish_characterization

        with pytest.raises(DBAPIError, match="failed analysis"), conn.begin_nested():
            publish_characterization(
                conn,
                cost=None,
                task_id=task,
                attempt=claim.attempt,
                holder="characterization-fixture",
                layer=failed,
                view=None,
            )
        wire["memberships"][0]["member"] = "missing"
        from corpus_structure.semantic._operation_calls import publish_characterization

        with pytest.raises(DBAPIError), conn.begin_nested():
            publish_characterization(
                conn,
                cost=None,
                task_id=task,
                attempt=claim.attempt,
                holder="characterization-fixture",
                layer=wire,
                view=None,
            )
        assert (
            conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": task}) == "running"
        )
        for field, bad in (("native_pointer", "#/texts/2"), ("page", 999)):
            wrong = validate_layer(source.prepared, layer_payload(source, config_hash)).payload
            wrong["occurrences"][0]["extents"][0][field] = bad
            wrong["occurrences"][0]["local_id"] = occurrence_id(
                source.base, wrong["occurrences"][0]["extents"]
            )
            old = wire["occurrences"][0]["local_id"]
            for node in (*wrong["annotations"], *wrong["memberships"]):
                node["occurrences"] = [
                    wrong["occurrences"][0]["local_id"] if ref == old else ref
                    for ref in node["occurrences"]
                ]
            with pytest.raises(DBAPIError, match="occurrence differs"), conn.begin_nested():
                publish_characterization(
                    conn,
                    cost=None,
                    task_id=task,
                    attempt=claim.attempt,
                    holder="characterization-fixture",
                    layer=wrong,
                    view=None,
                )
        with pytest.raises(DBAPIError, match="task attempt lost"), conn.begin_nested():
            publish_characterization(
                conn,
                cost=None,
                task_id=task,
                attempt=claim.attempt,
                holder="canceled-holder",
                layer=wire,
                view=None,
            )
        wire = validate_layer(source.prepared, layer_payload(source, config_hash)).payload
        wire["roles"] = [
            dict(
                local_id="r",
                owner="a0",
                member="a1",
                family="syntax",
                role="actor",
                scheme="test",
                basis=dict(
                    kind="released_construction",
                    status="witnessed",
                    rule_id="invented",
                    premises=["a0"],
                ),
            )
        ]
        with pytest.raises(DBAPIError), conn.begin_nested():
            publish_characterization(
                conn,
                cost=None,
                task_id=task,
                attempt=claim.attempt,
                holder="characterization-fixture",
                layer=wire,
                view=None,
            )

    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.characterization_product WHERE task_id=:id"),
                {"id": task},
            )
            == 0
        )


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_composition_source_only_and_indexed_keyset_pages(
    characterization_source, semantic_writer_engine, semantic_reader_engine
):
    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        layer = validate_layer(source.prepared, layer_payload(source, config_hash))
        layer_pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=layer,
        )
        view = validate_view(
            source.prepared,
            dict(
                format="enriched-document-view-v1",
                base_document=source.base.values(),
                release_id=source.prepared.release_id,
                source_scope=source.scope,
                layers=[layer_pin.values()],
                profile="selected_layers",
                coverage=layer.payload["coverage"],
            ),
            {layer_pin: layer},
        )
        view_task, view_claim, view_config_hash = make_task(
            conn, source, compose=True, layers=(layer_pin,)
        )
        from corpus_structure.core.method import UnitRef, UnitResult
        from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
        from corpus_structure.methods.characterization import ComposeViewMethod
        from corpus_structure.semantic.operations import complete_unit_result

        receipt = complete_unit_result(
            conn,
            task_id=view_task,
            attempt=view_claim.attempt,
            holder="characterization-fixture",
            prepared=source.prepared,
            result=UnitResult(
                ref=UnitRef(TaskUnitType.DOCUMENT, source.task["unit_id"], "text.compose_view"),
                outcome=ObservationOutcome.PRODUCED,
                characterization_view=view,
            ),
            method=ComposeViewMethod(),
            configuration_hash=view_config_hash,
            source="native-fixture",
        )
        assert receipt.receipt.protocol == "done"
        view_pin = view.reference(view_task)
        weak = validate_view(
            source.prepared,
            dict(
                format="enriched-document-view-v1",
                base_document=source.base.values(),
                release_id=source.prepared.release_id,
                source_scope=source.scope,
                profile="source_only",
            ),
            {},
        )
        weak_task, weak_claim, _ = make_task(conn, source, compose=True)
        weak_pin = compose_view(
            conn,
            task_id=weak_task,
            attempt=weak_claim.attempt,
            holder="characterization-fixture",
            view=weak,
        )
    with semantic_reader_engine.connect() as conn:
        assert read_view(conn, weak_pin).payload["layers"] == []
        # Book-wide metadata has a separate finite bound from natural-unit layers.
        assert read_view(conn, view_pin, max_bytes=64 * 1024**2).content == view.content
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_view(conn, view_pin, max_bytes=64 * 1024**2 + 1)
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_layer(conn, layer_pin, max_bytes=8 * 1024**2 + 1)
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(
                text("SELECT ops.read_characterization_product(:t,:k,:d,'view',NULL,NULL)"),
                dict(t=view_pin.task_id, k=view_pin.product_key, d=view_pin.content_digest),
            )
        first = read_memberships(conn, view_pin, ("a0",), limit=1)
        assert [row["membership"]["local_id"] for row in first["memberships"]] == ["m0"]
        second = read_memberships(
            conn, view_pin, ("a0",), limit=1, after=tuple(first["next_after"])
        )
        assert [row["membership"]["local_id"] for row in second["memberships"]] == ["m1"]
        assert second["next_after"] is None
        assert second["memberships"][0]["occurrences"][0]["extents"][0]["start"] == 4
        from corpus_structure.semantic.characterization_store import read_nodes

        nodes = read_nodes(conn, view_pin, "annotations", selectors={"family": "syntax"}, limit=1)
        assert nodes["nodes"][0]["node"]["local_id"] == "a0"
        remainder = read_nodes(
            conn,
            view_pin,
            "annotations",
            selectors={"family": "syntax"},
            after=tuple(nodes["next_after"]),
            limit=1,
        )
        assert [r["node"]["local_id"] for r in remainder["nodes"]] == ["a1"]
        assert remainder["next_after"] is None
        term_nodes = read_nodes(conn, view_pin, "terms", selectors={"local_id": "predicate"})[
            "nodes"
        ]
        assert len(term_nodes) == 1
        assert term_nodes[0]["node"]["children"][0]["target"] == "participant"
        assert term_nodes[0]["roles"][0]["local_id"] == "role"
        assert term_nodes[0]["choices"][0]["members"][0]["local_id"] == "reading"
        assert read_nodes(conn, view_pin, "annotations", selectors={"page": 999})["nodes"] == []
        on_page = read_nodes(conn, view_pin, "annotations", selectors={"page": 3})["nodes"]
        assert [row["node"]["local_id"] for row in on_page] == ["a0"]
        from corpus_structure.serve.characterization import (
            CharacterizationRequest,
            inspect_characterization,
        )

        cross_page = inspect_characterization(
            conn,
            CharacterizationRequest(
                run_id=source.task["run_id"],
                **view_pin.values(),
                view="membership",
                annotation_id="a0",
                page=3,
            ),
        )
        assert [
            (row["membership"]["local_id"], row["outside_selection"]) for row in cross_page.items
        ] == [("m0", False), ("m1", True)]
        assert cross_page.items[1]["occurrences"][0]["extents"][0]["page"] == 4
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_layer(conn, layer_pin, max_bytes=1)
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_memberships(conn, view_pin, ("a0",), max_bytes=1)


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_document_view_can_combine_metadata_beyond_one_layer_budget(
    characterization_source, semantic_writer_engine, semantic_reader_engine
):
    source = characterization_source
    layers = {}
    with semantic_writer_engine.begin() as conn:
        for index in range(2):
            selected = SimpleNamespace(**{**vars(source), "model": f"capacity-{index}"})
            task, claim, config_hash = make_task(conn, selected)
            payload = layer_payload(selected, config_hash)
            payload["coverage"][0]["reason"] = str(index) * (5 * 1024**2)
            layer = validate_layer(source.prepared, payload)
            assert len(layer.content) < 8 * 1024**2
            pin = publish_layer(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="characterization-fixture",
                layer=layer,
            )
            layers[pin] = layer
        view = validate_view(
            source.prepared,
            dict(
                format="enriched-document-view-v1",
                base_document=source.base.values(),
                release_id=source.prepared.release_id,
                source_scope=source.scope,
                layers=[pin.values() for pin in layers],
                profile="selected_layers",
                coverage=[row for layer in layers.values() for row in layer.payload["coverage"]],
            ),
            layers,
        )
        assert 8 * 1024**2 < len(view.content) < 64 * 1024**2
        task, claim, _ = make_task(conn, source, compose=True, layers=tuple(layers))
        pin = compose_view(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            view=view,
        )
    with semantic_reader_engine.connect() as conn:
        assert read_view(conn, pin).content == view.content
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_view(conn, pin, max_bytes=8 * 1024**2)


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_capture_detached_characterization_closure_while_run_unfinished(
    characterization_source,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
):
    """Real reader snapshot capture; public detached verify/inspect dispatch, no NLP."""
    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.serve.characterization import CharacterizationRequest
    from corpus_structure.serve.characterization_replay import (
        CharacterizationReviewSelection,
        capture_characterization_review,
        inspect_characterization_review,
    )
    from corpus_structure.serve.review_bundle import inspect_review_bundle, verify_review_bundle

    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        layer = validate_layer(source.prepared, layer_payload(source, config_hash))
        layer_pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=layer,
        )
        view = validate_view(
            source.prepared,
            dict(
                format="enriched-document-view-v1",
                base_document=source.base.values(),
                release_id=source.prepared.release_id,
                source_scope=source.scope,
                layers=[layer_pin.values()],
                profile="selected_layers",
                coverage=layer.payload["coverage"],
            ),
            {layer_pin: layer},
        )
        view_task, view_claim, _ = make_task(conn, source, compose=True, layers=(layer_pin,))
        view_pin = compose_view(
            conn,
            task_id=view_task,
            attempt=view_claim.attempt,
            holder="characterization-fixture",
            view=view,
        )
        assert (
            conn.scalar(
                text("SELECT status FROM ops.run WHERE id=:id"), {"id": source.task["run_id"]}
            )
            != "finished"
        )
    selection = CharacterizationReviewSelection(run_id=source.task["run_id"], **view_pin.values())
    destination = tmp_path / "detached-review"
    destination.mkdir()
    cancellation = OperationCancellation()
    with read_snapshot(semantic_reader_engine, cancellation=cancellation.postgresql) as conn:
        captured = capture_characterization_review(conn, selection, destination, cancellation)
    assert verify_review_bundle(destination) == captured
    assert inspect_review_bundle(destination)["layers"] == 1
    response = inspect_characterization_review(
        destination,
        CharacterizationRequest(
            run_id=source.task["run_id"], **view_pin.values(), view="membership", annotation_id="a0"
        ),
    )
    assert len(response.items) == 2
    assert response.membership_scope == "complete_recorded_members"
    page_response = inspect_characterization_review(
        destination,
        CharacterizationRequest(
            run_id=source.task["run_id"],
            **view_pin.values(),
            view="membership",
            annotation_id="a0",
            page=3,
        ),
    )
    assert [
        (row["membership"]["local_id"], row["outside_selection"]) for row in page_response.items
    ] == [("m0", False), ("m1", True)]
    assert (
        response.model_dump(mode="json")["items"][1]["occurrences"][0]["extents"][0]["start"] == 4
    )

    from corpus_structure.serve.characterization import inspect_characterization

    for mode in ("annotations", "membership"):
        request = CharacterizationRequest(
            run_id=source.task["run_id"],
            **view_pin.values(),
            view=mode,
            annotation_id="a0" if mode == "membership" else None,
            limit=1,
        )
        with read_snapshot(semantic_reader_engine) as conn:
            live = inspect_characterization(conn, request)
        detached = inspect_characterization_review(destination, request)
        assert detached.model_dump(mode="json") == live.model_dump(mode="json")
        assert detached.source_items
        assert detached.continuation is not None
        following = request.model_copy(update={"cursor": detached.continuation})
        with read_snapshot(semantic_reader_engine) as conn:
            live_following = inspect_characterization(conn, following)
        assert inspect_characterization_review(destination, following).model_dump(
            mode="json"
        ) == live_following.model_dump(mode="json")


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_factorized_diamond_dag_and_real_cycle_refusal(
    characterization_source, semantic_writer_engine, semantic_reader_engine, semantic_db_engine
):
    source = characterization_source
    stages = 24
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        wire = layer_payload(source, config_hash)
        # The expected graph is authored directly. It has shared joins rather than
        # enumerated derivation paths, and no timing assertion is involved.
        for index in range(stages):
            wire["terms"].append(
                dict(
                    local_id=f"d{index}",
                    kind="operator",
                    family="syntax",
                    vocabulary="test",
                    value="scope",
                    status="interpreted",
                    children=[
                        dict(role="left", target=f"l{index}", structural=True),
                        dict(role="right", target=f"r{index}", structural=True),
                    ],
                )
            )
            for branch in ("l", "r"):
                wire["terms"].append(
                    dict(
                        local_id=f"{branch}{index}",
                        kind="operator",
                        family="syntax",
                        vocabulary="test",
                        value="scope",
                        status="interpreted",
                        children=[dict(role="body", target=f"d{index + 1}", structural=True)],
                    )
                )
        wire["terms"].append(
            dict(
                local_id=f"d{stages}",
                kind="participant",
                family="syntax",
                vocabulary="test",
                value="leaf",
                status="interpreted",
            )
        )
        report = validate_layer(source.prepared, wire)
        pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=report,
        )
        invalid_task, invalid_claim, _ = make_task(conn, source)
        cyclic = deepcopy(report.payload)
        cyclic["terms"][-1]["children"] = [dict(role="back", target="d0", structural=True)]
        from corpus_structure.semantic._operation_calls import publish_characterization

        with (
            pytest.raises(DBAPIError, match="structural characterization dependency cycle"),
            conn.begin_nested(),
        ):
            publish_characterization(
                conn,
                cost=None,
                task_id=invalid_task,
                attempt=invalid_claim.attempt,
                holder="characterization-fixture",
                layer=cyclic,
                view=None,
            )
    with semantic_reader_engine.connect() as conn:
        assert len(read_layer(conn, pin).payload["terms"]) == 3 * stages + 3
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM kb.characterization_term_edge WHERE task_id=:id"),
                {"id": task},
            )
            == 4 * stages + 1
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.characterization_product WHERE task_id=:id"),
                {"id": invalid_task},
            )
            == 0
        )


@pytest.mark.parametrize("private_build", ["characterization_finalizable_pdf"], indirect=True)
def test_native_new_rule_release_reuses_original_native_layer_and_detached_contract(
    characterization_source,
    semantic_writer_engine,
    semantic_reader_engine,
    semantic_db_engine,
    tmp_path,
):
    import json
    from pathlib import Path

    import yaml

    from corpus_structure.orchestrate.commands import finalize_bound_run, start_bound_run
    from corpus_structure.semantic._operation_calls import select_source_view
    from corpus_structure.semantic._operation_ids import RunId, SourceViewId
    from corpus_structure.semantic.operations import OperationBinding, complete_task, create_run

    from .operation_scenario_support import prepare_operation_scenario

    old = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, old)
        old_body = layer_payload(old, config_hash)
        old_body.update(roles=[], terms=[], choices=[])
        old_body["annotations"][0].update(
            native_scheme="parser-v1",
            native_label="nsubj",
            provenance=["original-native-invocation"],
        )
        original = validate_layer(old.prepared, old_body)
        original_pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=original,
        )
        # Capture the exact original view before completion so the public source
        # runner must recover its completed R1 custody rather than recreate it in R2.
        original_view = validate_view(
            old.prepared,
            dict(
                format="enriched-document-view-v1",
                base_document=old.base.values(),
                release_id=old.prepared.release_id,
                source_scope=old.scope,
                layers=[original_pin.values()],
                profile="selected_layers",
                coverage=original.payload["coverage"],
            ),
            {original_pin: original},
        )
        original_view_task, original_view_claim, _ = make_task(
            conn, old, compose=True, layers=(original_pin,)
        )
        original_view_pin = compose_view(
            conn,
            task_id=original_view_task,
            attempt=original_view_claim.attempt,
            holder="characterization-fixture",
            view=original_view,
        )
        complete_task(
            conn,
            task_id=old.task["id"],
            attempt=old.task["attempt"],
            holder=old.task["claimed_by"],
            prepared=old.prepared,
            observations=[],
            outcome="empty",
            error=None,
        )
    finalize_bound_run(semantic_writer_engine, old.task["run_id"], "characterization-old-source")

    model_path = (
        Path(__file__).parents[2] / "src/corpus_structure/model/semantic/characterization.yaml"
    )
    declaration = yaml.safe_load(model_path.read_bytes())
    declaration["classes"]["ToyRuleUsingRetainedNative"] = dict(
        is_a="CharacterizationConstructionBasis",
        attributes=dict(
            rule_id=dict(required=True, equals_string="toy:retained-native-v1"),
            external_premises=dict(
                range="CharacterizationQualifiedReference",
                inlined=True,
                multivalued=True,
                required=True,
                minimum_cardinality=1,
            ),
        ),
    )
    current = prepare_operation_scenario(
        semantic_db_engine,
        observations=True,
        characterization=True,
        characterization_model=yaml.safe_dump(declaration).encode(),
        realization_id="z-new-rule",
    )
    assert current.release_id != old.prepared.release_id
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(current.release_id, "z-new-rule", 0, b"{}"),
            kind="full",
            options={},
            code_commit="characterization-new-rule",
        )
        select_source_view(
            conn,
            run_id=RunId(run),
            source_run_id=RunId(old.task["run_id"]),
            source_view_id=SourceViewId(old.scope["source_view_ids"][0]),
            projection_context=current,
        )
        runtime = conn.scalar(text("SELECT runtime_id FROM ops.run WHERE id=:id"), {"id": run})
        newer = SimpleNamespace(
            base=old.base,
            prepared=current,
            scope=old.scope,
            task={**old.task, "run_id": run, "runtime_id": runtime},
            grammar="toy:retained-native-v1",
            model="retained-native-no-new-inference",
        )
        semantic_task, semantic_claim, semantic_hash = make_task(
            conn, newer, layers=(original_pin,)
        )
        reader = published_record_reader(conn, old.base, projection_context=current)
        assert reader is not None
        (draft,) = published_section_drafts(
            reader,
            document_id=old.task["unit_id"],
            selections=("Nested selected section",),
            membership="direct",
            scope=None,
            consumer_release=current.release_id,
        )
        # This R2 invocation owns the same retained original bytes before it
        # publishes a new projection; selecting the R1 view alone is not custody
        # for publishing another source view under this task.
        from corpus_structure.semantic.pdf_contracts import store_pdf_original

        original_bytes = (tmp_path / "source.pdf").read_bytes()
        assert sha256(original_bytes).hexdigest() == reader.revision["source_digest"]
        assert draft.document_id == newer.task["unit_id"]
        store_pdf_original(
            conn,
            task_id=semantic_task,
            attempt=semantic_claim.attempt,
            holder="characterization-fixture",
            original=original_bytes,
            recipe_bytes=b'{"recipe":"retained-source-view-fixture"}',
        )
        duplicate_id = store_source_view(
            conn,
            run_id=run,
            task_id=semantic_task,
            attempt=semantic_claim.attempt,
            holder="characterization-fixture",
            draft=draft,
            position=1,
        )
        duplicate = (
            conn.execute(text("SELECT * FROM kb.source_view WHERE id=:id"), {"id": duplicate_id})
            .mappings()
            .one()
        )
        original_source = old.scope["source_views"][0]
        assert duplicate_id != original_source["source_view_id"]
        assert duplicate["key"] != original_source["key"]
        assert duplicate["projection_digest"] == original_source["projection_digest"]
        assert duplicate["recipe_digest"] == original_source["recipe_digest"]
        duplicate_scope = dict(
            old.scope,
            source_view_ids=[original_source["source_view_id"], duplicate_id],
            source_views=[
                original_source,
                dict(
                    source_view_id=duplicate_id,
                    key=duplicate["key"],
                    base_document=old.base.values(),
                    section_pointer=duplicate["section_pointer"],
                    membership=duplicate["membership"],
                    projection_digest=duplicate["projection_digest"],
                    recipe_digest=duplicate["recipe_digest"],
                ),
            ],
        )
        # One selector names the shared projection; native admission must validate
        # both distinct matching views rather than require a unique digest match.
        duplicate_owner = SimpleNamespace(**{**vars(newer), "scope": duplicate_scope})
        complete_task(
            conn,
            task_id=semantic_task,
            attempt=semantic_claim.attempt,
            holder="characterization-fixture",
            prepared=current,
            observations=[],
            outcome="empty",
            error=None,
        )
        semantic_task, semantic_claim, semantic_hash = make_task(
            conn, duplicate_owner, layers=(original_pin,)
        )
        body = layer_payload(duplicate_owner, semantic_hash)
        body.update(
            dependencies=[original_pin.values()], annotations=[], memberships=[], choices=[]
        )
        body["operation"]["required_layers"] = [original_pin.values()]
        body["operation"]["produced_families"] = ["construction"]
        body["coverage"][0]["family"] = "construction"
        for term in body["terms"]:
            term["family"] = "construction"
        body["roles"] = [
            dict(
                local_id="new-witness",
                owner="predicate",
                member="participant",
                family="construction",
                role="subject",
                scheme="toy",
                basis=dict(
                    kind="released_construction",
                    status="witnessed",
                    rule_id="toy:retained-native-v1",
                    external_premises=[dict(layer=original_pin.values(), local_id="a0")],
                ),
            )
        ]
        semantic = validate_layer(
            current,
            body,
            dependencies={original_pin: original},
            releases={old.prepared.release_id: old.prepared},
        )
        from corpus_structure.semantic._operation_calls import publish_characterization

        bad = deepcopy(body)
        bad["format"] = "characterization-layer-v2"
        with pytest.raises(DBAPIError), conn.begin_nested():
            publish_characterization(
                conn,
                cost=None,
                task_id=semantic_task,
                attempt=semantic_claim.attempt,
                holder="characterization-fixture",
                layer=bad,
                view=None,
            )
        bad = deepcopy(body)
        bad["base_document"]["content_digest"] = "0" * 64
        with pytest.raises(DBAPIError), conn.begin_nested():
            publish_characterization(
                conn,
                cost=None,
                task_id=semantic_task,
                attempt=semantic_claim.attempt,
                holder="characterization-fixture",
                layer=bad,
                view=None,
            )
        semantic_pin = publish_layer(
            conn,
            task_id=semantic_task,
            attempt=semantic_claim.attempt,
            holder="characterization-fixture",
            layer=semantic,
        )
        view = validate_view(
            current,
            dict(
                format="enriched-document-view-v1",
                base_document=old.base.values(),
                release_id=current.release_id,
                source_scope=duplicate_scope,
                layers=[original_pin.values(), semantic_pin.values()],
                profile="selected_layers",
                coverage=[*original.payload["coverage"], *semantic.payload["coverage"]],
            ),
            {original_pin: original, semantic_pin: semantic},
            releases={old.prepared.release_id: old.prepared},
        )
        view_task, view_claim, _ = make_task(
            conn, duplicate_owner, compose=True, layers=(original_pin, semantic_pin)
        )
        view_pin = compose_view(
            conn,
            task_id=view_task,
            attempt=view_claim.attempt,
            holder="characterization-fixture",
            view=view,
        )
        assert read_layer(conn, original_pin, run_id=run).content == original.content
        assert (
            read_layer(conn, original_pin).payload["operation"]["runtime"] == old.task["runtime_id"]
        )
        assert read_layer(conn, semantic_pin).payload["release_id"] == current.release_id
        assert (
            conn.scalar(text("SELECT status FROM ops.run WHERE id=:id"), {"id": run}) != "finished"
        )

    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.serve.characterization import CharacterizationRequest
    from corpus_structure.serve.characterization_replay import (
        CharacterizationReviewSelection,
        capture_characterization_review,
        inspect_characterization_review,
    )
    from corpus_structure.serve.review_bundle import verify_review_bundle

    cancellation = OperationCancellation()
    destination = tmp_path / "cross-release-review"
    destination.mkdir()
    with read_snapshot(semantic_reader_engine, cancellation=cancellation.postgresql) as conn:
        capture_characterization_review(
            conn,
            CharacterizationReviewSelection(run_id=run, **view_pin.values()),
            destination,
            cancellation,
        )
    verify_review_bundle(destination)
    response = inspect_characterization_review(
        destination,
        CharacterizationRequest(
            run_id=run,
            **view_pin.values(),
            view="terms",
            layer_key=semantic_pin.product_key,
            annotation_id="predicate",
        ),
    )
    assert response.items[0]["roles"][0]["basis"]["rule_id"] == "toy:retained-native-v1"
    with semantic_reader_engine.connect() as conn:
        assert read_layer(conn, original_pin).content == original.content

    from corpus_structure.core.method import Digest, MethodSettings, Resources, UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, Stage, TaskUnitType
    from corpus_structure.methods.characterization import ComposeViewMethod
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
    from corpus_structure.orchestrate.runner import Graph, Step
    from corpus_structure.semantic.characterization_store import read_inventory

    calls = []

    class RetainedSourceConsumer:
        name = "native-binding"
        version = "cross-release-consumer-1"
        family = "ingest"
        tier = "deterministic"
        confidence_source = None
        unit_type = TaskUnitType.SOURCE_VIEW
        resources = Resources()
        Config = create_model(
            "ExactRetainedSourceConsumer", characterization_layers=(tuple[dict, ...], ())
        )

        def select(self, run, cfg):
            assert tuple(ProductReference(**value) for value in cfg.characterization_layers) == (
                original_pin,
            )
            selected = run.reader.source_views()
            assert tuple(source.id for source in selected) == tuple(old.scope["source_view_ids"])
            assert selected[0].key == old.scope["source_views"][0]["key"]
            return tuple(
                UnitRef(TaskUnitType.SOURCE_VIEW, source.id, source.key) for source in selected
            )

        def input_digest(self, unit, cfg):
            return Digest(str((unit.ref, cfg.characterization_layers)).encode())

        def run(self, units, cfg, ctx):
            for unit in units:
                assert unit.ref.unit_id == old.scope["source_view_ids"][0]
                source = ctx.reader.source_view(unit.ref.unit_id)
                assert source.ref.native_product == old.base
                retained = ctx.reader.characterization_layers((original_pin,))
                assert retained[original_pin].content == original.content
                assert retained[original_pin].payload["release_id"] == old.prepared.release_id
                calls.append(unit.ref.unit_id)
            return tuple(
                UnitResult(ref=unit.ref, outcome=ObservationOutcome.EMPTY) for unit in units
            )

    pack = tmp_path / "consumer-pack" / "retained"
    pack.mkdir(parents=True)
    (pack / "guideline.md").write_text("Consume the exact selected retained source.\n")
    with semantic_writer_engine.connect() as conn:
        before_views = conn.scalar(text("SELECT count(*) FROM kb.source_view"))
    result = start_bound_run(
        semantic_writer_engine,
        release_id=current.release_id,
        realization_id="z-new-rule",
        project_id="p",
        domain="retained",
        domains=pack.parent,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        characterization_views=(original_view_pin,),
        registry_for=lambda _: MethodRegistry(
            (RetainedSourceConsumer(), ComposeViewMethod()),
            MethodsFile(
                configs={
                    "text.compose_view": {
                        "default": dict(
                            characterization_base_document=old.base.values(),
                            characterization_source_scope=old.scope,
                            characterization_profile="selected_layers",
                        )
                    }
                }
            ),
        ),
        graph=Graph(
            (
                (Stage.INGEST, (Step("ingest.pdf/default"),)),
                (Stage.EXTRACT, (Step("enrich.pdf_math/default"), Step("native-binding/default"))),
                (Stage.NORMALIZE, (Step("text.compose_view/default"),)),
            ),
            policy_propose=False,
        ),
    )
    assert result.status == "source_ready"
    assert calls == old.scope["source_view_ids"]
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM kb.source_view")) == before_views
        producer_run = (
            conn.execute(
                text("SELECT status,sealed,dependencies FROM ops.run WHERE id=:id"),
                {"id": result.run_id},
            )
            .mappings()
            .one()
        )
        assert producer_run["status"] != "finished" and not producer_run["sealed"]
        frozen = json.loads(producer_run["dependencies"])
        (selected_source,) = frozen["selected_sources"]
        assert selected_source["source_view_id"] == old.scope["source_view_ids"][0]
        assert selected_source["run_id"] == old.task["run_id"]
        assert selected_source["release_id"] == old.prepared.release_id
        assert (
            conn.execute(
                text("SELECT source_view_id FROM ops.run_source_view WHERE run_id=:run"),
                {"run": result.run_id},
            )
            .scalars()
            .all()
            == old.scope["source_view_ids"]
        )

        (produced_view,) = [
            row for row in read_inventory(conn, result.run_id)["products"] if row["kind"] == "view"
        ]
        unfinished_view_pin = ProductReference(**produced_view["reference"])
        assert read_view(conn, unfinished_view_pin).payload["release_id"] == current.release_id
    # This is the usual explicit-enrichment port: its producing run has selected
    # original sources but has not been finalized. Custody comes from its frozen
    # dependency manifest, not a fictitious completed result for that run.
    rebound = start_bound_run(
        semantic_writer_engine,
        release_id=current.release_id,
        realization_id="z-new-rule",
        project_id="p",
        domain="retained",
        domains=pack.parent,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        characterization_views=(unfinished_view_pin,),
        fresh=("native-binding",),
        registry_for=lambda _: MethodRegistry((RetainedSourceConsumer(),), MethodsFile()),
        graph=Graph(((Stage.EXTRACT, (Step("native-binding/default"),)),), policy_propose=False),
    )
    assert rebound.status == "source_ready"
    assert calls == old.scope["source_view_ids"] * 2
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM kb.source_view")) == before_views
        rebound_manifest = json.loads(
            conn.scalar(
                text("SELECT dependencies FROM ops.run WHERE id=:id"), {"id": rebound.run_id}
            )
        )
        assert rebound_manifest["selected_sources"] == frozen["selected_sources"]
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.completed_result WHERE run_id=:id"),
                {"id": result.run_id},
            )
            == 0
        )


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_joint_layer_and_view_completion_uses_producing_layer(
    characterization_source, semantic_writer_engine, semantic_reader_engine
):
    from pydantic import create_model

    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.semantic.operations import OperationDescriptor, complete_unit_result

    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        layer = validate_layer(source.prepared, layer_payload(source, config_hash))
        layer_pin = layer.reference(task)
        view = validate_view(
            source.prepared,
            dict(
                format="enriched-document-view-v1",
                base_document=source.base.values(),
                release_id=source.prepared.release_id,
                source_scope=source.scope,
                layers=[layer_pin.values()],
                profile="selected_layers",
                coverage=layer.payload["coverage"],
            ),
            {layer_pin: layer},
        )
        complete_unit_result(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            prepared=source.prepared,
            result=UnitResult(
                ref=UnitRef(TaskUnitType.DOCUMENT, source.task["unit_id"], "native-binding"),
                outcome=ObservationOutcome.PRODUCED,
                characterization_layer=layer,
                characterization_view=view,
            ),
            method=OperationDescriptor(
                "native-binding",
                "1",
                "ingest",
                "deterministic",
                TaskUnitType.DOCUMENT,
                create_model("JointCharacterizationFixture"),
            ),
            configuration_hash=config_hash,
            source="native-fixture",
        )
    with semantic_reader_engine.connect() as conn:
        assert read_layer(conn, layer_pin).content == layer.content
        assert read_view(conn, view.reference(task)).content == view.content


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_evidence_mutations_refuse_without_sealing(
    characterization_source, semantic_writer_engine, semantic_db_engine
):
    from corpus_structure.semantic._operation_calls import publish_characterization

    from .test_characterization_evidence import EVIDENCE_MUTATIONS, evidence_rows, mutate_evidence

    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        body = layer_payload(source, config_hash)
        evidence = evidence_rows(body["occurrences"])
        for annotation in evidence["annotations"]:
            if annotation["local_id"] in {"container", "symbol", "formal-token"}:
                annotation["occurrences"] = [body["occurrences"][0]["local_id"]]
        body["native_runs"] = evidence["native_runs"]
        body["annotations"].extend(evidence["annotations"])
        valid = validate_layer(source.prepared, body)
    for mutation in EVIDENCE_MUTATIONS:
        with semantic_writer_engine.begin() as conn:
            invalid = deepcopy(valid.payload)
            mutate_evidence(invalid, mutation)
            with pytest.raises(DBAPIError), conn.begin_nested():
                publish_characterization(
                    conn,
                    task_id=task,
                    attempt=claim.attempt,
                    holder="characterization-fixture",
                    layer=invalid,
                    view=None,
                    cost=None,
                )
            assert (
                conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": task})
                == "running"
            )
        with semantic_db_engine.connect() as owner:
            assert (
                owner.scalar(
                    text("SELECT count(*) FROM ops.characterization_product WHERE task_id=:id"),
                    {"id": task},
                )
                == 0
            )
    with semantic_writer_engine.begin() as conn:
        pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=valid,
        )
        assert read_layer(conn, pin).content == valid.content


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_witness_source_and_choice_conservation(
    characterization_source, semantic_writer_engine
):
    from corpus_structure.semantic._operation_calls import publish_characterization

    from .test_characterization_evidence import SUPPORT_MUTATIONS, mutate_witness, witness_rows

    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        body = witness_rows(layer_payload(source, config_hash))
        for annotation in body["annotations"]:
            if annotation["local_id"] in {"construction", "production"}:
                annotation["occurrences"] = [body["occurrences"][0]["local_id"]]
        valid = validate_layer(source.prepared, body)
        for mutation in SUPPORT_MUTATIONS:
            invalid = deepcopy(valid.payload)
            mutate_witness(invalid, mutation)
            with pytest.raises(DBAPIError, match="attachment"), conn.begin_nested():
                publish_characterization(
                    conn,
                    task_id=task,
                    attempt=claim.attempt,
                    holder="characterization-fixture",
                    layer=invalid,
                    view=None,
                    cost=None,
                )
            assert (
                conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": task})
                == "running"
            )
        pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=valid,
        )
        assert read_layer(conn, pin).content == valid.content


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_structural_token_span_preserves_retained_population(
    characterization_source, semantic_writer_engine, semantic_db_engine
):
    from corpus_structure.semantic.identity import canonical_bytes

    from .test_characterization_evidence import evidence_rows

    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        body = layer_payload(source, config_hash)
        evidence = evidence_rows(body["occurrences"])
        for annotation in evidence["annotations"]:
            if annotation["local_id"] in {"container", "symbol", "formal-token"}:
                annotation["occurrences"] = [body["occurrences"][0]["local_id"]]
        body["native_runs"] = evidence["native_runs"]
        body["annotations"].extend(evidence["annotations"])
        second = deepcopy(
            next(row for row in evidence["annotations"] if row["local_id"] == "token")
        )
        first = next(row for row in body["annotations"] if row["local_id"] == "token")
        first["occurrences"] = [body["occurrences"][0]["local_id"]]
        second.update(local_id="second-token", occurrences=[body["occurrences"][1]["local_id"]])
        second["native_token"]["index"] = 1
        body["annotations"].append(second)
        report = validate_layer(source.prepared, body)
        pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=report,
        )
    with semantic_db_engine.begin() as conn:
        retained = conn.scalar(
            text("SELECT payload FROM ops.characterization_product WHERE task_id=:task"),
            {"task": task},
        )
        layers = {canonical_bytes(pin.values()).decode(): retained}
        refs = [dict(layer=pin.values(), local_id=key) for key in ("token", "second-token")]
        statement = text(
            "SELECT ops.primary_structural_token_span("
            "CAST(:layers AS jsonb),CAST(:refs AS jsonb),v) "
            "FROM kb.source_view v WHERE id=:view"
        )
        values = dict(
            layers=canonical_bytes(layers).decode(),
            refs=canonical_bytes(refs).decode(),
            view=source.scope["source_view_ids"][0],
        )
        assert conn.scalar(statement, values) == [0, 7]
        for invalid in (
            list(reversed(refs)),
            [refs[0], refs[0]],
            [dict(layer=dict(pin.values(), content_digest="0" * 64), local_id="token")],
        ):
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.scalar(statement, dict(values, refs=canonical_bytes(invalid).decode()))


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_characterization_completion_retains_exact_cost_and_fences_replay(
    characterization_source, semantic_writer_engine
):
    import json

    from corpus_structure.core._model.shapes import Cost
    from corpus_structure.core.method import UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.semantic._operation_ids import TaskId
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operations import prepare_unit_completion

    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, configuration = make_task(conn, source)
        report = validate_layer(source.prepared, layer_payload(source, configuration))
        cost = Cost(wall_ms=17, tokens_in=13, tokens_out=5, model="retained-provider")
        result = UnitResult(
            ref=UnitRef(TaskUnitType.DOCUMENT, source.task["unit_id"], "native-binding"),
            outcome=ObservationOutcome.PRODUCED,
            characterization_layer=report,
            cost=cost,
        )
        method: Any = SimpleNamespace(name="native-binding", version="1")
        completion = prepare_unit_completion(
            conn,
            task_id=TaskId(task),
            attempt=claim.attempt,
            holder="characterization-fixture",
            prepared=source.prepared,
            result=result,
            method=method,
            configuration_hash=configuration,
            source="native-binding",
        )
        expected_cost = source_value(
            dict(wall_ms=17, tokens_in=13, tokens_out=5, model="retained-provider")
        )
        expected_json_cost = json.loads(canonical_bytes(expected_cost))
        assert completion.envelope["cost"] == expected_cost
        assert completion.apply(conn).transaction == "applied"
        assert (
            conn.scalar(
                text("SELECT body->'cost' FROM ops.task_result WHERE task_id=:task"),
                dict(task=task),
            )
            == expected_json_cost
        )
        assert completion.apply(conn).transaction == "replay"
        from corpus_structure.semantic._operation_calls import publish_characterization

        with pytest.raises(DBAPIError), conn.begin_nested():
            publish_characterization(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="characterization-fixture",
                layer=report.payload,
                view=None,
                cost=json.loads(
                    canonical_bytes(
                        source_value(
                            dict(wall_ms=18, tokens_in=13, tokens_out=5, model="retained-provider")
                        )
                    )
                ),
            )
        assert (
            conn.scalar(
                text("SELECT body->'cost' FROM ops.task_result WHERE task_id=:task"),
                dict(task=task),
            )
            == expected_json_cost
        )


@pytest.mark.parametrize("private_build", ["characterization_finalizable_pdf"], indirect=True)
def test_real_primary_demand_publishes_all_stages_and_reuses_exact_products(
    characterization_source, semantic_writer_engine, tmp_path
):
    """Opt-in actual providers through ordinary task publication, with no mocked provider."""
    import os
    from pathlib import Path

    from corpus_structure.core.method import MethodSettings
    from corpus_structure.orchestrate.characterization import (
        CharacterizationDemandRequest,
        execute_characterization_demand,
    )
    from corpus_structure.orchestrate.commands import finalize_bound_run
    from corpus_structure.semantic.characterization_store import read_layer
    from corpus_structure.semantic.operations import complete_task
    from corpus_structure.semantic.structural_sources import (
        StructuralPassageSelection,
        prepare_structural_sources,
    )

    assets = os.environ.get("CORPUS_PM2_NATIVE_TEST_ASSETS")
    if not assets:
        pytest.skip("locked native provider assets require CORPUS_PM2_NATIVE_TEST_ASSETS")
    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        complete_task(
            conn,
            task_id=source.task["id"],
            attempt=source.task["attempt"],
            holder=source.task["claimed_by"],
            prepared=source.prepared,
            observations=[],
            outcome="empty",
            error=None,
        )
    finalize_bound_run(semantic_writer_engine, source.task["run_id"], "primary-demand-source")
    (external,) = prepare_structural_sources(
        semantic_writer_engine,
        (
            StructuralPassageSelection(
                run_id=source.task["run_id"],
                source_view_id=source.scope["source_view_ids"][0],
                passage_id="primary-demand",
                start=0,
                end=7,
                scope="test",
            ),
        ),
    ).sources
    request = CharacterizationDemandRequest(
        project_id="p",
        release_id=source.prepared.release_id,
        realization_id="z",
        base_document=source.base,
        source_scope=source.scope,
        selected_sources=(external,),
    )
    settings = MethodSettings(data_dir=tmp_path, model_cache=Path(assets).resolve().parent)
    result = execute_characterization_demand(semantic_writer_engine, request, settings)
    with semantic_writer_engine.connect() as conn:
        view = read_view(conn, result.view).payload
        layers = {pin: read_layer(conn, pin) for pin in result.layers}
    operations = {layer.payload["operation"]["key"]: layer for layer in layers.values()}
    assert set(operations) == {
        "text.native_evidence",
        "text.formal_evidence",
        "text.constructions",
        "text.contextual_characterization",
        "text.model_characterization",
        "text.evaluate_context",
    }
    assert view["profile"] == "full_characterization"
    assert view["active_layers"] == view["layers"]
    providers = {
        row["provider"] for layer in layers.values() for row in layer.payload.get("native_runs", ())
    }
    assert {"spacy", "hanlp", "maverick", "dipo"} <= providers, result.preparation_diagnostics
    for operation in ("text.native_evidence", "text.contextual_characterization"):
        coverage = operations[operation].payload["coverage"]
        assert coverage and all(
            row["availability"] == "available"
            and row["outcome"] in {"complete", "empty", "partial"}
            for row in coverage
        ), (operation, coverage, result.preparation_diagnostics)
    from corpus_structure.semantic.interpretation_questions import CHARACTERIZATION_FAMILIES
    from corpus_structure.semantic.model_characterization import CANDIDATE_FAMILIES

    answers = [
        row["model_answer"]
        for row in operations["text.model_characterization"].payload["annotations"]
        if "model_answer" in row
    ]
    answered_families = {answer["family"] for answer in answers}
    assert set(CHARACTERIZATION_FAMILIES) - set(CANDIDATE_FAMILIES) <= answered_families
    assert answered_families <= set(CHARACTERIZATION_FAMILIES)
    model_coverage = operations["text.model_characterization"].payload["coverage"]
    assert {row["family"] for row in model_coverage} == set(CHARACTERIZATION_FAMILIES)
    # The two mathematical literals supply no required linguistic focus. Candidate
    # questions have an explicit empty eligible population, rather than invented
    # answers to a question that was never posed. Real focus/empty-option behavior
    # is independently exercised by the model-characterization controls.
    for family in set(CANDIDATE_FAMILIES) - answered_families:
        assert all(row["outcome"] == "empty" for row in model_coverage if row["family"] == family)
    unavailable = [
        (row["family"], row["outcome"], row["availability"], row.get("reason"))
        for row in model_coverage
        if row["outcome"] not in {"complete", "empty", "partial"}
        or row["availability"] != "available"
    ]
    assert not unavailable, unavailable
    # Ordinary repeated demand selects exact settled pins without new inference runs.
    repeated = execute_characterization_demand(
        semantic_writer_engine,
        request.model_copy(
            update={
                "selected_layers": result.layers,
                "active_layers": tuple(
                    ProductReference(**value) for value in view["active_layers"]
                ),
            }
        ),
        settings,
    )
    assert set(repeated.layers) == set(result.layers)
    assert len(repeated.runs) == 1  # composition only; its task may itself be reused.


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_retained_characterization_does_not_require_unrelated_producer_readiness(
    characterization_source, semantic_writer_engine, semantic_db_engine
):
    """Original finalized data stays readable when a current execution prerequisite is absent."""
    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        report = validate_layer(source.prepared, layer_payload(source, config_hash))
        pin = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=report,
        )
    # This test owns an isolated database. Remove one nonunique execution index,
    # leaving immutable published data and its archived schema/read contract intact.
    with semantic_db_engine.begin() as conn:
        row = (
            conn.execute(
                text("""
            SELECT item->>'index' name, pg_get_indexdef(i.indexrelid) definition
            FROM jsonb_array_elements(data.execution_contract_descriptor()->'indexes') item
            JOIN pg_index i ON i.indexrelid=to_regclass(item->>'index')
            WHERE NOT i.indisunique ORDER BY item->>'index' LIMIT 1
        """)
            )
            .mappings()
            .one()
        )
        from psycopg import sql

        qualified = sql.Identifier(*row["name"].split(".")).as_string()
        conn.exec_driver_sql("DROP INDEX " + qualified)
    try:
        with (
            semantic_db_engine.begin() as conn,
            pytest.raises(DBAPIError, match="index"),
            conn.begin_nested(),
        ):
            conn.execute(
                text("SELECT data.require_execution_release(:release)"),
                {"release": source.prepared.release_id},
            )
        with semantic_writer_engine.connect() as conn:
            assert read_layer(conn, pin).content == report.content
    finally:
        with semantic_db_engine.begin() as conn:
            conn.exec_driver_sql(row["definition"])


@pytest.mark.parametrize("private_build", ["characterization_finalizable_pdf"], indirect=True)
def test_empty_and_image_only_capture_enriches_without_language_provider_calls(
    private_build, semantic_writer_engine, tmp_path, monkeypatch
):
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.methods import native_evidence, pm2_worker, source_preparation
    from corpus_structure.methods.contextual_characterization import (
        ContextualCharacterizationMethod,
    )
    from corpus_structure.methods.model_characterization import ModelCharacterizationMethod
    from corpus_structure.orchestrate.characterization import characterize_captured_run
    from corpus_structure.semantic.operations import complete_task
    from corpus_structure.semantic.source_views import load_source_view

    publication = publish_selected(
        semantic_writer_engine,
        private_build,
        tmp_path / "empty-capture",
        characterization_pages=True,
        empty_sections=True,
    )
    base = ProductReference(private_build.task_id, "selected", publication.logical_digest)
    with semantic_writer_engine.begin() as conn:
        prepared = open_release(conn, private_build.release_id)
        task = (
            conn.execute(text("SELECT * FROM ops.task WHERE id=:id"), {"id": private_build.task_id})
            .mappings()
            .one()
        )
        reader = published_record_reader(conn, base, projection_context=prepared)
        assert reader is not None
        drafts = published_section_drafts(
            reader,
            document_id=task["unit_id"],
            selections=("Empty selected section", "Image-only selected section"),
            membership="direct",
            scope=None,
            consumer_release=prepared.release_id,
        )
        assert len(drafts) == 2
        ids = [
            store_source_view(
                conn,
                run_id=task["run_id"],
                task_id=task["id"],
                attempt=task["attempt"],
                holder=task["claimed_by"],
                draft=draft,
                position=position,
            )
            for position, draft in enumerate(drafts)
        ]
        selected = [load_source_view(conn, identity, analysis=False) for identity in ids]
        assert all(view.text == "" for view in selected)
        assert any(item["label"] == "picture" for view in selected for item in view.items)
        complete_task(
            conn,
            task_id=task["id"],
            attempt=task["attempt"],
            holder=task["claimed_by"],
            prepared=prepared,
            observations=[],
            outcome="empty",
            error=None,
        )

    def unrequested(*args, **kwargs):
        raise AssertionError("zero eligible language text must not prepare or invoke a provider")

    monkeypatch.setattr(native_evidence, "pipeline", unrequested)
    monkeypatch.setattr(source_preparation, "pipeline", unrequested)
    monkeypatch.setattr(pm2_worker, "preflight_pm2_runtime", unrequested)
    monkeypatch.setattr(ContextualCharacterizationMethod, "_native", unrequested)
    monkeypatch.setattr(ModelCharacterizationMethod, "_d1", unrequested)
    monkeypatch.setattr(ModelCharacterizationMethod, "_gliner", unrequested)
    result = characterize_captured_run(
        semantic_writer_engine,
        SimpleNamespace(run_id=task["run_id"]),
        project_id="p",
        release_id=prepared.release_id,
        realization_id="z",
        domain="statistics",
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        method_options={},
    )
    assert len(result) == 1
    with semantic_writer_engine.connect() as conn:
        view = read_view(conn, result[0].view).payload
        layers = [read_layer(conn, pin).payload for pin in result[0].layers]
    assert view["base_document"] == base.values()
    assert set(view["source_scope"]["source_view_ids"]) == set(ids)
    assert not result[0].missing_families
    assert not result[0].preparation_diagnostics
    for layer in layers:
        assert not layer.get("native_runs")
        assert not layer["occurrences"] and not layer["annotations"] and not layer["terms"]
        assert all(
            row["outcome"] == "empty"
            and row["availability"] == "available"
            and row["eligible"] == row["examined"]
            and not row.get("unexamined")
            for row in layer["coverage"]
        )

    refreshed = characterize_captured_run(
        semantic_writer_engine,
        SimpleNamespace(run_id=task["run_id"]),
        project_id="p",
        release_id=prepared.release_id,
        realization_id="z",
        domain="statistics",
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        method_options={},
        fresh_methods=("text.formal_evidence",),
    )
    with semantic_writer_engine.connect() as conn:

        def producer_pins(result, method):
            return {
                pin
                for pin in result.layers
                if read_layer(conn, pin).payload["operation"]["key"] == method
            }

        assert producer_pins(refreshed[0], "text.formal_evidence").isdisjoint(
            producer_pins(result[0], "text.formal_evidence")
        )
        assert producer_pins(refreshed[0], "text.native_evidence") == producer_pins(
            result[0], "text.native_evidence"
        )
        assert read_view(conn, result[0].view).payload == view


@pytest.mark.parametrize("private_build", ["characterization_finalizable_pdf"], indirect=True)
def test_unprojected_native_formula_publishes_and_replays_item_anchored_syntax(
    private_build, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.core.vocab import Stage
    from corpus_structure.methods.characterization import ComposeViewMethod
    from corpus_structure.methods.formal_evidence import FormalEvidenceMethod
    from corpus_structure.orchestrate.commands import finalize_bound_run
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
    from corpus_structure.orchestrate.runner import Graph, Step
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.semantic.characterization_store import read_inventory
    from corpus_structure.semantic.operations import OperationBinding, complete_task
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.source_views import load_source_view
    from corpus_structure.semantic.structural_products import ExternalSourceRef
    from corpus_structure.serve.characterization_replay import (
        CharacterizationReviewSelection,
        capture_characterization_review,
    )
    from corpus_structure.serve.review_bundle import verify_review_bundle

    from .witnessed_scenario_support import completed_metadata

    publication = publish_selected(
        semantic_writer_engine,
        private_build,
        tmp_path / "unprojected-capture",
        characterization_pages=True,
        unprojected_formula=True,
    )
    base = ProductReference(private_build.task_id, "selected", publication.logical_digest)
    with semantic_writer_engine.begin() as conn:
        prepared = open_release(conn, private_build.release_id)
        task = (
            conn.execute(text("SELECT * FROM ops.task WHERE id=:id"), {"id": private_build.task_id})
            .mappings()
            .one()
        )
        reader = published_record_reader(conn, base, projection_context=prepared)
        assert reader is not None
        (draft,) = published_section_drafts(
            reader,
            document_id=task["unit_id"],
            selections=("Unprojected formula section",),
            membership="direct",
            scope=None,
            consumer_release=prepared.release_id,
        )
        assert draft.text == "" and not draft.pieces
        identity = store_source_view(
            conn,
            run_id=task["run_id"],
            task_id=task["id"],
            attempt=task["attempt"],
            holder=task["claimed_by"],
            draft=draft,
            position=0,
        )
        source = load_source_view(conn, identity, analysis=False)
        (formula,) = [item for item in source.items if item.get("label") == "formula"]
        assert formula["orig"] == "x+1" and formula["text"] == ""
        assert source.health["formula_outcomes"] == [
            {"pointer": formula["self_ref"], "outcome": "failed"}
        ]
        complete_task(
            conn,
            task_id=task["id"],
            attempt=task["attempt"],
            holder=task["claimed_by"],
            prepared=prepared,
            observations=[],
            outcome="empty",
            error=None,
        )
    finalize_bound_run(semantic_writer_engine, task["run_id"], "unprojected-formula-capture")
    metadata, revision, _ = completed_metadata(
        SimpleNamespace(writer=semantic_writer_engine), task["run_id"]
    )
    external = ExternalSourceRef(
        project_id="p",
        run_id=task["run_id"],
        cut_id=metadata["cut_id"],
        release_id=prepared.release_id,
        result_revision=revision,
        source_view_id=identity,
        native_task_id=base.task_id,
        native_product_key=base.product_key,
        native_content_digest=base.content_digest,
        projection_digest=source.ref.projection_digest,
        recipe_digest=source.ref.recipe_digest,
        coordinate_version=3 if source.integrated_context is not None else 2,
    )
    scope = dict(
        source_view_ids=[identity],
        source_views=[
            dict(
                source_view_id=identity,
                key=source.ref.key,
                base_document=base.values(),
                section_pointer=source.ref.section_pointer,
                membership=source.ref.membership,
                projection_digest=source.ref.projection_digest,
                recipe_digest=source.ref.recipe_digest,
            )
        ],
        selectors=[dict(projection=source.ref.projection_digest, start=0, end=0)],
        profile="native-formula-object",
    )

    def run(method, cfg):
        result = run_source_methods(
            semantic_writer_engine,
            project_id="p",
            prepared=prepared,
            binding=OperationBinding(
                prepared.release_id, metadata["output_realization_id"], revision, b"{}"
            ),
            registry=MethodRegistry((method,), MethodsFile(configs={method.name: {"test": cfg}})),
            graph=Graph(((Stage.EXTRACT, (Step(method.name + "/test"),)),), policy_propose=False),
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            selected_sources=(external,),
        )
        assert result.status == "source_ready"
        with semantic_writer_engine.connect() as conn:
            (product,) = read_inventory(conn, result.run_id)["products"]
        return result, ProductReference(**product["reference"])

    config = dict(characterization_base_document=base.values(), characterization_source_scope=scope)
    _, layer_pin = run(FormalEvidenceMethod(), config)
    with semantic_reader_engine.connect() as conn:
        layer = read_layer(conn, layer_pin).payload
    inputs = {
        row["formal_input"]["representation"]: row["formal_input"]
        for row in layer["annotations"]
        if row["kind"] == "formal.input"
    }
    assert inputs["source_text"]["text"] == "x+1"
    assert inputs["source_text"]["syntax_outcome"] == "complete"
    assert inputs["recognized_latex"]["text"] == ""
    assert inputs["recognized_latex"]["syntax_outcome"] == "failed"
    assert any(row["kind"] == "formal.symbol" for row in layer["annotations"])
    assert all(
        extent["native_pointer"] == formula["self_ref"]
        and "start" not in extent
        and "text" not in extent
        for occurrence in layer["occurrences"]
        for extent in occurrence["extents"]
    )
    math_coverage = next(row for row in layer["coverage"] if row["family"] == "formal.math")
    assert math_coverage["outcome"] == "partial"
    composed, view_pin = run(
        ComposeViewMethod(),
        dict(
            config,
            characterization_layers=[layer_pin.values()],
            characterization_profile="selected_layers",
        ),
    )
    cancellation = OperationCancellation()
    destination = tmp_path / "unprojected-formula-review"
    destination.mkdir()
    with read_snapshot(semantic_reader_engine, cancellation=cancellation.postgresql) as conn:
        captured = capture_characterization_review(
            conn,
            CharacterizationReviewSelection(run_id=composed.run_id, **view_pin.values()),
            destination,
            cancellation,
        )
    assert verify_review_bundle(destination) == captured


@pytest.mark.parametrize("private_build", ["characterization_pdf"], indirect=True)
def test_native_layer_manifest_is_bounded_sealed_metadata(
    characterization_source,
    semantic_writer_engine,
    semantic_reader_engine,
):
    from corpus_structure.semantic.characterization_store import read_layer_manifest

    source = characterization_source
    with semantic_writer_engine.begin() as conn:
        task, claim, config_hash = make_task(conn, source)
        report = validate_layer(source.prepared, layer_payload(source, config_hash))
        pin = report.reference(task)
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_layer_manifest(conn, pin, run_id=source.task["run_id"])
        published = publish_layer(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=report,
        )
        assert published == pin
    with semantic_reader_engine.connect() as conn:
        manifest = read_layer_manifest(conn, pin, run_id=source.task["run_id"])
        assert manifest.reference(task) == pin
        assert manifest.base_document == source.base
        assert manifest.payload == {
            key: report.payload[key]
            for key in (
                "format",
                "release_id",
                "base_document",
                "operation",
                "source_scope",
                "outcome",
                "dependencies",
                "coverage",
            )
        }
        assert "annotations" not in manifest.payload and "native_runs" not in manifest.payload
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_layer_manifest(conn, pin, max_bytes=1)
        changed = ProductReference(pin.task_id, pin.product_key, "f" * 64)
        with pytest.raises(DBAPIError), conn.begin_nested():
            read_layer_manifest(conn, changed)
