from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import resumes, themes, cover_letters
from app.db.database import connect_to_mongo, close_mongo_connection
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="RMCraft API", version="0.2.0", lifespan=lifespan)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins - suitable for private development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(resumes.router, prefix="/api/v1/resumes", tags=["resumes"])
app.include_router(themes.router, prefix="/api/v1", tags=["themes"])
app.include_router(cover_letters.router, prefix="/api/v1/cover-letters", tags=["cover-letters"])

@app.get("/health", tags=["health"]) 
async def health():
    """Health check endpoint returning service status."""
    return {"status": "ok"}
