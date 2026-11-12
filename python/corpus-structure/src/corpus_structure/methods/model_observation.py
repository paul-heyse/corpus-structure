"""Release-owned request and window identity for located GLiNER observations."""

import json
from decimal import Decimal
from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Any, TypedDict

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.value_codec import decimal_text

from .gliner import GlinerPack, _json

MODEL_OBSERVATION_INPUT = "execution/implementation/operations/model-observation.json"
PRIVATE_DECLARATION_INPUT = "operation/pm2-definition-policy.json"
PRIVATE_DECLARATION_POLICY = {
    "scope": "private_development",
    "hanlp_layout_policy": "source-seam-continuation-1",
    "definition_declaration_chain": "definition-declaration-chain-1",
}


def private_declaration_enabled(manifest: bytes) -> bool:
    """Authorize a private staged release input; ordinary pack releases omit it."""
    matches = [
        digest
        for name, digest in json.loads(manifest).get("dependencies", ())
        if name == PRIVATE_DECLARATION_INPUT
        or (name.startswith("pack/") and name.endswith("/" + PRIVATE_DECLARATION_INPUT))
    ]
    return matches == [sha256(canonical_bytes(PRIVATE_DECLARATION_POLICY)).hexdigest()]


@cache
def installed_policy():
    content = Path(__file__).with_name("model_observation.json").read_bytes()
    return json.loads(content), sha256(content).hexdigest()


def released_policy(prepared):
    policy, actual = installed_policy()
    # Real prepared releases always supply the authenticated manifest.
    if dict(json.loads(prepared.manifest)["dependencies"]).get(MODEL_OBSERVATION_INPUT) != actual:
        raise ValueError("installed model observation policy differs from the selected release")
    return policy


def released_pack(release, policy, *, config=None):
    if config is None:
        return GlinerPack(release, policy["clause"], "native-combined-v2")
    declaration = "".join(
        _json(config[part["field"]]) if isinstance(part, dict) else part
        for part in policy["definition"][config["description_arm"]]
    )
    return GlinerPack(release, declaration, "native-local-v1")


def legacy_request_digest(pack, profile, inputs, threshold, overlap, evaluation, inference):
    values = {
        key: value for key, value in profile.items() if key not in {"snapshot", "artifact_hashes"}
    }
    values["timeout_seconds"] = decimal_text(Decimal(str(values["timeout_seconds"])))
    values["artifact_hashes"] = sorted(profile["artifact_hashes"])
    return sha256(
        canonical_bytes(
            [
                "located-model-request-1",
                pack.release,
                pack.version,
                pack.declaration_json,
                values,
                [
                    [item.operation, item.context_id, item.context_digest, item.text]
                    for item in inputs
                ],
                decimal_text(Decimal(str(threshold))),
                overlap,
                evaluation,
                inference,
            ]
        )
    ).hexdigest()


class BatchReceipt(TypedDict):
    version: int
    header: dict[str, Any]
    members: list[str]
    digest: str


def member_request_digest(item):
    """Commit the exact member, including text; equal strings do not merge contexts."""
    return sha256(
        canonical_bytes(
            [
                "located-model-member-2",
                item.operation,
                item.context_id,
                item.context_digest,
                item.text,
            ]
        )
    ).hexdigest()


def batch_receipt(pack, profile, inputs, threshold, overlap, evaluation, inference) -> BatchReceipt:
    values = {
        key: value for key, value in profile.items() if key not in {"snapshot", "artifact_hashes"}
    }
    values["timeout_seconds"] = decimal_text(Decimal(str(values["timeout_seconds"])))
    values["artifact_hashes"] = sorted(profile["artifact_hashes"])
    header = dict(
        release=pack.release,
        version=pack.version,
        declaration=pack.declaration_json,
        profile=values,
        threshold=decimal_text(Decimal(str(threshold))),
        overlap=overlap,
        evaluation=evaluation,
        inference=inference,
    )
    members = [member_request_digest(item) for item in inputs]
    return dict(version=2, header=header, members=members, digest=batch_digest(header, members))


def batch_digest(header, members):
    return sha256(canonical_bytes(["located-model-request-2", header, members])).hexdigest()


def request_digest(pack, profile, inputs, threshold, overlap, evaluation, inference):
    return batch_receipt(pack, profile, inputs, threshold, overlap, evaluation, inference)["digest"]


def observation_digest(request, raw_json, effective_json, *, ordinal=None, member=None):
    if ordinal is None and member is None:
        # Read-only historical receipt semantics, also used by unversioned diagnostics.
        value = [request, raw_json, effective_json]
    else:
        if type(ordinal) is not int or ordinal < 0 or not isinstance(member, str):
            raise ValueError("batch observation requires its exact member ordinal and digest")
        value = ["located-model-observation-2", request, ordinal, member, raw_json, effective_json]
    return sha256(canonical_bytes(value)).hexdigest()


def report_observation_digest(report, *, request_version="located-model-request-2"):
    """Validate the retained batch commitment before verifying its observation binding."""
    receipt_json = report.get("batch_receipt_json")
    ordinal = report.get("member_ordinal")
    if request_version not in {"located-model-request-1", "located-model-request-2"}:
        raise ValueError("unsupported observation request version")
    if receipt_json is None:
        if request_version != "located-model-request-1":
            raise ValueError("current observation requires its batch receipt")
        if ordinal is not None:
            raise ValueError("unversioned observation has a batch ordinal")
        return observation_digest(
            report["request_digest"], report["raw_json"], report["effective_profile_json"]
        )
    if request_version != "located-model-request-2":
        raise ValueError("historical observation cannot acquire batch provenance")
    receipt = json.loads(receipt_json)
    if not isinstance(receipt, dict) or set(receipt) != {"version", "header", "members", "digest"}:
        raise ValueError("unsupported batch receipt")
    members = receipt["members"]
    if (
        receipt["version"] != 2
        or not isinstance(members, list)
        or not members
        or type(ordinal) is not int
        or not 0 <= ordinal < len(members)
        or any(
            not isinstance(item, str)
            or len(item) != 64
            or any(c not in "0123456789abcdef" for c in item)
            for item in members
        )
        or len(set(members)) != len(members)
        or batch_digest(receipt["header"], members) != receipt["digest"]
        or receipt["digest"] != report["request_digest"]
    ):
        raise ValueError("observation batch commitment or ordinal differs")
    return observation_digest(
        report["request_digest"],
        report["raw_json"],
        report["effective_profile_json"],
        ordinal=ordinal,
        member=members[ordinal],
    )


def validate_pm2_batch_receipt(receipt, payload, provider):
    """Verify a retained member's exact request and the admitted cohort commitment."""
    if not isinstance(receipt, dict) or set(receipt) != {
        "version",
        "header",
        "members",
        "digest",
        "member_ordinal",
    }:
        raise ValueError("native batch member receipt shape differs")
    header, members, ordinal = receipt["header"], receipt["members"], receipt["member_ordinal"]
    if (
        receipt["version"] != 1
        or not isinstance(header, dict)
        or set(header) != {"provider", "profile", "runtime"}
        or header["provider"] != provider
        or any(
            not isinstance(header[key], str)
            or len(header[key]) != 64
            or any(c not in "0123456789abcdef" for c in header[key])
            for key in ("profile", "runtime")
        )
        or not isinstance(members, list)
        or not members
        or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
            for value in members
        )
        or type(ordinal) is not int
        or not 0 <= ordinal < len(members)
        or members[ordinal] != sha256(canonical_bytes(payload)).hexdigest()
        or receipt["digest"] != sha256(canonical_bytes([header, members])).hexdigest()
    ):
        raise ValueError("native batch member differs from its exact request/cohort")
