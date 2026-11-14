"""Controlled inputs and builders shared by the contextual characterization consumers."""

from corpus_structure.methods.native_evidence import native_run
from corpus_structure.semantic.contextual_characterization import (
    ContextInput,
    ContextPart,
    ContextualLayer,
)


def context_builder(source):
    view, base, scope, operation = source[3:]
    context = ContextInput.build([ContextPart(view, 0, len(view.text))], scope["selectors"])
    return ContextualLayer(
        base, scope, dict(operation, key="text.contextual_characterization"), context
    )


def add_metadata(builder, providers=("maverick", "dipo")):
    for provider in providers:
        row = native_run(
            provider,
            "fixture",
            "{}",
            model="fixture",
            version="1",
            runtime_version="fixture",
            layout=[],
            text=[],
        )
        row["configuration_codec"] = provider + "-config-json-v1"
        builder.native_runs.append(row)


def dipo_reply():
    return dict(
        mode="learned",
        post_tokenizer_tokens=6,
        edus=[
            dict(tokens=[0, 2], chars=[0, 4], text="X X"),
            dict(tokens=[2, 6], chars=[4, 14], text="é x+y [3]."),
        ],
        spans=[dict(left=[0, 1], right=[1, 2], nuclearity="SN", relation="contingency-condition")],
        boundaries=[
            dict(token_end=2, learned=True, forced=False, disposition="retained"),
            dict(token_end=6, learned=True, forced=False, disposition="retained"),
        ],
    )
