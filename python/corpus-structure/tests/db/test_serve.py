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
