"""LaunchDarkly client bootstrap and flag-change notifications."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, List, Tuple

import ldclient
from ldclient import Config, Context
from ldobserve import ObservabilityConfig, ObservabilityPlugin

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
    # Evaluate the flag for each connected browser session and push the result into their SSE queue.
    # Each session gets its own evaluation so per-user targeting rules are respected.
    client = ldclient.get()
    for get_ctx, queue in _connections:
        ctx = get_ctx()
        queue.put_nowait(bool(client.variation(flag_key, ctx, False)))


def init_ld(
    sdk_key: str,
    offline: bool,
    flag_key: str,
    on_flag_change: Callable[[], None],
    observability_config: ObservabilityConfig | None = None,
) -> None:
    # Caller passes LAUNCHDARKLY_SDK_KEY from .env (server-side key only; never send to the browser).
    # flag_key must match the boolean flag key you created in LaunchDarkly for listener filtering.
    # observability_config: optional LaunchDarkly ObservabilityPlugin (OpenTelemetry); omitted offline.
    plugins = []
    if not offline and observability_config is not None:
        plugins.append(ObservabilityPlugin(observability_config))
        log.info("LaunchDarkly Observability plugin enabled (OTEL → LaunchDarkly)")

    if offline:
        # No SDK key in .env — offline mode so the app starts without LD credentials.
        # Evaluations use SDK defaults (e.g. variation(..., False)); recreate flags in LD and set the key to go live.
        ldclient.set_config(Config(sdk_key="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", offline=True))
    else:
        cfg_kw = {"sdk_key": sdk_key}
        if plugins:
            cfg_kw["plugins"] = plugins
        ldclient.set_config(Config(**cfg_kw))

    client = ldclient.get()

    if not client.is_initialized():
        log.error("LaunchDarkly SDK failed to initialize")
    elif not offline:
        client.flush()

    def _on_flag_change(change) -> None:
        if change.key != flag_key:
            return
        # Flag value changed in LaunchDarkly — trigger a broadcast to all connected SSE clients
        # so the UI updates instantly without a page reload (Part 1: instant releases/rollbacks).
        on_flag_change()

    # Register a listener that fires whenever any flag changes in this environment.
    # The SDK maintains a persistent streaming connection to LaunchDarkly to receive updates.
    client.flag_tracker.add_listener(_on_flag_change)


def close_ld() -> None:
    try:
        ldclient.get().close()
    except Exception:
        pass
