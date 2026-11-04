"""Release-bound producer submission, composed with existing protected task completion.

A model session reads its complete packet, prepares a checked result outside a transaction,
then the caller commits the result under its live task attempt. No human grader is involved.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import JsonValue, TypeAdapter, ValidationError
from sqlalchemy import Connection

from corpus_structure.semantic._operation_ids import TaskAttempt, TaskId
from corpus_structure.semantic.operation_results import CompletionResult, OperationResult
from corpus_structure.semantic.proposals import (
    LocatedProposal,
    ProposalIssue,
    ProposalPacket,
    ProposalRefused,
    locate_proposal,
)
from corpus_structure.semantic.types import PreparedRelease


class ProposalProtocolRefused(ProposalRefused):
    """A packet/session mismatch, which does not consume an automated content retry."""


@dataclass(frozen=True)
class RefusedProposal:
    authored: dict[str, JsonValue]
    issues: tuple[ProposalIssue, ...]

    @property
    def clean(self) -> bool:
        return False


class HeldProposalCommit(OperationResult):
    disposition: Literal["held"] = "held"


class CompletedProposalCommit(OperationResult):
    """Completion of the checked report; fact selection has its own outcome domain."""

    disposition: Literal["completed_accepted", "completed_refused"]
    completion: CompletionResult
    producer_binding: dict[str, str]


type ProposalCommit = HeldProposalCommit | CompletedProposalCommit


@dataclass
class ProposalSession:
    prepared: PreparedRelease
    packet: ProposalPacket
    task_id: TaskId
    attempt: TaskAttempt
    holder: str
    _read: set[tuple[str, int]] = field(default_factory=set, init=False, repr=False)
    _checked: LocatedProposal | RefusedProposal | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.prepared.release_id != self.packet.release_id:
            raise ProposalRefused("packet and task interpretation differ")
        if self.task_id < 1 or self.attempt < 1 or not self.holder:
            raise ProposalRefused("submission requires a live task attempt and holder")

    def manifest(self) -> dict[str, Any]:
        return {
            "release_id": self.packet.release_id,
            "packet_hash": self.packet.hash,
            "schema_hash": self.packet.schema_hash,
            "parts": [
                {"name": part.name, "pages": len(self.packet.part_pages(part)), "hash": part.hash}
                for part in self.packet.parts()
            ],
        }

    def read(self, part: str, page: int = 1) -> str:
        selected = next((item for item in self.packet.parts() if item.name == part), None)
        if selected is None:
            raise ProposalRefused("unknown packet part")
        pages = self.packet.part_pages(selected)
        if not 1 <= page <= len(pages):
            raise ProposalRefused("packet page outside available range")
        self._read.add((part, page))
        return pages[page - 1]

    def check(
        self, batch: Mapping[str, Any], *, packet_hash: str, schema_hash: str
    ) -> LocatedProposal | RefusedProposal:
        """Perform source placement before the final SQLAlchemy publication transaction."""
        if packet_hash != self.packet.hash or schema_hash != self.packet.schema_hash:
            raise ProposalProtocolRefused("submission does not match the served packet/schema")
        needed = {
            (part.name, page)
            for part in self.packet.parts()
            for page in range(1, len(self.packet.part_pages(part)) + 1)
        }
        if needed - self._read:
            raise ProposalProtocolRefused("read every packet part/page before submitting")
        if batch.get("unit_ref") != self.packet.frame.unit_ref:
            raise ProposalProtocolRefused("proposal unit does not match its bound source frame")
        try:
            checked = locate_proposal(
                self.prepared,
                batch,
                self.packet.frame,
                known_classes=dict(self.packet.known_classes),
                macros=dict(self.packet.macros),
            )
        except (ProposalRefused, ValidationError) as exc:
            from copy import deepcopy

            checked = RefusedProposal(
                TypeAdapter(dict[str, JsonValue]).validate_python(deepcopy(dict(batch))),
                (ProposalIssue("$", "proposal_invalid", str(exc)),),
            )
        self._checked = checked
        return checked

    def commit(
        self, conn: Connection, checked: LocatedProposal | RefusedProposal
    ) -> ProposalCommit:
        """Append the rich located report and complete the task atomically under its fence."""
        if checked is not self._checked:
            raise ProposalRefused("checked result was not prepared by this served session")
        authored = (
            checked.authored
            if isinstance(checked, RefusedProposal)
            else checked.authored.model_dump(mode="json")
        )
        if authored["unit_ref"] != self.packet.frame.unit_ref:
            raise ProposalRefused("checked proposal belongs to another source unit")
        from sqlalchemy import select

        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.operations import complete_task, hold_agent_result

        tasks = table("ops.task")
        task = conn.execute(
            select(tasks.c.packet_hash, tasks.c.unit_key).where(tasks.c.id == self.task_id)
        ).one()
        if task.packet_hash != self.packet.hash or task.unit_key != self.packet.frame.unit_ref:
            raise ProposalRefused("served packet does not match the recorded task input")
        from corpus_structure.methods.llm.producer import producer_binding
        from corpus_structure.semantic.observations import source_value

        configurations, methods = table("ops.method_config"), table("ops.method")
        frozen = (
            conn.execute(
                select(
                    configurations.c.params,
                    methods.c.name.label("method"),
                    methods.c.version.label("method_version"),
                )
                .join(tasks, tasks.c.method_config_id == configurations.c.id)
                .join(methods, methods.c.id == configurations.c.method_id)
                .where(tasks.c.id == self.task_id)
            )
            .mappings()
            .one()
        )
        producer = producer_binding(
            frozen["method"],
            frozen["params"],
            unit="source_view",
            method_version=frozen["method_version"],
        )
        import os

        invocation_id = os.environ.get("CORPUS_AGENT_INVOCATION_ID")
        diagnostic: dict[str, JsonValue] = {
            "execution_identity": {
                "binding": dict[str, JsonValue](producer.values()),
                "task_id": self.task_id,
                "attempt": self.attempt,
                "holder": self.holder,
                "assurance": "provider_reported" if invocation_id else "manual_operator",
                "invocation_id": invocation_id,
                "provider_reported_model": None,
            },
            "packet_hash": self.packet.hash,
            "schema_hash": self.packet.schema_hash,
            "unit_ref": self.packet.frame.unit_ref,
            "clean": checked.clean,
            "issues": TypeAdapter(tuple[ProposalIssue, ...]).dump_python(
                checked.issues, mode="json"
            ),
            "authored": self.prepared.validate_python(
                "SourceObject", source_value(authored)
            ).model_dump(mode="json"),
        }
        holding = hold_agent_result(
            conn,
            task_id=self.task_id,
            attempt=self.attempt,
            holder=self.holder,
            packet_hash=self.packet.hash,
            clean=checked.clean,
            result=diagnostic,
            prepared=self.prepared,
        )
        if holding.disposition == "held":
            from corpus_structure.semantic.operation_results import validate_result_dimension

            validate_result_dimension(
                self.prepared, "check_submission", "disposition", "held", field="disposition"
            )
            return HeldProposalCommit()
        # The native helper holds the run/task locks through the terminal fence, including a
        # clean result racing an uncertain result. The durable first result cannot be lost.
        error = conn.execute(select(tasks.c.error).where(tasks.c.id == self.task_id)).scalar_one()
        first_result = error.get("semantic_proposal_first_result") if error else None
        envelope = {
            "operation": "agent_submission",
            "result": diagnostic,
            "first_result": first_result,
        }
        if isinstance(checked, RefusedProposal):
            from corpus_structure.semantic.observations import source_value
            from corpus_structure.semantic.operations import binding_of, observation_key

            row = conn.execute(select(tasks).where(tasks.c.id == self.task_id)).mappings().one()
            binding = binding_of(conn, row["run_id"])
            key = observation_key(
                binding,
                row["input_hash"],
                "SourceObservation",
                "semantic_proposal_refused/0",
                row["invocation_key"],
            )
            payload = self.prepared.validate_python(
                "SourceObservation",
                {
                    "observation_key": key,
                    "item_key": "semantic_proposal_refused/0",
                    "family": "semantic_proposal_refused",
                    "outcome": "failed",
                    "confidence_source": "agent",
                    "payload": source_value({"authored": authored, "issues": diagnostic["issues"]}),
                },
            ).model_dump(mode="python")
            coverage = self.prepared.validate_python(
                "SourceCoverage",
                {
                    "family": "claim_proposal",
                    "scope": self.packet.frame.unit_ref,
                    "outcome": "failed",
                    "reason": "proposal content refused after automated resubmission",
                },
            ).model_dump(mode="json")
            envelope["coverage"] = [coverage]
            definition = "SourceObservation"
            kind = "semantic_proposal_refused"
        else:
            payload = checked.stored.model_dump(mode="python")
            definition = "AgentStoredBatch"
            kind = "claim_proposal"
            key = None
        observation = {
            "payload_definition": definition,
            "item_key": payload["item_key"] if isinstance(checked, RefusedProposal) else "proposal",
            "kind": kind,
            "payload": payload,
            "outcome": payload["outcome"] if definition == "SourceObservation" else "produced",
        }
        if key is not None:
            observation["observation_key"] = key
        observations = complete_task(
            conn,
            task_id=self.task_id,
            attempt=self.attempt,
            holder=self.holder,
            prepared=self.prepared,
            envelope=envelope,
            observations=(observation,),
        )
        result = CompletedProposalCommit(
            disposition="completed_refused"
            if isinstance(checked, RefusedProposal)
            else "completed_accepted",
            completion=observations,
            producer_binding=producer.values(),
        )
        from corpus_structure.semantic.operation_results import validate_result_dimension

        validate_result_dimension(
            self.prepared,
            "check_submission",
            "disposition",
            result.disposition,
            field="disposition",
        )
        return result
