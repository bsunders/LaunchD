"""ABC Company fictional SaaS landing demo — LaunchDarkly SE exercise."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import httpx
import ldclient
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ldclient.context import Context
from ldclient.evaluation import EvaluationDetail
from pydantic import BaseModel, Field

from app import ld_service
from app.ld_service import broadcast_flag_state
from app.settings import Settings

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(directory=str(ROOT / "templates"))

# session_id -> LaunchDarkly Context (in-memory; fine for local demo)
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

    ld_service.init_ld(
        sdk_key=settings.sdk_key,
        offline=not bool(settings.sdk_key),
        flag_key=settings.feature_flag_key,
        on_flag_change=schedule_broadcast,
    )
    yield
    ld_service.close_ld()


app = FastAPI(title="ABC Company · Nimbus (LaunchDarkly demo)", lifespan=lifespan)
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
            "session": session_email_plan_region(ctx),
        },
    )


def session_email_plan_region(ctx: Context) -> dict[str, str]:
    """Expose attributes for template (avoid relying on internal Context helpers)."""

    # ldclient.Context uses .get_value - check
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
        "attributes": session_email_plan_region(ctx),
    }


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
        "attributes": session_email_plan_region(ctx),
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
            payload = json.dumps({"flag_key": fk, "variation": initial})
            yield f"data: {payload}\n\n"
            while True:
                val = await queue.get()
                out = json.dumps({"flag_key": fk, "variation": bool(val)})
                yield f"data: {out}\n\n"
        finally:
            ld_service.unregister_connection(queue)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/remediate")
async def api_remediate(settings: Annotated[Settings, Depends(get_settings)]):
    """
    Optional: PATCH the flag's environment toggle off via LaunchDarkly REST API.
    You can always remediate manually in the LaunchDarkly UI instead.
    """
    if not settings.api_access_token or not settings.project_key:
        raise HTTPException(
            status_code=501,
            detail=(
                "Set LAUNCHDARKLY_API_ACCESS_TOKEN and LAUNCHDARKLY_PROJECT_KEY for programmatic "
                "remediation, or turn the flag off in the LaunchDarkly dashboard."
            ),
        )

    flag_key = settings.feature_flag_key
    env_key = settings.environment_key
    url = f"https://app.launchdarkly.com/api/v2/flags/{settings.project_key}/{flag_key}"
    patch_body = [{"op": "replace", "path": f"/environments/{env_key}/on", "value": False}]
    headers = {
        "Authorization": settings.api_access_token,
        "Content-Type": "application/json-patch+json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(url, headers=headers, json=patch_body)

    if r.status_code >= 400:
        log.warning("LaunchDarkly API PATCH failed: %s %s", r.status_code, r.text[:500])
        raise HTTPException(
            status_code=502,
            detail=f"LaunchDarkly API error {r.status_code}: verify PROJECT_KEY, ENVIRONMENT_KEY, and flag key.",
        )

    return {"ok": True, "note": "Flag environment toggle set to off; SSE clients should update within seconds."}


def create_app():
    return app
