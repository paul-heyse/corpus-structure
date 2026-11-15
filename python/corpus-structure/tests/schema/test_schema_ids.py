"""Independent public JSON Schema identity expectations."""

import json

from jsonschema import Draft202012Validator

from corpus_structure.core import schemas
from corpus_structure.core._model import revision


def test_every_committed_schema_carries_its_id_and_is_valid() -> None:
    files = sorted(schemas.DIRECTORY.glob("*.json"))
    assert {p.stem for p in files} == set(schemas.SCHEMAS())
    ids = set()
    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(document)
        assert list(document)[:2] == ["$schema", "$id"], path.name
        assert document["$id"] == schemas.schema_id(path.stem), path.name
        assert document["$id"].split("/")[-2] == revision.CONTENT_HASH[:12]
        ids.add(document["$id"])
    assert len(ids) == len(files)


def test_a_schema_version_adds_its_segment() -> None:
    assert schemas.schema_id("batch.stored", "a" * 64, "b" * 64) == (
        f"{schemas.ID_ROOT}/{'a' * 12}/{'b' * 12}/batch.stored.json"
    )
