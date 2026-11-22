"""One acquired native read joins exact required scalar origin identities."""

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

from sqlalchemy import text

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic._data_operation_wire import WireReadDemandResultRequest
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_service import advance_demand_selection
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.target_installation import capture_target_installation
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel
from semantic.test_target_installation_native import install_target_root

ROOT = Path(__file__).resolve().parents[4]
LEFT = "urn:ddo-test:source"
RIGHT = "urn:ddo-test:other-source"
TARGET = "urn:ddo-test:pair-consumer"


def scalar_recipe():
    left = source_declaration()
    left["roles"][0].update(maximum=1, collection="scalar")
    right = source_declaration()
    right["id"] = RIGHT
    right["roles"][0].update(kind="string", maximum=1, collection="scalar")
    target = source_declaration()
    target["id"] = TARGET
    target["dependencies"] = [LEFT, RIGHT]
    target["roles"] = [
        {
            "name": name, "kind": kind, "direction": "input",
            "minimum": 1, "maximum": 1, "collection": "scalar", "presence": "required",
            "support": {
                "provenance": "exact", "source": "same-original", "origins": ["computation"],
                "coverage": {"role": name, "description": "exact scalar"},
                "identity_requirements": ["episode"],
            },
        }
        for name, kind in (("left", "integer"), ("right", "string"))
    ] + [{**left["roles"][0]}]
    return replace(
        STORAGE,
        name="scalar-readiness",
        declaration_content=canonical_bytes({
            "version": STORAGE.model_version, "operations": [left, right, target],
        }),
    )


def test_native_required_scalar_join_retains_exact_unchanged_origin_use(
    semantic_bare_engine, tmp_path, monkeypatch
):
    admin = semantic_bare_engine
    epoch = capture_target_installation(get_metadata(), logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    recipe = scalar_recipe()
    preparation = prepare_kernel(recipe, directory=tmp_path / "scalar-kernel")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, recipe, engine=admin, preparation=preparation)
    demand, _, _, right_attached = attach(kernel, operation=RIGHT, targets=(TARGET,))
    right_fence = claim(kernel, right_attached, seconds=300)
    string_kind = kernel.identities[
        next(role.kind for role in kernel.model.operation(RIGHT).roles if role.direction == "output"),
        "kind",
    ]

    def string_output(completion):
        completion["outputs"][0]["product"].update(
            kind_contract=string_kind, body=semantic_value("right")
        )

    right_intent = retain(kernel, right_fence, mutate=string_output)
    with admin.begin() as connection:
        selection = advance_demand_selection(
            connection, "ddo-test", "pair", demand["demand_id"],
            expected_demand_id=None, expected_generation=0,
        )
    assert selection.generation == 1

    def read(**pins):
        with admin.begin() as connection:
            return DataOperationStorage(connection).read_demand_result(
                cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"], **pins})
            )

    def readiness(page):
        (obligation,) = [row for row in page["obligations"] if row["operation_id"] == TARGET]
        assert "inputs_watermark" not in obligation
        return obligation["native_readiness"]

    initial = read()
    assert readiness(initial) == {
        "ready": False,
        "roles": [
            {"input_role": name, "state": "missing", "identity": None}
            for name in ("left", "right")
        ],
    }
    for producer in (LEFT, RIGHT):
        (row,) = [item for item in initial["obligations"] if item["operation_id"] == producer]
        assert row["native_readiness"] == {"ready": True, "roles": []}
        assert "inputs_watermark" not in row
    seed, _, _, left_attached = attach(kernel, operation=LEFT)
    left_fence = claim(kernel, left_attached, seconds=300)
    left_publication = publish(kernel, left_fence, retain(kernel, left_fence, outputs=(7,)))
    # A genuine equal product/episode in another demand still supplies no
    # exact eligible use here. Attach recovers it through native reuse.
    assert readiness(read()) == readiness(initial)
    reused, _, _, left_reused = attach(kernel, operation=LEFT, targets=(TARGET,))
    assert reused == demand and left_reused["fate"] == "fulfilled"
    with admin.begin() as connection:
        seed_use = DataOperationStorage(connection).read_demand_result(
            {"demand_id": seed["demand_id"]}
        )["uses"][0]["use_id"]
    middle = read()
    middle_ready = readiness(middle)
    assert middle_ready["ready"] is False
    left_role, right_role = middle_ready["roles"]
    assert left_role["state"] == "ready" and right_role["state"] == "missing"
    (left_support,) = left_role["identity"]["support"]
    assert left_support["derivation_id"] == left_publication["derivation_id"]
    assert left_support["admission_use_id"] != seed_use
    with admin.begin() as connection:
        assert all(
            item.operation != TARGET
            for item in DemandPlanner(kernel.model, DataOperationStorage(connection)).bound_requests(
                middle, authorization=b"{}"
            )
        )
        assert connection.scalar(text(
            "SELECT count(*) FROM ops.demand_use u JOIN ops.data_obligation o "
            "ON o.id=u.obligation_id WHERE o.operation_id=:target"
        ), {"target": TARGET}) == 0

    # Equal product under another exact episode is outside this demand's read.
    other, _, _, other_attached = attach(kernel, operation=LEFT, inference="other-episode")
    assert other["demand_id"] != demand["demand_id"]
    other_fence = claim(kernel, other_attached, seconds=300)
    other_publication = publish(kernel, other_fence, retain(kernel, other_fence, outputs=(7,)))
    assert other_publication["derivation_id"] != left_publication["derivation_id"]
    with admin.connect() as connection:
        products = connection.execute(text(
            "SELECT derivation_id,product_id FROM ops.data_derivation_output "
            "WHERE derivation_id IN (:own,:other)"
        ), {"own": left_publication["derivation_id"], "other": other_publication["derivation_id"]}).all()
    assert len(products) == 2 and products[0].product_id == products[1].product_id
    assert readiness(read()) == middle_ready

    right_publication = publish(kernel, right_fence, right_intent)
    current = read()
    ready = readiness(current)
    assert ready["ready"] is True
    assert ready["roles"][0] == left_role
    assert ready["roles"][1]["state"] == "ready"
    (right_support,) = ready["roles"][1]["identity"]["support"]
    assert right_support["derivation_id"] == right_publication["derivation_id"]
    assert right_support["admission_use_id"] != left_support["admission_use_id"]
    assert readiness(read(
        read_id=middle["read_id"], selection=middle["selection"],
        trust_snapshot=middle["trust_snapshot"],
    )) == middle_ready
    assert publish(kernel, right_fence, right_intent)["replayed"] is True
    assert readiness(read()) == ready
    with admin.begin() as connection:
        (scheduled,) = DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
            current, authorization=b"{}"
        )
    assert scheduled.operation == TARGET
    binding = json.loads(scheduled.binding)
    for role in ready["roles"]:
        identity = role["identity"]
        assert identity["input"] in binding["inputs"]
        assert identity["support"] == [
            item for item in binding["support"] if item["role"] == role["input_role"]
        ]
