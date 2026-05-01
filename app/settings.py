"""
Application settings loaded from `.env` (see `.env.example` and README).

LaunchDarkly resources are not created by this code — you create them in the LD UI (or API)
and set keys here so they match:

  - Boolean flag  → FEATURE_FLAG_KEY (type boolean)
  - AI Config       → LAUNCHDARKLY_AI_CONFIG_KEY (completion mode), optional for chat extra credit
  - Experiment metric event name → EXPERIMENT_CONVERSION_EVENT_KEY, optional for experimentation
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    feature_flag_key: str
    sdk_key: str
    ai_config_key: str
    experiment_conversion_event_key: str
    ld_observability_enabled: bool
    otel_service_name: str
    otel_service_version: str

    @staticmethod
    def load() -> "Settings":
        return Settings(
            # LD UI: create a boolean flag with this exact key (or change the env default to match your flag).
            feature_flag_key=os.getenv("FEATURE_FLAG_KEY", "hero-component-v2").strip(),
            # LD UI: Environments → Server-side SDK key (sdk-…). Paste into .env as LAUNCHDARKLY_SDK_KEY.
            # If empty, ld_service runs offline — flags never sync from LaunchDarkly.
            sdk_key=(os.getenv("LAUNCHDARKLY_SDK_KEY") or "").strip(),
            # LD UI: AI Configs → completion-mode config with this key (optional; chat falls back if missing).
            ai_config_key=os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY", "nimbus-support-chat").strip(),
            # LD UI: metric / experiment event key — match when creating a custom metric for hero CTA events.
            experiment_conversion_event_key=os.getenv(
                "EXPERIMENT_CONVERSION_EVENT_KEY", "nimbus-hero-cta-click"
            ).strip(),
            # LaunchDarkly Observability plugin (OpenTelemetry → LD). See README "Observability".
            ld_observability_enabled=_truthy("LAUNCHDARKLY_OBSERVABILITY"),
            otel_service_name=(os.getenv("OTEL_SERVICE_NAME") or "nimbus").strip(),
            otel_service_version=(os.getenv("OTEL_SERVICE_VERSION") or "dev").strip(),
        )
