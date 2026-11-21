"""Current candidate extraction preserves exact identities and bounded selectors."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_visual_read import visual_read_schema, visual_read_sql
from corpus_structure.semantic.data_operation_wire import validate_native_wire
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.visual_evidence import (
    VisualCaptionCandidate,
    VisualCellGroup,
    VisualEvidenceArtifact,
    VisualEvidencePin,
    VisualPicture,
    VisualSourceRegion,
    VisualTable,
    VisualTableCell,
    VisualText,
)


def artifact():
    return VisualEvidenceArtifact(
        page_no=1,
        rows=(
            VisualPicture(
                occurrence_id="p",
                source_region=VisualSourceRegion(left=1, top=1, right=10, bottom=10),
            ),
            VisualCaptionCandidate(
                occurrence_id="caption",
                text="Straße\u00a0Shared\u2003Distribution",
                associated_picture_occurrence_ids=("p",),
                source_region=VisualSourceRegion(left=1, top=1, right=10, bottom=10),
            ),
            VisualTable(
                occurrence_id="table",
                num_rows=1,
                num_cols=1,
                cells=(
                    VisualTableCell(
                        text="x",
                        start_row_offset_idx=0,
                        end_row_offset_idx=1,
                        start_col_offset_idx=0,
                        end_col_offset_idx=1,
                        content_occurrence_id="group",
                    ),
                ),
            ),
            VisualCellGroup(
                occurrence_id="group", parent_occurrence_id="table", native_label="group"
            ),
            VisualText(
                occurrence_id="term", parent_occurrence_id="group", kind="formula", text="x^2"
            ),
        ),
    )


@pytest.fixture
def candidate_read(native_rollback):
    connection = native_rollback.connection
    source = prepare_sql(visual_read_sql(), source="current-visual-read")
    connection.exec_driver_sql(source.excerpt(0), execution_options={"no_parameters": True})

    def read(**selectors):
        query = dict(after=0, limit=100, regions=[])
        query.update(selectors)
        return connection.execute(
            text(
                "SELECT ops.ddo_visual_candidate_rows(CAST(:artifact AS jsonb),CAST(:query AS jsonb))"
            ),
            dict(artifact=artifact().model_dump_json(exclude_none=True), query=json.dumps(query)),
        ).scalar_one()

    return read


def test_native_candidate_identity_search_cells_and_paging(candidate_read):
    first = candidate_read(limit=2)
    assert [row["occurrence_id"] for row in first["items"]] == ["p", "caption"]
    assert first["next_after"] == 2
    second = candidate_read(after=2)
    assert [row["occurrence_id"] for row in second["items"]] == ["table", "group", "term"]
    assert second["next_after"] is None
    assert [
        row["occurrence_id"]
        for row in candidate_read(query="shared distribution", kind="picture")["items"]
    ] == ["p"]
    assert [
        row["occurrence_id"] for row in candidate_read(query="STRASSE", kind="picture")["items"]
    ] == ["p"]
    cell = candidate_read(occurrence_id="table", cell_index=0)
    assert [row["occurrence_id"] for row in cell["items"]] == ["group", "term"]
    region = candidate_read(regions=[dict(left=0, top=0, right=2, bottom=2)])
    assert [row["occurrence_id"] for row in region["items"]] == ["p", "caption"]


@pytest.mark.parametrize(
    "selector",
    [
        dict(after=999),
        dict(occurrence_id="missing"),
        dict(occurrence_id="p", cell_index=0),
        dict(occurrence_id="table", cell_index=5),
    ],
)
def test_native_candidate_refuses_wrong_continuation_or_cell(candidate_read, selector):
    with pytest.raises(DBAPIError):
        candidate_read(**selector)


def test_current_visual_wire_is_closed_and_preserves_semantic_pins():
    source = dict(
        project_id="project",
        demand_id="demand",
        read_id="read",
        use_id="source-use",
        product_id="source",
        derivation_id="source-episode",
    )
    evidence = VisualEvidencePin(
        use_id="use", product_id="product", derivation_id="episode"
    ).model_dump()
    request = dict(
        source=source,
        evidence=evidence,
        mode="header",
        after=0,
        limit=10,
        max_bytes=10000,
        regions=[],
    )
    assert validate_native_wire("read_selected_visual_evidence", "input", request) == request
    with pytest.raises(ValueError):
        validate_native_wire(
            "read_selected_visual_evidence",
            "input",
            dict(request, evidence=dict(evidence, run_id=7)),
        )
    with pytest.raises(ValueError):
        validate_native_wire(
            "read_selected_visual_evidence", "input", dict(request, mode="artifact")
        )
    from jsonschema import Draft7Validator

    Draft7Validator(json.loads(visual_read_schema())).validate(
        dict(kind="rows", items=artifact().model_dump(mode="json")["rows"], next_after=None)
    )


@pytest.mark.parametrize('content, accepted', [('ab00', True), ('', True), ('ab\n', False), ('abc', False)])
def test_visual_artifact_hex_schema_matches_owning_model(content, accepted):
    from jsonschema import Draft7Validator
    from pydantic import ValidationError

    from corpus_structure.semantic.data_operation_visual_read import VisualArtifactReply, _schema

    schema = json.loads(_schema(VisualArtifactReply))
    assert schema['$schema'] == 'http://json-schema.org/draft-07/schema#'
    value = dict(kind='artifact', digest='original', media_type='image/png', content_hex=content,
                 offset=0, total_bytes=2, next_offset=None)
    assert Draft7Validator(schema).is_valid(value) is accepted
    if accepted:
        assert VisualArtifactReply.model_validate(value).content_hex == content
    else:
        with pytest.raises(ValidationError):
            VisualArtifactReply.model_validate(value)
