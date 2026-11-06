"""Recheck the frozen current bundle inventory, offline, after coordinator GO.

Running without --execute performs metadata preparation checks only. This script
does not create bundles, open a database, or call a model/provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

INVENTORY_SHA256 = "38438d93637208c66cf7562a508ecaa60f89b69c40d079a4e5dcdf50a220b898"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Coordinator GO received")
    parser.add_argument("--attempt", default="001")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.attempt):
        parser.error("attempt must contain only letters, numbers, underscores or hyphens")

    directory = Path(__file__).resolve().parent
    inventory_path = directory / "bundle-reverify-inventory.json"
    if digest(inventory_path) != INVENTORY_SHA256:
        raise ValueError("frozen inventory hash differs")
    inventory = json.loads(inventory_path.read_bytes())
    repo = next(parent for parent in directory.parents if (parent / "pyproject.toml").is_file())
    base = repo / inventory["evidence_root"]
    source = repo / inventory["verifier_source"]["path"]
    source_sha = inventory["verifier_source"]["sha256"]
    if digest(source) != source_sha:
        raise ValueError("final verifier source hash differs before execution")
    for entry in inventory["bundles"]:
        if digest(base / entry["manifest_path"]) != entry["manifest_sha256"]:
            raise ValueError(f"frozen manifest differs: {entry['id']}")
        for receipt in entry["prior_success_receipts"]:
            if digest(base / receipt["path"]) != receipt["sha256"]:
                raise ValueError(f"prior success receipt differs: {receipt['path']}")
    if not args.execute:
        print(json.dumps({"outcome": "not_run", "reason": "awaiting coordinator GO", "prepared_bundles": len(inventory["bundles"]), "verifier_source_sha256": source_sha}))
        return 0

    # Import only after explicit execution; call the ordinary offline verifier once
    # per bundle. Its returned manifest is the retained result, not a second export.
    from corpus_structure.serve.review_bundle import verify_review_bundle

    prefix = directory / f"bundle-reverify-run{args.attempt}"
    progress_path = prefix.with_suffix(".jsonl")
    result_path = prefix.with_suffix(".json")
    if result_path.exists():
        raise FileExistsError(result_path)
    progress = progress_path.open("x", buffering=1)
    started = now()
    results = []
    interrupted = False
    try:
        for entry in inventory["bundles"]:
            result = {"id": entry["id"], "path": entry["path"], "manifest_sha256": entry["manifest_sha256"], "verifier_source_sha256": source_sha, "started_at": now()}
            began = time.monotonic()
            try:
                if digest(source) != source_sha:
                    raise ValueError("final verifier source changed")
                manifest_path = base / entry["manifest_path"]
                if digest(manifest_path) != entry["manifest_sha256"]:
                    raise ValueError("manifest changed before verification")
                manifest = verify_review_bundle(base / entry["path"])
                if digest(source) != source_sha or digest(manifest_path) != entry["manifest_sha256"]:
                    raise ValueError("verifier source or manifest changed during verification")
                counts = {key: value["rows"] for key, value in manifest["relations"].items()}
                if counts != entry["declared_relation_rows"] or manifest["selection"] != entry["selection"]:
                    raise ValueError("verified selection or declared relation counts differ from inventory")
                result.update(outcome="passed", relations=counts, selection_digest=manifest["selection_digest"])
            except (Exception, KeyboardInterrupt) as error:
                interrupted = isinstance(error, KeyboardInterrupt)
                failure_path = directory / f"{prefix.name}-{entry['id']}-failure.txt"
                with failure_path.open("x") as failure:
                    traceback.print_exc(file=failure)
                result.update(outcome="interrupted" if interrupted else "failed", error_type=type(error).__name__, error=str(error), failure_path=failure_path.name)
            result.update(finished_at=now(), elapsed_seconds=time.monotonic() - began)
            results.append(result)
            progress.write(json.dumps(result, sort_keys=True) + "\n")
            progress.flush()
            print(json.dumps({"id": result["id"], "outcome": result["outcome"], "completed": len(results), "total": inventory["bundle_count"]}), flush=True)
            if interrupted:
                break
    finally:
        progress.close()
        all_passed = len(results) == inventory["bundle_count"] and all(result["outcome"] == "passed" for result in results)
        source_unchanged = digest(source) == source_sha
        output = {"protocol": "wce-gs120-final-source-bundle-reverify-1", "outcome": "passed" if all_passed and source_unchanged else "interrupted" if interrupted else "failed", "started_at": started, "finished_at": now(), "command": ["uv", "run", "python", str(Path(__file__).resolve().relative_to(repo)), "--execute", "--attempt", args.attempt], "repository_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(), "inventory_path": inventory_path.name, "inventory_sha256": INVENTORY_SHA256, "script_sha256": digest(Path(__file__)), "verifier_source": inventory["verifier_source"], "verifier_source_unchanged_after": source_unchanged, "requested_bundles": inventory["bundle_count"], "completed_bundles": len(results), "passed_bundles": sum(result["outcome"] == "passed" for result in results), "not_run": [entry["id"] for entry in inventory["bundles"][len(results):]], "results": results, "progress_sha256": digest(progress_path), "database_access": "not_run", "provider_access": "not_run", "bundle_mutation": "not_run", "limits_of_claim": inventory["limits_of_claim"]}
        with result_path.open("x") as target:
            json.dump(output, target, indent=2)
            target.write("\n")
        print(json.dumps({"result": str(result_path.relative_to(repo)), "sha256": digest(result_path), "outcome": output["outcome"]}), flush=True)
    return 0 if output["outcome"] == "passed" else 130 if interrupted else 1


if __name__ == "__main__":
    sys.exit(main())
