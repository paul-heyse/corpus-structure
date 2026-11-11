"""Portable primary-layer closure for analytical reports, without provider execution."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from typing import Any

from sqlalchemy import select

from corpus_structure.semantic.characterization import validate_layer
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference


def capture_primary_contract(conn, release, contracts, budget):
    from corpus_structure.semantic.releases import open_release

    from .characterization_replay import _capture_characterization_contract

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
    from .characterization_replay import _authenticate_contract, validate_captured_layer_sources
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
