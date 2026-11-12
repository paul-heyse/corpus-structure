"""Exact executable construction-resource identity for frozen operation selection."""

from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes

from .declarations import REVISION


def construction_digest() -> str:
    root = Path(__file__).parent
    names = {
        "declarations.py",
        "forest.py",
        "matching.py",
        "layers.py",
        "reuse.py",
        "nodes.py",
        "named.py",
        "named_nominations.py",
        "navigation.py",
        "math_scope.py",
    }
    files = sorted(
        [
            *(p for p in root.glob("*.py") if p.name in names or p.name.startswith("retained_")),
            *root.glob("retained_*.json"),
            *root.glob("navigation_*.json"),
            *root.glob("grammars/*.lark"),
        ]
    )
    material = [
        [str(path.relative_to(root)), sha256(path.read_bytes()).hexdigest()] for path in files
    ]
    matcher = root.parent.parent / "methods/annotation_rules.py"
    material.append(["annotation_rules.py", sha256(matcher.read_bytes()).hexdigest()])
    restoration = root.parent.parent / "methods/native_evidence_layers.py"
    material.append(["native_evidence_layers.py", sha256(restoration.read_bytes()).hexdigest()])
    producer = root.parent.parent / "methods/construction_characterization.py"
    material.append(["construction_characterization.py", sha256(producer.read_bytes()).hexdigest()])
    digest = sha256(canonical_bytes(material)).hexdigest()
    return REVISION + ":" + digest


def evaluation_digest() -> str:
    root = Path(__file__).parent
    files = [
        root / "evaluation.py",
        root / "nodes.py",
        root.parent.parent / "methods/contextual_interpretation.py",
    ]
    digest = sha256(
        canonical_bytes([[path.name, sha256(path.read_bytes()).hexdigest()] for path in files])
    ).hexdigest()
    return "primary-contextual-evaluation-1:" + digest
