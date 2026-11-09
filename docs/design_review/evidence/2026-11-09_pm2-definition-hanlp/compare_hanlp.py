"""Read-only HanLP syntax and SRL on the canonical retained definition window."""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.ingest.sentences import TextToken
from corpus_structure.methods.pm2_hanlp_products import hanlp_products
from corpus_structure.methods.pm2_worker import open_pm2_worker, preflight_pm2_runtime
from corpus_structure.orchestrate.pm2_stage import ParserScope, _sentences, _work
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.settings import Settings


def diagnostic_split(view, sentences, prior):
    """Replay the reviewed boundary correction as a distinct diagnostic only."""
    ((start, boundary, end),) = prior["split_boundaries"]
    (token,) = (item for item in view.layout.tokens if (item.start, item.end) == (start, end))
    if (
        token.role != "prose"
        or not any(
            piece["kind"] == "native_text" and piece["end"] == boundary for piece in view.pieces
        )
        or not any(
            piece["kind"] == "native_text" and piece["start"] == boundary for piece in view.pieces
        )
    ):
        raise ValueError("diagnostic split would alter a protected atom or an unpinned boundary")
    position = sentences.index((start, end))
    joined = sentences[position - 1][0], end
    if position == 0 or not any((lo, hi) == joined for lo, hi, _ in prior["split_sentences"]):
        raise ValueError("diagnostic sentence differs from the reviewed correction")
    layout = replace(
        view.layout,
        tokens=tuple(
            part
            for item in view.layout.tokens
            for part in (
                (
                    TextToken(start, boundary, False, "prose"),
                    TextToken(boundary, end, token.space, "prose"),
                )
                if item is token
                else (item,)
            )
        ),
    )
    return SimpleNamespace(text=view.text, layout=layout), [
        *sentences[: position - 1],
        joined,
        *sentences[position + 1 :],
    ]


def probe(
    worker, args, pin, target, prior, release, extent, view, sentences, source, prepared, variant
):
    startup = worker.startup
    work = _work(
        ParserScope.model_validate(
            dict(
                source=pin,
                extent=extent,
                profile=dict(provider="hanlp", device=args.device, startup=startup),
            )
        ),
        view,
        source,
        prepared,
        sentences,
    )
    response = worker.infer(work.request)
    result = dict(
        source=pin.model_dump(mode="json"),
        analysis_release=release,
        annotation_task=prior["annotation_task"],
        target=[target.start, target.end],
        extent=extent,
        layout_variant=variant,
        sentences=[(a, b, view.text[a:b]) for a, b in sentences],
        startup=startup,
        request=work.request,
        input_digest=work.input_digest,
        response=response,
    )
    if response["outcome"] == "succeeded":
        products = hanlp_products(work.mapping, work.request, response)
        result["tokens"] = [asdict(token) for token in work.mapping.tokens]
        result["products"] = [asdict(row) for row in products.products]
        result["locations"] = {
            key: list(value.anchors) if hasattr(value, "anchors") else str(value)
            for key, value in products.locations.items()
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--split-diagnostic", action="store_true")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    root = folder.parents[3]
    siblings = folder.parent
    inputs = StructuralInput.model_validate_json(
        (siblings / "2026-11-09_pm2-adoption/raw/target-inputs.json").read_bytes()
    )
    (target,) = (row for row in inputs.passages if row.passage_id == "binomial-distribution")
    (pin,) = (row for row in inputs.sources if row.identity == target.source_ref)
    prior_rows = json.loads(
        (siblings / "2026-11-09_pm2-definition-prerequisite/comparison.json").read_bytes()
    )
    (prior,) = (row for row in prior_rows if row["source"] == pin.model_dump(mode="json"))
    release = json.loads(
        (siblings / "2026-11-09_pm2-contract-remediation/raw/report-release.json").read_bytes()
    )["release"]
    settings = Settings()
    with (
        open_runtime_engine(settings, "pm2-definition-hanlp", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        conn.execute(
            select(func.ops.validate_structural_source(literal(pin.model_dump(mode="json"), JSONB)))
        )
        view = load_source_view(
            conn,
            pin.source_view_id,
            analysis_context=open_release(conn, release),
            read_budget=PublishedReadBudget(100_000, 256 * 1024 * 1024),
        )
    if view.text[target.start : target.end] != target.text:
        raise ValueError("target differs from authenticated projection")
    sentences = [
        (start, stop)
        for start, stop in _sentences(view)
        if start < target.end and stop > target.start
    ]
    extent = sentences[0][0], sentences[-1][1]
    if not 0 < extent[1] - extent[0] <= 1024:
        raise ValueError("canonical covering extent exceeds this probe's source bound")
    source = native_source_frame(view, ())
    prepared = PreparedNativeSources((source,), max_sources=1)
    script = root / "python/corpus-structure/src/corpus_structure/methods/pm2_native.py"
    project = root / "services/pm2-hanlp"
    python = project / ".venv/bin/python"
    assets = (root / settings.paths.model_cache / "pm2").resolve()
    preflight = preflight_pm2_runtime(
        python=python, script=script, project=project, provider="hanlp", assets=assets
    )
    worker_profile = dict(provider="hanlp", device=args.device, assets=str(assets))
    worker_profile["runtime_identity"] = preflight["runtime_identity"]
    variants = [("canonical", view, sentences)]
    if args.split_diagnostic:
        variants.append(
            ("split-reviewed-native-boundary-1", *diagnostic_split(view, sentences, prior))
        )
    with TemporaryDirectory(prefix="pm2-definition-hanlp-") as tmp:
        profile_path = Path(tmp) / "profile.json"
        profile_path.write_text(json.dumps(worker_profile))
        with open_pm2_worker(
            python=python,
            script=script,
            profile=profile_path,
            device=args.device,
            nemotron_endpoint=settings.nemotron.endpoint if args.device == "cuda" else None,
        ) as worker:
            results = [
                probe(
                    worker,
                    args,
                    pin,
                    target,
                    prior,
                    release,
                    extent,
                    selected_view,
                    selected_sentences,
                    source,
                    prepared,
                    variant,
                )
                for variant, selected_view, selected_sentences in variants
            ]
    if len({result["input_digest"] for result in results}) != len(results):
        raise ValueError("the diagnostic layout did not receive a distinct effective identity")
    if not args.split_diagnostic:
        # The original single-arm capture predates the two-arm result label.
        results[0].pop("layout_variant")
    print(
        json.dumps(
            results if args.split_diagnostic else results[0],
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
