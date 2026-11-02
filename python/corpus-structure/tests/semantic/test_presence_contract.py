"""Official presence and collection cardinality remain separate at the shared boundary."""

import json

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import _products
from corpus_structure.semantic.types import (
    PreparationError,
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
)


def presence_bundle(presence="PRESENT", *, scope="shape"):
    source = {
        "id": "https://example.org/presence",
        "name": "presence",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "types": {"string": {"base": "str", "uri": "xsd:string"}},
        "classes": {
            "Report": {
                "attributes": {
                    "events": {
                        "range": "string",
                        "multivalued": True,
                        "required": False,
                        "minimum_cardinality": 0,
                        "value_presence": presence,
                        "annotations": {"cs:constraint_scope": scope},
                    },
                    "legacy": {
                        "range": "string",
                        "multivalued": True,
                        "required": True,
                        "minimum_cardinality": 0,
                    },
                }
            }
        },
    }
    return SourceBundle("presence", (SourceArtifact("presence", yaml.safe_dump(source).encode()),))


def test_present_empty_and_nonempty_arrays_preserve_presence_without_minimum_one():
    prepared = prepare_release(presence_bundle())
    fields = prepared.index.properties_by_class["Report"]
    assert fields["events"].required and fields["events"].minimum_cardinality == 0
    assert fields["legacy"].required and fields["legacy"].minimum_cardinality == 1
    for events in ([], ["first", "second"]):
        value = prepared.validate_json("Report", json.dumps({"events": events, "legacy": ["ok"]}))
        assert value.model_fields_set == {"events", "legacy"}
        assert value.model_dump(mode="json", exclude_unset=True) == {
            "events": events,
            "legacy": ["ok"],
        }
    schema = prepared.json_schema("Report")
    required, properties = schema["required"], schema["properties"]
    assert isinstance(required, list) and isinstance(properties, dict)
    events, legacy = properties["events"], properties["legacy"]
    assert isinstance(events, dict) and isinstance(legacy, dict)
    assert set(required) == {"events", "legacy"}
    assert events["minItems"] == 0
    assert legacy["minItems"] == 1


@pytest.mark.parametrize(
    "body", [{"legacy": ["ok"]}, {"events": None, "legacy": ["ok"]}, {"events": [], "legacy": []}]
)
def test_missing_null_and_legacy_empty_remain_distinct_refusals(body):
    with pytest.raises(ValidationError):
        prepare_release(presence_bundle()).validate_json("Report", json.dumps(body))


@pytest.mark.parametrize(
    ("presence", "scope"),
    [("ABSENT", "shape"), ("UNCOMMITTED", "shape"), ("PRESENT", "accepted_value")],
)
def test_unimplemented_presence_profiles_are_explicit_refusals(presence, scope):
    with pytest.raises(PreparationError) as invalid:
        prepare_release(presence_bundle(presence, scope=scope))
    assert invalid.value.diagnostics[0].code == "value_presence"


def test_presence_archive_uses_existing_normalized_abi_without_current_compilation(monkeypatch):
    bundle = presence_bundle()
    prepared = prepare_release(bundle)
    from corpus_structure.semantic import prepare

    def unavailable(*args, **kwargs):
        raise AssertionError("archive read cannot invoke current preparation")

    monkeypatch.setattr(prepare, "prepare_release", unavailable)
    archived = reconstruct_release(
        json.loads(canonical_bytes(_products(prepared))),
        prepared.manifest,
        bundle,
        PreparationProfile(),
        prepared.artifacts,
    )
    value = archived.validate_json("Report", '{"events":[],"legacy":["kept"]}')
    assert value.model_dump(mode="json") == {"events": [], "legacy": ["kept"]}
    with pytest.raises(ValidationError):
        archived.validate_json("Report", '{"legacy":["kept"]}')
