"""Fresh external stdio MCP98: private reports, separate support and bounded paging."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CLI = HERE.parent / "2026-11-05_pce-structural-products/raw/public-cli-structure-003.json"
RUN, CUT = 98, 132


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")


async def journey(attempt):
    prefix = RAW / ("final_mcp_" + attempt)
    receipt = dict(outcome="failed", run_id=RUN, cut_id=CUT,
                   transport="fresh_external_stdio", calls=[], context_settled=False,
                   provider_execution="not_run", defaults_activated=False)
    expected = json.loads(CLI.read_text())
    assert expected["run_id"] == RUN and expected["cut_id"] == CUT
    transport = StdioTransport(command="uv", args=["run", "ci", "mcp", "serve",
                                                  "--semantic-run", str(RUN)])
    try:
        async with Client(transport) as client:
            async def call(name, request):
                response = await client.call_tool("structural_products", {"request": request},
                                                  raise_on_error=False)
                recorded = dict(request=request, is_error=response.is_error,
                                structured_content=response.structured_content,
                                content=[value.model_dump(mode="json")
                                         for value in response.content])
                save(Path(str(prefix) + "_" + name + ".json"), recorded)
                receipt["calls"].append(dict(name=name, is_error=response.is_error))
                return response, recorded

            private, _ = await call("private", dict(run_id=RUN))
            assert not private.is_error and private.structured_content is not None
            ordinary = private.structured_content
            assert ordinary["cut_id"] == CUT and len(ordinary["reports"]) == 4
            assert ordinary["standing"] == "private_proposals"
            assert ordinary["publication"] == "not_requested" and ordinary["public_assertions"] == []
            assert all(row["standing"] == "private_proposal" for row in ordinary["reports"])

            selected = dict(run_id=RUN, include_publication=True, include_support=True,
                            max_bytes=8_000_000)
            supported, _ = await call("supported", selected)
            assert not supported.is_error and supported.structured_content is not None
            common = supported.structured_content
            assert common == expected
            assert common["reports"] == ordinary["reports"]
            assert common["standing"] == "private_proposals" and common["publication"] == "included"
            assert len(common["public_assertions"]) == 4
            assert all(row["standing"] == "admitted_structural_statement" and row["sources"]
                       and row["statement"] for row in common["public_assertions"])

            task_ids, reports, assertions = [], [], {}
            after = 0
            for page_number in range(1, 5):
                response, _ = await call("page" + str(page_number),
                                          dict(**selected, limit=1, after_task_id=after))
                assert not response.is_error and response.structured_content is not None
                page = response.structured_content
                assert len(page["task_ids"]) == len(page["reports"]) == 1
                assert page["task_ids"][0] > after
                task_ids.extend(page["task_ids"])
                reports.extend(page["reports"])
                assertions.update((row["assertion_id"], row) for row in page["public_assertions"])
                cursor = page["next_after_task_id"]
                if page_number < 4:
                    assert cursor == page["task_ids"][0]
                    after = cursor
                else:
                    assert cursor is None
            assert task_ids == common["task_ids"] == [238, 239, 240, 241]
            assert reports == common["reports"]
            assert assertions == {row["assertion_id"]: row for row in common["public_assertions"]}

            wrong, wrong_raw = await call("wrong_cut", dict(run_id=RUN, cut_id=131))
            assert wrong.is_error and "exact completed cut" in json.dumps(wrong_raw)
            small, small_raw = await call("byte_refusal", dict(run_id=RUN, max_bytes=1))
            assert small.is_error and "byte budget" in json.dumps(small_raw)
        receipt.update(outcome="passed", context_settled=True,
                       common_cli_equal=True, default_private_reports=4,
                       separate_public_assertions=4, supported_source_witnesses=True,
                       task_pointer_paging=task_ids, wrong_cut_refused=True,
                       one_byte_refused=True,
                       source_scope="selected original sources; no whole-corpus or scientific-truth claim")
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        save(Path(str(prefix) + "_receipt.json"), receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True, choices=[f"{n:03d}" for n in range(1, 100)])
    args = parser.parse_args()
    asyncio.run(journey(args.attempt))
