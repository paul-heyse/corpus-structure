"""Controlled parity for the released named-link coverage asset."""

import json
from pathlib import Path

from sqlalchemy import func, literal, select, text
from sqlalchemy.dialects.postgresql import JSONB


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


def test_native_named_group_refuses_cue_outside_projection_piece(semantic_db_engine):
    package = Path(__file__).parents[2] / "src/corpus_structure"
    recipe = (package / "methods/named_link_rules.json").read_text()
    spelling = "See Section 6.2."
    tokens = [
        dict(start=0, end=3, head=0, sentence=0),
        dict(start=4, end=11, head=0, sentence=0),
    ]
    query = text("""
        SELECT count(*) FROM ops.named_link_expected_groups(
         :spelling,CAST(:tokens AS jsonb),
         jsonb_build_object('start',0,'end',CAST(:piece_end AS integer)),
         jsonb_build_object('start',0,'end',CAST(:passage_end AS integer)),
         CAST(:recipe AS jsonb))
    """)
    with semantic_db_engine.connect() as conn:

        def groups(piece_end):
            return conn.scalar(
                query,
                dict(
                    spelling=spelling,
                    tokens=json.dumps(tokens),
                    piece_end=piece_end,
                    passage_end=len(spelling),
                    recipe=recipe,
                ),
            )

        assert groups(len(spelling)) == 1
        assert groups(2) == 0


def test_native_named_group_requires_exact_selected_piece_for_v4(semantic_db_engine):
    package = Path(__file__).parents[2] / "src/corpus_structure"
    recipe = json.loads((package / "methods/named_link_rules.json").read_text())
    spelling = "Prior. See Section 6.2."
    cue, section, designator = (spelling.index(word) for word in ("See", "Section", "6.2"))
    piece = {"start": cue, "end": len(spelling)}
    tokens = [
        dict(start=0, end=6, head=0, sentence=0, piece_indices=[0]),
        dict(start=cue, end=cue + 3, head=1, sentence=1, piece_indices=[1]),
        dict(start=section, end=section + 7, head=1, sentence=1, piece_indices=[1]),
        dict(start=designator, end=designator + 3, head=2, sentence=1, piece_indices=[1]),
    ]
    expected = [("section", "see_or_consult", {"verb": 1, "section": 2})]

    def read(conn, proposed, *, exact):
        selected_recipe = dict(recipe, _native_piece_index=1) if exact else recipe
        groups = func.ops.named_link_expected_groups(
            spelling,
            literal(proposed, JSONB),
            literal(piece, JSONB),
            literal(piece, JSONB),
            literal(selected_recipe, JSONB),
        ).table_valued("rule_name", "variant", "nodes")
        return conn.execute(select(groups.c.rule_name, groups.c.variant, groups.c.nodes)).all()

    with semantic_db_engine.connect() as conn:
        # Exercise the forward SQL on the disposable native fixture before release deployment.
        sql = package / "semantic/sql/source_contributions.sql"
        conn.exec_driver_sql(sql.read_text(), execution_options={"no_parameters": True})
        assert read(conn, tokens, exact=True) == expected
        misplaced_cue = [tokens[0], dict(tokens[1], piece_indices=[0]), *tokens[2:]]
        crossing_role = [*tokens[:3], dict(tokens[3], piece_indices=[0, 1])]
        assert not read(conn, misplaced_cue, exact=True)
        assert not read(conn, crossing_role, exact=True)
        assert read(conn, misplaced_cue, exact=False) == expected
