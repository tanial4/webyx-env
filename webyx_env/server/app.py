# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""FastAPI application for the Webyx accessibility auditing benchmark."""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import WebyxAction, WebyxObservation
    from .webyx_env_environment import WebyxEnvironment
except ModuleNotFoundError:
    from models import WebyxAction, WebyxObservation
    from server.webyx_env_environment import WebyxEnvironment


# Create the app with web interface and README integration
app = create_app(
    WebyxEnvironment,
    WebyxAction,
    WebyxObservation,
    env_name="webyx_env",
    max_concurrent_envs=1,  # increase this number to allow more concurrent WebSocket sessions
)


def main():
    """Run the benchmark server from the command line."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
