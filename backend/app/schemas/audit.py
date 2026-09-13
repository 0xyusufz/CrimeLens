import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

_BLOCKED = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "secret",
    "authorization",
}


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    case_id: uuid.UUID | None
    resource_type: str | None
    resource_id: uuid.UUID | None
    result: str
    details: dict[str, Any]
    created_at: datetime

    @field_validator("details")
    @classmethod
    def strip_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in value.items() if str(k).lower() not in _BLOCKED}
