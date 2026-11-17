"""Selected production Docling assets and a three-page original-book recovery panel."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = ROOT / "docs/statistics_corpus/corpus/grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf"
PAGE_RANGE = (120, 122)


def selection():
    manifest = yaml.safe_load((ROOT / "domains/statistics/operations.yaml").read_bytes())
    selected = manifest["primary_profile"]["capture"]
    content = (ROOT / selected["assets_manifest"]).read_bytes()
    assets = json.loads(content)
    return selected, content, assets


def missing_pdf_resume_assets():
    from semantic.provider_book_panel_support import missing_snapshot

    selected, _content, assets = selection()
    missing = missing_snapshot(Path(selected["assets_root"]), tuple(name for name, _ in assets["files"]))
    original = missing_snapshot(ORIGINAL.parent, (ORIGINAL.name,))
    return "; ".join(item for item in (missing, original) if item) or None


def prepared_pdf_resume_assets():
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets

    selected, content, assets = selection()
    recipe = PdfRecipe.from_bytes((ROOT / selected["recipe"]).read_bytes())
    prepared = PreparedPdfAssets(
        Path(selected["assets_root"]), content,
        tuple(tuple(pair) for pair in assets["files"]),
        tuple(tuple(pair) for pair in assets["repositories"]),
    )
    prepared.verify()
    assert recipe.model_artifacts == prepared.files
    return recipe, prepared
