"""Source-free authored external recipe for native custody and transport controls."""

from corpus_structure.semantic.data_operation_version import MODEL_VERSION
from corpus_structure.semantic.identity import canonical_bytes
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_kernel_support import MANIFEST, STORAGE, KernelRecipe


def external_declaration():
    operation = source_declaration()
    operation.update(
        profile="command",
        external={
            "version": "external-executor-v1",
            "instructions": "Return the independently given integer seven in the result role.",
            "requested_actor": "controlled-external",
            "requested_model": None,
            "reference_scope": "declared-inputs-only",
        },
        effects=[
            {
                "name": "external-judgment",
                "authorization": ["native-purpose:write"],
                "idempotency": "external-packet",
                "fulfillment": "native-publication-receipt",
            }
        ],
    )
    operation["capabilities"]["preparation"] = "external"
    return operation


EXTERNAL = KernelRecipe(
    "external-custody",
    STORAGE.schema_text,
    canonical_bytes(
        {"version": MODEL_VERSION, "operations": [external_declaration()], "kinds": []}
    ),
    MANIFEST,
)


def _input_recipe():
    source = source_declaration()
    source["id"] = "urn:ddo-test:packet-source"
    external = external_declaration()
    external["dependencies"] = [source["id"]]
    external["roles"].insert(
        0,
        {
            "name": "selected",
            "kind": "integer",
            "direction": "input",
            "minimum": 2,
            "maximum": 2,
            "collection": "sequence",
            "presence": "required",
            "support": {
                "provenance": "exact",
                "identity_requirements": ["episode"],
                "source": "same-original",
                "coverage": {"role": "selected", "description": "declared-scope"},
            },
        },
    )
    external["binding"] = {"operator": "scan", "roles": ["selected"]}
    return KernelRecipe(
        "external-exact-inputs",
        STORAGE.schema_text,
        canonical_bytes({"version": MODEL_VERSION, "operations": [source, external], "kinds": []}),
        MANIFEST,
    )


EXTERNAL_INPUTS = _input_recipe()
