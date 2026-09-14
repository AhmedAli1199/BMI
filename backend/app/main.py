from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.automations  # noqa: F401 - import registers every automation's review kinds + producer jobs
from app.api.routes import (
    auth,
    automations,
    companies,
    contacts,
    dashboard,
    groups,
    health,
    review_queue,
    settings as settings_routes,
)
from app.automations.scheduler import start_scheduler, stop_scheduler
from app.core.config import settings
from app.core.security import require_api_key

docs_enabled = settings.environment != "production"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Starts every registered automation producer job that's currently
    # enabled (see app/automations/scheduler.py) - a no-op today since
    # both jobs default off. Assumes a single backend process: this repo's
    # Dockerfile runs plain `uvicorn` with no --workers, so there's only
    # ever one scheduler. If that ever changes, gate this behind a
    # "only the leader process runs jobs" check first, or every worker
    # will fire the same job.
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(contacts.router)
api_router.include_router(companies.router)
api_router.include_router(groups.router)
api_router.include_router(dashboard.router)
api_router.include_router(review_queue.router)
api_router.include_router(automations.router)
api_router.include_router(settings_routes.router)
app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "environment": settings.environment}
