"""Derived publication search, using the existing pinned Python projection producer.

The renderer asserts a derived projection. PostgreSQL independently authenticates
its publication, original atoms, membership, recipe and exact immutable replay;
it does not reproduce Docling rendering or grant the cache source standing.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from .identity import canonical_bytes
from .types import SourceArtifact

if TYPE_CHECKING:
    from corpus_structure.serve.selected_pdf import SelectedPdfSource

PUBLICATION_FILL_BYTES = 128 * 1024 * 1024
PUBLICATION_FILL_ROWS = 1_000_000
CONTRACT = "native/pdf-source-search-contract.json"
_SQL = Path(__file__).with_name("sql") / "pdf_source_search.sql"
_RENDERER_FILES = (
    "ingest/pdf_section_views.py", "ingest/pdf_hierarchy.py", "ingest/pdf_health.py",
    "semantic/source_products.py", "semantic/native_source_view.py", "semantic/pdf_source_search.py",
    "model/semantic/section-text-recipe.json",
)


def search_projection_sources() -> tuple[SourceArtifact, ...]:
    root = Path(__file__).resolve().parents[1]
    captured = tuple(SourceArtifact("native/search-renderer/" + name, root.joinpath(name).read_bytes())
                     for name in _RENDERER_FILES)
    renderer = {
        "sources": [(source.name, source.digest) for source in captured],
        "libraries": {name: version(name) for name in ("docling-core", "docling")},
    }
    policy = next(source.content for source in captured if source.name.endswith("section-text-recipe.json"))
    return (*captured, SourceArtifact(CONTRACT, canonical_bytes({
        "version": "pdf-source-search-v1", "renderer": sha256(canonical_bytes(renderer)).hexdigest(),
        "default_policy_digest": sha256(policy).hexdigest(), "max_fill_bytes": PUBLICATION_FILL_BYTES,
    })), SourceArtifact("native/pdf-source-search.sql", _SQL.read_bytes()))


@cache
def _running_contract() -> dict:
    return json.loads(next(source.content for source in search_projection_sources() if source.name == CONTRACT))


def search_projection_sql(sources) -> str:
    captured = {source.name: source.content for source in sources}
    contract = json.loads(captured[CONTRACT])
    sql = captured["native/pdf-source-search.sql"].decode()
    for token, value in (
        ("__SEARCH_RENDERER__", contract["renderer"]),
        ("__SEARCH_DEFAULT_POLICY__", contract["default_policy_digest"]),
        ("__SEARCH_FILL_BYTES__", str(contract["max_fill_bytes"])),
    ):
        sql = sql.replace(token, value)
    return sql


def projection_recipe(connection, source: SelectedPdfSource) -> tuple[dict, bytes | None]:
    from corpus_structure.ingest.pdf_hierarchy import retained_section_text_policy

    policy = retained_section_text_policy(connection, source.prepared)
    contract = _running_contract()
    recipe = {
        "version": "pdf-source-search-v1", "renderer": contract["renderer"],
        "policy_digest": sha256(policy).hexdigest() if policy is not None else contract["default_policy_digest"],
        "organization_owner": source.physical.values(), "analysis_eligible": True,
    }
    return recipe, policy


def population_identity(source: SelectedPdfSource, recipe: dict) -> str:
    publication = source.receipt.publication
    return "pdf-search:" + sha256(canonical_bytes([
        source.reference.project_id, publication.build_id, publication.task_id,
        publication.product_key, publication.logical_digest,
        sha256(canonical_bytes(recipe)).hexdigest(), "english",
    ])).hexdigest()


@dataclass(frozen=True)
class SearchPopulation:
    identity: str
    digest: str
    row_count: int
    recipe: dict


@contextmanager
def search_source_snapshot(engine):
    """Pinned sources retain their trust locks while a concurrent cache fill becomes visible.

    Only the derived cache needs a later statement snapshot. Each native read
    still checks the exact retained cut, producing episode and scoped live trust.
    """
    with engine.connect().execution_options(
        isolation_level="READ COMMITTED", postgresql_readonly=False,
    ) as connection, connection.begin():
        yield connection


def ensure_search_projection(connection, source: SelectedPdfSource, *, recipe: dict, policy: bytes | None,
                             fill_max_bytes: int = PUBLICATION_FILL_BYTES) -> SearchPopulation:
    """The definer lock serializes a first fill; cache hits transfer no section text."""
    from ._data_operation_wire import WireEnsurePdfSearchProjectionRequest
    from .data_operation_storage import DataOperationStorage
    from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
    from .source_products import FrozenNativeSource
    from corpus_structure.ingest.pdf_section_views import published_section_projections

    if type(fill_max_bytes) is not int or not 1 <= fill_max_bytes <= PUBLICATION_FILL_BYTES:
        raise ValueError("invalid publication search fill bound")
    storage = DataOperationStorage(connection)
    payload = {"source": source.reference.model_dump(), "recipe": recipe, "configuration": "english",
               "fill_max_bytes": fill_max_bytes}
    result = storage.ensure_pdf_search_projection(cast(WireEnsurePdfSearchProjectionRequest, payload))
    if result["state"] == "missing":
        budget = PublishedReadBudget(PUBLICATION_FILL_ROWS, fill_max_bytes)
        reader = PublishedPdfReader(connection, source.physical, projection_context=source.prepared,
                                    read_budget=budget)
        pointers = tuple(row["pointer"] for row in reader.sections())
        rows = []
        scopes: tuple[tuple[Literal["direct", "descendants"], tuple[str, ...]], ...] = (
            ("direct", ("#/body", *pointers)), ("descendants", pointers),
        )
        for membership, selected in scopes:
            if not selected:
                continue
            for row in published_section_projections(reader, selections=selected, membership=membership,
                    scope=None, projection_policy=policy, exact_sections=True):
                projected = FrozenNativeSource.from_projection(source.prepared,
                    document=source.original_source, section_pointer=row.section_pointer,
                    membership=row.membership, text=row.text, pieces=row.pieces, items=row.items,
                    ancestors=row.ancestors, recognition=row.health.get("formula_outcomes", ())).value
                rows.append({"section_pointer": row.section_pointer, "membership": row.membership,
                    "projection_digest": projected["source"]["projection"], "projection": {
                        "text": projected["text"], "pieces": projected["pieces"],
                        "items": [item["self_ref"] for item in projected["items"]],
                        "ancestors": [item["self_ref"] for item in projected["ancestors"]],
                        "health": {"formula_outcomes": projected["recognition"]},
                    }})
        rows.sort(key=lambda row: (row["section_pointer"], row["membership"]))
        budget.value(rows)
        result = storage.ensure_pdf_search_projection(cast(WireEnsurePdfSearchProjectionRequest,
                                                            {**payload, "rows": rows}))
    expected = population_identity(source, recipe)
    if result["state"] != "ready" or result["population_id"] != expected or result["set_digest"] is None:
        raise ValueError("native search population differs from the selected publication/recipe")
    return SearchPopulation(expected, result["set_digest"], result["row_count"], recipe)
