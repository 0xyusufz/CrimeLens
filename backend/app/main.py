from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.auth import router as auth_router
from app.api.routers.cases import router as cases_router
from app.api.routers.documents import router as documents_router
from app.api.routers.entities import router as entities_router
from app.api.routers.evidence import router as evidence_router
from app.api.routers.intelligence import router as intelligence_router
from app.api.routers.investigation import router as investigation_router
from app.api.routers.relationships import router as relationships_router

app = FastAPI(
    title="CrimeLens API",
    description=(
        "Case and document APIs require a JWT from POST /api/auth/login. "
        "ADMIN may access all cases; INVESTIGATOR may access cases listed in "
        "case_members. POST /api/documents/{document_id}/process validates "
        "Person B's ExtractionEnvelope, persists PostgreSQL, then projects Neo4j."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(documents_router, prefix="/api", tags=["documents"])
app.include_router(entities_router, prefix="/api", tags=["entities"])
app.include_router(evidence_router, prefix="/api", tags=["evidence"])
app.include_router(intelligence_router, prefix="/api/cases", tags=["intelligence"])
app.include_router(investigation_router, prefix="/api/investigation", tags=["investigation"])
app.include_router(relationships_router, prefix="/api", tags=["relationships"])


@app.get("/")
def root():
    return {"status": "ok"}
