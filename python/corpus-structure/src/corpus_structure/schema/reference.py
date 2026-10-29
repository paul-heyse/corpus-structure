"""The annotator-reference compiler (P0-S-1; D2 §7.5, §10.10; schema and rules §3.3).

Ported from S4's `reference.py` onto the lookup. It builds a structured document (`Reference`, its
sections in order) and renders it as Markdown; the reference is a function of the schema version
alone, since guideline text never enters:

- entity types: description, scope, identity slots, examples;
- predicate cards grouped by the pack's subsets, each with domain, range, object shape, meaning,
  its schema qualifiers, flags (functional, symmetric, transitive, inverse), the subset's rule
  and the `guideline:` checks that apply to it, and where the worked examples use it;
- the role and modality tables from `rules.yaml`'s `tables:`;
- qualifiers, enumerations (pack members included) and condition predicates;
- the exact shapes, rendered from one example instance per core shape, each validated against
  foundations' adapters when the reference compiles (a shape change it does not follow fails);
- the worked examples verbatim (packet text and authored batch), each validated against the
  model-facing batch adapter.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter, ValidationError

from corpus_structure.core import batch as B
from corpus_structure.core import values as V
from corpus_structure.schema.batches import BatchCompiler
from corpus_structure.schema.lookup import SchemaLookup
from corpus_structure.schema.pack import Pack, PackError
from corpus_structure.schema.tables import expand_applies_to

NO_SUBSET = "Claims in no predicate subset"
# The core closed sets a batch author writes or reads (the version-scoped ones are listed apart).
CORE_ENUMS = (
    "Polarity",
    "StatementRole",
    "ScopeExtent",
    "EntityExtent",
    "BindKind",
    "EvidenceRole",
    "ParseOutcome",
)

# One example instance per core shape (model-facing form), validated at compile time.
SHAPES: tuple[tuple[str, Any, dict[str, Any]], ...] = (
    (
        "formula value",
        V.VALUE_ADAPTERS["authored"],
        {"t": "formula", "latex": "a + b X", "symbols": {"X": {"bind": "variable", "entity": "X"}}},
    ),
    ("set value", V.VALUE_ADAPTERS["authored"], {"t": "set", "latex": "(0, \\infty)"}),
    ("text value", V.VALUE_ADAPTERS["authored"], {"t": "text", "v": "the standard score"}),
    ("number value", V.VALUE_ADAPTERS["authored"], {"t": "number", "v": "2.5", "unit": "cm"}),
    ("bool value", V.VALUE_ADAPTERS["authored"], {"t": "bool", "v": True}),
    (
        "enum value",
        V.VALUE_ADAPTERS["authored"],
        {"t": "enum", "enum": "ParameterRole", "v": "shape"},
    ),
    ("date value", V.VALUE_ADAPTERS["authored"], {"t": "date", "v": "2026-01-31"}),
    (
        "interval value",
        V.VALUE_ADAPTERS["authored"],
        {"t": "interval", "start": {"t": "number", "v": "0"}, "start_incl": False},
    ),
    (
        "phrase value",
        V.VALUE_ADAPTERS["authored"],
        {"t": "phrase", "text": "roughly", "sentence": "s1"},
    ),
    ("entity reference", TypeAdapter(V.EntityRef), {"ref": "X"}),
    ("binding", TypeAdapter(V.SymbolBinding), {"bind": "param_of", "claim": "c1", "param": "mean"}),
    ("binding", TypeAdapter(V.SymbolBinding), {"bind": "family_param", "entity": "k"}),
    ("binding", TypeAdapter(V.SymbolBinding), {"bind": "free"}),
    (
        "condition node",
        V.CONDITION_ADAPTERS["authored"],
        {
            "op": "and",
            "args": [
                {"op": "claim", "ref": "c1"},
                {
                    "op": "member",
                    "x": {"t": "formula", "latex": "b"},
                    "set": {"t": "set", "latex": "(0, \\infty)"},
                },
            ],
        },
    ),
    (
        "condition node",
        V.CONDITION_ADAPTERS["authored"],
        {
            "op": "cmp",
            "rel": "<",
            "lhs": {"t": "formula", "latex": "0"},
            "rhs": {"t": "formula", "latex": "b"},
        },
    ),
    (
        "condition node",
        V.CONDITION_ADAPTERS["authored"],
        {"op": "pred", "name": "independent", "args": [{"ref": "X"}, {"ref": "Y"}]},
    ),
    (
        "condition node",
        V.CONDITION_ADAPTERS["authored"],
        {
            "op": "forall",
            "var": "x",
            "set": {"t": "set", "latex": "\\R"},
            "body": {"op": "phrase", "text": "for all real x", "sentence": "s2"},
        },
    ),
    (
        "condition node",
        V.CONDITION_ADAPTERS["authored"],
        {"op": "unsupported", "text": "almost surely", "reason": "quantifier", "sentence": "s2"},
    ),
    (
        "evidence",
        TypeAdapter(B.AuthoredEvidence),
        {"sentence": "s1", "quote": "is normally distributed", "role": "primary"},
    ),
    ("alternative", TypeAdapter(B.AlternativeItem), {"refs": ["c1", "c2"], "reason": "ambiguous"}),
    (
        "unsupported",
        TypeAdapter(B.AuthoredUnsupported),
        {"local_ref": "u1", "sentence": "s3", "quote": "Find the probability", "reason": "asks"},
    ),
)


@dataclass(frozen=True)
class Section:
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class Reference:
    """The structured reference: its sections in order."""

    sections: tuple[Section, ...]

    def markdown(self) -> str:
        out = ["# Annotation reference (generated from the schema)", ""]
        for s in self.sections:
            out += [f"## {s.title}", "", *s.lines, ""]
        return "\n".join(out).rstrip() + "\n"


def _one(text: Any) -> str:
    return " ".join(str(text or "").split())


def _shape_examples() -> list[tuple[str, str]]:
    out = []
    for label, adapter, example in SHAPES:
        try:
            adapter.validate_python(example)
        except ValidationError as error:
            raise PackError(
                [f"reference: the {label} example no longer validates: {error}"]
            ) from None
        out.append((label, json.dumps(example, ensure_ascii=False)))
    return out


def build_reference(
    packs: Sequence[Pack], lookup: SchemaLookup, batches: BatchCompiler
) -> Reference:
    """The structured reference (module doc)."""
    sections = []
    entities = [
        "| Type | What it is | Scope | Identity slots | Examples |",
        "|---|---|---|---|---|",
    ]
    for name in lookup.batch_entity_types():
        e = lookup.entity_classes[name]
        keys = ", ".join(k.split(":", 1)[1] for k in e.identity_keys) or "—"
        entities.append(
            f"| `{name}` | {e.description} | {e.scope} | {keys} | {', '.join(e.examples) or '—'} |"
        )
    statement = lookup.entity_classes["Statement"]
    entities += [
        "",
        f"`Statement` ({statement.description}) is a `statements[]` item, its anchor "
        '`"unit"`, the sentence ids it lies in, or `"outside"` for a statement outside '
        "the unit that the unit refers to. A local entity has an `extent`; `identity` holds "
        "the class's identity slots, an entity-valued slot as a local-ref string.",
    ]
    sections.append(Section("1. Entity types", tuple(entities)))

    guideline = [
        (g, set(expand_applies_to(lookup, g.applies_to)))
        for pack in packs
        for g in pack.rules.guideline
    ]
    used: dict[str, list[str]] = {}
    for pack in packs:
        for example in pack.examples:
            for c in example.batch.get("claims", []):
                used.setdefault(c["predicate"], []).append(f"{example.name} `{c['local_ref']}`")
    cards = [
        "Grouped by the schema's predicate subsets; a predicate in two subsets is listed "
        "under the first.",
        "",
    ]
    done: set[str] = set()
    groups: list[tuple[str | None, tuple[str, ...]]] = [
        (s, preds) for s, (_, preds) in lookup.subsets.items()
    ]
    groups.append((None, tuple(p for p, i in lookup.predicates.items() if not i.subsets)))
    for subset, preds in groups:
        preds = tuple(p for p in preds if p not in done)
        if not preds:
            continue
        cards += [f"### {subset or NO_SUBSET}", ""]
        if subset:
            cards += [lookup.subsets[subset][0], ""]
        for name in preds:
            done.add(name)
            p = lookup.predicates[name]
            obj = batches.claims["model"][name].model_fields["object"].annotation
            shape = getattr(obj, "__name__", str(obj))
            cards += [
                f"#### `{name}`",
                "",
                f"- **Subject:** {p.domain}. **Object:** {p.range} (`{p.object_kind}`, `{shape}`).",
                f"- **Meaning:** {p.description}",
            ]
            if p.qualifiers:
                cards.append(
                    "- **Its qualifiers:** "
                    + ", ".join(f"`{q}`" for q in p.qualifiers)
                    + " (besides the core qualifiers)."
                )
            flags = [
                x
                for x, on in (
                    ("one object per subject in a statement", p.functional),
                    ("symmetric", p.symmetric),
                    ("transitive", p.transitive),
                )
                if on
            ]
            if p.inverse:
                flags.append(f"inverse of `{p.inverse}`")
            if len(p.subsets) > 1:
                flags.append("also in " + ", ".join(s for s in p.subsets if s != subset))
            if flags:
                cards.append(f"- **Also:** {'; '.join(flags)}.")
            rules = [g for g, ps in guideline if p.prefixed in ps and g.applies_to != "any"]
            if rules:
                cards.append("- **Rules:** " + " ".join(_one(g.description) for g in rules))
            if used.get(name):
                cards.append(f"- **In the worked examples:** {', '.join(used[name])}.")
            cards.append("")
    general = [g for g, _ in guideline if g.applies_to == "any"]
    cards += ["### Rules for every claim", "", *(f"- {_one(g.description)}" for g in general)]
    sections.append(Section("2. Predicates", tuple(cards)))

    tables: list[str] = []
    for pack in packs:
        for name, table in pack.rules.tables.items():
            tables += [f"`{name}`:", ""]
            for k, v in table.items():
                text = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
                tables.append(f"- {k}: {text or '(no role)'}")
            tables.append("")
    sections.append(Section("3. Statement roles and modality", tuple(tables)))

    quals = [
        "Core qualifiers are allowed on every predicate; the others only where a card lists "
        "them. An absent qualifier is omitted, never null; `modality` defaults to `asserted`, "
        "`polarity` to `positive`.",
        "",
        "| Qualifier | Value | Meaning |",
        "|---|---|---|",
    ]
    for name, q in lookup.qualifiers.items():
        value = f"{q.object_kind}" + (f" of {q.map_value_kind}" if q.map_value_kind else "")
        quals.append(
            f"| `{name}`{' (core)' if q.core else ''} | {value} ({q.range}) | {q.description} |"
        )
    sections.append(Section("4. Qualifiers", tuple(quals)))

    enums = []
    for set_name, s in lookup.version_sets.items():
        enums.append(
            f"- **{set_name}:** "
            + "; ".join(
                f"`{m.text}`" + (f" ({m.description})" if m.description else "") for m in s.members
            )
        )
    core_view = packs[0].view
    for name in CORE_ENUMS:
        e = core_view.get_enum(name)
        enums.append(
            f"- **{name}:** "
            + "; ".join(
                f"`{k}`" + (f" ({_one(v.description)})" if v.description else "")
                for k, v in e.permissible_values.items()
            )
        )
    for name, e in lookup.enums.items():
        if name == "ConditionPredicate":
            continue
        enums.append(
            f"- **{name}:** "
            + "; ".join(
                f"`{m.text}`" + (f" ({m.description})" if m.description else "") for m in e.members
            )
        )
    sections.append(Section("5. Enumerations", tuple(enums)))

    shapes = [
        "Fields may be omitted where the shape allows; an omitted field is absent, never `null`.",
        "",
        "| Item | Example |",
        "|---|---|",
    ]
    shapes += [f"| {label} | `{text}` |" for label, text in _shape_examples()]
    shapes += [
        "",
        "Condition predicates (`pred` `name`): "
        + "; ".join(
            f"`{n}` ({c.arity} {c.args}{', symmetric' if c.symmetric else ''})"
            for n, c in lookup.condition_predicates.items()
        ),
    ]
    sections.append(Section("6. Exact shapes", tuple(shapes)))

    examples: list[str] = []
    for pack in packs:
        for example in pack.examples:
            try:
                batches.validate(json.dumps(example.batch), "model")
            except ValidationError as error:
                raise PackError(
                    [f"reference/{example.name}: the batch does not validate: {error}"]
                ) from None
            examples += [
                f"### {example.name}",
                "",
                "Packet:",
                "",
                "```text",
                example.packet.rstrip(),
                "```",
                "",
                "Batch:",
                "",
                "```json",
                json.dumps(example.batch, indent=1, ensure_ascii=False),
                "```",
                "",
            ]
    sections.append(Section("7. Worked examples", tuple(examples)))
    return Reference(tuple(sections))
