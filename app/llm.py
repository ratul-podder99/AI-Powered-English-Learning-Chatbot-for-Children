"""Optional LLM layer for open-ended chat.

Design rule: the LLM is *never* on the critical path of teaching. Lessons, mode
detection and SEL are deterministic and run in <10 ms. The LLM is only asked to
answer free-form questions in conversation mode, with a hard timeout; on timeout,
error, missing key or an unsafe-looking answer, we fall back to rule-based text.
That keeps end-to-end latency under 2 s in all cases.
"""
from __future__ import annotations

import os
import re
from typing import Optional

import httpx

from .state import Session

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "1.3"))   # seconds; budget leaves room for rules + network
URL = "https://api.anthropic.com/v1/messages"

_client: Optional[httpx.AsyncClient] = None


def enabled() -> bool:
    return bool(API_KEY)


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=TIMEOUT)
    return _client


def build_system(s: Session) -> str:
    return (
        "You are Ollie the Owl, a kind English tutor for children under 7. "
        f"The child's name is {s.name or 'friend'}. English level: {s.level} of 3 "
        "(1 = single words, 2 = short phrases, 3 = short sentences). "
        f"Recent mood: {s.mood}. Last word learned: {s.last_word or 'none yet'}. "
        "Rules: reply in 1 or 2 very short, simple sentences (max 25 words). "
        "Use words a 5 year old knows. Be warm and encouraging. Use 1 emoji. "
        "Do not ask for personal information such as address, school or phone number. "
        "Never discuss violence, scary or adult topics; gently change the subject to a happy topic. "
        "If the child seems hurt or unsafe, tell them to find a trusted grown-up. "
        "Do not give a lesson unless asked."
    )


_BAD = re.compile(r"https?://|www\.|\b(kill|die|dead|sex|gun|drug|beer|wine)\b", re.I)


async def reply(s: Session, text: str) -> Optional[str]:
    if not enabled():
        return None
    msgs = [{"role": "user" if r == "user" else "assistant", "content": t} for r, t in s.history[-6:]]
    msgs.append({"role": "user", "content": text[:300]})
    # API requires alternating roles starting with user
    cleaned: list = []
    for m in msgs:
        if cleaned and cleaned[-1]["role"] == m["role"]:
            cleaned[-1]["content"] += " " + m["content"]
        else:
            cleaned.append(m)
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    try:
        r = await _get_client().post(
            URL,
            headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 80, "system": build_system(s), "messages": cleaned},
        )
        r.raise_for_status()
        out = "".join(b.get("text", "") for b in r.json().get("content", [])).strip()
    except Exception:
        return None
    if not out or len(out) > 260 or _BAD.search(out):
        return None
    return out
