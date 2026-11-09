# PostgreSQL discovery coverage

**Source-inspected 2026-11-09; research benefits Proposed.** This is the coverage appendix of the
[family briefing](../briefing.md), not a new opportunity/finding register. All nine main documents,
addenda, corrections and source maps were read end to end during planning; execution refreshed the
unchanged consumer/reference baseline at `51b3c28de`. Section ranges below are overview line ranges
at that baseline; they are navigation aids, not independent verification or runtime evidence.

## Reading and classification

- **Used:** the topic names an adopted mechanism and reason to retain it; adequacy is bounded by the inspected responsibility.
- **Underuse candidate:** an adopted capability has a concrete local seam worth investigating. Benefit/fit remains Proposed.
- **Unused lead:** no written use was found in the scoped production search, and a plausible consumer is named; indirect use remains unresolved.
- **Conditional:** deeper research needs a stated workload, operator, new type or consumer; availability alone is insufficient.
- **Unresolved:** exact integration, attribution or contract is unsettled. A no-hit is not proof of absence.

The rows route each section to a topic that owns the individual feature dispositions. “Mixed”
means a broad section contains both adopted foundations and research leads; it is not a blanket
unused/underused judgment. Source maps and architectural conclusions supply context, not new APIs.

Topic keys: T types/invariants; R relational operations; S SQL analysis; E evolution/catalog;
A Arrow/COPY; L lifetimes; V vector retrieval. Each key links to its owning topic.

## Section map

### sqlalchemy — 2,951 lines

[Complete overview](../../../../libraries/postgresql/sqlalchemy.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Architectural model and capability map | 33–82 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 2. SQLAlchemy Core: a programmable relational expression language | 83–322 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 3. Schema metadata, reflection, and database structure | 323–472 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 4. Type system and typed relational models | 473–600 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Main · 5. Object-relational mapping: modeling relational structures as Python objects | 601–790 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Main · 6. Advanced ORM attributes: expressing domain semantics in the mapping layer | 791–945 | Conditional: [T](domain-types-and-invariants.md) |
| Main · 7. ORM query execution, loading strategies, and bulk operations | 946–1091 | Conditional: [R](relational-operations-and-preparation.md) |
| Main · 8. Database execution, transactions, and resource management | 1092–1275 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 9. Dialect architecture and database-native capabilities | 1276–1368 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Main · 10. Extension architecture, events, and introspection | 1369–1482 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 11. Performance architecture and optimization mechanisms | 1483–1587 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 12. Important ecosystem integration boundaries | 1588–1646 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 13. SQLAlchemy 2.1-specific changes and compatibility considerations | 1647–1710 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 14. Cross-cutting limitations and consequential distinctions | 1711–1731 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Main · 15. Primary-source reference map | 1732–1786 | Supporting context: [R](relational-operations-and-preparation.md) |
| Main · 16. Architectural synthesis | 1787–1827 | Supporting context: [R](relational-operations-and-preparation.md) |
| Addendum · 1. Advanced relational operations and SQL construction | 1828–2061 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Addendum · 2. Programmable DDL, reflection, and schema-derived models | 2062–2206 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 3. Advanced ORM mapping and loading | 2207–2385 | Conditional: [T](domain-types-and-invariants.md) |
| Addendum · 4. ORM execution interception, substitution, and distributed routing | 2386–2467 | Conditional: [L](transactions-pools-and-outcomes.md) |
| Addendum · 5. Transaction ownership, Session scoping, and binding control | 2468–2554 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 6. Engine creation, connection errors, and low-level execution extensions | 2555–2642 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 7. JSON semantics and type-aware operator validation | 2643–2728 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Addendum · 8. Additional database-native schema and dialect functionality | 2729–2827 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Addendum · 9. SQLAlchemy 2.1.6 release corrections | 2828–2873 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 10. Cross-capability architectural implications | 2874–2909 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Addendum · 11. Primary-source additions for the reference map | 2910–2940 | Supporting context: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · Closing synthesis | 2941–2951 | Supporting context: [R](relational-operations-and-preparation.md) |

### pglast — 1,847 lines

[Complete overview](../../../../libraries/postgresql/pglast.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Executive orientation | 5–59 | Supporting context: [S](sql-analysis-and-source-fidelity.md) |
| Main · 2. Architecture and execution model | 60–127 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 3. Parsing and representation interfaces | 128–205 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 4. Typed AST objects and programmatic construction | 206–283 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 5. AST traversal, structural analysis, and transformation | 284–415 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 6. Lexical analysis, splitting, and source locations | 416–516 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 7. SQL fingerprinting and structural grouping | 517–573 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 8. SQL regeneration, formatting, and deparsing | 574–700 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 9. Custom SQL printers and serialization extension points | 701–787 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 10. Comments, procedural SQL, and command-line tooling | 788–897 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 11. Architectural applications and capability combinations | 898–1007 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 12. Integrations and adjacent libraries | 1008–1096 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 13. Performance, correctness, and operational constraints | 1097–1198 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 14. Key architectural distinctions | 1199–1222 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 15. Primary-source reference map | 1223–1257 | Supporting context: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 1. Advanced fingerprinting semantics and query identity | 1258–1328 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 2. Lower-level AST traversal and mutation machinery | 1329–1451 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 3. SQL printer internals and reusable generation primitives | 1452–1567 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 4. Comment representations, source spans, and diagnostics | 1568–1691 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 5. Procedural-language inspection through the CLI | 1692–1715 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 6. Version boundaries and corrections to the original guide | 1716–1828 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 7. Additional primary-source map | 1829–1847 | Supporting context: [S](sql-analysis-and-source-fidelity.md) |

### sqlglot — 2,724 lines

[Complete overview](../../../../libraries/postgresql/sqlglot.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Architectural orientation | 23–70 | Supporting context: [S](sql-analysis-and-source-fidelity.md) |
| Main · 2. SQL parsing and the expression model | 71–164 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 3. Dialect translation and SQL generation | 165–277 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 4. Schema-aware semantic analysis | 278–410 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 5. Rule-based query optimization and canonicalization | 411–523 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 6. Column-level data lineage | 524–593 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 7. AST differencing and structural change analysis | 594–637 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 8. AST serialization and query anonymization | 638–697 | Conditional: [S](sql-analysis-and-source-fidelity.md) |
| Main · 9. JSONPath parsing and semi-structured expressions | 698–723 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 10. Logical query planning and Python execution | 724–797 | Conditional: [S](sql-analysis-and-source-fidelity.md) |
| Main · 11. Extensibility: dialects, grammars, expressions, and transformation rules | 798–853 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 12. Diagnostics, command-line tooling, and operational use | 854–921 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 13. Installation, compiled acceleration, and versioning | 922–993 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 14. Capability composition and architectural opportunities | 994–1018 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 15. Ecosystem boundaries and complementary tools | 1019–1046 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 16. Cross-cutting limitations and correctness considerations | 1047–1080 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · Primary-source reference map | 1081–1110 | Supporting context: [S](sql-analysis-and-source-fidelity.md) |
| Main · Overall assessment | 1111–1134 | Supporting context: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 1. Expression architecture: traits, concrete nodes, and behavioral interfaces | 1135–1208 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 2. Recursive source expansion, query substitution, and table-identity transformations | 1209–1318 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 3. Structured SQL templates and AST-level placeholder substitution | 1319–1406 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 4. SQL structural metadata extraction and lightweight dependency analysis | 1407–1476 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 5. Structured DDL, DML, privileges, transactions, and administrative SQL | 1477–1629 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 6. Rich data-type representations and nested-data semantics | 1630–1771 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 7. Operator-aware output-schema reasoning for PIVOT and UNPIVOT | 1772–1850 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 8. Expression DSL, predicate composition, and structural identity | 1851–1969 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 9. Machine-readable SQL comments and parser directives | 1970–2072 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 10. AST diagnostics, source-position metadata, and transformation composition | 2073–2186 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 11. Specialized generator transformations | 2187–2430 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 12. Pipe-style SQL query syntax | 2431–2510 | Conditional: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 13. Date/time format translation and subsecond precision utilities | 2511–2586 | Conditional: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 14. SQLFrame: the former SQLGlot DataFrame API | 2587–2624 | Conditional: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · 15. Important semantic boundaries and capability interactions | 2625–2713 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Addendum · Addendum conclusion | 2714–2724 | Supporting context: [S](sql-analysis-and-source-fidelity.md) |

### psycopg — 2,307 lines

[Complete overview](../../../../libraries/postgresql/psycopg.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Conceptual architecture and capability map | 28–78 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 2. Installation, runtime architecture, and version requirements | 79–145 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 3. SQL execution, parameter binding, and query composition | 146–292 | Mixed; see feature dispositions: [S](sql-analysis-and-source-fidelity.md) |
| Main · 4. Prepared statements and repeated-query execution | 293–338 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 5. Pipeline mode and batch execution | 339–405 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 6. COPY: native high-throughput data movement | 406–475 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 7. PostgreSQL type adaptation and extensibility | 476–703 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Main · 8. Row factories, typed result materialization, and static typing | 704–765 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Main · 9. Result retrieval, streaming, and cursor lifecycle | 766–829 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 10. Transactions, savepoints, and distributed transaction support | 830–923 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 11. Concurrency and native asynchronous operations | 924–997 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 12. Connection pooling and connection lifecycle management | 998–1107 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 13. PostgreSQL-specific functionality, diagnostics, and lower-level interfaces | 1108–1223 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 14. Ecosystem integration and responsibility boundaries | 1224–1311 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 15. Performance mechanisms and architectural tradeoffs | 1312–1355 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 16. Important limitations and design distinctions | 1356–1382 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 17. Version-specific developments and feature maturity | 1383–1408 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 18. Primary-source research map | 1409–1443 | Supporting context: [L](transactions-pools-and-outcomes.md) |
| Main · 19. Overall architectural significance | 1444–1473 | Supporting context: [L](transactions-pools-and-outcomes.md) |
| Addendum · 1. Dynamic connection configuration and operational pool management | 1474–1583 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 2. Deliberate transaction rollback and observable transaction outcomes | 1584–1664 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 3. Additional type-adaptation capabilities and consequential type semantics | 1665–1829 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Addendum · 4. Binary protocol control, statement preparation, and runtime capability detection | 1830–1920 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Addendum · 5. COPY serialization and result-preserving batch execution | 1921–1989 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 6. Streaming results, server-side cursor navigation, and resource ownership | 1990–2087 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Addendum · 7. Pipeline synchronization and failure recovery | 2088–2145 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Addendum · 8. Cancellation, notifications, and independent protocol inspection | 2146–2271 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 9. Source-version and editorial qualifications | 2272–2307 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |

### psycopg-pool — 1,942 lines

[Complete overview](../../../../libraries/postgresql/psycopg-pool.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Purpose and architectural model | 25–71 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 2. Installation, dependencies, and execution model | 72–120 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 3. Connection ownership, borrowing, and transaction semantics | 121–210 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 4. Pool sizing, capacity management, and admission control | 211–236 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 5 | 237–240 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 5 | 241–244 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 0 | 245–248 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 0 | 249–323 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 5. Connection lifecycle customization | 324–429 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 6. Null pools: connection admission without persistent retention | 430–497 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 7. Failure recovery and connection health management | 498–618 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 8. Runtime pool operations and reconfiguration | 619–785 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 9. Observability, instrumentation, and pool diagnostics | 786–895 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 10. SQLAlchemy integration: one connection manager, two abstraction layers | 896–990 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 11. Typed connections, customization, and composition with Psycopg | 991–1125 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 12. Version-specific capabilities and current limitations | 1126–1193 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 13. Architectural combinations and selection tradeoffs | 1194–1219 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Main · 14. Overall assessment of the library's capabilities | 1220–1249 | Supporting context: [L](transactions-pools-and-outcomes.md) |
| Addendum · A1. Zero-minimum persistent pools: a third connection-management strategy | 1250–1301 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A2. Connection growth and maintenance scheduling | 1302–1377 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A3. Connection retirement, idle contraction, and runtime resizing | 1378–1456 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A4. Connection ownership and validation semantics | 1457–1559 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A5. `close_returns` compatibility is narrower than the common constructor interface suggests | 1560–1608 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A6. Null-pool foreground establishment and acquisition latency | 1609–1701 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A7. Observability: measurement coverage and statistical interpretation | 1702–1830 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A8. Runtime state inspection and lifecycle compatibility | 1831–1903 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · A9. Editorial corrections to the parent reference | 1904–1913 | Used foundation / conditional extensions: [L](transactions-pools-and-outcomes.md) |
| Addendum · Primary-source references | 1914–1942 | Supporting context: [L](transactions-pools-and-outcomes.md) |

### alembic — 2,418 lines

[Complete overview](../../../../libraries/postgresql/alembic.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Conceptual model and capability map | 26–78 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 2. Revision graph, dependency management, and schema history | 79–199 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 3. Migration operations and the DDL abstraction | 200–292 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 4. Schema autogeneration and metadata comparison | 293–428 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 5. Structured migration generation, rewriting, and plugins | 429–616 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 6. Batch migrations, table reconstruction, and constraint identity | 617–715 | Conditional: [E](schema-evolution-and-catalog-admission.md) |
| Main · 7. Online execution, offline SQL generation, and transaction semantics | 716–822 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 8. Programmatic control, migration-state inspection, and validation | 823–968 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 9. Multiple databases, schemas, tenants, and asynchronous execution | 969–1062 | Conditional: [E](schema-evolution-and-catalog-admission.md) |
| Main · 10. Performance, reliability, and operational boundaries | 1063–1158 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 11. Ecosystem integrations and capability boundaries | 1159–1238 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 12. Version-specific capabilities and compatibility | 1239–1302 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 13. Architectural significance | 1303–1344 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 14. Primary-source reference map | 1345–1382 | Supporting context: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · Scope and orientation | 1383–1402 | Supporting context: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 1. Additional autogeneration limitations and schema normalization | 1403–1483 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 2. Column-operation semantics and PostgreSQL-native DDL | 1484–1677 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 3. Programmable migration environments and configuration | 1678–1832 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 4. Additional structured-operation and dialect extension APIs | 1833–1958 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 5. Additional execution semantics and backend-specific behavior | 1959–2120 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 6. Historical migration testing and verification | 2121–2183 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 7. SQLAlchemy 2.1 integration: additional schema DDL and lifecycle semantics | 2184–2281 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 8. Alembic 1.20.1 corrections and unreleased 1.20.2 behavior | 2282–2390 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 9. Capability and version boundaries | 2391–2418 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |

### pgpq — 1,320 lines

[Complete overview](../../../../libraries/postgresql/pgpq.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Overview and architectural role | 5–63 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 2. Python API and encoding lifecycle | 64–146 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 3. Type system and schema translation | 147–235 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 4. Nested Arrow data: PostgreSQL arrays and composite types | 236–329 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 5. Custom encoders, JSONB, and the arrow-json companion | 330–433 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 6. Integration architecture and complementary libraries | 434–533 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 7. Performance characteristics and execution mechanics | 534–590 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 8. Correctness boundaries, error handling, and limitations | 591–668 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 9. Rust crate, packaging, and version considerations | 669–703 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 10. Overall capability boundary | 704–741 | Supporting context: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 1. PostgreSQL schema fidelity and generated-object lifecycle | 742–879 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 2. Batch validation, stream integrity, and resource behavior | 880–1009 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 3. String encoders, JSONB representation, and semantic preservation | 1010–1131 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 4. Rust and Python extension boundaries | 1132–1248 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 5. Remaining Arrow-type boundaries and operational inspection | 1249–1320 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |

### adbc-driver-postgresql — 1,506 lines

[Complete overview](../../../../libraries/postgresql/adbc-driver-postgresql.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Purpose, architecture, and capability map | 5–64 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 2. Python interfaces and connection model | 65–101 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 3. Query execution and Arrow result delivery | 102–187 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Main · 4. Arrow bulk ingestion and table creation | 188–231 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 5. PostgreSQL–Arrow type system and semantic fidelity | 232–397 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 6. Type discovery, OID resolution and connection startup | 398–445 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Main · 7. Database introspection and statistics | 446–520 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Main · 8. Transactions, connection state and execution control | 521–593 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Main · 9. Integration pathways and ecosystem boundaries | 594–672 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 10. Deployment compatibility and important limits | 673–713 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Main · 11. Version-specific changes and authoritative references | 714–772 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 1. Parameterized result queries and execution mechanics | 773–859 | Mixed; see feature dispositions: [R](relational-operations-and-preparation.md) |
| Addendum · 2. Target-aware bulk ingestion and native COPY encoding | 860–920 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 3. Additional PostgreSQL–Arrow type semantics | 921–1001 | Mixed; see feature dispositions: [T](domain-types-and-invariants.md) |
| Addendum · 4. Driver discovery, manifests and connection profiles | 1002–1089 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 5. Arrow interoperability without mandatory PyArrow materialization | 1090–1145 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 6. Metadata completeness and schema introspection boundaries | 1146–1194 | Mixed; see feature dispositions: [E](schema-evolution-and-catalog-admission.md) |
| Addendum · 7. Transaction, session and connection-lifecycle semantics | 1195–1271 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 8. Structured diagnostics and additional native execution controls | 1272–1367 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 9. Direct integration with DuckDB's ADBC community extension | 1368–1446 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |
| Addendum · 10. Inherited `libpq` connection and security capabilities | 1447–1488 | Mixed; see feature dispositions: [L](transactions-pools-and-outcomes.md) |
| Addendum · 11. Capability composition and architectural implications | 1489–1506 | Mixed; see feature dispositions: [A](typed-copy-and-arrow-transfer.md) |

### pgvector — 955 lines

[Complete overview](../../../../libraries/postgresql/pgvector.md). Main body and addendum both included where present.

| Part and section | Lines | Disposition and topic |
| --- | --- | --- |
| Main · 1. Architectural orientation | 19–44 | Supporting context: [V](typed-retrieval-and-vector-search.md) |
| Main · 2. Vector types, representations, and numerical semantics | 45–133 | Mixed; see feature dispositions: [V](typed-retrieval-and-vector-search.md) |
| Main · 3. Driver integration and PostgreSQL type adaptation | 134–203 | Mixed; see feature dispositions: [V](typed-retrieval-and-vector-search.md) |
| Main · 4. ORM integration and declarative query composition | 204–325 | Conditional: [V](typed-retrieval-and-vector-search.md) |
| Main · 5. Similarity search and approximate indexing | 326–477 | Used exact route / conditional extensions: [V](typed-retrieval-and-vector-search.md) |
| Main · 6. Advanced vector transformations and reduced-precision indexing | 478–571 | Mixed; see feature dispositions: [V](typed-retrieval-and-vector-search.md) |
| Main · 7. Higher-order retrieval architectures | 572–679 | Used exact route / conditional extensions: [V](typed-retrieval-and-vector-search.md) |
| Main · 8. Data lifecycle, performance, and operations | 680–787 | Mixed; see feature dispositions: [V](typed-retrieval-and-vector-search.md) |
| Main · 9. Important semantic constraints and boundaries | 788–860 | Mixed; see feature dispositions: [V](typed-retrieval-and-vector-search.md) |
| Main · 10. Version-sensitive behavior and compatibility | 861–904 | Mixed; see feature dispositions: [V](typed-retrieval-and-vector-search.md) |
| Main · 11. Capability synthesis | 905–937 | Supporting context: [V](typed-retrieval-and-vector-search.md) |
| Main · Primary source reference map | 938–955 | Supporting context: [V](typed-retrieval-and-vector-search.md) |

## Capability families retained beyond the immediate shortlist

| Family | Disposition and re-entry question |
| --- | --- |
| ORM mappings, composites, dataclass/attrs integration, inheritance, hybrids, expression properties, association proxies/objects and mutable/ordered collections | Conditional structural alternative under T: is there a concrete domain object graph whose full assembly/persistence lifecycle becomes simpler? |
| ORM loaders, UoW/cascades, versioning, WriteOnlyMapped, loader criteria, session scoping, registry/type-annotation events, interception and frozen-result merging | Conditional on a justified ORM consumer; do not investigate each as an independent adoption project |
| SQLAlchemy schemas/translation, async, sharding, engine plugins, hints and other dialects | Conditional on a real participant/deployment/query requirement; the personal PostgreSQL workload supplies no automatic trigger |
| pglast printer registries, formatting/safety-belt, comments, keyword inspection and pgpp | Used ordinary printers; deeper customization only for a missing serialization/diagnostic consumer. Round-trip AST equality is not semantic equivalence |
| pglast PL/pgSQL inspection, JSON/Protobuf parse/deparse, fingerprints and cross-language pg_query interchange | Conditional procedural, diagnostic or cross-process need. Fingerprints normalize distinctions and cannot own semantic identity; procedural dictionaries lack the SQL typed-AST ecosystem |
| SQLGlot optimizer passes, diff, serialization, anonymization, custom dialect/plugins and parser/generator extension | Conditional impact/portability/diagnostic consumer. Preserve NULL/volatile/helper semantics, unknowns and version-coupled AST boundaries |
| SQLGlot specialized generator transforms: QUALIFY/DISTINCT ON/windows, joins, UNNEST/EXPLODE/generate_series, recursion, percentile syntax, booleans/epoch, identifier/pivot fields, partition/schema movement, temporary CTAS and nested struct construction | Covered in main/addendum; conditional on an actually required source/target construct. A complete transform catalog is not an equivalence guarantee or a reason for a portability project |
| SQLGlot PIVOT/UNPIVOT output schemas, pipe SQL, temporal-format/subsecond utilities | Conditional on an admitted operator or source format. Names/format tokens are not complete result typing or temporal validation |
| SQLGlot Plan/PythonExecutor, SQLFrame, compiled acceleration | No selected alternative executor/DataFrame consumer or serious performance question; retain as conditional territory |
| Psycopg row factories, adaptation contexts, value-sensitive dumpers, NumPy/UUID/network/hstore, temporal infinities and experimental spatial adapters | Unused/conditional by actual value consumer; scalar/row construction cannot replace semantic admission or source precision |
| Psycopg RawCursor/ClientCursor, t-strings, named/server/refcursors, held/scrollable/chunked streams, result navigation and offline COPY writers | Conditional protocol, syntax or result-lifetime need; retain borrowing and transaction-settlement obligations |
| Pool async/custom connections, dynamic credentials, zero-minimum/null strategies, health/reset/drain/resize and metrics | Current regular pool integration used; additional behavior needs a concrete invalidation/capacity need. Selected null-pool close_returns limitation defeats transparent substitution |
| Psycopg notifications/notices, safe cancellation/capability checks, PGconn/PGresult tracing, libpq services/security/multihost and two-phase | Notices/cancellation already integrated; other mechanisms need a consumer/failure question. Notification is not durable replay; retry/commit knowledge stays operation-owned |
| Alembic branches/merges/multiple bases/depends_on, version inspection, config/templates/runtime kwargs and callbacks | Singular caller-owned migration lifecycle used; richer graphs/runtime variants only for a real independently evolving history. Runtime kwargs cannot silently change the meaning of a revision |
| Alembic offline/batch reconstruction/multi-database/async, pytest-alembic, Alembic Utils and enum extensions | Conditional demonstrated gap. Existing native checks exceed generic at-head inspection; no new gate or mandatory downgrade compatibility |
| pgpq generated schema/DDL and composites, nested OIDs, Rust traits/BytesMut/encoder APIs | Conditional actual nested transport or Rust consumer; generated objects need namespace/lifetime/constraint fidelity and high-level Python encoders are not arbitrary plugin interfaces |
| arrow-json companion | Not selected; conditional nested JSON bridge with explicit top-level null/serialization treatment |
| ADBC target-aware ingestion, create/append/create_append/replace, temporary targets and native COPY coercion | Conditional complete input operation, not a second speculative publisher |
| ADBC parameter schemas, bound result streams, direct C interfaces and connection cloning | Conditional consumer; distinguish schema negotiation, incremental COPY, bound PGresult buffering and session/snapshot ownership |
| ADBC metadata/statistics/info, resolver modes, driver manifests/profiles and DuckDB community extension | Existing description/capture used. Metadata underuse and lifetime consistency have concrete leads; broader configuration/federation requires a selected consumer and one settings authority |
| pgvector VECTOR/HALFVEC/SPARSEVEC/BIT, metric comparators, aggregates, normalization, arrays and binary codecs | VECTOR/cosine used; typed transient binding is concrete underuse. Other operations need model-owned metric/shape semantics |
| pgvector HNSW/IVFFlat, iterative/filtered search, half precision, quantization/reranking, subvectors, sparse/multivector/late interaction | Conditional existing scale/quality trigger or new actual retrieval consumer. Approximate ordering/reranking does not imply exact recall |
| pgvector other ORMs/drivers, ML/cross-encoder examples, replicas/partitioning/sharding | Conditional participant/functional need; no independent adoption priority established |

## Corrections and evidence limits

ADBC's addendum supersedes its main text's unsupported parameterized-SELECT claim. Bound output
execution is not COPY streaming. SQLAlchemy with_cols is static casting, not runtime validation.
SQLGlot schema UDF lookup is not automatic anonymous-function annotation or native overload binding;
selected annotate_types does not call get_udf_type. Pool3.3.3 async drain exists, but null-pool
close_returns behavior remains different. Read parent topics before applying overview examples.

Production-source searches exclude frozen historical migration bodies as current consumers and do
not establish runtime execution. Other frameworks, independently locked providers, optional extras
and remote deployment were not exhaustively attributed. Unknown metadata is retained as unknown.
No timing, throughput, capacity, quality gain or absent-feature claim follows from section coverage.
