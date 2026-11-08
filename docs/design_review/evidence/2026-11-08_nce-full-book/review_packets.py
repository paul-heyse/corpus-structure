"""Prepare per-page source and retained-output pairs for independent review."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from hashlib import file_digest
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PARENT = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
RUNS = {"standard": 297, "combined": 312}


def words(value):
    return re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold())


def page_outputs(conn, run):
    views = (
        conn.execute(
            text("""
            SELECT v.id,v.native_task_id,v.native_product_key,v.native_content_digest,v.projection
            FROM ops.run_source_view s JOIN kb.source_view v ON v.id=s.source_view_id
            WHERE s.run_id=:run ORDER BY s.position
        """),
            {"run": run},
        )
        .mappings()
        .all()
    )
    ((task, key, digest),) = {
        (v.native_task_id, v.native_product_key, v.native_content_digest) for v in views
    }
    product = {"task": task, "key": key, "digest": digest}
    pages_by_item = defaultdict(set)
    for pointer, page in conn.execute(
        text("""
            SELECT DISTINCT pointer,page_no FROM ops.pdf_published_region
            WHERE task_id=:task AND product_key=:key
        """),
        product,
    ):
        pages_by_item[pointer].add(page)
    parents = {}
    native_labels = defaultdict(Counter)
    for pointer, parent, label in conn.execute(
        text("""
            SELECT pointer,parent_pointer,label FROM ops.pdf_published_item
            WHERE task_id=:task AND product_key=:key
        """),
        product,
    ):
        parents[pointer] = parent
        for page in pages_by_item.get(pointer, ()):
            native_labels[page][label] += 1
    fragments = defaultdict(list)
    inherited = defaultdict(set)
    multiple = defaultdict(set)
    for view in views:
        projection = view.projection
        for piece in projection["pieces"]:
            if piece["kind"] != "native_text":
                continue
            pointer = piece["item_ref"]
            owner = pointer
            visited = {pointer}
            while owner and owner not in pages_by_item:
                owner = parents.get(owner)
                if owner in visited:
                    raise ValueError(f"native parent cycle for {pointer}")
                visited.add(owner)
            for page in sorted(pages_by_item.get(owner, ())):
                if owner != pointer:
                    inherited[page].add(pointer)
                if len(pages_by_item[owner]) > 1:
                    multiple[page].add(pointer)
                fragments[page].append(
                    dict(
                        view=view.id,
                        pointer=pointer,
                        field=piece.get("source_field", "text"),
                        start=piece["start"],
                        text=projection["text"][piece["start"] : piece["end"]],
                    )
                )
    return product, {
        page: dict(
            native_labels=dict(native_labels[page]),
            inherited_locators=len(inherited[page]),
            multipage_locators=len(multiple[page]),
            fragments=fragments[page],
        )
        for page in range(1, 519)
    }


def comparisons(reference, page_outputs):
    source_words = Counter(words(reference))
    selected = {}
    for name, output in page_outputs.items():
        joined = "\n".join(fragment["text"] for fragment in output["fragments"])
        bag = Counter(words(joined))
        unmatched = source_words - bag
        selected[name] = dict(
            source_token_hits=sum((source_words & bag).values()),
            output_tokens=sum(bag.values()),
            native_labels=output["native_labels"],
            inherited_locators=output["inherited_locators"],
            multipage_locators=output["multipage_locators"],
            absent_source_lines=[
                line
                for count, line in sorted(
                    (
                        (sum((Counter(words(line)) & unmatched).values()), line.strip())
                        for line in reference.splitlines()
                        if len(words(line)) >= 4
                    ),
                    reverse=True,
                )[:3]
                if count
            ],
            output_excerpt=" ".join(joined.split())[:240],
        )
    return dict(
        source_tokens=sum(source_words.values()),
        source_excerpt=" ".join(reference.split())[:240],
        **selected,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.pdf.open("rb") as source:
        if file_digest(source, "sha256").hexdigest() != PARENT:
            raise ValueError("review requires the authenticated whole-book parent")
    original = subprocess.check_output(
        ["pdftotext", "-layout", str(args.pdf), "-"], encoding="utf-8"
    ).split("\f")
    if len(original) != 519 or original[-1].strip():
        raise ValueError("reference extraction does not match the 518 physical pages")
    args.output.mkdir(parents=True, exist_ok=True)
    with (
        open_runtime_engine(Settings(), "gs518-review-packets", purpose="maintenance") as engine,
        read_snapshot(engine) as conn,
    ):
        products = {name: page_outputs(conn, run) for name, run in RUNS.items()}
    with (
        (args.output / "pages.jsonl").open("w", encoding="utf-8") as pages,
        (args.output / "comparison.jsonl").open("w", encoding="utf-8") as summary,
    ):
        for page, reference in enumerate(original[:-1], start=1):
            outputs = {name: result[page] for name, (_, result) in products.items()}
            pages.write(
                json.dumps(dict(page=page, source=reference, **outputs), ensure_ascii=False) + "\n"
            )
            summary.write(
                json.dumps(dict(page=page, **comparisons(reference, outputs)), ensure_ascii=False)
                + "\n"
            )
    (args.output / "manifest.json").write_text(
        json.dumps(
            dict(
                parent_sha256=PARENT,
                pages=518,
                sources={name: {"run": RUNS[name], **pin} for name, (pin, _) in products.items()},
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
