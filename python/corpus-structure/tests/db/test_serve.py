"""The current named-query plugin registry.

Native serving journeys live in semantic/test_serving.
"""

from pathlib import Path

import pytest

from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import QueryRegistryError, build_registry


def test_the_registry_loads_a_pack_plugin_and_refuses_malformed_ones(tmp_path: Path) -> None:
    pack = tmp_path / "toy"
    pack.mkdir()
    (pack / "queries.py").write_text(
        "from pydantic import BaseModel\n"
        "class P(BaseModel):\n    x: int = 0\n"
        "class Q:\n    name, version, params, result = 'plug', '1', P, P\n"
        "    def rows(self, ctx, p):\n        return iter(())\n"
        "    def scope(self, ctx, p):\n        return None\n"
        "class NoRows:\n    name, version, params, result = 'broken', '1', P, P\n"
        "    def scope(self, ctx, p):\n        return None\n"
        "QUERIES = [Q()]\n",
        encoding="utf-8",
    )
    assert set(build_registry([GENERIC[0]], pack)) == {"entity", "plug"}
    assert set(build_registry([GENERIC[0]], tmp_path / "absent")) == {"entity"}
    with pytest.raises(QueryRegistryError, match="clashes"):
        build_registry([GENERIC[0], GENERIC[0]])
    (pack / "queries.py").write_text(
        (pack / "queries.py").read_text().replace("QUERIES = [Q()]", "QUERIES = [NoRows()]")
    )
    with pytest.raises(QueryRegistryError, match=r"broken.*|no rows\(\)"):
        build_registry([], pack)


def test_named_source_entity_multiplexer_is_retired_without_removing_entity_query():
    from types import SimpleNamespace
    from corpus_structure.semantic.query import EntityReference
    from corpus_structure.serve.queries import GENERIC, Entity, EntityParams
    from corpus_structure.serve.results import EntityAnswer
    from corpus_structure.serve.registry import build_registry

    registry = build_registry(GENERIC)
    assert "find" not in registry
    seen = []
    answer = EntityAnswer(entity=EntityReference(entity_id="entity:alice", memberships=()))
    def rows(key, label, after):
        seen.append((key, label, after))
        yield answer
    query = registry["entity"]
    assert isinstance(query, Entity)
    selected = list(query.rows(SimpleNamespace(reader=SimpleNamespace(entity_rows=rows)), EntityParams(label="Alice"), after="entity:before"))
    assert selected[0].row is answer and selected[0].position == "entity:alice"
    assert seen == [(None, "Alice", "entity:before")]
