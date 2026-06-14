from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/healthz")


def _respond(checks: dict[str, bool]) -> JSONResponse:
    if all(checks.values()):
        return JSONResponse({"status": "ok"})
    return JSONResponse(
        {"status": "unavailable", "checks": checks}, status_code=503
    )


@router.get("/startup")
def startup(request: Request) -> JSONResponse:
    return _respond({"started": bool(getattr(request.app.state, "started", False))})


@router.get("/ready")
def ready(request: Request) -> JSONResponse:
    state = request.app.state
    return _respond(
        {
            "started": bool(getattr(state, "started", False)),
            "worker": state.worker.is_alive(),
            "watcher": state.watcher.is_alive(),
        }
    )


@router.get("/live")
def live(request: Request) -> JSONResponse:
    state = request.app.state
    return _respond(
        {
            "worker": state.worker.is_alive(),
            "watcher": state.watcher.is_alive(),
        }
    )
