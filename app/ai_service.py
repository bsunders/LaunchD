"""LaunchDarkly AI Config + OpenAI via managed model (ldai + ldai_openai)."""

from __future__ import annotations

import logging
import os
from typing import Any

import ldclient
from ldai import LDAIClient
from ldai.models import AICompletionConfigDefault, LDMessage, ModelConfig, ProviderConfig
from ldclient.context import Context

log = logging.getLogger(__name__)


def get_ldai() -> LDAIClient:
    return LDAIClient(ldclient.get())


def _fallback_config() -> AICompletionConfigDefault:
    return AICompletionConfigDefault(
        enabled=True,
        model=ModelConfig(os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")),
        provider=ProviderConfig("openai"),
        messages=[
            LDMessage(
                role="system",
                content=(
                    "You are the Nimbus Workspace assistant for ABC Company. "
                    "Be brief, friendly, and professional."
                ),
            )
        ],
    )


def _ctx_variables(ctx: Context) -> dict[str, Any]:
    return {
        "userName": str(ctx.get("name") or "Guest"),
        "userEmail": str(ctx.get("email") or ""),
        "userPlan": str(ctx.get("plan") or "free"),
    }


def _model_name_from_config(cfg) -> str | None:
    if cfg.model and getattr(cfg.model, "name", None):
        return str(cfg.model.name)
    return None


def _system_prompt_preview(messages: list | None, limit: int = 280) -> str:
    if not messages:
        return ""
    for m in messages:
        if getattr(m, "role", None) == "system" and getattr(m, "content", None):
            s = str(m.content).strip()
            return s if len(s) <= limit else s[: limit - 1] + "…"
    return ""


async def chat_turn(ctx: Context, user_message: str, ai_config_key: str) -> dict[str, Any]:
    """
    One chat turn: evaluates AI Config in LaunchDarkly, then calls OpenAI when configured.
    Without OPENAI_API_KEY, returns evaluated config metadata only (still proves LD-driven prompts/models).
    """
    user_message = (user_message or "").strip()[:4000]
    if not user_message:
        return {"ok": False, "error": "message is required"}

    client = get_ldai()
    variables = _ctx_variables(ctx)
    fallback = _fallback_config()

    cfg = client.completion_config(ai_config_key, ctx, fallback, variables)
    meta: dict[str, Any] = {
        "ai_config_key": ai_config_key,
        "ld_enabled": bool(cfg.enabled),
        "model_name": _model_name_from_config(cfg) or _model_name_from_config(fallback),
        "system_prompt_preview": _system_prompt_preview(cfg.messages or (fallback.messages or [])),
    }

    if not os.getenv("OPENAI_API_KEY", "").strip():
        return {
            "ok": True,
            "mode": "config_only",
            "reply": (
                "This path proved your AI Config was evaluated. Add OPENAI_API_KEY to your "
                "environment to stream a real model response; until then, no call is made to OpenAI."
            ),
            **meta,
        }

    try:
        model = await client.create_model(ai_config_key, ctx, fallback, variables, "openai")
    except Exception as exc:
        log.exception("create_model failed")
        return {"ok": False, "error": str(exc), **meta}

    if model is None:
        return {
            "ok": True,
            "mode": "disabled",
            "reply": "AI Config is disabled for this context in LaunchDarkly (or evaluation failed).",
            **meta,
        }

    try:
        resp = await model.invoke(user_message)
        text = (resp.message.content or "").strip()
        return {"ok": True, "mode": "live", "reply": text, **meta}
    except Exception as exc:
        log.warning("model.invoke failed: %s", exc)
        return {"ok": False, "error": str(exc), **meta}
