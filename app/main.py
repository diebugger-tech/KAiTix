import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.database import engine
from app.api.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up the DB connection pool on startup so the first request isn't slow."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("DB connection pool warmed up.")
    except Exception as exc:
        logger.warning("DB warm-up failed (non-fatal): %s", exc)
    yield
    await engine.dispose()
    logger.info("DB engine disposed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS middleware for local frontend integration (SvelteKit)
# LAN-IPs (z.B. 192.168.178.0/24) ggf. ergänzen wenn Frontend
# von anderen Geräten im Netzwerk aufgerufen wird
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register main API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Only fallback to SPA for 404s that are not API calls
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        index_path = "frontend/build/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Mount the static files from the SvelteKit build output
if os.path.exists("frontend/build"):
    app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "message": f"Welcome to the {settings.PROJECT_NAME} API (Frontend not built)",
            "docs_url": "/docs",
            "status": "healthy",
        }
