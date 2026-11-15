"""Selected numerical backend for exact contextual candidate retrieval."""

from functools import cache
from importlib.metadata import version
from platform import python_version
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import Integer, Text, cast, column, func, select, table

from corpus_structure.core.db.extensions import expected_extensions


class RetrievalNumericalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, validate_default=True)

    postgres_version_num: Annotated[int, Field(ge=180000, lt=190000)] = 180007
    pgvector_extension_version: Annotated[str, StringConstraints(pattern=r"^0\.8\.\d+$")] = Field(
        default_factory=lambda: expected_extensions()["vector"]
    )
    pgvector_python_version: Annotated[str, StringConstraints(pattern=r"^\S+$")] = Field(
        default_factory=lambda: version("pgvector")
    )
    sqlalchemy_version: Annotated[str, StringConstraints(pattern=r"^\S+$")] = Field(
        default_factory=lambda: version("sqlalchemy")
    )
    python_version: Annotated[str, StringConstraints(pattern=r"^\S+$")] = Field(
        default_factory=python_version
    )
    text_configuration: Literal["pg_catalog.english"] = "pg_catalog.english"
    distance_operator: Literal["pgvector-vector-cosine"] = "pgvector-vector-cosine"
    reciprocal_rank_offset: Literal[60] = 60
    fusion_arithmetic: Literal["python-float-sum"] = "python-float-sum"
    score_transport: Literal["postgres-float8"] = "postgres-float8"
    nonfinite: Literal["refuse"] = "refuse"
    equality: Literal["canonical-exact"] = "canonical-exact"
    arithmetic: Literal["selected-backend-dependent-bits"] = "selected-backend-dependent-bits"

    def require_fusion_runtime(self):
        if self.python_version != python_version():
            raise ValueError(
                "contextual reciprocal-rank arithmetic differs from selected Python policy"
            )

    def require_runtime(self, connection):
        self.require_fusion_runtime()
        if self.pgvector_python_version != version(
            "pgvector"
        ) or self.sqlalchemy_version != version("sqlalchemy"):
            raise ValueError("contextual retrieval numerical libraries differ from selected policy")
        extensions = table(
            "pg_extension", column("extname", Text), column("extversion", Text), schema="pg_catalog"
        )
        postgres = connection.scalar(
            select(cast(func.current_setting("server_version_num"), Integer))
        )
        vector = connection.scalar(
            select(extensions.c.extversion).where(extensions.c.extname == "vector")
        )
        if postgres != self.postgres_version_num or vector != self.pgvector_extension_version:
            raise ValueError(
                "contextual retrieval backend differs from exact selected numerical policy"
            )


@cache
def default_retrieval_numerics():
    """The repository's observed PG18.7 and actual pinned vector implementation."""
    return RetrievalNumericalPolicy(
        pgvector_extension_version=expected_extensions()["vector"],
        pgvector_python_version=version("pgvector"),
        sqlalchemy_version=version("sqlalchemy"),
    )
