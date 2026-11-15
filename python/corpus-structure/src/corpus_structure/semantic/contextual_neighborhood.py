"""Declared mutual neighborhoods over an exact retained inventory and vector frame."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import cache
from math import isfinite
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Integer, Text, cast, column, func, null, select, table
from sqlalchemy.dialects.postgresql import JSONB

from .contextual_operations import _PROFILE, _VECTORS, admitted_contextual_inventory
from .contextual_numerics import default_retrieval_numerics
from .identity import canonical_bytes
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
        postgres = connection.scalar(select(cast(func.current_setting("server_version_num"), Integer)))
        vector = connection.scalar(select(extensions.c.extversion).where(extensions.c.extname == "vector"))
        if (postgres, vector) != (self.postgres_version_num, self.pgvector_extension_version):
            raise ValueError("contextual neighborhood backend differs from selected numerical policy")


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


def neighborhood_kernel_asset():
    """Capture the actual maintained native function, preserving its authored body."""
    from pglast import ast

    from .prepared_sql import prepare_sql

    path = Path(__file__).with_name("sql") / "source_contributions.sql"
    source = prepare_sql(path.read_text(), source=str(path))
    declarations = [
        source.excerpt(index)
        for index, raw in enumerate(source.statements)
        if isinstance(raw.stmt, ast.CreateFunctionStmt)
        and tuple(part.sval for part in (raw.stmt.funcname or ())) == ("ops", "contextual_mutual_neighbors")
    ]
    if len(declarations) != 1:
        raise ValueError("contextual neighborhood requires its unique native kernel owner")
    return SourceArtifact("contextual/neighborhood-native-kernel", declarations[0].encode())


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
    if profile is not None and (len(values) > profile.max_items or len(selected.targets) > profile.max_items):
        raise ValueError("contextual neighborhood exceeds the captured encoder population bound")
    # Coverage, duplicates, dimension and normalization are interpreted by the native
    # kernel. Nonfinite values cannot cross PostgreSQL's vector boundary at all.
    if any(not isfinite(value) for vector in values for value in vector.values):
        raise ValueError("contextual neighborhood refuses nonfinite vectors")
    return NeighborhoodInputs(selected, profile, values, inventory["inventory"], vectors["profile"], vectors["vectors"])


def query_contextual_neighborhood(connection, inputs, *, numerical_policy=None):
    selected = default_neighborhood_numerics() if numerical_policy is None else numerical_policy
    selected.require_runtime(connection)
    inventory = asdict(inputs.inventory)
    profile = None if inputs.profile is None else dict(asdict(inputs.profile), profile_id=inputs.profile.profile_id)
    vectors = [asdict(vector) for vector in inputs.vectors]
    # JSONB binds stay on this caller-owned connection. The native kernel builds
    # its transient typed vector relation and owns exact distances and ordering.
    return connection.scalar(
        select(func.ops.contextual_mutual_neighbors(
            cast(inventory, JSONB), cast(null(), JSONB) if profile is None else cast(profile, JSONB), cast(vectors, JSONB)
        ))
    )


def finish_contextual_neighborhood(inputs, neighborhood):
    from .observations import source_value

    if neighborhood["policy"] != "mutual-exact-cosine-top5-2" or neighborhood["inventory_id"] != inputs.inventory.inventory_id:
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
    neighborhood = query_contextual_neighborhood(connection, inputs, numerical_policy=numerical_policy)
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
            raise ValueError("contextual neighborhood requires its sufficient acquired source context")
        check_active()
        values = {
            name: self.prepared.validate_json(kind, json_bytes(arguments.arguments[name])).model_dump(mode="python", exclude_unset=True)
            for name, kind in (("inventory", "DdoContextualInventory"), ("vectors", "DdoContextualVectors"))
        }
        inputs = prepare_contextual_neighborhood(**values)

        def compute():
            self.port._verify()
            check_active()
            with execution_owner.engine.begin() as connection:
                neighborhood = query_contextual_neighborhood(connection, inputs, numerical_policy=self.numerical_policy)
            check_active()
            product = finish_contextual_neighborhood(inputs, neighborhood)
            checked = self.prepared.validate_json("DdoContextualNeighborhoodProduct", json_bytes(product)).model_dump(mode="python", exclude_unset=True)
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
    if selected.semantic_id != ContextualNeighborhoodOperation.__data_operation__["id"] or selected.numerical_policy is None:
        raise PortRefusal("contextual neighborhood requires its own operation and numerical policy")
    policy = NeighborhoodNumericalPolicy.model_validate_json(selected.numerical_policy.body)
    receiver = ContextualNeighborhoodOperation(None)
    plan = ContextualNeighborhoodPlan(prepared, policy)
    port = PreparedOriginalCallPort(
        identity, model, selected, sources, custody, receiver.run, plan.plan,
        "corpus_structure.semantic.contextual_neighborhood.ContextualNeighborhoodPlan.plan",
        authorize,
        (contextual_retrieval_assets(), neighborhood_numerical_asset(policy), neighborhood_kernel_asset()),
        contextual_operation_sources(neighborhood_policy=policy),
        functions=tuple(
            ("corpus_structure.semantic.contextual_neighborhood." + function.__name__, function)
            for function in (prepare_contextual_neighborhood, query_contextual_neighborhood, finish_contextual_neighborhood)
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
