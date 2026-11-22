"""Admitted partition metadata and body-free projection key parity."""

from dataclasses import asdict
from decimal import Decimal

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_model import InputReadProjection, ProjectedCollection
from corpus_structure.semantic.data_operation_partitions import partition_group_digests
from corpus_structure.semantic.data_operation_projection_values import input_projection_digest
from corpus_structure.semantic.data_operation_read_native import read_native_programs
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from semantic.test_data_product_admission_programs import (
    partition_fixture,
    realize,
)
from semantic.test_data_product_admission_programs import product_connection as product_connection


def test_selected_whole_projection_digest_never_reads_partition_bodies(product_connection):
    connection = product_connection
    context, product, bodies, layout = partition_fixture(connection)
    header = decode_semantic_value(product["body"]) | {
        "source": {
            "document": "a",
            "ignored": "not an observed field",
            "precision": Decimal("1.2"),
        },
        "optional": None,
        "selectors": [{"relation": "original", "section": 2}],
    }
    product["body"] = semantic_value(header)
    admitted = realize(connection, context, product)

    # Supply the existing binding owner's selection response in this isolated
    # product fixture, which does not install all demand, trust and request state.
    connection.exec_driver_sql("CREATE TABLE ops.data_demand(id text, release_id text)")
    connection.exec_driver_sql(
        "CREATE TABLE sem.data_operation_definition("
        "release_id text, operation_id text, input_roles jsonb)"
    )
    connection.exec_driver_sql("INSERT INTO ops.data_demand VALUES ('demand', 'release')")
    connection.exec_driver_sql(
        """CREATE FUNCTION ops.ddo_binding_rows(
          text, text, jsonb, text, text, jsonb, jsonb, bool, jsonb
        ) RETURNS TABLE(product text, member text, meaning_body jsonb) LANGUAGE sql AS $$
          SELECT p.id, NULL::text, p.canonical_body
          FROM kb.data_product AS p
          JOIN jsonb_array_elements($9) AS pin ON p.id = pin->>'product_id'
          WHERE $1 = 'demand' AND $2 = 'operation' AND $4 = 'read' AND NOT $8
            AND pin->>'member_id' IS NULL
        $$"""
    )
    procedures = ("ddo_input_projection_header", "ddo_binding_input_projection_digest")
    programs = {
        entry.routine.name: entry
        for entry in read_native_programs(get_metadata())
        if entry.routine.name in procedures
    }
    for name in procedures:
        execute_native_sql(connection, programs[name].routine.render())

    # Product and group commitments were admitted before removing the unneeded
    # column. The fixture's transaction rolls back the DDL and all test writes.
    connection.exec_driver_sql("ALTER TABLE kb.data_product_partition DROP COLUMN body")
    read = text(
        "SELECT ops.ddo_binding_input_projection_digest("
        "'demand','operation','{}'::jsonb,:read,'subject',NULL,NULL,:pins,:role)"
    ).bindparams(bindparam("pins", type_=JSONB()))
    update = text(
        "INSERT INTO sem.data_operation_definition VALUES ('release', 'operation', :roles)"
    ).bindparams(bindparam("roles", type_=JSONB()))
    metadata = [
        {
            **{key: packet[key] for key in ("collection", "partition_key", "ordinal", "placement")},
            "group_digests": partition_group_digests(body, layout["field_groups"]),
        }
        for packet, body in zip(product["partitions"], bodies, strict=True)
    ]
    pins = [{"product_id": admitted, "member_id": None}]
    selectors = (
        ProjectedCollection("tokens", ("geometry",), True, True, True),
        ProjectedCollection("tokens", ("labels",), True, False, False),
        ProjectedCollection("tokens", (), False, False, True),
    )
    for index, selection in enumerate(selectors):
        projection = InputReadProjection(
            1,
            "whole",
            ("optional", "selectors", "source.document", "source.missing", "source.precision"),
            (selection,),
            None,
            f"input-read-projection:test-{index}",
        )
        connection.exec_driver_sql("DELETE FROM sem.data_operation_definition")
        connection.execute(
            update,
            {
                "roles": [
                    {
                        "name": "inventory",
                        "collection": "scalar",
                        "minimum": 1,
                        "maximum": 1,
                        "read_projection": asdict(projection),
                    }
                ],
            },
        )
        assert connection.scalar(read, dict(read="read", pins=pins, role="inventory")) == (
            input_projection_digest(projection, header, metadata)
        )

    assert connection.scalar(read, dict(read="other", pins=pins, role="inventory")) is None
    with pytest.raises(DBAPIError, match="declared scalar whole role"), connection.begin_nested():
        connection.scalar(read, dict(read="read", pins=pins, role="other"))
    with pytest.raises(DBAPIError, match="exact whole-product pin"), connection.begin_nested():
        connection.scalar(
            read,
            dict(read="read", pins=[{"product_id": admitted, "member_id": "m"}], role="inventory"),
        )
