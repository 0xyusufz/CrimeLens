from fastapi import FastAPI

app = FastAPI(title="CrimeLens API")


@app.get("/")
def root():
    return {"status": "ok"}
