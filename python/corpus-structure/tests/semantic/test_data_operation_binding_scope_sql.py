"""Execute selected binding statements under ordinary PL/pgSQL name resolution."""

import json
from importlib.resources import files

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


@pytest.mark.db
@pytest.mark.parametrize(
    "origin, forged_original",
    [
        ("original-source", False),
        ("original-source", True),
        ("computation", False),
        ("mixed", False),
        ("mixed", True),
    ],
)
def test_binding_population_variable_does_not_shadow_selected_support_aliases(
    semantic_bare_engine,
    origin,
    forged_original,
):
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    function = source[source.index("CREATE OR REPLACE FUNCTION ops.ddo_validate_binding(") :]
    function = function[: function.index("END $$;")]

    def excerpt(start, end):
        offset = function.index(start)
        return function[offset : function.index(end, offset) + len(end)]

    population = excerpt(" SELECT value INTO population_reference FROM", ";")
    selected_input = excerpt(" SELECT value INTO STRICT item FROM", "LIMIT 1;")
    occurrence_counts = excerpt(
        " IF (SELECT count(*) FROM jsonb_array_elements(rv->'value') other",
        "THEN RAISE EXCEPTION "
        "'semantic member occurrence counts differ from native manifest'; END IF;",
    )
    original = excerpt(" IF roledef->'identity_requirements' ? 'original-source' AND", "\n END IF;")
    episode = excerpt(" IF roledef->'identity_requirements' ? 'episode' AND", "\n END IF;")
    # Actual production SQL statements run with the same scalar variable names.
    # Native composite rows are unnecessary for these JSON manifest statements.
    sql = (
        """CREATE FUNCTION pg_temp.binding_manifest_scope(b jsonb,roledef jsonb,mv jsonb)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE population_reference jsonb; item jsonb; expected jsonb; original_identities jsonb; rv jsonb;
BEGIN
 rv:=jsonb_build_object('value',jsonb_build_array(mv));
"""
        + population
        + selected_input
        + occurrence_counts
        + original
        + "\n original_identities:=expected;\n"
        + episode
        + """
 RETURN jsonb_build_object('population',population_reference,'input',item,
                          'originals',original_identities,
                          'episodes',CASE WHEN roledef->'identity_requirements' ? 'episode'
                            THEN expected ELSE NULL END,
                          'support',b->'support');
END $$;"""
    )
    bundle = {
        "populations": [{"role": "source", "population_id": "population:one", "name": "source"}],
        "inputs": [
            {
                "role": "source",
                "product_id": "product:one",
                "member_id": None,
                "position": 0,
                "multiplicity": 1,
            }
        ],
        "support": [
            {
                "role": "source",
                "position": 0,
                "kind": "computation",
                "derivation_id": "episode:one",
            },
            {
                "role": "source",
                "position": 0,
                "kind": "original-source",
                "source_reference": "original:one",
            },
        ],
    }
    bundle["support"] = [
        item for item in bundle["support"] if origin == "mixed" or item["kind"] == origin
    ]
    role = {
        "name": "source",
        "collection": "sequence",
        "identity_requirements": (
            ["episode", "original-source"]
            if origin == "mixed"
            else ["episode" if origin == "computation" else "original-source"]
        ),
    }
    member = {"product": "product:one", "member": None, "position": 0, "multiplicity": 1}
    if origin in {"computation", "mixed"}:
        member["support_episodes"] = ["episode:one"]
    if origin in {"original-source", "mixed"}:
        member["original_sources"] = ["forged" if forged_original else "original:one"]
    with semantic_bare_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET LOCAL plpgsql.variable_conflict = error")
            connection.exec_driver_sql(sql)
            query = text(
                "SELECT pg_temp.binding_manifest_scope("
                "CAST(:b AS jsonb),CAST(:role AS jsonb),CAST(:member AS jsonb))"
            )
            args = {"b": json.dumps(bundle), "role": json.dumps(role), "member": json.dumps(member)}
            if forged_original:
                with pytest.raises(DBAPIError, match="original source identity differs"):
                    connection.scalar(query, args)
            else:
                actual = connection.scalar(query, args)
                assert actual == {
                    "population": bundle["populations"][0],
                    "input": bundle["inputs"][0],
                    "originals": ["original:one"]
                    if origin in {"original-source", "mixed"}
                    else None,
                    "episodes": ["episode:one"] if origin in {"computation", "mixed"} else None,
                    "support": bundle["support"],
                }
        finally:
            transaction.rollback()
