from fastapi import FastAPI

from app.api.routers.cases import router as cases_router

app = FastAPI(
    title="CrimeLens API",
    description=(
        "Case APIs are unauthenticated in this milestone. "
        "POST /api/cases attributes created_by to a development-only "
        "placeholder user until JWT/RBAC is implemented."
    ),
)

app.include_router(cases_router, prefix="/api/cases", tags=["cases"])


@app.get("/")
def root():
    return {"status": "ok"}
