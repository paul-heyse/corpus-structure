"""Declared capability inputs shared by native grant generation.

Public declarations supply their own purposes. These private helpers are the
remaining explicit declarations until the program registry owns their bodies.
"""

HELPER_PURPOSES = {
    ("sem", "admit_data_operation_definitions"): ("admit",),
    ("ops", "ddo_require_feature_fit_principal"): ("fit",),
    ("sem", "data_operation_native_descriptor"): ("read", "write", "admit", "evaluate"),
    ("data", "ddo_field"): ("read", "write", "evaluate"),
    ("ops", "data_binding_rows"): ("read", "write", "evaluate"),
}


def program_access(schema, name, public):
    from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess

    purposes = (
        tuple(public[name]["purposes"])
        if name in public
        else HELPER_PURPOSES.get((schema, name), ())
    )
    return NativeProgramAccess(purposes=purposes) if purposes else INTERNAL_PROGRAM
