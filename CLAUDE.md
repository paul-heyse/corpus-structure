@AGENTS.md

Process roles and native model routing target Codex. The tracked `.claude/skills` directory is
the source for Codex discovery through `.agents/skills`; its name does not add a Claude adapter.

On this workstation the global Claude Code SessionStart hook installs the shared per-command
Bash environment refresh. Use plain `uv run` for project Python commands; repository `.envrc`
files supply local/native settings. `UV_LOCKED=1` rejects stale locks; intentional dependency
changes explicitly use `UV_LOCKED=0`. No repository-specific environment hook is required.
