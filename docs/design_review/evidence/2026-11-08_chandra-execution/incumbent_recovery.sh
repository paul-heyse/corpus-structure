#!/usr/bin/env bash
# Publish the exact book's current Standard source and replay its retained A/B/C inputs.
set -euo pipefail

if (( $# < 3 || $# > 4 )); then
    echo 'Usage: bash incumbent_recovery.sh RELEASE REALIZATION NEW_OUTPUT_DIR [STANDARD_RUN]' >&2
    exit 2
fi

release=$1
realization=$2
output=$3
standard_run=${4-}
project=nce-grinstead-snell-full-book
book=Introduction_to_probability_grinstead_and_snell.pdf
evidence_dir=docs/design_review/evidence/2026-11-08_chandra-execution
receipts=build/nce-full-book/integrated-source/recognition
export CORPUS_NEMOTRON__RECEIPTS=$receipts
export UV_NO_SYNC=1 UV_OFFLINE=1 HF_HUB_OFFLINE=1

mkdir "$output"
domains="$output/domains"
mkdir -p "$domains/statistics"
cp domains/statistics/guideline.md "$domains/statistics/"
uv run python - "$book" "$domains" <<'PY'
import json
from pathlib import Path
import sys

import yaml

from corpus_structure.ingest.pdf_incumbent_recovery import ORIGINAL, RECIPE
from corpus_structure.ingest.pdf_recognition import PreparedRecognitionSource, admit_service_generation
from corpus_structure.ingest.pdf_recognition_methods import PdfIntegratedRecoveryConfig
from corpus_structure.settings import Settings

book, domains = sys.argv[1:]
source = PreparedRecognitionSource.prepare((Path("build/nce-full-book/corpus") / book).read_bytes())
if source.digest != ORIGINAL:
    raise SystemExit("Original digest differs from the reviewed book")
cfg = PdfIntegratedRecoveryConfig(source_recovery=RECIPE)
recipe = cfg.recognition_recipe()
settings = Settings()
root = settings.nemotron.receipts / source.digest / recipe.digest
for page in range(1, 519):
    attempts = (root / f"page-{page:05d}").glob("attempt-*/result.json")
    if not any(json.loads(attempt.read_bytes())["outcome"] == "succeeded" for attempt in attempts):
        raise SystemExit(f"No complete retained recognition attempt for page {page}")
admit_service_generation(settings.nemotron.endpoint, recipe)
pack = yaml.safe_load(Path("domains/statistics/methods.yaml").read_text())
pack["configs"]["ingest.pdf"]["default"]["originals"] = [book]
pack["configs"]["ingest.pdf_integrated"]["default"].update(
    originals=[book], source_recovery=RECIPE
)
(Path(domains) / "statistics/methods.yaml").write_text(yaml.safe_dump(pack))
PY

if [[ -z "$standard_run" ]]; then
    uv run python "$evidence_dir/standard_publication.py" "$release" "$domains" \
        --project "$project" --realization "$realization" \
        >"$output/standard.json" 2>"$output/standard.stderr"
    standard_run=$(jq -er 'select(.status == "source_ready").run_id' "$output/standard.json")
fi

uv run ci source native-products "$standard_run" --json 2>"$output/standard-catalog.stderr" |
    jq -e --arg release "$release" '
        [.[] | select(.product_key == "organized" and .release_id == $release and .health.conversion == "success")] |
        select(length == 1) | .[0] | {task_id, product_key, content_digest}
    ' >"$output/standard-pin.json"
uv run python "$evidence_dir/standard_publication.py" "$release" "$domains" \
    --project "$project" --realization "$realization" --integrate \
    --native-pin "$output/standard-pin.json" \
    >"$output/integrated.json" 2>"$output/integrated.stderr"
integrated_run=$(jq -er 'select(.status == "source_ready").run_id' "$output/integrated.json")
uv run ci source native-products "$integrated_run" --json 2>"$output/integrated-catalog.stderr" |
    jq -e --arg release "$release" '
        [.[] | select(.product_key == "integrated" and .release_id == $release and .health.conversion == "success")] |
        select(length == 1) | .[0] | {task_id, product_key, content_digest}
    ' >"$output/integrated-pin.json"
