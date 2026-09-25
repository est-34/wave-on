from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 - registers SQLAlchemy metadata
from .config import PROJECT_ROOT, settings
from .database import SessionLocal, init_db
from .routers import agent, demo, health, users
from .modules.demo.api import ensure_demo_user
from .modules.demo.adapters.repository import DemoRepository
from .shared.errors import ApplicationError
from fastapi.responses import JSONResponse

STATIC_DIR = PROJECT_ROOT / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    init_db()
    with SessionLocal() as db:
        ensure_demo_user(DemoRepository(db))
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Personalized Spatial Agent API: observation, pattern discovery, suggestion, "
        "personal gesture memory, execution, and feedback."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(agent.router, prefix=settings.api_prefix)
app.include_router(demo.router, prefix=settings.api_prefix)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def revalidate_static(request, call_next):
    """Make browsers revalidate /static instead of guessing a freshness window.

    StaticFiles sends no Cache-Control, so browsers heuristically cache app.js
    and can serve a stale UI on the demo machine. The ETag still answers 304.
    """
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["cache-control"] = "no-cache"
    return response


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.exception_handler(ApplicationError)
async def application_error(_request, exc: ApplicationError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
