"""Unicode admission uses the actual current release manifest."""

import pytest
from semantic.test_rich_knowledge_identity import release


@pytest.mark.parametrize("recorded", ["current", "missing", "incompatible"])
def test_unicode_admission_reads_actual_release_manifest(monkeypatch, recorded):
    import json
    from dataclasses import replace
    from typing import cast

    from sqlalchemy import Connection

    from corpus_structure.semantic import unicode_identity
    from corpus_structure.semantic.refusals import SemanticOperationRefusal

    prepared = release()
    manifest = json.loads(prepared.manifest)
    if recorded == "missing":
        del manifest["libraries"]["unicode-identity"]
    elif recorded == "incompatible":
        manifest["libraries"]["unicode-identity"] = "other-recipe"
    prepared = replace(prepared, manifest=json.dumps(manifest).encode())
    connection = cast(Connection, object())
    checked = []
    monkeypatch.setattr(unicode_identity, "require_current_unicode_pair", checked.append)
    if recorded == "current":
        unicode_identity.require_unicode_identity_release(connection, prepared)
        assert checked == [connection]
    else:
        with pytest.raises(SemanticOperationRefusal):
            unicode_identity.require_unicode_identity_release(connection, prepared)
        assert checked == []
