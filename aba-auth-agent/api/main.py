"""The API: login, reference data and import jobs, plus the built frontend.

Run (from aba-auth-agent/):  uvicorn api.main:app --port 8000
In development the Vite dev server proxies /api here; in production this also serves the
built frontend from web/dist.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()  # ANTHROPIC_API_KEY

from api import auth, clients, imports, periods, reference, templates  # noqa: E402
from auth_config import load_auth_config  # noqa: E402
from data.store import init_db  # noqa: E402

WEB_DIST = Path(__file__).parent.parent / "web" / "dist"

# The page is re-checked on every load so a rebuilt app is never hidden behind a stale copy.
# Files under /assets have a content hash in their name, so they can be kept forever.
NO_CACHE = {"Cache-Control": "no-cache"}
IMMUTABLE = "public, max-age=31536000, immutable"


class HashedAssets(StaticFiles):
    async def get_response(self, path, scope):
        response: Response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = IMMUTABLE
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    config = load_auth_config()
    app = FastAPI(title="Lumen ABA API", lifespan=lifespan)

    # Signed cookie session. SameSite=Lax means other sites can't make the browser send it
    # on a cross-site POST, which is what protects upload and answer requests.
    app.add_middleware(
        SessionMiddleware,
        secret_key=config["cookie"]["key"],
        session_cookie="aba_session",
        same_site="lax",
        https_only=os.environ.get("ABA_HTTPS_ONLY", "").lower() in ("1", "true", "yes"),
        max_age=int(config["cookie"].get("expiry_days", 7)) * 86400,
    )

    app.include_router(auth.router)
    protected = [Depends(auth.require_user)]
    app.include_router(reference.router, dependencies=protected)
    app.include_router(clients.router, dependencies=protected)
    app.include_router(periods.router, dependencies=protected)
    app.include_router(templates.router, dependencies=protected)
    app.include_router(imports.router)  # its routes declare require_user themselves

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    if WEB_DIST.exists():
        app.mount("/assets", HashedAssets(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            candidate = (WEB_DIST / path).resolve()
            if path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
                return FileResponse(candidate, headers=NO_CACHE)
            return FileResponse(WEB_DIST / "index.html", headers=NO_CACHE)

    return app


app = create_app()
