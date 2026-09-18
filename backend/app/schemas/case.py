import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CaseStatus


class CaseCreate(BaseModel):
    """Client payload for creating a case.

    Canonical `id`, `case_number`, `created_by`, and timestamps are assigned
    by the backend. Extra fields (including client-chosen UUIDs) are rejected.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None)
    status: CaseStatus = CaseStatus.OPEN


class CaseUpdate(BaseModel):
    """Client payload for updating a case."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None)
    status: CaseStatus | None = Field(default=None)


class CaseRead(BaseModel):
    """Full case row as stored in PostgreSQL.

    `cases` has no `updated_at` column; `created_at` is the stored timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_number: str
    title: str
    description: str | None
    status: CaseStatus
    created_by: uuid.UUID
    created_at: datetime


class CaseListItem(BaseModel):
    """List projection for case inventory."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_number: str
    title: str
    description: str | None = None
    status: CaseStatus
    created_by: uuid.UUID
    created_at: datetime
