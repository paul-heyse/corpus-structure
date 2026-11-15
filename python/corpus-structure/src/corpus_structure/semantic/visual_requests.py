"""Actual external Chandra receipts and declared mechanical visual mapping.

Local recognition consumes the native packet's exact PNG. Its raw response is
retained under the actual request/attempt before native admission; mapping is a
separate declared derivation over that admitted observation.
"""

from __future__ import annotations

import inspect
import json
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import yaml

from corpus_structure.semantic.identifiers import TaskAttempt, TaskId

from .data_operation_identity import decode_semantic_value, semantic_value
from .data_operation_json import json_bytes, wire_json_loads
from .data_operation_ports import PortCompletion, PortRefusal, RoleValue, _untrusted_value
from .identity import canonical_bytes
from .types import SourceArtifact

VISUAL_RECOGNIZE = "source.visual/recognize"
VISUAL_MAP = "source.visual/map"
VISUAL_INPUT = "source.visual_input/render"
_NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-visual/"
_PROVIDER = "datalab-chandra-2"
_MAX_REPLAY_BYTES = 8 * 1024 * 1024


def visual_external_declaration():
    """The existing Chandra actor uses native external packet/receipt authority."""
    from corpus_structure.ingest.pdf_chandra import (
        CHANDRA_REPOSITORY,
        CHANDRA_REVISION,
        chandra_recognition_identity,
    )

    from .data_operation_model import MODEL_VERSION

    root = Path(__file__).parents[1] / "model/semantic"
    image_fields = tuple(
        yaml.safe_load((root / "data-operation-visual.yaml").read_bytes())["classes"][
            "DdoVisualInput"
        ]["attributes"]
    )
    operation = {
        "id": VISUAL_RECOGNIZE,
        "profile": "command",
        "subject": "original-document",
        "subject_definition": {
            "id": "original-document",
            "identifier_kind": "string",
            "scope": "original-document",
        },
        "discovery_relation": "role-associated",
        "context": ["original-source", "exact-submitted-png"],
        "roles": [
            {
                "name": "image",
                "kind": _NAMESPACE + "DdoVisualInput",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "image", "description": "page-or-native-region"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "observation",
                "kind": _NAMESPACE + "DdoChandraObservation",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "dependencies": [VISUAL_INPUT],
        "parameters": {},
        "applicability": [
            {"kind": "documentation", "text": "actual-png-and-explicit-local-chandra-actor"}
        ],
        "invariants": [
            {"kind": "documentation", "text": "same-submitted-image"},
            {"kind": "documentation", "text": "actual-raw-response"},
            {"kind": "documentation", "text": "provider-reported-runtime"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "declared-contract", "reference": "self"}],
            "description": "exact-submitted-png",
        },
        "outcomes": ["success"],
        "precision_description": "unselected-chandra-raw-observation",
        "effects": [
            {
                "name": "external-chandra-observation",
                "authorization": ["native-purpose:write"],
                "idempotency": "external-packet",
                "fulfillment": "native-publication-receipt",
            }
        ],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "external",
            "cancellation": "lease-fence",
            "ownership": "native-task-packet",
        },
        "external": {
            "version": "external-executor-v1",
            "instructions": canonical_bytes(
                {
                    "version": "chandra-native-png-v1",
                    "policy": chandra_recognition_identity(),
                    "instructions": "Recognize exactly the submitted PNG. Return its unchanged image, actual response and provider-reported runtime; source fidelity remains unassessed.",
                }
            ).decode(),
            "requested_actor": _PROVIDER,
            "requested_model": CHANDRA_REPOSITORY + "@" + CHANDRA_REVISION,
            "reference_scope": "declared-inputs-only",
        },
        "behavior": "actual local Chandra work admitted through native external receipt custody",
        "binding": {"operator": "scan", "roles": ["image"]},
        "output_witnesses": [
            {
                "output_role": "observation",
                "records": "",
                "input_role": "image",
                "comparisons": [
                    {
                        "output_field": "/image/" + field,
                        "input": {
                            "role": "image",
                            "projection": _NAMESPACE + "DdoVisualInput",
                            "field": "/" + field,
                        },
                        "encoding": "value",
                    }
                    for field in image_fields
                ],
            }
        ],
    }
    return SourceArtifact(
        "visual/recognition-protocol.json",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "operations": [operation],
            }
        ),
    )


def visual_mapping_profile():
    from corpus_structure.ingest.pdf_chandra import chandra_parser_identity
    from corpus_structure.semantic.visual_evidence import VisualEvidenceArtifact

    root = Path(__file__).parents[1]
    return SourceArtifact(
        "visual-mapping/profile",
        canonical_bytes(
            {
                "version": "chandra-mechanical-mapping-v1",
                "parser": chandra_parser_identity(),
                "mapping": inspect.getsource(map_chandra_observation),
                "mapped_schema": VisualEvidenceArtifact.model_json_schema(),
                "files": [
                    (name, (root / name).read_bytes().hex())
                    for name in (
                        "ingest/pdf_chandra.py",
                        "semantic/pdf_visual_mapping.py",
                        "model/semantic/data-operation-visual.yaml",
                    )
                ],
            }
        ),
    )


def visual_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    return PythonSourceCollection(
        tuple(
            PythonSource(module, path.read_bytes(), str(path))
            for module, path in (
                ("corpus_structure.semantic.visual_requests", Path(__file__)),
                (
                    "corpus_structure.ingest.chandra_mapping_operation",
                    root / "ingest/chandra_mapping_operation.py",
                ),
            )
        ),
        boundary_contracts=(visual_mapping_profile(),),
    )


def map_chandra_observation(observation: dict) -> dict:
    """Use the actual incumbent parser/mapper with independent raw and image checks."""
    from PIL import Image

    from corpus_structure.ingest.pdf_chandra import parse_chandra_response

    from .pdf_visual_mapping import map_visual_result

    image = observation["image"]
    pixels, raw = bytes.fromhex(image["content_hex"]), observation["raw_response"].encode()
    if (
        sha256(pixels).hexdigest() != image["content_digest"]
        or sha256(raw).hexdigest() != observation["response_digest"]
    ):
        raise PortRefusal("visual mapping differs from actual submitted/response bytes")
    if len(raw) > _MAX_REPLAY_BYTES:
        raise PortRefusal("Chandra response exceeds the parser byte limit")
    with Image.open(BytesIO(pixels)) as picture:
        if picture.format != "PNG" or picture.size != (image["width"], image["height"]):
            raise PortRefusal("visual dimensions differ from the submitted PNG")
    parsed = parse_chandra_response(
        observation["raw_response"],
        image_size=(image["width"], image["height"]),
        page_no=image["page_no"],
        stop_reason=observation["finish_reason"] or None,
    )
    mapped = (
        None
        if parsed.document is None
        else map_visual_result(
            parsed.document,
            page_no=image["page_no"],
            transform=json.loads(image["transform_json"]),
            image_size=(image["width"], image["height"]),
        ).artifact_bytes()
    )
    return dict(
        observation=observation,
        parse_status=parsed.status.value,
        completion=parsed.completion.value,
        issues=[issue.value for issue in parsed.issues],
        mapped_hex="" if mapped is None else mapped.hex(),
        mapping_outcome="unknown" if mapped is None else "partial" if parsed.issues else "coarse",
        source_fidelity="unassessed",
        diagnostic=parsed.error or "",
    )


@dataclass(frozen=True)
class PreparedVisualMappingPort:
    identity: Any
    model: Any
    operation: Any
    prepared: Any
    authorize: Any
    custody: tuple
    sources: Any
    native_selections = ()

    @property
    def logical_signature(self):
        from corpus_structure.ingest.chandra_mapping_operation import ChandraMappingOperation

        signature = inspect.signature(ChandraMappingOperation.run, eval_str=True)
        return signature.replace(parameters=tuple(signature.parameters.values())[1:])

    def verify(self):
        from corpus_structure.ingest.chandra_mapping_operation import ChandraMappingOperation

        from .data_operation_prepared_products import verify_prepared_product

        if self.operation.semantic_id != VISUAL_MAP or self.operation.effects:
            raise PortRefusal("mapping requires its exact declared pure computation")
        verify_prepared_product(
            self.identity,
            self.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(visual_mapping_profile(),),
            functions=(
                (self.operation.callable_surfaces[0].declaration, ChandraMappingOperation.run),
                (
                    "corpus_structure.semantic.visual_requests.map_chandra_observation",
                    map_chandra_observation,
                ),
            ),
            authorize=self.authorize,
            required_sources=self.sources,
        )

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.method import PreparedWork
        from corpus_structure.ingest.chandra_mapping_operation import ChandraMappingOperation

        self.verify()
        if binding is None or not binding.sufficient or binding.operation != VISUAL_MAP:
            raise PortRefusal("mapping requires its actual sufficient binding")
        ids = {(item.owner, item.domain): item.key for item in self.model.identities}
        incoming = next(role for role in self.operation.roles if role.direction == "input")
        if (
            len(values) != 1
            or values[0].role != "observation"
            or values[0].kind_contract != ids[incoming.kind, "kind"]
        ):
            raise PortRefusal("mapping requires its exact nominal observation")
        observation = self.prepared.validate_json(
            "DdoChandraObservation", json_bytes(_untrusted_value(values[0].value))
        ).model_dump(mode="json")
        if decode_semantic_value(json.loads(binding.parameters)) != {}:
            raise PortRefusal("visual mapping has no caller-authored interpretation settings")

        def compute():
            check_active()
            self.verify()
            body = self.prepared.validate_python(
                "DdoVisualMapping", ChandraMappingOperation().run(observation)
            ).model_dump(mode="python", exclude_unset=True)
            self.verify()
            output = next(role for role in self.operation.roles if role.direction == "output")
            return PortCompletion(
                VISUAL_MAP,
                (
                    RoleValue(
                        output.name,
                        ids[output.kind, "kind"],
                        json_bytes(body),
                        canonical_bytes(semantic_value(body)),
                    ),
                ),
                outcome="success",
            )

        (completion,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        return completion


@dataclass(frozen=True)
class _ExternalClaim:
    task_id: int
    attempt: int
    holder: str
    release_id: str
    deadline: datetime


def _packet_image(read):
    packet = read["packet"]
    if packet["operation_id"] != VISUAL_RECOGNIZE:
        raise PortRefusal("local Chandra cannot execute another external operation")
    views = read["input_views"]
    if len(views) != 1 or views[0]["role"] != "image":
        raise PortRefusal("Chandra requires one exact submitted-image input")
    image = views[0]["value"]
    if packet["original_source"] != image["document"]:
        raise PortRefusal("Chandra image belongs to another original source")
    pixels = bytes.fromhex(image["content_hex"])
    if image["encoding"] != "png" or sha256(pixels).hexdigest() != image["content_digest"]:
        raise PortRefusal("Chandra submitted image differs from the selected packet")
    from PIL import Image

    with Image.open(BytesIO(pixels)) as picture:
        if picture.format != "PNG" or picture.size != (image["width"], image["height"]):
            raise PortRefusal("Chandra dimensions differ from the actual submitted PNG")
    return packet, image, pixels


def _observation(prediction, image, runtime):
    from docling.datamodel.base_models import VlmStopReason

    raw = prediction.text
    stop = prediction.stop_reason
    if stop in {VlmStopReason.INFERENCE_ERROR, VlmStopReason.CONTENT_FILTERED} or not raw.strip():
        outcome = "failed"
    elif stop == VlmStopReason.END_OF_SEQUENCE:
        outcome = "succeeded"
    elif stop in {None, VlmStopReason.UNSPECIFIED}:
        outcome = "unknown"
    else:
        outcome = "partial"
    return dict(
        image=image,
        raw_response=raw,
        response_digest=sha256(raw.encode()).hexdigest(),
        finish_reason=stop.value if stop is not None else "",
        runtime_identity_json=json.dumps(
            runtime.identity(), separators=(",", ":"), allow_nan=False
        ),
        provider_outcome=outcome,
        diagnostic=prediction.error_message or "",
    )


def _retain_visual_result(root, packet, claim, result, *, packet_digest):
    from corpus_structure.ingest.pdf_streaming import _atomic_bytes

    # Each path names an actual native attempt. A new attempt never adopts local
    # output as fresh inference; only native retained-intent reconciliation can do so.
    directory = (
        Path(root)
        / "chandra-native"
        / sha256(packet["packet_id"].encode()).hexdigest()
        / str(claim["attempt"])
    )
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = dict(
        version="chandra-native-attempt-v1",
        packet_id=packet["packet_id"],
        packet_digest=packet_digest,
        packet_bytes_digest=sha256(json_bytes(packet)).hexdigest(),
        fence={
            name: claim[name]
            for name in ("request_id", "generation", "task_id", "attempt", "holder")
        },
        runtime_id=packet["runtime_id"],
        result=result,
    )
    path = directory / "result.json"
    content = json_bytes(record)
    if path.exists() and path.read_bytes() != content:
        raise PortRefusal("immutable Chandra attempt result already differs")
    _atomic_bytes(path, content, "chandra-native-attempt")
    return path


def _read_retained_visual_result(root, packet, claim, *, packet_digest):
    directory = Path(root) / "chandra-native" / sha256(packet["packet_id"].encode()).hexdigest()
    expected = directory / str(claim["attempt"]) / "result.json"
    if not expected.exists():
        previous = tuple(directory.glob("*/result.json"))
        if previous:
            raise PortRefusal(
                "prior Chandra raw output lacks native admission; inspect its original attempt before repeating inference"
            )
        return None
    record = wire_json_loads(expected.read_bytes())
    fence = {
        name: claim[name] for name in ("request_id", "generation", "task_id", "attempt", "holder")
    }
    if (
        record.get("version") != "chandra-native-attempt-v1"
        or record.get("packet_id") != packet["packet_id"]
        or record.get("packet_digest") != packet_digest
        or record.get("packet_bytes_digest") != sha256(json_bytes(packet)).hexdigest()
        or record.get("fence") != fence
        or record.get("runtime_id") != packet["runtime_id"]
    ):
        raise PortRefusal("retained Chandra result differs from its actual packet/attempt")
    return record["result"], expected


class _LocalChandraGroup:
    """Reuse the incumbent supervised child while serial native packet claims own work."""

    def __init__(self, artifacts, endpoint, lifetime):
        self.artifacts, self.endpoint, self.lifetime = artifacts, endpoint, lifetime
        self._runtime = None
        self._child = None
        self._recognize = None
        self._retirement_failure = None

    def runtime(self):
        from corpus_structure.ingest.pdf_chandra import ChandraRuntime

        if self._runtime is None:
            self._runtime = ChandraRuntime(self.artifacts)
            self.lifetime.callback(self._runtime.close)
        return self._runtime

    def recognize(self, pixels, *, check_active, before_submit):
        from corpus_structure.ingest.pdf_capacity import pdf_gpu_slot, suspend_resident_nemotron
        from corpus_structure.ingest.pdf_chandra import ChandraWorkerLost, supervised_chandra

        if self._retirement_failure is not None:
            raise PortRefusal(
                "prior Chandra child retirement is unresolved"
            ) from self._retirement_failure
        runtime = self.runtime()
        if self._child is None:
            self.lifetime.enter_context(pdf_gpu_slot(check_active=check_active))
            self.lifetime.enter_context(
                suspend_resident_nemotron(self.endpoint, check_active=check_active)
            )
            self._child = self.lifetime.enter_context(ExitStack())
        if self._recognize is None:
            self._recognize = self._child.enter_context(supervised_chandra(runtime))
        try:
            return self._recognize(pixels, check_active=check_active, before_submit=before_submit)
        except ChandraWorkerLost as error:
            self._recognize = None
            try:
                self._child.close()
            except BaseException as cleanup:
                from corpus_structure.core.db.store import record_cleanup_failure

                self._retirement_failure = cleanup
                record_cleanup_failure(error, cleanup)
                raise error from cleanup
            raise


def execute_chandra_packet(
    session,
    packet_id: str,
    *,
    artifacts: Path,
    receipts: Path,
    nemotron_endpoint=None,
    lease_seconds=300,
    interval=30,
    group=None,
):
    """Fulfill one actual external packet using the incumbent supervised local actor."""
    from corpus_structure.ingest.pdf_capacity import pdf_gpu_slot, suspend_resident_nemotron
    from corpus_structure.ingest.pdf_chandra import ChandraRuntime, recognize_supervised

    from .claim_lifetime import ClaimFenceLost, maintained_claims
    from .data_operation_storage import DataOperationStorage

    inspected = session.inspect(packet_id)
    if inspected["state"] == "committed":
        return inspected
    claim = session.claim(packet_id, lease_seconds=lease_seconds)
    if claim["state"] != "claimed":
        raise PortRefusal("Chandra requires an actual claimed external packet")
    if claim["action"] == "reconcile":
        return session.reconcile(packet_id, claim)
    read = session.read(packet_id, claim)
    packet, image, pixels = _packet_image(read)
    if packet["packet_id"] != packet_id or read["packet_id"] != packet_id:
        raise PortRefusal("Chandra read belongs to another native packet")
    protocol = packet["protocol"]
    from corpus_structure.ingest.pdf_chandra import CHANDRA_REPOSITORY, CHANDRA_REVISION

    model_assertion = CHANDRA_REPOSITORY + "@" + CHANDRA_REVISION
    if protocol["requested_actor"] != _PROVIDER or protocol["requested_model"] != model_assertion:
        raise PortRefusal("packet does not request the acquired local Chandra actor/model")
    owned = _ExternalClaim(
        claim["task_id"],
        claim["attempt"],
        claim["holder"],
        packet["release_id"],
        datetime.fromisoformat(claim["lease_until"]),
    )

    def renew(conn, current):
        from ._data_operation_wire import WireGeneration, WireRenewDataRequestRequest, WireRequestId

        request = WireRenewDataRequestRequest(
            request_id=WireRequestId(claim["request_id"]),
            generation=WireGeneration(claim["generation"]),
            task_id=TaskId(claim["task_id"]),
            attempt=TaskAttempt(claim["attempt"]),
            holder=claim["holder"],
            lease_seconds=lease_seconds,
        )
        result = DataOperationStorage(conn).renew_data_request(request)
        if result["state"] == "lost":
            raise ClaimFenceLost(current, result["reason"])

    marker, runtime, failure = None, None, None
    try:
        with maintained_claims(
            session.engine, [owned], owned.holder, interval=interval, renew=renew
        ) as owner:

            def active():
                owner.check_claim(owned)

            runtime = ChandraRuntime(artifacts) if group is None else group.runtime()
            try:
                instructions = wire_json_loads(protocol["instructions"])
            except (ValueError, TypeError, KeyError) as error:
                raise PortRefusal("Chandra packet lacks its captured inference policy") from error
            if (
                not isinstance(instructions, dict)
                or instructions.get("version") != "chandra-native-png-v1"
                or instructions.get("policy") != runtime.identity()
            ):
                raise PortRefusal(
                    "local Chandra runtime differs from the packet's frozen inference policy"
                )
            active()
            retained = _read_retained_visual_result(
                receipts, packet, claim, packet_digest=read["packet_digest"]
            )
            if retained is None:
                if group is None:
                    with (
                        pdf_gpu_slot(check_active=active),
                        suspend_resident_nemotron(nemotron_endpoint, check_active=active),
                    ):
                        prediction = recognize_supervised(
                            runtime, pixels, check_active=active, before_submit=active
                        )
                else:
                    prediction = group.recognize(pixels, check_active=active, before_submit=active)
                # Retain the producing attempt's real bytes even if its publication
                # fence was lost while inference was returning.
                result = {
                    "outcome": "success",
                    "outputs": [
                        {"role": "observation", "body": _observation(prediction, image, runtime)}
                    ],
                }
                marker = _retain_visual_result(
                    receipts, packet, claim, result, packet_digest=read["packet_digest"]
                )
            else:
                result, marker = retained
            with owner.lock:
                owner.check_claim(owned)
                submitted = session.submit(
                    packet_id,
                    claim,
                    result,
                    actor_assertion=_PROVIDER,
                    model_assertion=model_assertion,
                )
                if submitted["state"] != "committed":
                    raise PortRefusal("Chandra result has no committed native publication receipt")
                del owner.active[owned.task_id, owned.attempt, owned.holder]
            return submitted
    except BaseException as error:
        failure = error
        if marker is not None:
            error.add_note("actual Chandra attempt output retained at " + str(marker))
        raise
    finally:
        if group is None and runtime is not None:
            try:
                runtime.close()
            except BaseException as cleanup:
                from corpus_structure.core.db.store import record_cleanup_failure

                if failure is not None:
                    record_cleanup_failure(failure, cleanup)
                    raise failure from cleanup
                raise


@dataclass(frozen=True)
class ChandraActorInputs:
    artifacts: Path
    receipts: Path
    nemotron_endpoint: str | None = None


def execute_visual_demand(engine, demand_id, *, visual_actor: ChandraActorInputs, **execution):
    """Advance one retained demand, fulfilling only its actual Chandra packet frontier."""
    from corpus_structure.orchestrate.data_operations import (
        DemandAdvance,
        NativeDemandExecutionError,
    )

    from .data_operation_external import ExternalDataSession
    from .data_operation_service import execute_data_demand, read_data_demand

    with engine.begin() as conn:
        snapshot = read_data_demand(conn, demand_id, limit=1)
    project = snapshot["project_id"]
    if execution.get("project_id") is not None and execution["project_id"] != project:
        raise PortRefusal("visual demand belongs to another project")
    session = ExternalDataSession(engine, project, demand_id=demand_id)
    receipts, count, latest = [], 0, None
    limit = execution.get("limit", 100)

    def observed(result):
        nonlocal count, latest
        latest = result
        count += result.receipt_count
        receipts.extend(result.receipts[: max(0, limit - len(receipts))])
        return DemandAdvance(
            demand_id, result.snapshot, tuple(receipts), count, result.snapshot_standing
        )

    def advance():
        try:
            return observed(execute_data_demand(engine, demand_id, **execution))
        except NativeDemandExecutionError as error:
            raise NativeDemandExecutionError(observed(error.result), error.failures) from error

    try:
        for _ in range(execution.get("max_rounds", 100)):
            result = advance()
            packets = [
                item
                for item in session.queue(limit=4)["packets"]
                if item["operation_id"] == VISUAL_RECOGNIZE
            ]
            if not packets:
                return result
            failures = []
            with ExitStack() as lifetime:
                group = _LocalChandraGroup(
                    visual_actor.artifacts, visual_actor.nemotron_endpoint, lifetime
                )
                for packet in packets:
                    try:
                        submitted = execute_chandra_packet(
                            session,
                            packet["packet_id"],
                            artifacts=visual_actor.artifacts,
                            receipts=visual_actor.receipts,
                            nemotron_endpoint=visual_actor.nemotron_endpoint,
                            group=group,
                        )
                    except Exception as error:
                        failures.append(error)
                    else:
                        count += 1
                        if len(receipts) < limit:
                            receipts.append(json_bytes(submitted))
            if failures:
                with engine.begin() as conn:
                    current = read_data_demand(conn, demand_id, limit=limit)
                raise NativeDemandExecutionError(
                    DemandAdvance(demand_id, json_bytes(current), tuple(receipts), count),
                    tuple(failures),
                )
        # Obtain the current native frontier after the last external completion.
        with engine.begin() as conn:
            current = read_data_demand(conn, demand_id, limit=limit)
        return DemandAdvance(demand_id, json_bytes(current), tuple(receipts), count)
    except NativeDemandExecutionError:
        raise
    except Exception as error:
        if latest is None:
            raise
        result = DemandAdvance(demand_id, latest.snapshot, tuple(receipts), count, "last-pinned")
        raise NativeDemandExecutionError(result, (error,)) from error
