"""FastAPI main application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.routers import classifier, auth, sectors, gaps, ubigeo
from app.core.config import settings
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Brecha AI Service...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Pub/Sub Topic: {settings.PUBSUB_TOPIC_ID}")
    yield
    logger.info("Shutting down Brecha AI Service...")


# Create FastAPI app
app = FastAPI(
    title="Brecha AI Service",
    description="""
## API de Clasificación de Proyectos de Infraestructura Pública

Permite identificar **brechas de infraestructura** en proyectos públicos usando IA (Gemini).
El procesamiento es **asíncrono** vía Google Pub/Sub.

### Flujo de uso

1. **Autenticarse**: `POST /api/v1/auth/login` → obtener `access_token`
2. **Clasificar**: `POST /api/v1/classify` con Bearer token → obtener `query_id`
3. **Consultar estado**: `GET /api/v1/query/{query_id}` hasta que `status = completed`
4. **Ver historial**: `GET /api/v1/history`

### Autenticación

Usa el botón **Authorize** e ingresa tu token JWT obtenido desde `/api/v1/auth/login`.
""",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    contact={"name": "Brecha AI Team"},
    license_info={"name": "Privado - UPC"},
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ALLOWED_ORIGINS == "*" else settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(classifier.router, prefix="/api/v1", tags=["Clasificación"])
app.include_router(ubigeo.router, prefix="/api/v1/ubigeo", tags=["Ubigeo"])
app.include_router(sectors.router, prefix="/api/v1/admin", tags=["Admin - Sectores"])
app.include_router(gaps.router, prefix="/api/v1/admin", tags=["Admin - Brechas"])


def custom_openapi():
    """Generate OpenAPI schema with JWT security scheme."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add JWT Bearer security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Token JWT obtenido desde POST /api/v1/auth/login",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "service": settings.APP_NAME},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
