from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Family Menu API", version="0.1.0")
    install_error_handlers(app)
    app.include_router(api_router, prefix=get_settings().api_prefix)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
