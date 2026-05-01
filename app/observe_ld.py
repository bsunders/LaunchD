"""LaunchDarkly Observability `observe.*` API — use only after LD client + ObservabilityPlugin init."""

from __future__ import annotations

import logging

from ldobserve import observe

from app.settings import Settings

log = logging.getLogger(__name__)


def emit_startup_telemetry(settings: Settings) -> None:
    """Matches LD docs: observe.record_log(...) after the plugin has registered (first ldclient.get())."""
    if not settings.sdk_key or not settings.ld_observability_enabled:
        return

    if not observe.is_initialized():
        log.warning(
            "LAUNCHDARKLY_OBSERVABILITY set but observe singleton not initialized — "
            "ensure ObservabilityPlugin is on Config and ldclient.get() ran."
        )
        return

    observe.record_log(
        "Nimbus observability bootstrap — server ready",
        logging.INFO,
        {"custom": "startup", "service": settings.otel_service_name},
    )
    _flush_otel()


def _flush_otel() -> None:
    """Help spans/logs reach the exporter quickly during local demos (batching delays otherwise)."""
    try:
        from opentelemetry import metrics, trace

        tp = trace.get_tracer_provider()
        if hasattr(tp, "force_flush"):
            tp.force_flush(timeout_millis=5000)
        mp = metrics.get_meter_provider()
        if hasattr(mp, "force_flush"):
            mp.force_flush(timeout_millis=5000)
    except Exception:
        log.debug("OTEL force_flush skipped", exc_info=True)
