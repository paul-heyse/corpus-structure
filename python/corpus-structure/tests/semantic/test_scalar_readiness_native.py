"""One acquired native read joins exact required scalar origin identities."""

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import (
    WireAttachDataRequestsRequest,
    WireReadDemandResultRequest,
    WireReadGovernedSelectionRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_service import advance_demand_selection
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from native_test_support import principal_engine
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel

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
            "name": name,
            "kind": kind,
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "exact",
                "source": "same-original",
                "origins": ["computation"],
                "coverage": {"role": name, "description": "exact scalar"},
                "identity_requirements": ["episode"],
            },
        }
        for name, kind in (("left", "integer"), ("right", "string"))
    ] + [{**left["roles"][0]}]
    return replace(
        STORAGE,
        name="scalar-readiness",
        declaration_content=canonical_bytes(
            {
                "version": STORAGE.model_version,
                "operations": [left, right, target],
            }
        ),
    )


@pytest.fixture
def scalar_writer(commit_db_engine, native_settings):
    writer = principal_engine(native_settings, "write", commit_db_engine.url.database)
    yield writer
    writer.dispose()


@pytest.fixture
def scalar_reader(commit_db_engine, native_settings):
    reader = principal_engine(native_settings, "read", commit_db_engine.url.database)
    yield reader
    reader.dispose()


def test_native_required_scalar_join_retains_exact_unchanged_origin_use(
    commit_db_engine, scalar_writer, scalar_reader, tmp_path
):
    admin = commit_db_engine
    writer = scalar_writer
    recipe = scalar_recipe()
    preparation = prepare_kernel(recipe, directory=tmp_path / "scalar-kernel")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, recipe, engine=admin, preparation=preparation)
    demand, _, _, right_attached = attach(kernel, operation=RIGHT, targets=(TARGET,))
    right_fence = claim(kernel, right_attached, seconds=300)
    string_kind = kernel.identities[
        next(
            role.kind for role in kernel.model.operation(RIGHT).roles if role.direction == "output"
        ),
        "kind",
    ]

    def string_output(completion):
        completion["outputs"][0]["product"].update(
            kind_contract=string_kind, body=semantic_value("right")
        )

    right_intent = retain(kernel, right_fence, mutate=string_output)
    with admin.begin() as connection:
        selection = advance_demand_selection(
            connection,
            "ddo-test",
            "pair",
            demand["demand_id"],
            expected_demand_id=None,
            expected_generation=0,
        )
    assert selection.generation == 1

    def read(**pins):
        with writer.begin() as connection:
            return DataOperationStorage(connection).resume_data_demand(
                cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"], **pins})
            )

    def settlement(page):
        (obligation,) = [row for row in page["obligations"] if row["operation_id"] == TARGET]
        return obligation["native_settlement"]

    def scope_settlement(page):
        with writer.begin() as connection:
            return DataOperationStorage(connection).read_demand_settlement(
                {"read_id": page["read_id"]}
            )

    def governed(*, scope=None, **options):
        with scalar_reader.begin() as connection:
            return DataOperationStorage(connection).read_governed_selection(
                cast(
                    WireReadGovernedSelectionRequest,
                    dict(
                        project_id="ddo-test",
                        selection_name="pair",
                        scope={"operation_id": TARGET, **(scope or {})},
                        **options,
                    ),
                ),
            )

    def cut_count():
        with admin.connect() as connection:
            return connection.scalar(
                text(
                    "SELECT count(*) FROM ops.data_obligation_cut c JOIN ops.data_obligation o "
                    "ON o.id=c.obligation_id WHERE o.operation_id=:target"
                ),
                {"target": TARGET},
            )

    def readiness(page):
        (obligation,) = [row for row in page["obligations"] if row["operation_id"] == TARGET]
        return obligation["native_readiness"]

    initial = read()
    public_pending = governed()
    assert public_pending["state"] == "Pending"
    assert public_pending["selection_generation"] == 1
    assert public_pending["demand_id"] == demand["demand_id"]
    assert set(public_pending) == {
        "selection_name",
        "selection_generation",
        "state",
        "last_settled",
        "demand_id",
        "read_id",
    }
    assert governed(mode="last-settled")["state"] == "Unknown"
    assert readiness(initial) == {
        "ready": False,
        "roles": [
            {"input_role": name, "state": "missing", "identity": None} for name in ("left", "right")
        ],
    }
    assert settlement(initial) == [
        {
            "selection_name": "pair",
            "selection_generation": 1,
            "state": "pending",
            "binding_read_id": None,
            "attachment_use_id": None,
            "successor_use_id": None,
        }
    ]
    assert cut_count() == 0
    observed = scope_settlement(initial)
    assert observed["read_id"] == initial["read_id"] and observed["scope"] == {}
    assert observed["selections"] == [
        {
            "selection_name": "pair",
            "selection_generation": 1,
            "state": "pending",
            "obligation_count": 3,
            "settled_count": 0,
            "unavailable_count": 0,
            "pending_count": 3,
            "uncovered_count": 0,
            "discovery_complete": True,
        }
    ]
    for producer in (LEFT, RIGHT):
        (row,) = [item for item in initial["obligations"] if item["operation_id"] == producer]
        assert row["native_readiness"] == {"ready": True, "roles": []}
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
    assert scope_settlement(middle)["selections"][0]["state"] == "pending"
    with admin.begin() as connection:
        assert all(
            item.operation != TARGET
            for item in DemandPlanner(
                kernel.model, DataOperationStorage(connection)
            ).bound_requests(middle, authorization=b"{}")
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM ops.demand_use u JOIN ops.data_obligation o "
                    "ON o.id=u.obligation_id WHERE o.operation_id=:target"
                ),
                {"target": TARGET},
            )
            == 0
        )

    # Equal product under another exact episode is outside this demand's read.
    other, _, _, other_attached = attach(kernel, operation=LEFT, inference="other-episode")
    assert other["demand_id"] != demand["demand_id"]
    other_fence = claim(kernel, other_attached, seconds=300)
    other_publication = publish(kernel, other_fence, retain(kernel, other_fence, outputs=(7,)))
    assert other_publication["derivation_id"] != left_publication["derivation_id"]
    with admin.connect() as connection:
        products = connection.execute(
            text(
                "SELECT derivation_id,product_id FROM ops.data_derivation_output "
                "WHERE derivation_id IN (:own,:other)"
            ),
            {"own": left_publication["derivation_id"], "other": other_publication["derivation_id"]},
        ).all()
    assert len(products) == 2 and products[0].product_id == products[1].product_id
    assert readiness(read()) == middle_ready
    assert scope_settlement(read())["selections"][0]["state"] == "pending"

    right_publication = publish(kernel, right_fence, right_intent)
    current = read()
    ready = readiness(current)
    assert ready["ready"] is True
    assert ready["roles"][0] == left_role
    assert ready["roles"][1]["state"] == "ready"
    (right_support,) = ready["roles"][1]["identity"]["support"]
    assert right_support["derivation_id"] == right_publication["derivation_id"]
    assert right_support["admission_use_id"] != left_support["admission_use_id"]
    assert (
        readiness(
            read(
                read_id=middle["read_id"],
                selection=middle["selection"],
                trust_snapshot=middle["trust_snapshot"],
            )
        )
        == middle_ready
    )
    assert publish(kernel, right_fence, right_intent)["replayed"] is True
    assert readiness(read()) == ready
    assert settlement(current)[0]["state"] == "pending"
    assert cut_count() == 0
    with admin.connect() as connection:
        transaction = connection.begin()
        (rolled_back,) = DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
            current, authorization=b"{}"
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM ops.data_obligation_cut WHERE obligation_id=:obligation"
                ),
                {"obligation": rolled_back.obligation},
            )
            == 1
        )
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
        "selection_name": "pair",
        "selection_generation": 1,
        "state": "pending",
        "binding_read_id": current["read_id"],
        "attachment_use_id": native["use_id"],
        "successor_use_id": None,
    }
    assert cut_count() == 1
    successor_fence = claim(kernel, native, seconds=300)

    def joined_output(completion):
        completion.update(inputs=binding["inputs"], support=binding["support"])

    successor_publication = publish(
        kernel,
        successor_fence,
        retain(kernel, successor_fence, outputs=(11,), mutate=joined_output),
    )
    completed = read()
    public_fresh = governed()
    assert public_fresh["state"] == "Fresh"
    assert public_fresh["last_settled"] is False
    wrong_qualification = governed(scope={"analyzed_scope": {"page": 2}})
    assert wrong_qualification["state"] != "Fresh"
    exact_qualification = governed(scope={"analyzed_scope": {"page": 1}})
    assert exact_qualification["state"] == "Fresh"
    assert (
        governed(mode="last-settled", scope={"analyzed_scope": {"page": 1}})["read_id"]
        == exact_qualification["read_id"]
    )
    last_settled = governed(mode="last-settled")
    assert last_settled["state"] == "Fresh" and last_settled["last_settled"] is True
    assert last_settled["read_id"] == public_fresh["read_id"]
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
        read_id=attached_page["read_id"],
        selection=attached_page["selection"],
        trust_snapshot=attached_page["trust_snapshot"],
    )
    assert settlement(pinned_attached) == [attached_cut]

    with admin.begin() as connection:
        superseded = advance_demand_selection(
            connection,
            "ddo-test",
            "pair",
            other["demand_id"],
            expected_demand_id=demand["demand_id"],
            expected_generation=1,
        )
    assert superseded.generation == 2
    historical_fresh = governed(mode="last-settled")
    assert historical_fresh["selection_generation"] == 1
    assert historical_fresh["read_id"] == public_fresh["read_id"]
    assert settlement(read()) == []
    assert cut_count() == 1
    with admin.begin() as connection:
        restored = advance_demand_selection(
            connection,
            "ddo-test",
            "pair",
            demand["demand_id"],
            expected_demand_id=other["demand_id"],
            expected_generation=2,
        )
    assert restored.generation == 3
    historical_again = governed(
        mode="last-settled", read_id=public_fresh["read_id"], selection_generation=1
    )
    assert historical_again["selection_generation"] == 1
    assert historical_again["read_id"] == public_fresh["read_id"]
    restored_page = read()
    assert settlement(restored_page)[0]["state"] == "pending"
    assert settlement(restored_page)[0]["attachment_use_id"] is None

    # A completed historical computation still needs an actual current-generation
    # native authoring step. Identical content cannot promote the old cut.
    reattach = cast(
        WireAttachDataRequestsRequest,
        {
            "read_id": restored_page["read_id"],
            "items": [
                {
                    "obligation_id": scheduled.obligation,
                    "request_meaning": json.loads(scheduled.request),
                    "request_key": native["request_id"],
                    "binding": {**binding, "read_id": restored_page["read_id"]},
                    "replicate": None,
                }
            ],
        },
    )
    with admin.begin() as connection:
        authored = DataOperationStorage(connection).attach_data_requests(reattach)["items"][0]
    assert authored["state"] == "fulfilled"
    assert authored["result"]["derivation_id"] == successor_publication["derivation_id"]
    with admin.begin() as connection:
        assert (
            DataOperationStorage(connection).attach_data_requests(reattach)["items"][0] == authored
        )
    (restored_cut,) = settlement(read())
    assert restored_cut["state"] == "settled" and restored_cut["selection_generation"] == 3
    assert restored_cut["attachment_use_id"] == authored["result"]["use_id"]
    assert restored_cut["successor_use_id"] == authored["result"]["use_id"]
    assert restored_cut["binding_read_id"] == restored_page["read_id"]
    assert cut_count() == 2

    with admin.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:test",
                    "selector_kind": "derivation",
                    "selector": left_publication["derivation_id"],
                    "reason": "left selected authority withdrawn",
                },
            )
        )
    with pytest.raises(DBAPIError, match="read trust changed"):
        governed(mode="last-settled")
    with pytest.raises(DBAPIError, match="read trust changed"):
        governed(mode="last-settled", read_id=public_fresh["read_id"], selection_generation=1)
    revoked = read()
    assert readiness(revoked)["ready"] is False
    assert settlement(revoked)[0]["state"] == "pending"
    assert cut_count() == 2


@pytest.mark.parametrize("outcome", ["empty", "failed"])
def test_closed_scalar_arm_stays_distinct_from_an_incomplete_join(
    commit_db_engine, scalar_writer, tmp_path, outcome
):
    admin = commit_db_engine
    recipe = scalar_recipe()
    preparation = prepare_kernel(recipe, directory=tmp_path / "closed-scalar-kernel")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, recipe, engine=admin, preparation=preparation)
    demand, _, _, right = attach(kernel, operation=RIGHT, targets=(TARGET,))
    with admin.begin() as connection:
        advance_demand_selection(
            connection,
            "ddo-test",
            "closed-pair",
            demand["demand_id"],
            expected_demand_id=None,
            expected_generation=0,
        )

    def read():
        with scalar_writer.begin() as connection:
            return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(
                demand["demand_id"], settlement=True
            )

    def target(page):
        return next(row for row in page["obligations"] if row["operation_id"] == TARGET)

    initial = read()
    assert [arm["state"] for arm in target(initial)["native_readiness"]["roles"]] == [
        "missing",
        "missing",
    ]
    right_fence = claim(kernel, right)
    publish(kernel, right_fence, retain(kernel, right_fence, outputs=(), outcome=outcome))
    interrupted = read()
    assert [arm["state"] for arm in target(interrupted)["native_readiness"]["roles"]] == [
        "missing",
        "unavailable",
    ]
    assert target(interrupted)["native_settlement"][0]["state"] == "pending"
    assert interrupted["scheduler_settlement"]["selections"][0]["state"] == "pending"

    _, _, _, left = attach(kernel, operation=LEFT, targets=(TARGET,))
    left_fence = claim(kernel, left)
    publication = publish(kernel, left_fence, retain(kernel, left_fence, outputs=(7,)))
    completed = read()
    arms = target(completed)["native_readiness"]["roles"]
    assert [arm["state"] for arm in arms] == ["ready", "unavailable"]
    assert arms[0]["identity"]["support"][0]["derivation_id"] == publication["derivation_id"]
    cut = target(completed)["native_settlement"][0]
    assert cut["state"] == "unavailable" and cut["attachment_use_id"] is None
    scope = completed["scheduler_settlement"]["selections"][0]
    assert scope == {
        "selection_name": "closed-pair",
        "selection_generation": 1,
        "state": "unavailable",
        "obligation_count": 3,
        "settled_count": 2 if outcome == "empty" else 1,
        "unavailable_count": 1 if outcome == "empty" else 2,
        "pending_count": 0,
        "uncovered_count": 0,
        "discovery_complete": True,
    }
    with scalar_writer.begin() as connection:
        assert all(
            request.operation != TARGET
            for request in DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
                completed, authorization=b"{}"
            )
        )
