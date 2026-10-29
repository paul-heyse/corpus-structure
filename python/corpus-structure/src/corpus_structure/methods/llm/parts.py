"""Prompt parts, their hashes and pages, and the guideline's sections (agent interface §3.2, §3.4;
D4 §4.2; D2 §10).

| Part | Source |
|---|---|
| `system` | `prompts/extract.md` |
| `guideline` | the run's guideline version: its sections tagged `<!-- core -->`, whole |
| `reference` | the compiled annotator reference (artifact `annotator_reference`/`reference`) |
| `format` | `prompts/format.md` |
| `schema` | the compiled model-facing JSON Schema (`json_schema`/`batch.model_facing`), with the `$id` of the run's model revision |

A part's hash is its text's, or for `reference` and `schema` the compiled artifact's hash (which
covers the `$id`, so a new model revision is a new part). Parts are served in pages of at most
`PAGE_CHARS` characters, cut at line ends.

**Sections.** A guideline section is a `## <id> <title>` heading and its text up to the next such
heading. The `<!-- core -->` tag beside the heading puts it in the `guideline` part. A declaration
`<!-- applies: <feature>=<value>, … -->` beside the heading states the unit features it applies
to (`by_unit`, D2 §10): each feature a member of `UnitFeatureKind`, refused otherwise. A unit's
features come from its unit segment: its kind, and its hint's `statement_kind` and
`claim_bearing`. A section applies to a unit when it declares nothing, when the unit has one of
its declared values, or when the unit records no value for a declared feature (it cannot exclude
it).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from typing import Any

from corpus_structure.core.canonical import canonical_json, digest
from corpus_structure.core.evidence import Segment
from corpus_structure.core.vocab import UnitFeatureKind

PAGE_CHARS = 24_000
PART_NAMES = ("system", "guideline", "reference", "format", "schema")
_HEADING = re.compile(r"^## (\d+(?:\.\d+)*) (.+)$", re.M)
_APPLIES = re.compile(r"<!--\s*applies:\s*(.*?)\s*-->")


class GuidelineError(ValueError):
    """A section declaration names a feature outside the unit-feature vocabulary."""


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt(name: str) -> str:
    return (resources.files("corpus_structure.methods.llm") / "prompts" / name).read_text(
        encoding="utf-8"
    )


@dataclass(frozen=True)
class Part:
    name: str
    text: str
    hash: str

    def pages(self, size: int = PAGE_CHARS) -> list[str]:
        return pages(self.text, size)


def pages(text: str, size: int = PAGE_CHARS) -> list[str]:
    """`text` in pages of at most `size` characters, each ending at a line end where one fits."""
    out: list[str] = []
    rest = text
    while len(rest) > size:
        cut = rest.rfind("\n", 0, size) + 1 or size
        out.append(rest[:cut])
        rest = rest[cut:]
    return [*out, rest] if rest or not out else out


# --- Guideline sections -----------------------------------------------------------------------


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    text: str  # the heading line through the section's end
    core: bool
    applies: tuple[tuple[str, str], ...]  # declared (feature, value); () = every unit


def sections(guideline: str) -> list[Section]:
    """The guideline's `## <id>` sections (module doc), validating declarations."""
    heads = list(_HEADING.finditer(guideline))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(guideline)
        body = guideline[m.start() : end].rstrip("\n") + "\n"
        near = body.split("\n", 3)[:3]  # the heading and the lines beside it
        declared: list[tuple[str, str]] = []
        for line in near:
            for decl in _APPLIES.findall(line):
                for item in filter(None, (x.strip() for x in decl.split(","))):
                    feature, _, value = item.partition("=")
                    feature, value = feature.strip(), value.strip()
                    if feature not in {f.value for f in UnitFeatureKind} or not value:
                        raise GuidelineError(
                            f"§{m.group(1)}: {item!r} is not <feature>=<value> with a feature of "
                            f"{sorted(f.value for f in UnitFeatureKind)}"
                        )
                    declared.append((feature, value))
        core = any("<!-- core -->" in line for line in near)
        out.append(Section(m.group(1), m.group(2).strip(), body, core, tuple(sorted(declared))))
    return out


def core_guideline(guideline: str) -> str:
    """The `guideline` part: the core sections, whole, in order."""
    return "\n".join(s.text for s in sections(guideline) if s.core)


def unit_features(segment: Segment) -> dict[str, str]:
    """The unit's recorded features (module doc), as strings."""
    hint = (segment.attrs or {}).get("hint") or {}
    out = {UnitFeatureKind.SEGMENT_KIND.value: segment.kind.value}
    if hint.get("statement_kind"):
        out[UnitFeatureKind.STATEMENT_KIND.value] = str(hint["statement_kind"])
    if "claim_bearing" in hint:
        out[UnitFeatureKind.CLAIM_BEARING.value] = str(bool(hint["claim_bearing"])).lower()
    return out


def applies(section: Section, features: Mapping[str, str]) -> bool:
    if not section.applies:
        return True
    return any(features.get(f) in (None, v) for f, v in section.applies)


def mapping_hash(all_sections: Sequence[Section]) -> str:
    return digest({s.id: [list(p) for p in s.applies] for s in all_sections if s.applies})


def by_unit_guideline(guideline: str, segment: Segment) -> str:
    """`by_unit`'s guideline input: the applicable core sections' ids and texts with the
    mapping's hash."""
    found = sections(guideline)
    features = unit_features(segment)
    chosen = [[s.id, s.text] for s in found if s.core and applies(s, features)]
    return digest({"sections": chosen, "mapping": mapping_hash(found)})


# --- The parts --------------------------------------------------------------------------------


def _artifact_text(body: bytes | str) -> Any:
    value = json.loads(body) if isinstance(body, bytes | bytearray) else body
    return value


def build_parts(
    guideline: str,
    reference_body: bytes | str,
    reference_hash: str,
    schema_body: bytes | str,
    schema_hash: str,
) -> dict[str, Part]:
    """The five parts of an extract run (module doc)."""
    reference = _artifact_text(reference_body)
    schema = _artifact_text(schema_body)
    schema_text = (
        schema if isinstance(schema, str) else json.dumps(schema, indent=1, ensure_ascii=False)
    )
    system, fmt = prompt("extract.md"), prompt("format.md")
    core = core_guideline(guideline)
    return {
        "system": Part("system", system, text_hash(system)),
        "guideline": Part("guideline", core, text_hash(core)),
        "reference": Part("reference", str(reference), reference_hash),
        "format": Part("format", fmt, text_hash(fmt)),
        "schema": Part("schema", schema_text + "\n", schema_hash),
    }


def parts_hash(parts: Mapping[str, Part]) -> str:
    return hashlib.sha256(canonical_json({n: p.hash for n, p in parts.items()})).hexdigest()
