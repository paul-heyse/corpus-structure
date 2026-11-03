"""Actual sealed-cut record publication and native refusal controls.

Requires the coherent forward native candidate, never edits frozen100 or a live default.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, cast

import pytest
from sqlalchemy import bindparam, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import CoverageDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.analytics import compile_projection
from corpus_structure.semantic.arrow_publication import AppendPublication, stage_arrow
from corpus_structure.semantic.domain_operations import _cut_input, consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import complete_unit_result, seal_cut
from corpus_structure.semantic.record_projection import RECORD_ROW_TYPES, reconstruct_record

from .test_private_records import candidate, complete
from .test_private_records import private_source as private_source


def record_cut(case, *, empty=False):
    with case.writer.begin() as conn:
        if empty:
            complete_unit_result(
                conn,
                task_id=case.task,
                attempt=case.held.attempt,
                holder="records",
                prepared=case.prepared,
                method=case.method,
                configuration_hash="private-config",
                source="private-unit",
                result=UnitResult(
                    ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                    outcome=ObservationOutcome.EMPTY,
                    coverage=(
                        CoverageDraft(
                            family="table",
                            scope="private-unit",
                            outcome="complete",
                            reason="controlled inspection completed with empty record output",
                        ),
                    ),
                ),
                records=(),
            )
        else:
            complete(case, conn, (candidate(case), candidate(case, 1, projected=True)))
        return seal_cut(conn, case.run, "records-final", final=True)


def test_actual_cut_records_publish_without_graph_product_membership(private_source):
    case = private_source
    cut = record_cut(case)
    result = consolidate_cut(case.writer, cut, "public-record-result")
    assert consolidate_cut(case.writer, cut, "public-record-result") == result
    with case.writer.connect() as conn:
        rows = {
            name: conn.execute(
                select(table("data." + name)).where(
                    table("data." + name).c.realization_id == result.realization_id,
                    table("data." + name).c.release_id == case.prepared.release_id,
                )
            )
            .mappings()
            .all()
            for name in RECORD_ROW_TYPES
        }
        assert len(rows["source_record"]) == 2
        assert len(rows["record_admission"]) == 2
        assert rows["record_assertion"] == []
        assert len(rows["record_report"]) == 2  # native producer absence + record report
        assert {row["records_present"] for row in rows["record_report"]} == {False, True}
        for original in (candidate(case), candidate(case, 1, projected=True)):
            restored = reconstruct_record(
                rows, original["record_id"], original["interpretation_id"]
            )
            assert restored == original
        assert not conn.execute(
            select(table("data.membership")).where(
                table("data.membership").c.realization_id == result.realization_id
            )
        ).all()
        assert not conn.execute(
            select(table("data.typed_value")).where(
                table("data.typed_value").c.realization_id == result.realization_id
            )
        ).all()
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.publication_intent WHERE realization_id=:z"),
                {"z": result.realization_id},
            )
            == 1
        )


def test_completed_empty_cut_keeps_report_and_routing_coverage(private_source):
    case = private_source
    cut = record_cut(case, empty=True)
    result = consolidate_cut(case.writer, cut, "public-record-empty")
    with case.writer.connect() as conn:
        reports = (
            conn.execute(
                select(table("data.record_report")).where(
                    table("data.record_report").c.realization_id == result.realization_id
                )
            )
            .mappings()
            .all()
        )
        assert len(reports) == 2
        assert sum(report["records_present"] for report in reports) == 1
        assert not conn.execute(
            select(table("data.source_record")).where(
                table("data.source_record").c.realization_id == result.realization_id
            )
        ).all()
        coverage = (
            conn.execute(
                select(table("data.coverage")).where(
                    table("data.coverage").c.realization_id == result.realization_id
                )
            )
            .mappings()
            .all()
        )
        assert any(
            (row["family"], row["scope"], row["outcome"], row["source_outcome"])
            == ("table", "private-unit", "complete", "complete")
            for row in coverage
        )


def test_native_tampering_accepted_standing_and_append_refuse_atomically(private_source):
    case = private_source
    cut = record_cut(case)
    inputs = _cut_input(case.writer, cut, "public-record-forgery")
    compiled = compile_projection(case.prepared, inputs.source_binding, kind="candidate")
    # Probe native enforcement using the supported explicit-row transport. A forged
    # row cannot retain the analytical preparation witness for the original rows.
    clean = replace(inputs.batch, _analysis_input=None)
    from corpus_structure.semantic.record_projection import project_record_reports

    all_empty = project_record_reports(case.prepared, ())
    changes = [
        replace(
            clean,
            record_field=(
                replace(clean.record_field[0], decimal_lexical="13"),
                *clean.record_field[1:],
            ),
        ),
        replace(
            clean,
            record_anchor=(
                replace(clean.record_anchor[0], source_piece="13"),
                *clean.record_anchor[1:],
            ),
        ),
        replace(
            clean,
            record_admission=(
                replace(clean.record_admission[0], decision="accepted"),
                *clean.record_admission[1:],
            ),
        ),
        replace(clean, **all_empty),
        replace(clean, record_report_member=()),
        replace(clean, record_report=()),
    ]
    with (
        case.writer.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin() as transaction,
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"),
            {"cut": cut, "out": inputs.output_realization_id},
        )
        for batch in changes:
            with pytest.raises(DBAPIError), conn.begin_nested():
                transport = AppendPublication.from_rows(batch)
                stage_arrow(conn, transport)
                conn.execute(
                    text(
                        "SELECT data.publish_derived_batch_v2(:r,:z,:b,:content,:sr,:sz,:revision,"
                        ":capture,'evaluate',:projection,'candidate',:cut,:profile)"
                    ),
                    dict(
                        r=case.prepared.release_id,
                        z=inputs.output_realization_id,
                        b=transport.batch_id,
                        content=transport.content,
                        sr=inputs.source_binding.release_id,
                        sz=inputs.source_binding.realization_id,
                        revision=inputs.source_binding.data_revision,
                        capture=inputs.source_binding.capture_id,
                        projection=compiled.projection_id,
                        cut=cut,
                        profile=compiled.profile.digest,
                    ),
                )
        with pytest.raises(DBAPIError, match="sealed-cut derived publication"), conn.begin_nested():
            transport = AppendPublication.from_rows(clean)
            stage_arrow(conn, transport)
            conn.execute(
                text("SELECT data.publish_batch(:r,:z,:b,:content)"),
                dict(
                    r=case.prepared.release_id,
                    z=inputs.output_realization_id,
                    b=transport.batch_id,
                    content=transport.content,
                ),
            )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.batch WHERE realization_id=:z"),
                {"z": inputs.output_realization_id},
            )
            == 0
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.source_record WHERE realization_id=:z"),
                {"z": inputs.output_realization_id},
            )
            == 0
        )
        transaction.rollback()


def test_shared_structure_accepts_complete_reference_but_public_policy_still_refuses(
    private_source, semantic_db_engine
):
    """Structural correctness is shared; evaluator/public authority remains separate."""
    from copy import deepcopy

    from sqlalchemy.dialects.postgresql import JSONB

    from .test_private_records import identities

    case = private_source
    expected = candidate(case)
    expected["standing"] = "accepted"
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        statement = text("SELECT data.validate_source_record_structure(:r,:record)").bindparams(
            bindparam("record", type_=JSONB)
        )
        conn.execute(statement, {"r": case.prepared.release_id, "record": expected})
        public = text("SELECT data.validate_record_relationships(:r,:record)").bindparams(
            bindparam("record", type_=JSONB)
        )
        with pytest.raises(DBAPIError, match="candidate-only"), conn.begin_nested():
            conn.execute(public, {"r": case.prepared.release_id, "record": expected})
        mutations = []
        missing = deepcopy(expected)
        missing["fields"][0].update(
            state="unstated", reason="not stated", evidence_status="unavailable", evidence_sets=()
        )
        for key in ("value", "original"):
            missing["fields"][0].pop(key)
        mutations.append((missing, "accepted record"))
        cyclic = deepcopy(expected)
        cyclic["fields"][0]["premises"] = ("location",)
        cyclic["fields"][1]["premises"] = ("value",)
        mutations.append((cyclic, "form a cycle"))
        dangling = deepcopy(expected)
        dangling["fields"][0]["premises"] = ("missing-role",)
        mutations.append((dangling, "premise role is unavailable"))
        metadata_premise = deepcopy(expected)
        metadata_premise["fields"][0]["premises"] = ("family",)
        mutations.append((metadata_premise, "premise role is unavailable"))
        metadata_role = deepcopy(expected)
        metadata_role["evidence_sets"][0]["role"] = "family"
        mutations.append((metadata_role, "role or anchor membership"))
        duplicate_role = deepcopy(expected)
        duplicate_role["fields"] = (*duplicate_role["fields"], duplicate_role["fields"][0])
        mutations.append((duplicate_role, "family roles or collection identities"))
        duplicate_anchor = deepcopy(expected)
        duplicate_anchor["anchors"] = (*duplicate_anchor["anchors"], duplicate_anchor["anchors"][0])
        mutations.append((duplicate_anchor, "family roles or collection identities"))
        alternative = deepcopy(expected)
        alternative["fields"][0]["alternatives"] = (
            dict(
                alternative_id="alternative-1",
                value=dict(kind="decimal", lexical="13"),
                reason="counterreading",
                evidence_sets=("missing-set",),
            ),
        )
        mutations.append((alternative, "alternative evidence membership"))
        for forged, message in mutations:
            identities(case, forged)
            with pytest.raises(DBAPIError, match=message), conn.begin_nested():
                conn.execute(statement, {"r": case.prepared.release_id, "record": forged})
        altered_assertion = deepcopy(expected)
        altered_assertion["assertion_members"] = ("private:altered-without-identity",)
        with (
            pytest.raises(DBAPIError, match="interpretation identity differs"),
            conn.begin_nested(),
        ):
            conn.execute(statement, {"r": case.prepared.release_id, "record": altered_assertion})
    with case.writer.connect() as conn, pytest.raises(DBAPIError, match="permission denied"):
        conn.execute(statement, {"r": case.prepared.release_id, "record": expected})


def test_shared_structure_requires_each_complete_literal_set_in_source_order(
    private_source, semantic_db_engine
):
    from copy import deepcopy

    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity

    from .test_private_records import identities

    case = private_source
    expected = candidate(case)
    expected["standing"] = "accepted"
    second = deepcopy(candidate(case, 1)["anchors"][0])
    expected["anchors"] = (*expected["anchors"], second)
    evidence = expected["evidence_sets"][0]
    evidence["anchors"] = (*evidence["anchors"], second["anchor_id"])
    evidence["set_id"] = evidence_set_identity(evidence)
    field = expected["fields"][0]
    field.pop("original")
    field.update(
        original_pieces=("12", "12"),
        value=dict(kind="text_sequence", items=("12", "12")),
        evidence_sets=(evidence["set_id"],),
    )
    identities(case, expected)
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        statement = text("SELECT data.validate_source_record_structure(:r,:record)").bindparams(
            bindparam("record", type_=JSONB)
        )
        conn.execute(statement, {"r": case.prepared.release_id, "record": expected})
        unordered = deepcopy(expected)
        unordered["evidence_sets"][0]["ordering"] = "unordered"
        unordered["evidence_sets"][0]["set_id"] = evidence_set_identity(
            unordered["evidence_sets"][0]
        )
        unordered["fields"][0]["evidence_sets"] = (unordered["evidence_sets"][0]["set_id"],)
        identities(case, unordered)
        with pytest.raises(DBAPIError, match="requires ordered"), conn.begin_nested():
            conn.execute(statement, {"r": case.prepared.release_id, "record": unordered})
        mismatch = deepcopy(expected)
        mismatch["fields"][0].update(
            original_pieces=("12", "13"), value=dict(kind="text_sequence", items=("12", "13"))
        )
        identities(case, mismatch)
        with (
            pytest.raises(DBAPIError, match="reconstruct complete evidence set"),
            conn.begin_nested(),
        ):
            conn.execute(statement, {"r": case.prepared.release_id, "record": mismatch})
        overlap = deepcopy(expected)
        repeated = overlap["anchors"][-1]
        previous_id = repeated["anchor_id"]
        repeated.update(
            pointer=overlap["anchors"][0]["pointer"],
            binding=dict(version=2, relationship="primary", policy="attributed-selected-source-2"),
        )
        repeated["anchor_id"] = anchor_identity(repeated)
        overlap["evidence_sets"][0]["anchors"] = tuple(
            repeated["anchor_id"] if aid == previous_id else aid
            for aid in overlap["evidence_sets"][0]["anchors"]
        )
        overlap["evidence_sets"][0]["set_id"] = evidence_set_identity(overlap["evidence_sets"][0])
        overlap["fields"][0]["evidence_sets"] = (overlap["evidence_sets"][0]["set_id"],)
        identities(case, overlap)
        with pytest.raises(DBAPIError, match="overlap or reverse"), conn.begin_nested():
            conn.execute(statement, {"r": case.prepared.release_id, "record": overlap})


def test_completed_public_reader_pins_detached_projection_and_retains_source_selectors(
    private_source, semantic_reader_engine
):
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.record_queries import read_completed_record_projection
    from corpus_structure.semantic.refusals import SemanticRefusal

    case = private_source
    cut = record_cut(case)
    result = consolidate_cut(case.writer, cut, "public-reader-result")
    with read_snapshot(semantic_reader_engine) as conn:
        packet = read_completed_record_projection(
            conn, run_id=case.run, project_id="private-records"
        )
        assert packet.run_id == case.run
        assert packet.release_id == case.prepared.release_id
        assert packet.realization_id == result.realization_id
        assert packet.data_revision == result.data_revision
        assert packet.binding.capture_id == f"cut:{cut}"
        assert packet.binding.release_id == case.prepared.release_id
        assert packet.binding.realization_id == result.realization_id
        assert packet.cut_id == cut
        assert packet.source_view_ids is None
        assert packet.projection_digest == next(
            artifact.digest
            for artifact in packet.prepared.artifacts
            if artifact.kind == "record_projection.json"
        )
        assert packet.report_source_view_ids == {case.task: case.view}
        assert len(packet.rows["source_record"]) == 2
        assert len(packet.rows["record_report"]) == 2
        selected = read_completed_record_projection(
            conn, run_id=case.run, source_view_ids=(case.view,)
        )
        assert selected.source_view_ids == (case.view,)
        assert len(selected.rows["record_report"]) == 1
        assert selected.rows["record_report"][0].records_present is True
        assert selected.rows["source_record"] == packet.rows["source_record"]
        assert selected.report_source_view_ids == {case.task: case.view}
        missing = read_completed_record_projection(
            conn, run_id=case.run, source_view_ids=(case.other_view,)
        )
        assert missing.source_view_ids == (case.other_view,)
        assert missing.report_source_view_ids == {}
        assert all(not collection for collection in missing.rows.values())
        explicit_empty = read_completed_record_projection(conn, run_id=case.run, source_view_ids=())
        assert explicit_empty.source_view_ids == ()
        assert explicit_empty.report_source_view_ids == {}
        assert all(not collection for collection in explicit_empty.rows.values())
        with pytest.raises(SemanticRefusal, match="outside the completed run"):
            read_completed_record_projection(conn, run_id=case.run, source_view_ids=(10**15,))
    # Reconstruct after the snapshot/connection lifetime has ended: no lazy task/report reads.
    for original in (candidate(case), candidate(case, 1, projected=True)):
        assert (
            reconstruct_record(packet.rows, original["record_id"], original["interpretation_id"])
            == original
        )


def test_completed_public_reader_distinguishes_empty_report_from_missing_source(
    private_source, semantic_reader_engine
):
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.record_queries import read_completed_record_projection

    case = private_source
    cut = record_cut(case, empty=True)
    consolidate_cut(case.writer, cut, "public-reader-empty")
    with read_snapshot(semantic_reader_engine) as conn:
        present = read_completed_record_projection(
            conn, run_id=case.run, source_view_ids=(case.view,)
        )
        missing = read_completed_record_projection(
            conn, run_id=case.run, source_view_ids=(case.other_view,)
        )
    assert present.rows["source_record"] == missing.rows["source_record"] == ()
    assert len(present.rows["record_report"]) == 1
    assert present.rows["record_report"][0].outcome == "empty"
    assert present.rows["record_report"][0].records_present is True
    assert present.report_source_view_ids == {case.task: case.view}
    assert missing.rows["record_report"] == ()
    assert missing.report_source_view_ids == {}


def test_completed_public_reader_refuses_wrong_run_project_and_invalid_selectors(
    private_source, semantic_reader_engine
):
    from corpus_structure.semantic.operations import OperationBinding, create_run
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.record_queries import read_completed_record_projection
    from corpus_structure.semantic.refusals import SemanticRefusal

    case = private_source
    cut = record_cut(case)
    consolidate_cut(case.writer, cut, "public-reader-ownership")
    with case.writer.begin() as conn:
        unfinished = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(case.prepared.release_id, "private-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="reader-ownership-control",
        )
    with read_snapshot(semantic_reader_engine) as conn:
        for wrong_run in (unfinished, 10**15):
            with pytest.raises(SemanticRefusal, match="completed run/project"):
                read_completed_record_projection(
                    conn, run_id=wrong_run, project_id="private-records"
                )
        with pytest.raises(SemanticRefusal, match="completed run/project"):
            read_completed_record_projection(conn, run_id=case.run, project_id="other-project")
        with pytest.raises(ValueError, match="duplicate"):
            read_completed_record_projection(
                conn, run_id=case.run, source_view_ids=(case.view, case.view)
            )
        with pytest.raises(ValueError, match="positive integer"):
            read_completed_record_projection(conn, run_id=case.run, source_view_ids=(0,))
        with pytest.raises(ValueError, match="positive integers"):
            read_completed_record_projection(conn, run_id=case.run, max_records=0)
        with pytest.raises(ValueError, match="positive integers"):
            read_completed_record_projection(conn, run_id=case.run, max_rows=0)
        with pytest.raises(ValueError, match="positive integers"):
            read_completed_record_projection(conn, run_id=case.run, max_bytes=0)


def test_completed_public_reader_record_row_and_exact_serialized_byte_budgets(
    private_source, semantic_reader_engine
):
    import json
    from dataclasses import asdict

    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.record_queries import (
        RecordReadLimit,
        read_completed_record_projection,
    )

    case = private_source
    cut = record_cut(case)
    consolidate_cut(case.writer, cut, "public-reader-budgets")
    with read_snapshot(semantic_reader_engine) as conn:
        packet = read_completed_record_projection(conn, run_id=case.run)
        assert len(packet.rows["source_record"]) == 2
        row_collections: Mapping[str, Any] = packet.rows
        row_count = sum(len(collection) for collection in row_collections.values())
        # Independent whole-payload serialization checks the API's declared byte scope,
        # including every relation name/array/comma and source-map framing.
        raw = {
            name: [asdict(row) for row in collection]
            for name, collection in row_collections.items()
        }
        payload = dict(rows=raw, report_source_view_ids=dict(packet.report_source_view_ids))
        byte_count = len(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        )
        exact = read_completed_record_projection(
            conn, run_id=case.run, max_records=2, max_rows=row_count, max_bytes=byte_count
        )
        assert exact.rows == packet.rows
        with pytest.raises(RecordReadLimit, match="record count"):
            read_completed_record_projection(conn, run_id=case.run, max_records=1)
        with pytest.raises(RecordReadLimit, match="row count"):
            read_completed_record_projection(conn, run_id=case.run, max_rows=row_count - 1)
        with pytest.raises(RecordReadLimit, match="record bytes"):
            read_completed_record_projection(conn, run_id=case.run, max_bytes=byte_count - 1)
        with pytest.raises(RecordReadLimit, match="metadata bytes"):
            read_completed_record_projection(conn, run_id=case.run, max_bytes=1)
        # A refusal never poisons a caller's read scope or returns partial denominator data.
        assert read_completed_record_projection(conn, run_id=case.run).rows == packet.rows


def test_completed_public_reader_refuses_archive_without_record_projection(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    from importlib.resources import files

    from sqlalchemy import insert

    from corpus_structure.semantic import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
        prepare_release,
    )
    from corpus_structure.semantic.analytical_profile import analytical_inputs
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.domain_operations import domain_rule_inputs
    from corpus_structure.semantic.operations import OperationBinding, create_run
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.record_queries import read_completed_record_projection
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.releases import persist_release

    # This genuine immutable archive predates M1 *in declared capability*: it has no
    # SourceRecord definition/artifact. No retired compiler or modified archive is used.
    bundle = SourceBundle(
        "unprojected",
        (
            SourceArtifact(
                "unprojected",
                b"""id: https://example/unprojected
name: unprojected
imports: [semantic_core]
prefixes: {ex: "https://example/"}
default_prefix: ex
classes:
  Thing:
    attributes:
      name: {range: string}
""",
            ),
            SourceArtifact(
                "semantic_core",
                files("corpus_structure").joinpath("model/semantic/core.yaml").read_bytes(),
            ),
        ),
    )
    dependencies = domain_rule_inputs(ResolvedDependencies(), b"rules: []\n")
    bundle, dependencies = analytical_inputs(bundle, dependencies)
    dependencies = composed_dependencies(dependencies)
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    assert not any(artifact.kind == "record_projection.json" for artifact in prepared.artifacts)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="unprojected"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="unprojected",
                realization_id="unprojected-input",
                release_id=prepared.release_id,
            )
        )
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="unprojected",
            binding=OperationBinding(prepared.release_id, "unprojected-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="archive-reader-control",
        )
        cut = seal_cut(conn, run, "unprojected-final", final=True)
    consolidate_cut(semantic_writer_engine, cut, "unprojected-output")
    with (
        read_snapshot(semantic_reader_engine) as conn,
        pytest.raises(SemanticRefusal, match="no supported record projection"),
    ):
        read_completed_record_projection(conn, run_id=run, project_id="unprojected")


def test_completed_public_reader_selects_and_pages_roots_before_hydration(
    private_source, semantic_reader_engine
):
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.record_queries import (
        RecordReadLimit,
        RecordReadSelection,
        read_completed_record_projection,
    )

    case = private_source
    cut = record_cut(case)
    consolidate_cut(case.writer, cut, "public-reader-paged")
    with read_snapshot(semantic_reader_engine) as conn:
        with pytest.raises(RecordReadLimit):
            read_completed_record_projection(conn, run_id=case.run, max_records=1)
        first = read_completed_record_projection(
            conn,
            run_id=case.run,
            max_records=1,
            selection=RecordReadSelection(family="table", standing="candidate", limit=1),
        )
        assert first.matching_records == 2 and first.more_records
        assert len(first.rows["source_record"]) == 1
        assert len(first.rows["record_report_member"]) == 1
        assert len(first.rows["record_report"]) == 2
        key = (
            first.rows["source_record"][0].record_id,
            first.rows["source_record"][0].interpretation_id,
        )
        second = read_completed_record_projection(
            conn,
            run_id=case.run,
            max_records=1,
            selection=RecordReadSelection(family="table", standing="candidate", after=key, limit=1),
        )
        assert second.matching_records == 2 and not second.more_records
        assert len(second.rows["source_record"]) == 1
        assert second.rows["source_record"] != first.rows["source_record"]
        inspected = read_completed_record_projection(
            conn,
            run_id=case.run,
            max_records=1,
            selection=RecordReadSelection(record_id=key[0], interpretation_id=key[1]),
        )
        assert inspected.matching_records == 1 and not inspected.more_records
        assert inspected.rows["source_record"] == first.rows["source_record"]
        row_relations = cast(Mapping[str, Sequence[Any]], inspected.rows)
        assert all(
            (row.record_id, row.interpretation_id) == key
            for name, values in row_relations.items()
            if name not in {"record_report"}
            for row in values
        )
