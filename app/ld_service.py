"""LaunchDarkly client bootstrap and flag-change notifications."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, List, Tuple

import ldclient
from ldclient import Config, Context

log = logging.getLogger(__name__)

ContextGetter = Callable[[], Context]

Connection = Tuple[ContextGetter, asyncio.Queue[bool]]
_connections: List[Connection] = []


def register_connection(resolve_context: ContextGetter) -> asyncio.Queue[bool]:
    q: asyncio.Queue[bool] = asyncio.Queue()
    _connections.append((resolve_context, q))
    return q


def unregister_connection(q: asyncio.Queue[bool]) -> None:
    global _connections
    _connections = [(getter, qq) for getter, qq in _connections if qq is not q]


def broadcast_flag_state(flag_key: str) -> None:
    client = ldclient.get()
    for get_ctx, q in _connections:
        ctx = get_ctx()
        q.put_nowait(bool(client.variation(flag_key, ctx, False)))


def init_ld(sdk_key: str, offline: bool, flag_key: str, on_flag_change: Callable[[], None]) -> None:
    if offline:
        ldclient.set_config(Config(sdk_key="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", offline=True))
    else:
        ldclient.set_config(Config(sdk_key=sdk_key))

    client = ldclient.get()

    if not client.is_initialized():
        log.error("LaunchDarkly SDK failed to initialize")
    elif not offline:
        client.flush()

    def _on_flag_change(change) -> None:
        if change.key != flag_key:
            return
        on_flag_change()

    client.flag_tracker.add_listener(_on_flag_change)


def close_ld() -> None:
    try:
        ldclient.get().close()
    except Exception:
        pass
