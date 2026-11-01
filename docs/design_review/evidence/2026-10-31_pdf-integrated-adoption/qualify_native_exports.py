"""Actual CLI exports, detached native roundtrip, and exact integrated inventory custody."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from hashlib import file_digest, sha256
from pathlib import Path


def canonical(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def qualify(selection: dict, database: str, root: Path, output: Path) -> None:
    output.mkdir()
    receipts = []
    partial = output / "partial.json"

    def checkpoint() -> None:
        partial.write_text(
            json.dumps(
                {"outcome": "partial", "selection": selection, "calls": receipts},
                indent=2,
            )
            + "\n"
        )

    def export(
        format: str, filename: str, *, section: bool = False, wrong_pin: bool = False
    ) -> Path:
        destination = output / filename
        args = [
            str(root / ".venv/bin/ci"),
            "source",
            "native-export",
            str(selection["run_id"]),
            str(selection["task_id"]),
            selection["product_key"],
            "0" * 64 if wrong_pin else selection["content_digest"],
            str(destination),
            "--format",
            format,
        ]
        if section:
            args.extend(
                [
                    "--section",
                    selection["section_pointer"],
                    "--membership",
                    selection["membership"],
                ]
            )
        env = dict(
            os.environ,
            CORPUS_DATABASE__URL=database,
            PYTHONPATH=str(root / "python/corpus-structure/src"),
        )
        result = subprocess.run(
            args,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        (output / (filename + ".stdout.log")).write_text(result.stdout)
        (output / (filename + ".stderr.log")).write_text(result.stderr)
        receipts.append(
            {
                "operation": "native-export",
                "argv": args,
                "returncode": result.returncode,
                "wrong_pin": wrong_pin,
            }
        )
        checkpoint()
        if wrong_pin:
            assert result.returncode != 0 and not destination.exists()
            assert (
                "pin" in result.stdout + result.stderr
                or "digest" in result.stdout + result.stderr
            )
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            assert destination.is_file()
        return destination

    checkpoint()
    jsonl = export("jsonl", "section.items.jsonl", section=True)
    parquet = export("parquet", "section.items.parquet", section=True)
    docling = export("docling-json", "whole.docling.json")
    integrated = export("integrated-json", "whole.integrated.json")
    export("integrated-json", "wrong-pin.json", wrong_pin=True)

    import pyarrow.parquet as pq
    from docling_core.types.doc import DoclingDocument

    json_rows = [json.loads(line) for line in jsonl.read_text().splitlines()]
    parquet_table = pq.read_table(parquet)
    parquet_rows = parquet_table.to_pylist()
    assert json_rows and json_rows == parquet_rows
    assert all(
        row["content_digest"] == selection["content_digest"] for row in json_rows
    )
    metadata = parquet_table.schema.metadata
    assert metadata and b"source_contract" in metadata
    assert (
        json.loads(metadata[b"source_contract"])["contract"]
        == "integrated-pdf-source-3"
    )
    receipts.append(
        {
            "operation": "projection-equality",
            "outcome": "passed",
            "rows": len(json_rows),
            "columns": parquet_table.column_names,
            "canonical_rows_sha256": sha256(canonical(json_rows)).hexdigest(),
        }
    )
    checkpoint()
    # Fully detached reload: no database engine or live product reader is involved.
    native_value = json.loads(docling.read_bytes())
    restored = DoclingDocument.model_validate_json(docling.read_bytes())
    restored.validate_document()
    assert restored.validate_tree(restored.body, raise_on_error=True)
    assert restored.export_to_dict() == native_value
    with integrated.open() as stream:
        envelope = json.load(stream)
    product = envelope["product"]
    assert product["kind"] == "integrated"
    assert product["product_key"] == selection["product_key"]
    if product["version"] == 2:
        assert envelope["export_profile"] == "pdf-integrated-record-export-v2"
        assert product["logical_digest"] == selection["content_digest"]
        assert product["content"] == native_value
        assert all(product["revision"][key] for key in (
            "build_id", "release_id", "source_digest", "schema_digest", "recipe_digest", "frozen_digest"))
        assert "native_metadata" in product and "request_outcomes" in product
        # Conventional export SHA is verified against actual bytes, never compared
        # with the distinct admitted record-fold identity.
        export_manifest = json.loads(integrated.with_name(integrated.name + ".manifest.json").read_bytes())
        with integrated.open("rb") as stream:
            assert file_digest(stream,"sha256").hexdigest() == export_manifest["serialization_sha256"]
    else:
        assert product["version"] == 1
        assert sha256(canonical(product)).hexdigest() == selection["content_digest"]
        assert product["content"]["document"] == native_value
    assert envelope["binding"]["contract"] == "integrated-pdf-source-3"
    assert (
        envelope["binding"]["selection"]["content_digest"]
        == selection["content_digest"]
    )
    assert all(
        product[name] for name in ("inputs", "occurrences", "relations", "coverage")
    )
    # Selected content JSON explicitly declares the companion information it omits.
    manifest = json.loads(
        docling.with_name(docling.name + ".manifest.json").read_bytes()
    )
    assert manifest["projection"] == "docling-content-only" and manifest["omissions"]
    receipts.append(
        {
            "operation": "detached-roundtrip",
            "outcome": "passed",
            "native_schema_version": restored.version,
            "native_collections": {
                key: len(value)
                for key, value in native_value.items()
                if isinstance(value, (list, dict))
            },
            "integrated_inventory": {
                key: len(product.get(key, []))
                for key in (
                    "inputs",
                    "occurrences",
                    "relations",
                    "coverage",
                    "mapping_reports",
                )
            },
            "canonical_product_sha256": sha256(canonical(product)).hexdigest(),
        }
    )
    checkpoint()
    hashes = {}
    for path in sorted(output.iterdir()):
        if path.is_file():
            with path.open("rb") as stream:
                digest = file_digest(stream, "sha256").hexdigest()
            hashes[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
    with (output / "result.json").open("x") as stream:
        json.dump(
            {
                "outcome": "passed",
                "selection": selection,
                "calls": receipts,
                "artifacts": hashes,
            },
            stream,
            indent=2,
        )
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    qualify(
        json.loads(arguments.selection.read_bytes()),
        arguments.database,
        Path(__file__).resolve().parents[4],
        arguments.output,
    )
