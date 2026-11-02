"""Package entry installs only the finite query-source custody import boundary."""


def _install_query_custody():
    import importlib.util
    import sys
    from pathlib import Path

    name = __name__ + "._query_custody"
    path = Path(__file__).with_name("_query_custody.py")
    source = path.read_bytes()
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None:
        raise ImportError("query source-custody bootstrap is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
        module.install(source)
    except BaseException:
        sys.modules.pop(name, None)
        raise


_install_query_custody()
del _install_query_custody
