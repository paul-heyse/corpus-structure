"""Deterministic native authoring products; deployment executes frozen revisions only."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256

from pglast import ast, parse_sql
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import (
    AddConstraint,
    CheckConstraint,
    CreateIndex,
    CreateTable,
    UniqueConstraint,
)

from .metadata import metadata


def selected_fact_query():
    """The fixed accepted-fact projection uses the same scoped relationship keys."""
    from sqlalchemy import and_, select

    fact, selection = (
        metadata.tables["data.fact"].alias("f"),
        metadata.tables["data.selection"].alias("s"),
    )
    return select(fact).select_from(
        fact.join(
            selection,
            and_(
                selection.c.realization_id == fact.c.realization_id,
                selection.c.release_id == fact.c.release_id,
                selection.c.fact_id == fact.c.fact_id,
            ),
        )
    )


@dataclass(frozen=True)
class NativeProduct:
    name: str
    content: bytes

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


def physical_products() -> tuple[NativeProduct, ...]:
    """Render fixed DDL from the single physical model, in dependency order."""
    pg = dialect()
    products = []
    for relation in sorted(metadata.tables.values(), key=lambda item: item.fullname):
        products.append(
            NativeProduct(
                relation.fullname,
                (
                    str(
                        CreateTable(relation, include_foreign_key_constraints=[]).compile(
                            dialect=pg
                        )
                    ).strip()
                    + ";\n"
                ).encode(),
            )
        )
        for index in sorted(relation.indexes, key=lambda item: str(item.name or "")):
            products.append(
                NativeProduct(
                    str(index.name),
                    (str(CreateIndex(index).compile(dialect=pg)).strip() + ";\n").encode(),
                )
            )
    for relation in sorted(metadata.tables.values(), key=lambda item: item.fullname):
        for constraint in sorted(
            relation.foreign_key_constraints, key=lambda item: str(item.name or "")
        ):
            products.append(
                NativeProduct(
                    relation.fullname + "/" + str(constraint.name),
                    (
                        str(
                            AddConstraint(constraint, isolate_from_table=False).compile(dialect=pg)
                        ).strip()
                        + ";\n"
                    ).encode(),
                )
            )
    return tuple(products)


def function_bodies(sql: str) -> dict[str, str]:
    """Inspect emitted function declarations structurally; never scrape a live deployment."""
    result = {}
    for raw in parse_sql(sql):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt):
            name = ".".join(part.sval for part in statement.funcname or ())
            body = next(option for option in statement.options or () if option.defname == "as")
            result[name] = body.arg[0].sval
    return result


def edge_projection(edges: Iterable[tuple[str, str, str, str]]) -> NativeProduct:
    """Finite edges are ordered model data, never inferred from kernel source."""
    from .identity import canonical_bytes

    return NativeProduct("execution-edges.json", canonical_bytes(sorted(edges)))


def closure_products(model=None) -> tuple[NativeProduct, ...]:
    """Author forward products from reviewed templates and the trusted model.

    The result is written into a new revision by an explicit authoring command. Historical
    migrations never import this module. The previous descriptor is a bounded custody input
    for unchanged kernels, not an oracle of the changed kernels' behavior.
    """
    import json
    from pathlib import Path
    from typing import Any

    import yaml
    from pglast.stream import RawStream
    from sqlalchemy.sql.ddl import CreateView, sort_tables

    from .composed import composed_dependencies
    from .contracts import compile_execution_model, trusted_execution_inputs
    from .identity import canonical_bytes
    from .metadata import PHYSICAL_MODEL, PHYSICAL_MODEL_ID
    from .types import ResolvedDependencies

    source = Path(__file__).with_name("sql")
    declarations = yaml.safe_load(PHYSICAL_MODEL.read_bytes())["classes"]
    classified = {
        f"{definition['in_subset'][0]}.{name}": definition.get("annotations", {}).get(
            "ph:immutability"
        )
        for name, definition in declarations.items()
        if definition.get("annotations", {}).get("ph:immutability")
    }
    intrinsic = [
        relation.name
        for relation in sort_tables(
            [metadata.tables[name] for name, mode in classified.items() if mode == "intrinsic"]
        )
    ]
    new_tables = {
        "sem." + name
        for name in (
            "execution_operation",
            "execution_transition",
            "execution_edge",
            "operation_effect",
            "transition_effect",
            "operation_property_role",
            "scientific_decision_rule",
        )
    }
    guards = []
    for name, mode in classified.items():
        if name not in new_tables:
            continue
        guards.append(
            "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON "
            f"{name}"
            " FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();"
        )
        if mode == "intrinsic":
            guards.append(
                "CREATE TRIGGER release_finalized BEFORE INSERT ON "
                f"{name}"
                " FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert();"
            )
    from .routines import _transport_sql, stage_disposal_sql

    kernels = (
        "SET LOCAL ROLE corpus_sem_publisher;\n"
        + source.joinpath("execution_projection_check.sql").read_text()
        + "\n"
        + (
            source.joinpath("closure.sql")
            .read_text()
            .replace("{intrinsic_relations}", ",".join("'" + name + "'" for name in intrinsic))
            .replace("-- {immutability_guards}", "\n".join(guards))
            .replace("{transport_disposal}", stage_disposal_sql())
        )
    )
    kernels += "\n" + "\n".join(
        f"GRANT SELECT ON {name} TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;"
        for name in sorted(new_tables)
    )
    from dataclasses import fields

    from .publication import STAGE_TYPES

    inference_relations = {"typed_value", "fact", "selection", "derivation", "derivation_premise"}
    kernels += "\n" + source.joinpath("derived_publication.sql").read_text().replace(
        "{accepted_empty_stages}",
        " OR ".join(
            "EXISTS(SELECT FROM pg_temp.sp_" + name + ")"
            for name in STAGE_TYPES
            if name not in inference_relations
        ),
    )
    kernels += "\n" + source.joinpath("exclusions.sql").read_text()
    create, verify, content, insert = _transport_sql("corpus_sem_writer")
    transport = source.joinpath("transport.sql").read_text()
    for marker, fragment in (
        ("create", create),
        ("verify", verify),
        ("content", content),
        ("insert", insert),
    ):
        transport = transport.replace("{" + marker + "}", fragment)
    kernels = "\n".join(
        line
        for line in kernels.splitlines()
        if not line.startswith("CREATE TRIGGER native_float_codec")
    )
    kernels += "\n" + transport
    kernels += "\n" + source.joinpath("execution_projection.sql").read_text()
    kernels += (
        "\nSET LOCAL ROLE __MIGRATION_OWNER__;\n"
        + source.joinpath("execution_guards.sql").read_text()
        + "\nSET LOCAL ROLE corpus_sem_publisher;\n"
    )

    row_type, types = STAGE_TYPES["typed_value"]
    signatures = ",".join(
        "'" + column.name + ":" + kind + "'"
        for column, kind in zip(fields(row_type), types, strict=True)
    )
    typed_verify = (
        (
            "IF NOT EXISTS(SELECT FROM pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND "
            "c.relname='sp_typed_value' AND c.relkind='r' AND c.relpersistence='t' AND c.relown"
            "er=current_user::regrole AND (SELECT array_agg(stage_attr.attname||':'||format_typ"
            "e(stage_attr.atttypid,stage_attr.atttypmod) ORDER BY stage_attr.attnum) FROM pg_at"
            "tribute stage_attr WHERE stage_attr.attrelid=c.oid AND stage_attr.attnum>0 AND NOT"
            " stage_attr.attisdropped)=ARRAY["
        )
        + signatures
        + "]) THEN RAISE EXCEPTION 'untrusted typed-value staging'; END IF;"
    )
    kernels = kernels.replace("{typed_value_stage_verify}", typed_verify)
    model = compile_execution_model(trusted_execution_inputs()) if model is None else model
    for operation in model.operations:
        model.require_operation(operation.id)
    edge_sql = ""  # Finite edges are immutable release rows consumed by stable guards.
    physical = "\n".join(
        product.content.decode()
        for product in physical_products()
        if product.name in new_tables
        or any(product.name.startswith(name + "/") for name in new_tables)
    )
    physical += edge_sql
    view_query = selected_fact_query()
    physical += (
        "\n"
        + str(
            CreateView(view_query, "selected_fact", schema="data", or_replace=True).compile(
                dialect=dialect()
            )
        )
        + ";\n"
    )
    physical += "\nGRANT CREATE ON SCHEMA sem TO corpus_sem_publisher;\n"
    for name in sorted(new_tables):
        physical += f"ALTER TABLE {name} OWNER TO corpus_sem_publisher;\n"

    physical += (
        "GRANT SELECT,INSERT,TRIGGER ON ALL TABLES IN SCHEMA sem TO corpus_sem_publisher WITH G"
        "RANT OPTION;\n"
    )
    physical += (
        "GRANT SELECT,TRIGGER ON ALL TABLES IN SCHEMA data TO corpus_sem_publisher WITH GRANT O"
        "PTION;\n"
    )
    physical += (
        "GRANT SELECT ON ALL TABLES IN SCHEMA ops TO corpus_sem_publisher WITH GRANT OPTION;\n"
    )
    physical += "GRANT USAGE ON SCHEMA sem TO corpus_sem_publisher WITH GRANT OPTION;\n"
    physical += (
        "DO $acl$ BEGIN EXECUTE format('REVOKE TEMP ON DATABASE %I FROM PUBLIC,corpus_sem_write"
        "r,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator',current_database()); EXE"
        "CUTE format('GRANT TEMP ON DATABASE %I TO corpus_sem_publisher',current_database()); E"
        "ND $acl$;\n"
    )
    physical += "GRANT USAGE ON SCHEMA sem,data,ops TO corpus_sem_admitter;\n"
    physical += "SET LOCAL ROLE corpus_sem_publisher;\n"
    physical += (
        "DO $reference$ BEGIN IF to_regclass('pg_temp.semantic_physical_checks') IS NOT NULL TH"
        "EN RAISE EXCEPTION 'preexisting physical contract workspace'; END IF; END $reference$;"
        "\nCREATE TEMP TABLE semantic_physical_checks(relation_name text,constraint_name text,e"
        "xpression text) ON COMMIT DROP;\nGRANT SELECT,INSERT ON pg_temp.semantic_physical_chec"
        "ks TO corpus_sem_publisher,SESSION_USER;\n"
    )
    check_sources = []
    for relation in sorted(metadata.tables.values(), key=lambda item: item.fullname):
        checks = sorted(
            (check for check in relation.constraints if isinstance(check, CheckConstraint)),
            key=lambda item: str(item.name),
        )
        uniques = sorted(
            (check for check in relation.constraints if isinstance(check, UniqueConstraint)),
            key=lambda item: str(item.name),
        )
        if not checks and not uniques:
            continue
        qualified = relation.fullname
        commands = []
        if checks:
            from sqlalchemy import Column, MetaData, Table

            reference = Table(
                "semantic_check_reference",
                MetaData(),
                *(Column(column.name, column.type) for column in relation.columns),
                prefixes=["TEMPORARY"],
            )
            reference_ddl = (
                str(CreateTable(reference).compile(dialect=dialect())).strip().replace("'", "''")
            )
            commands.append(
                (
                    "IF to_regclass('pg_temp.semantic_check_reference') IS NOT NULL THEN RAISE "
                    "EXCEPTION 'preexisting migration CHECK reference'; END IF; EXECUTE '"
                )
                + reference_ddl
                + "';"
            )
            for check in checks:
                rendered = dialect().identifier_preparer.format_constraint(check)
                if rendered is None:
                    raise ValueError("physical CHECK has no name")
                desired = rendered.strip('"')
                reference_ddl = (
                    str(AddConstraint(check, isolate_from_table=False).compile(dialect=dialect()))
                    .replace(
                        "ALTER TABLE " + qualified, "ALTER TABLE pg_temp.semantic_check_reference"
                    )
                    .replace("'", "''")
                )
                commands.append("EXECUTE '" + reference_ddl + "';")
                check_sources.append((qualified, desired, str(check.sqltext)))
                commands.append(
                    "INSERT INTO pg_temp.semantic_physical_checks SELECT '"
                    f"{qualified}"
                    "','"
                    f"{desired}"
                    "',pg_get_expr(conbin,conrelid) FROM pg_constraint WHERE conrelid='pg_t"
                    "emp.semantic_check_reference'::regclass AND conname='"
                    f"{desired}"
                    "';"
                )
                commands.append(
                    "SELECT conname INTO n FROM pg_constraint WHERE conrelid='"
                    f"{qualified}"
                    "'::regclass AND contype='c' AND pg_get_expr(conbin,conrelid)=(SELECT p"
                    "g_get_expr(conbin,conrelid) FROM pg_constraint WHERE conrelid='pg_temp"
                    ".semantic_check_reference'::regclass AND conname='"
                    f"{desired}"
                    "');"
                )
                if qualified == "eval.document_split":
                    replacement = str(
                        AddConstraint(check, isolate_from_table=False).compile(dialect=dialect())
                    ).replace("'", "''")
                    commands.append(
                        "IF n IS NULL THEN ALTER TABLE eval.document_split DROP CONSTRAINT "
                        "IF EXISTS ck_document_split_physical_23de252598; EXECUTE '"
                        f"{replacement}"
                        "'; n:='"
                        f"{desired}"
                        "'; END IF;"
                    )
                commands.append(
                    "IF n IS NULL THEN RAISE EXCEPTION 'unmatched physical CHECK requires r"
                    "eviewed forward repair: "
                    f"{qualified}"
                    "."
                    f"{desired}"
                    "'; ELSIF n<>'"
                    f"{desired}"
                    "' THEN EXECUTE format('ALTER TABLE "
                    f"{qualified}"
                    " RENAME CONSTRAINT %I TO %I',n,'"
                    f"{desired}"
                    "'); END IF;"
                )
            commands.append("DROP TABLE pg_temp.semantic_check_reference;")
        for unique in uniques:
            columns = ",".join("'" + column.name + "'" for column in unique.columns)
            rendered = dialect().identifier_preparer.format_constraint(unique)
            if rendered is None:
                raise ValueError("physical unique key has no name")
            desired = rendered.strip('"')
            commands.append(
                "SELECT conname INTO n FROM pg_constraint c WHERE c.conrelid='"
                f"{qualified}"
                "'::regclass AND c.contype='u' AND ARRAY(SELECT a.attname::text FROM unnest"
                "(c.conkey) WITH ORDINALITY cols(num,pos) JOIN pg_attribute a ON a.attrelid"
                "=c.conrelid AND a.attnum=cols.num ORDER BY cols.pos)=ARRAY["
                f"{columns}"
                "];"
            )
            commands.append(
                "IF n IS NULL THEN RAISE EXCEPTION 'missing physical unique key "
                f"{qualified}"
                "'; ELSIF n<>'"
                f"{desired}"
                "' THEN EXECUTE format('ALTER TABLE "
                f"{qualified}"
                " RENAME CONSTRAINT %I TO %I',n,'"
                f"{desired}"
                "'); END IF;"
            )
        physical += (
            (
                "\nDO $repair$ DECLARE n text; owner_name text; previous_name text:=current_use"
                "r; BEGIN SELECT pg_get_userbyid(relowner) INTO owner_name FROM pg_class WHERE "
                "oid='"
                f"{qualified}"
                "'::regclass; EXECUTE format('SET LOCAL ROLE %I',owner_name); "
            )
            + " ".join(commands)
            + " EXECUTE format('SET LOCAL ROLE %I',previous_name); END $repair$;\n"
        )
    check_source_digest = sha256(canonical_bytes(check_sources)).hexdigest()
    physical += (
        "INSERT INTO sem.physical_contract SELECT '"
        + PHYSICAL_MODEL_ID
        + (
            "',COALESCE(jsonb_agg(jsonb_build_object('relation',relation_name,'name',constraint"
            "_name,'expression',expression) ORDER BY relation_name,constraint_name),'[]'::jsonb"
            "),'"
        )
        + check_source_digest
        + "' FROM pg_temp.semantic_physical_checks;\nDROP TABLE pg_temp.semantic_physical_checks;\n"
    )
    descriptor: dict[str, Any] = json.loads(source.joinpath("native_descriptor.json").read_bytes())
    descriptor["physical_checks_source_digest"] = check_source_digest
    descriptor["base_derived_protocol"] = {
        "operation": "publish_inference",
        "projection": "accepted",
        "universe": "eligible_positive_accepted",
        "values": "exact",
        "target": "same_realization",
    }
    descriptor["physical_relations"] = sorted(metadata.tables)
    descriptor["views"] = [
        {"relation": "data.selected_fact", "query": str(view_query.compile(dialect=dialect()))}
    ]
    from .effect_support import SUPPORTED_EFFECT_VERSIONS, SUPPORTED_EFFECTS

    descriptor["supported_effects"] = {
        operation.id: {
            **SUPPORTED_EFFECTS[operation.id],
        }
        for operation in model.operations
    }
    from .scientific_evidence import scientific_report_layout

    layout = scientific_report_layout()
    if not layout["comparison_paths"] or not layout["array_rules"]:
        raise ValueError("owned scientific report layout must define comparison and array consumers")
    descriptor["scientific_report_layout"] = layout
    descriptor["supported_effect_versions"] = SUPPORTED_EFFECT_VERSIONS
    descriptor["execution_abi"] = "4"
    descriptor["model_id"] = model.model_id
    descriptor["physical_id"] = PHYSICAL_MODEL_ID
    descriptor["inputs"] = [
        {"name": item.name, "sha256": item.digest}
        for item in composed_dependencies(ResolvedDependencies()).artifacts
    ]
    functions = {item["signature"]: item for item in descriptor["functions"]}

    def stream(node: Any) -> str:
        return RawStream()(node)

    for raw in parse_sql(
        (kernels + edge_sql).replace("__MIGRATION_OWNER__", "corpus_migration_owner")
    ):
        stmt = raw.stmt
        if isinstance(stmt, ast.CreateFunctionStmt):
            if stmt.returnType is None:
                raise ValueError("native function requires explicit return type")
            name = ".".join(part.sval for part in stmt.funcname or ())
            signature = (
                name
                + "("
                + ",".join(stream(parameter.argType) for parameter in stmt.parameters or ())
                + ")"
            )
            options = {option.defname: option.arg for option in stmt.options or ()}
            body = options["as"][0].sval
            previous = functions.get(signature, {})
            from copy import copy

            result_type = copy(stmt.returnType)
            result_type.setof = False
            functions[signature] = {
                "signature": signature,
                "body_sha256": sha256(body.encode()).hexdigest(),
                "language": options["language"].sval,
                "security": bool(options.get("security") and options["security"].boolval),
                "strict": bool(options.get("strict") and options["strict"].boolval),
                "volatility": {"immutable": "i", "stable": "s", "volatile": "v"}.get(
                    options.get("volatility").sval if options.get("volatility") else "volatile", "v"
                ),
                "parallel": "u",
                "leakproof": False,
                "setof": bool(stmt.returnType.setof),
                "result": stream(result_type),
                "config": ["search_path=pg_catalog, pg_temp"],
                "owner": previous.get("owner", "corpus_sem_publisher"),
                "execute_roles": list(previous.get("execute_roles", [])),
            }
        elif (
            isinstance(stmt, ast.GrantStmt)
            and stmt.objtype is not None
            and stmt.objtype.name == "OBJECT_FUNCTION"
        ):
            for obj in stmt.objects or ():
                signature = (
                    ".".join(part.sval for part in obj.objname)
                    + "("
                    + ",".join(stream(arg) for arg in obj.objargs or ())
                    + ")"
                )
                if signature not in functions:
                    continue
                roles = set(functions[signature]["execute_roles"])
                for grantee in stmt.grantees or ():
                    if grantee.rolename:
                        if stmt.is_grant:
                            roles.add(grantee.rolename)
                        else:
                            roles.discard(grantee.rolename)
                functions[signature]["execute_roles"] = sorted(roles)
        elif isinstance(stmt, ast.CreateTrigStmt):
            if (
                stmt.relation is None
                or stmt.relation.schemaname is None
                or stmt.relation.relname is None
                or stmt.timing is None
                or stmt.events is None
            ):
                raise ValueError("native trigger requires a qualified relation and events")
            descriptor["triggers"].append(
                {
                    "relation": stmt.relation.schemaname + "." + stmt.relation.relname,
                    "name": stmt.trigname,
                    "function": ".".join(part.sval for part in stmt.funcname or ()) + "()",
                    "type": stmt.timing | stmt.events | int(bool(stmt.row)),
                    "columns": [],
                    "when": None,
                    "args": "",
                    "deferrable": bool(stmt.deferrable),
                    "deferred": bool(stmt.initdeferred),
                }
            )
    for name in sorted(new_tables):
        relation = metadata.tables[name]
        descriptor["tables"].append(
            {
                "relation": name,
                "owner": "corpus_sem_publisher",
                "columns": [
                    {
                        "name": column.name,
                        "type": column.type.compile(dialect=dialect()).lower(),
                        "not_null": not column.nullable,
                        "default": None,
                        "identity": "",
                        "generated": "",
                    }
                    for column in relation.columns
                ],
                "primary_key": [column.name for column in relation.primary_key.columns],
                "foreign_keys": [
                    {
                        "name": constraint.name,
                        "columns": [column.name for column in constraint.columns],
                        "target": constraint.elements[0].target_fullname.rsplit(".", 1)[0],
                        "remote_columns": [
                            item.target_fullname.rsplit(".", 1)[1] for item in constraint.elements
                        ],
                        "on_delete": "a",
                        "on_update": "a",
                        "match": "s",
                        "deferrable": False,
                        "deferred": False,
                        "validated": True,
                    }
                    for constraint in relation.foreign_key_constraints
                ],
            }
        )
    descriptor["checks"] = []
    for name in ("eval.document_split", "eval.reference_set"):
        for check in metadata.tables[name].constraints:
            if not isinstance(check, CheckConstraint):
                continue
            parsed = parse_sql("SELECT " + str(check.sqltext))[0].stmt
            if not isinstance(parsed, ast.SelectStmt) or not parsed.targetList:
                raise ValueError("unsupported native CHECK")
            expression = parsed.targetList[0].val
            if not isinstance(expression, ast.A_Expr) or not isinstance(expression.rexpr, tuple):
                raise ValueError("unsupported native split CHECK")
            choices = [value.val.sval for value in expression.rexpr]
            definition = (
                "CHECK ((split = ANY (ARRAY["
                + ", ".join("'" + value + "'::text" for value in choices)
                + "])))"
            )
            descriptor["checks"].append(
                {"relation": name, "name": check.name, "definition": definition}
            )
    descriptor["functions"] = sorted(functions.values(), key=lambda item: item["signature"])
    required = source.joinpath("admission.sql").read_text()
    required = required.replace(
        "-- {finalized_release}",
        (
            "IF NOT EXISTS(SELECT FROM sem.release_finalization WHERE release_id=r) THEN RAISE "
            "EXCEPTION 'release is not finalized' USING ERRCODE='23514'; END IF;"
        ),
    )
    required = required.replace(
        "-- {record_native_admission}",
        (
            "IF NOT EXISTS(SELECT FROM sem.deployment_admission WHERE release_id=r AND physical"
            "_id=expected->>'physical_id' AND deployment_id=encode(sha256(convert_to(expected::"
            "text,'UTF8')),'hex') AND kind='native' AND content=convert_to(expected::text,'UTF8"
            "')) THEN\n IF NOT (pg_has_role(session_user,'corpus_sem_admitter','USAGE') OR pg_h"
            "as_role(session_user,owner_name,'MEMBER')) THEN RAISE EXCEPTION 'native admission "
            "requires restricted admission phase' USING ERRCODE='42501'; END IF;\n PERFORM sem."
            "record_deployment_admission(r,expected->>'physical_id',encode(sha256(convert_to(ex"
            "pected::text,'UTF8')),'hex'),'native',convert_to(expected::text,'UTF8'));\n END IF"
            ";"
        ),
    )
    require_body = function_bodies(required)["data.require_execution_release"]
    for function in descriptor["functions"]:
        if function["signature"] == "data.require_execution_release(text)":
            function["body_sha256"] = sha256(require_body.encode()).hexdigest()
            function["execute_roles"] = sorted(
                set(function["execute_roles"]) | {"corpus_sem_admitter"}
            )
    encoded = canonical_bytes(descriptor).decode().replace("'", "''")
    admission = (
        (
            "SET LOCAL ROLE corpus_sem_publisher;\nCREATE OR REPLACE FUNCTION data.execution_co"
            "ntract_descriptor() RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalo"
            "g,pg_temp AS $descriptor$\n SELECT '"
        )
        + encoded
        + "'::jsonb\n$descriptor$;\n"
        + required
    )
    return (
        NativeProduct("semantic_0033_physical.sql", physical.encode()),
        NativeProduct("semantic_0033_kernels.sql", kernels.encode()),
        NativeProduct("semantic_0033_admission.sql", admission.encode()),
    )


def consolidation_products(model=None) -> tuple[NativeProduct, ...]:
    """Complete forward authoring: fixed schema, row consumers, transport and Core view.

    Historical migrations execute only committed adjacent products. No physical product
    is discarded by assuming that every future model has the same tables or views.
    """
    return closure_products(model)
