"""ABC Company fictional SaaS landing demo — LaunchDarkly SE exercise."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import ldclient
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ldclient.context import Context
from ldclient.evaluation import EvaluationDetail
from pydantic import BaseModel, Field

from app import ai_service, ld_service
from app.ld_service import broadcast_flag_state
from app.settings import Settings

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(directory=str(ROOT / "templates"))

sessions: dict[str, Context] = {}


def _reason_kind(detail: EvaluationDetail | None) -> str:
    if detail is None:
        return ""
    r: Any = detail.reason
    if isinstance(r, dict):
        return str(r.get("kind", ""))
    return str(getattr(r, "kind", "") or "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    settings = Settings.load()
    loop = asyncio.get_running_loop()

    def schedule_broadcast() -> None:
        loop.call_soon_threadsafe(lambda: broadcast_flag_state(settings.feature_flag_key))

    if settings.sdk_key:
        log.info("LaunchDarkly online, flag=%r", settings.feature_flag_key)
    else:
        log.warning("LAUNCHDARKLY_SDK_KEY empty — offline mode")

    ld_service.init_ld(
        sdk_key=settings.sdk_key,
        offline=not bool(settings.sdk_key),
        flag_key=settings.feature_flag_key,
        on_flag_change=schedule_broadcast,
    )
    yield
    ld_service.close_ld()


app = FastAPI(title="ABC Company · Nimbus", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


def get_settings() -> Settings:
    return Settings.load()


def ctx_from_session(session_id: str) -> Context:
    if session_id not in sessions:
        sessions[session_id] = (
            Context.builder(session_id)
            .kind("user")
            .name("Guest")
            .set("email", "")
            .set("plan", "free")
            .set("region", "us-east")
            .build()
        )
    return sessions[session_id]


def replace_context(session_id: str, email: str, name: str, plan: str, region: str) -> Context:
    ctx = (
        Context.builder(session_id)
        .kind("user")
        .name(name[:80] if name else "Guest")
        .set("email", email[:128])
        .set("plan", plan[:64])
        .set("region", region[:64])
        .build()
    )
    sessions[session_id] = ctx
    return ctx


class ContextUpdate(BaseModel):
    email: str = Field("", max_length=128)
    name: str = Field("Jane Developer", max_length=80)
    plan: str = Field("free", max_length=32)
    region: str = Field("us-east", max_length=64)


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


@app.middleware("http")
async def demo_session_cookie(request: Request, call_next):
    sid = request.cookies.get("demo_sid")
    fresh = False
    if not sid:
        sid = str(uuid.uuid4())
        fresh = True
    request.state.demo_sid = sid
    response = await call_next(request)
    if fresh:
        response.set_cookie(
            key="demo_sid",
            value=sid,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    sid = request.state.demo_sid
    ctx = ctx_from_session(sid)
    enabled = bool(ldclient.get().variation(settings.feature_flag_key, ctx, False))
    detail = ldclient.get().variation_detail(settings.feature_flag_key, ctx, False)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "flag_key": settings.feature_flag_key,
            "enabled": enabled,
            "reason": _reason_kind(detail) if detail else "",
            "context_key": sid,
            "session": session_attrs(ctx),
            "ai_config_key": settings.ai_config_key,
            "experiment_event_key": settings.experiment_conversion_event_key,
        },
    )


def session_attrs(ctx: Context) -> dict[str, str]:
    return {
        "email": str(ctx.get("email") or ""),
        "plan": str(ctx.get("plan") or ""),
        "region": str(ctx.get("region") or ""),
        "name": str(ctx.get("name") or ""),
    }


@app.post("/api/context")
async def api_context_update(
    body: ContextUpdate,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    sid = request.state.demo_sid
    replace_context(sid, body.email.strip(), body.name.strip(), body.plan, body.region.strip())
    ctx = sessions[sid]
    broadcast_flag_state(settings.feature_flag_key)
    enabled = bool(ldclient.get().variation(settings.feature_flag_key, ctx, False))
    detail = ldclient.get().variation_detail(settings.feature_flag_key, ctx, False)

    return {
        "ok": True,
        "variation": enabled,
        "evaluation_reason": _reason_kind(detail) if detail else "",
        "attributes": session_attrs(ctx),
    }


@app.post("/api/events/hero-cta")
async def api_experiment_hero_cta(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Send a custom event for experimentation metrics (matches EXPERIMENT_CONVERSION_EVENT_KEY)."""
    sid = request.state.demo_sid
    ctx = ctx_from_session(sid)
    ldclient.get().track(settings.experiment_conversion_event_key, ctx)
    ldclient.get().flush()
    return {"ok": True, "event_key": settings.experiment_conversion_event_key}


@app.post("/api/chat")
async def api_chat(
    body: ChatMessage,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    sid = request.state.demo_sid
    ctx = ctx_from_session(sid)
    return await ai_service.chat_turn(ctx, body.message, settings.ai_config_key)


@app.get("/api/variation")
async def api_variation(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    sid = request.state.demo_sid
    ctx = ctx_from_session(sid)
    enabled = bool(ldclient.get().variation(settings.feature_flag_key, ctx, False))
    detail = ldclient.get().variation_detail(settings.feature_flag_key, ctx, False)
    return {
        "flag_key": settings.feature_flag_key,
        "variation": enabled,
        "evaluation_reason": _reason_kind(detail) if detail else "",
        "attributes": session_attrs(ctx),
    }


@app.get("/events/stream")
async def events_stream(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    sid = request.state.demo_sid

    def resolve_ctx() -> Context:
        return ctx_from_session(sid)

    queue = ld_service.register_connection(resolve_ctx)

    async def gen():
        client = ldclient.get()
        fk = settings.feature_flag_key
        try:
            initial = bool(client.variation(fk, resolve_ctx(), False))
            yield f"data: {json.dumps({'flag_key': fk, 'variation': initial})}\n\n"
            while True:
                val = await queue.get()
                yield f"data: {json.dumps({'flag_key': fk, 'variation': bool(val)})}\n\n"
        finally:
            ld_service.unregister_connection(queue)

    return StreamingResponse(gen(), media_type="text/event-stream")
