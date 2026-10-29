"""The MCP servers the Claude Code session works through (agent interface §3.5, §3.6; D8 §1-§3;
ADR-0015).

- `service`: the application functions behind the main profile's tools (`queue_status`,
  `queue_next`, `read_unit`, `read_instructions`, `release`, `record_direction`), on a `Session`
  that holds the instance id and what this instance served;
- `submission`: `propose_claims`, the submission pipeline and its one transaction;
- `server`: the FastMCP main profile over them (`ci mcp serve`);
- `testing`: the submission harness, which drives the tools through an in-process client.

The main profile imports nothing that imports the math grammar (P0CL-14).
"""
