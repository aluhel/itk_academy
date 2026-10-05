from fastapi import FastAPI

from itk_academy.api.v1.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="ITK Academy — Events Aggregator",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
