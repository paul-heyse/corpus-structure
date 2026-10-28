"""`python -m corpus_structure.core.schemas`: regenerate the committed JSON Schema files."""

from corpus_structure.core.schemas import write

for path in write():
    print(path.name)
