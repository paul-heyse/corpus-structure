"""Selected native declaration facts shared by current authors and admission products.

This reads generated source, never a deployed catalog. Frozen predecessor inventories are
explicit inputs; unrelated overloads and properties survive unless a declaration changes them.
"""

from __future__ import annotations

from copy import copy
from hashlib import sha256

from pglast import ast, enums
from pglast.stream import RawStream

from .native_function_signatures import (
    function_signature,
    qualified_name,
    remove_output_signature_aliases,
)
from .prepared_sql import PreparedSQL, prepare_sql


def function_descriptor(statement, previous, *, owner):
    options = {option.defname: option.arg for option in statement.options or ()}
    if statement.is_procedure or statement.returnType is None:
        raise ValueError("native authoring supports functions with an explicit result")
    if "language" not in options:
        raise ValueError("native authoring requires a single source body and language")
    from .native_sql_body import SQL_STANDARD_PROFILE, body_source

    source = body_source(statement)
    result_type = copy(statement.returnType)
    result_type.setof = False
    config = []
    for option in statement.options or ():
        if option.defname != "set":
            continue
        setting = option.arg
        if setting.kind != enums.VariableSetKind.VAR_SET_VALUE:
            raise ValueError(f"native authoring requires an explicit value for {setting.name}")
        values = []
        for arg in setting.args or ():
            if not isinstance(arg, ast.A_Const) or arg.isnull:
                raise ValueError(f"unsupported native configuration {setting.name}")
            value = getattr(arg.val, "sval", None)
            if value is None:
                value = RawStream()(arg)
            values.append(value)
        config.append(setting.name + "=" + ", ".join(values))
    descriptor = dict(
        signature=function_signature(statement),
        body_sha256=sha256(source.encode()).hexdigest(),
        language=options["language"].sval,
        security=bool(options.get("security") and options["security"].boolval),
        strict=bool(options.get("strict") and options["strict"].boolval),
        volatility={"immutable": "i", "stable": "s", "volatile": "v"}[
            options["volatility"].sval if options.get("volatility") else "volatile"
        ],
        parallel={"unsafe": "u", "restricted": "r", "safe": "s"}[
            options["parallel"].sval if options.get("parallel") else "unsafe"
        ],
        leakproof=bool(options.get("leakproof") and options["leakproof"].boolval),
        setof=bool(statement.returnType.setof),
        result=RawStream()(result_type),
        config=config,
        owner=previous.get("owner", owner),
        execute_roles=list(previous.get("execute_roles", ["PUBLIC"])),
    )
    if statement.sql_body is not None:
        # The source hash is custody only. Candidate admission replaces it with the
        # bound profile from its normalized NativeObject before accepting deployment.
        descriptor.update(body_kind="sql_standard", body_profile=SQL_STANDARD_PROFILE)
    return descriptor


def _object_signature(obj):
    return (
        qualified_name(obj.objname)
        + "("
        + ",".join(RawStream()(arg) for arg in obj.objargs or ())
        + ")"
    )


def update_function_inventory(
    functions: dict[str, dict], sql: str | PreparedSQL, *, owner="corpus_sem_publisher"
) -> PreparedSQL:
    """Apply current function declarations and explicit owner/EXECUTE effects to a copy's facts."""
    prepared = prepare_sql(sql, source="<native declarations>")
    remove_output_signature_aliases(functions, prepared.statements)
    for raw in prepared.statements:
        stmt = raw.stmt
        if isinstance(stmt, ast.VariableSetStmt) and stmt.name == "role":
            if stmt.args and isinstance(stmt.args[0].val, ast.String):
                owner = stmt.args[0].val.sval
        elif isinstance(stmt, ast.CreateFunctionStmt):
            signature = function_signature(stmt)
            functions[signature] = function_descriptor(
                stmt, functions.get(signature, {}), owner=owner
            )
        elif (
            isinstance(stmt, ast.AlterOwnerStmt)
            and stmt.objectType == enums.ObjectType.OBJECT_FUNCTION
        ):
            signature = _object_signature(stmt.object)
            if signature in functions:
                if stmt.newowner is None or stmt.newowner.rolename is None:
                    raise ValueError("native owner effects require an explicit named role")
                functions[signature]["owner"] = stmt.newowner.rolename
        elif isinstance(stmt, ast.GrantStmt) and stmt.objtype == enums.ObjectType.OBJECT_FUNCTION:
            if stmt.privileges and any(
                privilege.priv_name.lower() != "execute" for privilege in stmt.privileges
            ):
                raise ValueError("unsupported native function privilege")
            if stmt.grant_option:
                raise ValueError("descriptor EXECUTE roles cannot represent grant options")
            if all(isinstance(obj, ast.String) for obj in stmt.objects or ()):
                prefixes = tuple(qualified_name((obj,)) + "." for obj in stmt.objects or ())
                signatures = [name for name in functions if name.startswith(prefixes)]
            else:
                signatures = [_object_signature(obj) for obj in stmt.objects or ()]
            for signature in signatures:
                if signature not in functions:
                    continue
                roles = set(functions[signature]["execute_roles"])
                for grantee in stmt.grantees or ():
                    role = (
                        "PUBLIC"
                        if grantee.roletype == enums.RoleSpecType.ROLESPEC_PUBLIC
                        else grantee.rolename
                    )
                    if not role:
                        raise ValueError("native grants require explicit named roles")
                    if stmt.is_grant:
                        roles.add(role)
                    else:
                        roles.discard(role)
                functions[signature]["execute_roles"] = sorted(roles)
    return prepared
