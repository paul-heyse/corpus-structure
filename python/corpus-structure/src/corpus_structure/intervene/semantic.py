"""Release-bound producer submission, composed with existing protected task completion.

A model session reads its complete packet, prepares a checked result outside a transaction,
then the caller commits the result under its live task attempt. No human grader is involved.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Connection

from corpus_structure.semantic.proposals import (
    LocatedProposal,
    ProposalPacket,
    ProposalRefused,
    locate_proposal,
)
from corpus_structure.semantic.types import PreparedRelease


@dataclass
class ProposalSession:
    prepared: PreparedRelease
    packet: ProposalPacket
    task_id: int
    attempt: int
    holder: str
    _read: set[tuple[str, int]] = field(default_factory=set, init=False, repr=False)
    _checked: LocatedProposal | None = field(default=None, init=False, repr=False)

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
    ) -> LocatedProposal:
        """Perform source placement before the final SQLAlchemy publication transaction."""
        if packet_hash != self.packet.hash or schema_hash != self.packet.schema_hash:
            raise ProposalRefused("submission does not match the served packet/schema")
        needed = {
            (part.name, page)
            for part in self.packet.parts()
            for page in range(1, len(self.packet.part_pages(part)) + 1)
        }
        if needed - self._read:
            raise ProposalRefused("read every packet part/page before submitting")
        checked = locate_proposal(
            self.prepared,
            batch,
            self.packet.frame,
            known_classes=dict(self.packet.known_classes),
            macros=dict(self.packet.macros),
        )
        self._checked = checked
        return checked

    def commit(self, conn: Connection, checked: LocatedProposal) -> list[int]:
        """Append the rich located report and complete the task atomically under its fence."""
        if checked is not self._checked:
            raise ProposalRefused("checked result was not prepared by this served session")
        if not checked.clean:
            raise ProposalRefused("unresolved source placement requires automated resubmission")
        payload = checked.stored.model_dump(mode="python")
        if payload["unit_ref"] != self.packet.frame.unit_ref:
            raise ProposalRefused("checked proposal belongs to another source unit")
        from sqlalchemy import select

        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.operations import complete_task

        tasks = table("ops.task")
        task = conn.execute(
            select(tasks.c.packet_hash, tasks.c.unit_key)
            .where(tasks.c.id == self.task_id)
            .with_for_update(read=True)
        ).one()
        if task.packet_hash != self.packet.hash or task.unit_key != self.packet.frame.unit_ref:
            raise ProposalRefused("served packet does not match the recorded task input")
        # Revalidation at the protected operational boundary cannot admit knowledge directly.
        return complete_task(
            conn,
            task_id=self.task_id,
            attempt=self.attempt,
            holder=self.holder,
            prepared=self.prepared,
            observations=(
                {
                    "payload_definition": "AgentStoredBatch",
                    "item_key": "proposal",
                    "kind": "claim_proposal",
                    "payload": payload,
                },
            ),
        )
