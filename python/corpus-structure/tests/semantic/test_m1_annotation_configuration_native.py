"""Persisted annotation v1 survives the projection-selector configuration ABI."""

from hashlib import sha256
from types import SimpleNamespace
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.m1_annotations import M1AnnotationConfig, M1Annotations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict, record_method

from .operation_scenario_support import prepare_operation_scenario


# The original v1 class had no description in its JSON schema.
class LegacyAnnotationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", title="M1AnnotationConfig")
    recipe: Literal["m1-owned-linguistic-product-1"] = "m1-owned-linguistic-product-1"
    sentences: SentenceConfig = Field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    max_annotation_chars: int = Field(default=32768, ge=1)


class UnversionedSelector(M1Annotations):
    version = "1"


def test_projection_selector_versions_contract_without_mutating_persisted_v1(
    semantic_db_engine, semantic_writer_engine
):
    legacy_digest = sha256(canonical_bytes(LegacyAnnotationConfig.model_json_schema())).hexdigest()
    assert legacy_digest == "6ea6682a111c7097c3c26df64ed5f2a807289dc9843d20527d5e4f2e9f4e345e"
    prepared = prepare_operation_scenario(semantic_db_engine)
    legacy_params = LegacyAnnotationConfig().model_dump(mode="json")
    legacy_method = SimpleNamespace(
        name=M1Annotations.name,
        version="1",
        family="extract",
        tier="deterministic",
        confidence_source=None,
        unit_type="source_view",
        Config=LegacyAnnotationConfig,
    )
    with semantic_writer_engine.begin() as conn:
        old_config = record_method(
            conn,
            legacy_method,
            "default",
            legacy_params,
            sha256(canonical_bytes(legacy_params)).hexdigest(),
            prepared=prepared,
        )
    methods, configs = map(table, ("ops.method", "ops.method_config"))
    with semantic_db_engine.connect() as conn:
        before = dict(
            conn.execute(
                select(methods).where(
                    methods.c.name == M1Annotations.name, methods.c.version == "1"
                )
            )
            .mappings()
            .one()
        )
    params = M1AnnotationConfig(source_projection_digest="a" * 64).model_dump(mode="json")
    with (
        pytest.raises(OperationConflict, match="another method contract"),
        semantic_writer_engine.begin() as conn,
    ):
        record_method(
            conn,
            UnversionedSelector(),
            "default",
            params,
            sha256(canonical_bytes(params)).hexdigest(),
            prepared=prepared,
        )
    with semantic_writer_engine.begin() as conn:
        new_config = record_method(
            conn,
            M1Annotations(),
            "default",
            params,
            sha256(canonical_bytes(params)).hexdigest(),
            prepared=prepared,
        )
    with semantic_db_engine.connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                select(methods).where(methods.c.name == M1Annotations.name)
            ).mappings()
        ]
        assert {row["version"] for row in rows} == {"1", "2"}
        assert next(row for row in rows if row["version"] == "1") == before
        assert (
            conn.scalar(select(configs.c.params).where(configs.c.id == old_config)) == legacy_params
        )
        assert conn.scalar(select(configs.c.params).where(configs.c.id == new_config)) == params
        assert old_config != new_config
