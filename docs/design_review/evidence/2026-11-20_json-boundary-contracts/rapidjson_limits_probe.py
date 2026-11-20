"""python-rapidjson 1.25: crash-prone depth cases, stream error handling, runtime notes.

Each risky case runs in a child interpreter so a segfault shows as a return code.
Run from the repository root:

    uv run python -I docs/design_review/evidence/2026-11-20_json-boundary-contracts/rapidjson_limits_probe.py
"""

import subprocess
import sys
import textwrap


def child(code, timeout=120):
    proc = subprocess.run([sys.executable, "-I", "-c", textwrap.dedent(code)],
                          capture_output=True, text=True, timeout=timeout)
    tail = (proc.stdout.strip().splitlines() or [""])[-1]
    err = (proc.stderr.strip().splitlines() or [""])[-1]
    signal = f" (signal {-proc.returncode})" if proc.returncode < 0 else ""
    return f"rc={proc.returncode}{signal} out={tail[:160]!r} err={err[:160]!r}"


print("python", sys.version.split()[0], "| sys._is_gil_enabled:", getattr(sys, "_is_gil_enabled", lambda: "n/a")())

print("\n== Q3 decode depth when the program raises the recursion limit")
for limit, depth in ((1000, 100_000), (100_000, 50_000), (10_000_000, 1_000_000), (10_000_000, 5_000_000)):
    print(f"  loads depth {depth:>9} with setrecursionlimit({limit}):",
          child(f"""
            import sys, rapidjson
            sys.setrecursionlimit({limit})
            v = rapidjson.loads('[' * {depth} + ']' * {depth})
            print('decoded', type(v).__name__)
          """))
    print(f"  stdlib json.loads depth {depth:>9} with setrecursionlimit({limit}):",
          child(f"""
            import sys, json
            sys.setrecursionlimit({limit})
            v = json.loads('[' * {depth} + ']' * {depth})
            print('decoded', type(v).__name__)
          """))

print("\n== Q3 encode depth (Py_EnterRecursiveCall; CPython 3.14 C-stack protection)")
for depth in (100_000, 1_000_000):
    print(f"  dumps nested list depth {depth}:", child(f"""
        import rapidjson
        v = []
        for _ in range({depth}):
            v = [v]
        try:
            print('encoded', len(rapidjson.dumps(v)))
        except RecursionError as exc:
            print('RecursionError', exc)
    """))
    print(f"  stdlib json.dumps nested list depth {depth}:", child(f"""
        import json
        v = []
        for _ in range({depth}):
            v = [v]
        try:
            print('encoded', len(json.dumps(v)))
        except RecursionError as exc:
            print('RecursionError', exc)
    """))

print("\n== Q8 Validator on deep documents (Document::Parse has no depth guard)")
for depth in (10_000, 100_000, 1_000_000):
    print(f"  Validator('{{}}') on depth {depth}:", child(f"""
        import rapidjson
        rapidjson.Validator('{{}}')('[' * {depth} + ']' * {depth})
        print('validated')
    """))
    print(f"  Validator(type array, items) on depth {depth}:", child(f"""
        import rapidjson
        v = rapidjson.Validator('{{"items": {{"$ref": "#"}}, "type": "array"}}')
        v('[' * {depth} + ']' * {depth})
        print('validated')
    """))
print("  Validator schema depth 1_000_000:", child("""
    import rapidjson
    rapidjson.Validator('{"not":' * 1_000_000 + '{}' + '}' * 1_000_000)
    print('constructed')
"""))

print("\n== Q7 stream write() raising: are further writes attempted with the error pending?")
print("  ", child("""
    import io, rapidjson, gc
    calls = {"n": 0, "after": 0, "raised": False}
    class Bounded:
        def write(self, chunk):
            calls["n"] += 1
            if calls["raised"]:
                calls["after"] += 1
                return len(chunk)
            if calls["n"] * 64 > 128:
                calls["raised"] = True
                raise OverflowError("bound")
            return len(chunk)
    try:
        rapidjson.dump(["y" * 10000], Bounded(), chunk_size=64)
    except BaseException as exc:
        print("raised", type(exc).__name__, exc, "| write calls after the raising one:", calls["after"])
"""))
print("  same with a write() that calls a C function after the error:", child("""
    import rapidjson, time
    state = {"raised": False, "errors": []}
    class Bounded:
        def write(self, chunk):
            if state["raised"]:
                try:
                    time.perf_counter()
                except SystemError as exc:
                    state["errors"].append(str(exc))
                return len(chunk)
            state["raised"] = True
            raise OverflowError("bound")
    try:
        result = rapidjson.dump(["y" * 1000], Bounded(), chunk_size=64)
        print("dump RETURNED", result, "after write() raised; SystemErrors caught inside later write():",
              len(state["errors"]), state["errors"][:1])
    except BaseException as exc:
        print("raised", type(exc).__name__, "| SystemErrors seen inside later write():", len(state["errors"]),
              state["errors"][:1])
"""))
print("  bound enforced from the producer (generator raises) instead of write():", child("""
    import rapidjson
    class Sink:
        total = 0
        calls = 0
        def write(self, chunk):
            Sink.calls += 1
            Sink.total += len(chunk)
    def items(n, limit, sink):
        for i in range(n):
            if sink.total > limit:
                raise OverflowError("bound exceeded at item %d" % i)
            yield {"i": i, "pad": "x" * 20}
    sink = Sink()
    try:
        rapidjson.dump(items(10**6, 50_000, sink), sink, chunk_size=4096)
    except BaseException as exc:
        print("raised", type(exc).__name__, exc, "| writes", Sink.calls, "bytes", Sink.total)
"""))

print("\n== Q6 RawJSON non-ASCII text with ensure_ascii=True (Writer<..., ASCII<>> raw transcoding)")
for raw in ('"é"', '"€"', '"😀"', '"aé"', '"éa"', '{"k":"é"}'):
    print(f"  dumps([RawJSON({raw!r})]):", child(f"""
        import rapidjson
        try:
            out = rapidjson.dumps([rapidjson.RawJSON({raw!r})])
            print('ok', ascii(out))
        except Exception as exc:
            print('raise', type(exc).__name__, exc)
    """))

print("\n== Q7 Decoder stream with small chunk size")
print("  ", child("""
    import io, rapidjson
    class RefuseDuplicates(rapidjson.Decoder):
        def start_object(self):
            return []
        def end_object(self, pairs):
            out = {}
            for k, v in pairs:
                if k in out:
                    raise ValueError("duplicate " + k)
                out[k] = v
            return out
    d = RefuseDuplicates(number_mode=rapidjson.NM_DECIMAL)
    print(d(io.BytesIO('{"longer_key_é":1.5,"b":{"c":[1,2]}}'.encode()), chunk_size=4))
    try:
        d(io.BytesIO(b'{"a":1,"a":2}'), chunk_size=4)
    except ValueError as exc:
        print("stream duplicate:", exc)
"""))

print("\n== Q9 subinterpreter import (own GIL) and module slots")
print("  ", child("""
    try:
        from concurrent import interpreters
    except ImportError as exc:
        print("no concurrent.interpreters", exc)
    else:
        interp = interpreters.create()
        try:
            interp.exec("import rapidjson; print(rapidjson.__version__)")
            print("imported in isolated subinterpreter")
        except Exception as exc:
            print("subinterpreter import failed:", type(exc).__name__, str(exc).splitlines()[-1][:150])
"""))
print("  legacy (shared-GIL) subinterpreter:", child("""
    import _interpreters
    try:
        cfg = _interpreters.new_config("legacy")
        iid = _interpreters.create(cfg)
        _interpreters.run_string(iid, "import rapidjson")
        print("imported in legacy subinterpreter")
    except Exception as exc:
        print("legacy failed:", type(exc).__name__, str(exc)[:150])
"""))
