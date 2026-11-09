"""Compare ordinary PM2 parser and p289 public reads across Reader, CLI and stdio MCP."""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import (
    ContributionPage,
    ContributionRequest,
    serve_contributions,
)
from corpus_structure.serve.structural_products import (
    StructuralPage,
    StructuralRequest,
    serve_structural_products,
)
from corpus_structure.settings import Settings

COMMAND = str(Path(sys.executable).with_name("ci"))
ENV = os.environ | {"CORPUS_RUNTIME__DEFAULT_PROJECT": "nce-grinstead-snell-full-book"}
FACETS = (
    "qualifier_host_candidates",
    "modifier_candidates",
    "clause_containment",
    "local_referent_candidates",
)


def cli(*args):
    return subprocess.run(
        (COMMAND, *args, "--json"),
        env=ENV,
        check=True,
        capture_output=True,
        timeout=180,
    ).stdout


async def mcp(name, request):
    with TemporaryDirectory(prefix="pm2-reader-") as temporary:
        transport = StdioTransport(
            command=COMMAND,
            args=["mcp", "serve", "--semantic-run", str(request.run_id)],
            env=ENV,
            keep_alive=False,
            log_file=Path(temporary) / "stdio.log",
        )
        async with Client(transport, timeout=120) as client:
            response = await client.call_tool(
                name, {"request": request.model_dump(mode="json")}
            )
        if response.is_error:
            raise RuntimeError(response.content)
        return response.structured_content


def comparable(page):
    value = page.model_dump(mode="json")
    if "binding" in value:
        # Each read independently allocates its own transport snapshot capture ID.
        value["binding"].pop("capture_id")
    return value


def assert_same(page, other, label):
    left, right = comparable(page), comparable(other)
    assert left == right, (
        label,
        sorted(key for key in left if left[key] != right.get(key)),
    )


def parser_read(engine, run, view, method, cut, mandatory_facet):
    request = ContributionRequest(
        run_id=run,
        source_view_id=view,
        method=method,
        include_interpretation=True,
        limit=1000,
        page_bytes=8_000_000,
    )
    with read_snapshot(engine) as conn:
        page = serve_contributions(conn, request)
    by_cli = ContributionPage.model_validate_json(
        cli(
            "contributions",
            "list",
            "--run",
            str(run),
            "--source-view",
            str(view),
            "--method",
            method,
            "--include-interpretation",
            "--limit",
            "1000",
            "--page-bytes",
            "8000000",
        )
    )
    by_mcp = ContributionPage.model_validate(anyio.run(mcp, "contributions", request))
    assert_same(page, by_cli, (request.run_id, "CLI"))
    assert_same(page, by_mcp, (request.run_id, "MCP"))
    assert page.cut_id == cut and page.standing == "retained_private"
    observed = {
        key: [
            {"contribution_id": item["row"]["contribution_id"], "value": value}
            for item in page.items
            if item["population"] == "interpretation"
            and (value := (item["row"].get("composition") or {}).get(key)) is not None
        ]
        for key in FACETS
    }
    assert observed[mandatory_facet], (
        "the selected live page omitted the intended candidate facet"
    )
    return {
        "run": run,
        "cut": cut,
        "view": view,
        "method": method,
        "standing": page.standing,
        "facets": {
            key: {"count": len(items), "example": items[0] if items else None}
            for key, items in observed.items()
        },
        "page_sha256": sha256(
            canonical_bytes(page.model_dump(mode="json"))
        ).hexdigest(),
    }


def public_control(engine):
    request = StructuralRequest(
        run_id=477,
        cut_id=594,
        kind="condition_qualification",
        include_publication=True,
        include_support=True,
    )
    with read_snapshot(engine) as conn:
        page = serve_structural_products(conn, request)
    by_cli = StructuralPage.model_validate_json(
        cli(
            "structure",
            "list",
            "--run",
            "477",
            "--cut",
            "594",
            "--kind",
            request.kind,
            "--include-publication",
            "--include-support",
        )
    )
    by_mcp = StructuralPage.model_validate(
        anyio.run(mcp, "structural_products", request)
    )
    assert_same(page, by_cli, (request.run_id, "CLI"))
    assert_same(page, by_mcp, (request.run_id, "MCP"))
    (assertion,) = page.public_assertions
    return {"run": 477, "cut": 594, "assertion": assertion}


def main():
    settings = Settings()
    with open_runtime_engine(
        settings, application_name="pm2-reader-candidates", purpose="read"
    ) as engine:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                "hanlp": pool.submit(
                    parser_read,
                    engine,
                    421,
                    389,
                    "extract.pm2_hanlp",
                    524,
                    "qualifier_host_candidates",
                ),
                "maverick": pool.submit(
                    parser_read,
                    engine,
                    432,
                    405,
                    "extract.pm2_maverick",
                    532,
                    "local_referent_candidates",
                ),
                "public_preservation": pool.submit(public_control, engine),
            }
            controls = {key: future.result() for key, future in futures.items()}
    print(
        canonical_bytes(
            {
                "transports": ["ordinary Reader", "installed CLI", "fresh stdio MCP"],
                "scope": "retained candidate and existing assertion readback; no new semantic grading or admission",
                **controls,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
