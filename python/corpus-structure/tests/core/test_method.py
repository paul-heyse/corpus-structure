"""Independent shared payload, digest, settings and configuration-reference contracts."""

from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sysconfig
import unicodedata
from pathlib import Path
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import Column, Connection, MetaData, Table, select, text
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.core.method import (
    ArtifactRef,
    ConfigRef,
    Digest,
    MethodSettings,
    METHOD_SOURCE,
    ObservationDraft,
    PackSection,
    Resources,
    UnitRef,
    UnitResult,
    config_references,
    payload_hash,
)
from corpus_structure.core.payloads import AuthorMarkupPayload, LinkPayload
from corpus_structure.core.vocab import (
    ConfidenceSource,
    ObservationKind,
    ObservationOutcome,
    TaskUnitType,
)

REPO = Path(__file__).resolve().parents[4]


# --- Stub methods ------------------------------------------------------------------------------


class StubConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    threshold: str = "0.5"


def test_digest_retains_exact_input_and_optional_packet_identity() -> None:
    plain = Digest(b"u1|0.5")
    assert plain.bytes == b"u1|0.5" and plain.packet_hash is None
    packet = Digest(b"packet of u1", payload_hash({"packet": "packet of u1"}))
    assert packet.bytes == b"packet of u1"
    # Independent canonical packet bytes, without a run or method dispatcher.
    import hashlib

    assert packet.packet_hash == hashlib.sha256(b'{"packet":"packet of u1"}').hexdigest()


def test_payload_hash_ignores_key_order_and_normalization() -> None:
    nfd = unicodedata.normalize("NFD", "Café")
    assert nfd != "Café"
    written = {"term": "Café", "attrs": {"a": 1, "b": [True, None]}}
    read_back = {"attrs": {"b": [True, None], "a": 1}, "term": nfd}  # as JSONB may return it
    assert payload_hash(written) == payload_hash(read_back)
    assert payload_hash(written) != payload_hash({**written, "term": "cafe"})


def link(score: float = 0.85) -> LinkPayload:
    return LinkPayload(pair=("ent:a", "ent:b"), candidate="ent:b", score=score,
                       features={"cosine": 0.731, "same_page": True})  # fmt: skip


CAFE_NFD = unicodedata.normalize("NFD", "Café")
ROUND_TRIPS: list[BaseModel | dict[str, Any]] = [
    link(),
    LinkPayload(pair=("ent:a", "ent:b"), candidate="ent:b", score=1.0, rank=3,
                features={"count": 1e16, "huge": 1.5e300, "tiny": 1e-20, "sum": 0.1 + 0.2,
                          "whole": 2.0, "big_int": 10**20, "negative": -7, "zero": 0}),
    AuthorMarkupPayload(markup="dfn", value=CAFE_NFD),
    {"score": 1e16, "ints": [0, 1, -1, 2**63], "decimals": [0.5, 1.25, 1e-7, 123456789.125],
     "nested": {"z": {"b": [{"y": 1.0, "x": "Ångström"}], "a": None}, "aa": True},
     "text": CAFE_NFD, CAFE_NFD: "key"},
]  # fmt: skip


@pytest.mark.parametrize("payload", ROUND_TRIPS)
def test_payload_hash_agrees_on_write_and_jsonb_read_back(
    infrastructure_rollback: Connection, payload
) -> None:
    """Written through SQLAlchemy's JSONB binding, read back as psycopg returns it from PG 18."""
    table = Table("payload_round_trip", MetaData(), Column("payload", JSONB, nullable=False),
                  prefixes=["TEMPORARY"])  # fmt: skip
    table.create(infrastructure_rollback)
    written = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    infrastructure_rollback.execute(table.insert(), {"payload": written})
    read_back = infrastructure_rollback.execute(select(table.c.payload)).scalar_one()
    table.drop(infrastructure_rollback)
    assert payload_hash(payload) == payload_hash(read_back)
    assert payload_hash(written) == payload_hash(read_back)


def test_the_jsonb_read_back_differs_from_what_was_written(
    infrastructure_rollback: Connection,
) -> None:
    """The round trip changes what the hash must see through: an integral float comes back an
    integer, keys in JSONB's order, text unnormalized."""
    payload = {"score": 1e16, "ab": 1.0, "b": CAFE_NFD}
    stored = infrastructure_rollback.execute(
        text("SELECT CAST(:p AS jsonb)"), {"p": json.dumps(payload)}
    )
    read_back = stored.scalar_one()
    assert read_back == {"b": CAFE_NFD, "ab": 1.0, "score": 10000000000000000}
    assert isinstance(read_back["score"], int) and list(read_back) == ["b", "ab", "score"]
    assert payload_hash(payload) == payload_hash(read_back)
    assert payload_hash(link()) != payload_hash(link(0.86))
    assert payload_hash({"n": 1}) != payload_hash({"n": 2})


def test_payload_hash_converts_numbers_and_refuses_non_finite_floats() -> None:
    assert payload_hash({"score": 0.85}) == payload_hash({"score": "0.85"})  # decimal_of_float
    assert payload_hash({"score": 1e-3}) == payload_hash({"score": "0.001"})
    assert payload_hash({"score": 1e16}) == payload_hash({"score": 10000000000000000})
    assert payload_hash({"n": 3}) == payload_hash({"n": 3.0}) == payload_hash({"n": "3"})
    for bad in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError, match="non-finite"):
            payload_hash({"score": bad})
    with pytest.raises(ValueError):
        payload_hash({"when": datetime.date(2026, 1, 1)})  # not JSON


# --- Drafts and results ------------------------------------------------------------------------


def test_a_draft_names_its_payload_class_version_and_source() -> None:
    payload = link()
    draft = ObservationDraft(kind=ObservationKind.LINK, payload=payload, payload_class=LinkPayload,
                             payload_version="1")  # fmt: skip
    assert draft.confidence_source is METHOD_SOURCE
    own = ObservationDraft(kind=ObservationKind.LINK, payload=payload, payload_class=LinkPayload,
                           payload_version="1",
                           confidence_source=ConfidenceSource.RULES)  # fmt: skip
    assert own.confidence_source is ConfidenceSource.RULES
    with pytest.raises(TypeError, match="not the named"):
        ObservationDraft(kind=ObservationKind.LINK, payload=payload,
                         payload_class=AuthorMarkupPayload,
                         payload_version="1")  # fmt: skip
    with pytest.raises(TypeError):
        type.__call__(ObservationDraft, kind=ObservationKind.LINK, payload=payload)


@pytest.mark.skipif(shutil.which("pyrefly") is None, reason="blocked: pyrefly not on PATH")
def test_a_draft_without_a_payload_class_fails_to_type_check(tmp_path: Path) -> None:
    snippet = tmp_path / "draft.py"
    snippet.write_text(
        "from corpus_structure.core.method import ObservationDraft\n"
        "from corpus_structure.core.payloads import LinkPayload\n"
        "from corpus_structure.core.vocab import ObservationKind\n"
        "def make(p: LinkPayload) -> object:\n"
        "    return ObservationDraft(kind=ObservationKind.LINK, payload=p, payload_version='1')\n"
    )
    pyrefly = shutil.which("pyrefly")
    assert pyrefly is not None
    out = subprocess.run(
        [pyrefly, "check", str(snippet), "--python-version", "3.14",
         "--search-path", str(REPO / "python/corpus-structure/src"),
         "--site-package-path", sysconfig.get_paths()["purelib"]],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert out.returncode != 0
    assert "payload_class" in out.stdout + out.stderr


def test_a_unit_result_keeps_rule_2() -> None:
    ref = UnitRef(TaskUnitType.RENDITION, 1)
    draft = ObservationDraft(kind=ObservationKind.LINK, payload=link(), payload_class=LinkPayload,
                             payload_version="1")  # fmt: skip
    assert UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, observations=(draft,))
    assert UnitResult(ref=ref, outcome=ObservationOutcome.EMPTY)
    assert UnitResult(ref=ref, outcome=ObservationOutcome.FAILED, error="boom")
    bad_results: list[dict[str, Any]] = [
        {"outcome": ObservationOutcome.PRODUCED},
        {"outcome": ObservationOutcome.EMPTY, "observations": (draft,)},
        {"outcome": ObservationOutcome.FAILED},
        {"outcome": ObservationOutcome.FAILED, "error": "x", "observations": (draft,)},
    ]
    for bad in bad_results:
        with pytest.raises(ValueError, match="rule 2"):
            UnitResult(ref=ref, **bad)


# --- Settings and context ----------------------------------------------------------------------


def test_method_settings_hold_only_their_declared_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    assert set(MethodSettings.model_fields) == {
        "execution_policy",
        "data_dir",
        "model_cache",
        "nemotron_endpoint",
        "nemotron_python",
        "nemotron_worker",
        "nemotron_receipts",
        "nemotron_timeout_seconds",
    }
    monkeypatch.setenv("CORPUS_PATHS__DATA_DIR", "/elsewhere")
    settings = MethodSettings(data_dir=Path("d"), model_cache=Path("m"))
    assert settings.data_dir == Path("d")  # the environment is never read
    assert settings.execution_policy.cpu_native_threads == 1
    assert settings.execution_policy.provider_interop_threads == 1
    assert settings.execution_policy.max_owned_bytes == 2 * 1024**3
    with pytest.raises(ValidationError):
        MethodSettings.model_validate(
            {"data_dir": Path("d"), "model_cache": Path("m"), "execution_policy": {"workers": 0}}
        )
    with pytest.raises(ValidationError):
        MethodSettings.model_validate(
            {"data_dir": Path("d"), "model_cache": Path("m"), "database_url": "postgresql:///x"}
        )
    with pytest.raises(ValidationError):
        MethodSettings.model_validate({})
    from pydantic_settings import BaseSettings

    assert not issubclass(MethodSettings, BaseSettings)


def test_resources_keep_explicit_worker_and_positive_bounds() -> None:
    resource = Resources(worker="encoder", batch_size=4, max_concurrency=2)
    assert (resource.worker, resource.batch_size, resource.max_concurrency) == ("encoder", 4, 2)
    for batch_size, max_concurrency in ((0, 1), (1, -1)):
        with pytest.raises(ValueError, match="at least 1"):
            Resources(batch_size=batch_size, max_concurrency=max_concurrency)


# --- Configuration references ------------------------------------------------------------------


class Sentences(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    abbreviations: Annotated[tuple[str, ...], PackSection("aliases")] = ()


class SourceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_hash: Annotated[str, ArtifactRef("json_schema", "batch.model_facing")] = ""
    sentences: Annotated[Sentences, ConfigRef("segment.sentences")] = Sentences()
    math: Annotated[dict[str, str], PackSection("math")] = {}
    plain: int = 3


def test_a_configs_references_are_found_by_introspection() -> None:
    assert config_references(SourceConfig) == {
        ("schema_hash",): ArtifactRef("json_schema", "batch.model_facing"),
        ("sentences",): ConfigRef("segment.sentences"),
        ("sentences", "abbreviations"): PackSection("aliases"),
        ("math",): PackSection("math"),
    }
    assert config_references(StubConfig) == {}

    class Twice(BaseModel):
        x: Annotated[str, PackSection("a"), ConfigRef("b")] = ""

    with pytest.raises(TypeError, match="2 references"):
        config_references(Twice)
