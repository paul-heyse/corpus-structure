"""Retain and publish an authored result for an authenticated ready request."""

import json
from typing import cast as typing_cast

from corpus_structure.semantic._data_operation_wire import WireRetainDataCompletionIntentRequest
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_demand_support import claim, publish


def complete_ready(ddo_kernel, ready, value=1):
    binding = json.loads(ready.binding)
    claim_fence = claim(ddo_kernel, json.loads(ready.native))
    kind = next(
        role.kind
        for operation in ddo_kernel["model"].operations
        if operation.semantic_id == ready.operation
        for role in operation.roles
        if role.direction == "output"
    )
    kind_contract = ddo_kernel["identities"][kind, "kind"]
    with ddo_kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).retain_data_completion_intent(
            typing_cast(
                WireRetainDataCompletionIntentRequest,
                {
                    **claim_fence,
                    "runtime_id": ddo_kernel["runtime"],
                    "completion": {
                        "outcome": "success",
                        "implementation_revision": "native-test-source-v1",
                        "inputs": binding["inputs"],
                        "support": binding["support"],
                        "outputs": [
                            {
                                "role": "result",
                                "position": 0,
                                "multiplicity": 1,
                                "product": {
                                    "kind_contract": kind_contract,
                                    "body": semantic_value(value),
                                    "members": [],
                                },
                            }
                        ],
                    },
                },
            )
        )
    return publish(ddo_kernel, claim_fence, intent)
