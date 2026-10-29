# Semantic PostgreSQL model

No—a constantly evolving schema does not necessarily mean you need a graph database. PostgreSQL can accommodate substantial evolution without repeatedly altering its physical schema.

In fact, what you're describing sounds like a strong candidate for a hybrid relational–graph data model within PostgreSQL, particularly if most of the underlying data is structured and the evolution comes from discovering new entities, attributes, or relationships.

The important distinction is between:

1. Physical schema evolution: Adding tables, columns, foreign keys, or indexes through PostgreSQL migrations.
2. Logical schema evolution: Discovering additional entity types, properties, relationships, and constraints, represented as data inside existing tables.
3. Connectivity evolution: Discovering new relationships between existing entities, without changing either schema.

The second and third can happen continuously without physical schema migrations.

For your situation, I would start by separating the relational structure of the data from the evolving knowledge of how that data is connected.

## 1. Four architectural approaches

| Approach                                | How it accommodates evolution                                    | Main tradeoff                                                                  |
| --------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Conventional relational tables          | New columns, link tables, or migrations                          | Excellent typing and integrity; cumbersome for frequent structural changes     |
| PostgreSQL + `JSONB`                    | New attributes appear without new columns                        | Flexible properties, but weaker built-in structural guarantees                 |
| PostgreSQL + entity/relationship tables | New entity and relationship types become rows rather than tables | Flexible connectivity, but requires explicit semantic modeling                 |
| Native graph database                   | Dynamically evolving nodes, edges, and properties                | Natural graph traversal, but may complicate conventional relational operations |

My preferred starting point is the third approach, combined selectively with the second.

PostgreSQL supports indexed `JSONB` queries alongside ordinary relational tables, making this a supported combination rather than an unusual workaround.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

PostgreSQL



## 2. A PostgreSQL architecture that avoids continuous migrations

I would separate the model into three layers:

Semantic schema registry

Entity types · Attribute definitions · Relationship types · Constraints

Relational core

Typed tables · Stable columns · Foreign keys · SQL

Dynamic connectivity

Entities · Edges · JSONB properties · Discovery metadata

Unified query layer

SQL joins · Recursive traversal · Views · Graph projections

The physical tables can remain stable even as the logical model grows.

| Table                  | Responsibility                                                           |
| ---------------------- | ------------------------------------------------------------------------ |
| `entity_registry`      | Stable identity for every entity, including its type                     |
| `relationship`         | Source entity, target entity, relationship type, and optional properties |
| `relationship_type`    | Registry of permissible relationship meanings and constraints            |
| `attribute_definition` | Definitions, types, and validation rules for evolving attributes         |
| Domain-specific tables | Conventional PostgreSQL tables for established, strongly typed data      |

For example, discovering that two previously unrelated entity classes have a `depends_on` relationship means adding a relationship-type definition and relationship records—not adding a foreign key or creating a new table.

The important feature is that the database schema can be stable while the semantic schema is extensible.

## 3. How to handle the different forms of evolution

| What changes?                                    | Recommended mechanism                            | PostgreSQL migration needed? |
| ------------------------------------------------ | ------------------------------------------------ | ---------------------------- |
| New entity instance                              | Insert into existing entity/domain tables        | No                           |
| New entity classification                        | Insert into entity-type registry                 | No                           |
| New relationship type                            | Insert into relationship-type registry           | No                           |
| New discovered relationship                      | Insert into edge table                           | No                           |
| New optional attribute                           | `JSONB` plus an attribute definition             | No                           |
| New validation rule                              | Update semantic registry and validation logic    | Usually no                   |
| Attribute becomes critical to filtering or joins | Add targeted indexing or promote to typed column | Sometimes                    |
| New performance-critical relational structure    | New specialized table, index, or constraint      | Potentially                  |

There is one critical design principle here: relationships should generally be represented as first-class relational records, not merely IDs embedded inside JSONB.

That preserves referential integrity, makes relationships independently indexable, and allows you to attach provenance, confidence, temporal validity, and other metadata.

For indexing, PostgreSQL provides ordinary B-tree indexes for relationship endpoints and GIN or expression indexes for JSONB properties. It also supports `WITH RECURSIVE` queries, including cycle detection, for navigating relationships of variable depth.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

PostgreSQL

+1



## 4. When does a graph database actually become advantageous?

The deciding factor is more often the query workload than the rate of schema evolution.

| Workload                                            | PostgreSQL                                     | Native graph database              |
| --------------------------------------------------- | ---------------------------------------------- | ---------------------------------- |
| Structured filtering, joins, aggregation            | Excellent                                      | Depends on graph engine            |
| Frequent additions of relationship types            | Excellent with generalized edges               | Excellent                          |
| One-to-three-hop relationship lookups               | Often very efficient with indexes              | Also efficient                     |
| Deep, variable-length graph traversal               | Possible, but potentially expensive            | Often more natural and optimized   |
| Shortest paths, graph algorithms, large expansions  | May require extensions or external computation | Often stronger native capabilities |
| Strong relational constraints and transaction logic | Particularly strong                            | Engine-dependent                   |

A graph database such as SurrealDB or Neo4j becomes more compelling if connectivity itself is the dominant access pattern, especially when complex traversals are frequent.

There are also intermediate options. Apache AGE adds graph-query capabilities to PostgreSQL, so graph-oriented querying does not necessarily require moving to a separate database engine. Compatibility with your PostgreSQL version should be checked.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://age.apache.org\&sz=32)

age.apache.org



## 5. The semantic model is the more important architectural decision

One potentially valuable approach, especially given the dynamic discovery process, is to use LinkML as the evolving semantic model, rather than equating your domain schema with PostgreSQL DDL.

LinkML can describe classes, properties, constraints, and relationships independently of whether the data lives in relational, JSON, or graph storage. Its validation framework also supports multiple representations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



That suggests:

- LinkML / semantic registry: Defines what entities, attributes, and relationships mean.
- PostgreSQL: Stores structured facts, dynamic relationships, and their provenance.
- Rust runtime: Performs discovery, validation, transformations, and optionally specialized graph computations.

This allows new discoveries to extend the model without automatically triggering database migrations. You can subsequently promote frequently queried attributes or relationships into optimized relational structures when justified.

The main cost is that dynamically defined constraints require explicit validation or enforcement logic; PostgreSQL cannot automatically enforce every changing semantic rule as though it were a statically declared SQL constraint.

## Recommendation

I would retain PostgreSQL as the primary structured store and add a first-class, semantically governed relationship layer, rather than choosing a graph database simply because connectivity is evolving.

The key is to avoid allowing every new semantic discovery to require a physical schema change.

The question that would most influence my recommendation is this:

When you say the schema evolves, are you predominantly discovering new relationships between existing kinds of entities, or are you also continuously discovering entirely new entity types and attributes?

The former strongly favors a conventional relational core with a generalized relationship table. The latter favors a more comprehensive metadata-driven architecture, although it still does not necessarily require a graph database.