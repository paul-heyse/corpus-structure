"""The selected population owner wakes its exact waiting consumer."""

from pathlib import Path

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic.data_operation_demands import DemandPlanner, RootSubject
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.target_installation import capture_target_installation
from semantic.data_operation_binding_support import discover
from semantic.data_operation_kernel_support import POPULATION, admit_kernel, prepare_kernel
from semantic.test_target_installation_native import install_target_root

ROOT = Path(__file__).resolve().parents[4]


def test_selected_population_wakes_only_exact_waiter(semantic_bare_engine, tmp_path, monkeypatch):
    admin = semantic_bare_engine
    capture = capture_target_installation(get_metadata(), logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, capture, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    prepared = prepare_kernel(POPULATION, directory=tmp_path / "selected-population")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, POPULATION, engine=admin, preparation=prepared)

    demand, selected, parent = discover(
        kernel, additional_roots=(RootSubject("another doc", "source:test", b'{"page":1}'),)
    )
    demand_id = demand["demand_id"]

    def resume(**pins):
        with admin.begin() as connection:
            return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(
                demand_id, **pins
            )

    def consumers(page):
        return {
            str(row["obligation_id"]): row
            for row in page["obligations"]
            if row["operation_id"] == "urn:consumer"
        }

    before = resume()
    targets = consumers(before)
    holder = str(selected["obligation_id"])
    assert {row["subject"] for row in targets.values()} == {"doc", "another doc"}
    with admin.begin() as connection:
        storage = DataOperationStorage(connection)
        for row in targets.values():
            storage.record_data_fate(
                {
                    "obligation_id": row["obligation_id"],
                    "fate": "awaiting-population",
                    "selection": {
                        "read_id": before["read_id"],
                        "inputs_watermark": row["inputs_watermark"],
                        "reasons": [],
                    },
                }
            )
    waiting = resume()
    assert all(not row["binding_population_changed"] for row in consumers(waiting).values())

    with admin.begin() as connection:
        receipt = DataOperationStorage(connection).select_data_population(
            {
                "obligation_id": selected["obligation_id"],
                "population_name": "selected-items",
                "parent_population_id": parent["population_id"],
                "read_id": waiting["read_id"],
            }
        )
    replay = resume(
        read_id=waiting["read_id"],
        selection=waiting["selection"],
        trust_snapshot=waiting["trust_snapshot"],
    )
    assert all(not row["binding_population_changed"] for row in consumers(replay).values())

    current = resume()
    for key, row in consumers(current).items():
        assert row["binding_population_changed"] is (key == holder)
        assert row["inputs_watermark"] == targets[key]["inputs_watermark"]

    with admin.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        (consumer,) = [
            request
            for request in planner.ready(current, authorization=b"{}")
            if request.operation == "urn:consumer"
        ]
    assert consumer.obligation == holder
    assert receipt["evidence"]["selection"]["obligation_id"] == holder
    after = consumers(resume())
    assert {key: row["fate"] for key, row in after.items()} == {
        key: "attached" if key == holder else "awaiting-population" for key in targets
    }
