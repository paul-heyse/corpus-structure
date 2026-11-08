"""Replay retained Nemotron responses through the selected Docling page parser."""

import argparse
import json
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from docling.utils.nemotron_parse_v3_5_utils import parse_nemotron_parse_v3_5
from docling_core.types.doc import Size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recognition_root", type=Path)
    args = parser.parse_args()
    rows = []
    for page_no in (108, 151, 301, 398, 416, 509):
        (page,) = args.recognition_root.glob(f"*/*/page-{page_no:05d}")
        for raw_path in sorted((page / "attempt-00001").glob("request-*.raw.txt")):
            request = int(raw_path.name.split("-")[1].split(".")[0])
            if request == 1:
                continue
            raw = raw_path.read_bytes()
            # Units are a normalized replay frame. The original product owns exact
            # physical crop-to-page coordinates; this replay compares parsed content.
            doc = parse_nemotron_parse_v3_5(
                raw.decode(), Size(width=1000, height=1000), page_no, normalize_heading_levels=False
            )
            rows.append(
                {
                    "page": page_no,
                    "request": request,
                    "raw_sha256": sha256(raw).hexdigest(),
                    "tables": [
                        {
                            "shape": [item.data.num_rows, item.data.num_cols],
                            "cells": [
                                cell.model_dump(mode="json") for cell in item.data.table_cells
                            ],
                        }
                        for item in doc.tables
                    ],
                    "formulas": [item.text for item in doc.texts if item.label.value == "formula"],
                    "captions": [item.text for item in doc.texts if item.label.value == "caption"],
                    "pictures": len(doc.pictures),
                }
            )
    print(json.dumps({"docling": version("docling"), "rows": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
