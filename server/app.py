"""FastAPI application for the Webyx accessibility auditing benchmark."""

import os
from pathlib import Path

from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import WebyxAction, WebyxObservation
    from .webyx_env_environment import WebyxEnvironment
except (ImportError, ModuleNotFoundError):
    from models import WebyxAction, WebyxObservation
    from server.webyx_env_environment import WebyxEnvironment


def make_env():
    env = WebyxEnvironment()
    env.reset()
    return env


app = create_app(
    make_env,
    WebyxAction,
    WebyxObservation,
    env_name="webyx_env",
    max_concurrent_envs=1,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_UI_FILE = Path(__file__).parent / "webyx_ui.html"

@app.get("/", response_class=HTMLResponse)
async def ui():
    if _UI_FILE.exists():
        return HTMLResponse(content=_UI_FILE.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>UI not found</h1>", status_code=404)


def main():
    """Run the benchmark server from the command line."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()