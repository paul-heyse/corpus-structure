"""Generated fixed-call enumeration types; physical declarations own nominal identities."""

from typing import Literal

type PdfFrozenBuildKind = Literal["integrated", "native"]
type PdfPublishedRevisionKind = Literal["integrated", "native"]
type PdfSourceViewPublicationMembership = Literal["descendants", "direct"]
type PdfStageBuildState = Literal["abandoned", "frozen", "open", "published"]
type PublishedSectionNodeRowRole = Literal["ancestor", "selected"]
