"""Portable characterization pins, independent source text and mutation refusals."""

import base64
import json
from hashlib import sha256

import pytest

from corpus_structure.semantic.characterization import (
    occurrence_id,
    validate_layer,
    validate_view,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.characterization_replay import (
    CharacterizationReviewSelection,
    _Budget,
    _Sink,
    inspect_characterization_review,
)
from corpus_structure.serve.review_bundle import inspect_review_bundle, verify_review_bundle
from semantic.characterization_replay_support import (
    bundle as bundle,
)
from semantic.characterization_replay_support import (
    construction_release_inputs as construction_release_inputs,
)
from semantic.characterization_replay_support import (
    contract_data as contract_data,
)
from semantic.characterization_replay_support import (
    prepared as prepared,
)


@pytest.mark.parametrize("with_layer", [False, True])
def test_existing_review_dispatch_replays_source_and_exact_layer_pins(
    tmp_path, prepared, with_layer
):
    root = tmp_path / "review"
    manifest = bundle(root, prepared, with_layer=with_layer)
    assert verify_review_bundle(root) == manifest
    assert inspect_review_bundle(root)["layers"] == int(with_layer)


@pytest.mark.parametrize(
    "member,field",
    [
        ("layer-0.json", "terms"),
        ("base.json", "content"),
        ("base.json", "companions"),
        ("sources.json", "text"),
    ],
)
def test_resealed_transport_mutation_still_fails_exact_product_or_source_proof(
    tmp_path, prepared, member, field
):
    root = tmp_path / "review"
    manifest = bundle(root, prepared)
    body = json.loads((root / member).read_bytes())
    if field == "terms":
        body["terms"][0]["value"] = "not"
    elif field == "content":
        body["product"]["content"]["texts"][0]["text"] = "not"
    elif field == "companions":
        body["product"]["native_metadata"][0]["value"]["score"] = 0.0
    else:
        body[0]["text"] = "not"
    content = canonical_bytes(body)
    (root / member).write_bytes(content)
    manifest["files"][member].update(sha256=sha256(content).hexdigest(), bytes=len(content))
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    with pytest.raises(ValueError, match="differ"):
        verify_review_bundle(root)


def test_stream_budget_refuses_before_oversized_write():
    from io import BytesIO

    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.semantic.refusals import SemanticRefusal

    output = BytesIO()
    sink = _Sink(output, _Budget(3, OperationCancellation()))
    sink.write(b"abc")
    with pytest.raises(SemanticRefusal, match="budget"):
        sink.write(b"d")
    assert output.getvalue() == b"abc"


@pytest.mark.parametrize("view", ["terms", "coverage"])
def test_detached_inspection_uses_same_domain_projection(tmp_path, prepared, view):
    from corpus_structure.serve.characterization import CharacterizationRequest

    root = tmp_path / "review"
    manifest = bundle(root, prepared)
    selection = manifest["selection"]
    request = CharacterizationRequest(
        run_id=selection["run_id"],
        task_id=selection["task_id"],
        product_key=selection["product_key"],
        content_digest=selection["content_digest"],
        view=view,
    )
    response = inspect_characterization_review(root, request)
    assert response.standing == "private_analyses"
    if view == "coverage":
        assert list(response.items) == json.loads((root / "view.json").read_bytes())["coverage"]
        assert response.coverage_total == 1
        assert response.source_items == {}
        return
    assert response.model_dump(mode="json")["items"][0]["term"]["value"] == "all"
    assert response.model_dump(mode="json")["source_items"]["#/texts/0"]["text"] == "all"
    assert "#/body" in response.source_items


@pytest.mark.parametrize("case", ["metadata_envelope", "external_scalar"])
def test_resealed_exact_companion_capture_still_requires_native_identity(tmp_path, prepared, case):
    root = tmp_path / "review"
    manifest = bundle(root, prepared)
    rows = [json.loads(line) for line in (root / "companions.jsonl").read_bytes().splitlines()]
    if case == "metadata_envelope":
        rows[1]["body"]["pointer"] = "#/texts/999"
    else:
        raw = base64.b64decode(rows[1]["fields"][0]["content_base64"])
        rows[1]["fields"][0]["content_base64"] = base64.b64encode(
            raw.replace(b"-0.0", b"0.0")
        ).decode()
    content = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    (root / "companions.jsonl").write_bytes(content)
    manifest["files"]["companions.jsonl"].update(
        sha256=sha256(content).hexdigest(), bytes=len(content)
    )
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    with pytest.raises(ValueError, match="differs from exact base pin"):
        verify_review_bundle(root)


@pytest.mark.parametrize("field", ["schemas", "attachment_policies", "sources"])
def test_resealed_contract_cannot_replace_released_schema_or_policy(tmp_path, prepared, field):
    root = tmp_path / "review"
    manifest = bundle(root, prepared)
    contract = json.loads((root / "contracts.json").read_bytes())
    if field == "schemas":
        contract["schemas"]["AnnotationLayer"]["title"] = "Different meaning"
    elif field == "attachment_policies":
        contract["attachment_policies"]["released_construction"]["rules"] = {
            "unreleased": {"class_name": "AnnotationLayer"}
        }
    else:
        name = next(iter(contract["sources"]))
        contract["sources"][name] = base64.b64encode(b"name: substitution").decode()
    content = canonical_bytes(contract)
    (root / "contracts.json").write_bytes(content)
    manifest["files"]["contracts.json"].update(
        sha256=sha256(content).hexdigest(), bytes=len(content)
    )
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    with pytest.raises(ValueError, match="differ from release"):
        verify_review_bundle(root)


@pytest.mark.parametrize("field", ["native_pointer", "page"])
def test_new_pin_cannot_claim_wrong_pointer_or_page_on_authenticated_source(
    tmp_path, prepared, field
):
    root = tmp_path / "review"
    manifest = bundle(root, prepared)
    layer = json.loads((root / "layer-0.json").read_bytes())
    extent = layer["occurrences"][0]["extents"][0]
    extent[field] = "#/body" if field == "native_pointer" else 999
    layer["occurrences"][0]["local_id"] = occurrence_id(layer["base_document"], [extent])
    for term in layer["terms"]:
        term["occurrences"] = [layer["occurrences"][0]["local_id"]]
    layer_bytes = canonical_bytes(layer)
    pin = dict(
        task_id=8,
        product_key="characterization-layer:" + sha256(layer_bytes).hexdigest(),
        content_digest=sha256(layer_bytes).hexdigest(),
    )
    view = json.loads((root / "view.json").read_bytes())
    view["layers"] = [pin]
    view_bytes = canonical_bytes(view)
    view_digest = sha256(view_bytes).hexdigest()
    manifest["selection"].update(
        product_key="characterization-view:" + view_digest, content_digest=view_digest
    )
    manifest["layers"][0]["reference"] = pin
    base = json.loads((root / "base.json").read_bytes())
    base["binding"]["view"] = {
        key: manifest["selection"][key] for key in ("task_id", "product_key", "content_digest")
    }
    for name, content in [
        ("layer-0.json", layer_bytes),
        ("view.json", view_bytes),
        ("base.json", canonical_bytes(base)),
    ]:
        (root / name).write_bytes(content)
        manifest["files"][name].update(sha256=sha256(content).hexdigest(), bytes=len(content))
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    with pytest.raises(ValueError, match="differs from authenticated native"):
        verify_review_bundle(root)


@pytest.mark.parametrize("target", ["scope", "eligible", "examined", "unexamined"])
def test_successful_empty_or_partial_family_selectors_still_require_source_proof(
    tmp_path, prepared, target
):
    root = tmp_path / "review"
    manifest = bundle(root, prepared)
    layer = json.loads((root / "layer-0.json").read_bytes())
    layer["terms"] = []
    layer["occurrences"] = []
    coverage = layer["coverage"][0]
    coverage["outcome"] = "empty"
    if target == "scope":
        layer["source_scope"]["selectors"][0]["page"] = 999
    elif target == "unexamined":
        layer["outcome"] = "partial"
        coverage.update(
            outcome="partial",
            reason="not examined",
            unexamined=[dict(coverage["eligible"][0], page=999)],
        )
    else:
        # Empty success has matching eligible/examined scope; both receive the same
        # forged pointer/offset pairing, which remains structurally self-consistent.
        forged = dict(coverage["eligible"][0], native_pointer="#/body", start=0, end=3)
        coverage["eligible"] = [forged]
        coverage["examined"] = [forged]
    layer_bytes = canonical_bytes(layer)
    digest = sha256(layer_bytes).hexdigest()
    pin = dict(task_id=8, product_key="characterization-layer:" + digest, content_digest=digest)
    view = json.loads((root / "view.json").read_bytes())
    view.update(layers=[pin], coverage=layer["coverage"], source_scope=layer["source_scope"])
    view_bytes = canonical_bytes(view)
    view_digest = sha256(view_bytes).hexdigest()
    manifest["selection"].update(
        product_key="characterization-view:" + view_digest, content_digest=view_digest
    )
    manifest["layers"][0]["reference"] = pin
    base = json.loads((root / "base.json").read_bytes())
    base["binding"]["view"] = {
        key: manifest["selection"][key] for key in ("task_id", "product_key", "content_digest")
    }
    for name, content in [
        ("layer-0.json", layer_bytes),
        ("view.json", view_bytes),
        ("base.json", canonical_bytes(base)),
    ]:
        (root / name).write_bytes(content)
        manifest["files"][name].update(sha256=sha256(content).hexdigest(), bytes=len(content))
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    with pytest.raises(ValueError, match=r"selector .*differs from authenticated"):
        verify_review_bundle(root)


def cross_release_bundle(root, prepared):
    from copy import deepcopy

    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.characterization import LayerReport

    manifest = bundle(root, prepared, native_evidence=True)
    old_bytes = (root / "layer-0.json").read_bytes()
    old = LayerReport(old_bytes)
    old_pin = ProductReference(**manifest["layers"][0]["reference"])
    new_inputs = construction_release_inputs()
    newer = prepare_release(new_inputs)
    assert newer.release_id != prepared.release_id
    payload = deepcopy(old.payload)
    payload.update(
        release_id=newer.release_id,
        dependencies=[old_pin.values()],
        annotations=[],
        memberships=[],
        roles=[],
        terms=[],
    )
    payload["operation"].update(
        key="text.construction",
        grammar="replay:body-v1",
        produced_families=["construction"],
        required_layers=[old_pin.values()],
    )
    external = {"layer": old_pin.values(), "local_id": "native-token"}
    payload["terms"] = [
        dict(
            local_id="reading",
            family="construction",
            kind="predicate",
            vocabulary="toy",
            value="supported reading",
            status="interpreted",
            external_premises=[external],
            occurrences=[payload["occurrences"][0]["local_id"]],
        )
    ]
    payload["roles"] = [
        dict(
            local_id="body-role",
            family="construction",
            owner="reading",
            member="reading",
            role="body",
            scheme="toy",
            basis=dict(
                kind="released_construction",
                status="witnessed",
                rule_id="replay:body-v1",
                premises=["reading"],
                external_premises=[external],
            ),
        )
    ]
    for row in payload["coverage"]:
        row.update(family="construction", operation="text.construction")
    report = validate_layer(
        newer, payload, dependencies={old_pin: old}, releases={prepared.release_id: prepared}
    )
    new_pin = report.reference(10)
    layers = {old_pin: old, new_pin: report}
    view_payload = json.loads((root / "view.json").read_bytes())
    view_payload.update(
        release_id=newer.release_id,
        layers=[pin.values() for pin in layers],
        coverage=[*old.payload["coverage"], *report.payload["coverage"]],
    )
    view = validate_view(newer, view_payload, layers, releases={prepared.release_id: prepared})
    old_contract = json.loads((root / "contracts.json").read_bytes())
    new_contract = contract_data(newer, new_inputs)
    new_contract["layer_contracts"] = {prepared.release_id: old_contract}

    def store(name, content):
        (root / name).write_bytes(content)
        manifest["files"][name] = dict(
            path=name, sha256=sha256(content).hexdigest(), bytes=len(content)
        )

    store("layer-1.json", report.content)
    store("view.json", view.content)
    store("contracts.json", canonical_bytes(new_contract))
    manifest["layers"].append(dict(reference=new_pin.values(), path="layer-1.json"))
    manifest["selection"].update(view.reference(9).values())
    base = json.loads((root / "base.json").read_bytes())
    base["binding"]["view"] = view.reference(9).values()
    store("base.json", canonical_bytes(base))
    (root / "manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
    return manifest, old_bytes, old_pin, newer


def test_two_release_replay_consumes_native_evidence_without_rewriting_original_pin(
    tmp_path, prepared
):
    root = tmp_path / "review"
    manifest, original, pin, newer = cross_release_bundle(root, prepared)
    assert verify_review_bundle(root) == manifest
    assert (root / "layer-0.json").read_bytes() == original
    assert manifest["layers"][0]["reference"] == pin.values()
    view = json.loads((root / "view.json").read_bytes())
    assert view["release_id"] == newer.release_id
    assert json.loads(original)["release_id"] == prepared.release_id
    assert json.loads((root / "layer-1.json").read_bytes())["dependencies"] == [pin.values()]


@pytest.mark.parametrize(
    "case", ["foreign_schema", "foreign_policy", "missing_contract", "unsupported_layer"]
)
def test_two_release_replay_refuses_resealed_foreign_or_unsupported_contract(
    tmp_path, prepared, case
):
    root = tmp_path / "review"
    manifest, _original, pin, _newer = cross_release_bundle(root, prepared)
    contract = json.loads((root / "contracts.json").read_bytes())
    if case == "foreign_schema":
        contract["layer_contracts"][prepared.release_id]["schemas"]["AnnotationLayer"]["title"] = (
            "Substitution"
        )
    elif case == "foreign_policy":
        contract["layer_contracts"][prepared.release_id]["attachment_policies"][
            "released_construction"
        ]["rules"] = {"invented": {"class_name": "AnnotationLayer"}}
    elif case == "missing_contract":
        contract["layer_contracts"].clear()
    else:
        layer = json.loads((root / "layer-0.json").read_bytes())
        layer["format"] = "characterization-layer-v2"
        from corpus_structure.semantic.characterization import LayerReport

        report = LayerReport(canonical_bytes(layer))
        changed_pin = report.reference(pin.task_id)
        manifest["layers"][0]["reference"] = changed_pin.values()
        _reseal_member(root, manifest, "layer-0.json", report.content)
        view = json.loads((root / "view.json").read_bytes())
        view["layers"][0] = changed_pin.values()
        view_bytes = canonical_bytes(view)
        digest = sha256(view_bytes).hexdigest()
        new_view = dict(
            task_id=9, product_key="characterization-view:" + digest, content_digest=digest
        )
        manifest["selection"].update(new_view)
        _reseal_member(root, manifest, "view.json", view_bytes)
        base = json.loads((root / "base.json").read_bytes())
        base["binding"]["view"] = new_view
        _reseal_member(root, manifest, "base.json", canonical_bytes(base))
    _reseal_member(root, manifest, "contracts.json", canonical_bytes(contract))
    (root / "manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
    expected = {
        "foreign_schema": "schemas or attachment policies differ from released inputs",
        "foreign_policy": "schemas or attachment policies differ from released inputs",
        "missing_contract": "participating release contract closure differs",
        "unsupported_layer": "unsupported characterization layer contract",
    }[case]
    with pytest.raises(ValueError, match=expected):
        verify_review_bundle(root)


def _reseal_member(root, manifest, name, content):
    (root / name).write_bytes(content)
    manifest["files"][name] = dict(
        path=name, sha256=sha256(content).hexdigest(), bytes=len(content)
    )


def test_detached_layer_mapping_hydrates_one_exact_report_without_retaining_it(monkeypatch):
    import weakref

    from corpus_structure.semantic.characterization import LayerReport
    from corpus_structure.serve.characterization_replay import _LayerFiles

    class TrackedReport(LayerReport):
        pass

    monkeypatch.setattr("corpus_structure.serve.characterization_replay.LayerReport", TrackedReport)

    reports = [LayerReport(canonical_bytes({"operation": index})) for index in range(3)]
    members = [
        dict(reference=report.reference(index + 1).values(), path=f"layer-{index}.json")
        for index, report in enumerate(reports)
    ]
    content = {
        member["path"]: report.content for member, report in zip(members, reports, strict=True)
    }
    loaded = []

    def load(name):
        loaded.append(name)
        return content[name]

    layers = _LayerFiles(members, load)
    pins = list(layers)
    assert pins[0] in layers
    assert loaded == []
    report = layers[pins[1]]
    reference = weakref.ref(report)
    assert loaded == ["layer-1.json"]
    del report
    assert reference() is None
    content["layer-1.json"] = content["layer-2.json"]
    with pytest.raises(ValueError, match="exact published pin"):
        layers[pins[1]]


def test_capture_writes_and_releases_sealed_layers_before_next_read(
    tmp_path, prepared, monkeypatch
):
    import weakref
    from unittest.mock import Mock

    import corpus_structure.semantic.characterization as characterization
    import corpus_structure.semantic.characterization_store as store
    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.serve.characterization_replay import capture_characterization_review

    original = tmp_path / "original"
    bundle(original, prepared)
    content = (original / "layer-0.json").read_bytes()
    report = characterization.LayerReport(content)
    pins = [report.reference(task) for task in (8, 10, 12)]
    payload = json.loads((original / "view.json").read_bytes())
    payload["layers"] = [pin.values() for pin in pins]
    view = characterization.EnrichedDocumentView(canonical_bytes(payload))
    selection = CharacterizationReviewSelection(run_id=3, **view.reference(9).values())
    metadata = {
        name: value
        for name, value in report.payload.items()
        if name not in {"occurrences", "annotations", "memberships", "roles", "terms", "choices"}
    }
    read_reports = []

    class TrackedReport(characterization.LayerReport):
        pass

    def read_layer(conn, pin, **kwargs):
        assert all(reference() is None for reference in read_reports)
        value = TrackedReport(content)
        read_reports.append(weakref.ref(value))
        return value

    monkeypatch.setattr(store, "read_view", Mock(return_value=view))
    monkeypatch.setattr(store, "read_layer", read_layer)
    monkeypatch.setattr(
        store,
        "read_layer_manifest",
        lambda conn, pin, **kw: characterization._published_layer_manifest(pin, metadata),
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.releases.open_release", Mock(return_value=prepared)
    )
    monkeypatch.setattr(
        "corpus_structure.serve.characterization_replay._capture_characterization_contract",
        Mock(return_value={}),
    )
    validate = characterization.validate_published_view

    def stop_after_composition(*args):
        validate(*args)
        raise RuntimeError("composition checked")

    monkeypatch.setattr(characterization, "validate_published_view", stop_after_composition)
    root = tmp_path / "capture"
    root.mkdir()
    with pytest.raises(RuntimeError, match="composition checked"):
        capture_characterization_review(Mock(), selection, root, OperationCancellation())
    assert len(read_reports) == 3
    assert all(reference() is None for reference in read_reports)
    assert [(root / f"layer-{index}.json").read_bytes() for index in range(3)] == [content] * 3


@pytest.mark.parametrize("case", ["external_premise", "external_choice", "choice_cycle"])
def test_detached_lazy_validation_refuses_resealed_correlated_graph(tmp_path, prepared, case):
    from corpus_structure.semantic.characterization import LayerReport

    root = tmp_path / "review"
    manifest, _, _, _ = cross_release_bundle(root, prepared)
    body = json.loads((root / "layer-1.json").read_bytes())
    if case == "external_premise":
        body["terms"][0]["external_premises"][0]["local_id"] = "absent"
        expected = "dangling external premise"
    elif case == "external_choice":
        body["terms"][0]["required_external_choices"] = body["terms"][0]["external_premises"]
        expected = "required external choice is not a choice member"
    else:
        body["choices"] = [
            dict(
                local_id="site",
                family="construction",
                compatibility="unknown",
                members=[dict(local_id="choice", root="reading", required_choices=["choice"])],
            )
        ]
        expected = "choice dependency structural cycle"
    report = LayerReport(canonical_bytes(body))
    pin = report.reference(10)
    manifest["layers"][1]["reference"] = pin.values()
    _reseal_member(root, manifest, "layer-1.json", report.content)
    view = json.loads((root / "view.json").read_bytes())
    view["layers"][1] = pin.values()
    view_bytes = canonical_bytes(view)
    digest = sha256(view_bytes).hexdigest()
    view_pin = dict(task_id=9, product_key="characterization-view:" + digest, content_digest=digest)
    manifest["selection"].update(view_pin)
    _reseal_member(root, manifest, "view.json", view_bytes)
    base = json.loads((root / "base.json").read_bytes())
    base["binding"]["view"] = view_pin
    _reseal_member(root, manifest, "base.json", canonical_bytes(base))
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    with pytest.raises(ValueError, match=expected):
        verify_review_bundle(root)
