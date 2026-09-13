from fastapi import FastAPI

from app.api.routers.cases import router as cases_router
from app.api.routers.documents import router as documents_router

app = FastAPI(
    title="CrimeLens API",
    description=(
        "Case and document APIs are unauthenticated in this milestone. "
        "created_by and uploaded_by use a development-only placeholder user "
        "until JWT/RBAC is implemented. Uploaded files are stored locally; "
        "ML processing and the evidence ledger are not invoked."
    ),
)

app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(documents_router, prefix="/api", tags=["documents"])


@app.get("/")
def root():
    return {"status": "ok"}
