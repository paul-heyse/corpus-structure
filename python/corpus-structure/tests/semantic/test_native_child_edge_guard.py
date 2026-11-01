"""Independent small graph faults and non-executing plan proof for shared child checks."""

import json
import re
from copy import deepcopy
from hashlib import sha256

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes

from . import test_pdf_integrated as fixtures

native_source = fixtures.native_source
pdf13_db = fixtures.pdf13_db


def test_child_target_backpointer_multi_parent_and_leafs_in_both_publishers(pdf13_db):
    db = pdf13_db
    for route in ("native", "integrated"):
        base = (
            db.native.values() if route == "native" else fixtures.integrated(db.source, db.inputs)
        )
        prepared = db.native if route == "native" else fixtures.prepare(base, db.source)
        for fault in ("missing_target", "wrong_backpointer", "multi_parent", "leaf"):
            value = deepcopy(base)
            value["product_key"] = f"edge-{route}-{fault}"
            content = value if route == "native" else value["content"]
            document = content["document"]
            first, second = document["texts"][:2]
            assert first.get("children", []) == [] and second.get("children", []) == []
            if fault == "missing_target":
                document["body"]["children"].append({"$ref": "#/texts/999"})
            elif fault == "wrong_backpointer":
                first["parent"] = {"$ref": second["self_ref"]}
                for item in content["items"]:
                    if item["pointer"] == first["self_ref"]:
                        item["parent_pointer"] = second["self_ref"]
            elif fault == "multi_parent":
                second.setdefault("children", []).append({"$ref": first["self_ref"]})
            if route == "integrated":
                statement = text(
                    "SELECT ops.publish_integrated_pdf("
                    ":task,:attempt,:holder,:contract,:payload,:artifacts)"
                )
                parameters = dict(
                    task=db.job.task,
                    attempt=db.job.attempt,
                    holder=fixtures.HOLDER,
                    contract=prepared.contract_digest,
                    payload=canonical_bytes(value),
                    artifacts=list(prepared.artifacts),
                )
            else:
                statement = text(
                    "SELECT ops.publish_native_document("
                    ":task,:attempt,:holder,:contract,:payload,NULL,:schema,:recipe)"
                )
                parameters = dict(
                    task=db.job.task,
                    attempt=db.job.attempt,
                    holder=fixtures.HOLDER,
                    contract=prepared.contract_digest,
                    payload=canonical_bytes(value),
                    schema=db.source.schema,
                    recipe=db.source.recipe,
                )
            with db.writer.begin() as conn:
                if fault == "leaf":
                    assert (
                        conn.scalar(statement, parameters)
                        == sha256(canonical_bytes(value)).hexdigest()
                    )
                else:
                    with (
                        pytest.raises(
                            DBAPIError, match="native access universe/order/membership differs"
                        ),
                        conn.begin_nested(),
                    ):
                        conn.scalar(statement, parameters)
    with db.writer.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.pdf_product WHERE product_key LIKE 'edge-%'")
            )
            == 2
        )


def test_child_integrity_generic_plan_is_global_not_correlated(pdf13_db):
    db = pdf13_db
    with db.writer.connect() as conn:
        body = conn.scalar(
            text("""
          SELECT prosrc FROM pg_proc WHERE oid=
            'ops.publish_integrated_pdf(bigint,bigint,text,text,bytea,bytea[])'::regprocedure
        """)
        )
        start = body.index(" -- Compare the complete access universe")
        end = body.index(
            " THEN RAISE EXCEPTION 'native access universe/order/membership differs'", start
        )
        chunk = body[start:end]
        query = chunk[chunk.index("IF EXISTS(") + len("IF EXISTS(") :].rstrip()
        assert query.endswith(")")
        query = query[:-1].strip()
        query = re.sub(r"\bselected_document\b", "($1::jsonb)", query)
        query = re.sub(r"\bselected_content\b", "($2::jsonb)", query)
        result = conn.exec_driver_sql(
            "EXPLAIN (GENERIC_PLAN TRUE,COSTS FALSE,FORMAT JSON) SELECT EXISTS(" + query + ")"
        ).scalar_one()
    plan = json.loads(result) if isinstance(result, str) else result

    def nodes(value):
        if isinstance(value, dict):
            if "Node Type" in value:
                yield value
            for child in value.values():
                yield from nodes(child)
        elif isinstance(value, list):
            for child in value:
                yield from nodes(child)

    all_nodes = list(nodes(plan))
    # The only correlated subplan left is parent existence. Child expansion must
    # live in an uncorrelated InitPlan; this is not an actual-loop measurement.
    assert all(
        not any(child["Node Type"] == "Function Scan" for child in nodes(node))
        for node in all_nodes
        if node.get("Parent Relationship") == "SubPlan"
    )
    assert any(
        any(child.get("Alias", "").startswith("edge_target") for child in nodes(node))
        for node in all_nodes
        if node.get("Parent Relationship") == "InitPlan"
    )
