"""Independent graph faults at current PDF preparation; no database publication claim.

Native record publication and correspondence guards retain their own controls in
``test_pdf_record_native.py`` and ``test_pdf_access_correspondence.py``.
"""

from copy import deepcopy
from hashlib import sha256

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product

from . import pdf_integration_support as fixtures

native_source = fixtures.native_source


@pytest.mark.parametrize(
    ("fault", "exception", "reason"),
    [
        ("missing_target", IndexError, "list index out of range"),
        (
            "wrong_backpointer",
            ValidationError,
            "Document hierarchy is inconsistent. #/body has child #/texts/0 with parent #/texts/1",
        ),
        (
            "multi_parent",
            ValidationError,
            "#/texts/1 references #/texts/0, which is already reachable through another reference",
        ),
        ("leaf", None, ""),
    ],
)
def test_current_preparation_refuses_graph_faults_and_preserves_valid_leafs(
    native_source, fault, exception, reason
):
    value = deepcopy(native_source.payload)
    value["product_key"] = f"edge-{fault}"
    document = value["document"]
    first, second = document["texts"][:2]
    assert first.get("children", []) == [] and second.get("children", []) == []
    if fault == "missing_target":
        document["body"]["children"].append({"$ref": "#/texts/999"})
    elif fault == "wrong_backpointer":
        first["parent"] = {"$ref": second["self_ref"]}
        for item in value["items"]:
            if item["pointer"] == first["self_ref"]:
                item["parent_pointer"] = second["self_ref"]
    elif fault == "multi_parent":
        second.setdefault("children", []).append({"$ref": first["self_ref"]})

    def prepare():
        return prepare_pdf_product(
            value, native_source.original, native_source.schema, native_source.recipe
        )

    if exception is None:
        prepared = prepare()
        assert prepared.values()["document"] == document
        assert prepared.digest == sha256(canonical_bytes(value)).hexdigest()
    else:
        # Docling's model construction currently exposes a raw IndexError for a
        # missing target; keep that distinction from its typed hierarchy failures.
        with pytest.raises(exception) as failure:
            prepare()
        assert reason in str(failure.value)
