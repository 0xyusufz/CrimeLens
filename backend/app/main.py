from fastapi import FastAPI

from app.api.routers.auth import router as auth_router
from app.api.routers.cases import router as cases_router
from app.api.routers.documents import router as documents_router

app = FastAPI(
    title="CrimeLens API",
    description=(
        "Case and document APIs require a JWT from POST /api/auth/login. "
        "ADMIN may access all cases; INVESTIGATOR may access cases listed in "
        "case_members. POST /api/documents/{document_id}/process validates "
        "Person B's ExtractionEnvelope, persists PostgreSQL, then projects Neo4j."
    ),
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(documents_router, prefix="/api", tags=["documents"])


@app.get("/")
def root():
    return {"status": "ok"}
