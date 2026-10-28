"""Check that active Codex instructions, shared roles and skills resolve.

- `.agents/skills` (Codex discovery) is a symlink to `.claude/skills`.
- Every skill's frontmatter `name` matches its directory.
- In the agent-facing documents, every relative markdown link and every
  backticked repo path exists, and every `just <recipe>` names a real recipe.

Instructions that point at things which do not exist are how the previous
repository's agents were sent after deleted commands; this is the oracle.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from repo_paths import local_skill

ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
TICK_RE = re.compile(r"`([^`\s]+)`")
JUST_RE = re.compile(r"`just ([a-z][a-z0-9-]*)")
PLACEHOLDER = re.compile(r"[<>{}*]|NNNN|YYYY|\.\.\.|…")


def ignored(root: Path, paths: list[str]) -> set[str]:
    """The subset of `paths` Git ignores; outside a Git work tree nothing is ignored."""
    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=root,
        input="\n".join(paths),
        capture_output=True,
        text=True,
        check=False,
    )
    return set(result.stdout.split())


def process_skills(root: Path) -> list[str]:
    """Skills the repository tracks; ignored entries may identify retained inactive central references."""
    names = sorted(
        p.parent.name
        for p in (root / ".claude" / "skills").glob("*/SKILL.md")
        if not p.parent.is_symlink()
    )
    skip = ignored(root, [f".claude/skills/{n}/SKILL.md" for n in names])
    return [n for n in names if f".claude/skills/{n}/SKILL.md" not in skip]


def path_roots(root: Path) -> tuple[str, ...]:
    """Top-level directories that belong to the repository (not build output or caches)."""
    dirs = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name != ".git")
    skip = ignored(root, dirs)
    return tuple(f"{d}/" for d in dirs if d not in skip)


def documents(root: Path) -> list[Path]:
    docs = [root / "AGENTS.md", root / ".claude" / "skills" / "README.md"]
    docs += [root / ".claude" / "skills" / s / "SKILL.md" for s in process_skills(root)]
    docs += sorted((root / ".agents" / "roles").glob("*.md"))
    docs += sorted((root / ".codex" / "agents").glob("*.toml"))
    for skill in process_skills(root):
        docs += sorted((root / ".claude" / "skills" / skill / "references").glob("*.md"))
    return docs


def recipes(root: Path) -> set[str]:
    out = subprocess.run(
        ["just", "--summary"], cwd=root, capture_output=True, text=True, check=True
    ).stdout
    return set(out.split())


def check(root: Path) -> list[str]:
    problems: list[str] = []
    link = root / ".agents" / "skills"
    if not link.is_symlink() or link.resolve() != (root / ".claude" / "skills").resolve():
        problems.append(".agents/skills must be a symlink to ../.claude/skills")

    for skill_md in sorted((root / ".claude" / "skills").glob("*/SKILL.md")):
        match = re.search(r"^name:\s*(\S+)", skill_md.read_text(), re.M)
        if not match or match.group(1) != skill_md.parent.name:
            problems.append(f"{skill_md.relative_to(root)}: `name` must equal its directory")

    known = recipes(root)
    roots = path_roots(root)
    for doc in documents(root):
        if not doc.exists():
            problems.append(f"{doc.relative_to(root)}: missing")
            continue
        text = doc.read_text()
        rel = doc.relative_to(root)
        for target in LINK_RE.findall(text):
            if "://" in target or PLACEHOLDER.search(target):
                continue
            if not (doc.parent / target).exists() and not local_skill(
                root, (doc.parent / target).resolve()
            ):
                problems.append(f"{rel}: link target does not exist: {target}")
        for token in TICK_RE.findall(text):
            token = token.rstrip(".,:;")
            if not token.startswith(roots) or PLACEHOLDER.search(token):
                continue
            if not (root / token.split(":")[0]).exists() and not local_skill(
                root, root / token.split(":")[0]
            ):
                problems.append(f"{rel}: path does not exist: {token}")
        for recipe in JUST_RE.findall(text):
            if recipe not in known:
                problems.append(f"{rel}: unknown just recipe: just {recipe}")
    return problems


def main() -> int:
    problems = check(ROOT)
    for p in problems:
        print(p)
    if not problems:
        print("lint-agents: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
