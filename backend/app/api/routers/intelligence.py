"""Case Network Intelligence and Gemini Copilot endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_case_access
from app.models.case import Case
from app.models.user import User
from app.services.gemini_provider import gemini_engine

router = APIRouter()


class CopilotChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


class CopilotChatResponse(BaseModel):
    answer: str
    model: str = "gemini-3.6-flash"


class NetworkBriefResponse(BaseModel):
    brief: str
    model: str = "gemini-3.6-flash"


@router.get("/{case_id}/intelligence/tables")
def get_case_network_tables(
    case_id: UUID,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Retrieve structured entity and relationship tables extracted for this case."""
    try:
        tables = gemini_engine.build_case_tables(db, case_id)
        return {
            "case_id": str(case_id),
            "entities_count": tables["entities_count"],
            "relationships_count": tables["relationships_count"],
            "entities_table_md": tables["entities_table_md"],
            "relationships_table_md": tables["relationships_table_md"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch network tables: {str(e)}",
        )


@router.get("/{case_id}/intelligence/brief", response_model=NetworkBriefResponse)
def get_case_network_brief(
    case_id: UUID,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Generates an executive case network analysis dossier using Gemini 3.6-Flash."""
    try:
        brief = gemini_engine.generate_network_brief(db, case_id)
        return NetworkBriefResponse(brief=brief, model=gemini_engine.model)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini analysis failed: {str(e)}",
        )


@router.post("/{case_id}/intelligence/copilot", response_model=CopilotChatResponse)
def chat_with_case_copilot(
    case_id: UUID,
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Interactive question answering with Gemini Copilot over the case's extracted relation table."""
    try:
        answer = gemini_engine.chat_copilot(
            db,
            case_id=case_id,
            question=payload.question,
            chat_history=payload.history,
        )
        return CopilotChatResponse(answer=answer, model=gemini_engine.model)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Copilot query failed: {str(e)}",
        )
