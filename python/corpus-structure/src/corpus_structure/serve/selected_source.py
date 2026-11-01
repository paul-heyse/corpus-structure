"""Selected source events, verified offline index and admitted formula preparation."""

from __future__ import annotations

import base64
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Literal

import ijson
import yaml
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from corpus_structure.serve.companion_export import PublishedSourcePin, _publish_directory

if TYPE_CHECKING:
    from corpus_structure.methods.math.pdf import PreparedFormulaOccurrence
    from corpus_structure.semantic.analysis_contracts import PreparedInterpretationContext


@lru_cache(maxsize=1)
def _protocol():
    source = files("corpus_structure").joinpath("model/semantic/selected-source.yaml").read_bytes()
    declaration = yaml.safe_load(source)
    spec = json.loads(declaration.pop("annotations")["selected-source"])
    boundary_source = yaml.safe_dump(declaration, sort_keys=False).encode()
    boundary = prepare_release(
        SourceBundle("selected-source", (SourceArtifact("selected-source", boundary_source),))
    )
    return spec, boundary, sha256(source).hexdigest()


class SelectedSourceSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    root: str = Field(pattern=r"^#(/[^/]+)+$")
    membership: Literal["descendants"] = "descendants"


class SelectedSourceExportRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    pin: PublishedSourcePin
    selection: SelectedSourceSelection
    destination: Path
    context_policy: Literal["section-source-context-v1"] = "section-source-context-v1"


class SelectedSourceExportReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    format: Literal["selected-source-v1"] = "selected-source-v1"
    pin: PublishedSourcePin
    selection: SelectedSourceSelection
    context_policy: str
    projection_id: str
    schema_digest: str
    header_sha256: str
    byte_length: int
    serialization_sha256: str
    event_counts: dict[str, int]
    selected_record_count: int
    membership_sha256: str


class SelectedSourceUnavailable(ValueError):
    pass


class SelectedSourceInputRequired(SelectedSourceUnavailable):
    outcome = "input_required"

    def __init__(self, artifacts):
        self.artifacts = tuple(artifacts)
        super().__init__(
            "input_required: original artifact bodies are omitted from selected source"
        )


class AdditionalContextRequired(SelectedSourceUnavailable):
    outcome = "additional_context_required"

    def __init__(self, references):
        self.references = tuple(references)
        super().__init__(
            "additional_context_required: selected source omits requested outside values"
        )


def _event(kind: str, data: Any = None, **values) -> dict[str, Any]:
    value = {"event": kind, **values}
    if data is not None:
        value["data"] = canonical_bytes(data).decode()
    _protocol()[1].validate_json("SelectedSourceEvent", json.dumps(value))
    return value


def _part_events(chunks):
    """Bound encoded lines independently of the producer's chunk/scalar boundaries."""
    size = _protocol()[0]["part_bytes"]
    pending = b""
    ordinal = 0
    for chunk in chunks:
        pending += chunk
        while len(pending) > size:
            value, pending = pending[:size], pending[size:]
            yield _event(
                "scalar_part",
                part=ordinal,
                encoding="base64",
                value=base64.b64encode(value).decode(),
                final=False,
            )
            ordinal += 1
    yield _event(
        "scalar_part",
        part=ordinal,
        encoding="base64",
        value=base64.b64encode(pending).decode(),
        final=True,
    )


def _membership_row(pointer, ordinal, parent):
    return f"{pointer}\t{ordinal}\t{parent or ''}\n".encode()


def _write_selected_package(
    reader,
    native_events,
    request,
    temporary: Path,
    *,
    interpretation_model_id,
    implementation_digests,
    cancellation: BorrowerCancellation | None = None,
):
    cancellation = cancellation or BorrowerCancellation()
    cancellation.check_active()
    spec, _, schema = _protocol()
    events = iter(native_events)
    metadata = next(events, None)
    if not metadata or metadata.get("event") != "selection_metadata":
        raise SelectedSourceUnavailable("selected source membership attestation is unavailable")
    header = dict(
        format=spec["format"],
        pin=request.pin.model_dump(),
        selection=request.selection.model_dump(),
        context_policy=request.context_policy,
        schema_digest=schema,
        projection_id="selected-source:"
        + sha256(canonical_bytes([schema, PHYSICAL_MODEL_ID])).hexdigest(),
        physical_model_id=PHYSICAL_MODEL_ID,
        interpretation_model_id=interpretation_model_id,
        implementation_digests=list(implementation_digests),
        included_families=spec["included_families"],
        omissions=spec["omissions"],
        selected_record_count=metadata["selected_count"],
        membership_sha256=metadata["membership_sha256"],
        artifact_references=[
            dict(kind=kind, sha256=reader.revision[key], availability="not_included")
            for kind, key in (
                ("original", "source_digest"),
                ("native_schema", "schema_digest"),
                ("recipe", "recipe_digest"),
            )
        ],
    )
    counts = Counter()
    digest, membership = sha256(), sha256()
    length = selected_count = 0

    with (temporary / "events.jsonl").open("xb") as sink:

        def emit(value):
            nonlocal length
            cancellation.check_active()
            body = canonical_bytes(value) + b"\n"
            if len(body) > spec["max_event_bytes"]:
                raise SelectedSourceUnavailable("selected source event exceeds bounded protocol")
            sink.write(body)
            cancellation.check_active()
            digest.update(body)
            length += len(body)
            counts[value["event"]] += 1

        def emit_payload(chunks):
            payload_digest, payload_length = sha256(), 0
            try:
                for part in _part_events(chunks):
                    raw = base64.b64decode(part["value"], validate=True)
                    payload_digest.update(raw)
                    payload_length += len(raw)
                    emit(part)
            finally:
                chunks.close()
            return dict(byte_length=payload_length, sha256=payload_digest.hexdigest())

        emit(_event("header", header))
        for event in events:
            kind = event["event"]
            if kind == "record_start":
                descriptor = {k: v for k, v in event.items() if k != "event"}
                membership.update(
                    _membership_row(event["pointer"], event["ordinal"], event["parent_pointer"])
                )
                selected_count += 1
                emit(_event("record_start", descriptor))
                ending = None

                def fragments():
                    nonlocal ending
                    for following in events:
                        if following["event"] == "record_end":
                            ending = following
                            return
                        if following["event"] != "native_fragment":
                            raise SelectedSourceUnavailable("native record event was interrupted")
                        yield following["native"]
                    raise SelectedSourceUnavailable("native record event is incomplete")

                payload = emit_payload(reader.iter_native_json(events=fragments()))
                if ending is None or ending["pointer"] != event["pointer"]:
                    raise SelectedSourceUnavailable("native record closing pointer differs")
                emit(
                    _event(
                        "record_end",
                        dict(
                            pointer=event["pointer"],
                            **payload,
                        ),
                    )
                )
            elif kind == "companion_native_start":
                descriptor = {k: v for k, v in event.items() if k != "event"}
                emit(_event("companion_start", descriptor))
                ending = None

                def companion_fragments():
                    nonlocal ending
                    for following in events:
                        if following["event"] == "companion_native_end":
                            ending = following
                            return
                        if following["event"] != "companion_native_fragment":
                            raise SelectedSourceUnavailable(
                                "companion native event was interrupted"
                            )
                        yield following["fragment"]
                    raise SelectedSourceUnavailable("companion native event is incomplete")

                payload = emit_payload(
                    reader.iter_companion_json(descriptor["family"], events=companion_fragments())
                )
                if ending is None:
                    raise SelectedSourceUnavailable("companion native close is missing")
                emit(_event("companion_end", payload))
            elif kind == "scalar_part":
                # PostgreSQL base64 may include line breaks; use one canonical spelling.
                raw = base64.b64decode(event["value"])
                emit(
                    _event(
                        kind,
                        part=event["part"],
                        encoding="base64",
                        value=base64.b64encode(raw).decode(),
                        final=event["final"],
                    )
                )
            elif kind in {"companion_start", "companion_end", "context", "outside_reference"}:
                emit(_event(kind, {k: v for k, v in event.items() if k != "event"}))
            else:
                raise SelectedSourceUnavailable(f"unsupported selected-source native event {kind}")
        if (
            selected_count != header["selected_record_count"]
            or membership.hexdigest() != header["membership_sha256"]
        ):
            raise SelectedSourceUnavailable(
                "selected source membership differs from native attestation"
            )
        emit(
            _event(
                "trailer",
                dict(
                    outcome="complete",
                    event_counts=dict(counts),
                    selected_record_count=selected_count,
                    membership_sha256=membership.hexdigest(),
                    omissions_declared=True,
                ),
            )
        )
    receipt = SelectedSourceExportReceipt(
        pin=request.pin,
        selection=request.selection,
        context_policy=request.context_policy,
        projection_id=header["projection_id"],
        schema_digest=schema,
        header_sha256=sha256(canonical_bytes(header)).hexdigest(),
        byte_length=length,
        serialization_sha256=digest.hexdigest(),
        event_counts=dict(counts),
        selected_record_count=selected_count,
        membership_sha256=membership.hexdigest(),
    )
    (temporary / "receipt.json").write_text(receipt.model_dump_json(indent=2) + "\n")
    return receipt


def export_selected_source(
    request: SelectedSourceExportRequest,
    settings,
    *,
    cancellation: BorrowerCancellation | None = None,
):
    """Close readers and settle the snapshot before atomic no-replace publication."""
    from corpus_structure.semantic.contracts import bound_execution_model
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    cancellation = cancellation or BorrowerCancellation()
    cancellation.check_active()
    spec, boundary, _ = _protocol()
    boundary.validate_json("SelectedSourceExportRequest", request.model_dump_json())
    destination = request.destination
    if destination.exists():
        raise FileExistsError(destination)
    with TemporaryDirectory(prefix=".selected-source-", dir=destination.parent) as owned:
        temporary = Path(owned) / "package"
        temporary.mkdir()
        with (
            open_runtime_engine(
                settings, application_name="ci-selected-source", purpose="read"
            ) as engine,
            read_snapshot(engine, cancellation=cancellation) as connection,
        ):
            release = open_release(connection, request.pin.release_id)
            if release.execution_model_id is None:
                raise SelectedSourceUnavailable(
                    "selected source requires an admitted retained interpretation model"
                )
            model = bound_execution_model(release)
            reader = published_record_reader(
                connection,
                ProductReference(
                    request.pin.task_id, request.pin.product_key, request.pin.content_digest
                ),
                cancellation=cancellation,
            )
            if reader is None:
                raise SelectedSourceUnavailable(
                    "selected source requires a published record-backed product"
                )
            parameters = dict(
                project=request.pin.project_id,
                run=request.pin.run_id,
                release=request.pin.release_id,
                task=request.pin.task_id,
                product=request.pin.product_key,
                digest=request.pin.content_digest,
                section=request.selection.root,
                membership=request.selection.membership,
                policy=spec["context_policy"],
            )
            with connection.execute(
                text(
                    "SELECT * FROM ops.read_pdf_selected_source_events(:project,:run,:release,"
                    ":task,:product,:digest,:section,:membership,:policy)"
                ).execution_options(yield_per=128),
                parameters,
            ) as result:
                receipt = _write_selected_package(
                    reader,
                    (row[0] for row in result),
                    request,
                    temporary,
                    interpretation_model_id=model.model_id,
                    implementation_digests=model.implementation_digests,
                    cancellation=cancellation,
                )
        cancellation.check_active()
        _publish_directory(temporary, destination)
        return receipt


@dataclass(frozen=True)
class PreparedSelectedFormulaInputs:
    pin: PublishedSourcePin
    selection: SelectedSourceSelection
    formulas: tuple[PreparedFormulaOccurrence, ...]
    context_policy: str


class SelectedSourceReader:
    """Verify once into an owned disk index before exposing any accepted prepared input."""

    def __init__(self, package: Path, *, expected_pin=None, expected_selection=None):
        self.package = Path(package)
        self._temporary = TemporaryDirectory(prefix="selected-source-reader-")
        self._root = Path(self._temporary.name)
        self._index = sqlite3.connect(self._root / "index.sqlite3")
        self._closed = False
        self._verified = False
        self.header: dict[str, Any] = {}
        try:
            self.receipt = SelectedSourceExportReceipt.model_validate_json(
                (self.package / "receipt.json").read_bytes()
            )
            if expected_pin is not None and expected_pin != self.receipt.pin:
                raise SelectedSourceUnavailable("selected source pin differs from requested pin")
            if expected_selection is not None and expected_selection != self.receipt.selection:
                raise SelectedSourceUnavailable(
                    "selected source root/membership differs from requested selection"
                )
            self._verify()
        except (ijson.JSONError, UnicodeError, KeyError, sqlite3.IntegrityError) as error:
            self.close()
            raise SelectedSourceUnavailable(
                "selected source JSON/identity/state is invalid"
            ) from error
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if not self._closed:
            self._index.close()
            self._temporary.cleanup()
            self._closed = True

    def _verify(self):
        spec, boundary, schema = _protocol()
        self._index.execute(
            "CREATE TABLE records(pointer TEXT PRIMARY KEY, record_id TEXT UNIQUE, "
            "ordinal INTEGER UNIQUE, parent TEXT, label TEXT, path TEXT)"
        )
        self._index.execute(
            "CREATE TABLE companions(family TEXT, local_id TEXT, ordinal INTEGER, "
            "path TEXT, PRIMARY KEY(family,local_id))"
        )
        self._index.execute("CREATE TABLE descriptors(kind TEXT, body TEXT)")
        self._index.execute(
            "CREATE TABLE endpoints(relation_id TEXT, ordinal INTEGER, "
            "path TEXT, PRIMARY KEY(relation_id,ordinal))"
        )
        digest, membership = sha256(), sha256()
        length = selected_count = 0
        counts = Counter()
        active = None
        payload = None
        payload_digest = sha256()
        payload_length = part_ordinal = 0
        final = trailer_seen = False
        header = None
        last_ordinal = -1
        try:
            with (self.package / "events.jsonl").open("rb") as source:
                while line := source.readline(spec["max_event_bytes"] + 1):
                    if len(line) > spec["max_event_bytes"] or not line.endswith(b"\n"):
                        raise SelectedSourceUnavailable(
                            "selected source line is oversized/incomplete"
                        )
                    digest.update(line)
                    length += len(line)
                    event = json.loads(line)
                    boundary.validate_json("SelectedSourceEvent", line)
                    kind = event["event"]
                    data: dict[str, Any] = json.loads(event["data"]) if "data" in event else {}
                    if trailer_seen:
                        raise SelectedSourceUnavailable("selected source has events after trailer")
                    if kind == "header":
                        if counts or header is not None or not isinstance(data, dict):
                            raise SelectedSourceUnavailable(
                                "selected source header ordering differs"
                            )
                        header = data
                        if (
                            header["schema_digest"] != schema
                            or header["format"] != spec["format"]
                            or header["omissions"] != spec["omissions"]
                            or header["included_families"] != spec["included_families"]
                            or header["context_policy"] != spec["context_policy"]
                            or self.receipt.context_policy != header["context_policy"]
                            or self.receipt.schema_digest != header["schema_digest"]
                            or self.receipt.projection_id != header["projection_id"]
                            or PublishedSourcePin.model_validate(header["pin"]) != self.receipt.pin
                            or SelectedSourceSelection.model_validate(header["selection"])
                            != self.receipt.selection
                            or sha256(canonical_bytes(header)).hexdigest()
                            != self.receipt.header_sha256
                        ):
                            raise SelectedSourceUnavailable(
                                "selected source header/pin/schema/omissions differ"
                            )
                    elif header is None:
                        raise SelectedSourceUnavailable("selected source header is missing")
                    elif kind in {"record_start", "companion_start"}:
                        boundary.validate_json(
                            "SelectedSourceRecordDescriptor"
                            if kind == "record_start"
                            else "SelectedSourceCompanionDescriptor",
                            json.dumps(data),
                        )
                        if active is not None:
                            raise SelectedSourceUnavailable("selected source payloads overlap")
                        if kind == "record_start":
                            if data["ordinal"] <= last_ordinal or data["role"] != "selected":
                                raise SelectedSourceUnavailable(
                                    "selected source record ordering differs"
                                )
                            last_ordinal = data["ordinal"]
                            membership.update(
                                _membership_row(
                                    data["pointer"], data["ordinal"], data["parent_pointer"]
                                )
                            )
                            selected_count += 1
                        path = self._root / f"payload-{sum(counts.values())}.json"
                        payload = path.open("xb")
                        active = (kind, data, path)
                        payload_digest, payload_length, part_ordinal, final = sha256(), 0, 0, False
                    elif kind == "scalar_part":
                        if (
                            active is None
                            or final
                            or event.get("encoding") != "base64"
                            or event.get("part") != part_ordinal
                        ):
                            raise SelectedSourceUnavailable(
                                "selected source scalar-part boundary differs"
                            )
                        raw = base64.b64decode(event["value"], validate=True)
                        if len(raw) > spec["part_bytes"]:
                            raise SelectedSourceUnavailable(
                                "selected source scalar part exceeds profile"
                            )
                        assert payload is not None
                        payload.write(raw)
                        payload_digest.update(raw)
                        payload_length += len(raw)
                        part_ordinal += 1
                        final = event["final"]
                    elif kind in {"record_end", "companion_end"}:
                        if active is None or not final or kind != active[0].replace("start", "end"):
                            raise SelectedSourceUnavailable("selected source payload end differs")
                        assert payload is not None
                        payload.close()
                        payload = None
                        if (
                            payload_length != data["byte_length"]
                            or payload_digest.hexdigest() != data["sha256"]
                        ):
                            raise SelectedSourceUnavailable(
                                "selected source payload digest/length differs"
                            )
                        start, descriptor, path = active
                        # Validate UTF-8/JSON incrementally without hydrating the record/root.
                        native_identity = {}
                        with path.open("rb") as body:
                            for prefix, token, value in ijson.parse(body, use_float=False):
                                if (
                                    prefix in {"self_ref", "label", "parent.$ref"}
                                    and token == "string"
                                ):
                                    native_identity[prefix] = value
                        if active[0] == "record_start":
                            if native_identity.get("self_ref") != active[1]["pointer"]:
                                raise SelectedSourceUnavailable(
                                    "selected record native address differs"
                                )
                            if (
                                "label" in native_identity
                                and native_identity["label"] != active[1]["label"]
                            ):
                                raise SelectedSourceUnavailable(
                                    "selected record native label differs"
                                )
                            if (
                                "parent.$ref" in native_identity
                                and native_identity["parent.$ref"] != active[1]["parent_pointer"]
                            ):
                                raise SelectedSourceUnavailable(
                                    "selected record native parent differs"
                                )
                        if start == "record_start":
                            if data["pointer"] != descriptor["pointer"]:
                                raise SelectedSourceUnavailable(
                                    "selected source pointer changed inside record"
                                )
                            self._index.execute(
                                "INSERT INTO records VALUES(?,?,?,?,?,?)",
                                (
                                    descriptor["pointer"],
                                    descriptor["record_id"],
                                    descriptor["ordinal"],
                                    descriptor["parent_pointer"],
                                    descriptor["label"],
                                    str(path),
                                ),
                            )
                        else:
                            self._index.execute(
                                "INSERT INTO companions VALUES(?,?,?,?)",
                                (
                                    descriptor["family"],
                                    descriptor["local_id"],
                                    descriptor["ordinal"],
                                    str(path),
                                ),
                            )
                            if descriptor["family"] == "endpoint":
                                endpoint = json.loads(path.read_bytes())
                                if not all(
                                    key in endpoint
                                    for key in (
                                        "target_task_id",
                                        "target_product_key",
                                        "target_content_digest",
                                        "occurrence_id",
                                        "role",
                                        "relation_id",
                                        "endpoint_ordinal",
                                    )
                                ):
                                    raise SelectedSourceUnavailable(
                                        "relation endpoint is not qualified"
                                    )
                                self._index.execute(
                                    "INSERT INTO endpoints VALUES(?,?,?)",
                                    (
                                        endpoint["relation_id"],
                                        endpoint["endpoint_ordinal"],
                                        str(path),
                                    ),
                                )
                        active = None
                    elif kind in {"context", "outside_reference"}:
                        if active is not None:
                            raise SelectedSourceUnavailable(
                                "selected source descriptor interrupts payload"
                            )
                        if kind == "outside_reference":
                            target = data.get("body", {}).get("target", {})
                            if data.get("body", {}).get(
                                "resolution"
                            ) != "qualified_external" or not all(
                                key in target
                                for key in ("task_id", "product_key", "content_digest")
                            ):
                                raise SelectedSourceUnavailable(
                                    "outside reference is not product qualified"
                                )
                        self._index.execute(
                            "INSERT INTO descriptors VALUES(?,?)", (kind, json.dumps(data))
                        )
                    elif kind == "trailer":
                        if (
                            active is not None
                            or data.get("outcome") != "complete"
                            or data.get("omissions_declared") is not True
                        ):
                            raise SelectedSourceUnavailable("selected source trailer is incomplete")
                        if (
                            data["event_counts"] != dict(counts)
                            or data["selected_record_count"] != selected_count
                            or data["membership_sha256"] != membership.hexdigest()
                        ):
                            raise SelectedSourceUnavailable(
                                "selected source trailer counts/membership differ"
                            )
                        trailer_seen = True
                    else:
                        raise SelectedSourceUnavailable(
                            "selected source required event kind is unsupported"
                        )
                    counts[kind] += 1
            if not trailer_seen or active is not None or header is None:
                raise SelectedSourceUnavailable("selected source trailer/payload is incomplete")
            if (
                length != self.receipt.byte_length
                or digest.hexdigest() != self.receipt.serialization_sha256
                or dict(counts) != self.receipt.event_counts
                or selected_count != self.receipt.selected_record_count
                or selected_count != header["selected_record_count"]
                or membership.hexdigest() != self.receipt.membership_sha256
                or membership.hexdigest() != header["membership_sha256"]
            ):
                raise SelectedSourceUnavailable(
                    "selected source receipt/membership/serialization differs"
                )
            root = self.receipt.selection.root
            rows = self._index.execute("SELECT pointer,parent FROM records ORDER BY ordinal")
            if not self._index.execute("SELECT 1 FROM records WHERE pointer=?", (root,)).fetchone():
                raise SelectedSourceUnavailable("selected source root is absent")
            for pointer, parent in rows:
                if (
                    pointer != root
                    and not self._index.execute(
                        "SELECT 1 FROM records WHERE pointer=?", (parent,)
                    ).fetchone()
                ):
                    raise SelectedSourceUnavailable("selected source ancestry leaves its root")
            reachable = self._index.execute(
                "WITH RECURSIVE reached(pointer) AS (SELECT pointer FROM records WHERE pointer=? "
                "UNION SELECT r.pointer FROM records r JOIN reached p ON r.parent=p.pointer) "
                "SELECT count(*) FROM reached",
                (root,),
            ).fetchone()[0]
            if reachable != selected_count:
                raise SelectedSourceUnavailable(
                    "selected source contains disconnected/cyclic ancestry"
                )
            for relation_id, path in self._index.execute(
                "SELECT local_id,path FROM companions WHERE family='relation'"
            ):
                relation = json.loads(Path(path).read_bytes())
                endpoint_rows = list(
                    self._index.execute(
                        "SELECT ordinal,path FROM endpoints WHERE relation_id=? ORDER BY ordinal",
                        (relation_id,),
                    )
                )
                declared = relation.get("endpoints", [])
                if [row[0] for row in endpoint_rows] != list(range(len(declared))):
                    raise SelectedSourceUnavailable(
                        "relation endpoint multiplicity/ordinals differ"
                    )
                for expected, (_, endpoint_path) in zip(declared, endpoint_rows, strict=True):
                    endpoint = json.loads(Path(endpoint_path).read_bytes())
                    if (expected["role"], expected["occurrence_id"]) != (
                        endpoint["role"],
                        endpoint["occurrence_id"],
                    ):
                        raise SelectedSourceUnavailable("relation endpoint role/occurrence differs")
            self.header = header
            self._verified = True
        finally:
            if payload is not None:
                payload.close()

    def descriptors(self, kind="context"):
        if self._closed or not self._verified:
            raise SelectedSourceUnavailable("selected source reader is closed/unverified")
        return tuple(
            json.loads(row[0])
            for row in self._index.execute("SELECT body FROM descriptors WHERE kind=?", (kind,))
        )

    def prepare_formula_inputs(
        self,
        context: PreparedInterpretationContext,
        *,
        required_outside_values=(),
        required_artifact_digests=(),
    ) -> PreparedSelectedFormulaInputs:
        """Prepare the selected extraction input through FormulaOccurrence's existing frontend."""
        from corpus_structure.methods.math.pdf import FormulaOccurrence

        if self._closed or not self._verified:
            raise SelectedSourceUnavailable("selected source reader is closed/unverified")
        if (
            context.release_id != self.receipt.pin.release_id
            or context.model_id != self.header["interpretation_model_id"]
            or [list(value) for value in context.implementation_digests]
            != self.header["implementation_digests"]
        ):
            raise SelectedSourceUnavailable(
                "admitted retained interpretation context/model/artifacts are required"
            )
        if required_artifact_digests:
            requested = set(required_artifact_digests)
            references = [
                value
                for value in self.header["artifact_references"]
                if value["sha256"] in requested
            ]
            raise SelectedSourceInputRequired(references)
        required = set(required_outside_values)
        external = self.descriptors("outside_reference") if required else ()
        needed = [
            item["body"]
            for item in external
            if item["body"]["target"].get("pointer") in required
            or item["body"]["target"].get("occurrence_id") in required
        ]
        if required and (
            needed
            or not required
            <= {row[0] for row in self._index.execute("SELECT pointer FROM records")}
        ):
            raise AdditionalContextRequired(needed or external)
        outcomes = {}
        for (path,) in self._index.execute(
            "SELECT path FROM companions WHERE family='native_metadata'"
        ):
            body = json.loads(Path(path).read_bytes())
            if body.get("kind") == "formula_outcomes":
                value = body.get("value", {})
                pointer = value.get("pointer", body.get("pointer"))
                if pointer in outcomes:
                    raise SelectedSourceUnavailable("formula recognition attribution is ambiguous")
                outcomes[pointer] = value.get("outcome", body.get("outcome", "unknown"))
        prepared = []
        for pointer, path in self._index.execute(
            "SELECT pointer,path FROM records WHERE label='formula' ORDER BY ordinal"
        ):
            body = json.loads(Path(path).read_bytes())
            if body.get("self_ref") != pointer:
                raise SelectedSourceUnavailable("formula native address differs")
            prepared.append(
                FormulaOccurrence(
                    self.receipt.pin.content_digest,
                    pointer,
                    body.get("text", ""),
                    body.get("orig", ""),
                    outcomes.get(pointer, "unknown"),
                ).prepare(context)
            )
        return PreparedSelectedFormulaInputs(
            self.receipt.pin, self.receipt.selection, tuple(prepared), self.receipt.context_policy
        )


def export_selected_native_source(
    request, destination: Path, settings, *, cancellation: BorrowerCancellation | None = None
):
    """Resolve the CLI's run qualification, then execute the owned package service."""
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    cancellation = cancellation or BorrowerCancellation()
    cancellation.check_active()
    if (
        request.section_pointer is None
        or request.membership != "descendants"
        or any(
            value is not None
            for value in (
                request.pointer,
                request.cell_index,
                request.cursor,
                request.occurrence_id,
            )
        )
    ):
        raise SelectedSourceUnavailable(
            "selected-source-v1 requires one section and descendant membership"
        )
    with (
        open_runtime_engine(
            settings, application_name="ci-selected-source-pin", purpose="read"
        ) as engine,
        read_snapshot(engine, cancellation=cancellation) as connection,
    ):
        runs = table("ops.run")
        row = connection.execute(
            select(runs.c.project_id, runs.c.release_id).where(runs.c.id == request.run_id)
        ).one()
    selected = SelectedSourceExportRequest(
        pin=PublishedSourcePin(
            project_id=row.project_id,
            release_id=row.release_id,
            run_id=request.run_id,
            task_id=request.task_id,
            product_key=request.product_key,
            content_digest=request.content_digest,
        ),
        selection=SelectedSourceSelection(root=request.section_pointer),
        destination=destination,
    )
    return export_selected_source(selected, settings, cancellation=cancellation)
