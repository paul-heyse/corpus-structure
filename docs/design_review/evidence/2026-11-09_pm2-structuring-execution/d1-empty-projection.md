# I01 · Completed empty d1 read

**Tested · 2026-11-09.** The maintained-claim native PostgreSQL control and
six existing interpretation controls passed in managed result
`bdb7cf2b077a44bb9d243f3747069b7e`. The same absent question has the same
payload in mixed and all-empty replies. The former v2 projection still
settles an all-empty reply without a contribution; a limited v3 request
also emits no question contribution. Malformed source, question and
empty replies are refused. The contribution read exposes both v3 missing
answers as unresolved and neither has a physical occurrence.

The [CUDA request](raw/d1-empty-request.json) asked the released date
question about a sentence that states no date, using the exact retained
p289 view 410 (source run 474/cut 588, native product 1566/organized).
`uv run ci run interpret --request REQUEST --json` settled the
[v3 result](raw/d1-empty-result.json) at run 481/cut 596/task 2221.
The provider settled `empty`; projection settled `succeeded` with one
inspected scope and one emitted contribution. The
[ordinary CLI](raw/d1-empty-cli.json) and
[fresh stdio MCP](raw/d1-empty-mcp.json) matched except for their separate
capture UUIDs. The date is `unresolved`, retains native `found=0.0`,
has no answer location or occurrence, and remains private.

The first CUDA attempt (run 480/task 2220) failed in the result binder:
it did not construct an exact source field for an empty rendered reply.
The successor path now binds source fields for all completed projected
products, including v3 empty d1, while retaining existing native task and
contribution outcome guards. The exact interrupted run was
[cancelled by the managed route](raw/d1-empty-initial-cancel.json) after
the corrected run settled. No activation, selection, recognition or
calibration occurred.
