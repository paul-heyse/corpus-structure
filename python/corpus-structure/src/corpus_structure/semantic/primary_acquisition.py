"""Select primary acquisition from authored operation facts before provider assets."""

from pathlib import Path

import yaml

from .python_operation_sources import ClosedPythonSources, PythonSource, PythonSourceCollection


def requested_source_modules(
    requested, *, organized=False, extra_sources=None, declarations=(), resolve_declarations=None
):
    """Resolve dependency closure using the same literal and inheritance interpretation."""
    root = Path(__file__).parents[1]
    sources = {}
    for directory in (root / "methods", root / "ingest"):
        for path in sorted(directory.rglob("*.py")):
            if path.name.startswith("pdf_raw_") and organized:
                continue
            if path.name.startswith("pdf_organized_") and not organized:
                continue
            content = path.read_bytes()
            if b"__data_operation__" not in content:
                continue
            module = "corpus_structure." + path.relative_to(root).with_suffix(
                ""
            ).as_posix().replace("/", ".")
            sources[module] = PythonSource(module, content, str(path))
    if extra_sources is not None:
        sources.update({source.module: source for source in extra_sources.sources})
    frontend = ClosedPythonSources(PythonSourceCollection(tuple(sources.values())))
    records, owners = {}, {}
    for exposed in frontend.metadata:
        record, _, _ = frontend.operation_metadata(exposed)
        if record.get("abstract", False):
            continue
        identifier = record.get("id")
        if not identifier:
            raise ValueError("operation acquisition requires an inherited operation id: " + exposed)
        if identifier in records:
            raise ValueError("duplicate operation acquisition declaration: " + identifier)
        records[identifier] = record
        owners[identifier] = record.get("acquired_by", frontend._module_for(exposed))
    for source in declarations:
        for record in yaml.safe_load(source.content).get("operations", ()):
            identifier = record["id"]
            if identifier in records:
                raise ValueError("duplicate operation acquisition declaration: " + identifier)
            records[identifier] = record
    from .data_operation_wire import wire_operations

    for operation in wire_operations():
        identifier = "data." + operation["name"]
        if identifier in records:
            raise ValueError("duplicate fixed native operation declaration: " + identifier)
        records[identifier] = {"id": identifier}
    pending, selected = list(requested), set()
    while pending:
        identifier = pending.pop()
        if identifier in selected:
            continue
        if identifier not in records and resolve_declarations is not None:
            for source in resolve_declarations():
                for record in yaml.safe_load(source.content).get("operations", ()):
                    if record["id"] in records:
                        raise ValueError(
                            "duplicate operation acquisition declaration: " + record["id"]
                        )
                    records[record["id"]] = record
            resolve_declarations = None
        if identifier not in records:
            raise ValueError("requested operation has no declared acquisition owner: " + identifier)
        selected.add(identifier)
        record = records[identifier]
        pending.extend((*record.get("dependencies", ()), *record.get("potential_dependencies", ())))
    return frozenset(owners[identifier] for identifier in selected if identifier in owners)


def needs(modules, *owners):
    """An unspecified selection deliberately acquires the full configured profile."""
    return modules is None or any("corpus_structure." + owner in modules for owner in owners)
