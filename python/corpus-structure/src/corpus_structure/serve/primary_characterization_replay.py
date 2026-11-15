"""Portable primary-layer closure for analytical reports, without provider execution."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from hashlib import sha256
from typing import Any

from sqlalchemy import select

from corpus_structure.semantic.characterization import validate_layer
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference


def capture_primary_contract(conn, release, contracts, budget):
    from corpus_structure.semantic.releases import open_release

    if release in contracts:
        return None
    contracts.add(release)
    contract = _capture_characterization_contract(conn, open_release(conn, release))
    budget.value(contract)
    return contract


def capture_primary_layers(
    conn, references, *, run_id, seen, contracts, budget
) -> Iterator[tuple[str, dict[str, Any]]]:
    from corpus_structure.semantic.characterization_store import read_layer
    from corpus_structure.semantic.metadata import table

    pending = list(references)
    while pending:
        pin = ProductReference(**pending.pop())
        if pin in seen:
            continue
        layer = read_layer(conn, pin, run_id=run_id)
        seen.add(pin)
        body = layer.payload
        release = body["release_id"]
        contract = capture_primary_contract(conn, release, contracts, budget)
        if contract is not None:
            yield "characterization_contracts", contract
        task, config, method, run = map(
            table, ("ops.task", "ops.method_config", "ops.method", "ops.run")
        )
        producer = dict(
            conn.execute(
                select(
                    task.c.input_hash,
                    config.c.config_hash,
                    method.c.name,
                    method.c.version,
                    run.c.runtime_id,
                    task.c.release_id,
                )
                .select_from(
                    task.join(config, config.c.id == task.c.method_config_id)
                    .join(method, method.c.id == config.c.method_id)
                    .join(run, run.c.id == task.c.run_id)
                )
                .where(task.c.id == pin.task_id)
            )
            .mappings()
            .one()
        )
        row = dict(reference=pin.values(), payload=body, producer=producer)
        budget.value(row)
        yield "characterization_layers", row
        pending.extend(body["dependencies"])


def retained_primary_layers(root, manifest):
    """Authenticate archived declarations, exact pins and the source-backed DAG once."""
    from .review_bundle import _detached_relation

    contracts = {}
    for contract in _detached_relation(root, manifest, "characterization_contracts"):
        release = contract["release_id"]
        if release in contracts:
            raise ValueError("duplicate primary layer contract")
        contracts[release] = _authenticate_contract(
            contract, base64.b64decode(contract["manifest_base64"], validate=True)
        )
    rows = {}
    for row in _detached_relation(root, manifest, "characterization_layers"):
        pin = ProductReference(**row["reference"])
        if pin in rows:
            raise ValueError("duplicate primary layer product")
        rows[pin] = row
    from corpus_structure.semantic.characterization import LayerReport

    layers = {pin: LayerReport(canonical_bytes(row["payload"])) for pin, row in rows.items()}
    sources = {row["source_view_id"]: row for row in _detached_relation(root, manifest, "sources")}
    for pin, layer in layers.items():
        body = layer.payload
        if layer.reference(pin.task_id) != pin:
            raise ValueError("primary layer differs from immutable product pin")
        prepared = contracts.get(body["release_id"])
        if prepared is None:
            raise ValueError("primary layer lacks its original released contract")
        validated = validate_layer(prepared, body, dependencies=layers, releases=contracts)
        if validated.content != layer.content:
            raise ValueError("primary layer differs from released canonical contract")
        producer, operation = rows[pin]["producer"], body["operation"]
        if (
            producer["name"],
            producer["version"],
            producer["config_hash"],
            producer["input_hash"],
            producer["runtime_id"],
            producer["release_id"],
        ) != (
            operation["key"],
            operation["version"],
            operation["configuration"],
            operation["input"],
            operation["runtime"],
            body["release_id"],
        ):
            raise ValueError("primary layer differs from exact producing operation")
        selected = []
        for source in body["source_scope"]["source_views"]:
            captured = sources.get(source["source_view_id"])
            if captured is None:
                raise ValueError("primary layer source closure is missing")
            ref = captured["ref"]
            if (ref["native_product"], ref["projection_digest"], ref["recipe_digest"]) != (
                body["base_document"],
                source["projection_digest"],
                source["recipe_digest"],
            ):
                raise ValueError("primary layer differs from captured original source")
            selected.append(captured)
        validate_captured_layer_sources(body, sources)
    return layers, contracts


def primary_layers_for_report(root, manifest, report, *, source_view_id=None, retained=None):
    layers, releases = retained if retained is not None else retained_primary_layers(root, manifest)
    pins = tuple(
        ProductReference(**value)
        for value in report["configuration"].get("characterization_layers", ())
    )
    if not pins or len(set(pins)) != len(pins) or any(pin not in layers for pin in pins):
        raise ValueError("analytical report lacks its frozen primary layer closure")
    selected = {
        pin: layers[pin]
        for pin in pins
        if source_view_id is None
        or source_view_id in layers[pin].payload["source_scope"]["source_view_ids"]
    }
    return selected, releases


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
