"""In-memory session store with TTL eviction.

Trade-off: no database means zero extra latency and zero setup, but state is lost
on restart. The Session object is JSON-serialisable, so swapping the store for
Redis/SQLite is a ~20 line change (see docs/SYSTEM_DESIGN.md).
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional

SESSION_TTL_SECONDS = 60 * 60 * 6
MAX_SESSIONS = 5000


@dataclass
class Session:
    id: str
    created: float = field(default_factory=time.time)
    touched: float = field(default_factory=time.time)

    # profile
    name: Optional[str] = None
    level: int = 1

    # learning state
    pending_item: Optional[str] = None      # id of the exercise currently open
    attempts_on_pending: int = 0
    seen: list = field(default_factory=list)            # item ids shown, in order
    mastery: dict = field(default_factory=dict)         # item id -> 0..1
    recent_results: list = field(default_factory=list)  # last results (1/0) at current level
    correct_at_level: int = 0
    stars: int = 0
    wrong_streak: int = 0
    lesson_streak: int = 0                  # consecutive learn turns without a break
    awaiting_checkin: bool = False
    awaiting_choice: bool = False           # offered (rest/talk/play) after a support turn

    # affect / context
    mood: str = "neutral"                   # last detected emotion label
    mood_history: list = field(default_factory=list)
    mode: str = "converse"
    mode_history: list = field(default_factory=list)
    turns: int = 0
    last_word: Optional[str] = None
    engage_count: int = 0
    history: list = field(default_factory=list)  # [(role, text)] last 8

    def remember(self, role: str, text: str) -> None:
        self.history.append((role, text))
        self.history = self.history[-8:]

    def to_dict(self) -> dict:
        return asdict(self)


class SessionStore:
    def __init__(self) -> None:
        self._data: dict[str, Session] = {}

    def get(self, sid: str) -> Session:
        now = time.time()
        s = self._data.get(sid)
        if s is None:
            if len(self._data) >= MAX_SESSIONS:
                self._evict(now, force=True)
            s = Session(id=sid)
            self._data[sid] = s
        s.touched = now
        if len(self._data) % 50 == 0:
            self._evict(now)
        return s

    def _evict(self, now: float, force: bool = False) -> None:
        stale = [k for k, v in self._data.items() if now - v.touched > SESSION_TTL_SECONDS]
        for k in stale:
            del self._data[k]
        if force and len(self._data) >= MAX_SESSIONS:
            oldest = sorted(self._data.items(), key=lambda kv: kv[1].touched)[: MAX_SESSIONS // 10]
            for k, _ in oldest:
                del self._data[k]

    def __len__(self) -> int:
        return len(self._data)
