"""Portable source projection replay from the qualified PDF record fold."""

from __future__ import annotations

import base64
import json
import sqlite3
import struct
import zlib
from collections import defaultdict
from collections.abc import Mapping
from hashlib import sha256
from itertools import batched

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_hierarchy import (
    project_section_nodes,
    section_text_recipe,
    section_view_key,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_identity import (
    MAX_FRAME_BYTES,
    PROTOCOL,
    IdentityFold,
    describe_scalar,
    record_frame,
)
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import ReadLimit

SECTION_TEXT_INPUT = "execution/implementation/pdf/section-text-recipe.json"
_COMPLETE_INVENTORY_RECIPE = "native-section-text-v10"
_SECTIONS = {"section", "chapter"}
_MAX_PROOF_FRAMES = 1_000_000
_MAX_PROOF_BYTES = 384 * 1024**2
_BATCH_BYTES = 512 * 1024

# Only these projected fields affect the section inventory or selected spelling.
_ITEM_FIELDS = {
    "self_ref": None,
    "label": None,
    "content_layer": None,
    "parent": {"$ref": None},
    "children": ({"$ref": None},),
    "captions": ({"$ref": None},),
    "text": None,
    "orig": None,
    "prov": (
        {
            "page_no": None,
            "charspan": (None,),
            "bbox": {"l": None, "t": None, "r": None, "b": None, "coord_origin": None},
        },
    ),
    "data": {"table_cells": ({"text": None, "ref": {"$ref": None}},)},
    "meta": {"tabular_chart": {"title": None, "chart_data": {"table_cells": ({"text": None},)}}},
}


def capture_source_projection(connection, source, budget):
    """Resolve the exact consumer release independently of the source payload."""
    view = table("kb.source_view")
    query = select(view.c.release_id).where(view.c.id == source.ref.id)
    budget.preflight(connection, query)
    return connection.execute(query).scalar_one()


def capture_source_proof(connection, reference, prepared, cancellation):
    """Transfer the ordered logical frames once, in bounded compressed batches."""
    reader = published_record_reader(connection, reference, projection_context=prepared)
    if reader is None:
        raise ValueError("review source has no qualified native product")
    rev = reader.revision
    yield dict(
        product=reference.values(),
        original=rev["source_digest"],
        producer_release=rev["release_id"],
        native_schema=rev["schema_digest"],
    )
    pin = dict(task=reference.task_id, key=reference.product_key, digest=reference.content_digest)
    frame_query = text("""
        SELECT frame FROM ops.read_pdf_record_identity_frames(:task,:key,:digest)
        WITH ORDINALITY AS proof(frame, ordinal) ORDER BY ordinal
    """)
    count, size, batch = 0, 0, bytearray()
    try:
        with connection.execute(frame_query.execution_options(yield_per=64), pin) as result:
            for raw in result.scalars():
                cancellation.check_active()
                raw = bytes(raw)
                count += 1
                size += len(raw)
                if (
                    count > _MAX_PROOF_FRAMES
                    or size > _MAX_PROOF_BYTES
                    or len(raw) > MAX_FRAME_BYTES
                ):
                    raise ReadLimit("review native proof exceeds frame budget", reason="work_limit")
                if batch and len(batch) + len(raw) > _BATCH_BYTES:
                    yield {"frames": base64.b64encode(zlib.compress(batch)).decode("ascii")}
                    batch.clear()
                batch.extend(raw)
    except DBAPIError as error:
        if getattr(error.orig, "sqlstate", None) == "54000":
            raise ReadLimit(
                "review native proof exceeds frame budget", reason="work_limit"
            ) from error
        raise
    if batch:
        yield {"frames": base64.b64encode(zlib.compress(batch)).decode("ascii")}
    target_query = text("SELECT * FROM ops.read_pdf_record_identity_targets(:task,:key,:digest)")
    with connection.execute(target_query.execution_options(yield_per=128), pin) as result:
        for rows in batched(result, 256, strict=False):
            cancellation.check_active()
            yield {"targets": [tuple(row) for row in rows]}
    item_query = text("SELECT * FROM ops.read_pdf_record_identity_items(:task,:key,:digest)")
    with connection.execute(item_query.execution_options(yield_per=64), pin) as result:
        for rows in batched(result.mappings(), 128, strict=False):
            cancellation.check_active()
            yield {"items": [dict(row) for row in rows]}


def open_proof_index(path):
    database = sqlite3.connect(path)
    database.executescript("""
        CREATE TABLE records (product TEXT, family TEXT, key TEXT, body BLOB,
          PRIMARY KEY(product, family, key)) WITHOUT ROWID;
        CREATE TABLE targets (product TEXT, owner TEXT, field TEXT, position INTEGER, target TEXT,
          PRIMARY KEY(product, owner, field, position)) WITHOUT ROWID;
    """)
    return database


def archived_projection_policy(contract):
    archived = contract["section_text_policy"]
    manifest = base64.b64decode(archived["manifest_base64"], validate=True)
    policy = base64.b64decode(archived["input_base64"], validate=True)
    if "release:" + sha256(manifest).hexdigest() != contract["release_id"] or sha256(
        policy
    ).hexdigest() != dict(json.loads(manifest)["dependencies"]).get(SECTION_TEXT_INPUT):
        raise ValueError("review source projection recipe is not bound to its archived release")
    return policy


def load_source_proofs(database, rows):
    proofs = {}
    current = None
    for row in rows:
        if "product" in row:
            if current is not None:
                current.settle()
            current = NativeProjectionProof(database, row)
            if current.reference in proofs:
                raise ValueError("review repeats a native product proof")
            proofs[current.reference] = current
        elif current is None or len(row) != 1:
            raise ValueError("review native proof requires a product header")
        elif "frames" in row:
            current.add_frames(row["frames"])
        elif "targets" in row:
            current.add_targets(row["targets"])
        elif "items" in row:
            current.add_items(row["items"])
        else:
            raise ValueError("unknown review native proof batch")
    if current is not None:
        current.settle()
    database.commit()
    return proofs


def _tagged(value, start, tag):
    if start + 9 > len(value) or value[start] != ord(tag):
        raise ValueError("invalid native proof frame tag")
    size = struct.unpack_from(">q", value, start + 1)[0]
    end = start + 9 + size
    if size < 0 or end > len(value):
        raise ValueError("invalid native proof frame length")
    return value[start + 9 : end], end


def _fields(raw):
    body, end = _tagged(raw, 0, "R")
    if end != len(raw) or len(body) < 8:
        raise ValueError("invalid native proof frame")
    count = struct.unpack_from(">q", body)[0]
    if not 0 <= count <= len(body) // 50:
        raise ValueError("invalid native proof field count")
    schema, pos = _tagged(body, 8, "s")
    family, pos = _tagged(body, pos, "f")
    key, pos = _tagged(body, pos, "k")
    fields = {}
    for _ in range(count):
        name, pos = _tagged(body, pos, "n")
        name = name.decode()
        if name in fields or pos + 41 > len(body):
            raise ValueError("invalid native proof field")
        fields[name] = body[pos : pos + 41]
        pos += 41
    if pos != len(body):
        raise ValueError("native proof frame has trailing data")
    return schema.decode(), family.decode(), key.decode(), fields


def _batch(value):
    packed = base64.b64decode(value, validate=True)
    if len(packed) > _BATCH_BYTES + 1024:
        raise ValueError("review native proof batch exceeds byte budget")
    decoder = zlib.decompressobj()
    try:
        body = decoder.decompress(packed, _BATCH_BYTES + 1)
    except zlib.error as error:
        raise ValueError("invalid compressed native proof batch") from error
    if not decoder.eof or decoder.unused_data or len(body) > _BATCH_BYTES:
        raise ValueError("invalid compressed native proof batch")
    pos = 0
    while pos < len(body):
        _, end = _tagged(body, pos, "R")
        if end - pos > MAX_FRAME_BYTES:
            raise ValueError("review native proof frame exceeds byte budget")
        yield body[pos:end]
        pos = end


def _scalar_matches(expected, value):
    if expected is None or type(value) not in {str, int, float, bool, type(None)}:
        return False
    if expected[:1] == b"f" and type(value) in {int, float}:
        # JSONB delivery treats integer spelling and signed zero as the same number.
        return describe_scalar(float(value)).encode() == expected or (
            value == 0 and describe_scalar(-0.0).encode() == expected
        )
    return describe_scalar(value).encode() == expected


def _membership_key(parent, field, position):
    return json.dumps([parent, field, position], ensure_ascii=True, separators=(",", ":"))


class NativeProjectionProof:
    """Disk-indexed proof data is scoped to one verification invocation."""

    def __init__(self, database, header):
        self.db = database
        self.reference = ProductReference(**header["product"])
        self.key = self.reference.content_digest
        self.index_key = json.dumps(self.reference.values(), sort_keys=True)
        self.original = header["original"]
        self.schema = header["native_schema"]
        self.release = header["producer_release"]
        self.fold = IdentityFold("records")
        self.previous = None
        self.inventory = {}
        self.by_parent = defaultdict(list)
        self.ordinal = {}
        self._total_items = 0
        self._total_targets = 0

    def add_frames(self, value):
        for raw in _batch(value):
            schema, family, key, fields = _fields(raw)
            if schema != self.schema or (
                self.previous is not None and (family, key) <= self.previous
            ):
                raise ValueError("review native proof frame order or schema differs")
            if self.previous is None and raw != record_frame(
                self.schema,
                "@context",
                "@context",
                (("protocol", PROTOCOL), ("release", self.release), ("source", self.original)),
            ):
                raise ValueError("review native proof context differs")
            self.previous = family, key
            self.fold.add(raw)
            if self.fold.count > _MAX_PROOF_FRAMES or self.fold.byte_length > _MAX_PROOF_BYTES:
                raise ValueError("review native proof exceeds frame budget")
            if family in {"native", "membership"}:
                self.db.execute(
                    "INSERT INTO records VALUES(?,?,?,?)", (self.index_key, family, key, raw)
                )
                if family == "native" and "self_ref/value" in fields:
                    self._total_items += 1
                if family == "native":
                    self._total_targets += sum(name.endswith("/target") for name in fields)
                if family == "membership" and "target" in fields and "ordinal" in fields:
                    self._total_targets += 1

    def _record(self, family, key):
        row = self.db.execute(
            "SELECT body FROM records WHERE product=? AND family=? AND key=?",
            (self.index_key, family, key),
        ).fetchone()
        if row is None:
            raise ValueError("review source native proof is missing a record")
        return _fields(row[0])[3]

    def _object_id(self, expected, claimed):
        # Native targets are SHA-256 occurrence IDs. Resolve a target from the
        # authenticated native index, never from a self-supplied descriptor.
        if not _scalar_matches(expected, claimed):
            raise ValueError("review source native target differs")
        return claimed

    def _targets(self, owner, field, position=None):
        row = self.db.execute(
            "SELECT target FROM targets WHERE product=? AND owner=? AND field=? AND position=?",
            (self.index_key, owner, field, -1 if position is None else position),
        ).fetchone()
        if row is None:
            raise ValueError("review source native proof is missing a target")
        return row[0]

    def add_targets(self, rows):
        for owner, field, position, target in rows:
            if self._total_targets <= 0:
                raise ValueError("review native proof target budget exhausted")
            self._total_targets -= 1
            if position == -1:
                expected = self._record("native", owner).get(field + "/target")
            else:
                expected = self._record("membership", _membership_key(owner, field, position)).get(
                    "target"
                )
            self._object_id(expected, target)
            self.db.execute(
                "INSERT INTO targets VALUES(?,?,?,?,?)",
                (self.index_key, owner, field, position, target),
            )

    def _check_value(self, record, fields, field, value, shape):
        expected = fields.get(field + "/value")
        if expected is not None:
            if not _scalar_matches(expected, value):
                raise ValueError(
                    "review source value differs from the authenticated native occurrence"
                )
            return
        kind = fields.get(field + "/kind")
        if kind is None:
            raise ValueError(
                "review source field is absent from the authenticated native occurrence"
            )
        if (
            isinstance(shape, Mapping)
            and isinstance(value, dict)
            and _scalar_matches(kind, "object")
        ):
            target = self._object_id(fields.get(field + "/target"), self._targets(record, field))
            self._check_object(target, value, shape)
            return
        if isinstance(shape, tuple) and isinstance(value, list) and _scalar_matches(kind, "array"):
            if not _scalar_matches(fields.get(field + "/length"), len(value)):
                raise ValueError("review source native array inventory differs")
            for i, item in enumerate(value):
                member = self._record("membership", _membership_key(record, field, i))
                if "target" in member and isinstance(item, dict) and isinstance(shape[0], Mapping):
                    target = self._object_id(member["target"], self._targets(record, field, i))
                    self._check_object(target, item, shape[0])
                elif not _scalar_matches(member.get("value"), item):
                    raise ValueError("review source native array member differs")
            return
        raise ValueError("review source native field representation differs")

    def _check_object(self, record, value, shape):
        fields = self._record("native", record)
        for name, subshape in shape.items():
            present = name + "/value" in fields or name + "/kind" in fields
            if present != (name in value):
                raise ValueError("review source native field inventory differs")
            if present:
                self._check_value(record, fields, name, value[name], subshape)

    def add_items(self, rows):
        for row in rows:
            pointer, record = row["pointer"], row["record_id"]
            if pointer in self.inventory or len(self.inventory) >= self._total_items:
                raise ValueError("review source native inventory repeats an occurrence")
            fields = self._record("native", record)
            if not _scalar_matches(fields.get("self_ref/value"), pointer):
                raise ValueError(
                    "review source pointer differs from authenticated native occurrence"
                )
            label, layer, parent, children = (
                row["label"],
                row["content_layer"],
                row["parent_pointer"],
                row["children"],
            )
            for name, value, default in (
                ("label", label, "unspecified"),
                ("content_layer", layer, "body"),
            ):
                expected = fields.get(name + "/value")
                if (expected is not None and not _scalar_matches(expected, value)) or (
                    expected is None and value != default
                ):
                    raise ValueError(
                        "review source exclusion differs from authenticated native occurrence"
                    )
            if parent is not None or "parent/kind" in fields:
                self._check_value(
                    record,
                    fields,
                    "parent",
                    None if parent is None else {"$ref": parent},
                    _ITEM_FIELDS["parent"],
                )
            if children is not None or "children/kind" in fields:
                self._check_value(record, fields, "children", children, _ITEM_FIELDS["children"])
            self.inventory[pointer] = (record, label, layer, parent, children or ())
            self.by_parent[parent].append(pointer)

    def settle(self):
        if (
            self.fold.digest().hex() != self.key
            or len(self.inventory) != self._total_items
            or self._total_targets
        ):
            raise ValueError("review native proof does not match the exact product and inventory")
        pending = [pointer for pointer in ("#/furniture", "#/body") if pointer in self.inventory]
        while pending:
            pointer = pending.pop()
            if pointer in self.ordinal:
                raise ValueError("review native occurrence order is ambiguous")
            self.ordinal[pointer] = len(self.ordinal)
            pending.extend(child["$ref"] for child in reversed(self.inventory[pointer][4]))
        for pointer in sorted(self.inventory.keys() - self.ordinal.keys()):
            self.ordinal[pointer] = len(self.ordinal)

    def members(self, section, membership):
        direct = membership == "direct"
        _, label, layer, parent, _ = self.inventory[section]
        if layer != "body" or (
            label not in _SECTIONS and not (direct and section == "#/body" and parent is None)
        ):
            raise ValueError("review native source section differs")
        selected, pending = set(), [section]
        while pending:
            pointer = pending.pop()
            if pointer in selected:
                raise ValueError("review native source membership is cyclic")
            selected.add(pointer)
            pending.extend(
                child
                for child in self.by_parent[pointer]
                if self.inventory[child][2] == "body"
                and not (direct and self.inventory[child][1] in _SECTIONS)
            )
        ancestry = []
        while parent is not None:
            if parent in ancestry:
                raise ValueError("review native source ancestry is cyclic")
            ancestry.append(parent)
            parent = self.inventory[parent][3]
        return (
            tuple(sorted(selected, key=self.ordinal.__getitem__)),
            tuple(
                pointer
                for pointer in reversed(ancestry)
                if pointer not in {"#/body", "#/furniture"}
            ),
        )

    def check_item(self, node):
        self._check_object(self.inventory[node["self_ref"]][0], node, _ITEM_FIELDS)
        if node.get("label") == "formula" and any(
            set(loc) - {"page_no", "charspan", "bbox"}
            or set(loc.get("bbox", ())) - {"l", "t", "r", "b", "coord_origin"}
            for loc in node.get("prov", ())
        ):
            raise ValueError("review formula provenance differs from authenticated witness fields")


def verify_source_projection(value, policy, proof):
    """Derive the current membership and ordered field inventory from verified records."""
    ref, context = value["ref"], value["context"]
    recipe = section_text_recipe(
        proof.reference, analysis_eligible=ref["analysis_eligible"], policy=policy
    )
    if (
        json.loads(policy).get("recipe") != _COMPLETE_INVENTORY_RECIPE
        or sha256(recipe).hexdigest() != ref["recipe_digest"]
        or ref["key"]
        != section_view_key(
            value["consumer_release"],
            proof.reference,
            ref["section_pointer"],
            ref["membership"],
            ref["analysis_eligible"],
            recipe,
        )
    ):
        raise ValueError(
            "review source projection recipe differs from its archived consumer release"
        )
    selected, ancestry = proof.members(ref["section_pointer"], ref["membership"])
    if selected != tuple(item["self_ref"] for item in context["items"]) or ancestry != tuple(
        item["self_ref"] for item in context["ancestors"]
    ):
        raise ValueError("review source membership differs from authenticated native inventory")
    for item in (*context["items"], *context["ancestors"]):
        proof.check_item(item)
    nodes = {item["self_ref"]: item for item in (*context["items"], *context["ancestors"])}
    # The projector requires known but excluded structural children to stop traversal.
    for pointer in selected:
        for child in proof.inventory[pointer][4]:
            address = child["$ref"]
            if address not in nodes:
                _, label, layer, _, _ = proof.inventory[address]
                nodes[address] = {"self_ref": address, "label": label, "content_layer": layer}
    projection = project_section_nodes(
        nodes,
        proof.key,
        ref["section_pointer"],
        "direct" if ref["membership"] == "direct" else "descendant",
        section_refs=frozenset(
            pointer
            for pointer, (_, label, _, _, _) in proof.inventory.items()
            if pointer == "#/body" or label in _SECTIONS
        ),
        selected_items=selected,
        projection_policy=recipe,
        original_digest=proof.original,
    )
    if (
        projection.text != value["text"]
        or [p.to_wire() for p in projection.pieces] != context["pieces"]
    ):
        raise ValueError(
            "review source field address inventory differs from selected native occurrences"
        )
    return proof.original
