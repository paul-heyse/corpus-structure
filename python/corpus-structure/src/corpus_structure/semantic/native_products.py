"""Deterministic native authoring products; deployment executes frozen revisions only."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from pglast import ast
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import (
    AddConstraint,
    CheckConstraint,
    CreateIndex,
    CreateTable,
    DefaultClause,
    MetaData,
)

from .metadata import metadata
from .prepared_sql import PreparedSQL

if TYPE_CHECKING:
    from .data_operation_model import EffectiveDataOperationModel
    from .types import SourceArtifact


def selected_fact_query(target_metadata: MetaData | None = None):
    """The fixed accepted-fact projection uses the same scoped relationship keys."""
    from sqlalchemy import and_, select

    target_metadata = metadata if target_metadata is None else target_metadata
    fact, selection = (
        target_metadata.tables["data.fact"].alias("f"),
        target_metadata.tables["data.selection"].alias("s"),
    )
    return select(fact).select_from(
        fact.join(
            selection,
            and_(
                selection.c.realization_id == fact.c.realization_id,
                selection.c.release_id == fact.c.release_id,
                selection.c.fact_id == fact.c.fact_id,
            ),
        )
    )


@dataclass(frozen=True)
class NativeProduct:
    name: str
    content: bytes

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


@dataclass(frozen=True)
class NativeAuthoringProvenance:
    """The exact closed inputs used when a native revision was authored.

    These describe that authoring event. SQL bodies, effects, physical checks,
    privileges and inventories are derived independently by the current generator.
    """

    model_id: str
    inputs: tuple[tuple[str, str], ...]

    def descriptor_fields(self) -> dict:
        return {
            "model_id": self.model_id,
            "inputs": [{"name": name, "sha256": digest} for name, digest in self.inputs],
        }


@dataclass(frozen=True)
class NativeAuthoringInputs:
    """Closed current native authority, independent of application producer acquisition."""

    model: EffectiveDataOperationModel
    sources: tuple[SourceArtifact, ...]
    physical_id: str


def capture_native_authoring_inputs(*, target_metadata: MetaData | None = None) -> NativeAuthoringInputs:
    """Acquire the native protocol, exact physical closure and real helper assets once.

    Application operations, providers and historical execution catalogs are not inputs
    to authoring the shared kernel. Frozen predecessors are separately supplied SQL.
    """
    from dataclasses import asdict
    from pathlib import Path

    from .data_operation_artifacts import capture_port_generator_sources
    from .data_operation_compilation import compile_data_operations
    from .data_operation_storage import native_operation_calls, native_operation_declarations, native_protocol_sources
    from .identity import canonical_bytes
    from .pdf_domain import pdf_domain_sources
    from .types import SourceArtifact

    selected = metadata if target_metadata is None else target_metadata
    physical = selected.info.get("physical_sources")
    types = selected.info.get("physical_linkml_types")
    if not physical or not isinstance(types, bytes):
        raise ValueError("native authoring requires captured physical sources and LinkML types")
    native = native_protocol_sources(physical_sources=physical, linkml_types=types)
    declarations = native_operation_declarations(native)
    calls = native_operation_calls(sources=native)
    sources = (
        *native,
        declarations,
        *capture_port_generator_sources(),
        *pdf_domain_sources(physical_sources=physical, linkml_types=types),
        *(SourceArtifact("physical/" + name, content) for name, content in sorted(physical.items())),
        SourceArtifact("physical/linkml-types.yaml", types),
        SourceArtifact("authoring/native-fixed-calls.json", canonical_bytes([(owner, asdict(call)) for owner, call in calls])),
        *(SourceArtifact("authoring/" + name, Path(__file__).with_name(name).read_bytes()) for name in ("native_products.py", "source_view_native.py", "native_candidate.py", "data_operation_compilation.py", "data_operation_model.py", "data_operation_identity.py")),
        SourceArtifact("authoring/scientific.yaml", Path(__file__).resolve().parents[1].joinpath("model/semantic/scientific.yaml").read_bytes()),
        SourceArtifact("authoring/scientific-evidence.py", Path(__file__).with_name("scientific_evidence.py").read_bytes()),
        SourceArtifact("authoring/runtime-bindings.sql", Path(__file__).with_name("sql").joinpath("runtime_bindings.sql").read_bytes()),
        SourceArtifact("authoring/execution-projection-check.sql", Path(__file__).with_name("sql").joinpath("execution_projection_check.sql").read_bytes()),
        SourceArtifact("authoring/admission.sql", Path(__file__).with_name("sql").joinpath("admission.sql").read_bytes()),
    )
    names = [source.name for source in sources]
    if len(names) != len(set(names)):
        raise ValueError("native authoring source capture repeats an input")
    sources = tuple(sorted(sources, key=lambda item: item.name))
    model = compile_data_operations(declarations=(declarations,), captured_contracts=sources)
    return NativeAuthoringInputs(model, sources, selected.info["physical_model_id"])


def current_authoring_provenance(inputs: NativeAuthoringInputs | None = None) -> NativeAuthoringProvenance:
    """Fingerprint one explicit current native capture, never an application release."""
    captured = capture_native_authoring_inputs() if inputs is None else inputs
    return NativeAuthoringProvenance(
        sha256(captured.model.content).hexdigest(),
        tuple((item.name, item.digest) for item in captured.sources),
    )


def relation_descriptor(relation) -> dict:
    """Complete named physical row shape; PK/FK vectors retain their declared order."""
    from .alembic_privileges import DEFAULT_READ_ROLES

    columns = []
    for column in sorted(relation.columns, key=lambda column: column.name):
        kind = column.type.compile(dialect=dialect()).lower()
        if kind == "float":
            kind = "double precision"
        default = None
        generated = ""
        if column.computed is not None:
            default = str(
                column.computed.sqltext.compile(
                    dialect=dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )
            generated = "v" if column.computed.persisted is False else "s"
        elif column.identity is None and column.server_default is not None:
            if not isinstance(column.server_default, DefaultClause):
                raise ValueError(f"native physical default requires explicit SQL: {column}")
            value = column.server_default.arg
            default = (
                value
                if isinstance(value, str)
                else str(
                    value.compile(
                        dialect=dialect(),
                        compile_kwargs={"literal_binds": True},
                    )
                )
            )
        columns.append(
            dict(
                name=column.name,
                type=kind,
                not_null=not column.nullable,
                default=default,
                identity=("a" if column.identity.always else "d")
                if column.identity is not None
                else "",
                generated=generated,
            )
        )
    result = dict(
        relation=relation.fullname,
        read_roles=list(relation.info.get("read_roles", DEFAULT_READ_ROLES)),
        owner="corpus_sem_publisher",
        columns=columns,
        primary_key=[c.name for c in relation.primary_key.columns],
        foreign_keys=[
            dict(
                name=dialect().identifier_preparer.format_constraint(c),
                columns=[v.name for v in c.columns],
                target=c.elements[0].target_fullname.rsplit(".", 1)[0],
                remote_columns=[e.target_fullname.rsplit(".", 1)[1] for e in c.elements],
                on_delete="a",
                on_update="a",
                match="s",
                deferrable=False,
                deferred=False,
                validated=True,
            )
            for c in sorted(
                relation.foreign_key_constraints,
                key=lambda c: str(dialect().identifier_preparer.format_constraint(c)),
            )
        ],
    )
    return result


def physical_products() -> tuple[NativeProduct, ...]:
    """Render fixed DDL from the single physical model, in dependency order."""
    pg = dialect()
    products = []
    for relation in sorted(metadata.tables.values(), key=lambda item: item.fullname):
        products.append(
            NativeProduct(
                relation.fullname,
                (
                    str(
                        CreateTable(relation, include_foreign_key_constraints=[]).compile(
                            dialect=pg
                        )
                    ).strip()
                    + ";\n"
                ).encode(),
            )
        )
        for index in sorted(relation.indexes, key=lambda item: str(item.name or "")):
            products.append(
                NativeProduct(
                    str(index.name),
                    (str(CreateIndex(index).compile(dialect=pg)).strip() + ";\n").encode(),
                )
            )
    for relation in sorted(metadata.tables.values(), key=lambda item: item.fullname):
        for constraint in sorted(
            relation.foreign_key_constraints, key=lambda item: str(item.name or "")
        ):
            products.append(
                NativeProduct(
                    relation.fullname + "/" + str(constraint.name),
                    (
                        str(
                            AddConstraint(constraint, isolate_from_table=False).compile(dialect=pg)
                        ).strip()
                        + ";\n"
                    ).encode(),
                )
            )
    return tuple(products)


def literal_json_descriptor(sql: str | PreparedSQL, name: str) -> dict[str, Any]:
    """Decode a frozen literal descriptor without executing the supplied SQL."""
    import json

    from .prepared_sql import prepare_sql

    body = function_bodies(sql)[name]
    (raw,) = prepare_sql(body, source=name + ":descriptor").statements
    query = raw.stmt
    if not isinstance(query, ast.SelectStmt) or not query.targetList:
        raise ValueError("native descriptor must be a literal SELECT")
    (target,) = query.targetList
    value = target.val if isinstance(target, ast.ResTarget) else None
    if (
        not isinstance(value, ast.TypeCast)
        or not isinstance(value.arg, ast.A_Const)
        or not isinstance(value.arg.val, ast.String)
        or value.arg.val.sval is None
    ):
        raise ValueError("native descriptor must be a JSON string literal")
    result = json.loads(value.arg.val.sval)
    if not isinstance(result, dict):
        raise ValueError("native descriptor must contain a JSON object")
    return result


def function_bodies(sql: str | PreparedSQL, *, by_signature: bool = False) -> dict[str, str]:
    """Inspect emitted function declarations structurally; never scrape a live deployment."""
    result = {}
    from .prepared_sql import prepare_sql

    for raw in prepare_sql(sql, source="<native function bodies>").statements:
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt):
            from .native_function_signatures import function_signature

            name = (
                function_signature(statement)
                if by_signature
                else ".".join(part.sval for part in statement.funcname or ())
            )
            from .native_sql_body import body_source

            result[name] = body_source(statement)
    return result


def edge_projection(edges: Iterable[tuple[str, str, str, str]]) -> NativeProduct:
    """Finite edges are ordered model data, never inferred from kernel source."""
    from .identity import canonical_bytes

    return NativeProduct("execution-edges.json", canonical_bytes(sorted(edges)))


def derived_publication_sql():
    from pathlib import Path

    from .publication import STAGE_TYPES

    inference_relations = {"typed_value", "fact", "selection", "derivation", "derivation_premise"}
    return (
        Path(__file__)
        .with_name("sql")
        .joinpath("derived_publication.sql")
        .read_text()
        .replace(
            "{accepted_empty_stages}",
            " OR ".join(
                "EXISTS(SELECT FROM pg_temp.sp_" + name + ")"
                for name in STAGE_TYPES
                if name not in inference_relations
            ),
        )
    )


def current_admission_fields(inputs: NativeAuthoringInputs | None = None, *, target_metadata: MetaData | None = None) -> dict:
    """Model-owned admission fields; immutable predecessors own unchanged native programs."""
    from .data_operation_model import MODEL_VERSION
    from .identity import canonical_bytes

    target_metadata = metadata if target_metadata is None else target_metadata
    captured = capture_native_authoring_inputs(target_metadata=target_metadata) if inputs is None else inputs
    if captured.physical_id != target_metadata.info["physical_model_id"]:
        raise ValueError("native authoring capture belongs to another physical model")
    check_sources = [
        (relation.fullname, str(check.name), str(check.sqltext))
        for relation in sorted(target_metadata.tables.values(), key=lambda item: item.fullname)
        for check in sorted(
            (item for item in relation.constraints if isinstance(item, CheckConstraint)),
            key=lambda item: str(item.name),
        )
    ]
    descriptor: dict[str, Any] = {
        "physical_checks_source_digest": sha256(canonical_bytes(check_sources)).hexdigest()
    }
    descriptor["physical_relations"] = sorted(target_metadata.tables)
    descriptor["views"] = [
        {
            "relation": "data.selected_fact",
            "query": str(selected_fact_query(target_metadata).compile(dialect=dialect())),
        }
    ]
    from .scientific_evidence import scientific_report_layout

    layout = scientific_report_layout(next(source.content for source in captured.sources if source.name == "authoring/scientific.yaml"))
    if not layout["comparison_paths"] or not layout["array_rules"]:
        raise ValueError(
            "owned scientific report layout must define comparison and array consumers"
        )
    descriptor["scientific_report_layout"] = layout
    from .analytics import COMPILER_VERSION as analytical_compiler

    descriptor["analytical_abi"] = analytical_compiler
    descriptor["data_operation_abi"] = MODEL_VERSION
    descriptor["physical_id"] = target_metadata.info["physical_model_id"]
    descriptor.update(current_authoring_provenance(captured).descriptor_fields())
    return descriptor


def admission_kernel() -> str:
    """Current enforcement kernel; this does not prepare native deployment products."""
    from pathlib import Path

    required = Path(__file__).with_name("sql").joinpath("admission.sql").read_text()
    required = required.replace(
        "-- {finalized_release}",
        (
            "IF NOT EXISTS(SELECT FROM sem.release_finalization WHERE release_id=r) THEN RAISE "
            "EXCEPTION 'release is not finalized' USING ERRCODE='23514'; END IF;"
        ),
    )
    required = required.replace(
        "-- {record_native_admission}",
        (
            "IF NOT EXISTS(SELECT FROM sem.deployment_admission WHERE release_id=r AND physical"
            "_id=expected->>'physical_id' AND deployment_id=encode(sha256(convert_to(expected::"
            "text,'UTF8')),'hex') AND kind='native' AND content=convert_to(expected::text,'UTF8"
            "')) THEN\n IF NOT (pg_has_role(session_user,'corpus_sem_admitter','USAGE') OR pg_h"
            "as_role(session_user,owner_name,'MEMBER')) THEN RAISE EXCEPTION 'native admission "
            "requires restricted admission phase' USING ERRCODE='42501'; END IF;\n PERFORM sem."
            "record_deployment_admission(r,expected->>'physical_id',encode(sha256(convert_to(ex"
            "pected::text,'UTF8')),'hex'),'native',convert_to(expected::text,'UTF8'));\n END IF"
            ";"
        ),
    )
    return required
