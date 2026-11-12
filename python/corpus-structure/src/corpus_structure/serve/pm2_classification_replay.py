"""Check a managed classification against captured source, release and raw model custody."""

from __future__ import annotations

import base64
import json
from hashlib import sha256

from corpus_structure.methods.pm2_gliner_classification import (
    FAMILY,
    METHOD,
    VERSION,
    ClassificationProfile,
    classification_mapping,
    classification_product,
    classification_request,
    profile_digest,
    require_classification_request,
)
from corpus_structure.methods.pm2_result import pm2_input_digest
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    compile_question_families,
    declared_families,
    is_question_input,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import PreparedNativeSources, record_source_pin
from corpus_structure.semantic.types import SourceArtifact

from .model_observation_replay import _policy


def _released_family(contract):
    manifest = base64.b64decode(
        contract["model_observation_policy"]["manifest_base64"], validate=True
    )
    dependencies = dict(json.loads(manifest)["dependencies"])
    inputs = contract.get("interpretation_question_inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        name for name in dependencies if is_question_input(name)
    }:
        raise ValueError("classification question inputs differ from the exact release")
    artifacts = tuple(
        SourceArtifact(name, base64.b64decode(encoded, validate=True))
        for name, encoded in inputs.items()
    )
    if any(artifact.digest != dependencies[artifact.name] for artifact in artifacts):
        raise ValueError("classification question input digest differs from the exact release")
    family = declared_families(compile_question_families(artifacts)).get(FAMILY)
    if family is None:
        raise ValueError("classification question is absent from the exact release")
    return family


def verify_classification_replay(raw, row, view, contract):
    body = raw["body"]
    value = source_python(row["value"])
    native = source_python(body["parse_detail"])["pm2_native"]
    profile = ClassificationProfile.model_validate(raw["configuration"])
    config_hash = profile_digest(profile)
    source = native_source_frame(view, ())
    pin = record_source_pin(source)
    extent = value["assessed_scope"]["projection_extent"]
    if (
        (raw["method"], body["method"], body["operation_version"])
        != (METHOD, METHOD, body["operation_version"])
        or body["operation_version"] not in {"1", VERSION}
        or body["outcome"] != "produced"
        or body["release_id"] != contract["release_id"]
        or raw["origin_unit_id"] != source.source_view_id
        or body["source"] != source.unit_ref
        or raw["config_hash"] != config_hash
        or body["configuration_hash"] != config_hash
        or native["effective_profile_digest"] != config_hash
        or row["pin"] != pin
        or not isinstance(extent, list)
        or len(extent) != 2
        or any(type(bound) is not int for bound in extent)
    ):
        raise ValueError("classification differs from its exact producer, profile or source")
    mapping = classification_mapping(
        source, (extent[0], extent[1]), PreparedNativeSources((source,))
    )
    policy = _policy(contract)
    request = classification_request(
        contract["release_id"],
        _released_family(contract),
        value["question_key"],
        mapping,
        profile,
        policy["inference"],
        operation_version=body["operation_version"],
    )
    require_classification_request(native["request"], request)
    if native["native"]["outcome"] != "succeeded":
        raise ValueError("classification product lacks a successful raw observation")
    product = classification_product(
        request, native["native"]["gliner"], profile, request_version=policy["request_version"]
    )
    input_hash = pm2_input_digest(
        mapping,
        profile.startup,
        request,
        question=FAMILY,
        operation_version=body["operation_version"],
    )
    operation = operation_identity(FAMILY, body["operation_version"], source.unit_ref, input_hash)
    if (
        raw["input_hash"] != input_hash
        or body["input_hash"] != input_hash
        or native["input_digest"] != input_hash
        or native["scope_digest"] != mapping.scope_digest
        or native["source_map_digest"] != mapping.input_digest
        or native["authorized_source_path"] is not None
        or native["locations"]
        or row.get("anchors")
        or row.get("members")
        or row["operation_key"] != operation
        or row["semantic_type"] != product.semantic_type
        or row["item_key"] != product.key
        or row["kind"] != "proposal"
        or canonical_bytes(value)
        != canonical_bytes({**product.value, "location_keys": [], "unlocated_members": []})
        or len(body["contribution_operations"]) != 1
    ):
        raise ValueError("classification product differs from the replayed raw observation")
    (reported,) = body["contribution_operations"]
    if (
        (
            reported["operation_key"],
            reported["question"],
            reported["operation_version"],
            reported["outcome"],
        )
        != (operation, FAMILY, body["operation_version"], "succeeded")
        or reported["report_digest"] != sha256(canonical_bytes(native)).hexdigest()
        or reported["computation_dependencies"] != [input_hash]
    ):
        raise ValueError("classification differs from the exact producing operation")
