"""Read-only CLI/MCP comparison of retained uses across the adopted successor."""
import json
import subprocess
import sys
from pathlib import Path

import anyio
from fastmcp import Client

from corpus_structure.intervene.semantic_server import build_semantic_server
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.settings import Settings

BEFORE = "release:7caa087c2b31e65c316fc3224b6fe236d93a68a817ea10f5745bcd9c88464fa1"
AFTER = sys.argv[1]
RAW = Path(__file__).parent / "raw"


async def main():
    assert BEFORE != AFTER
    results = []
    async with Client(build_semantic_server(settings=Settings())) as client:
        for source, review, cut in ((487, 491, 606), (493, 495, 612)):
            arguments = dict(before=BEFORE, after=AFTER, source_run_id=source,
                             review_run_id=review, review_cut_id=cut, use_limit=1)
            seen = []
            cursor = None
            for page in range(10):
                if cursor is not None:
                    arguments["use_after"] = cursor
                argv = ["uv", "run", "ci", "schema", "diff", BEFORE, AFTER,
                        "--source-run-id", str(source), "--review-run-id", str(review),
                        "--review-cut-id", str(cut), "--use-limit", "1", "--json"]
                if cursor is not None:
                    argv.extend(("--use-after", cursor))
                process = subprocess.run(argv, capture_output=True, text=True)
                prefix = RAW / f"retained-{review}-page-{page}"
                prefix.with_suffix(".stdout.json").write_text(process.stdout)
                prefix.with_suffix(".stderr.txt").write_text(process.stderr)
                assert process.returncode == 0, process.stderr
                report = json.loads(process.stdout)
                reply = await client.call_tool("compare_semantic_releases", arguments)
                assert not reply.is_error and reply.structured_content == report
                assert report["report_version"] == 4
                survey = source_python(report["vocabulary_uses"])
                assert survey["vocabulary_release"] == BEFORE
                assert len(survey["items"]) <= 1
                seen.extend(survey["items"])
                if survey["complete"]:
                    break
                cursor = survey["next_after"]
                assert isinstance(cursor, str)
            else:
                raise AssertionError("finite retained population did not terminate")
            assert seen
            if source == 493:
                assert {row["selected_value"] for row in seen} == {"HOUR", "TIME"}
            results.append(dict(source_run=source, review_run=review, review_cut=cut,
                                pages=page + 1, uses=len(seen)))
    print(canonical_bytes(dict(outcome="passed", before=BEFORE, after=AFTER,
                               populations=results,
                               limits="Selected retained populations only; other uses unknown.")).decode())


anyio.run(main)
