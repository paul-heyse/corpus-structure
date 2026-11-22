"""One acquired native read joins exact required scalar origin identities."""

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

from sqlalchemy import text

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic._data_operation_wire import (
    WireAttachDataRequestsRequest,
    WireReadDemandResultRequest,
    WireRevokeDataSupportRequest,
)
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

    def settlement(page):
        (obligation,) = [row for row in page["obligations"] if row["operation_id"] == TARGET]
        return obligation["native_settlement"]

    def cut_count():
        with admin.connect() as connection:
            return connection.scalar(text(
                "SELECT count(*) FROM ops.data_obligation_cut c JOIN ops.data_obligation o "
                "ON o.id=c.obligation_id WHERE o.operation_id=:target"
            ), {"target": TARGET})

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
    assert settlement(initial) == [{
        "selection_name": "pair", "selection_generation": 1, "state": "pending",
        "binding_read_id": None, "attachment_use_id": None, "successor_use_id": None,
    }]
    assert cut_count() == 0
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
    assert settlement(current)[0]["state"] == "pending"
    assert cut_count() == 0
    with admin.connect() as connection:
        transaction = connection.begin()
        (rolled_back,) = DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
            current, authorization=b"{}"
        )
        assert connection.scalar(text(
            "SELECT count(*) FROM ops.data_obligation_cut WHERE obligation_id=:obligation"
        ), {"obligation": rolled_back.obligation}) == 1
        transaction.rollback()
    assert cut_count() == 0
    assert settlement(read())[0]["attachment_use_id"] is None
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

    native = json.loads(scheduled.native)
    attached_page = read()
    (attached_cut,) = settlement(attached_page)
    assert attached_cut == {
        "selection_name": "pair", "selection_generation": 1, "state": "pending",
        "binding_read_id": current["read_id"], "attachment_use_id": native["use_id"],
        "successor_use_id": None,
    }
    assert cut_count() == 1
    successor_fence = claim(kernel, native, seconds=300)

    def joined_output(completion):
        completion.update(inputs=binding["inputs"], support=binding["support"])

    successor_publication = publish(
        kernel, successor_fence,
        retain(kernel, successor_fence, outputs=(11,), mutate=joined_output),
    )
    completed = read()
    (completed_cut,) = settlement(completed)
    assert completed_cut["state"] == "settled"
    assert completed_cut["attachment_use_id"] == native["use_id"]
    assert completed_cut["binding_read_id"] == current["read_id"]
    successor_use = next(
        use for use in completed["uses"] if use["obligation_id"] == scheduled.obligation
    )
    assert completed_cut["successor_use_id"] == successor_use["use_id"]
    assert successor_use["derivation_id"] == successor_publication["derivation_id"]
    assert completed_cut["successor_use_id"] != completed_cut["attachment_use_id"]
    assert readiness(completed) == ready
    pinned_attached = read(
        read_id=attached_page["read_id"], selection=attached_page["selection"],
        trust_snapshot=attached_page["trust_snapshot"],
    )
    assert settlement(pinned_attached) == [attached_cut]

    with admin.begin() as connection:
        superseded = advance_demand_selection(
            connection, "ddo-test", "pair", other["demand_id"],
            expected_demand_id=demand["demand_id"], expected_generation=1,
        )
    assert superseded.generation == 2
    assert settlement(read()) == []
    assert cut_count() == 1
    with admin.begin() as connection:
        restored = advance_demand_selection(
            connection, "ddo-test", "pair", demand["demand_id"],
            expected_demand_id=other["demand_id"], expected_generation=2,
        )
    assert restored.generation == 3
    restored_page = read()
    assert settlement(restored_page)[0]["state"] == "pending"
    assert settlement(restored_page)[0]["attachment_use_id"] is None

    # A completed historical computation still needs an actual current-generation
    # native authoring step. Identical content cannot promote the old cut.
    reattach = cast(WireAttachDataRequestsRequest, {
        "read_id": restored_page["read_id"],
        "items": [{
            "obligation_id": scheduled.obligation,
            "request_meaning": json.loads(scheduled.request),
            "request_key": native["request_id"],
            "binding": {**binding, "read_id": restored_page["read_id"]},
            "replicate": None,
        }],
    })
    with admin.begin() as connection:
        authored = DataOperationStorage(connection).attach_data_requests(reattach)["items"][0]
    assert authored["state"] == "fulfilled"
    assert authored["result"]["derivation_id"] == successor_publication["derivation_id"]
    with admin.begin() as connection:
        assert DataOperationStorage(connection).attach_data_requests(reattach)["items"][0] == authored
    (restored_cut,) = settlement(read())
    assert restored_cut["state"] == "settled" and restored_cut["selection_generation"] == 3
    assert restored_cut["attachment_use_id"] == authored["result"]["use_id"]
    assert restored_cut["successor_use_id"] == authored["result"]["use_id"]
    assert restored_cut["binding_read_id"] == restored_page["read_id"]
    assert cut_count() == 2
    with admin.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(cast(WireRevokeDataSupportRequest, {
            "project_id": "ddo-test", "original_source": "source:test",
            "selector_kind": "derivation", "selector": left_publication["derivation_id"],
            "reason": "left selected authority withdrawn",
        }))
    revoked = read()
    assert readiness(revoked)["ready"] is False
    assert settlement(revoked)[0]["state"] == "pending"
    assert cut_count() == 2
