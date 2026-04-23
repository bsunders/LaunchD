"""LaunchDarkly client bootstrap and flag-change notifications."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, List, Tuple

import ldclient
from ldclient import Config, Context

if TYPE_CHECKING:
    from ldclient.interfaces import FlagChange

log = logging.getLogger(__name__)

ContextGetter = Callable[[], Context]

# (resolver for latest Context, queue for SSE)
Connection = Tuple[ContextGetter, asyncio.Queue[bool]]
_connections: List[Connection] = []
_listener_handle: Any = None


def register_connection(resolve_context: ContextGetter) -> asyncio.Queue[bool]:
    q: asyncio.Queue[bool] = asyncio.Queue()
    _connections.append((resolve_context, q))
    return q


def unregister_connection(q: asyncio.Queue[bool]) -> None:
    global _connections
    _connections = [(getter, qq) for getter, qq in _connections if qq is not q]


def broadcast_flag_state(flag_key: str) -> None:
    """Re-evaluate the flag for every SSE connection (call from the asyncio loop only)."""
    client = ldclient.get()
    for get_ctx, q in _connections:
        ctx = get_ctx()
        q.put_nowait(bool(client.variation(flag_key, ctx, False)))


def init_ld(sdk_key: str, offline: bool, flag_key: str, on_flag_change: Callable[[], None]) -> None:
    """Configure global LD client and subscribe to flag updates (SDK 9.1+)."""
    global _listener_handle
    if offline:
        ldclient.set_config(Config(sdk_key="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", offline=True))
    else:
        ldclient.set_config(Config(sdk_key=sdk_key))

    ldclient.get()

    def _on_flag_change(change: FlagChange) -> None:
        if change.key != flag_key:
            return
        on_flag_change()

    _listener_handle = ldclient.get().flag_tracker.add_listener(_on_flag_change)


def close_ld() -> None:
    try:
        ldclient.get().close()
    except Exception:
        pass
