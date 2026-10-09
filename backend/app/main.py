from fastapi import FastAPI

from app.core.errors import install_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Family Menu API", version="0.1.0")
    install_error_handlers(app)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
