"""Bounded CPU preparation keeps captured lexical meaning and parser admission."""

from corpus_structure import caches
from corpus_structure.semantic.constructions import retained_rules


def test_frame_runtime_keys_exact_lexical_facts_and_keeps_matcher_vocabulary():
    recipe = retained_rules._recipe_identity()
    version = retained_rules.spacy.__version__
    lexemes = (("Alpha", "retained", False, False, False, False, False),)
    strings = ("Alpha", "retained")
    first = retained_rules._frame_runtime(lexemes, strings, ("",), recipe, version)
    assert retained_rules._frame_runtime(lexemes, strings, ("",), recipe, version) is first
    assert first.vocab["Alpha"].lower_ == "retained"
    assert first.vocab["Alpha"].is_alpha is False
    assert all(matcher.vocab is first.vocab for matcher in (*first.patterns, first.qualifiers))

    changed = (("Alpha", "alpha", True, False, False, False, False),)
    second = retained_rules._frame_runtime(changed, ("Alpha", "alpha"), ("",), recipe, version)
    assert second is not first
    assert second.vocab["Alpha"].lower_ == "alpha"
    assert second.vocab["Alpha"].is_alpha is True
    assert first.vocab["Alpha"].lower_ == "retained"


def test_frame_runtime_oversize_remains_usable_without_retention():
    before = caches.configured()
    try:
        caches.configure(before.model_copy(update={"runtime_bytes": 1}))
        arguments = (
            (),
            (),
            (),
            retained_rules._recipe_identity(),
            retained_rules.spacy.__version__,
        )
        first = retained_rules._frame_runtime(*arguments)
        second = retained_rules._frame_runtime(*arguments)
        assert first is not second
        assert first.retained_bytes > 1
        assert first.patterns[0].vocab is first.vocab
        assert retained_rules._frame_runtime.cache_info().currsize == 0
    finally:
        caches.configure(before)


def test_gliner_pack_compilation_reports_its_own_process_retained_weight(monkeypatch):
    import runpy

    from corpus_structure.methods import native_host_adapters, native_pack_cache
    from corpus_structure.methods.gliner import GlinerPack

    class Schema:
        def build(self):
            return {"entities": ["variable"]}

    calls = []

    def compile_pack(pack):
        calls.append(pack)
        return Schema()

    native_pack_cache.compiled_gliner_pack.cache_clear()
    monkeypatch.setattr(GlinerPack, "compile", compile_pack)
    pack = GlinerPack("release:test", '{"entities":["variable"]}')
    first = native_pack_cache.compiled_gliner_pack(pack, "runtime:a")
    assert native_pack_cache.compiled_gliner_pack(pack, "runtime:a") is first
    assert native_pack_cache.compiled_gliner_pack(pack, "runtime:b") is not first
    assert len(calls) == 2
    assert first.retained_bytes > len(pack.declaration_json)
    # Each resident loads its audited adapter path. That load must not replace the
    # process's existing cache wrapper or lose its counters.
    runpy.run_path(native_host_adapters.__file__)
    runpy.run_path(native_host_adapters.__file__)
    snapshot = caches.snapshot(owner="native-host-test")
    report = next(row for row in snapshot.caches if row.name == "runtime.gliner-pack")
    assert report.entries == 2 and report.size == 2 * first.retained_bytes
    assert report.hits == 1 and report.misses == 2
