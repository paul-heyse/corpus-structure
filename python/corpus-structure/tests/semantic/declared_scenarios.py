"""Current declared packet and selected-result scenario producers."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from scenario_recipes import register_scenario_builder
from sqlalchemy import Engine, select

from corpus_structure.semantic._data_operation_wire import WireDemandId, WireExternalPacketId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.types import PreparedRelease

if TYPE_CHECKING:
    from semantic.data_operation_kernel_support import KernelSeedStage


@dataclass(frozen=True)
class DeclaredAgentRecipe:
    """Current packet lifecycle over authentic published semantic source products.

    These integer products exercise custody, context and multiplicity. They do
    not stand in for rich reports, reference answers or consolidated facts.
    """

    source_values: tuple[int, int] = (3, 5)
    subject: str = "declared-agent:subject"
    original_source: str = "declared-agent:source"


@dataclass(frozen=True)
class DeclaredAgentStage:
    kernel: KernelSeedStage
    demand_id: WireDemandId
    packet_id: WireExternalPacketId
    source_receipt: bytes
    subject: str
    original_source: str
    project_id: str = "ddo-test"

    @property
    def prepared(self) -> PreparedRelease:
        return self.kernel.preparation.prepared

    @property
    def runtime(self) -> str:
        return self.kernel.preparation.runtime.runtime_id

    @property
    def seed_files(self) -> tuple[Path, ...]:
        return self.kernel.seed_files

    def validate_clone(self, admin: Engine) -> None:
        self.kernel.validate_clone(admin)
        receipt = json.loads(self.source_receipt)
        with admin.connect() as connection:
            actual = connection.scalar(
                select(table("ops.data_publication_receipt").c.derivation_id).where(
                    table("ops.data_publication_receipt").c.id == receipt["receipt_id"]
                )
            )
        if actual != receipt["derivation_id"]:
            raise ValueError("declared packet seed lost its authentic source episode")


def build_declared_agent_recipe(
    recipe: DeclaredAgentRecipe,
    admin: Engine,
    writer: Engine,
    directory: Path,
    *,
    purpose_engine=None,
) -> DeclaredAgentStage:
    """Publish exact source values and hand off an admitted external request."""
    from typing import cast

    from corpus_structure.semantic._data_operation_wire import WireRetainExternalDataPacketRequest
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.data_operation_demand_support import claim, publish, retain
    from semantic.data_operation_kernel_support import Kernel, build_kernel
    from semantic.external_scenarios import EXTERNAL_INPUTS

    stage = build_kernel(EXTERNAL_INPUTS, admin, writer, directory, purpose_engine=purpose_engine)
    kernel = Kernel(writer, stage.preparation, stage.identities, EXTERNAL_INPUTS)
    frozen = freeze_demand(
        kernel.model,
        roots=(RootSubject(recipe.subject, recipe.original_source, b'{"page":1}'),),
        targets=("urn:ddo-test:source",),
        inference="declared-agent-fixture",
        execution_profile="execution:test",
    )
    with writer.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        demand = planner.register(
            frozen, project="ddo-test", release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
        (producer,) = planner.ready(planner.resume(demand), authorization=b"{}")
    source_claim = claim(kernel, json.loads(producer.native))
    source_receipt = publish(
        kernel, source_claim, retain(kernel, source_claim, outputs=recipe.source_values)
    )
    with writer.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        (external,) = planner.ready(planner.resume(demand), authorization=b"{}")
    external_claim = claim(kernel, json.loads(external.native))
    with writer.begin() as connection:
        packet = DataOperationStorage(connection).retain_external_data_packet(
            cast(
                WireRetainExternalDataPacketRequest,
                {**external_claim, "runtime_id": kernel.runtime, "max_bytes": 100000},
            )
        )
    return DeclaredAgentStage(
        stage,
        demand,
        packet["packet_id"],
        canonical_bytes(source_receipt),
        recipe.subject,
        recipe.original_source,
    )


register_scenario_builder(DeclaredAgentRecipe, build_declared_agent_recipe)


@dataclass(frozen=True)
class DeclaredServingRecipe:
    """Completed current selected result; no run, task or synthetic fact addresses."""

    source_values: tuple[int, int] = (3, 5)
    result: int = 7


@dataclass(frozen=True)
class DeclaredServingStage:
    agent: DeclaredAgentStage
    publication: bytes

    @property
    def seed_files(self):
        return self.agent.seed_files

    @property
    def prepared(self):
        return self.agent.prepared

    @property
    def demand_id(self):
        return self.agent.demand_id

    def validate_clone(self, admin: Engine) -> None:
        self.agent.validate_clone(admin)
        from corpus_structure.semantic.demand_results import read_demand_result

        expected = json.loads(self.publication)["publication"]["derivation_id"]
        with admin.begin() as connection:
            selected = read_demand_result(
                connection, self.demand_id, project_id=self.agent.project_id
            )
        if not any(member["derivation_id"] == expected for member in selected.members()):
            raise ValueError("serving seed lacks its actual selected producing episode")


def build_declared_serving_recipe(recipe, admin, writer, directory, *, purpose_engine=None):
    from corpus_structure.semantic.data_operation_external import ExternalDataSession
    from corpus_structure.semantic.identity import canonical_bytes

    agent = build_declared_agent_recipe(
        DeclaredAgentRecipe(recipe.source_values),
        admin,
        writer,
        directory,
        purpose_engine=purpose_engine,
    )
    session = ExternalDataSession(writer, agent.project_id, demand_id=agent.demand_id)
    claim = session.claim(agent.packet_id)
    if claim["state"] != "claimed":
        raise ValueError("declared serving fixture failed to acquire its packet")
    publication = session.submit(
        agent.packet_id,
        claim,
        {"outcome": "success", "outputs": [{"role": "result", "body": recipe.result}]},
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    return DeclaredServingStage(agent, canonical_bytes(publication))


register_scenario_builder(DeclaredServingRecipe, build_declared_serving_recipe)


@pytest.fixture(scope="session")
def declared_serving_seed(scenario_seeds):
    return scenario_seeds.seed(DeclaredServingRecipe())


@pytest.fixture
def declared_serving_case(declared_serving_seed, scenario_seeds):
    with scenario_seeds.commit_clone(declared_serving_seed.recipe) as clone:
        yield clone
