"""Native declarations for shared CLI meanings; domain validity stays with its owner."""

from pathlib import Path
from typing import Annotated, Literal

import typer


def pack_name(value: str) -> str:
    """A logical pack name is neither an opened resource nor a filesystem path."""
    if not value or value in {".", ".."} or Path(value).name != value:
        raise ValueError("domain must name a pack under --domains")
    return value


Domains = Annotated[
    Path,
    typer.Option(
        "--domains",
        file_okay=False,
        help="Directory containing named domain packs.",
        rich_help_panel="Inputs",
    ),
]
Domain = Annotated[
    list[str] | None,
    typer.Option(
        "--domain",
        parser=pack_name,
        help="Pack name; repeat to compose packs. Defaults to statistics.",
        rich_help_panel="Inputs",
    ),
]
RetainDiagnostics = Annotated[
    bool,
    typer.Option(
        "--retain-diagnostics/--no-retain-diagnostics",
        help="Retain correction evidence as a managed result.",
        rich_help_panel="Delivery",
    ),
]
CorrectionDetail = Annotated[
    bool,
    typer.Option(
        "--correction-detail/--no-correction-detail",
        help="Include bounded attributed correction details.",
        rich_help_panel="Correction",
    ),
]
RawEvidence = Annotated[
    bool,
    typer.Option(
        "--raw-evidence/--no-raw-evidence",
        help="Opt in to raw evidence; may disclose supplied input.",
        rich_help_panel="Correction",
    ),
]
CorrectionErrors = Annotated[
    int,
    typer.Option(
        "--max-errors",
        min=1,
        max=1000,
        help="Maximum projected correction errors.",
        rich_help_panel="Correction",
    ),
]
CorrectionDepth = Annotated[
    int,
    typer.Option(
        "--max-depth",
        min=1,
        max=16,
        help="Maximum nested correction depth.",
        rich_help_panel="Correction",
    ),
]
CorrectionBytes = Annotated[
    int,
    typer.Option(
        "--max-bytes",
        min=1024,
        max=1048576,
        help="Maximum projected correction bytes.",
        rich_help_panel="Correction",
    ),
]
DiagnosticBytes = Annotated[
    int,
    typer.Option(
        "--max-bytes",
        min=1024,
        max=8388608,
        help="Maximum retained diagnostic bytes to read.",
        rich_help_panel="Delivery",
    ),
]
DependencyDetail = Annotated[
    bool,
    typer.Option(
        "--dependency-detail/--no-dependency-detail",
        help="Include retained dependency occurrences; unavailable coverage stays explicit.",
        rich_help_panel="Dependencies",
    ),
]
DependencyFamily = Annotated[
    str | None,
    typer.Option(
        "--dependency-family",
        help="Exact projection family filter.",
        rich_help_panel="Dependencies",
    ),
]
DependencyOutput = Annotated[
    str | None,
    typer.Option(
        "--dependency-output",
        help="Exact dependency output filter.",
        rich_help_panel="Dependencies",
    ),
]
DependencyOccurrence = Annotated[
    str | None,
    typer.Option(
        "--dependency-occurrence",
        help="Exact dependency occurrence filter.",
        rich_help_panel="Dependencies",
    ),
]
DependencyAfter = Annotated[
    int,
    typer.Option(
        "--dependency-after",
        min=0,
        help="Continue after this dependency ordinal.",
        rich_help_panel="Dependencies",
    ),
]
DependencyLimit = Annotated[
    int,
    typer.Option(
        "--dependency-limit",
        min=1,
        max=1000,
        help="Maximum dependency occurrences.",
        rich_help_panel="Dependencies",
    ),
]
ContractKind = Literal["class", "property", "operation"]
ContractView = Literal["summary", "detail"]
ValidationPurpose = Literal["structural", "accepted"]
ContractKindOption = Annotated[
    ContractKind,
    typer.Option("--subject-kind", help="Kind of archived contract.", rich_help_panel="Inputs"),
]
ContractViewOption = Annotated[
    ContractView,
    typer.Option("--view", help="Summary or paged contract detail.", rich_help_panel="Inputs"),
]
ValidationPurposeOption = Annotated[
    ValidationPurpose | None,
    typer.Option(
        "--validation-purpose",
        help=(
            "Structural validation checks shape; accepted validation also "
            "checks released semantic constraints."
        ),
        rich_help_panel="Inputs",
    ),
]
ContractLimit = Annotated[
    int,
    typer.Option(
        "--limit",
        min=1,
        max=100,
        help="Maximum contract entries per page.",
        rich_help_panel="Inputs",
    ),
]
ContractInput = Annotated[
    Path | None,
    typer.Option(
        "--input",
        exists=True,
        dir_okay=False,
        readable=True,
        help="JSON input to validate against the selected contract; no effects.",
        rich_help_panel="Inputs",
    ),
]
