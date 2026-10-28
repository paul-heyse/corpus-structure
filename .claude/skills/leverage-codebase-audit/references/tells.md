# Optional search cues

These cues nominate places to inspect. Apply the pattern framework to understand the actual
responsibility, value and counterconditions. They are neither a checklist nor automatic findings.
Use the host's existing search and static-analysis tools when useful; do not introduce alignment
lints or permanent detectors merely to operate this framework.

## Responsibility and architecture

- Custom parsers, solvers, workflow engines, schedulers, plugin loaders, query builders or caches.
- A routine extension requiring parallel edits to model, validation, codec and dispatch code.
- Repeated conversion or hydration between neighboring libraries and internal models.
- Polling, flag files, custom task maps or several layers independently managing one lifecycle.
- Consumers unable to express a set, predicate, projection or complete operation through a port.
- The same intended behavior served through several helpers, libraries or configurations.
- Manual developer/operator workflows or intended consumers lacking a usable operation.

## Names and comments

- Utility namespaces and generic capability names such as retry, parse, normalize or registry.
- Comments describing copied upstream code, workarounds, backports or temporary shims.
- Broad names such as engine, framework or platform whose actual responsibility needs inspection.

Names can locate code while providing little evidence of its meaning. A utility namespace can
contain sound domain operations; a small helper can hide a substantial generic mechanism.

## Implementation shapes

- A loop holding a try block, sleep and counter; maps carrying timestamps and eviction logic.
- Loops accumulating joins, grouping, aggregation or repeated calls over a coherent population.
- Manually synchronized lists, switches, schemas, constructors, serializers or validators.
- Full loading followed by narrow selection, or intermediate materialization between operators.
- Repeated compilation, schema creation, planning, indexing or resolution at inner lifetimes.
- Scattered acquire/release, begin/commit, cancellation, retry or cleanup logic.
- Regex parsing of structured standard formats or manual quoting and composition.

Each can have a legitimate purpose. Inspect error semantics, effects, ordering, trust boundaries,
resource lifetime and supported workload before proposing delegation or removal.

## Existing dependencies

- Wrappers rebuilding functionality around lower-level calls or recomputing returned information.
- Private member access, monkey-patching, internal subclasses or repeated escape hatches.
- Version guards, deprecated calls or workarounds whose original premise may have changed.
- Bulk-capable systems driven through scalar calls or forced into eager conversions.

Low call-site count and pin age alone establish no under-use. Research the specific capability
and selected realization; a version change can help only if it fits the actual remaining contract.
