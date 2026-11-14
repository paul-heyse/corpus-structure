"""One static capture/compilation of the actual located-definition recipe, no DB."""

from __future__ import annotations

import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "python/corpus-structure/tests"))

from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.prepare import prepare_release
from semantic.test_native_definition_demand import _captured_definition_recipe


def digest(content):
    return hashlib.sha256(content).hexdigest()


encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def size(value):
    return sum(len(part.encode("utf-8")) for part in encoder.iterencode(value))


def main():
    result = {
        "observed_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "head_before": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version,
        "failure_result": "2950f7ac49574c4a970e491119d89972",
        "recipe": "_captured_definition_recipe",
        "execution": "static acquisition and compilation only; no DB, runtime binding, inference or publication",
    }
    print("capturing actual recipe metadata", file=sys.stderr, flush=True)
    captured = _captured_definition_recipe(Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])).captured_inputs
    assert captured is not None
    result["captured_inputs"] = [
        {"category": category, "name": artifact.name, "bytes": len(artifact.content), "sha256": digest(artifact.content)}
        for category, artifacts in (("source", captured.bundle.sources), ("dependency", captured.dependencies.artifacts))
        for artifact in artifacts
    ]
    (Path(__file__).with_name("inputs.json")).write_text(json.dumps(result, indent=2) + "\n")
    print("compiling one captured model", file=sys.stderr, flush=True)
    prepared = prepare_release(captured.bundle, captured.dependencies, captured.profile)
    model = bound_data_operation_model(prepared)
    print("examining existing serialized model", file=sys.stderr, flush=True)
    content = model.content
    result["model_bytes"] = len(content)
    result["model_sha256"] = digest(content)
    document = json.loads(content)
    result["arrays"] = {name: {"count": len(value), "bytes": size(value)} for name, value in document.items() if isinstance(value, list)}
    del document
    result["largest_kind_facts"] = sorted(({"id": k.semantic_id, "bytes": len(k.facts)} for k in model.kinds), key=lambda v: v["bytes"], reverse=True)[:10]
    result["largest_semantic_nodes"] = sorted(({"id": n.id, "bytes": len(n.payload)} for n in model.nodes), key=lambda v: v["bytes"], reverse=True)[:10]
    result["slices"] = [{"root": s.root, "nodes": len(s.nodes), "payload_bytes": sum(len(n.payload) for n in s.nodes)} for s in model.implementation_slices]
    result["identity_domains"] = {domain: {"count": len(identities), "canonical_input_bytes": sum(len(i.canonical_input) for i in identities)} for domain, identities in _by_domain(model.identities).items()}
    result["largest_identity_inputs"] = sorted(({"owner": i.owner, "domain": i.domain, "bytes": len(i.canonical_input)} for i in model.identities), key=lambda v: v["bytes"], reverse=True)[:15]
    bodies = collections.defaultdict(list)
    for n in model.nodes:
        bodies[digest(n.payload)].append((n.id, len(n.payload)))
    for s in model.implementation_slices:
        for n in s.nodes:
            bodies[digest(n.payload)].append((s.root + " :: " + n.id, len(n.payload)))
    result["repeated_node_payloads"] = sorted(({"sha256": key, "copies": len(items), "bytes_each": items[0][1], "owners": [name for name, _ in items[:4]]} for key, items in bodies.items() if len(items) > 1), key=lambda v: v["copies"] * v["bytes_each"], reverse=True)[:10]
    result["prepared_artifacts"] = [{"kind": a.kind, "bytes": len(a.content), "sha256": digest(a.content)} for a in prepared.artifacts]
    result["head_after"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    Path(__file__).with_name("result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({name: result[name] for name in ("model_bytes", "arrays", "identity_domains", "largest_identity_inputs")}, indent=2))


def _by_domain(identities):
    result = collections.defaultdict(list)
    for identity in identities:
        result[identity.domain].append(identity)
    return result


if __name__ == "__main__":
    main()
