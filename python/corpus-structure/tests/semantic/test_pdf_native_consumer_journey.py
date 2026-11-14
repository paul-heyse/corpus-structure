"""Native PDF frames enter the real proposal, consolidation and evaluator boundaries."""

import json
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.semantic import (
    create_reference_set,
    record_pass,
    reference_evaluate,
    split_documents,
)
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_views import load_source_view
from semantic.agent_scenarios import lease_and_read
from semantic.agent_scenarios import (
    native_build_resubmission_case as native_build_resubmission_case,
)


def authored(unit, sentence, prefix) -> dict[str, Any]:
    # Independent expected authoring uses source text, never copied prediction entities/claims.
    return {
        "unit_ref": unit,
        "entities": [
            {"id": prefix + "_person", "class_iri": "https://example.org/Person", "label": "Alice"}
        ],
        "statements": [{"id": prefix + "_statement", "kind": "remark", "anchor": sentence}],
        "claims": [
            {
                "id": prefix + "_name",
                "subject": prefix + "_person",
                "predicate": "https://example.org/name",
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "statement": prefix + "_statement",
                "statement_role": "conclusion",
                "evidence": [{"sentence": sentence, "quote": "Alice is here.", "role": "primary"}],
            }
        ],
    }


def test_native_proposal_consolidation_and_independent_reference_journey(
    commit_db_engine, commit_writer_engine, commit_evaluator_engine, tmp_path
):
    _prepared, run, task, view, key = native_build_resubmission_case(
        commit_db_engine, commit_writer_engine, tmp_path
    )
    session = SemanticAgentSession(commit_writer_engine, run)

    async def submit():
        async with Client(build_semantic_server(session)) as client:
            unit = await lease_and_read(client, run, task)
            assert unit["native_source"]["source_view_id"] == view
            response = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": authored(
                        key, unit["native_source"]["native_evidence"][0]["handle"], "prediction"
                    ),
                },
            )
            assert response.structured_content is not None
            assert response.structured_content["submission_disposition"] == "completed_accepted"

    anyio.run(submit)
    finalize_bound_run(commit_writer_engine, run, "native-result")
    with commit_writer_engine.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM data.evidence_source WHERE "
                    "source_view_id=:view AND native_address LIKE 'pdf:%'"
                ),
                {"view": view},
            )
            > 0
        )
        assert conn.scalar(text("SELECT to_regclass('kb.rendition')")) is None
        source = load_source_view(conn, view)
    frame = native_source_frame(source, [("reference_sentence", 0, 14)])
    expected = canonical_bytes(authored(key, "native_evidence:0", "reference"))
    with commit_evaluator_engine.begin() as conn:
        split_documents(conn, "native-consumer")
        made = create_reference_set(
            conn,
            project_id="native-consumer",
            source_run_id=run,
            label="native-independent",
            split="dev",
            size=1,
            forced=(key,),
        )
        unit = made["units"][key]
        assert made["sampling"]["source_frame_abi"] == "native-source-view-1"
        for kind in ("A", "B", "C"):
            record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor="automated-independent-" + kind,
                authored=expected,
                frame=frame,
            )
        result = reference_evaluate(
            conn, project_id="native-consumer", run_id=run, set_id=made["set_id"]
        )
        assert result.result["tiers"]["full"]["matched"] == 1
        assert result.result["tiers"]["full"]["reference"] == 1
        assert result.result["tiers"]["full"]["prediction"] == 1
        assert result.reference_snapshot[0]["source_view_id"] == view
        sentence = frame.sentences[0]
        valid = json.loads(sentence.locator[4:])
        count_before = conn.scalar(
            text("SELECT count(*) FROM eval.reference_pass WHERE unit_id=:unit"), {"unit": unit}
        )
        for invalid in (
            {**valid, "pointer": "#/texts/forged"},
            {**valid, "cell_index": 999},
            {**valid, "projection_digest": "f" * 64},
            {**valid, "product_digest": "e" * 64},
            {**valid, "source_view_id": view + 100},
        ):
            citations = [
                dict(
                    sentence="native_evidence:0",
                    start=0,
                    end=14,
                    quote="Alice is here.",
                    role="primary",
                    placement="exact_cited",
                    matches=1,
                    picked=False,
                    timeouts=[],
                    outcome="located",
                    family="claims",
                    item_ref="reference_name",
                    evidence_index=0,
                    locator="pdf:" + canonical_bytes(invalid).decode(),
                )
            ]
            with pytest.raises(DBAPIError, match="native"), conn.begin_nested():
                conn.execute(
                    text(
                        "SELECT "
                        "eval.record_native_reference_pass(:unit,'C','forged',:"
                        "authored,CAST(:citations AS jsonb),CAST(:source_frame "
                        "AS jsonb))"
                    ),
                    dict(
                        unit=unit,
                        authored=expected,
                        citations=json.dumps(citations),
                        source_frame=json.dumps(asdict(frame)),
                    ),
                )

        noncanonical = [dict(citations[0], locator="pdf:" + json.dumps(valid))]
        with (
            pytest.raises(DBAPIError, match="canonical source product custody"),
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "SELECT "
                    "eval.record_native_reference_pass(:unit,'C','noncanonical'"
                    ",:authored,CAST(:citations AS jsonb),CAST(:source_frame AS jsonb))"
                ),
                dict(
                    unit=unit,
                    authored=expected,
                    citations=json.dumps(noncanonical),
                    source_frame=json.dumps(asdict(frame)),
                ),
            )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM eval.reference_pass WHERE unit_id=:unit"), {"unit": unit}
            )
            == count_before
        )


def test_native_cell_evidence_alias_stays_within_its_retained_projection_piece():
    from dataclasses import replace

    from corpus_structure.semantic.proposals import (
        ProposalSentence,
        locate_proposal,
        native_address,
        native_evidence_entries,
    )
    from semantic.proposals_support import batch, prepared

    text_value = "Alice is here. Bob is there."
    source = SimpleNamespace(
        ref=SimpleNamespace(
            id=7,
            key="native-cell-unit",
            native_product=ProductReference(2, "native", "a" * 64),
            section_pointer="#/groups/0",
            membership="direct",
            projection_digest="b" * 64,
            recipe_digest="c" * 64,
        ),
        text=text_value,
        pieces=(
            {
                "kind": "native_text",
                "item_ref": "#/tables/0",
                "cell_index": 0,
                "source_field": "cell_text",
                "start": 0,
                "end": 14,
            },
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 15,
                "end": len(text_value),
            },
        ),
        items=(
            {"self_ref": "#/tables/0", "label": "table"},
            {"self_ref": "#/texts/0", "label": "text"},
        ),
        ancestors=(),
        health={},
    )
    frame = native_source_frame(source, [("s1", 0, len(text_value))])
    entries = native_evidence_entries(frame)
    assert entries[0]["handle"] == "native_evidence:0" and entries[0]["cell_index"] == 0
    assert entries[0]["pointer"] == "#/tables/0" and entries[0]["text"] == "Alice is here."
    raw = batch()
    raw["unit_ref"] = frame.unit_ref
    raw["statements"][0]["anchor"] = "native_evidence:0"
    citation = raw["claims"][0]["evidence"][0]
    citation["sentence"] = "native_evidence:0"
    located = locate_proposal(prepared(), raw, frame)
    assert located.clean
    evidence = located.stored.model_dump(mode="json")["claims"][0]["evidence"][0]
    assert (evidence["start"], evidence["end"], evidence["locator"]) == (
        0,
        14,
        entries[0]["locator"],
    )
    citation["sentence"] = "native_evidence:1"
    refused = locate_proposal(prepared(), raw, frame)
    assert not refused.clean  # The quote exists elsewhere; the named cell/piece cannot relocate.
    wrong = ProposalSentence(
        "native_evidence:0",
        native_address(frame, start=15, end=len(text_value)),
        15,
        len(text_value),
    )
    with pytest.raises(ValueError, match="retained projection piece"):
        replace(
            frame, sentences=tuple(wrong if row.id == wrong.id else row for row in frame.sentences)
        )


def test_ancestor_evidence_keeps_its_own_offsets_and_statement_source():
    from dataclasses import asdict, replace

    from corpus_structure.semantic.domain_operations import NativeEvidenceLink, _evidence_link
    from corpus_structure.semantic.proposals import (
        locate_proposal,
        native_frame_from_dict,
        native_frame_source,
        native_statement_source,
        statement_anchor,
    )
    from semantic.proposals_support import batch, prepared

    product = ProductReference(2, "native", "a" * 64)
    parent_group = {"self_ref": "#/groups/parent", "label": "section"}

    def source(identity, pointer, text, ancestors):
        return SimpleNamespace(
            ref=SimpleNamespace(
                id=identity,
                key=f"native:{identity}",
                native_product=product,
                section_pointer=pointer,
                membership="direct",
                projection_digest=str(identity) * 64,
                recipe_digest="c" * 64,
            ),
            text=text,
            pieces=(
                {
                    "kind": "native_text",
                    "item_ref": f"#/texts/{identity}",
                    "source_field": "text",
                    "start": 0,
                    "end": len(text),
                },
            ),
            items=({"self_ref": f"#/texts/{identity}", "label": "text", "text": text},),
            ancestors=ancestors,
            health={},
        )

    parent = source(6, "#/groups/parent", "Long parent context. Alice is here.", ())
    child = source(7, "#/groups/child", "Child fact.", (parent_group,))
    parent_frame = native_source_frame(parent, [("s1", 21, len(parent.text))])
    parent_source = native_frame_source(parent_frame)
    frame = replace(
        native_source_frame(child, [("s1", 0, len(child.text))]), context_sources=(parent_source,)
    )
    raw = batch()
    raw["unit_ref"] = frame.unit_ref
    handle = "native_context:6:s1"
    raw["statements"][0]["anchor"] = handle
    raw["claims"][0]["evidence"][0]["sentence"] = handle
    located = locate_proposal(prepared(), raw, frame)
    assert located.clean
    citation = located.stored.model_dump(mode="json")["claims"][0]["evidence"][0]
    assert citation["start"] == 21 and citation["start"] > len(child.text)
    assert json.loads(citation["locator"][4:])["source_view_id"] == 6
    link = _evidence_link(
        {"id": 10}, {"frame": frame}, citation["start"], citation["end"], citation["locator"]
    )
    assert isinstance(link, NativeEvidenceLink)
    assert link.source_view_id == 6 and link.start == 21
    assert native_statement_source(frame, statement_anchor(handle, frame)).unit_ref == "native:6"
    roundtrip = native_frame_from_dict(asdict(frame))
    assert roundtrip == frame
    with pytest.raises(ValueError, match="direct ancestor"):
        replace(frame, context_sources=(replace(parent_source, membership="descendants"),))


def test_native_parent_premise_survives_submission_custody_and_independent_grade(
    commit_db_engine, commit_writer_engine, commit_evaluator_engine, tmp_path
):
    from dataclasses import asdict, replace

    from corpus_structure.semantic.proposals import native_address, native_frame_source
    from corpus_structure.semantic.source_projection import statement_identity

    prepared, run, task, child, key = native_build_resubmission_case(
        commit_db_engine, commit_writer_engine, tmp_path, ancestor=True
    )
    with commit_writer_engine.connect() as conn:
        parent, selected_child, sibling = conn.scalars(
            text(
                "SELECT source_view_id FROM ops.run_source_view WHERE run_id=:run ORDER BY position"
            ),
            {"run": run},
        ).all()
        assert selected_child == child
        parent_view = load_source_view(conn, parent)
        child_view = load_source_view(conn, child)
        sibling_view = load_source_view(conn, sibling)

    def claims(prefix, child_handle, parent_handle):
        value = authored(key, child_handle, prefix)
        value["statements"].append(
            dict(id=prefix + "_assumption", kind="assumption", anchor=parent_handle)
        )
        premise = dict(
            id=prefix + "_premise",
            subject=prefix + "_person",
            predicate="https://example.org/name",
            object={"kind": "text", "text": "Alice"},
            qualification={"modality": "supposed", "polarity": True},
            establishment="stated",
            statement=prefix + "_assumption",
            statement_role="premise",
            evidence=[dict(sentence=parent_handle, quote="Alice is here.", role="primary")],
        )
        value["claims"][0]["qualification"]["condition"] = {"kind": "claim", "ref": premise["id"]}
        value["claims"].insert(0, premise)
        return value

    async def submit():
        async with Client(
            build_semantic_server(SemanticAgentSession(commit_writer_engine, run))
        ) as client:
            unit = await lease_and_read(client, run, task)
            contexts = unit["native_source"]["context_sources"]
            assert [source["source_view_id"] for source in contexts] == [parent]
            handle = contexts[0]["native_evidence"][0]["handle"]
            result = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": claims(
                        "prediction", unit["native_source"]["native_evidence"][0]["handle"], handle
                    ),
                },
            )
            assert result.structured_content is not None
            assert result.structured_content["submission_disposition"] == "completed_accepted"

    anyio.run(submit)
    finalize_bound_run(commit_writer_engine, run, "native-parent-result")
    parent_frame = native_source_frame(
        parent_view, [("reference_parent", 0, len(parent_view.text))]
    )
    frame = replace(
        native_source_frame(child_view, [("reference_child", 0, len(child_view.text))]),
        context_sources=(native_frame_source(parent_frame),),
    )
    parent_handle = f"native_context:{parent}:reference_parent"
    expected = canonical_bytes(claims("reference", "reference_child", parent_handle))
    parent_locator = native_address(parent_frame, start=0, end=len(parent_view.text))
    expected_statement = statement_identity(
        prepared.release_id, "native-parent-result", parent_view.ref.key, parent_locator
    )
    with commit_writer_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT es.native_address FROM data.evidence_source es\n"
                "            JOIN kb.observation observation ON "
                "observation.id=es.observation_id\n"
                "            WHERE observation.task_id=:task AND "
                "observation.source_view_id=:child AND es.source_view_id=:parent"
            ),
            dict(task=task, child=child, parent=parent),
        ).scalar_one()
        address = json.loads(row[4:])
        assert (
            address["source_view_id"] == parent
            and address["end"] == 22
            and address["end"] > len(child_view.text)
        )
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM data.occurrence_context WHERE "
                    "statement_entity_id=:statement AND statement_role='premise'"
                ),
                {"statement": expected_statement},
            )
            == 1
        )
        assert conn.scalar(text("SELECT to_regclass('kb.rendition')")) is None
    with commit_evaluator_engine.begin() as conn:
        split_documents(conn, "native-consumer")
        made = create_reference_set(
            conn,
            project_id="native-consumer",
            source_run_id=run,
            label="parent-independent",
            split="dev",
            size=1,
            forced=(key,),
        )
        unit = made["units"][key]
        for kind in ("A", "B", "C"):
            last_pass = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor="automated-parent-" + kind,
                authored=expected,
                frame=frame,
            )
        result = reference_evaluate(
            conn, project_id="native-consumer", run_id=run, set_id=made["set_id"]
        )
        assert result.result["tiers"]["full"]["reference"] == 2
        assert result.result["tiers"]["full"]["prediction"] == 2
        assert result.result["tiers"]["full"]["matched"] == 2
        entries = conn.scalar(
            text("SELECT frame FROM eval.reference_frame WHERE pass_id=:pass"), {"pass": last_pass}
        )
        # Bypass Python constructors to exercise the SQL source association authority.
        sibling_frame = native_source_frame(
            sibling_view, [("forged_sibling", 0, len(sibling_view.text))]
        )
        forged: dict[str, Any] = asdict(frame)
        forged["context_sources"] = [asdict(native_frame_source(sibling_frame))]
        with (
            pytest.raises(DBAPIError, match="selected same-product direct ancestor"),
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "SELECT "
                    "eval.record_native_reference_pass(:unit,'C','forged-siblin"
                    "g',:authored,CAST(:entries AS jsonb),CAST(:frame AS jsonb))"
                ),
                dict(
                    unit=unit,
                    authored=expected,
                    entries=json.dumps(entries),
                    frame=json.dumps(forged),
                ),
            )
        forged = asdict(frame)
        forged["context_sources"][0]["native_product"]["content_digest"] = "f" * 64
        with (
            pytest.raises(DBAPIError, match="source differs from immutable view"),
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "SELECT "
                    "eval.record_native_reference_pass(:unit,'C','forged-produc"
                    "t',:authored,CAST(:entries AS jsonb),CAST(:frame AS jsonb))"
                ),
                dict(
                    unit=unit,
                    authored=expected,
                    entries=json.dumps(entries),
                    frame=json.dumps(forged),
                ),
            )

        import copy

        wrong_source = copy.deepcopy(entries)
        premise = next(entry for entry in wrong_source if entry["item_ref"] == "reference_premise")
        premise.update(locator=frame.sentences[0].locator, start=0, end=14)
        with (
            pytest.raises(DBAPIError, match="outside supplied independent sentences"),
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "SELECT "
                    "eval.record_native_reference_pass(:unit,'C','cross-source-"
                    "handle',:authored,CAST(:entries AS jsonb),CAST(:frame AS jsonb))"
                ),
                dict(
                    unit=unit,
                    authored=expected,
                    entries=json.dumps(wrong_source),
                    frame=json.dumps(asdict(frame)),
                ),
            )
