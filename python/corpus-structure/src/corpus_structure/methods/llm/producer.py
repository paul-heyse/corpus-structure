"""One executable proposal binding shared by policy, queue, lease and automation."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from corpus_structure.core.vocab import TaskUnitType

PROPOSAL_PROTOCOL = "semantic-claims"
SUPPORTED_PRODUCERS = frozenset({"agent.opus", "agent.general"})


@dataclass(frozen=True)
class ProducerBinding:
    method: str
    unit: str
    protocol: str
    version: str
    execution_kind: str
    mode: str
    configured_model: str

    def values(self) -> dict[str, str]:
        return asdict(self)


def producer_binding(
    method: str, configuration: Mapping[str, Any], *, unit: str = TaskUnitType.SOURCE_VIEW,
    method_version: str | None = None,
) -> ProducerBinding:
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.proposals import SEMANTIC_AGENT_VERSION

    if method_version is not None and method_version != SEMANTIC_AGENT_VERSION:
        raise OperationConflict("persisted producer version is not executable by this runtime")
    if method not in SUPPORTED_PRODUCERS:
        raise OperationConflict(f"{method}: no implemented proposal producer binding")
    protocol = configuration.get("proposal_protocol", PROPOSAL_PROTOCOL)
    version = configuration.get("proposal_version", SEMANTIC_AGENT_VERSION)
    execution_kind = configuration.get("execution_kind", "agent")
    mode = configuration.get("mode", "extract")
    model = configuration.get("model")
    if (str(unit), protocol, version, execution_kind, mode) != (
        TaskUnitType.SOURCE_VIEW.value,
        PROPOSAL_PROTOCOL,
        SEMANTIC_AGENT_VERSION,
        "agent",
        "extract",
    ):
        raise OperationConflict(
            "producer unit/protocol/version/execution kind/mode is not executable"
        )
    if not isinstance(model, str) or not model.strip():
        raise OperationConflict("producer requires an explicitly configured model")
    return ProducerBinding(method, str(unit), protocol, version, execution_kind, mode, model)
