"""Dialogue manager: ties mode detection, curriculum, SEL and (optional) LLM together."""
from __future__ import annotations

import difflib
import re
import time
from typing import Optional

from . import llm, modes, sel
from .curriculum import ITEMS_BY_ID, LEVELS, LEVEL_NAMES, Item, NUMBER_WORDS
from .modes import CONVERSE, ENGAGE, LEARN, SUPPORT
from .state import Session

LEVEL_UP_CORRECT = 6      # correct answers needed at a level
LEVEL_UP_ACCURACY = 0.75  # over the rolling window
WINDOW = 8
LEVEL_DOWN_ACCURACY = 0.35
CHECKIN_EVERY = 3         # break the lesson after this many consecutive learn turns

EMOJI_WORDS = {"😀": "happy", "😊": "happy", "😄": "happy", "🙂": "happy", "😐": "okay", "😢": "sad", "😭": "sad",
               "😡": "angry", "😠": "angry", "😴": "tired", "😨": "scared", "😱": "scared"}


# --------------------------------------------------------------------------- helpers
def _emoji_to_words(text: str) -> str:
    for e, w in EMOJI_WORDS.items():
        text = text.replace(e, f" {w} ")
    return text.strip()


def _name(s: Session) -> str:
    return s.name or "friend"


def _fmt(template: str, s: Session, **kw) -> str:
    return template.format(n=_name(s), **kw)


def check_answer(item: Item, text: str) -> bool:
    t = modes.normalize(text)
    if not t:
        return False
    if item.id == "l3_name":
        return bool(modes.extract_name(text)) or "my name is" in t
    tokens = t.split()
    tokens = [NUMBER_WORDS.get(tok, tok) if tok in NUMBER_WORDS and item.kind == "count" else tok for tok in tokens]
    answers = set(item.answers)
    if item.kind == "order":
        return " ".join(w for w in tokens if w) == item.answers[0] or t.replace(" ", "") == item.answers[0].replace(" ", "")
    # negative guard: "not a cat"
    if "not" in tokens or "no" in tokens and len(tokens) > 1:
        return False
    for tok in tokens:
        if tok in answers:
            return True
        # typo tolerance for words of 4+ letters (kids can't spell yet)
        if len(tok) >= 4:
            for a in answers:
                if len(a) >= 4 and difflib.SequenceMatcher(None, tok, a).ratio() >= 0.8:
                    return True
    return False


def _rolling_accuracy(s: Session) -> float:
    r = s.recent_results[-WINDOW:]
    return sum(r) / len(r) if r else 1.0


def pick_next_item(s: Session) -> Item:
    level_items = LEVELS[s.level]
    last = s.seen[-1] if s.seen else None
    # every 4th item at a level: spaced review of the weakest word seen so far
    if len(s.seen) % 4 == 3:
        weak = [(s.mastery.get(i, 0), i) for i in set(s.seen) if s.mastery.get(i, 1) < 0.6 and i != last]
        if weak:
            return ITEMS_BY_ID[min(weak)[1]]
    unseen = [i for i in level_items if i.id not in s.seen]
    if unseen:
        return unseen[0]
    candidates = [i for i in level_items if i.id != last] or level_items
    return min(candidates, key=lambda i: s.mastery.get(i.id, 0))


def _present(item: Item) -> str:
    parts = [item.teach, item.prompt] if item.teach else [item.prompt]
    return "\n".join(p for p in parts if p)


def _resp(s: Session, reply: str, mode: str, emoji: str = "🦉", quick: Optional[list] = None,
          reason: str = "", source: str = "rules", safety: bool = False) -> dict:
    s.remember("bot", reply)
    s.mode = mode
    s.mode_history = (s.mode_history + [mode])[-10:]
    return {
        "reply": reply,
        "speak": re.sub(r"[^\w\s,.!?'\-:/]", "", reply).replace("___", "blank"),
        "emoji": emoji,
        "mode": mode,
        "level": s.level,
        "level_name": LEVEL_NAMES[s.level],
        "stars": s.stars,
        "progress": {"correct": s.correct_at_level, "target": LEVEL_UP_CORRECT},
        "quick_replies": quick or [],
        "safety_flag": safety,
        "debug": {"reason": reason, "source": source, "mood": s.mood},
    }


# --------------------------------------------------------------------------- learn
def _start_item(s: Session, prefix: str = "") -> dict:
    item = pick_next_item(s)
    s.pending_item = item.id
    s.attempts_on_pending = 0
    s.seen.append(item.id)
    text = (prefix + "\n" if prefix else "") + _present(item)
    quick = [o for o in item.options]
    return _resp(s, text, LEARN, item.emoji, quick, reason="new_item")


def _record(s: Session, item: Item, ok: bool, first_try: bool) -> None:
    m = s.mastery.get(item.id, 0.0)
    if ok:
        m = min(1.0, m + (0.34 if first_try else 0.2))
        s.correct_at_level += 1
        s.stars += 1 if first_try else 0
        s.wrong_streak = 0
        s.last_word = item.word
    else:
        m = max(0.0, m - 0.25)
        s.wrong_streak += 1
    s.mastery[item.id] = m
    s.recent_results = (s.recent_results + [1 if ok else 0])[-WINDOW:]


def _maybe_change_level(s: Session) -> Optional[str]:
    acc = _rolling_accuracy(s)
    if s.level < 3 and s.correct_at_level >= LEVEL_UP_CORRECT and acc >= LEVEL_UP_ACCURACY:
        s.level += 1
        s.correct_at_level = 0
        s.recent_results = []
        s.wrong_streak = 0
        return f"🎊 LEVEL UP! You are now on Level {s.level}: {LEVEL_NAMES[s.level]}! 🎊"
    if s.level > 1 and len(s.recent_results) >= 6 and acc < LEVEL_DOWN_ACCURACY:
        s.level -= 1
        s.correct_at_level = 0
        s.recent_results = []
        s.wrong_streak = 0
        return f"Let's practice some easier ones first, {_name(s)}. That helps us get strong! 💪"
    return None


def _learn_turn(s: Session, text: str) -> dict:
    if not s.pending_item:
        s.lesson_streak += 1
        intro = "Yay, let's learn! 🎈" if s.turns <= 2 or s.lesson_streak == 1 else ""
        return _start_item(s, intro)

    item = ITEMS_BY_ID[s.pending_item]
    ok = check_answer(item, text)
    s.attempts_on_pending += 1
    s.lesson_streak += 1

    if ok:
        first_try = s.attempts_on_pending == 1
        _record(s, item, True, first_try)
        s.pending_item = None
        praise = sel.pick(sel.PRAISE, s.turns).format(n=_name(s))
        level_msg = _maybe_change_level(s)
        lines = [praise]
        if level_msg:
            lines.append(level_msg)
        if s.lesson_streak >= CHECKIN_EVERY and not level_msg:
            # not every turn is a lesson: pause for an emotional check-in
            s.lesson_streak = 0
            s.awaiting_checkin = True
            lines.append(sel.pick(sel.CHECKIN, s.turns))
            return _resp(s, "\n".join(lines), CONVERSE, "💗", sel.CHECKIN_REPLIES, reason="sel_checkin")
        return _start_item(s, "\n".join(lines))

    # wrong answer
    if s.attempts_on_pending == 1:
        enc = sel.pick(sel.TRY_AGAIN, s.turns).format(n=_name(s))
        text_out = f"{enc}\nHint: {item.hint}\n{item.prompt}"
        return _resp(s, text_out, LEARN, item.emoji, list(item.options), reason="hint")
    # second miss: reveal, lower pressure, move on
    _record(s, item, False, False)
    s.pending_item = None
    answer = item.answers[0]
    reveal = sel.pick(sel.REVEAL, s.turns).format(a=answer)
    level_msg = _maybe_change_level(s)
    if s.wrong_streak >= 3:
        s.wrong_streak = 0
        s.lesson_streak = 0
        return _resp(s, f"{reveal}\nLearning is hard sometimes, and that's okay! Let's have a little fun first. 🎈",
                     ENGAGE, "🎈", ["🎵 Sing", "😄 Joke", "▶️ Keep learning"], reason="difficulty_break")
    return _start_item(s, "\n".join(x for x in [reveal, level_msg] if x))


# --------------------------------------------------------------------------- support
def _support_turn(s: Session, d: modes.ModeDecision, text: str) -> dict:
    s.lesson_streak = 0
    s.wrong_streak = 0
    s.awaiting_checkin = False
    t = modes.normalize(text)
    if d.signals.get("safety"):
        return _resp(s, _fmt(sel.SAFETY, s), SUPPORT, "💛", ["👍 I told someone"], reason=d.reason, safety=True)
    if d.signals.get("low_confidence"):
        s.pending_item = None
        return _resp(s, _fmt(sel.LOW_CONFIDENCE, s), SUPPORT, "🌱", ["💪 Try again", "🎲 Play a game"], reason=d.reason)
    s.awaiting_choice = True
    s.pending_item = None
    base = _fmt(sel.EMOTION_REPLY.get(d.emotion, sel.EMOTION_REPLY["sad"]), s)
    emoji = {"sad": "💙", "angry": "🔥", "scared": "🛡️", "shy": "🦁"}.get(d.emotion, "💛")
    return _resp(s, f"{base}\n{sel.SUPPORT_OFFER}", SUPPORT, emoji, sel.SUPPORT_REPLIES, reason=d.reason)


def _handle_choice(s: Session, text: str) -> dict:
    s.awaiting_choice = False
    t = modes.normalize(text)
    if "breath" in t:
        return _resp(s, sel.BREATHING, SUPPORT, "🌸", ["😊 Better", "😐 Same"], reason="breathing")
    if "talk" in t or "tell" in t:
        return _resp(s, f"I'm listening, {_name(s)}. 👂 Tell me with a few words.", SUPPORT, "👂", reason="listening")
    return _engage_turn(s, modes.ModeDecision(ENGAGE, "chosen_game"))


# --------------------------------------------------------------------------- engage
def _engage_turn(s: Session, d: modes.ModeDecision, text: str = "") -> dict:
    s.lesson_streak = 0
    s.wrong_streak = 0
    s.pending_item = None
    flags = modes.intent_flags(text)
    n = s.engage_count
    s.engage_count += 1
    if flags["joke"] or (n % 3 == 0 and not flags["song"] and not flags["story"]):
        q, a = sel.JOKES[n % len(sel.JOKES)]
        body, emoji = f"{q}\n{a}", "😹"
    elif flags["song"] or n % 3 == 1:
        body, emoji = sel.SONGS[n % len(sel.SONGS)], "🎵"
    else:
        body, emoji = sel.STORIES[0], "📖"
    opener = sel.pick(sel.ENGAGE_OPENERS, n).format(n=_name(s))
    bridge = sel.pick(sel.ENGAGE_BRIDGE, n)
    return _resp(s, f"{opener}\n{body}\n{bridge}", ENGAGE, emoji, ["▶️ Yes", "😄 Another one", "🛑 No thanks"],
                 reason=d.reason)


# --------------------------------------------------------------------------- converse
async def _converse_turn(s: Session, d: modes.ModeDecision, text: str) -> dict:
    flags = modes.intent_flags(text)
    new_name = modes.extract_name(text)
    s.lesson_streak = 0

    if s.awaiting_checkin:
        s.awaiting_checkin = False
        base = _fmt(sel.EMOTION_REPLY.get(d.emotion, "Thanks for telling me, {n}! 💛"), s)
        return _resp(s, f"{base}\nWant to keep learning?", CONVERSE, "💗", ["▶️ Yes", "🎵 A song", "🛑 Stop"], reason="checkin_reply")

    if new_name:
        s.name = new_name
        return _resp(s, f"Nice to meet you, {s.name}! 🦉 What a lovely name. Want to learn some English words?",
                     CONVERSE, "🦉", ["▶️ Yes", "💬 Chat"], reason="learned_name")

    if flags["bye"]:
        return _resp(s, _fmt(sel.pick(sel.SOCIAL["bye"], s.turns), s), CONVERSE, "👋", reason="bye")

    if flags["thanks"]:
        return _resp(s, _fmt(sel.SOCIAL["thanks"][0], s), CONVERSE, "💛", ["▶️ Learn more"], reason="thanks")

    if flags["name_q"]:
        return _resp(s, f"My name is Ollie the Owl! 🦉 What is your name? Say: My name is ...", CONVERSE, "🦉", reason="name_q")

    if d.emotion in modes.LOW_ENERGY:
        base = _fmt(sel.EMOTION_REPLY[d.emotion], s)
        return _resp(s, f"{base}\nWe can chat, or learn one tiny word.", CONVERSE, "😴" if d.emotion == "tired" else "🍎",
                     ["💬 Chat", "▶️ One tiny word"], reason=d.reason)

    if d.emotion in modes.POSITIVE:
        base = _fmt(sel.EMOTION_REPLY[d.emotion], s)
        return _resp(s, f"{base}\nWant to learn something new?", CONVERSE, "🎉", ["▶️ Yes", "💬 Chat"], reason=d.reason)

    if flags["greet"] or s.turns <= 1:
        greeting = _fmt(sel.pick(sel.SOCIAL["greet"], s.turns), s)
        # context-aware: follow up on earlier feelings or the last word learned
        recent = s.mood_history[-1:] if s.mood_history else []
        if recent and recent[0] in modes.NEGATIVE:
            extra = "Last time you felt a little down. How are you feeling now? 💛"
        elif s.last_word:
            extra = f"Do you remember the word \"{s.last_word}\"? Want to practice more?"
        else:
            extra = "Do you want to learn English with me?"
        return _resp(s, f"{greeting}\n{extra}", CONVERSE, "🦉", ["▶️ Yes", "💬 Chat"], reason="greeting")

    # open-ended: try the LLM within its budget, otherwise rules
    out = await llm.reply(s, text) if flags["question"] or len(text.split()) > 2 else None
    if out:
        return _resp(s, out, CONVERSE, "🦉", ["▶️ Let's learn", "💬 Chat more"], reason="open_chat", source="llm")
    curious = sel.pick(sel.CURIOUS, s.turns)
    if flags["question"]:
        reply = f"What a great question, {_name(s)}! 🦉 I'm a little owl, so I know best about English words. {curious}"
    else:
        reply = f"Thanks for telling me! 😊 {curious}"
    return _resp(s, f"{reply}\nWant to play a word game?", CONVERSE, "🦉", ["▶️ Yes", "💬 Chat more"], reason="chat")


# --------------------------------------------------------------------------- public API
async def handle(s: Session, text: str, idle: bool = False) -> dict:
    t0 = time.perf_counter()
    text = _emoji_to_words((text or "").strip()[:300])
    s.turns += 1
    if text:
        s.remember("user", text)

    d = modes.detect(text, s, idle=idle)
    if d.emotion != "neutral":
        s.mood = d.emotion
        s.mood_history = (s.mood_history + [d.emotion])[-10:]

    if d.mode == SUPPORT:
        out = _support_turn(s, d, text)
    elif s.awaiting_choice:
        out = _handle_choice(s, text)
    elif d.mode == ENGAGE:
        out = _engage_turn(s, d, text)
    elif d.mode == LEARN:
        s.awaiting_checkin = False
        out = _learn_turn(s, text)
    else:
        out = await _converse_turn(s, d, text)

    # learning intent expressed as "yes"/"play" after an engage/chat turn
    out["debug"]["signals"] = d.signals
    out["debug"]["detected_mode"] = d.mode
    out["debug"]["engine_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return out


async def start(s: Session) -> dict:
    """First message of a session (also used when a returning child opens the app)."""
    s.turns += 1
    if s.turns > 1 or s.history:
        return await _converse_turn(s, modes.ModeDecision(CONVERSE, "return"), "hello")
    return _resp(
        s,
        "Hello! I am Ollie the Owl. 🦉\nI help kids learn English. What is your name?\nYou can say: My name is ...",
        CONVERSE, "🦉", ["▶️ Let's learn", "💬 Chat"], reason="first_visit",
    )
