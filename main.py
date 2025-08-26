from fastapi import FastAPI
from app.api.v1.endpoints import resumes

app = FastAPI(title="Minimal FastAPI App", version="0.1.0")

app.include_router(resumes.router, prefix="/api/v1/resumes", tags=["resumes"])

@app.get("/health", tags=["health"]) 
async def health():
    """Health check endpoint returning service status."""
    return {"status": "ok"}
