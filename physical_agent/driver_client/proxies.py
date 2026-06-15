"""EnvInterface proxy that ships calls over a DriverClient.

The agent process holds a single :class:`LiberoPrimitiveDriver` whose
``env`` is a :class:`RemoteEnvProxy`. Each call on the proxy serializes
to one RPC on the bound
:class:`~physical_agent.driver_client.base.DriverClient` and returns the
remote method's return value. The ``model`` is supplied directly by the
runner (see :class:`~physical_agent.driver_client.vla_client.VLAClient`)
and does not go through a socket proxy.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from physical_agent.driver_client.base import DriverClient


_TIMEOUT_S = {
    "env.reset": 120.0,
    "env.step": 60.0,
    "env.raw_obs": 30.0,
    "env.render_agentview": 30.0,
    "env.get_camera_meta": 30.0,
    "env.set_image_render_enabled": 30.0,
    "env.cached_image": 30.0,
}


class RemoteEnvProxy:
    """Implements ``EnvInterface`` (see :mod:`physical_agent.tools.libero`)
    by shipping calls over a :class:`DriverClient`."""

    def __init__(self, client: DriverClient):
        self._client = client

    def reset(self) -> tuple[dict, Any]:
        return self._client.call("env.reset", timeout_s=_TIMEOUT_S["env.reset"])

    def step(self, action) -> tuple[dict, Any, np.ndarray, Any, Any]:
        return self._client.call(
            "env.step", args=(action,), timeout_s=_TIMEOUT_S["env.step"]
        )

    def raw_obs(self, env_idx: int = 0) -> dict:
        return self._client.call(
            "env.raw_obs", args=(env_idx,), timeout_s=_TIMEOUT_S["env.raw_obs"]
        )

    def render_agentview(self, env_idx: int = 0) -> np.ndarray:
        return self._client.call(
            "env.render_agentview",
            args=(env_idx,),
            timeout_s=_TIMEOUT_S["env.render_agentview"],
        )

    def get_camera_meta(self) -> dict | None:
        return self._client.call(
            "env.get_camera_meta", timeout_s=_TIMEOUT_S["env.get_camera_meta"]
        )

    def set_image_render_enabled(self, enabled: bool) -> None:
        self._client.call(
            "env.set_image_render_enabled",
            args=(bool(enabled),),
            timeout_s=_TIMEOUT_S["env.set_image_render_enabled"],
        )

    def cached_image(self) -> np.ndarray | None:
        return self._client.call(
            "env.cached_image", timeout_s=_TIMEOUT_S["env.cached_image"]
        )
