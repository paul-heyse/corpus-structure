"""Release-owned request and window identity for located GLiNER observations."""

import json
from decimal import Decimal
from functools import cache
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.value_codec import decimal_text

from .gliner import GlinerPack, _json

MODEL_OBSERVATION_INPUT = "execution/implementation/operations/model-observation.json"


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


def request_digest(pack, profile, inputs, threshold, overlap, evaluation, inference):
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


def observation_digest(request, raw_json, effective_json):
    return sha256(canonical_bytes([request, raw_json, effective_json])).hexdigest()
