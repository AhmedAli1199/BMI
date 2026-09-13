from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, companies, contacts, dashboard, groups, health
from app.core.config import settings
from app.core.security import require_api_key

docs_enabled = settings.environment != "production"

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
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
app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "environment": settings.environment}
