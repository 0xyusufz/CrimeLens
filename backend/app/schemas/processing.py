import uuid

from pydantic import BaseModel, ConfigDict


class DocumentProcessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    case_id: uuid.UUID
    entities_processed: int
    mentions_persisted: int
    relationships_processed: int
    relationships_persisted: int
    relationships_unresolved: int
