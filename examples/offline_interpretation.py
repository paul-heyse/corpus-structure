"""Independent offline structural preflight. Requires jsonschema4.26/referencing0.37.

Run: python offline_interpretation.py PACKAGE INSTANCE [--expected-digest SHA256]
No corpus_structure import, database, remote resolution or semantic admission occurs.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from itertools import islice
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

MAX_INPUT_BYTES = 4 * 1024**2
MAX_SCHEMA_BYTES = 8 * 1024**2
MAX_REPORT_BYTES = 1024**2


def bounded_read(path, maximum):
    with path.open("rb") as stream:
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("portable input exceeds byte limit")
    return content


DIALECT = "https://json-schema.org/draft/2020-12/schema"


def preflight(package: Path, instance, expected_digest=None):
    content = bounded_read(package / "manifest.json", 65536)
    if expected_digest is not None and sha256(content).hexdigest() != expected_digest:
        raise ValueError("package manifest digest differs")
    manifest = json.loads(content)
    if (
        type(manifest["version"]) is not int
        or manifest["version"] != 1
        or manifest["mode"] != "validation"
        or manifest["dialect"] != DIALECT
        or manifest["entry"] != "schema.json"
    ):
        raise ValueError("unsupported portable contract profile")
    content = bounded_read(package / "schema.json", MAX_SCHEMA_BYTES)
    if sha256(content).hexdigest() != manifest["schema_digest"]:
        raise ValueError("retained schema digest differs")
    schema = json.loads(content)
    if schema.get("$schema", DIALECT) != DIALECT:
        raise ValueError("unsupported schema dialect")

    def admit(node):
        if isinstance(node, dict):
            if "$dynamicRef" in node:
                raise ValueError("unsupported dynamic reference")
            if "$vocabulary" in node and any(node["$vocabulary"].values()):
                raise ValueError("required custom vocabulary outside profile")
            if "$ref" in node and not node["$ref"].startswith("#"):
                raise ValueError("missing offline resource")
            for value in node.values():
                admit(value)
        elif isinstance(node, list):
            for value in node:
                admit(value)

    admit(schema)
    Draft202012Validator.check_schema(schema)
    resource = Resource.from_contents(schema, default_specification=DRAFT202012)
    registry = Registry().with_resource("urn:portable:entry", resource).crawl()

    # Resolve references before instance validation, including unused union branches.
    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                registry.resolver("urn:portable:entry").lookup(node["$ref"])
            for value in node.values():
                resolve(value)
        elif isinstance(node, list):
            for value in node:
                resolve(value)

    resolve(schema)
    validator = Draft202012Validator(schema, registry=registry)
    errors = list(islice(validator.iter_errors(instance), 101))
    inventory_complete = len(errors) <= 100
    remaining_nodes = 1000

    def view(error, depth=0):
        nonlocal remaining_nodes
        remaining_nodes -= 1
        children = []
        if depth < 8:
            for child in error.context[:50]:
                if remaining_nodes <= 0:
                    break
                children.append(view(child, depth + 1))
        return dict(
            instance_path=list(error.absolute_path),
            schema_path=list(error.absolute_schema_path),
            keyword=error.validator,
            causes=children,
            detail_complete=len(children) == len(error.context),
        )

    details = []
    for error in errors[:100]:
        if remaining_nodes <= 0:
            break
        details.append(view(error))

    def rendered_completely(node):
        return node["detail_complete"] and all(
            rendered_completely(child) for child in node["causes"]
        )

    result = dict(
        outcome="failed" if errors else "passed",
        claim="structural_preflight_only",
        release_id=manifest["release_id"],
        errors=details,
        inventory_complete=inventory_complete,
        complete=inventory_complete
        and remaining_nodes > 0
        and all(rendered_completely(node) for node in details),
        limitations=manifest["limitations"],
    )
    while len(json.dumps(result).encode()) > MAX_REPORT_BYTES and result["errors"]:
        result["errors"].pop()
        result["complete"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("instance", type=Path)
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    result = preflight(
        args.package, json.loads(bounded_read(args.instance, MAX_INPUT_BYTES)), args.expected_digest
    )
    print(json.dumps(result))
    return 0 if result["outcome"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
