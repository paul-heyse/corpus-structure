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

    from .native_program_registry import ProgramDeclaration

PUBLICATION_FILL_BYTES = 128 * 1024 * 1024
PUBLICATION_FILL_ROWS = 1_000_000
CONTRACT = "native/pdf-source-search-contract.json"
_PIN_SQL = "native/pdf-search-pin.sql"
_RENDERER_FILES = (
    "ingest/pdf_section_views.py",
    "ingest/pdf_hierarchy.py",
    "ingest/pdf_health.py",
    "semantic/source_products.py",
    "semantic/native_source_view.py",
    "semantic/pdf_source_search.py",
    "model/semantic/section-text-recipe.json",
)


def search_configuration(model) -> str:
    configuration = model.tables["ops.pdf_source_search_section"].c.search_vector.info.get(
        "search_configuration"
    )
    if not isinstance(configuration, str) or not configuration:
        raise ValueError("PDF search vector has no declared configuration")
    return configuration


def search_projection_sources(
    *, target_metadata=None, pdf_domain=None
) -> tuple[SourceArtifact, ...]:
    from .pdf_domain import CONTRACT as PDF_DOMAIN_CONTRACT
    from .pdf_domain import PdfDomainContract, pdf_call_bindings, pdf_domain_sources
    from .pdf_search_native import search_program_sql

    root = Path(__file__).resolve().parents[1]
    captured = tuple(
        SourceArtifact("native/search-renderer/" + name, root.joinpath(name).read_bytes())
        for name in _RENDERER_FILES
    )
    renderer = {
        "sources": [(source.name, source.digest) for source in captured],
        "libraries": {name: version(name) for name in ("docling-core", "docling")},
    }
    policy = next(
        source.content for source in captured if source.name.endswith("section-text-recipe.json")
    )
    renderer_digest = sha256(canonical_bytes(renderer)).hexdigest()
    policy_digest = sha256(policy).hexdigest()
    if target_metadata is None:
        from .metadata import get_metadata

        target_metadata = get_metadata()
    configuration = search_configuration(target_metadata)
    if pdf_domain is None and target_metadata.info.get("physical_sources"):
        pdf_sources = pdf_domain_sources(
            physical_sources=target_metadata.info["physical_sources"],
            linkml_types=target_metadata.info["physical_linkml_types"],
        )
        pdf_contract = next(source for source in pdf_sources if source.name == PDF_DOMAIN_CONTRACT)
        pdf_domain = PdfDomainContract(
            pdf_contract.content,
            tuple(source for source in pdf_sources if source.name != PDF_DOMAIN_CONTRACT),
        )
    return (
        *captured,
        SourceArtifact(
            CONTRACT,
            canonical_bytes(
                {
                    "version": "pdf-source-search-v1",
                    "renderer": renderer_digest,
                    "configuration": configuration,
                    "default_policy_digest": policy_digest,
                    "max_fill_bytes": PUBLICATION_FILL_BYTES,
                }
            ),
        ),
        SourceArtifact(
            _PIN_SQL,
            _search_pin_sql(
                target_metadata,
                renderer=renderer_digest,
                configuration=configuration,
                default_policy_digest=policy_digest,
            ).encode(),
        ),
        SourceArtifact(
            "native/pdf-source-search.sql",
            search_program_sql(
                target_metadata,
                pdf_call_bindings(pdf_domain),
                max_fill_bytes=PUBLICATION_FILL_BYTES,
                configuration=configuration,
            ).encode(),
        ),
        SourceArtifact(
            "native/pdf-search-native.py",
            Path(__file__).with_name("pdf_search_native.py").read_bytes(),
        ),
    )


def search_pin_native_programs(
    metadata, *, renderer: str, default_policy_digest: str, configuration: str
) -> tuple[ProgramDeclaration, ...]:
    """Authenticate one selected publication against its captured rendering recipe."""
    from sqlalchemy import Text, func, literal, select
    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.schema.integrity import role_name

    from .native_objects import INTERNAL_PROGRAM
    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        NativeRoutine,
        Parameter,
        Perform,
        Raise,
        Return,
        SelectInto,
        call,
        core_variable,
        pg_type,
        variable,
    )
    from .native_program import (
        literal as pg_literal,
    )
    from .native_program_registry import ProgramDeclaration

    publication = metadata.tables["ops.pdf_published_revision"]
    revision = publication.alias("revision")
    input_ = metadata.tables["sem.input"]
    selected = core_variable("selected", JSONB())
    source = core_variable("p_source", JSONB())
    recipe = core_variable("p_recipe", JSONB())
    expected = core_variable("expected", JSONB())
    policy = core_variable("policy", input_.c.content.type)
    policy_digest = core_variable("policy_digest", input_.c.content_digest.type)
    recipe_digest = core_variable("recipe_digest", Text())
    receipt = selected["receipt"]["publication"]
    release = selected["cut"]["release_id"].astext

    def field(name: str):
        return core_variable("publication", publication.c[name].type, publication.c[name].name)

    routine = NativeRoutine(
        "ops",
        "ddo_pdf_search_pin",
        parameters=(
            Parameter("p_source", pg_type("jsonb")),
            Parameter("p_recipe", pg_type("jsonb")),
        ),
        returns=pg_type("jsonb"),
        volatility="volatile",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            locals=(
                Local("selected", pg_type("jsonb")),
                Local("publication", publication),
                Local("policy_digest", pg_type("text")),
                Local("policy", pg_type("bytea")),
                Local("expected", pg_type("jsonb")),
                Local("recipe_digest", pg_type("text")),
                Local("population", pg_type("text")),
            ),
            statements=(
                Assign(
                    "selected",
                    func.ops.ddo_impl_read_selected_pdf_source(source, type_=JSONB())["payload"],
                ),
                Perform(func.ops.require_pdf_operation(release, literal("search_native_source"))),
                SelectInto(
                    select(*revision.c).where(
                        revision.c.build_id == receipt["build_id"].astext,
                        revision.c.task_id
                        == receipt["task_id"].astext.cast(revision.c.task_id.type),
                        revision.c.product_key == receipt["product_key"].astext,
                        revision.c.logical_digest == receipt["logical_digest"].astext,
                    ),
                    ("publication",),
                    strict=True,
                ),
                SelectInto(
                    select(input_.c.content, input_.c.content_digest).where(
                        input_.c.release_id == release,
                        input_.c.input_kind == "dependency",
                        input_.c.input_name
                        == "execution/implementation/pdf/section-text-recipe.json",
                    ),
                    ("policy", "policy_digest"),
                ),
                If(
                    policy_digest.is_(None),
                    (Assign("policy_digest", literal(default_policy_digest)),),
                    (
                        If(
                            func.encode(func.sha256(policy), literal("hex")).is_distinct_from(
                                policy_digest
                            ),
                            (Raise("search policy differs from retained release bytes", "23514"),),
                        ),
                    ),
                ),
                Assign(
                    "expected",
                    func.jsonb_build_object(
                        "version",
                        "pdf-source-search-v1",
                        "renderer",
                        renderer,
                        "policy_digest",
                        policy_digest,
                        "organization_owner",
                        func.jsonb_build_object(
                            "task_id",
                            field("task_id"),
                            "product_key",
                            field("product_key"),
                            "content_digest",
                            field("logical_digest"),
                        ),
                        "analysis_eligible",
                        True,
                        type_=JSONB(),
                    ),
                ),
                If(
                    recipe.is_distinct_from(expected),
                    (
                        Raise(
                            "search projection recipe differs from selected publication/code",
                            "23514",
                        ),
                    ),
                ),
                Assign("recipe_digest", func.ops.ddo_digest(expected, type_=Text())),
                Assign(
                    "population",
                    literal("pdf-search:")
                    + func.ops.ddo_digest(
                        func.jsonb_build_array(
                            source["project_id"].astext,
                            field("build_id"),
                            field("task_id"),
                            field("product_key"),
                            field("logical_digest"),
                            recipe_digest,
                            configuration,
                        ),
                        type_=Text(),
                    ),
                ),
                Return(
                    call(
                        "pg_catalog",
                        "jsonb_build_object",
                        pg_literal("population_id"),
                        variable("population"),
                        pg_literal("recipe_digest"),
                        variable("recipe_digest"),
                        pg_literal("publication"),
                        call("pg_catalog", "to_jsonb", variable("publication")),
                        pg_literal("selected"),
                        variable("selected"),
                    )
                ),
            ),
        ),
    )
    return (
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        ),
    )


def _search_pin_sql(
    metadata, *, renderer: str, default_policy_digest: str, configuration: str
) -> str:
    return (
        search_pin_native_programs(
            metadata,
            renderer=renderer,
            default_policy_digest=default_policy_digest,
            configuration=configuration,
        )[0].routine.render()
        + ";\n"
    )


@cache
def _running_contract() -> dict:
    return json.loads(
        next(source.content for source in search_projection_sources() if source.name == CONTRACT)
    )


def search_projection_programs(
    sources, *, target_metadata=None, pdf_domain=None
) -> tuple[ProgramDeclaration, ...]:
    """Bind captured rendering determinants at both actual typed search producers."""
    from .pdf_domain import CONTRACT as PDF_CONTRACT
    from .pdf_domain import PdfDomainContract, pdf_call_bindings, pdf_domain_sources
    from .pdf_search_native import search_native_programs

    captured = {source.name: source.content for source in sources}
    if target_metadata is None:
        physical = {
            name.removeprefix("native/projection-physical/"): content
            for name, content in captured.items()
            if name.startswith("native/projection-physical/")
        }
        if physical:
            from corpus_structure.schema.physical import compile_physical

            target_metadata = compile_physical(
                physical, linkml_types=captured["native/projection-linkml-types.yaml"]
            )
        else:
            from .metadata import get_metadata

            target_metadata = get_metadata()
    if pdf_domain is None and target_metadata.info.get("physical_sources"):
        domain_sources = pdf_domain_sources(
            physical_sources=target_metadata.info["physical_sources"],
            linkml_types=target_metadata.info["physical_linkml_types"],
        )
        contract = next(item.content for item in domain_sources if item.name == PDF_CONTRACT)
        pdf_domain = PdfDomainContract(
            contract, tuple(item for item in domain_sources if item.name != PDF_CONTRACT)
        )
    facts = json.loads(captured[CONTRACT])
    pin = search_pin_native_programs(
        target_metadata,
        renderer=facts["renderer"],
        default_policy_digest=facts["default_policy_digest"],
        configuration=facts["configuration"],
    )
    search = search_native_programs(
        target_metadata,
        pdf_call_bindings(pdf_domain),
        max_fill_bytes=facts["max_fill_bytes"],
        configuration=facts["configuration"],
    )
    if "".join(item.routine.render() + ";\n" for item in pin).encode() != captured[_PIN_SQL]:
        raise ValueError("search pin declarations differ from captured rendering/model statements")
    if (
        "".join(item.routine.render() + ";\n" for item in search).encode()
        != captured["native/pdf-source-search.sql"]
    ):
        raise ValueError("search declarations differ from captured rendering/model statements")
    return (*pin, *search)


def search_projection_sql(sources) -> str:
    captured = {source.name: source.content for source in sources}
    return captured[_PIN_SQL].decode() + "\n" + captured["native/pdf-source-search.sql"].decode()


def projection_recipe(connection, source: SelectedPdfSource) -> tuple[dict, bytes | None]:
    from corpus_structure.ingest.pdf_hierarchy import retained_section_text_policy

    policy = retained_section_text_policy(connection, source.prepared)
    contract = _running_contract()
    recipe = {
        "version": "pdf-source-search-v1",
        "renderer": contract["renderer"],
        "policy_digest": sha256(policy).hexdigest()
        if policy is not None
        else contract["default_policy_digest"],
        "organization_owner": source.physical.values(),
        "analysis_eligible": True,
    }
    return recipe, policy


def population_identity(source: SelectedPdfSource, recipe: dict) -> str:
    publication = source.receipt.publication
    return (
        "pdf-search:"
        + sha256(
            canonical_bytes(
                [
                    source.reference.project_id,
                    publication.build_id,
                    publication.task_id,
                    publication.product_key,
                    publication.logical_digest,
                    sha256(canonical_bytes(recipe)).hexdigest(),
                    _running_contract()["configuration"],
                ]
            )
        ).hexdigest()
    )


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
    with (
        engine.connect().execution_options(
            isolation_level="READ COMMITTED",
            postgresql_readonly=False,
        ) as connection,
        connection.begin(),
    ):
        yield connection


def ensure_search_projection(
    connection,
    source: SelectedPdfSource,
    *,
    recipe: dict,
    policy: bytes | None,
    fill_max_bytes: int = PUBLICATION_FILL_BYTES,
) -> SearchPopulation:
    """The definer lock serializes a first fill; cache hits transfer no section text."""
    from corpus_structure.ingest.pdf_section_views import published_section_projections

    from ._data_operation_wire import WireEnsurePdfSearchProjectionRequest
    from .data_operation_storage import DataOperationStorage
    from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
    from .source_products import FrozenNativeSource

    if type(fill_max_bytes) is not int or not 1 <= fill_max_bytes <= PUBLICATION_FILL_BYTES:
        raise ValueError("invalid publication search fill bound")
    storage = DataOperationStorage(connection)
    payload = {
        "source": source.reference.model_dump(),
        "recipe": recipe,
        "configuration": _running_contract()["configuration"],
        "fill_max_bytes": fill_max_bytes,
    }
    result = storage.ensure_pdf_search_projection(
        cast(WireEnsurePdfSearchProjectionRequest, payload)
    )
    if result["state"] == "missing":
        budget = PublishedReadBudget(PUBLICATION_FILL_ROWS, fill_max_bytes)
        reader = PublishedPdfReader(
            connection, source.physical, projection_context=source.prepared, read_budget=budget
        )
        pointers = tuple(row["pointer"] for row in reader.sections())
        rows = []
        scopes: tuple[tuple[Literal["direct", "descendants"], tuple[str, ...]], ...] = (
            ("direct", ("#/body", *pointers)),
            ("descendants", pointers),
        )
        for membership, selected in scopes:
            if not selected:
                continue
            for row in published_section_projections(
                reader,
                selections=selected,
                membership=membership,
                scope=None,
                projection_policy=policy,
                exact_sections=True,
            ):
                projected = FrozenNativeSource.from_projection(
                    source.prepared,
                    document=source.original_source,
                    section_pointer=row.section_pointer,
                    membership=row.membership,
                    text=row.text,
                    pieces=row.pieces,
                    items=row.items,
                    ancestors=row.ancestors,
                    recognition=row.health.get("formula_outcomes", ()),
                ).value
                rows.append(
                    {
                        "section_pointer": row.section_pointer,
                        "membership": row.membership,
                        "projection_digest": projected["source"]["projection"],
                        "projection": {
                            "text": projected["text"],
                            "pieces": projected["pieces"],
                            "items": [item["self_ref"] for item in projected["items"]],
                            "ancestors": [item["self_ref"] for item in projected["ancestors"]],
                            "health": {"formula_outcomes": projected["recognition"]},
                        },
                    }
                )
        rows.sort(key=lambda row: (row["section_pointer"], row["membership"]))
        budget.value(rows)
        result = storage.ensure_pdf_search_projection(
            cast(WireEnsurePdfSearchProjectionRequest, {**payload, "rows": rows})
        )
    expected = population_identity(source, recipe)
    if (
        result["state"] != "ready"
        or result["population_id"] != expected
        or result["set_digest"] is None
    ):
        raise ValueError("native search population differs from the selected publication/recipe")
    return SearchPopulation(expected, result["set_digest"], result["row_count"], recipe)
