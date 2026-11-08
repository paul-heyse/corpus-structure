"""Read a live group's manifest and exact mapped member through MCP."""

import argparse
import asyncio
import json
import sys
from hashlib import sha256
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from corpus_structure.semantic.identity import canonical_bytes


async def verify(group: dict) -> dict:
    source = group["source"]
    member = next(member for member in group["members"] if member["mapped"] is not None)
    page_no = member["selection"]["page_no"]
    request = dict(
        **source,
        view="visual_evidence",
        page_no=page_no,
        evidence=member["mapped"],
        max_bytes=8 * 1024 * 1024,
    )
    process = StdioServerParameters(
        command=str(Path(sys.executable).with_name("ci")),
        args=["mcp", "serve", "--semantic-run", str(source["run_id"])],
    )
    async with stdio_client(process) as (reader, writer), ClientSession(reader, writer) as session:
        await session.initialize()

        async def call(name, **params):
            reply = await session.call_tool(name, params)
            if reply.is_error or reply.structured_content is None:
                raise RuntimeError(str(reply.content)[:2500])
            return reply.structured_content

        manifest = await call("list_visual_observations", source=source, page_no=page_no)
        assert any(
            row["mapped"] == member["mapped"] and row["raw"] == member["raw"]
            for row in manifest["observations"]
        )
        inspection = await call("inspect_source", request=request)
        packet = await call("visual_evidence_packet", request=request)
        assert packet["source"] == inspection
        digest = packet.pop("digest")
        assert sha256(canonical_bytes(packet)).hexdigest() == digest
        return {
            "source": source,
            "member": member["mapped"],
            "page": page_no,
            "packet_digest": digest,
            "outcome": inspection["outcome"],
            "mapping_availability": inspection["visual_evidence"]["mapping_availability"],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(verify(json.loads(args.group.read_bytes())))))
