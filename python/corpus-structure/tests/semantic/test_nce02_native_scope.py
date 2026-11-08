"""Native host replay over an independently authored two-item list."""

import json
from dataclasses import asdict, replace
from hashlib import sha256

from methods.test_scoped_relations import complete_native_fields, source
from sqlalchemy import text

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.scoped_relations import discover_relations
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.structural_products import StructuralPassage


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
    prepared = prepare_source(view, profile=AnnotationProfile(), annotations_only=True)
    assert not prepared.annotation_errors
    selection = StructuralPassage(
        passage_id="layout",
        scope="layout",
        source_ref="fixture",
        start=0,
        end=len(spelling),
        text=spelling,
    )
    output = discover_relations(
        native_source_frame(view, ()),
        annotations=prepared.annotations,
        passages=(selection,),
        predicate_version="3",
    )
    population = {row["contribution_id"]: row for row in output["contributions"]}
    annotations = {f"annotation:{a.dependency_digest}": asdict(a) for a in prepared.annotations}
    witnessed = {}
    for row in population.values():
        relation = row.get("component", {})
        if "host_witness" not in relation:
            continue
        host = population[relation["host_contribution_id"]]
        component = host["component"]
        predicate = next(m for m in component["frame_members"] if m["role"] == "predicate")
        (anchor,) = population[predicate["contribution"]]["anchors"]
        cue = population[relation["qualifier_contribution_id"]]["component"]
        witnessed[anchor["source_piece"]] = dict(
            view=json.dumps(
                dict(
                    projection=projection,
                    native_task_id=1,
                    native_product_key="organized",
                    native_content_digest="fixture",
                )
            ),
            population=json.dumps(population),
            cue=json.dumps(cue),
            host=json.dumps(host),
            relation=json.dumps(relation),
            source_annotation=json.dumps(annotations[cue["annotation"]]),
            host_annotation=json.dumps(annotations[component["annotation"]]),
            selection=selection.model_dump_json(),
        )
    assert set(witnessed) == {"records", "checks"}

    check = text("""
        SELECT ops.predicate_cross_block_host_matches(
            jsonb_populate_record(NULL::kb.source_view, CAST(:view AS jsonb)),
            CAST(:population AS jsonb), CAST(:cue AS jsonb), CAST(:host AS jsonb),
            CAST(:relation AS jsonb), CAST(:source_annotation AS jsonb),
            CAST(:host_annotation AS jsonb), CAST(:selection AS jsonb))
    """)
    with semantic_db_engine.connect() as conn:
        # Controlled native-item input isolates the installed host guard.
        conn.exec_driver_sql("""
            CREATE OR REPLACE FUNCTION ops.read_pdf_published_items(
                p_task bigint,p_product text,p_digest text,p_pointers text[])
            RETURNS TABLE(product_id text,revision_id text,pointer text,ordinal bigint,
                label text,parent_pointer text,section_pointer text,content_layer text,
                text text,native_json jsonb) LANGUAGE sql STABLE AS $$
                SELECT NULL::text,NULL::text,p,NULL::bigint,NULL::text,NULL::text,
                    NULL::text,NULL::text,item->>'text',item
                FROM unnest(p_pointers) p
                CROSS JOIN LATERAL (
                    SELECT current_setting('test.nce02_native_items')::jsonb->p AS item
                ) value
            $$
        """)
        original = {node["self_ref"]: node for node in nodes}

        def bind(items):
            conn.execute(
                text("SELECT set_config('test.nce02_native_items',:items,true)"),
                {"items": json.dumps(items)},
            )

        bind(original)
        assert all(conn.scalar(check, row) is True for row in witnessed.values())

        # Both the frame and candidate list still cite the second item after
        # its actual native parent is changed. The guard must refuse that edge.
        bind({**original, second["self_ref"]: {**second, "parent": ref(parent)}})
        assert conn.scalar(check, witnessed["records"]) is True
        assert conn.scalar(check, witnessed["checks"]) is False

        bind(original)
        clipped = selection.model_copy(update={"end": spelling.index("\nThe reviewer")})
        assert (
            conn.scalar(check, {**witnessed["checks"], "selection": clipped.model_dump_json()})
            is False
        )


def test_native_clipped_role_population_detects_omitted_roles(semantic_db_engine):
    spelling = "The analyst records the input."
    view = complete_native_fields(source(spelling, labels=("text",)))
    prepared = prepare_source(view, profile=AnnotationProfile(), annotations_only=True)
    (annotation,) = prepared.annotations
    from corpus_structure.methods.predicate_frames import interpretation_recipe

    start = spelling.index("records")
    action_only = (start, start + len("records"))
    actor = {
        "role": "actor",
        "head_token": 1,
        "token_indices": [0, 1],
        "reason": "outside_selection",
    }
    object_ = {
        "role": "object",
        "head_token": 4,
        "token_indices": [3, 4],
        "reason": "outside_selection",
    }
    check = text("""
        WITH expected AS (
          SELECT jsonb_agg(to_jsonb(r)-'predicate') roles
          FROM ops.predicate_argument_inventory(
            jsonb_build_object('text',CAST(:spelling AS text)),
            CAST(:tokens AS jsonb),CAST(:recipe AS jsonb)) r
          WHERE r.predicate=2
        )
        SELECT ops.predicate_clipped_roles_match(
          CAST(:mapped AS int8multirange),CAST(:tokens AS jsonb),roles,
          :start,:end,CAST(:reported AS jsonb)) FROM expected
    """)
    with semantic_db_engine.connect() as conn:

        def matches(reported, selection=action_only, mapping=None):
            return conn.scalar(
                check,
                dict(
                    spelling=spelling,
                    tokens=json.dumps([asdict(token) for token in annotation.tokens]),
                    recipe=json.dumps(interpretation_recipe()),
                    mapped=mapping or f"{{[0,{len(spelling)})}}",
                    start=selection[0],
                    end=selection[1],
                    reported=json.dumps(reported),
                ),
            )

        assert matches([actor, object_]) is True
        assert matches([object_, actor]) is True
        assert matches([object_]) is False
        assert matches([]) is False
        assert matches([actor, object_, actor]) is False
        assert matches([actor, {**object_, "token_indices": [4, 3]}]) is False
        # The exact determiner remains located even though the object head is clipped.
        through_determiner = (start, spelling.index("input"))
        assert matches([actor], through_determiner) is True
        # A selected extent without mapped native text is distinct from clipping.
        unmappable_object = {**object_, "reason": "unmappable"}
        assert matches([actor, unmappable_object], (start, len(spelling)), "{[12,19)}") is True
