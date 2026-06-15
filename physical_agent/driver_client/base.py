"""Driver client interface for env + model RPC.

The agent process holds a :class:`LiberoPrimitiveDriver` whose ``env`` and
``model`` attributes are remote proxies. The proxies invoke methods on
the driver process (which owns the LIBERO env and the OpenPI policy)
through a :class:`DriverClient` — a thin transport that ships
(method, args, kwargs) tuples and returns the method's return value
verbatim.
"""
from __future__ import annotations

from typing import Any, Protocol


class DriverClient(Protocol):
    """Transport from the agent process to the env/model host process."""

    def call(
        self,
        method: str,
        args: tuple = (),
        kwargs: dict | None = None,
        *,
        timeout_s: float | None = None,
    ) -> Any:
        """Invoke a remote method and return its result.

        Errors on the remote side raise; the wire never returns error
        dicts in the result slot.
        """

    def close(self) -> None:
        """Release any client-side transport resources."""
