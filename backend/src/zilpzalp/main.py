from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from zilpzalp.config import load_config
from zilpzalp.queue import Queue
from zilpzalp.watcher import Watcher
from zilpzalp.web.health import router as health_router
from zilpzalp.web.routes import router
from zilpzalp.worker import Worker

CONFIG_ENV = "ZILPZALP_CONFIG"
DEFAULT_CONFIG_PATH = "config.yaml"
_STATIC_DIR = Path(__file__).parent / "web" / "static"


def get_config_path() -> Path:
    return Path(os.environ.get(CONFIG_ENV, DEFAULT_CONFIG_PATH))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started = False
    config_path = get_config_path()
    config = load_config(config_path)
    app.state.config = config
    app.state.config_path = config_path
    queue = Queue()
    app.state.queue = queue
    worker = Worker(queue, lambda: app.state.config)
    app.state.worker = worker
    worker.start()
    watcher = Watcher(config.paths.watchfolder, worker.submit)
    app.state.watcher = watcher
    watcher.start()
    app.state.started = True
    try:
        yield
    finally:
        app.state.started = False
        watcher.stop()
        worker.stop()


app = FastAPI(title="ZilpZalp", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.include_router(router)
app.include_router(health_router)
