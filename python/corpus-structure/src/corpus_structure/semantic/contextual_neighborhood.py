"""Declared mutual neighborhoods over an exact retained inventory and vector frame."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import cache
from math import isfinite
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Integer, Text, cast, column, func, null, select, table
from sqlalchemy.dialects.postgresql import JSONB

from .contextual_numerics import default_retrieval_numerics
from .contextual_operations import _PROFILE, _VECTORS, admitted_contextual_inventory
from .identity import canonical_bytes
from .native_program_registry import ProgramDeclaration
from .types import SourceArtifact


class NeighborhoodNumericalPolicy(BaseModel):
    """The native cosine and ordering contract, independent of candidate fusion."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    postgres_version_num: Annotated[int, Field(ge=180000, lt=190000)]
    pgvector_extension_version: str
    policy: Literal["mutual-exact-cosine-top5-2"] = "mutual-exact-cosine-top5-2"
    representative: Literal["first-C-ordered-group-member"] = "first-C-ordered-group-member"
    distance_operator: Literal["pgvector-vector-cosine"] = "pgvector-vector-cosine"
    tie_collation: Literal["C"] = "C"
    directed_limit: Literal[5] = 5
    membership: Literal["reciprocal-directed-intersection"] = "reciprocal-directed-intersection"
    score_transport: Literal["postgres-float8"] = "postgres-float8"
    nonfinite: Literal["refuse"] = "refuse"
    equality: Literal["canonical-exact"] = "canonical-exact"
    arithmetic: Literal["selected-backend-dependent-bits"] = "selected-backend-dependent-bits"

    def require_runtime(self, connection):
        extensions = table(
            "pg_extension", column("extname", Text), column("extversion", Text), schema="pg_catalog"
        )
        postgres = connection.scalar(
            select(cast(func.current_setting("server_version_num"), Integer))
        )
        vector = connection.scalar(
            select(extensions.c.extversion).where(extensions.c.extname == "vector")
        )
        if (postgres, vector) != (self.postgres_version_num, self.pgvector_extension_version):
            raise ValueError(
                "contextual neighborhood backend differs from selected numerical policy"
            )


@cache
def default_neighborhood_numerics():
    backend = default_retrieval_numerics()
    return NeighborhoodNumericalPolicy(
        postgres_version_num=backend.postgres_version_num,
        pgvector_extension_version=backend.pgvector_extension_version,
    )


def neighborhood_numerical_asset(policy=None):
    selected = default_neighborhood_numerics() if policy is None else policy
    return SourceArtifact(
        "contextual/neighborhood-numerical-policy",
        canonical_bytes({"policy": selected.model_dump(mode="json")}),
    )


def contextual_neighborhood_programs() -> tuple[ProgramDeclaration, ...]:
    """Compile exact mutual cosine neighborhoods over the retained typed JSON frame."""
    from decimal import Decimal

    from pglast import ast
    from pglast.stream import RawStream
    from pgvector.sqlalchemy import VECTOR
    from sqlalchemy import case, distinct, exists, literal, literal_column, true
    from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, aggregate_order_by

    from corpus_structure.schema.integrity import role_name

    from .native_objects import INTERNAL_PROGRAM
    from .native_program import (
        NativeRoutine,
        Parameter,
        call,
        core_variable,
        pg_type,
        variable,
    )
    from .native_program import (
        literal as native_literal,
    )

    inventory = core_variable("inv", JSONB())
    profile = core_variable("profile", JSONB())
    vectors = core_variable("vectors", JSONB())

    def items(value, name):
        return (
            func.pg_catalog.jsonb_array_elements(value)
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
        )

    target_rows = items(inventory["targets"], "target_input")
    targets = (
        select(
            target_rows.c.value["target_id"].astext.label("id"),
            target_rows.c.value["representation_digest"].astext.label("digest"),
            target_rows.c.value["source_binding"].astext.label("source"),
        )
        .cte("targets")
        .prefix_with("MATERIALIZED")
    )
    vector_rows = items(vectors, "vector_input")
    observed = vector_rows.c.value
    vector = literal_column(
        RawStream()(
            ast.TypeCast(
                arg=ast.TypeCast(
                    arg=call(
                        "pg_catalog",
                        "jsonb_extract_path",
                        variable(vector_rows.name, "value"),
                        native_literal("values"),
                    ),
                    typeName=pg_type("text"),
                ),
                typeName=pg_type("public", "vector"),
            )
        ),
        type_=VECTOR(),
    )
    eligible = (
        select(targets.c.id, targets.c.digest, vector.label("vector"))
        .select_from(targets.join(vector_rows, observed["object_id"].astext == targets.c.id))
        .where(
            observed["profile_id"].astext == profile["profile_id"].astext,
            observed["representation_digest"].astext == targets.c.digest,
            observed["source_binding"].astext == targets.c.source,
            func.public.vector_dims(vector) == cast(profile["dimension"].astext, Integer()),
            func.pg_catalog.abs(func.public.vector_norm(vector) - 1) <= Decimal("0.00001"),
        )
        .cte("eligible")
        .prefix_with("MATERIALIZED")
    )
    target_count = select(func.count()).select_from(targets).scalar_subquery()
    eligible_count = select(func.count()).select_from(eligible).scalar_subquery()
    candidate_count = (
        select(func.count())
        .select_from(targets.join(vector_rows, observed["object_id"].astext == targets.c.id))
        .where(observed["profile_id"].astext == profile["profile_id"].astext)
        .scalar_subquery()
    )
    coverage = select(
        case(
            (~exists(select(1).select_from(targets)), "completed"),
            (profile.is_(None), "profile_unavailable"),
            (
                (target_count != eligible_count)
                | (eligible_count != select(func.count(distinct(eligible.c.id))).scalar_subquery())
                | (candidate_count != eligible_count),
                "vector_coverage_unavailable",
            ),
            else_="completed",
        ).label("status")
    ).cte("coverage")
    groups = items(inventory["semantic_groups"], "group_input")
    representatives = (
        select(eligible, groups.c.value["target_id"].astext.label("group_id"))
        .select_from(
            coverage.join(groups, true()).join(
                eligible, eligible.c.id == groups.c.value["member_target_ids"][0].astext
            )
        )
        .where(coverage.c.status == "completed")
        .cte("representatives")
        .prefix_with("MATERIALIZED")
    )
    left = representatives.alias("a")
    right = representatives.alias("b")
    distance = left.c.vector.op("OPERATOR(public.<=>)", return_type=DOUBLE_PRECISION())(
        right.c.vector
    )
    nearest = (
        select(right.c.id, distance.label("distance"))
        .where(right.c.id != left.c.id)
        .order_by(distance, right.c.id.collate("C"))
        .limit(NeighborhoodNumericalPolicy.model_fields["directed_limit"].default)
        .correlate(left)
        .lateral("nearest")
    )
    directed = (
        select(
            left.c.id.label("from_id"),
            nearest.c.id.label("to_id"),
            func.row_number()
            .over(partition_by=left.c.id, order_by=(nearest.c.distance, nearest.c.id.collate("C")))
            .label("rank_"),
            nearest.c.distance,
        )
        .select_from(left.join(nearest, true()))
        .cte("directed")
        .prefix_with("MATERIALIZED")
    )
    forward, reverse = directed.alias("d"), directed.alias("r")
    mutual = (
        select(
            forward.c.from_id,
            forward.c.to_id,
            forward.c.rank_.label("left_rank"),
            reverse.c.rank_.label("right_rank"),
            forward.c.distance,
        )
        .select_from(
            forward.join(
                reverse,
                (reverse.c.from_id == forward.c.to_id) & (reverse.c.to_id == forward.c.from_id),
            )
        )
        .where(forward.c.from_id.collate("C") < forward.c.to_id.collate("C"))
        .cte("mutual")
    )
    object_ = func.pg_catalog.jsonb_build_object
    ranks = select(
        func.pg_catalog.jsonb_agg(
            aggregate_order_by(
                object_(
                    "from_id",
                    directed.c.from_id,
                    "to_id",
                    directed.c.to_id,
                    "rank",
                    directed.c.rank_,
                    "distance",
                    directed.c.distance,
                ),
                directed.c.from_id.collate("C"),
                directed.c.rank_,
            )
        )
    ).scalar_subquery()
    edges = (
        select(
            func.pg_catalog.jsonb_agg(
                aggregate_order_by(
                    object_(
                        "left_id",
                        mutual.c.from_id,
                        "right_id",
                        mutual.c.to_id,
                        "left_group",
                        left.c.group_id,
                        "right_group",
                        right.c.group_id,
                        "left_digest",
                        left.c.digest,
                        "right_digest",
                        right.c.digest,
                        "left_rank",
                        mutual.c.left_rank,
                        "right_rank",
                        mutual.c.right_rank,
                        "distance",
                        mutual.c.distance,
                    ),
                    mutual.c.from_id.collate("C"),
                    mutual.c.to_id.collate("C"),
                )
            )
        )
        .select_from(
            mutual.join(left, left.c.id == mutual.c.from_id).join(
                right, right.c.id == mutual.c.to_id
            )
        )
        .scalar_subquery()
    )
    empty = cast(literal("[]"), JSONB())
    result = select(
        func.pg_catalog.jsonb_strip_nulls(
            object_(
                "policy",
                NeighborhoodNumericalPolicy.model_fields["policy"].default,
                "inventory_id",
                inventory["inventory_id"].astext,
                "profile_id",
                profile["profile_id"].astext,
                "status",
                coverage.c.status,
                "directed_ranks",
                func.coalesce(ranks, empty),
                "edges",
                func.coalesce(edges, empty),
            )
        )
    ).select_from(coverage)
    routine = NativeRoutine(
        "ops",
        "contextual_mutual_neighbors",
        parameters=tuple(
            Parameter(name, pg_type("jsonb")) for name in ("inv", "profile", "vectors")
        ),
        returns=pg_type("jsonb"),
        body=result,
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )
    return (
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        ),
    )


def contextual_neighborhood_sql() -> str:
    """Render the captured kernel from its typed declaration."""
    return contextual_neighborhood_programs()[0].routine.render()


def neighborhood_kernel_asset():
    """Capture the same typed native function used by installation."""
    return SourceArtifact(
        "contextual/neighborhood-native-kernel", contextual_neighborhood_sql().encode()
    )


@dataclass(frozen=True)
class NeighborhoodInputs:
    inventory: Any
    profile: Any
    vectors: tuple
    inventory_value: Any
    profile_value: Any
    vectors_value: Any


def prepare_contextual_neighborhood(inventory, vectors):
    from .observations import source_python

    selected = admitted_contextual_inventory(inventory)
    raw_profile = source_python(vectors["profile"])
    profile = None if raw_profile is None else _PROFILE.validate_python(raw_profile)
    values = _VECTORS.validate_python(source_python(vectors["vectors"]))
    if profile is not None and (
        len(values) > profile.max_items or len(selected.targets) > profile.max_items
    ):
        raise ValueError("contextual neighborhood exceeds the captured encoder population bound")
    # Coverage, duplicates, dimension and normalization are interpreted by the native
    # kernel. Nonfinite values cannot cross PostgreSQL's vector boundary at all.
    if any(not isfinite(value) for vector in values for value in vector.values):
        raise ValueError("contextual neighborhood refuses nonfinite vectors")
    return NeighborhoodInputs(
        selected, profile, values, inventory["inventory"], vectors["profile"], vectors["vectors"]
    )


def query_contextual_neighborhood(connection, inputs, *, numerical_policy=None):
    selected = default_neighborhood_numerics() if numerical_policy is None else numerical_policy
    selected.require_runtime(connection)
    inventory = asdict(inputs.inventory)
    profile = (
        None
        if inputs.profile is None
        else dict(asdict(inputs.profile), profile_id=inputs.profile.profile_id)
    )
    vectors = [asdict(vector) for vector in inputs.vectors]
    # JSONB binds stay on this caller-owned connection. The native kernel builds
    # its transient typed vector relation and owns exact distances and ordering.
    return connection.scalar(
        select(
            func.ops.contextual_mutual_neighbors(
                cast(inventory, JSONB),
                cast(null(), JSONB) if profile is None else cast(profile, JSONB),
                cast(vectors, JSONB),
            )
        )
    )


def finish_contextual_neighborhood(inputs, neighborhood):
    from .observations import source_value

    if (
        neighborhood["policy"] != "mutual-exact-cosine-top5-2"
        or neighborhood["inventory_id"] != inputs.inventory.inventory_id
    ):
        raise ValueError("native neighborhood differs from its exact inventory or policy")
    return {
        "version": "declared-contextual-neighborhood-1",
        "inventory": inputs.inventory_value,
        "profile": inputs.profile_value,
        "vectors": inputs.vectors_value,
        "neighborhood": source_value(neighborhood),
    }


def contextual_neighborhood_values(connection, inventory, vectors, *, numerical_policy=None):
    inputs = prepare_contextual_neighborhood(inventory, vectors)
    neighborhood = query_contextual_neighborhood(
        connection, inputs, numerical_policy=numerical_policy
    )
    return finish_contextual_neighborhood(inputs, neighborhood)


def execute_neighborhood_profile(receiver, inventory, vectors):
    return receiver.execute(inventory, vectors)


@dataclass
class ContextualNeighborhoodPlan:
    prepared: Any
    numerical_policy: NeighborhoodNumericalPolicy
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.core.method import PreparedWork

        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or not binding.sufficient or binding.subject_context is None:
            raise ValueError(
                "contextual neighborhood requires its sufficient acquired source context"
            )
        check_active()
        values = {
            name: self.prepared.validate_json(
                kind, json_bytes(arguments.arguments[name])
            ).model_dump(mode="python", exclude_unset=True)
            for name, kind in (
                ("inventory", "DdoContextualInventory"),
                ("vectors", "DdoContextualVectors"),
            )
        }
        inputs = prepare_contextual_neighborhood(**values)

        def compute():
            self.port._verify()
            check_active()
            with execution_owner.engine.begin() as connection:
                neighborhood = query_contextual_neighborhood(
                    connection, inputs, numerical_policy=self.numerical_policy
                )
            check_active()
            product = finish_contextual_neighborhood(inputs, neighborhood)
            checked = self.prepared.validate_json(
                "DdoContextualNeighborhoodProduct", json_bytes(product)
            ).model_dump(mode="python", exclude_unset=True)
            self.port._verify()
            return PreparedCallResult(checked)

        (result,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        return result


def resolve_neighborhood_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_declared import ContextualNeighborhoodOperation

    from .contextual_operations import contextual_operation_sources, contextual_retrieval_assets
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if (
        selected.semantic_id != ContextualNeighborhoodOperation.__data_operation__["id"]
        or selected.numerical_policy is None
    ):
        raise PortRefusal("contextual neighborhood requires its own operation and numerical policy")
    policy = NeighborhoodNumericalPolicy.model_validate_json(selected.numerical_policy.body)
    receiver = ContextualNeighborhoodOperation(None)
    plan = ContextualNeighborhoodPlan(prepared, policy)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.contextual_neighborhood.ContextualNeighborhoodPlan.plan",
        authorize,
        (
            contextual_retrieval_assets(),
            neighborhood_numerical_asset(policy),
            neighborhood_kernel_asset(),
        ),
        contextual_operation_sources(neighborhood_policy=policy),
        functions=tuple(
            ("corpus_structure.semantic.contextual_neighborhood." + function.__name__, function)
            for function in (
                prepare_contextual_neighborhood,
                query_contextual_neighborhood,
                finish_contextual_neighborhood,
            )
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
