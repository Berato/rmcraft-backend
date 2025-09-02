from fastapi import FastAPI
from app.api.v1.endpoints import resumes, themes

app = FastAPI(title="RMCraft API", version="0.2.0")

app.include_router(resumes.router, prefix="/api/v1/resumes", tags=["resumes"])
app.include_router(themes.router, prefix="/api/v1/themes", tags=["themes"])


@app.get("/health", tags=["health"]) 
async def health():
    """Health check endpoint returning service status."""
    return {"status": "ok"}
