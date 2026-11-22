"""Bounded controls for occurrence keys, selected lookup and projected custody."""

import json
from hashlib import sha256

import duckdb
import pyarrow as pa

from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_product_reference import SemanticReference
from corpus_structure.semantic.pdf_payloads import prepare_payload_family
from corpus_structure.semantic.reference_resolution import (
    AcquiredReferencePartition,
    ProducingReferenceBindings,
    ProducingReferenceInput,
    ReferenceResolver,
    ReferenceTarget,
)


def finite_relation():
    walk = """
    WITH RECURSIVE edges(src, dst, role) AS (
        VALUES ('start','left','a'), ('start','right','b'),
               ('left','join','in'), ('right','join','in')
    ), reach(node, arm) USING KEY ({key}) AS (
        VALUES ('start','')
        UNION ALL
        SELECT dst, CASE WHEN arm = '' THEN role ELSE arm END
        FROM reach JOIN edges ON src = node
    )
    SELECT arm FROM reach WHERE node = 'join' ORDER BY arm
    """
    with duckdb.connect() as connection:
        coarse = connection.execute(walk.format(key="node")).fetchall()
        exact = connection.execute(walk.format(key="node, arm")).fetchall()
        difference = "SELECT * FROM (VALUES ('equal'), ('equal')) EXCEPT {} SELECT 'equal'"
        distinct = connection.execute(difference.format("")).fetchall()
        bag = connection.execute(difference.format("ALL")).fetchall()
    assert len(coarse) == 1 and exact == [("a",), ("b",)]
    assert distinct == [] and bag == [("equal",)]
    return {"arms_with_node_only": len(coarse), "arms_with_role": exact, "bag_difference": bag}


class FixtureAccess:
    def __init__(self):
        self.authorizations = 0
        self.partition_opens = 0
        self.allowed = True

    def authorize(self, binding):
        assert binding.product_id == "selected-source"
        self.authorizations += 1
        if not self.allowed:
            raise PermissionError("selected parent is withheld")

    def product(self, product_id):
        raise AssertionError("addressed read asked for a whole product")

    def member(self, product_id, member_id):
        raise AssertionError("addressed read asked for a standalone member")

    def partition(self, product_id, collection, partition_key):
        assert (product_id, collection, partition_key) == ("selected-source", "rows", "p")
        self.partition_opens += 1
        return AcquiredReferencePartition(
            "fixture-body", semantic_value([{"ordinal": 0}, {"ordinal": 1}]), ("ordinal",)
        )


def selected_lookup():
    binding = ProducingReferenceInput("sentences", "selected-source", "kind")
    producing = ProducingReferenceBindings("derivation", (binding,))
    target = ReferenceTarget("sentences", "partition-item", "kind", "rows")
    access = FixtureAccess()
    resolver = ReferenceResolver(producing, access)
    for ordinal in (0, 1, 0):
        reference = SemanticReference.item("sentences", "rows", "p", (ordinal,))
        assert resolver.resolve(reference, target) == {"ordinal": ordinal}
    missing = SemanticReference.item("sentences", "rows", "p", (2,))
    try:
        resolver.resolve(missing, target)
    except ValueError as error:
        assert "does not resolve" in str(error)
    else:
        raise AssertionError("admitted missing item resolved")
    access.allowed = False
    try:
        resolver.resolve(reference, target)
    except PermissionError:
        pass
    else:
        raise AssertionError("cached body bypassed a withheld parent")
    assert (access.partition_opens, access.authorizations) == (1, 5)
    return {"partition_opens": access.partition_opens, "authorization_calls": access.authorizations}


def projected_payload():
    family = prepare_payload_family()
    page = {"page_no": 1, "has_chars": False, "has_words": False, "has_vectors": False}
    changed = {**page, "has_vectors": True}
    original = family.encode(page, compression="zstd")
    replacement = family.encode(changed, compression="zstd")
    assert sha256(original).digest() != sha256(replacement).digest()
    before = family.read_batch(original, columns=("page_no",))
    after = family.read_batch(replacement, columns=("page_no",))
    assert before.equals(after) and before.to_pylist() == [{"page_no": 1}]
    assert family.logical_digest(page) != family.logical_digest(changed)
    return {"same_projected_page": True, "same_bytes": False, "same_logical_identity": False}


def main():
    print(
        json.dumps(
            {
                "pyarrow": pa.__version__,
                "duckdb": duckdb.__version__,
                "finite_relation": finite_relation(),
                "selected_lookup": selected_lookup(),
                "projected_payload": projected_payload(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
