import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    feature_flag_key: str
    sdk_key: str
    ai_config_key: str
    experiment_conversion_event_key: str

    @staticmethod
    def load() -> "Settings":
        return Settings(
            # Must match the boolean flag key you created in LaunchDarkly (e.g. "hero-component-v2").
            # Create this flag in your LD project before running the app.
            feature_flag_key=os.getenv("FEATURE_FLAG_KEY", "hero-component-v2").strip(),
            # Replace with your server-side SDK key from LaunchDarkly (Settings → Environments → SDK key).
            # Without this, the app runs in offline mode and all flags return their default values.
            sdk_key=(os.getenv("LAUNCHDARKLY_SDK_KEY") or "").strip(),
            # Must match the completion-mode AI Config key you created in LaunchDarkly.
            ai_config_key=os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY", "nimbus-support-chat").strip(),
            # Must match the custom metric event key you created in LaunchDarkly for experimentation.
            experiment_conversion_event_key=os.getenv(
                "EXPERIMENT_CONVERSION_EVENT_KEY", "nimbus-hero-cta-click"
            ).strip(),
        )
