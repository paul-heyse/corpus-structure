"""Rich external source reports, preserving the existing placement/reference kernels."""

from __future__ import annotations

import inspect
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .data_operation_json import json_bytes, wire_json_loads
from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-external-extraction.yaml"
_FILES = (
    "methods/external_extraction.py",
    "semantic/external_extraction.py",
    "semantic/declared_proposal_frames.py",
    "semantic/proposals.py",
    "semantic/declared_record_sources.py",
    "methods/llm/cascade.py",
    "semantic/sentence_products.py",
    "semantic/analysis_contracts.py",
    "semantic/declared_math_products.py",
    "semantic/declared_structural_references.py",
    "semantic/structural_base.py",
    "semantic/observations.py",
    "core/evidence.py",
)
_NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-external-extraction/"
_PACKET = _NAMESPACE + "DdoExternalExtractionPacket"


def external_extraction_inputs(
    bundle,
    dependencies=None,
    *,
    qualification_class="Qualification",
    statement_class="SourceStatement",
):
    """Reuse the release's actual Agent vocabulary and existing declared source pins."""
    import yaml

    from .proposals import proposal_inputs
    from .sentence_products import sentence_product_inputs

    names = {source.name for source in bundle.sources}
    if "data_operation_sentences" not in names:
        bundle = sentence_product_inputs(bundle)
    if "agent" not in names:
        observation_content = next(
            source.content for source in bundle.sources if source.name == "observations"
        )
        options = {
            "qualification_class": qualification_class,
            "statement_class": statement_class,
            "observation_content": observation_content,
        }
        bundle = (
            proposal_inputs(bundle, **options)
            if dependencies is None
            else proposal_inputs(bundle, dependencies, **options)
        )
    name, root = "data_operation_external_extraction", "data_operation_external_extraction_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("rich external schema differs from its captured owner")
        return bundle
    if root in existing:
        raise ValueError("rich external schema root is reserved")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:external-extraction-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def external_extraction_assets():
    from .analysis_contracts import acquire_analysis_context_profile, prepare_placement_policy

    policy = prepare_placement_policy(context_profile=acquire_analysis_context_profile())
    return SourceArtifact(
        "external-extraction/algorithm-assets",
        canonical_bytes(
            {
                "version": "rich-external-placement-1",
                "schema": _MODEL.read_bytes().hex(),
                "placement_policy": asdict(policy),
                "files": [(name, (_ROOT / name).read_bytes().hex()) for name in _FILES],
            }
        ),
    )


def external_extraction_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in _FILES[:2]
        ),
        boundary_contracts=(external_extraction_assets(),),
    )


def rich_external_declarations(protocol):
    """One authored external actor/protocol, with no central agent/method registry."""
    from .data_operation_model import MODEL_VERSION, ExternalExecutorContract

    if not isinstance(protocol, ExternalExecutorContract):
        raise TypeError("rich extraction requires its explicit authored external contract")
    operation = {
        "id": "extract.rich_external",
        "profile": "command",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": ["original-source", "exact-rich-extraction-input"],
        "roles": [
            {
                "name": "packet",
                "kind": _PACKET,
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "subject_field": "/source_pin/subject",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "complete-prepared-packet",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "authored",
                "kind": "https://corpus-structure.dev/semantic/agent/AgentAuthoredBatch",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "dependencies": ["prepare.external_extraction"],
        "parameters": {},
        "applicability": [{'kind': 'documentation', 'text': 'explicit-authored-protocol'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'unlocated-rich-source-report'},
            {'kind': 'documentation', 'text': 'no-knowledge-admission'},
            {'kind': 'documentation', 'text': 'no-protected-evaluator-inputs'},
        ],
        "coverage": "complete-selected-packet",
        "outcomes": ["success"],
        "precision": "authored_source_report",
        "effects": [
            {
                "name": "external-rich-extraction",
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
        "external": asdict(protocol),
        "behavior": "authored rich source extraction; mechanical placement is a separate derivation",
        "binding": {"operator": "scan", "roles": ["packet"]},
        "output_witnesses": [
            {
                "output_role": "authored",
                "records": "",
                "input_role": "packet",
                "comparisons": [
                    {
                        "output_field": "unit_ref",
                        "input": {"role": "packet", "projection": _PACKET, "field": "/unit_ref"},
                        "encoding": "value",
                    }
                ],
            }
        ],
    }
    return SourceArtifact(
        "external-extraction/authored-operation.json",
        canonical_bytes({"version": MODEL_VERSION, "operations": [operation]}),
    )


def _proposal_source(prepared, model, source, annotations, pin):
    from .declared_proposal_frames import DeclaredProposalSource
    from .declared_record_sources import DeclaredNativeFrameSource
    from .proposals import ProposalSentence, native_address
    from .sentence_products import source_annotation_member_values, validate_source_annotations
    from .source_products import FrozenNativeSource

    native = FrozenNativeSource.acquire(prepared, source)
    base = DeclaredNativeFrameSource(native.content.decode(), canonical_bytes(pin).decode())
    checked = validate_source_annotations(prepared, model, annotations, native)
    retained = wire_json_loads(checked.content)
    if any(block["annotation"]["source"] != pin for block in retained["blocks"]):
        raise ValueError(
            "retained sentences differ from the actual selected native source/member context"
        )
    rows = source_annotation_member_values(retained)
    sentences = [
        ProposalSentence(
            row["local_id"],
            native_address(base, start=row["start"], end=row["end"]),
            row["start"],
            row["end"],
        )
        for row in rows
        if row["record_type"] == "sentence"
    ]
    sentences.extend(
        ProposalSentence(
            "native_evidence:" + str(index),
            native_address(base, start=piece["start"], end=piece["end"]),
            piece["start"],
            piece["end"],
        )
        for index, piece in enumerate(base.pieces)
        if piece["kind"] == "native_text"
        and piece.get("item_ref")
        and base.contains_span(piece["start"], piece["end"])
    )
    return DeclaredProposalSource(
        base.source_content, base.pin_content, sentence_values=tuple(sentences)
    )


def prepare_external_packet(prepared, model, values, source_pins, *, check_active):
    from corpus_structure.core.evidence import MACRO_NAME, MacroDef

    from .declared_proposal_frames import DeclaredProposalFrame
    from .observations import source_python, source_value
    from .proposals import MAX_KNOWN, KnownProposalEntity

    policy = prepared.validate_json(
        "DdoExternalExtractionPolicy", json_bytes(values["policy"])
    ).model_dump(mode="python", exclude_unset=True)
    known = source_python(policy["known_classes"])
    macros = source_python(policy["macros"])
    if not isinstance(known, dict) or not isinstance(macros, dict) or len(known) > MAX_KNOWN:
        raise ValueError("rich context requires explicit bounded known-class and macro mappings")
    if any(
        not isinstance(iris, list) or not iris or len(set(iris)) != len(iris)
        for iris in known.values()
    ):
        raise ValueError("authored known references require explicit nonempty class-IRI sets")
    classes = {definition.iri for definition in prepared.definitions}
    if any(iri not in classes for iris in known.values() for iri in iris):
        raise ValueError("authored known reference class is outside the effective release")
    entities = tuple(
        KnownProposalEntity(row["entity_id"], row["label"], tuple(row["aliases"]))
        for row in policy["known_entities"]
    )
    if (
        len(entities) > MAX_KNOWN
        or len({entity.entity_id for entity in entities}) != len(entities)
        or {entity.entity_id for entity in entities} - known.keys()
    ):
        raise ValueError(
            "authored entity labels/aliases require distinct explicitly supplied class references"
        )
    parsed_macros = {name: MacroDef.model_validate(value) for name, value in macros.items()}
    if any(re.fullmatch(MACRO_NAME, name) is None for name in parsed_macros):
        raise ValueError("macro context requires actual control-word names")
    check_active()
    primary = _proposal_source(
        prepared, model, values["source"], values["annotations"], source_pins["source"][0]
    )
    contexts = []
    available = {}
    for value, pin in zip(values["context_sources"], source_pins["context_sources"], strict=True):
        key = canonical_bytes([value["source"], value["selectors"]])
        if key in available:
            raise ValueError("context source coordinate is ambiguous among supplied native inputs")
        available[key] = (value, pin)
    annotation_index = {}
    for annotation in values["context_annotations"]:
        key = canonical_bytes([annotation["source"], annotation["selectors"]])
        if key in annotation_index:
            raise ValueError("context annotation coordinate is ambiguous")
        annotation_index[key] = annotation
    requested = policy["context_sources"]
    if len(set(requested)) != len(requested):
        raise ValueError("context policy repeats a separately pinned native source")
    by_reference = {pin["source"]: (value, pin) for value, pin in available.values()}
    for reference in requested:
        check_active()
        if reference not in by_reference:
            raise ValueError("explicit ancestor source is unavailable among admitted inputs")
        value, pin = by_reference[reference]
        annotation = annotation_index.get(canonical_bytes([value["source"], value["selectors"]]))
        if annotation is None:
            raise ValueError("explicit ancestor lacks its separately admitted retained sentences")
        contexts.append(_proposal_source(prepared, model, value, annotation, pin))
    frame = DeclaredProposalFrame(
        primary.source_content,
        primary.pin_content,
        sentence_values=primary.sentences,
        context_sources=tuple(contexts),
    )
    scopes = values["scopes"]
    if (policy["scope_standing"] == "explicitly-none") != (not scopes):
        raise ValueError("scope context standing differs from actual supplied scope products")
    observations = []
    if scopes:
        from .declared_math_products import DeclaredMathScopeProduct

        frame_pins = [source.pin.values() for source in (frame, *frame.context_sources)]
        for value in scopes:
            check_active()
            scope = DeclaredMathScopeProduct.model_validate(value)
            if not any(scope.source.matches_pin(pin) for pin in frame_pins):
                raise ValueError("mathematical scope belongs to an unselected source frame")
            observations.append(scope.model_dump(mode="json", exclude_none=True))
    return {
        "version": "external-extraction-input-1",
        "unit_ref": frame.unit_ref,
        "source_pin": frame.pin.values(),
        "frame": source_value(frame.record),
        "guideline": policy["guideline"],
        "known_reference_standing": "authored",
        "known_classes": policy["known_classes"],
        "known_entities": policy["known_entities"],
        "bootstrap_terms": policy["bootstrap_terms"],
        "macros": policy["macros"],
        "native_observations": source_value(observations),
        "scope_standing": policy["scope_standing"],
    }


def external_extraction_prompt(packet):
    """Derive a readable view once; retain only the exact original frame in the product."""
    from .declared_proposal_frames import declared_proposal_frame_from_dict
    from .observations import source_python
    from .proposals import native_evidence_entries, native_frame_entries

    frame = declared_proposal_frame_from_dict(source_python(packet["frame"]))
    entries = native_frame_entries(frame)
    aliases = {
        id(source): {entry["handle"]: entry for entry in native_evidence_entries(source)}
        for source in (frame, *frame.context_sources)
    }
    return {
        "unit_ref": frame.unit_ref,
        "source_pin": frame.pin.values(),
        "text": frame.text,
        "context": wire_json_loads(frame.native_context),
        "guideline": packet["guideline"],
        "sentences": [
            {
                "id": handle,
                "locator": sentence.locator,
                "text": source.text[sentence.start : sentence.end],
            }
            for handle, (source, sentence) in entries.items()
            if not sentence.id.startswith("native_evidence:")
        ],
        "native_evidence": [
            dict(aliases[id(source)][sentence.id], handle=handle)
            for handle, (source, sentence) in entries.items()
            if sentence.id.startswith("native_evidence:")
        ],
        "known_classes": source_python(packet["known_classes"]),
        "known_entities": packet["known_entities"],
        "known_reference_standing": packet["known_reference_standing"],
        "bootstrap_terms": packet["bootstrap_terms"],
        "macros": source_python(packet["macros"]),
        "native_observations": source_python(packet["native_observations"]),
        "scope_standing": packet["scope_standing"],
    }


def locate_external_extraction(prepared, packet, authored, *, placement_policy, check_active):
    from corpus_structure.core.evidence import MacroDef

    from .declared_proposal_frames import declared_proposal_frame_from_dict
    from .observations import source_python, source_value
    from .proposals import locate_proposal

    packet = prepared.validate_json("DdoExternalExtractionPacket", json_bytes(packet)).model_dump(
        mode="python", exclude_unset=True
    )
    frame = declared_proposal_frame_from_dict(source_python(packet["frame"]))
    if frame.pin.values() != packet["source_pin"] or frame.unit_ref != packet["unit_ref"]:
        raise ValueError("rich placement packet changed its selected source frame")
    check_active()
    located = locate_proposal(
        prepared,
        authored,
        frame,
        macros={
            name: MacroDef.model_validate(value)
            for name, value in source_python(packet["macros"]).items()
        },
        known_classes={
            key: tuple(iris) for key, iris in source_python(packet["known_classes"]).items()
        },
        placement_policy=placement_policy,
    )
    check_active()
    return {
        "version": "located-external-extraction-1",
        "unit_ref": frame.unit_ref,
        "source_pin": frame.pin.values(),
        "standing": "unselected_source_report",
        "authored": located.authored.model_dump(mode="python", exclude_unset=True),
        "stored": located.stored.model_dump(mode="python", exclude_unset=True),
        "issues": source_value([asdict(issue) for issue in located.issues]),
        "known_reference_standing": "authored",
    }


def located_external_batch(prepared, value):
    """Immediate target consumer: retain all rich fields and placement diagnostics."""
    from .observations import source_python

    checked = prepared.validate_json("DdoLocatedExternalExtraction", json_bytes(value))
    return (checked.stored, tuple(source_python(checked.issues.model_dump(mode="python"))))


def execute_rich_profile(receiver, values):
    return receiver.execute(values)


def execute_rich_kernel(
    action: str, values: dict, source_pins: dict, placement_policy: dict, *, prepared, check_active
) -> dict:
    from .data_operation_admission import bound_data_operation_model

    if action == "prepare.external_extraction":
        return prepare_external_packet(
            prepared,
            bound_data_operation_model(prepared),
            values,
            source_pins,
            check_active=check_active,
        )
    if action == "locate.external_extraction":
        from corpus_structure.methods.llm.cascade import PlacementPolicy

        return locate_external_extraction(
            prepared,
            values["packet"],
            values["authored"],
            placement_policy=PlacementPolicy(**placement_policy),
            check_active=check_active,
        )
    raise ValueError("unknown captured rich extraction kernel")


@dataclass
class RichInvocationPlan:
    prepared: Any
    model: Any
    operation: str
    placement_policy: dict
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_prepared_call import PreparedCallResult
        from .declared_record_sources import DeclaredRecordSource
        from .source_products import FrozenNativeSource

        if binding is None or binding.subject_context is None:
            raise ValueError("rich extraction requires actual native input/context custody")
        source_pins = {}
        values = arguments.arguments
        if self.operation == "prepare.external_extraction":
            roles = {role.name: role for role in binding.roles}
            for role in ("source", "context_sources"):
                bodies = (values[role],) if role == "source" else values[role]
                source_pins[role] = [
                    DeclaredRecordSource.from_bound(
                        FrozenNativeSource.acquire(self.prepared, body),
                        member,
                        project=binding.subject_context.project_id,
                    ).pin()
                    for body, member in zip(bodies, roles[role].members, strict=True)
                ]
        signature = inspect.signature(execute_rich_kernel, eval_str=True)
        bound = signature.bind(
            action=self.operation,
            values=values,
            source_pins=source_pins,
            placement_policy=self.placement_policy,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = external_extraction_operation_sources()
        reply = yield from self.port.plan_cpu_reply(
            execute_rich_kernel,
            bound,
            captured,
            prepared_release_id=self.prepared.release_id,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        return PreparedCallResult(
            wire_json_loads(reply.content),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )


def resolve_rich_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.external_extraction import (
        RichExtractionInputOperation,
        RichExtractionPlacementOperation,
    )

    from .data_operation_prepared_call import PreparedOriginalCallPort

    owners = {
        RichExtractionInputOperation.__data_operation__["id"]: RichExtractionInputOperation,
        RichExtractionPlacementOperation.__data_operation__["id"]: RichExtractionPlacementOperation,
    }
    if operation not in owners:
        raise ValueError("rich prepared capability belongs to another declared owner")
    receiver = owners[operation](None)
    artifacts = [
        artifact for artifact in custody if artifact.name == "external-extraction/algorithm-assets"
    ]
    if len(artifacts) != 1:
        raise ValueError("rich acquisition requires its exact captured placement policy")
    plan = RichInvocationPlan(
        prepared, model, operation, wire_json_loads(artifacts[0].content)["placement_policy"]
    )
    port = PreparedOriginalCallPort(
        identity,
        model,
        model.operation(operation),
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.external_extraction.RichInvocationPlan.plan",
        authorize,
        (external_extraction_assets(),),
        external_extraction_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.external_extraction.execute_rich_kernel",
                execute_rich_kernel,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
