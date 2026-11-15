---
id: ADR-0106
title: DDO PostgreSQL derives structural wire APIs and reserves renewal custody
status: accepted
date: 2026-11-14
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A supported protocol cannot receive a faithful structural projection, or an admitted shared-engine workload cannot provide the explicit renewal and foreground capacity contract.
---

## Context

The operator selected the [PostgreSQL alignment amendment](../plans/declared-data-operations_2026-11-12.md#postgresql-domain-alignment-amendment--accepted-2026-11-14)
and its integrated source/API execution on 2026-11-14. The semantic model and PostgreSQL remain
structure and instance authorities; this record chooses their concrete interface and resource
realization under existing §B4/§B5, without changing those binding decisions. The coordinator owns
implementation and source/context-qualified evidence. Persistent deployment and historical conversion
remain excluded from this increment.

Closed Draft7 native validation already exists, but current consumers otherwise reconstruct fields
through Any mappings and operation strings. Pydantic JSON materialization also bypasses the exact
scope-number codec. Concurrent port calls and renewal borrow independently from a finite writer
inventory. SQLAlchemy NullPool setup repeatedly registers its notice callback on Psycopg's reused
physical session. Legacy installed table/interchange compilation has only one live Arrow helper
consumer and historical producing metadata, not current physical authority.

## Options

1. Retain validated generic mappings and local field knowledge. Functional but leaves consumers
   duplicating schema structure and makes the wide public migration repeat that knowledge.
2. Generate another Pydantic runtime model layer. It can enforce useful structure but requires
   extra unset/default tracking and exact-number conversion over existing schema enforcement.
3. Derive static structural views and named methods from the captured schema; keep authoritative
   schema validation and exact transport. Chosen: it removes independently maintained interfaces
   without claiming conditional JSON semantics are fully expressible in Python types.
4. Add a permanent renewal pool or raise connection limits without a workload owner. Either adds
   inventory or leaves renewal competing for checkout. Reserve an existing writer checkout instead;
   bound actual foreground worker admission and retain separate purpose credentials.
5. Replace Psycopg pooling or bypass SQLAlchemy dialect initialization to fix notices. Disproportionate
   and risks losing driver/isolation setup. Use a store-owned connection subclass with idempotent
   public notice registration instead.
6. Preserve the retired compiler by keeping its current identity marker, or rewrite old compiler
   maps. Both confuse current generation with historical producing identity. Keep old maps exact and
   publish the actual current compiler set alongside current generated artifacts.

These choices apply FP-01/04/05/06/07 and the efficient-architecture heuristics: use existing library
ownership, retain semantic distinctions, remove redundant conversion/work, and size lifecycle
machinery for actual participants rather than layering another pool, DTO authority or compiler.
No quantitative benefit is claimed.

## Decision

- The captured native protocol owns wire shape. Generate TypedDict/Required/NotRequired/Literal
  views, explicit model-owned NewType bindings and fixed named storage methods through existing
  generation/correspondence custody. Physical JSON parameters/results remain JSON. Draft7 owns
  conditional/dependent constraints; exact JSON codecs preserve number and absent/null meaning.
  Returned mappings are detached snapshots, not deeply immutable objects. SQLAlchemy TypedColumns/
  Named remain the corresponding static mechanism for relational rows, not runtime authorization.
- The existing writer pool owns physical inventory. One renewal-thread checkout is reserved before
  foreground admission, remains transaction-idle between renewal cycles, and is returned only after
  its owner has stopped using it. Foreground port workers and the driver have explicit remaining
  capacity. Unmanaged/shared engines require a stated capacity contract. No transparent replay of
  uncertain renewal commits is introduced. Foreground ports hold no checkout through inference waits.
- Store connections make repeated registration of an equal notice callback idempotent through
  Psycopg public add/remove APIs. SQLAlchemy invalidation uses its public invalidate event to finish the
  borrowed libpq handle and return the dead session to Psycopg for replacement: ordinary
  close-returns must not turn physical invalidation into reuse. SQLAlchemy retains its full dialect setup; pool sanitation,
  extension checks, JSON adapters and primary failure/cleanup attribution remain owned as before.
- Retire installed legacy relational/interchange compilation after migrating its actual helper
  consumers. A historical declaration log retains producing compiler maps unchanged. Validation
  of current declaration identity compares label/content/key scheme; current generated artifacts
  record current compiler identities. This realizes ADR-0024's replacement of installed-only
  interpretation, rather than reviving superseded ADR-0022 coupling or changing frozen history.
- Public selection/reuse and historical retirement continue under the existing DDO semantic owners.
  A narrow historical reader is justified only by its actual sealed custody obligation, not as a
  current fallback. Native function changes use frozen forward authoring; no deployment follows
  from code generation or registration.

## Consequences

Useful native type knowledge reaches actual callers, exact codecs remain authoritative, renewal
cannot queue behind foreground port checkouts, and obsolete current compiler machinery can disappear
without rewriting historical records. The connection subclass and reserved checkout have narrow
explicit contracts and focused tests; generic libraries retain the remaining responsibilities.

Source implementation and bounded pure checks exist; native integration, complete public migration
and assembled qualification remain with the [coordinator](../plans/declared-data-operations_2026-11-12.md).
Accepted means these choices govern the increment, not that its findings or wider packages are closed.

The invalidation event precedes SQLAlchemy's final close attempt ([SQLAlchemy 2.1 events](https://docs.sqlalchemy.org/en/21/core/events.html#sqlalchemy.events.PoolEvents.invalidate)).
Psycopg's [close-returns contract](https://www.psycopg.org/psycopg3/docs/api/pool.html#psycopg_pool.ConnectionPool)
otherwise returns that live handle to its pool. Installed 3.3.6/3.3.3 source confirms a finished
handle is closed and pool return replaces it; scoped native reconnect control passed on 2026-11-14
in `5fccf0c69835479da445a64d2f4895a0`, after retained failure `b441ebc54d2f488fac2088d02abed8b5`.
