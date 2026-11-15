"""Legacy synthetic rich-report fixtures awaiting current semantic consumer migration.

These fixtures manufacture current run/task records; they are not immutable
historical custody and carry no preservation exemption. Current packet lifecycle
and selected-result tests use DeclaredAgentRecipe/DeclaredServingRecipe instead.
Remaining rich exclusion/fact consumers require their actual target projection.
"""

from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from sqlalchemy import Connection, Engine, select

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic import source_frames
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import MethodConfigId, RunId, TaskId
from corpus_structure.semantic.operations import (
    OperationDescriptor,
    claim_tasks,
    create_task,
    record_method,
)
from corpus_structure.semantic.retained_agent_packets import _packet_for_unit
from corpus_structure.semantic.types import PreparedRelease


def create_historical_agent_task(
    conn: Connection,
    *,
    run_id: RunId,
    prepared: PreparedRelease,
    configuration: Mapping[str, Any],
    source_view_id: int,
    unit_key: str,
    method_name: str = "agent.opus",
    trigger=None,
    admin: Engine | None = None,
) -> TaskId:
    """Create one explicitly selected fixture task; no routing, graph or policy execution."""
    from corpus_structure.methods.llm.agent_opus import AgentOpusConfig
    from corpus_structure.methods.llm.producer import producer_binding

    if type(source_view_id) is not int or source_view_id < 1:
        raise ValueError(
            "historical fixture requires an actual positive source-view row identifier"
        )
    producer = producer_binding(method_name, configuration)
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, source_view_id, unit_key)
    packet = _packet_for_unit(conn, run_id, prepared, ref, configuration)
    config_hash = (
        "configuration:"
        + sha256(canonical_bytes([producer.method, producer.version, configuration])).hexdigest()
    )
    from contextlib import nullcontext

    with admin.begin() if admin is not None else nullcontext(conn) as metadata_connection:
        config = record_method(
            metadata_connection,
            OperationDescriptor(
                producer.method,
                producer.version,
                "agent",
                "agent",
                TaskUnitType.SOURCE_VIEW,
                AgentOpusConfig,
                "agent",
            ),
            "extract",
            configuration,
            config_hash,
            prepared=prepared,
        )
    runs = table("ops.run")
    run = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
    input_hash = (
        "historical-fixture:"
        + sha256(
            canonical_bytes(
                [
                    run["release_id"],
                    run["input_realization_id"],
                    run["input_revision"],
                    run["dependencies"].hex(),
                    config_hash,
                    packet.hash,
                ]
            )
        ).hexdigest()
    )
    with admin.begin() if admin is not None else nullcontext(conn) as setup:
        task = create_task(
            setup,
            run_id=run_id,
            config_id=config,
            stage="propose",
            unit_type="source_view",
            unit_id=source_view_id,
            unit_key=unit_key,
            input_hash=input_hash,
            packet_hash=packet.hash,
            agent=True,
            fresh=method_name in run["options"].get("fresh", ()),
            trigger={
                "fixture": "historical-rich-source-report",
                "producer_binding": producer.values(),
                **(trigger or {}),
            },
        )
    reused = conn.scalar(
        select(table("ops.task").c.reused_task_id).where(table("ops.task").c.id == task)
    )
    if reused is None:
        source_frames.capture_source_frame(conn, task, packet)
    return task


def historical_agent_packet(
    conn: Connection, run_id: RunId, task_id: TaskId, prepared: PreparedRelease
):
    """Read the fixture's exact recorded packet without granting any queue capability."""
    tasks, configurations = table("ops.task"), table("ops.method_config")
    row = (
        conn.execute(
            select(tasks.c.unit_id, tasks.c.unit_key, tasks.c.packet_hash, configurations.c.params)
            .join(configurations, configurations.c.id == tasks.c.method_config_id)
            .where(tasks.c.id == task_id, tasks.c.run_id == run_id)
        )
        .mappings()
        .one()
    )
    packet = _packet_for_unit(
        conn,
        run_id,
        prepared,
        UnitRef(TaskUnitType.SOURCE_VIEW, row["unit_id"], row["unit_key"]),
        row["params"],
    )
    if packet.hash != row["packet_hash"]:
        raise ValueError("historical fixture packet differs from its actual native task")
    return packet


class HistoricalAgentPublication:
    """One exact native claim and the production rich report validator/publication owner."""

    def __init__(
        self,
        engine: Engine,
        run_id: RunId,
        task_id: TaskId,
        prepared: PreparedRelease | None = None,
    ):
        from corpus_structure.intervene.semantic import ProposalSession, RefusedProposal
        from corpus_structure.semantic.proposals import LocatedProposal
        from corpus_structure.semantic.releases import open_release

        self.checked: LocatedProposal | RefusedProposal | None = None
        self.engine, self.run_id, self.task_id = engine, run_id, task_id
        with engine.begin() as conn:
            tasks = table("ops.task")
            row = (
                conn.execute(select(tasks).where(tasks.c.id == task_id, tasks.c.run_id == run_id))
                .mappings()
                .one()
            )
            self.prepared = prepared or open_release(conn, row["release_id"])
            self.packet = historical_agent_packet(conn, run_id, task_id, self.prepared)
            holder = "historical-fixture:" + str(task_id)
            claims = claim_tasks(
                conn,
                run_id=RunId(run_id),
                config_id=MethodConfigId(row["method_config_id"]),
                holder=holder,
                agent=True,
                prepared=self.prepared,
            )
            if len(claims) != 1 or claims[0].task_id != task_id:
                raise ValueError("historical fixture did not acquire its exact selected task")
            claim = claims[0]
        self.session = ProposalSession(self.prepared, self.packet, task_id, claim.attempt, holder)
        for part in self.packet.parts():
            for index in range(1, len(self.packet.part_pages(part)) + 1):
                self.session.read(part.name, index)

    def unit(self):
        import json

        return json.loads(next(part.text for part in self.packet.parts() if part.name == "unit"))

    @property
    def issues(self):
        if self.checked is None:
            raise AssertionError("historical fixture has not prepared a rich report")
        return self.checked.issues

    @property
    def stored(self) -> dict[str, Any]:
        from corpus_structure.semantic.proposals import LocatedProposal

        if not isinstance(self.checked, LocatedProposal):
            raise AssertionError("historical fixture expected a located rich report")
        return self.checked.stored.model_dump(mode="python")

    def publish(self, batch):
        checked = self.session.check(
            batch, packet_hash=self.packet.hash, schema_hash=self.packet.schema_hash
        )
        self.checked = checked
        with self.engine.begin() as connection:
            return self.session.commit(connection, checked)
