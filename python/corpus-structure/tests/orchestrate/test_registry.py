"""The registry and `methods.yaml` (P0-O-1, orchestration §3.2): loading, the whole-replacement
overlay, reference resolution, hashing, recording, and the run's recorded map."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from corpus_structure.core.evidence import config_key
from corpus_structure.core.method import (
    ArtifactRef,
    ConfigRef,
    PackSection,
    Resources,
)
from corpus_structure.core.vocab import ConfidenceSource, MethodFamily, MethodTier, TaskUnitType
from corpus_structure.orchestrate import registry as reg

REPO = Path(__file__).resolve().parents[4]


class Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SentencesConfig(Strict):
    model: str = "en_core_web_sm"
    exclude: tuple[str, ...] = ("ner",)


class IngestConfig(Strict):
    # a reference field holds its resolved form after resolution (core.method's contract)
    sentences: Annotated[Any, ConfigRef("segment.sentences")] = "segment.sentences/default"
    threshold: float = 0.5
    macros: dict[str, str] = {"\\R": "\\mathbb{R}", "\\N": "\\mathbb{N}"}


class AgentConfig(Strict):
    batch_schema: Annotated[str, ArtifactRef("json_schema", "batch.model_facing")] = ""
    math: Annotated[Any, PackSection("math")] = None
    packet_cap_chars: int = 18000


@dataclass
class Stub:
    name: str
    Config: type[BaseModel]
    tier: MethodTier = MethodTier.DETERMINISTIC
    version: str = "1"
    family: MethodFamily = MethodFamily.INGEST
    unit_type: TaskUnitType = TaskUnitType.DOCUMENT
    confidence_source: ConfidenceSource | None = None
    resources: Resources = field(default_factory=Resources)

    def select(self, run: Any, cfg: Any) -> list[Any]:
        return []

    def input_digest(self, unit: Any, cfg: Any) -> Any:
        raise NotImplementedError

    def run(self, units: Any, cfg: Any, ctx: Any) -> list[Any]:
        return []


METHODS = [
    Stub("ingest.pdf", IngestConfig),
    Stub("segment.sentences", SentencesConfig),
    Stub(
        "agent.opus",
        AgentConfig,
        MethodTier.AGENT,
        family=MethodFamily.AGENT,
        confidence_source=ConfidenceSource.AGENT,
    ),
]
ARTIFACTS = {("json_schema", "batch.model_facing"): "a" * 64}


def methods_file(tmp_path: Path, data: dict[str, Any]) -> reg.MethodsFile:
    path = tmp_path / "methods.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return reg.load_methods(path)


FILE = {
    "version": "0.1.0",
    "math": {"macros": {"\\E": "\\mathbb{E}"}, "constants": ["e"]},
    "configs": {
        "ingest.pdf": {"default": {"macros": {"\\P": "\\mathbb{P}"}, "threshold": 0.1}},
        "segment.sentences": {"default": {}, "bare": {"exclude": []}},
        "agent.opus": {"extract": {}, "adjudicate": {"packet_cap_chars": 9000}},
    },
}


def test_every_reference_kind_resolves(tmp_path: Path) -> None:
    registry = reg.MethodRegistry(METHODS, methods_file(tmp_path, FILE))
    resolved = registry.resolve_all(ARTIFACTS)
    assert sorted(resolved) == [
        "agent.opus/adjudicate",
        "agent.opus/extract",
        "ingest.pdf/default",
        "segment.sentences/bare",
        "segment.sentences/default",
    ]
    ingest: Any = resolved["ingest.pdf/default"].params
    assert ingest["sentences"] == {"model": "en_core_web_sm", "exclude": ["ner"]}
    agent = resolved["agent.opus/extract"].params
    assert agent["batch_schema"] == "a" * 64
    assert agent["math"] == {"macros": {"\\E": "\\mathbb{E}"}, "constants": ["e"]}


def test_floats_hash_as_canonical_decimals_and_the_key_covers_defaults(tmp_path: Path) -> None:
    registry = reg.MethodRegistry(METHODS, methods_file(tmp_path, FILE))
    rc = registry.resolve("ingest.pdf", "default", ARTIFACTS)
    assert rc.params["threshold"] == "0.1"
    assert rc.config_hash == config_key("ingest.pdf", "1", rc.params)
    assert set(rc.params) == {"sentences", "threshold", "macros"}


def test_a_nested_object_replaces_the_default_whole(tmp_path: Path) -> None:
    registry = reg.MethodRegistry(METHODS, methods_file(tmp_path, FILE))
    rc = registry.resolve("ingest.pdf", "default", ARTIFACTS)
    assert rc.params["macros"] == {"\\P": "\\mathbb{P}"}  # no default entry merged in
    bare = registry.resolve("segment.sentences", "bare")
    assert bare.params["exclude"] == []


def test_equal_configurations_share_a_key(tmp_path: Path) -> None:
    data = {"configs": {"segment.sentences": {"default": {}, "same": {"model": "en_core_web_sm"}}}}
    registry = reg.MethodRegistry(METHODS, methods_file(tmp_path, data))
    a = registry.resolve("segment.sentences", "default")
    b = registry.resolve("segment.sentences", "same")
    assert a.config_hash == b.config_hash


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"configs": {"extract.gliner": {"default": {}}}}, "no registered method 'extract.gliner'"),
        (
            {"configs": {"segment.sentences": {"default": {"modle": "x"}}}},
            "segment.sentences/default: modle: Extra inputs are not permitted",
        ),
    ],
)
def test_unregistered_methods_and_unknown_params_are_refused(
    tmp_path: Path, data: dict[str, Any], message: str
) -> None:
    with pytest.raises(reg.RegistryError, match=message):
        reg.MethodRegistry(METHODS, methods_file(tmp_path, data)).resolve_all(ARTIFACTS)


def test_a_missing_artifact_or_section_is_refused(tmp_path: Path) -> None:
    registry = reg.MethodRegistry(METHODS, methods_file(tmp_path, {"configs": {}}))
    with pytest.raises(reg.RegistryError) as err:
        registry.resolve("agent.opus", "default", {})
    assert any("no json_schema batch.model_facing artifact" in p for p in err.value.problems)
    assert any("no section 'math'" in p for p in err.value.problems)


def test_the_loader_ignores_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = methods_file(tmp_path, FILE)
    before = reg.MethodRegistry(METHODS, file).resolve_all(ARTIFACTS)
    monkeypatch.setenv("CORPUS_GPU__MODE", "exclusive")
    monkeypatch.setenv("CORPUS_PATHS__DATA_DIR", "/elsewhere")
    after = reg.MethodRegistry(METHODS, reg.load_methods(tmp_path / "methods.yaml"))
    assert {k: v.config_hash for k, v in after.resolve_all(ARTIFACTS).items()} == {
        k: v.config_hash for k, v in before.items()
    }


def test_literal_configuration_reference_is_validated_as_referenced_value(tmp_path: Path):
    import copy

    source: dict[str, Any] = copy.deepcopy(FILE)
    source["configs"]["ingest.pdf"]["default"]["sentences"] = {
        "model": "explicit-model",
        "exclude": [],
    }
    registry = reg.MethodRegistry(METHODS, methods_file(tmp_path, source))
    result = registry.resolve("ingest.pdf", "default", ARTIFACTS)
    assert result.params["sentences"] == {"model": "explicit-model", "exclude": []}


def test_statistics_producer_configurations_are_executable():
    from corpus_structure.methods.llm.agent_opus import AgentOpus
    from corpus_structure.methods.llm.producer import producer_binding

    pack = reg.load_methods(Path(__file__).parents[4] / "domains/statistics/methods.yaml")
    named = pack.configs["agent.opus"]
    assert set(named) == {"extract", "expectation"}
    registry = reg.MethodRegistry([AgentOpus()], reg.MethodsFile(configs={"agent.opus": named}))
    for method, name in registry.named():
        binding = producer_binding(method, registry.overlay(method, name).model_dump(mode="json"))
        assert binding.mode == "extract"
        assert registry.method(method).version == binding.version
