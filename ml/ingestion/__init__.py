"""Evidence ingestion primitives for the ML pipeline.

The module performs local classification and metadata collection only.  It
never stores files, calls a remote model, or creates database identities.
"""

from ml.ingestion.file_router import (
    DocumentKind,
    IngestedDocument,
    PageContent,
    ingest_document,
)

__all__ = ["DocumentKind", "IngestedDocument", "PageContent", "ingest_document"]
