"""FastAPI entrypoint: JSON chat API + static frontend."""
from __future__ import annotations

import os
import re
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import engine, llm
from .state import SessionStore

app = FastAPI(title="Ollie the Owl - English Buddy", version="1.0.0")
store = SessionStore()
STATIC = Path(__file__).resolve().parent.parent / "static"
SID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class ChatIn(BaseModel):
    session_id: str | None = Field(default=None, description="Client-generated id; created if missing")
    message: str = Field(default="", max_length=300)
    idle: bool = False          # client sends true when the child has been silent for a while
    start: bool = False         # true on first open of the app


@app.middleware("http")
async def timing(request: Request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    resp.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
    resp.headers["Cache-Control"] = resp.headers.get("Cache-Control", "no-store" if request.url.path.startswith("/api") else "public, max-age=300")
    return resp


@app.post("/api/chat")
async def chat(body: ChatIn):
    sid = body.session_id if body.session_id and SID_RE.match(body.session_id) else uuid.uuid4().hex
    s = store.get(sid)
    out = await (engine.start(s) if body.start else engine.handle(s, body.message, idle=body.idle))
    out["session_id"] = sid
    return JSONResponse(out)


@app.get("/api/session/{sid}")
async def session_info(sid: str):
    """Parent-facing progress snapshot (no message content beyond the last turns kept in memory)."""
    if not SID_RE.match(sid):
        return JSONResponse({"error": "bad id"}, status_code=400)
    s = store.get(sid)
    return {"name": s.name, "level": s.level, "stars": s.stars, "mastery": s.mastery, "mood_history": s.mood_history,
            "turns": s.turns}


@app.get("/api/health")
async def health():
    return {"status": "ok", "sessions": len(store), "llm_enabled": llm.enabled(), "version": app.version}


app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")
