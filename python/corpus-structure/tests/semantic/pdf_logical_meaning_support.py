"""Independent expected PDF target records over authentic fixture publications.

These assertions run only inside an actual current native journey. They grant no
provider standing, and do not replace source/support/receipt/refusal controls.
"""

import json

from sqlalchemy import text

from corpus_structure.semantic.data_operation_model import json_context_meaning
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_observations import observation_meaning
from corpus_structure.semantic.pdf_record_identity import IdentityFold, record_frame
from corpus_structure.semantic.product_reference import ProductReference


def assert_published_target_meaning(connection, reference: ProductReference, *, specification=None):
    """Compare the private native lowering to independently assembled frame fields.

    Native/integrated expected values come from their real sealed receipt, rather
    than from the target function being assessed. Observation inputs are traversed
    by physical pin, retaining role/order, with genuine sealed targets as leaves.
    """
    memo = {}

    def expected(pin):
        identity = pin.task_id, pin.product_key, pin.content_digest
        if identity in memo:
            return memo[identity]
        params = dict(task=pin.task_id, key=pin.product_key, digest=pin.content_digest)
        product = connection.execute(
            text("SELECT kind,artifact_digest,contract_digest FROM ops.pdf_product "
                 "WHERE task_id=:task AND product_key=:key AND content_digest=:digest"),
            params,
        ).mappings().one()
        if product["kind"] in ("native", "integrated"):
            revision = connection.execute(
                text("SELECT kind,source_digest,schema_digest,recipe_digest,logical_digest "
                     "FROM ops.pdf_published_revision WHERE task_id=:task AND product_key=:key "
                     "AND logical_digest=:digest"), params,
            ).mappings().one()
            result = {"version": "pdf-published-target-v1", **revision}
        else:
            assert product["kind"] == "recognition_observation"
            assert specification is not None
            retained = connection.execute(
                text("SELECT payload,recipe_digest FROM ops.pdf_product_body "
                     "WHERE task_id=:task AND product_key=:key"), params,
            ).mappings().one()
            supplied = json.loads(bytes(retained["payload"]))
            meaning = json_context_meaning(canonical_bytes(
                observation_meaning(supplied, specification=specification)
            )).decode()
            schema = product["contract_digest"]
            inputs = list(connection.execute(
                text("SELECT input_index,role,input_task_id,input_product_key,input_content_digest "
                     "FROM ops.pdf_product_input WHERE task_id=:task AND product_key=:key "
                     "ORDER BY input_index"), params,
            ).mappings())
            assert inputs and any(row["role"] == "structural" for row in inputs)
            targets = []
            for position, row in enumerate(inputs):
                assert row["input_index"] == position
                target = expected(ProductReference(
                    row["input_task_id"], row["input_product_key"], row["input_content_digest"]
                ))
                targets.append({"ordinal": position, "role": row["role"], "target_meaning": target})
            fold = IdentityFold("records")
            fold.add(record_frame(schema, "observation", "root", (
                ("profile", "pdf-published-target-v1"),
                ("source", product["artifact_digest"]),
                ("recipe", retained["recipe_digest"]),
                ("meaning", meaning),
                ("inputs", canonical_bytes(targets).decode()),
            )))
            result = {
                "version": "pdf-published-target-v1", "kind": "recognition_observation",
                "source_digest": product["artifact_digest"], "schema_digest": schema,
                "recipe_digest": retained["recipe_digest"], "logical_digest": fold.digest().hex(),
            }
        memo[identity] = result
        return result

    expected_value = expected(reference)
    actual = connection.scalar(
        text("SELECT ops.pdf_identity_published_target(:task,:key,:digest)"),
        dict(task=reference.task_id, key=reference.product_key, digest=reference.content_digest),
    )
    assert actual == expected_value
    return actual


def assert_current_target_meanings(case):
    """The current rich journey has raw, organized, integrated and observations.

    Enrichment has its own actual transform-demand journey; declaring that producer
    in a recipe does not establish it ran here.
    """
    assert {"native", "organized", "integrated"} <= case.publications.keys()
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_release

    with case.clone.admin.connect() as connection:
        context = pdf_context_for_release(connection, case.prepared)
        specification = context.domain.source("schema/pdf_observation_meaning").content
        for key in ("native", "organized", "integrated"):
            value = assert_published_target_meaning(connection, case.publications[key])
            assert value["kind"] == ("integrated" if key == "integrated" else "native")
        for reference, _ in case.observations:
            value = assert_published_target_meaning(connection, reference, specification=specification)
            assert value["kind"] == "recognition_observation"
