"""Independent native field/span authentication with admitted source-record custody."""

import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import SourceArtifact, SourceBundle
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.interpretations import metadata_binding
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.query import read_snapshot
from semantic.native_record_fixtures import private_source as private_source

from .native_record_fixtures import candidate, complete


@pytest.fixture
def private_source_options():
    def transform(bundle):
        path = Path(__file__).parents[4] / "domains/statistics/terminology.yaml"
        body = yaml.safe_load(path.read_bytes())
        body["imports"] = ["core"]
        sources = []
        for source in bundle.sources:
            if source.name == bundle.root:
                root = yaml.safe_load(source.content)
                root["imports"].append(body["name"])
                source = SourceArtifact(source.name, yaml.safe_dump(root).encode())
            sources.append(source)
        return SourceBundle(
            bundle.root, (*sources, SourceArtifact(body["name"], yaml.safe_dump(body).encode()))
        )

    def captured_dependencies(dependencies):
        from dataclasses import replace

        from corpus_structure.semantic.terminology import acquire_terminology

        _, artifacts, ontology_names = acquire_terminology(
            Path(__file__).parents[4] / "domains/statistics"
        )
        return replace(
            dependencies,
            artifacts=(*dependencies.artifacts, *artifacts),
            ontology_sources=(*dependencies.ontology_sources, *ontology_names),
        )

    return {"bundle_transform": transform, "dependencies_transform": captured_dependencies}


def test_native_interpretation_source_field_span_and_vocabulary_closure(
    private_source, semantic_db_engine
):
    case = private_source
    record = candidate(case)
    with case.writer.begin() as conn:
        complete(case, conn, (record,))
        cut = seal_cut(conn, case.run, "source-final", final=True)
    result = consolidate_cut(case.writer, cut, "interpretation-source-result")
    anchor = record["anchors"][0]
    digest, _ = metadata_binding(case.prepared)
    payload = dict(
        source_record=dict(
            project_id="private-records",
            run_id=case.run,
            cut_id=cut,
            release_id=case.prepared.release_id,
            realization_id=result.realization_id,
            data_revision=1,
            record_id=record["record_id"],
            interpretation_id=record["interpretation_id"],
            source_view_id=case.view,
        ),
        vocabulary_release=case.prepared.release_id,
        metadata_digest=digest,
        lookup_policy="released-lexical-1",
        decisions=[
            dict(
                field="distribution_family",
                focus=dict(
                    role="value", anchor_id=anchor["anchor_id"], start=0, end=2, source_piece="12"
                ),
                candidates=[
                    dict(
                        value="normal",
                        meaning="STATO:0000227",
                        label="normal distribution",
                        matching_field="browse",
                        matching_predicate="",
                    )
                ],
                outcome="selected",
                selected_value="normal",
                mapping_predicate="http://www.w3.org/2004/02/skos/core#closeMatch",
                mapping_direction="source_to_term",
                assessment=(
                    "Controlled source-authentication case; "
                    "this test makes no scientific mapping claim."
                ),
                reviewer="independent-control",
            )
        ],
    )
    contribution = dict(
        kind="proposal",
        semantic_type="terminology.interpretation",
        pin=record["pin"],
        anchors=[anchor],
    )
    statement = text(
        "SELECT ops.require_source_interpretation(:task,"
        "CAST(:contribution AS jsonb),CAST(:payload AS jsonb))"
    )
    with semantic_db_engine.begin() as conn:
        from sqlalchemy import select

        from corpus_structure.semantic.metadata import table

        revision = conn.scalar(
            select(table("data.realization").c.data_revision).where(
                table("data.realization").c.realization_id == result.realization_id
            )
        )
        payload["source_record"]["data_revision"] = revision
        conn.execute(
            statement,
            dict(
                task=case.task, contribution=json.dumps(contribution), payload=json.dumps(payload)
            ),
        )
        for mutation in (
            "cut",
            "field",
            "span",
            "metadata",
            "candidate",
            "selection",
            "direction",
            "matching_predicate",
        ):
            changed = json.loads(json.dumps(payload))
            if mutation == "cut":
                changed["source_record"]["cut_id"] += 10000
            elif mutation == "field":
                changed["decisions"][0]["focus"]["role"] = "location"
            elif mutation == "span":
                changed["decisions"][0]["focus"]["source_piece"] = "13"
            elif mutation == "metadata":
                changed["metadata_digest"] = "0" * 64
            elif mutation == "candidate":
                changed["decisions"][0]["candidates"][0]["meaning"] = "STATO:wrong"
            elif mutation == "selection":
                changed["decisions"][0]["selected_value"] = "poisson"
            elif mutation == "direction":
                changed["decisions"][0]["mapping_direction"] = "term_to_source"
            else:
                changed["decisions"][0]["candidates"][0]["matching_predicate"] = "invented"
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    statement,
                    dict(
                        task=case.task,
                        contribution=json.dumps(contribution),
                        payload=json.dumps(changed),
                    ),
                )


def test_authored_review_completion_filter_and_selected_root_ambiguity(private_source, tmp_path):
    from typing import Any

    from sqlalchemy import select

    from corpus_structure.semantic.interpretation_queries import TerminologySelection
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.serve.interpretation_authoring import author_interpretations
    from corpus_structure.serve.record_results import RecordRequest, serve_record_results
    from corpus_structure.settings import Settings

    case = private_source
    records = (candidate(case), candidate(case, 1))
    with case.writer.begin() as conn:
        complete(case, conn, records)
        cut = seal_cut(conn, case.run, "source-final", final=True)
    result = consolidate_cut(case.writer, cut, "review-filter-source-result")
    digest, _ = metadata_binding(case.prepared)
    with read_snapshot(case.writer) as conn:
        revision = conn.scalar(
            select(table("data.realization").c.data_revision).where(
                table("data.realization").c.realization_id == result.realization_id
            )
        )
    reviews: list[dict[str, Any]] = []
    for i, record in enumerate((records[0], records[0], records[1])):
        anchor = record["anchors"][0]
        reviews.append(
            dict(
                source_record=dict(
                    project_id="private-records",
                    run_id=case.run,
                    cut_id=cut,
                    release_id=case.prepared.release_id,
                    realization_id=result.realization_id,
                    data_revision=revision,
                    record_id=record["record_id"],
                    interpretation_id=record["interpretation_id"],
                    source_view_id=case.view,
                ),
                vocabulary_release=case.prepared.release_id,
                metadata_digest=digest,
                lookup_policy="released-lexical-1",
                decisions=[
                    dict(
                        field="distribution_family",
                        focus=dict(
                            role="value",
                            anchor_id=anchor["anchor_id"],
                            start=0,
                            end=2,
                            source_piece="12",
                        ),
                        candidates=[
                            dict(
                                value="normal",
                                meaning="STATO:0000227",
                                label="normal distribution",
                                matching_field="browse",
                                matching_predicate="",
                            )
                        ],
                        outcome="selected",
                        selected_value="normal",
                        mapping_predicate="http://www.w3.org/2004/02/skos/core#"
                        + ("closeMatch" if i == 0 else "exactMatch"),
                        mapping_direction="source_to_term",
                        assessment=(
                            "Controlled source/selection test, not a scientific mapping claim."
                        ),
                        reviewer="independent-control",
                    )
                ],
            )
        )
    from corpus_structure.semantic.structural_sources import (
        StructuralPassageSelection,
        prepare_structural_sources,
    )

    original = prepare_structural_sources(
        case.writer,
        [
            StructuralPassageSelection(
                run_id=case.run,
                source_view_id=case.view,
                passage_id="controlled-source",
                start=0,
                end=2,
                scope="controlled native completion test",
            )
        ],
    ).sources[0]
    configuration: dict[str, Any] = dict(
        source=original.model_dump(mode="json"),
        reviews=reviews,
    )
    authored = author_interpretations(
        case.writer,
        case.prepared,
        kind="terminology",
        configuration=configuration,
        settings=Settings(paths={"data_dir": tmp_path, "model_cache": tmp_path / "models"}),
    )
    selection = TerminologySelection(
        review_run_id=authored["run_id"],
        review_cut_id=authored["cut_id"],
        vocabulary_release=case.prepared.release_id,
        field="distribution_family",
        value="normal",
    )
    with read_snapshot(case.writer) as conn:
        second = serve_record_results(
            conn,
            RecordRequest(
                run_id=case.run, record_id=records[1]["record_id"], terminology=selection
            ),
        )
        assert second.matching_records == 1 and len(second.records) == 1
        assert len(second.records[0].terminology_reviews) == 1
        assert second.records[0].record["record_id"] == records[1]["record_id"]
        with pytest.raises(SemanticRefusal, match="multiple field reviews"):
            serve_record_results(
                conn,
                RecordRequest(
                    run_id=case.run, record_id=records[0]["record_id"], terminology=selection
                ),
            )
    # Later record-result custody is distinct from the original coordinate authority.
    # Retain another located record through the ordinary authored-record producer,
    # then review that later result while selecting its ORIGINAL source reference.
    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        interpretation_identity,
        record_identity,
    )

    later_record = candidate(case, 1)
    later_pin = dict(later_record["pin"], source=case.view_row["key"])
    anchor_ids = {}
    for anchor in later_record["anchors"]:
        old_id = anchor["anchor_id"]
        anchor["pin"] = later_pin
        anchor["anchor_id"] = anchor_identity(anchor)
        anchor_ids[old_id] = anchor["anchor_id"]
    set_ids = {}
    for evidence in later_record["evidence_sets"]:
        old_id = evidence["set_id"]
        evidence["anchors"] = tuple(anchor_ids[a] for a in evidence["anchors"])
        evidence["set_id"] = evidence_set_identity(evidence)
        set_ids[old_id] = evidence["set_id"]
    for field in later_record["fields"]:
        field["evidence_sets"] = tuple(set_ids[s] for s in field["evidence_sets"])
    later_record["pin"] = later_pin
    later_record["occurrence_anchors"] = tuple(
        anchor_ids[a] for a in later_record["occurrence_anchors"]
    )
    later_record["record_id"] = record_identity(case.prepared.release_id, later_record)
    later_record["interpretation_id"] = interpretation_identity(later_record)
    later = author_interpretations(
        case.writer,
        case.prepared,
        kind="source_records",
        configuration=dict(
            source=configuration["source"], records=[json.loads(json.dumps(later_record))]
        ),
        settings=Settings(paths={"data_dir": tmp_path, "model_cache": tmp_path / "models"}),
    )
    with read_snapshot(case.writer) as conn:
        later_revision = conn.scalar(
            select(table("data.realization").c.data_revision).where(
                table("data.realization").c.realization_id == later["realization_id"]
            )
        )
    later_reference = dict(
        reviews[-1]["source_record"],
        run_id=later["run_id"],
        cut_id=later["cut_id"],
        realization_id=later["realization_id"],
        data_revision=later_revision,
        record_id=later_record["record_id"],
        interpretation_id=later_record["interpretation_id"],
    )
    later_focus = dict(
        reviews[-1]["decisions"][0]["focus"], anchor_id=later_record["anchors"][0]["anchor_id"]
    )
    # A selected measurement contributes two distinct vocabulary uses. An unresolved
    # review retains both empty dimensions, rather than disappearing from coverage.
    measurement = dict(
        source_record=later_reference,
        focus=later_focus,
        vocabulary_release=case.prepared.release_id,
        metadata_digest=digest,
        outcome="selected",
        unit="HOUR",
        quantity_kind="TIME",
        basis_status="unknown",
        assessment="Controlled identifier-use survey, not a scientific measurement claim.",
        reviewer="independent-control",
        numerical_equivalence="unassessed",
    )
    unresolved = {k: v for k, v in measurement.items() if k not in {"unit", "quantity_kind"}}
    unresolved["outcome"] = "unresolved"
    measured = author_interpretations(
        case.writer,
        case.prepared,
        kind="measurement",
        configuration=dict(source=configuration["source"], reviews=[measurement, unresolved]),
        settings=Settings(paths={"data_dir": tmp_path, "model_cache": tmp_path / "models"}),
    )
    from corpus_structure.semantic.interpretation_queries import collect_interpretation_uses

    with read_snapshot(case.writer) as conn:
        bound = dict(
            source_run_id=later["run_id"],
            review_run_id=measured["run_id"],
            review_cut_id=measured["cut_id"],
            vocabulary_release=case.prepared.release_id,
        )
        uses = collect_interpretation_uses(conn, **bound)
        assert uses["complete"] and len(uses["items"]) == 4
        assert {row["semantic_type"] for row in uses["items"]} == {"measurement.interpretation"}
        assert {(row["field"], row["selected_value"]) for row in uses["items"]} == {
            ("unit", "HOUR"),
            ("quantity_kind", "TIME"),
            ("unit", None),
            ("quantity_kind", None),
        }
        first = collect_interpretation_uses(conn, **bound, limit=2)
        assert not first["complete"] and len(first["items"]) == 2
        second = collect_interpretation_uses(
            conn, **bound, limit=2, after=tuple(first["next_after"])
        )
        assert second["complete"] and first["items"] + second["items"] == uses["items"]
        hours = collect_interpretation_uses(conn, **bound, enum="RecognizedTimeUnit", member="HOUR")
        assert hours["complete"] and len(hours["items"]) == 1
        assert hours["items"][0]["field"] == "unit"

    forged_source = dict(configuration["source"], native_content_digest="0" * 64)
    with pytest.raises(DBAPIError, match="original completed source custody"):
        author_interpretations(
            case.writer,
            case.prepared,
            kind="measurement",
            configuration=dict(source=forged_source, reviews=[measurement]),
            settings=Settings(paths={"data_dir": tmp_path, "model_cache": tmp_path / "models"}),
        )
