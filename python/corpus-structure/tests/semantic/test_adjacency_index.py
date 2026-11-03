"""Trusted physical index lowering preserves the query's collation and covering columns."""

from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from corpus_structure.schema.relational import compile_metadata


def test_collated_covering_index_lowers_from_trusted_declaration():
    schema = """
id: https://corpus-structure.org/model/semantic/physical
name: physical
prefixes:
  linkml: https://w3id.org/linkml/
imports: [linkml:types]
subsets: {data: {}}
classes:
  edge:
    in_subset: [data]
    attributes:
      subject: {range: string}
      fact_id: {range: string}
      property_id: {range: string}
    annotations:
      ph:indexes: >-
        [{"name":"ix_edge_adjacency","columns":["subject","fact_id"],
          "collations":{"fact_id":"C"},"include":["property_id"]}]
"""
    metadata = compile_metadata(SchemaView(schema), target="semantic")
    (index,) = metadata.tables["data.edge"].indexes
    sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert sql == (
        "CREATE INDEX ix_edge_adjacency ON data.edge USING btree "
        '(subject, (fact_id COLLATE "C")) INCLUDE (property_id)'
    )
