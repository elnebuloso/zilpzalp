from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from zilpzalp.config import load_config
from zilpzalp.queue import Queue
from zilpzalp.watcher import Watcher

CONFIG_ENV = "ZILPZALP_CONFIG"
DEFAULT_CONFIG_PATH = "config.yaml"


def get_config_path() -> Path:
    return Path(os.environ.get(CONFIG_ENV, DEFAULT_CONFIG_PATH))


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config(get_config_path())
    app.state.config = config
    queue = Queue()
    app.state.queue = queue
    watcher = Watcher(config.paths.watchfolder, queue.add)
    app.state.watcher = watcher
    watcher.start()
    try:
        yield
    finally:
        watcher.stop()


app = FastAPI(title="ZilpZalp", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
