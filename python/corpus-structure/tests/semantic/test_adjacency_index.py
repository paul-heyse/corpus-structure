"""Trusted physical index lowering preserves the query's collation and covering columns."""

import yaml
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from corpus_structure.model.compiled import compiled_model, running_model


def test_collated_covering_index_lowers_from_trusted_declaration():
    model = running_model()
    physical = yaml.safe_load(model.sources["physical.yaml"])
    physical["classes"]["edge"] = yaml.safe_load(
        """
    in_subset: [data]
    attributes:
      subject: {range: string}
      fact_id: {range: string}
      property_id: {range: string}
    annotations:
      ph:indexes:
        tag: ph:indexes
        value:
          - name: ix_edge_adjacency
            columns: [subject, fact_id]
            collations: {fact_id: C}
            include: [property_id]
"""
    )
    sources = {**model.sources, "physical.yaml": yaml.safe_dump(physical).encode()}
    metadata = compiled_model(sources).physical()
    (index,) = metadata.tables["data.edge"].indexes
    sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert sql == (
        "CREATE INDEX ix_edge_adjacency ON data.edge USING btree "
        '(subject, (fact_id COLLATE "C")) INCLUDE (property_id)'
    )
