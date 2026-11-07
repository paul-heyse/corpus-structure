"""Standalone Tree-sitter comparison. Run in a subprocess with core dumps disabled."""

import resource
import sys

from tree_sitter import Language, Parser, Query, QueryCursor

import tree_sitter_python

resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
language = Language(tree_sitter_python.language())
tree = Parser(language).parse(b"result = retire(target)\n" * 5000)
query = Query(
    language,
    "(call function: (identifier) @function arguments: (argument_list (identifier) @argument))",
)
assert len(QueryCursor(query).matches(tree.root_node)) == 5000
print("ordinary matches: 5000", flush=True)


def stop(_offset: int) -> bool:
    print("callback entered", flush=True)
    return True


if sys.argv[1:] == ["--cancel"]:
    QueryCursor(query).matches(tree.root_node, progress_callback=stop)
