"""Portable exact enriched-document closure through the shared review export owner."""

from __future__ import annotations

import base64
import json
import os
from contextlib import closing
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO, Literal, cast

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.semantic.characterization import (
    EnrichedDocumentView,
    LayerReport,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.refusals import SemanticRefusal

FORMAT = "enriched-document-review-v1"


class CharacterizationReviewSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    format: Literal["enriched-document-review-v1"] = FORMAT
    run_id: int = Field(strict=True, gt=0)
    task_id: int = Field(strict=True, gt=0)
    product_key: str = Field(min_length=1)
    content_digest: str = Field(pattern="^[0-9a-f]{64}$")
    max_bytes: int = Field(default=134_217_728, strict=True, gt=0)
    max_source_rows: int = Field(default=100_000, strict=True, gt=0)

    def reference(self):
        return ProductReference(self.task_id, self.product_key, self.content_digest)


class _Budget:
    def __init__(self, limit, cancellation):
        self.remaining, self.cancellation = limit, cancellation

    def write(self, sink, content):
        self.cancellation.check_active()
        if len(content) > self.remaining:
            raise SemanticRefusal("enriched-document review exceeds total byte budget")
        self.remaining -= len(content)
        return sink.write(content)


class _Sink:
    def __init__(self, sink, budget):
        self.sink, self.budget = sink, budget

    def write(self, content):
        return self.budget.write(self.sink, content)


def capture_characterization_review(conn, selection, root, cancellation):
    """Capture immutable products under the caller's existing authorized read snapshot."""
    from corpus_structure.semantic.characterization import validate_view
    from corpus_structure.semantic.characterization_store import read_layer, read_view
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.source_views import load_source_view

    from .native_source import NativeSourceRequest, inspect_native_source
    from .review_bundle import _contract_row
    from .review_source_projection import capture_source_proof

    budget = _Budget(selection.max_bytes, cancellation)
    files = {}

    def store(name, content):
        with (root / name).open("xb") as sink:
            budget.write(sink, content)
        files[name] = {"path": name, "sha256": sha256(content).hexdigest(), "bytes": len(content)}
        return name

    view = read_view(conn, selection.reference(), run_id=selection.run_id)
    prepared = open_release(conn, view.payload["release_id"])
    layers = {}
    for value in view.payload.get("layers", ()):
        pin = ProductReference(**value)
        layers[pin] = read_layer(conn, pin, run_id=selection.run_id)
    store("view.json", view.content)
    layer_members = []
    for index, (pin, layer) in enumerate(layers.items()):
        layer_members.append(
            {"reference": pin.values(), "path": store(f"layer-{index}.json", layer.content)}
        )
    contracts = {prepared.release_id: _capture_characterization_contract(conn, prepared)}
    releases = {prepared.release_id: prepared}
    for layer in layers.values():
        release_id = layer.payload["release_id"]
        if release_id not in releases:
            releases[release_id] = open_release(conn, release_id)
            contracts[release_id] = _capture_characterization_contract(conn, releases[release_id])
    validate_view(prepared, view.payload, layers, releases=releases)
    contract = contracts.pop(prepared.release_id)
    contract["layer_contracts"] = contracts
    store("contracts.json", canonical_bytes(contract))

    base = view.base_document
    inspect_native_source(
        conn,
        NativeSourceRequest(
            run_id=selection.run_id,
            task_id=base.task_id,
            product_key=base.product_key,
            content_digest=base.content_digest,
            view="products",
            limit=1,
        ),
        cancellation=cancellation.postgresql,
    )
    native = published_record_reader(
        conn, base, projection_context=prepared, cancellation=cancellation.postgresql
    )
    if native is None:
        raise ValueError("enriched-document base has no published native record")
    artifacts = table("kb.source_artifact")
    native_schema = bytes(
        conn.execute(
            select(artifacts.c.content).where(
                artifacts.c.artifact_digest == native.revision["schema_digest"]
            )
        ).scalar_one()
    )
    if sha256(native_schema).hexdigest() != native.revision["schema_digest"]:
        raise ValueError("archived native schema digest differs")
    store("native-schema.json", native_schema)
    with (root / "base.json").open("xb") as sink:
        receipt = native.write_complete_json(
            cast(BinaryIO, _Sink(sink, budget)),
            binding={"view": selection.reference().values(), "base_document": base.values()},
        )
    files["base.json"] = {
        "path": "base.json",
        "sha256": receipt.serialization_sha256,
        "bytes": receipt.byte_length,
    }
    # Preserve the exact retained metadata envelopes and external scalar bytes as well
    # as the public native JSON codec, which intentionally strips locator columns.
    payload_schemas = {}
    with (root / "companions.jsonl").open("xb") as sink:
        for row in native.iter_rows("companion"):
            fields = []
            for field in row.get("_fields", ()):
                chunks, length = [], 0
                for chunk in native.scalar(field["stream_id"]):
                    length += len(chunk)
                    if length * 4 // 3 > budget.remaining:
                        raise SemanticRefusal(
                            "enriched-document review exceeds external field byte budget"
                        )
                    chunks.append(chunk)
                raw = b"".join(chunks)
                fields.append(
                    {
                        "name": field["field_name"],
                        "profile": field["encoding_profile"],
                        "kind": field["scalar_kind"],
                        "content_base64": base64.b64encode(raw).decode(),
                    }
                )
                from corpus_structure.semantic.pdf_payloads import PROFILE, prepare_payload_family

                if field["encoding_profile"] == PROFILE:
                    family = prepare_payload_family(native._payload_context())
                    payload_schemas[family.schema_digest] = family.json_schema
            budget.write(
                sink,
                canonical_bytes(
                    {
                        "family": row["family"],
                        "local_id": row["local_id"],
                        "ordinal": row["ordinal"],
                        "body": row["body"],
                        "fields": fields,
                    }
                )
                + b"\n",
            )
    companion_content = (root / "companions.jsonl").read_bytes()
    files["companions.jsonl"] = {
        "path": "companions.jsonl",
        "sha256": sha256(companion_content).hexdigest(),
        "bytes": len(companion_content),
    }
    store("payload-schemas.json", canonical_bytes(payload_schemas))
    with (root / "source-proofs.jsonl").open("xb") as sink:
        for row in capture_source_proof(conn, base, prepared, cancellation):
            budget.write(sink, canonical_bytes(row) + b"\n")
    proof_content = (root / "source-proofs.jsonl").read_bytes()
    files["source-proofs.jsonl"] = {
        "path": "source-proofs.jsonl",
        "sha256": sha256(proof_content).hexdigest(),
        "bytes": len(proof_content),
    }
    source_rows, contracts = [], {}
    scope = view.payload["source_scope"]
    if len(scope["source_view_ids"]) > selection.max_source_rows:
        raise SemanticRefusal("enriched-document review exceeds source row budget")
    for identity in scope["source_view_ids"]:
        source = load_source_view(conn, identity, analysis=False)
        if source.ref.native_product != base:
            raise ValueError("enriched-document source belongs to another base document")
        views = table("kb.source_view")
        release = conn.execute(
            select(views.c.release_id).where(views.c.id == identity)
        ).scalar_one()
        if release not in contracts:
            contracts[release] = _contract_row(conn, open_release(conn, release))
        source_rows.append(
            {
                "source_view_id": identity,
                "ref": asdict(source.ref),
                "text": source.text,
                "context": source.context(),
                "consumer_release": release,
            }
        )
    store("sources.json", canonical_bytes(source_rows))
    store("source-contracts.json", canonical_bytes(contracts))
    manifest = {
        "format": FORMAT,
        "selection": selection.model_dump(mode="json"),
        "view": "view.json",
        "layers": layer_members,
        "files": files,
        "original_source_completeness": "complete_native_document_and_companions",
        "completeness": "exact_view_closure",
        "standing": "private_analyses",
    }
    manifest_bytes = canonical_bytes(manifest) + b"\n"
    with (root / "manifest.json").open("xb") as sink:
        budget.write(sink, manifest_bytes)
    return manifest


def export_characterization_review(
    selection, destination, settings, *, cancellation=None, retain_binding=None
):
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    from .companion_export import _publish_directory

    cancellation = cancellation or OperationCancellation()
    cancellation.check_active()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".characterization-", dir=destination.parent) as temporary:
        root = Path(temporary) / "review"
        root.mkdir()
        with (
            open_runtime_engine(settings, "characterization-review", purpose="read") as engine,
            read_snapshot(engine, cancellation=cancellation.postgresql) as conn,
        ):
            from corpus_structure.semantic.characterization_store import read_view

            from .review_bundle import _acquired_database_identity

            acquired = read_view(conn, selection.reference(), run_id=selection.run_id)
            if retain_binding:
                retain_binding(
                    sha256(
                        canonical_bytes(
                            {
                                **_acquired_database_identity(conn),
                                "root": {
                                    "run_id": selection.run_id,
                                    "view": acquired.reference(selection.task_id).values(),
                                },
                            }
                        )
                    ).hexdigest()
                )
            manifest = capture_characterization_review(conn, selection, root, cancellation)
        verify_characterization_review(root)
        cancellation.check_active()
        _publish_directory(root, destination)
        return manifest


def verify_characterization_review(root: Path | int, *, manifest_digest=None):
    """Authenticate transport, exact pins, archived shapes, graph and source closure offline."""
    from .review_bundle import _member

    if not isinstance(root, int):
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            return verify_characterization_review(descriptor, manifest_digest=manifest_digest)
        finally:
            os.close(descriptor)
    with _member(root, "manifest.json", digest=manifest_digest) as stream:
        manifest = json.load(stream)
    if manifest.get("format") != FORMAT:
        raise ValueError("unsupported enriched-document review format")
    selection = CharacterizationReviewSelection.model_validate(manifest["selection"])
    files = manifest["files"]
    if set(os.listdir(root)) != {"manifest.json", *files}:
        raise ValueError("review package has undeclared or missing members")
    if sum(spec["bytes"] for spec in files.values()) > selection.max_bytes:
        raise ValueError("enriched-document review exceeds total byte budget")

    def content(name):
        spec = files[name]
        if spec["path"] != name:
            raise ValueError("review member name differs")
        with _member(root, name, digest=spec["sha256"], size=spec["bytes"]) as stream:
            return stream.read()

    # Verify even members that a selected weaker profile does not inspect.
    for name in files:
        content(name)
    view_bytes = content(manifest["view"])
    view = EnrichedDocumentView(view_bytes)
    if view.reference(selection.task_id) != selection.reference():
        raise ValueError("review view differs from exact selected pin")
    contract = json.loads(content("contracts.json"))
    release_manifest = base64.b64decode(contract["manifest_base64"], validate=True)
    if (
        "release:" + sha256(release_manifest).hexdigest() != contract["release_id"]
        or view.payload["release_id"] != contract["release_id"]
    ):
        raise ValueError("review characterization release differs")
    prepared = _authenticate_contract(contract, release_manifest)
    releases = {prepared.release_id: prepared}
    for release_id, foreign_contract in contract.get("layer_contracts", {}).items():
        if release_id == prepared.release_id or release_id != foreign_contract["release_id"]:
            raise ValueError("review foreign layer contract identity differs")
        releases[release_id] = _authenticate_contract(
            foreign_contract, base64.b64decode(foreign_contract["manifest_base64"], validate=True)
        )
    layers = {}
    for member in manifest["layers"]:
        pin = ProductReference(**member["reference"])
        report = LayerReport(content(member["path"]))
        if pin in layers or report.reference(pin.task_id) != pin:
            raise ValueError("review layer differs from exact published pin")
        layers[pin] = report
    needed = {
        view.payload["release_id"],
        *(layer.payload["release_id"] for layer in layers.values()),
    }
    if set(releases) != needed:
        raise ValueError("review participating release contract closure differs")
    from corpus_structure.semantic.characterization import validate_view

    validate_view(prepared, view.payload, layers, releases=releases)
    _verify_sources(root, manifest, selection, view, content)
    return manifest


def _verify_sources(root, manifest, selection, view, content):
    from .review_source_projection import (
        archived_projection_policy,
        load_source_proofs,
        open_proof_index,
        verify_source_projection,
    )

    sources = json.loads(content("sources.json"))
    if len(sources) > selection.max_source_rows:
        raise ValueError("review source row budget exceeded")
    contracts = json.loads(content("source-contracts.json"))
    base = json.loads(content("base.json"))
    if base.get("export_profile") != "pdf-complete-record-export-v1" or base["binding"] != {
        "view": selection.reference().values(),
        "base_document": view.base_document.values(),
    }:
        raise ValueError("review full native export binding differs")
    product = base["product"]
    if (
        product["logical_digest"] != view.base_document.content_digest
        or product["product_key"] != view.base_document.product_key
    ):
        raise ValueError("review native export pin differs")
    with (
        TemporaryDirectory(prefix="characterization-proof-") as temporary,
        closing(open_proof_index(Path(temporary) / "proof.sqlite")) as database,
    ):
        proofs = load_source_proofs(
            database, (json.loads(line) for line in content("source-proofs.jsonl").splitlines())
        )
        if set(proofs) != {view.base_document}:
            raise ValueError("review native proof closure differs")
        proof = proofs[view.base_document]
        _verify_full_native(product, proof, content("native-schema.json"))
        _verify_companions(
            product,
            proof,
            content("companions.jsonl"),
            json.loads(content("payload-schemas.json")),
            content("source-proofs.jsonl"),
        )
        expected = {p["source_view_id"]: p for p in view.payload["source_scope"]["source_views"]}
        actual = {}
        for source in sources:
            identity, ref = source["source_view_id"], source["ref"]
            pin = {
                "source_view_id": identity,
                "key": ref["key"],
                "base_document": ref["native_product"],
                "section_pointer": ref["section_pointer"],
                "membership": ref["membership"],
                "projection_digest": ref["projection_digest"],
                "recipe_digest": ref["recipe_digest"],
            }
            if identity in actual or pin != expected.get(identity):
                raise ValueError("review source scope differs from exact view pin")
            actual[identity] = pin
            projection = {
                "text": source["text"],
                "pieces": source["context"]["pieces"],
                "items": [i["self_ref"] for i in source["context"]["items"]],
                "ancestors": [i["self_ref"] for i in source["context"]["ancestors"]],
                "health": source["context"]["health"],
            }
            if sha256(canonical_bytes(projection)).hexdigest() != pin["projection_digest"]:
                raise ValueError("review source projection digest differs")
            verify_source_projection(
                source, archived_projection_policy(contracts[source["consumer_release"]]), proof
            )
        if actual != expected:
            raise ValueError("review source closure is incomplete")
        by_id = {source["source_view_id"]: source for source in sources}
        bodies = [
            view.payload,
            *(json.loads(content(layer["path"])) for layer in manifest["layers"]),
        ]
        for body in bodies:
            validate_captured_layer_sources(body, by_id)


def validate_captured_layer_sources(body, by_id):
    """Authenticate every source selector and literal occurrence against captured pieces."""
    selected_sources = [by_id[identity] for identity in body["source_scope"]["source_view_ids"]]
    for pin in body["source_scope"]["source_views"]:
        source = by_id[pin["source_view_id"]]
        ref = source["ref"]
        expected = dict(
            source_view_id=source["source_view_id"],
            key=ref["key"],
            base_document=ref["native_product"],
            section_pointer=ref["section_pointer"],
            membership=ref["membership"],
            projection_digest=ref["projection_digest"],
            recipe_digest=ref["recipe_digest"],
        )
        if pin != expected:
            raise ValueError("characterization source differs from exact captured view pin")
    selectors = list(body["source_scope"]["selectors"])
    for coverage in body.get("coverage", ()):
        for field in ("eligible", "examined", "unexamined"):
            selectors.extend(coverage.get(field, ()))
    for name in ("annotations", "memberships", "roles", "terms"):
        for node in body.get(name, ()):
            for context in (node.get("context", {}),):
                for field in ("focal", "examined", "gaps"):
                    selectors.extend(context.get(field, ()))
    for selector in selectors:
        _validate_captured_selector(selector, selected_sources)
    for occurrence in body.get("occurrences", ()):
        for extent in occurrence["extents"]:
            source = by_id[extent["source_view_id"]]
            native = {item["self_ref"]: item for item in source["context"]["items"]}
            pointer = extent.get("native_pointer")
            if pointer not in native:
                raise ValueError("annotation native pointer differs from retained source selection")
            if "page" in extent and extent["page"] not in {
                region["page_no"] for region in native[pointer].get("prov", ())
            }:
                raise ValueError("annotation page differs from authenticated native region")
            if (
                not extent["synthetic"]
                and "start" in extent
                and not any(
                    piece.get("kind") == "native_text"
                    and piece.get("item_ref") == pointer
                    and piece["start"] <= extent["start"] < extent["end"] <= piece["end"]
                    for piece in source["context"]["pieces"]
                )
            ):
                raise ValueError("annotation extent differs from authenticated native source piece")
            if "end" in extent and extent["end"] > len(source["text"]):
                raise ValueError("annotation extent exceeds retained source")
            if (
                "text" in extent
                and not extent["synthetic"]
                and source["text"][extent["start"] : extent["end"]] != extent["text"]
            ):
                raise ValueError("annotation literal differs from retained source")


def _verify_full_native(product, proof, native_schema):
    """Re-lower every native value and compare its exact identity-bearing record frame."""
    from corpus_structure.semantic.pdf_record_identity import (
        ScalarDescriptor,
        byte_root,
        record_frame,
    )
    from corpus_structure.semantic.pdf_records import (
        iter_native_records,
        native_record_identity_fields,
        prepare_native_schema_mapping,
    )

    if sha256(native_schema).hexdigest() != proof.schema:
        raise ValueError("review archived native schema differs from published pin")
    mapping = prepare_native_schema_mapping(native_schema, allow_archived_default=True)
    scalars = {}

    def scalar(stream_id, profile, chunks):
        kind = (
            b"y" if profile == "pdf-record-native-json-v1" else profile.rsplit(":", 1)[-1].encode()
        )
        length, digest = byte_root(chunks)
        descriptor = ScalarDescriptor(kind, length, digest)
        scalars[stream_id] = descriptor
        return descriptor

    addresses = _native_addresses(proof, product["content"])
    records = iter_native_records(
        product["content"],
        product_id="detached",
        revision_id="detached",
        release_id=proof.release,
        source_digest=proof.original,
        record_id_for=lambda address, kind: addresses[address],
        write_scalar=scalar,
        mapping=mapping,
    )
    seen = set()
    for row in records:
        identity = native_record_identity_fields(row, scalar_descriptor=scalars.__getitem__)
        if identity is None:
            continue
        family, key, fields = identity
        if family == "document":
            continue
        expected = proof.db.execute(
            "SELECT body FROM records WHERE product=? AND family=? AND key=?",
            (proof.index_key, family, key),
        ).fetchone()
        if expected is None or bytes(expected[0]) != record_frame(
            proof.schema, family, key, fields
        ):
            raise ValueError("review complete native value differs from exact published pin")
        seen.add((family, key))
    count = proof.db.execute(
        "SELECT count(*) FROM records WHERE product=?", (proof.index_key,)
    ).fetchone()[0]
    if len(seen) != count:
        raise ValueError("review complete native inventory differs from exact published pin")


def _postgres_json(value):
    """JSONB canonical rendering used by the existing native companion identity."""
    from decimal import Decimal

    if isinstance(value, dict):
        return (
            "{"
            + ",".join(
                json.dumps(key, ensure_ascii=False) + ":" + _postgres_json(value[key])
                for key in sorted(value)
            )
            + "}"
        )
    if isinstance(value, list):
        return "[" + ",".join(_postgres_json(item) for item in value) + "]"
    if isinstance(value, float):
        return format(Decimal(str(value)), "f")
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _verify_companions(product, proof, content, schemas, proof_content):
    """Bind every complete companion envelope and exact decoded scalar to the base pin."""
    from corpus_structure.semantic.pdf_payloads import FAMILY, PROFILE, prepare_payload_schema
    from corpus_structure.semantic.pdf_record_identity import (
        ScalarDescriptor,
        byte_root,
        structured_payload_scalar,
    )

    from .review_source_projection import _batch, _fields, _scalar_matches

    expected = {}
    document_frame = None
    for row in (json.loads(line) for line in proof_content.splitlines()):
        if "frames" not in row:
            continue
        for raw in _batch(row["frames"]):
            _, family, key, fields = _fields(raw)
            if family.startswith("companion/"):
                expected[(family.removeprefix("companion/"), key)] = fields
            elif family == "document":
                document_frame = fields
    if document_frame is None:
        raise ValueError("review full native proof lacks document header")
    root_id = _native_root(proof)
    for name, value in (("root_id", root_id), ("native_schema_digest", proof.schema)):
        if not _scalar_matches(document_frame[name], value):
            raise ValueError("review native document header differs")
    present = set()
    collections = {}
    for row in (json.loads(line) for line in content.splitlines()):
        key = row["family"], row["local_id"]
        fields = expected.get(key)
        if fields is None or key in present:
            raise ValueError("review complete companion inventory differs")
        present.add(key)
        family = row["family"]
        body = dict(row["body"])
        identity_body = dict(body)
        if family == "native_metadata":
            identity_body.pop("value", None)
            if body["kind"] == FAMILY:
                identity_body.pop("payload_codec", None)
                identity_body.pop("payload_schema_digest", None)
        elif family == "occurrence":
            identity_body.pop("text", None)
        # Relations restore external fields before the owned native identity fold.
        for field in row["fields"]:
            raw = base64.b64decode(field["content_base64"], validate=True)
            if field["profile"] == PROFILE:
                schema = schemas.get(body["payload_schema_digest"])
                if schema is None:
                    raise ValueError("review structured payload schema is missing")
                codec = prepare_payload_schema(schema)
                value = codec.decode(
                    raw,
                    schema_digest=body["payload_schema_digest"],
                    logical_digest=body["payload_logical_digest"],
                )
                descriptor = structured_payload_scalar(body["payload_logical_digest"])
            else:
                size, digest = byte_root((raw,))
                descriptor = ScalarDescriptor(field["kind"].encode(), size, digest)
                value = json.loads(raw) if field["kind"] == "y" else raw.decode()
            if field["name"] in body:
                raise ValueError("review companion has competing scalar values")
            body[field["name"]] = value
            if family == "relation":
                identity_body[field["name"]] = value
            elif fields.get(field["name"]) != descriptor.encode():
                raise ValueError("review external companion scalar differs from exact base pin")
        if not _scalar_matches(
            fields.get("body"), _postgres_json(identity_body)
        ) or not _scalar_matches(fields.get("ordinal"), row["ordinal"]):
            raise ValueError("review companion envelope differs from exact base pin")
        if family == "occurrence" and not any(f["name"] == "text" for f in row["fields"]):
            from corpus_structure.semantic.pdf_record_identity import ABSENT

            if not _scalar_matches(fields.get("text"), body.get("text", ABSENT)):
                raise ValueError("review occurrence text differs from exact base pin")
        if family == "native_metadata":
            from corpus_structure.semantic.pdf_record_reader import _METADATA_PROJECTIONS

            for name in _METADATA_PROJECTIONS:
                body.pop(name, None)
        collections.setdefault(family, []).append((row["ordinal"], row["local_id"], body))
    if present != set(expected):
        raise ValueError("review complete companion closure is missing")
    for family, name in (
        ("input", "inputs"),
        ("occurrence", "occurrences"),
        ("relation", "relations"),
        ("mapping_report", "mapping_reports"),
        ("coverage", "coverage"),
        ("health", "health"),
        ("request_outcome", "request_outcomes"),
        ("native_metadata", "native_metadata"),
    ):
        actual = [row[2] for row in sorted(collections.get(family, ()))]
        if canonical_bytes(actual) != canonical_bytes(product.get(name, [])):
            raise ValueError(
                "review full native export companion values differ from exact base pin"
            )


def inspect_characterization_review(root: Path | int, request, *, manifest_digest=None):
    """Replay the same bounded domain inspection from an authenticated detached closure."""
    from .characterization import add_source_context, inspect_captured_characterization
    from .review_bundle import _member

    if not isinstance(root, int):
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            return inspect_characterization_review(
                descriptor, request, manifest_digest=manifest_digest
            )
        finally:
            os.close(descriptor)
    manifest = verify_characterization_review(root, manifest_digest=manifest_digest)
    selection = CharacterizationReviewSelection.model_validate(manifest["selection"])
    if request.reference() != selection.reference() or request.run_id != selection.run_id:
        raise ValueError("detached characterization inspection differs from captured selection")

    def payload(name):
        spec = manifest["files"][name]
        with _member(root, name, digest=spec["sha256"], size=spec["bytes"]) as stream:
            return json.load(stream)

    layers = {}
    for item in manifest["layers"]:
        pin = ProductReference(**item["reference"])
        layers[(pin.task_id, pin.product_key, pin.content_digest)] = payload(item["path"])
    response = inspect_captured_characterization(payload(manifest["view"]), layers, request)
    from corpus_structure.semantic.pdf_contracts import resolve_native_pointer

    document = payload("base.json")["product"]["content"]
    return add_source_context(
        response,
        request,
        lambda pointers: {
            pointer: resolve_native_pointer(document, pointer) for pointer in pointers
        },
    )


def _native_root(proof):
    from .review_source_projection import _fields, _scalar_matches

    roots = [
        key
        for key, raw in proof.db.execute(
            "SELECT key,body FROM records WHERE product=? AND family='native'", (proof.index_key,)
        )
        if _scalar_matches(_fields(raw)[3].get("native_type"), "DoclingDocument")
    ]
    if len(roots) != 1:
        raise ValueError("review native proof requires one complete document root")
    return roots[0]


def _native_addresses(proof, document):
    """Recover addresses from authenticated edges, independent of producer ID allocation."""
    from corpus_structure.semantic.pdf_record_identity import describe_scalar

    from .review_source_projection import _fields, _scalar_matches

    records = {
        key: _fields(raw)[3]
        for key, raw in proof.db.execute(
            "SELECT key,body FROM records WHERE product=? AND family='native'", (proof.index_key,)
        )
    }
    targets = {describe_scalar(key).encode(): key for key in records}
    addresses = {"#": _native_root(proof)}
    pending = [("#", addresses["#"], document)]

    def escaped(value):
        return str(value).replace("~", "~0").replace("/", "~1")

    while pending:
        path, record, value = pending.pop()
        fields = records[record]
        members = {"items": value} if isinstance(value, list) else value
        for name, member in members.items():
            field_path = path if isinstance(value, list) else path + "/" + escaped(name)
            target = fields.get(name + "/target")
            if target is not None:
                if target not in targets:
                    raise ValueError("review native object target is missing")
                identity = targets[target]
                addresses[field_path] = identity
                pending.append((field_path, identity, member))
            elif _scalar_matches(fields.get(name + "/kind"), "array") or _scalar_matches(
                fields.get(name + "/kind"), "map"
            ):
                mapped = isinstance(member, dict)
                entries = member.items() if mapped else enumerate(member)
                for index, item in entries:
                    key = describe_scalar(index).encode().hex() if mapped else index
                    membership_key = json.dumps(
                        [record, name, key], ensure_ascii=True, separators=(",", ":")
                    )
                    relation = proof._record("membership", membership_key)
                    target = relation.get("target")
                    if target is None:
                        continue
                    if target not in targets:
                        raise ValueError("review native membership target is missing")
                    identity = targets[target]
                    member_path = field_path + "/" + escaped(index)
                    addresses[member_path] = identity
                    pending.append((member_path, identity, item))
    return addresses


def _authenticate_contract(contract, manifest_bytes):
    """Recompile exact archived inputs so a transport reseal cannot change release policy."""
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.characterization import attachment_policies
    from corpus_structure.semantic.types import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
        VocabularyMember,
        VocabularySnapshot,
    )

    manifest = json.loads(manifest_bytes)
    if "release:" + sha256(manifest_bytes).hexdigest() != contract["release_id"]:
        raise ValueError("review archived contract release identity differs")

    def inputs(field):
        values = tuple(
            SourceArtifact(name, base64.b64decode(value, validate=True))
            for name, value in contract[field].items()
        )
        if sorted((value.name, value.digest) for value in values) != [
            tuple(value) for value in manifest[field]
        ]:
            raise ValueError("review archived release inputs differ from release manifest")
        return values

    bundle = SourceBundle(manifest["root"], inputs("sources"))
    vocabularies = tuple(
        VocabularySnapshot(
            enum=value["enum"],
            members=tuple(VocabularyMember(**member) for member in value["members"]),
            dependency=value["dependency"],
            definition_digest=value["definition_digest"],
            dependency_digest=value["dependency_digest"],
            unchecked=tuple(value["unchecked"]),
        )
        for value in manifest["vocabularies"]
    )
    dependencies = ResolvedDependencies(
        inputs("dependencies"), vocabularies, tuple(manifest["ontology_sources"])
    )
    prepared = prepare_release(bundle, dependencies, PreparationProfile(**manifest["profile"]))
    if prepared.manifest != manifest_bytes or prepared.release_id != contract["release_id"]:
        raise ValueError("review released compiler context differs from archived release")
    policies = attachment_policies(prepared)
    names = {"AnnotationLayer", "EnrichedDocumentView"} | {
        row["class_name"] for row in policies.values()
    }
    names.update(
        rule["class_name"]
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    )
    if (
        policies != contract["attachment_policies"]
        or set(contract["schemas"]) != names
        or any(prepared.json_schema(name) != schema for name, schema in contract["schemas"].items())
    ):
        raise ValueError(
            "review archived schemas or attachment policies differ from released inputs"
        )
    return prepared


def _validate_captured_selector(selector, sources):
    matches = [
        source for source in sources if source["ref"]["projection_digest"] == selector["projection"]
    ]
    if not matches:
        raise ValueError("selector cannot resolve exact authenticated source projection")
    for source in matches:
        _validate_captured_selector_source(selector, source)


def _validate_captured_selector_source(selector, source):
    pointer = selector.get("native_pointer")
    items = {item["self_ref"]: item for item in source["context"]["items"]}
    if ("start" in selector) != ("end" in selector) or (
        "start" in selector and not 0 <= selector["start"] <= selector["end"] <= len(source["text"])
    ):
        raise ValueError("selector extent differs from authenticated source projection")
    if pointer is not None and pointer not in items:
        raise ValueError("selector pointer differs from authenticated source selection")

    def contained(native_pointer):
        return any(
            piece.get("kind") == "native_text"
            and piece.get("item_ref") == native_pointer
            and piece["start"] <= selector["start"] <= selector["end"] <= piece["end"]
            for piece in source["context"]["pieces"]
        )

    if pointer is not None and "start" in selector and not contained(pointer):
        raise ValueError("selector extent differs from authenticated native source piece")
    if "page" in selector and not any(
        selector["page"] in {region["page_no"] for region in item.get("prov", ())}
        and (pointer is None or pointer == native_pointer)
        and ("start" not in selector or contained(native_pointer))
        for native_pointer, item in items.items()
    ):
        raise ValueError("selector page differs from authenticated native region and piece")


def _capture_characterization_contract(conn, prepared):
    from corpus_structure.semantic.characterization import attachment_policies
    from corpus_structure.semantic.metadata import table

    policies = attachment_policies(prepared)
    names = {"AnnotationLayer", "EnrichedDocumentView"} | {
        row["class_name"] for row in policies.values()
    }
    names.update(
        rule["class_name"]
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    )
    inputs = table("sem.input")
    archived = {"sources": {}, "dependencies": {}}
    for row in conn.execute(
        select(inputs).where(inputs.c.release_id == prepared.release_id)
    ).mappings():
        destination = {"source": "sources", "dependency": "dependencies"}.get(row["input_kind"])
        if destination is not None:
            archived[destination][row["input_name"]] = base64.b64encode(
                bytes(row["content"])
            ).decode()
    return {
        "release_id": prepared.release_id,
        "manifest_base64": base64.b64encode(prepared.manifest).decode(),
        "schemas": {name: prepared.json_schema(name) for name in sorted(names)},
        "attachment_policies": policies,
        **archived,
    }
