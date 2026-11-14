"""Independent native field/span authentication with admitted source-record custody."""

import json

import pytest
import yaml
from native_refusals import native_refusal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import SourceBundle
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.interpretations import metadata_binding
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.query import read_snapshot
from semantic.native_admission_scenarios import InterpretationSourceRecipe
from semantic.native_record_fixtures import RecordSourceRecipe, candidate, complete
from semantic.native_record_fixtures import private_source as private_source


@pytest.fixture
def interpretation_source_case(scenario_seeds):
    with scenario_seeds.rollback_family(InterpretationSourceRecipe()) as family:
        case, _, cut = family.stage.bind(family.reader)
        yield case, cut, family.stage.result, family.stage.data_revision, family.connection


@pytest.mark.parametrize(
    "mutation",
    (
        "cut",
        "field",
        "span",
        "metadata",
        "candidate",
        "selection",
        "direction",
        "matching_predicate",
    ),
)
def test_native_interpretation_source_field_span_and_vocabulary_closure(
    interpretation_source_case, mutation
):
    case, cut, result, revision, conn = interpretation_source_case
    record = candidate(case)
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
    payload["source_record"]["data_revision"] = revision
    with conn.begin_nested() as positive:
        conn.execute(
            statement,
            dict(
                task=case.task, contribution=json.dumps(contribution), payload=json.dumps(payload)
            ),
        )
        positive.rollback()
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
    expected = {
        "cut": "interpretation source record differs from completed pinned result",
        "field": "interpretation focus does not authenticate record field source span",
        "span": "interpretation focus does not authenticate record field source span",
        "metadata": "interpretation vocabulary metadata pins differ",
        "candidate": "candidate differs from released vocabulary",
        "selection": "selected terminology mapping lacks examined candidate or predicate",
        "direction": "selected terminology mapping lacks examined candidate or predicate",
        "matching_predicate": "candidate matching field or predicate differs from source metadata",
    }[mutation]
    with native_refusal("23514", message=expected), conn.begin_nested():
        conn.execute(
            statement,
            dict(
                task=case.task, contribution=json.dumps(contribution), payload=json.dumps(changed)
            ),
        )
    # This validation-only boundary must preserve the completed source receipt.
    assert (
        conn.scalar(
            text("SELECT count(*) FROM ops.task_result WHERE task_id=:task"), {"task": case.task}
        )
        == 1
    )


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="interpretations")],
    indirect=True,
    ids=("record-interpretations",),
)
def test_authored_review_completion_filter_and_selected_root_ambiguity(
    private_source, tmp_path, cli
):
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
    reference = cli("docs", "commands", "interpretations", "author", "--stdout")
    assert reference.exit_code == 0, reference.output
    assert "private knowledge" in reference.stdout
    selected = Settings(
        database={
            "url": case.writer.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        },
        paths={"data_dir": tmp_path, "model_cache": tmp_path / "models"},
    )
    contract_path = tmp_path / "portable-contract"
    contract = cli(
        "interpretations",
        "export-contract",
        case.prepared.release_id,
        str(contract_path),
        "--json",
        settings=lambda: selected,
    )
    assert contract.exit_code == 0, contract.output
    manifest = json.loads((contract_path / "manifest.json").read_bytes())
    assert manifest["release_id"] == case.prepared.release_id
    assert "structural_preflight_only" in manifest["limitations"]
    input_path = tmp_path / "authored-review.json"
    input_path.write_text(json.dumps(configuration))
    completed = cli(
        "interpretations",
        "author",
        case.prepared.release_id,
        "terminology",
        str(input_path),
        "--json",
        settings=lambda: selected,
    )
    assert completed.exit_code == 0, completed.output
    authored = json.loads(completed.stdout)["body"]
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

    # A real proposed release removes the old unit and changes a source mapping.
    # Retained uses still belong to the before release, with original meaning intact.
    from dataclasses import replace
    from hashlib import sha256

    from rdflib import Graph, URIRef
    from rdflib.namespace import SKOS

    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.operation_reporting import compare_semantic_releases
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.terminology import ORIGINAL, PROFILE

    bundle, dependencies, profile = case.preparation_inputs
    changed_sources = []
    for source in bundle.sources:
        body = yaml.safe_load(source.content)
        if "RecognizedTimeUnit" in body.get("enums", {}):
            del body["enums"]["RecognizedTimeUnit"]["permissible_values"]["HOUR"]
            source = replace(source, content=yaml.safe_dump(body).encode())
        changed_sources.append(source)
    original = next(item for item in dependencies.artifacts if item.name == ORIGINAL)
    graph = Graph().parse(data=original.content, format="xml")
    graph.add(
        (
            URIRef("http://purl.obolibrary.org/obo/STATO_0000693"),
            SKOS.exactMatch,
            URIRef("https://example.org/proposed-variance-mapping"),
        )
    )
    changed_original = graph.serialize(format="xml").encode()
    updated_assets = []
    for source in dependencies.artifacts:
        if source.name == ORIGINAL:
            source = replace(source, content=changed_original)
        elif source.name == PROFILE:
            facts = json.loads(source.content)
            facts["original_sha256"] = sha256(changed_original).hexdigest()
            source = replace(source, content=json.dumps(facts).encode())
        updated_assets.append(source)
    proposed = prepare_release(
        SourceBundle(bundle.root, tuple(changed_sources)),
        replace(dependencies, artifacts=tuple(updated_assets)),
        profile,
    )
    assert proposed.release_id != case.prepared.release_id
    with read_snapshot(case.writer) as conn:
        arguments = dict(
            connection=conn,
            source_run_id=later["run_id"],
            review_run_id=measured["run_id"],
            review_cut_id=measured["cut_id"],
        )
        first_report = compare_semantic_releases(
            case.prepared, proposed, **arguments, use_limit=1
        ).model_dump(mode="json")
        first = source_python(first_report["vocabulary_uses"])
        assert first["side"] == "before" and first["vocabulary_release"] == case.prepared.release_id
        assert not first["complete"] and isinstance(first["next_after"], str)
        remaining = compare_semantic_releases(
            case.prepared, proposed, **arguments, use_limit=100, use_after=first["next_after"]
        ).model_dump(mode="json")
        second = source_python(remaining["vocabulary_uses"])
        assert second["complete"] and len(first["items"] + second["items"]) == 4
        assert any(row["selected_value"] == "HOUR" for row in first["items"] + second["items"])
        assert {change["aspect"] for change in first_report["changes"]} >= {
            "vocabulary_membership",
            "vocabulary_metadata",
        }
        assert "proposed-variance-mapping" in json.dumps(first_report["changes"])
        after = compare_semantic_releases(
            case.prepared, proposed, **arguments, use_side="after"
        ).model_dump(mode="json")
        assert source_python(after["vocabulary_uses"])["items"] == []
        assert not after["complete"] and any(
            "Other retained" in value for value in after["unknowns"]
        )
        with pytest.raises(ValueError, match="continuation"):
            compare_semantic_releases(
                case.prepared,
                proposed,
                **arguments,
                use_side="after",
                use_after=first["next_after"],
            )

    forged_source = dict(configuration["source"], native_content_digest="0" * 64)
    with pytest.raises(DBAPIError, match="original completed source custody"):
        author_interpretations(
            case.writer,
            case.prepared,
            kind="measurement",
            configuration=dict(source=forged_source, reviews=[measurement]),
            settings=Settings(paths={"data_dir": tmp_path, "model_cache": tmp_path / "models"}),
        )
