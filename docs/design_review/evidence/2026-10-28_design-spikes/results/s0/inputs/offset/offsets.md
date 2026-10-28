# Offset-form probe: how to cite evidence

This probe differs from the main passes in one respect: cite evidence by **character offsets**,
not by quote. Each `units/<unit>.md` gives the unit's exact text between the two marker lines.
Offsets count Unicode code points from 0 at the first character after the opening marker line;
`end` is exclusive. In your batch, each evidence item is `{"start": int, "end": int, "role": …}`,
statement anchors are `"unit"`, and `unsupported` items carry `start`/`end` instead of
`sentence`/`quote`. Everything else follows `format.md`.
