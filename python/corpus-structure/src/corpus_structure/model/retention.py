"""Process retention of content-addressed model interpretations, outside composition."""

from corpus_structure.caches import declare

from .compiled import CompiledModel


@declare("compiled-model", "model_entries")
def held_compiled_model(sources: tuple[tuple[str, bytes], ...]) -> CompiledModel:
    return CompiledModel(sources)
