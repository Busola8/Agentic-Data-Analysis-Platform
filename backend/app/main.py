from fastapi import FastAPI

app = FastAPI(title="Agentic Data Platform API")


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}