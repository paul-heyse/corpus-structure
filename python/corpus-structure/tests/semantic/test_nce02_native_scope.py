"""Native primary projections preserve independently authored predicate scope and roles."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest
from methods.primary_reading_fixture import primary_product
from methods.test_scoped_relations import complete_native_fields, discover_relations, source
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.predicate_frames import predicate_frames
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.structural_products import StructuralPassage


def primary_parameters(view, layers):
    """Pass actual primary products to installed immutable projection functions."""
    return dict(
        layers=json.dumps(
            {canonical_bytes(pin.values()).decode(): layer.payload for pin, layer in layers.items()}
        ),
        view=json.dumps(
            dict(
                id=view.ref.id,
                projection_digest=view.ref.projection_digest,
                projection=dict(text=view.text, pieces=view.pieces),
            )
        ),
    )


def native_child(conn, layers, reference, role):
    return conn.scalar(
        text("""
            WITH input AS (SELECT CAST(:layers AS jsonb) layers,CAST(:ref AS jsonb) ref)
            SELECT ops.primary_characterization_child(
                layers,ref,ops.primary_characterization_node(layers,ref),:role)->>'value'
            FROM input
        """),
        dict(
            layers=json.dumps(
                {
                    canonical_bytes(pin.values()).decode(): layer.payload
                    for pin, layer in layers.items()
                }
            ),
            ref=json.dumps(reference if isinstance(reference, dict) else reference.values()),
            role=role,
        ),
    )


def native_member(conn, parameters, member, anchors, *, selection, indices=None):
    return conn.scalar(
        text("""
            WITH input AS (SELECT CAST(:layers AS jsonb) layers,CAST(:ref AS jsonb) ref,
                jsonb_populate_record(NULL::kb.source_view,CAST(:view AS jsonb)) view_)
            SELECT ops.predicate_primary_member_matches(layers,ref,
                ops.primary_characterization_node(layers,ref),view_,:lo,:hi,
                CAST(:extents AS jsonb),CAST(:anchors AS jsonb),CAST(:indices AS jsonb))
            FROM input
        """),
        dict(
            **parameters,
            ref=json.dumps(member["primary_node"]),
            extents=json.dumps(member["extents"]),
            anchors=json.dumps(anchors),
            indices=json.dumps(member["token_indices"] if indices is None else indices),
            lo=selection[0],
            hi=selection[1],
        ),
    )


def passage(spelling, start=0, end=None):
    end = len(spelling) if end is None else end
    return StructuralPassage(
        passage_id="scope",
        scope="scope",
        source_ref="fixture",
        start=start,
        end=end,
        text=spelling[start:end],
    )


def frame_rows(output):
    return [
        row["component"]
        for row in output["contributions"]
        if row.get("component", {}).get("kind") == "predicate_frame"
    ]


def authored_product(monkeypatch, spelling, columns):
    """Native lexical positions with independent POS/dependency/lemma gold."""
    from ingest.test_annotations import ControlledPipeline, item

    controlled = ControlledPipeline()
    monkeypatch.setattr(annotations, "pipeline", lambda _: controlled)
    (product,) = annotations.annotate((item(controlled, spelling, start=0),))
    assert len(product.tokens) == len(columns)
    product = replace(
        product,
        tokens=tuple(
            replace(token, pos=pos, dependency=dep, head=head, lemma=lemma)
            for token, (pos, dep, head, lemma) in zip(product.tokens, columns, strict=True)
        ),
    )
    return primary_product(
        spelling, product, AnnotationProfile(), native_profile=controlled.selection().native
    )


def test_native_list_host_requires_exact_selected_membership(semantic_db_engine):
    intro = "For each of the following, assume that all inputs are valid:"
    spelling = f"{intro}\nThe analyst records the input.\nThe reviewer checks the result."
    view = complete_native_fields(source(spelling, labels=("text", "list_item", "list_item")))
    intro_node, first, second = (
        {**node, "content_layer": "body", "children": []} for node in view.items
    )
    parent, group = "#/groups/1", "#/groups/2"

    def ref(pointer):
        return {"$ref": pointer}

    intro_node["parent"] = ref(parent)
    first["parent"] = second["parent"] = ref(group)
    nodes = (
        dict(
            self_ref=parent,
            label="section",
            content_layer="body",
            children=[ref(intro_node["self_ref"]), ref(group)],
        ),
        intro_node,
        dict(
            self_ref=group,
            label="list",
            content_layer="body",
            parent=ref(parent),
            children=[ref(first["self_ref"]), ref(second["self_ref"])],
        ),
        first,
        second,
    )
    projection = dict(
        text=spelling,
        pieces=view.pieces,
        items=[node["self_ref"] for node in nodes],
        ancestors=[],
        health={},
    )
    view = replace(
        view,
        items=nodes,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    output = discover_relations(native_source_frame(view, ()), passages=(passage(spelling),))
    population = {row["contribution_id"]: row for row in output["contributions"]}
    parameters = primary_parameters(view, output["_primary_layers"])
    witnessed = {}
    with semantic_db_engine.connect() as conn:
        for row in population.values():
            relation = row.get("component", {})
            if "host_witness" not in relation:
                continue
            assert relation["host_witness"] == dict(kind="list_intro", list_group=group)
            host = population[relation["host_contribution_id"]]["component"]
            predicate = next(m for m in host["frame_members"] if m["role"] == "predicate")
            anchors = population[predicate["contribution"]]["anchors"]
            cue = population[relation["qualifier_contribution_id"]]["component"]
            assert (
                native_child(
                    conn, output["_primary_layers"], cue["primary_node"], "native_list_group"
                )
                == group
            )
            assert (
                native_member(conn, parameters, predicate, anchors, selection=(0, len(spelling)))
                is True
            )
            witnessed[anchors[0]["source_piece"]] = (predicate, anchors)
        assert set(witnessed) == {"records", "checks"}
        predicate, anchors = witnessed["checks"]
        assert (
            native_member(
                conn,
                parameters,
                predicate,
                anchors,
                selection=(0, spelling.index("\nThe reviewer")),
            )
            is False
        )
    # A new native ancestry/projection cannot reuse old positioned source evidence.
    changed = dict(
        parameters,
        view=json.dumps(dict(id=view.ref.id, projection_digest="f" * 64, projection=projection)),
    )
    with semantic_db_engine.connect() as conn, pytest.raises(DBAPIError) as refused:
        native_member(conn, changed, predicate, anchors, selection=(0, len(spelling)))
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"


def test_native_clipped_role_population_detects_omitted_roles(semantic_db_engine):
    spelling = "The analyst records the input."
    view = complete_native_fields(source(spelling, labels=("text",)))
    prepared = prepare_source(view, annotations_only=True)
    start = spelling.index("records")
    frame = native_source_frame(view, ())
    output = discover_relations(
        frame, annotations=prepared.annotations, passages=(passage(spelling),)
    )
    (whole,) = frame_rows(output)
    members = {m["role"]: m for m in whole["frame_members"]}
    assert members["actor"]["token_indices"] == (0, 1)
    assert members["object"]["token_indices"] == (3, 4)
    action = discover_relations(
        frame,
        annotations=prepared.annotations,
        primary_layers=output["_primary_layers"],
        passages=(passage(spelling, start, start + len("records")),),
    )
    (clipped,) = frame_rows(action)
    assert clipped["unlocated_roles"] == (
        dict(role="actor", head_token=1, token_indices=(0, 1), reason="outside_selection"),
        dict(role="object", head_token=4, token_indices=(3, 4), reason="outside_selection"),
    )
    determiner = discover_relations(
        frame,
        annotations=prepared.annotations,
        primary_layers=output["_primary_layers"],
        passages=(passage(spelling, start, spelling.index("input")),),
    )
    (partial,) = frame_rows(determiner)
    assert partial["unlocated_roles"] == (clipped["unlocated_roles"][0],)
    (object_,) = [m for m in partial["frame_members"] if m["role"] == "object"]
    assert object_["token_indices"] == (3,) and object_["outcome"] == "partial"
    population = {row["contribution_id"]: row for row in output["contributions"]}
    parameters = primary_parameters(view, output["_primary_layers"])
    with semantic_db_engine.connect() as conn:
        for role in ("actor", "object"):
            member = members[role]
            anchors = population[member["contribution"]]["anchors"]
            assert (
                native_member(conn, parameters, member, anchors, selection=(0, len(spelling)))
                is True
            )
            for indices in (
                [],
                member["token_indices"][:1],
                member["token_indices"][::-1],
                (*member["token_indices"], member["token_indices"][0]),
            ):
                assert (
                    native_member(
                        conn,
                        parameters,
                        member,
                        anchors,
                        selection=(0, len(spelling)),
                        indices=indices,
                    )
                    is False
                )
        partial_population = {row["contribution_id"]: row for row in determiner["contributions"]}
        assert (
            native_member(
                conn,
                parameters,
                object_,
                partial_population[object_["contribution"]]["anchors"],
                selection=(start, spelling.index("input")),
            )
            is True
        )
        # Unmapped native text cannot support a located role even inside the selection.
        physical = json.loads(parameters["view"])
        physical["projection"]["pieces"] = [
            dict(view.pieces[0], start=start, end=start + len("records"))
        ]
        assert (
            native_member(
                conn,
                dict(parameters, view=json.dumps(physical)),
                members["object"],
                population[members["object"]["contribution"]]["anchors"],
                selection=(0, len(spelling)),
            )
            is False
        )


def test_native_attribution_requires_an_eligible_reporting_governor(
    semantic_db_engine, monkeypatch
):
    spelling = "Suppose we wait."
    with semantic_db_engine.connect() as conn:
        for pos, expected in (("VERB", "reference"), ("NOUN", "unresolved")):
            product = authored_product(
                monkeypatch,
                spelling,
                (
                    (pos, "ROOT", 0, "suppose"),
                    ("PRON", "nsubj", 2, "we"),
                    ("VERB", "ccomp", 0, "wait"),
                    ("PUNCT", "punct", 2, "."),
                ),
            )
            result = predicate_frames(spelling, (product,))
            assert not result.issues
            (frame,) = [f for f in result.frames if f.predicate.tokens == (2,)]
            assert frame.interpretation == expected
            assert (
                native_child(conn, product.primary_layers, frame.primary_ref, "interpretation")
                == expected
            )
            assert (
                native_child(conn, product.primary_layers, frame.primary_ref, "voice") == "active"
            )
            assert (
                native_child(conn, product.primary_layers, frame.primary_ref, "polarity")
                == "positive"
            )


def test_native_block_negation_preserves_direct_and_shared_scope(semantic_db_engine, monkeypatch):
    with semantic_db_engine.connect() as conn:
        for connector, expected in (
            ("and", {2: "negative_scope_unresolved", 4: "negative_scope_unresolved"}),
            ("but", {2: "negative", 4: "positive"}),
        ):
            spelling = f"Do not heat {connector} stir"
            product = authored_product(
                monkeypatch,
                spelling,
                (
                    ("AUX", "aux", 2, "do"),
                    ("PART", "neg", 2, "not"),
                    ("VERB", "ROOT", 2, "heat"),
                    ("CCONJ", "cc", 2, connector),
                    ("VERB", "conj", 2, "stir"),
                ),
            )
            result = predicate_frames(spelling, (product,))
            assert not result.issues
            assert {f.predicate.tokens[0]: f.polarity for f in result.frames} == expected
            for frame in result.frames:
                assert (
                    native_child(conn, product.primary_layers, frame.primary_ref, "polarity")
                    == expected[frame.predicate.tokens[0]]
                )


def test_native_example_cue_uses_one_governor_and_refuses_numbered_reference(
    semantic_db_engine, monkeypatch
):
    cases = (
        (
            "For example, permutations are",
            (
                ("ADP", "prep", 3, "for"),
                ("NOUN", "pobj", 0, "example"),
                ("PUNCT", "punct", 3, ","),
                ("NOUN", "nsubj", 4, "permutation"),
                ("AUX", "ROOT", 4, "be"),
            ),
            4,
            "example",
        ),
        (
            "Figure Tree for Example 4.25",
            (
                ("VERB", "ROOT", 0, "figure"),
                ("NOUN", "appos", 0, "tree"),
                ("ADP", "prep", 1, "for"),
                ("PROPN", "pobj", 2, "example"),
                ("NUM", "nummod", 3, "4.25"),
            ),
            0,
            "unresolved",
        ),
    )
    with semantic_db_engine.connect() as conn:
        for spelling, columns, host, expected in cases:
            product = authored_product(monkeypatch, spelling, columns)
            result = predicate_frames(spelling, (product,))
            assert not result.issues
            (frame,) = [f for f in result.frames if f.predicate.tokens == (host,)]
            assert frame.interpretation == expected
            assert (
                native_child(conn, product.primary_layers, frame.primary_ref, "interpretation")
                == expected
            )
            if expected == "example":
                assert len([f for f in result.frames if f.interpretation == "example"]) == 1
