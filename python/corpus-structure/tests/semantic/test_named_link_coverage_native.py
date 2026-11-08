"""Controlled parity for the released named-link coverage asset."""

import json
from pathlib import Path

from sqlalchemy import text


def test_native_named_coverage_rule_availability_and_identifier_extent(semantic_db_engine):
    package = Path(__file__).parents[2] / "src/corpus_structure"
    sql = package / "semantic/sql/source_contributions.sql"
    recipe = json.loads((package / "methods/named_link_coverage.json").read_text())
    source = 'Use definition ID "PX:18.1" as defined in Section 6.2.'
    cue = source.index("as defined")
    span = [source.index("PX:"), source.index('"', source.index("PX:"))]
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql(sql.read_text(), execution_options={"no_parameters": True})
        assert (
            conn.scalar(
                text("SELECT ops.named_link_definition_subject(:source,0,:cue,:pattern)"),
                {"source": source, "cue": cue, "pattern": recipe["definition_identifier_pattern"]},
            )
            == span
        )
        assert (
            conn.scalar(
                text("SELECT ops.named_link_definition_subject(:source,0,:cue,:pattern)"),
                {"source": source, "cue": cue, "pattern": r'"([A-Za-z][A-Za-z0-9 -]{0,79})" +$'},
            )
            is None
        )
        rule = {"mechanism": "dependency", "nodes": [{"attrs": {"LEMMA": "define"}}]}
        for columns, expected in ((["DEP", "LEMMA"], True), (["DEP"], False), (["LEMMA"], False)):
            assert (
                conn.scalar(
                    text(
                        "SELECT ops.named_link_rule_available("
                        "CAST(:rule AS jsonb),CAST(:columns AS jsonb))"
                    ),
                    {"rule": json.dumps(rule), "columns": json.dumps(columns)},
                )
                is expected
            )
