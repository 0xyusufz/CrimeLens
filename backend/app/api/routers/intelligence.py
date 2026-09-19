"""Case Network Intelligence and Gemini Copilot endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
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
    user_message_id: str | None = None
    assistant_message_id: str | None = None


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


from app.models.chat import CaseChatMessage


@router.get("/{case_id}/intelligence/chat")
def get_case_chat_history(
    case_id: UUID,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Fetches persisted conversation history between investigator and AI assistant."""
    try:
        stmt = (
            select(CaseChatMessage)
            .where(CaseChatMessage.case_id == case_id)
            .order_by(CaseChatMessage.created_at.asc())
        )
        msgs = list(db.scalars(stmt).all())
        return [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "model": m.model,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}",
        )


@router.delete("/{case_id}/intelligence/chat")
def clear_case_chat_history(
    case_id: UUID,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Clears persisted chat history for a new session."""
    try:
        db.execute(delete(CaseChatMessage).where(CaseChatMessage.case_id == case_id))
        db.commit()
        return {"status": "cleared"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear chat history: {str(e)}",
        )


@router.delete("/{case_id}/intelligence/chat/{message_id}")
def delete_case_chat_message(
    case_id: UUID,
    message_id: UUID,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Deletes an individual chat message."""
    try:
        db.execute(
            delete(CaseChatMessage).where(
                CaseChatMessage.case_id == case_id,
                CaseChatMessage.id == message_id,
            )
        )
        db.commit()
        return {"status": "deleted", "message_id": str(message_id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat message: {str(e)}",
        )


@router.post("/{case_id}/intelligence/copilot", response_model=CopilotChatResponse)
def chat_with_case_copilot(
    case_id: UUID,
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Interactive question answering with Gemini Copilot over the case's extracted relation table.

    Persists both investigator queries and AI answers to PostgreSQL.
    """
    try:
        # 1. Save user query to DB
        user_msg = CaseChatMessage(
            case_id=case_id,
            role="user",
            content=payload.question,
            model=None,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # 2. Generate response via Copilot
        answer = gemini_engine.chat_copilot(
            db,
            case_id=case_id,
            question=payload.question,
            chat_history=payload.history,
        )

        # 3. Save assistant response to DB
        asst_msg = CaseChatMessage(
            case_id=case_id,
            role="assistant",
            content=answer,
            model=gemini_engine.model,
        )
        db.add(asst_msg)
        db.commit()
        db.refresh(asst_msg)

        return CopilotChatResponse(
            answer=answer,
            model=gemini_engine.model,
            user_message_id=str(user_msg.id),
            assistant_message_id=str(asst_msg.id),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Copilot query failed: {str(e)}",
        )


from typing import Optional

from app.services.case_intelligence_store import (
    check_report_status,
    get_or_analyze_network,
)


class NetworkAnalyzeRequest(BaseModel):
    mode: str = Field(default="full")  # "full" or "node"
    selected_node_ids: list[str] = Field(default_factory=list)
    hops: int = Field(default=2, ge=1, le=3)
    force_refresh: bool = Field(default=False)


@router.get("/{case_id}/intelligence/analyze/status")
def get_case_network_analysis_status(
    case_id: UUID,
    mode: str = "full",
    target_node_id: Optional[str] = None,
    hops: int = 2,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Checks whether a saved network report exists and whether the network has changed since."""
    try:
        status_info = check_report_status(
            session=db,
            case_id=case_id,
            mode=mode,
            target_node_id=target_node_id,
            hops=hops,
        )
        return status_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check report status: {str(e)}",
        )


@router.post("/{case_id}/intelligence/analyze")
def analyze_case_network(
    case_id: UUID,
    payload: NetworkAnalyzeRequest,
    db: Session = Depends(get_db),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
):
    """Deep graph reasoning with Gemini/Groq. Automatically persists and caches results

    against the network fingerprint. If the network has not changed and force_refresh is false,
    returns the saved analysis instantly.
    """
    try:
        result = get_or_analyze_network(
            session=db,
            case_id=case_id,
            mode=payload.mode,
            selected_node_ids=payload.selected_node_ids,
            hops=payload.hops,
            force_refresh=payload.force_refresh,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Network analysis failed: {str(e)}",
        )

