"""Portable characterization pins, independent source text and mutation refusals."""

import base64
import json
import zlib
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.ingest.pdf_hierarchy import section_text_recipe, section_view_key
from corpus_structure.semantic.characterization import (
    attachment_policies,
    occurrence_id,
    validate_layer,
    validate_view,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_identity import (
    PROTOCOL,
    IdentityFold,
    ScalarDescriptor,
    byte_root,
    record_frame,
)
from corpus_structure.semantic.pdf_records import (
    iter_native_records,
    native_record_identity_fields,
    native_schema_bytes,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.characterization_replay import (
    FORMAT,
    CharacterizationReviewSelection,
    _Budget,
    _Sink,
    inspect_characterization_review,
)
from corpus_structure.serve.review_bundle import inspect_review_bundle, verify_review_bundle
from corpus_structure.serve.review_source_projection import SECTION_TEXT_INPUT


@pytest.fixture(scope="module")
def prepared():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.characterization import characterization_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    return prepare_release(characterization_inputs(bundle))


def bundle(root, prepared, *, with_layer=True, native_evidence=False) -> dict[str, Any]:
    root.mkdir()
    document: dict[str, Any] = {
        "name": "Retained source",
        "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]},
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "text",
                "text": "all",
                "orig": "all",
                "parent": {"$ref": "#/body"},
            }
        ],
    }
    document["pages"] = {"1": {"page_no": 1, "size": {"width": 100.0, "height": 100.0}}}
    document["texts"][0]["prov"] = [
        {
            "page_no": 1,
            "charspan": [0, 3],
            "bbox": {"l": 0.0, "t": 0.0, "r": 20.0, "b": 5.0, "coord_origin": "TOPLEFT"},
        }
    ]
    original, producer_release = "a" * 64, "release:producer"
    descriptors = {}

    def write(stream, profile, chunks):
        size, digest = byte_root(chunks)
        value = ScalarDescriptor(
            b"y" if profile == "pdf-record-native-json-v1" else profile[-1:].encode(), size, digest
        )
        descriptors[stream] = value
        return value

    rows = list(
        iter_native_records(
            document,
            product_id="base",
            revision_id="base",
            release_id=producer_release,
            source_digest=original,
            record_id_for=lambda address, kind: sha256(
                (original + "\0" + address + "\0" + kind).encode()
            ).hexdigest(),
            write_scalar=write,
        )
    )
    schema = native_schema_bytes()
    schema_digest = sha256(schema).hexdigest()
    identities = {}
    inventory, targets = [], []
    for row in rows:
        identity = native_record_identity_fields(row, scalar_descriptor=descriptors.__getitem__)
        if identity:
            family, key, fields = identity
            identities[(family, key)] = fields
        if row.kind == "native":
            scalars = json.loads(row.values["scalars_json"])
            structure = json.loads(row.values["structure_json"])["fields"]
            for name, value in structure.items():
                if value["kind"] == "object":
                    targets.append((row.values["record_id"], name, -1, value["target"]))
            if "self_ref" in scalars:
                pointer = scalars["self_ref"]
                node = document["body"] if pointer == "#/body" else document["texts"][0]
                inventory.append(
                    dict(
                        pointer=pointer,
                        record_id=row.values["record_id"],
                        label=node.get("label", "unspecified"),
                        content_layer="body",
                        parent_pointer=node.get("parent", {}).get("$ref"),
                        children=node.get("children"),
                    )
                )
        if (
            row.kind == "membership"
            and row.values["value_kind"] == "record"
            and "member_key" not in row.values
            and "member_key_stream_id" not in row.values
        ):
            targets.append(
                (
                    row.values["parent_id"],
                    row.values["field_name"],
                    row.values["ordinal"],
                    row.values["record_id"],
                )
            )
    metadata_value = {"score": -0.0, "small": 1e-7, "text": "retained"}
    metadata_bytes = canonical_bytes(metadata_value)
    metadata_length, metadata_root = byte_root((metadata_bytes,))
    metadata_body = {"kind": "runtime_report", "ordinal": 0, "pointer": "#/body"}
    input_body = {"role": "structural", "configuration": "cfg"}
    identities[("companion/input", "0")] = (
        ("body", '{"configuration":"cfg","role":"structural"}'),
        ("ordinal", 0),
    )
    identities[("companion/native_metadata", "runtime_report:0")] = (
        ("body", '{"kind":"runtime_report","ordinal":0,"pointer":"#/body"}'),
        ("ordinal", 0),
        ("value", ScalarDescriptor(b"y", metadata_length, metadata_root)),
    )
    companions = [
        dict(family="input", local_id="0", ordinal=0, body=input_body, fields=[]),
        dict(
            family="native_metadata",
            local_id="runtime_report:0",
            ordinal=0,
            body=metadata_body,
            fields=[
                dict(
                    name="value",
                    profile="pdf-companion-json-field-v1",
                    kind="y",
                    content_base64=base64.b64encode(metadata_bytes).decode(),
                )
            ],
        ),
    ]
    identities[("@context", "@context")] = (
        ("protocol", PROTOCOL),
        ("release", producer_release),
        ("source", original),
    )
    frames = [
        record_frame(schema_digest, family, key, fields)
        for (family, key), fields in sorted(identities.items())
    ]
    fold = IdentityFold("records")
    for frame in frames:
        fold.add(frame)
    base = ProductReference(7, "native", fold.digest().hex())
    proofs = [
        dict(
            product=base.values(),
            native_schema=schema_digest,
            original=original,
            producer_release=producer_release,
        ),
        dict(frames=base64.b64encode(zlib.compress(b"".join(frames))).decode()),
        dict(targets=targets),
        dict(items=inventory),
    ]
    policy = (
        b'{"content_layers":["body"],"readable_formula_originals":[],'
        b'"recipe":"native-section-text-v10"}'
    )
    policy_manifest = canonical_bytes(
        {"dependencies": [[SECTION_TEXT_INPUT, sha256(policy).hexdigest()]]}
    )
    source_release = "release:" + sha256(policy_manifest).hexdigest()
    recipe = section_text_recipe(base, analysis_eligible=True, policy=policy)
    context = dict(
        items=[document["body"], document["texts"][0]],
        ancestors=[],
        pieces=[
            dict(item_ref="#/texts/0", start=0, end=3, kind="native_text", source_field="text")
        ],
        health={"state": "unknown"},
    )
    projection = {
        "text": "all",
        "pieces": context["pieces"],
        "items": ["#/body", "#/texts/0"],
        "ancestors": [],
        "health": context["health"],
    }
    projection_digest = sha256(canonical_bytes(projection)).hexdigest()
    source_pin = dict(
        source_view_id=11,
        key=section_view_key(source_release, base, "#/body", "direct", True, recipe),
        base_document=base.values(),
        section_pointer="#/body",
        membership="direct",
        projection_digest=projection_digest,
        recipe_digest=sha256(recipe).hexdigest(),
    )
    scope = dict(
        source_view_ids=[11],
        source_views=[source_pin],
        profile="bounded",
        selectors=[{"projection": projection_digest}],
    )
    layers = {}
    if with_layer:
        extents = [
            dict(
                projection=projection_digest,
                source_view_id=11,
                native_pointer="#/texts/0",
                page=1,
                start=0,
                end=3,
                text="all",
                synthetic=False,
            )
        ]
        report = validate_layer(
            prepared,
            dict(
                format="characterization-layer-v1",
                base_document=base.values(),
                release_id=prepared.release_id,
                operation=dict(
                    key="text.test",
                    version="1",
                    runtime="test",
                    model="none",
                    grammar="none",
                    configuration="cfg",
                    input="input",
                    context="section",
                    produced_families=["scope"],
                    outcomes=["complete", "partial", "failed"],
                    result_determinants=["input"],
                ),
                source_scope=scope,
                outcome="complete",
                occurrences=[dict(local_id=occurrence_id(base, extents), extents=extents)],
                annotations=[
                    dict(
                        local_id="native-token",
                        family="scope",
                        kind="token",
                        vocabulary="toy-native",
                        native_scheme="retained-parser-v1",
                        native_label="DT",
                        status="native_evidence",
                        occurrences=[occurrence_id(base, extents)],
                    )
                ]
                if native_evidence
                else [],
                terms=[
                    dict(
                        local_id="all",
                        family="scope",
                        kind="operator",
                        vocabulary="logic",
                        value="all",
                        status="interpreted",
                        occurrences=[occurrence_id(base, extents)],
                    )
                ],
                coverage=[
                    dict(
                        family="scope",
                        operation="text.test",
                        eligible=scope["selectors"],
                        examined=scope["selectors"],
                        availability="available",
                        outcome="complete",
                        profile="bounded",
                    )
                ],
            ),
        )
        layers[report.reference(8)] = report
    view = validate_view(
        prepared,
        dict(
            format="enriched-document-view-v1",
            base_document=base.values(),
            release_id=prepared.release_id,
            source_scope=scope,
            layers=[p.values() for p in layers],
            profile="selected_layers" if layers else "source_only",
            coverage=[row for layer in layers.values() for row in layer.payload["coverage"]],
        ),
        layers,
    )
    selection = CharacterizationReviewSelection(run_id=3, **view.reference(9).values())
    files = {}

    def store(name, content):
        (root / name).write_bytes(content)
        files[name] = dict(path=name, sha256=sha256(content).hexdigest(), bytes=len(content))

    store("view.json", view.content)
    layer_members = []
    for i, (pin, layer) in enumerate(layers.items()):
        name = f"layer-{i}.json"
        store(name, layer.content)
        layer_members.append(dict(reference=pin.values(), path=name))
    policies = attachment_policies(prepared)
    names = {"AnnotationLayer", "EnrichedDocumentView"} | {
        p["class_name"] for p in policies.values()
    }
    names.update(
        rule["class_name"]
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    )
    from corpus_structure.semantic import SourceArtifact, SourceBundle
    from corpus_structure.semantic.characterization import characterization_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release_inputs = characterization_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    store(
        "contracts.json",
        canonical_bytes(
            dict(
                release_id=prepared.release_id,
                manifest_base64=base64.b64encode(prepared.manifest).decode(),
                schemas={name: prepared.json_schema(name) for name in names},
                attachment_policies=policies,
                sources={
                    source.name: base64.b64encode(source.content).decode()
                    for source in release_inputs.sources
                },
                dependencies={},
            )
        ),
    )
    store("native-schema.json", schema)
    store("companions.jsonl", b"".join(canonical_bytes(row) + b"\n" for row in companions))
    store("payload-schemas.json", b"{}")
    store(
        "base.json",
        canonical_bytes(
            dict(
                export_profile="pdf-complete-record-export-v1",
                binding=dict(view=selection.reference().values(), base_document=base.values()),
                product=dict(
                    product_key=base.product_key,
                    logical_digest=base.content_digest,
                    content=document,
                    inputs=[input_body],
                    native_metadata=[dict(kind="runtime_report", ordinal=0, value=metadata_value)],
                ),
            )
        ),
    )
    store("source-proofs.jsonl", b"".join(canonical_bytes(row) + b"\n" for row in proofs))
    ref = dict(
        id=11,
        document_id=17,
        key=source_pin["key"],
        native_product=base.values(),
        section_pointer="#/body",
        membership="direct",
        projection_digest=projection_digest,
        recipe_digest=source_pin["recipe_digest"],
        analysis_eligible=True,
    )
    store(
        "sources.json",
        canonical_bytes(
            [
                dict(
                    source_view_id=11,
                    ref=ref,
                    text="all",
                    context=context,
                    consumer_release=source_release,
                )
            ]
        ),
    )
    store(
        "source-contracts.json",
        canonical_bytes(
            {
                source_release: dict(
                    release_id=source_release,
                    section_text_policy=dict(
                        manifest_base64=base64.b64encode(policy_manifest).decode(),
                        input_base64=base64.b64encode(policy).decode(),
                    ),
                )
            }
        ),
    )
    manifest = dict(
        format=FORMAT,
        selection=selection.model_dump(mode="json"),
        view="view.json",
        layers=layer_members,
        files=files,
        original_source_completeness="complete_native_document_and_companions",
        completeness="exact_view_closure",
        standing="private_analyses",
    )
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    return manifest


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


def test_detached_inspection_uses_same_domain_projection(tmp_path, prepared):
    from corpus_structure.serve.characterization import CharacterizationRequest

    root = tmp_path / "review"
    manifest = bundle(root, prepared)
    selection = manifest["selection"]
    request = CharacterizationRequest(
        run_id=selection["run_id"],
        task_id=selection["task_id"],
        product_key=selection["product_key"],
        content_digest=selection["content_digest"],
        view="terms",
    )
    response = inspect_characterization_review(root, request)
    assert response.model_dump(mode="json")["items"][0]["term"]["value"] == "all"
    assert response.standing == "private_analyses"
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


def construction_release_inputs():
    """A real added witnessed-rule declaration, not a relabelled release identifier."""
    import yaml

    from corpus_structure.semantic import SourceArtifact, SourceBundle
    from corpus_structure.semantic.characterization import characterization_inputs

    model_root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = yaml.safe_load((model_root / "characterization.yaml").read_bytes())
    model["classes"]["ReplayConstructionBasis"] = {
        "is_a": "CharacterizationConstructionBasis",
        "attributes": {
            "rule_id": {"required": True, "equals_string": "replay:body-v1"},
            "premises": {
                "range": "string",
                "multivalued": True,
                "required": True,
                "minimum_cardinality": 1,
            },
        },
    }
    return characterization_inputs(
        SourceBundle("core", (SourceArtifact("core", (model_root / "core.yaml").read_bytes()),)),
        model_content=yaml.safe_dump(model).encode(),
    )


def contract_data(prepared, sources):
    policies = attachment_policies(prepared)
    names = {"AnnotationLayer", "EnrichedDocumentView"} | {
        row["class_name"] for row in policies.values()
    }
    names.update(
        rule["class_name"]
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    )
    return dict(
        release_id=prepared.release_id,
        manifest_base64=base64.b64encode(prepared.manifest).decode(),
        schemas={name: prepared.json_schema(name) for name in names},
        attachment_policies=policies,
        sources={
            source.name: base64.b64encode(source.content).decode() for source in sources.sources
        },
        dependencies={},
    )


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
