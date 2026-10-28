"""Inactive references resolve without installing or discovering capability skills."""

import subprocess
from pathlib import Path

from check_agents import process_skills
from repo_paths import local_skill


def test_inactive_reference_does_not_require_a_store(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    skills = tmp_path / ".claude/skills"
    skills.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text(
        "/.claude/skills/*\n!/.claude/skills/README.md\n!/.claude/skills/process/\n"
    )
    (skills / "README.md").write_text("[Former index](old-library/SKILL.md)\n")
    (skills / "process").mkdir()
    (skills / "process/SKILL.md").write_text(
        "---\nname: process\ndescription: Process fixture\n---\n"
    )
    assert local_skill(tmp_path, skills / "old-library/SKILL.md")
    assert local_skill(tmp_path, skills / "old-library/references/capabilities.md")
    assert not local_skill(tmp_path, skills / "unknown/SKILL.md")
    assert not local_skill(tmp_path, skills / "process/missing.md")
    assert process_skills(tmp_path) == ["process"]


def test_leftover_central_link_is_an_inactive_reference(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    skills = tmp_path / ".claude/skills"
    skills.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("/.claude/skills/*\n")
    (skills / "README.md").write_text("[Former index](old-library/SKILL.md)\n")
    store = tmp_path / "store"
    store.mkdir()
    (store / "SKILL.md").write_text("---\nname: old-library\n---\n")
    (skills / "old-library").symlink_to(store, target_is_directory=True)
    assert local_skill(tmp_path, skills / "old-library/references/missing.md")
    assert process_skills(tmp_path) == []
