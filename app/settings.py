import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    feature_flag_key: str
    sdk_key: str
    api_access_token: str
    project_key: str
    environment_key: str

    @staticmethod
    def load() -> "Settings":
        return Settings(
            feature_flag_key=os.getenv("FEATURE_FLAG_KEY", "hero-component-v2").strip(),
            sdk_key=(os.getenv("LAUNCHDARKLY_SDK_KEY") or "").strip(),
            api_access_token=(os.getenv("LAUNCHDARKLY_API_ACCESS_TOKEN") or "").strip(),
            project_key=(os.getenv("LAUNCHDARKLY_PROJECT_KEY") or "").strip(),
            environment_key=(os.getenv("LAUNCHDARKLY_ENVIRONMENT_KEY") or "test").strip(),
        )
