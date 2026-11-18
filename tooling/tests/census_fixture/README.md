# Census fixture repository

Hand-written sources for the LDT-04 census tests (`test_census.py`). Every file carries a
`.fixture` suffix so that ruff, pyrefly, pytest and uv never treat it as part of this
repository; the tests copy the tree under `tmp_path` and drop the suffix. The import roots used
are `alpha` and `beta`, the import names the shared fake environment (`conftest.py`) installs.

A trailing `# @tag` comment names a site; the expected rows for every tag are written by hand
in `test_census.py`, independent of the code under test. A line without a tag must yield no
attributed row.
