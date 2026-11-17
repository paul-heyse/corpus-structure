"""Explicit lightweight installed command registry (D8 §4)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandRegistration:
    names: tuple[str, ...]
    module: str
    function: str = "register"


REGISTRY = (
    CommandRegistration(("doctor", "setup", "check", "format", "context", "docs", "evidence", "adr", "host", "release"), "operations"),
    CommandRegistration(("results",), "managed"),
    CommandRegistration(("test",), "testing"),
    CommandRegistration(("db",), "db"),
    CommandRegistration(("demands",), "demands"),
    CommandRegistration(("regenerate",), "regenerate"),
    CommandRegistration(("schema",), "schema"),
    CommandRegistration(("model",), "model"),
    CommandRegistration(("model",), "source_inspection", "register_model"),
    CommandRegistration(("demands",), "source_inspection", "register_demands"),
    CommandRegistration(("ingest", "project", "run", "tasks"), "orchestrate"),
    CommandRegistration(("status",), "status"),
    CommandRegistration(("source",), "source"),
    CommandRegistration(("query", "explain", "review", "export", "records", "contributions", "characterization", "query-context", "neighborhood", "definition"), "selected_results"),
    CommandRegistration(("research",), "research"),
    CommandRegistration(("interpretations",), "interpretations"),
    CommandRegistration(("structure",), "structure"),
    CommandRegistration(("golden", "eval"), "selected_assessment"),
    CommandRegistration(("mcp",), "mcp"),
)
