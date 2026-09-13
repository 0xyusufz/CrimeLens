from fastapi import FastAPI

from app.api.routers.cases import router as cases_router
from app.api.routers.documents import router as documents_router

app = FastAPI(
    title="CrimeLens API",
    description=(
        "Case and document APIs are unauthenticated in this milestone. "
        "created_by and uploaded_by use a development-only placeholder user "
        "until JWT/RBAC is implemented. Uploaded files are stored locally. "
        "POST /api/documents/{document_id}/process validates Person B's "
        "ExtractionEnvelope, persists to PostgreSQL, then projects Neo4j."
    ),
)

app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(documents_router, prefix="/api", tags=["documents"])


@app.get("/")
def root():
    return {"status": "ok"}
