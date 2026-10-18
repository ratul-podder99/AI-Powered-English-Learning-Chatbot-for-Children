"""Child mode / mood detection.

Pure-Python, rule + lexicon based (sub-millisecond). Produces a ModeDecision with the
selected mode and the signals that led to it, so decisions are explainable and testable.

Modes
  learn     - the child is attempting an exercise or asks to learn/play
  converse  - small talk, questions, sharing, greetings
  engage    - the child seems bored/disengaged: switch activity (joke, song, game)
  support   - negative emotion, frustration, low confidence or a safety concern
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .state import Session

LEARN, CONVERSE, ENGAGE, SUPPORT = "learn", "converse", "engage", "support"

EMOTIONS = {
    "sad": ["sad", "cry", "crying", "cried", "unhappy", "miss mom", "miss dad", "miss my mom", "miss my dad", "lonely", "alone"],
    "angry": ["angry", "mad", "hate", "furious", "annoyed", "grr"],
    "scared": ["scared", "afraid", "fear", "nightmare", "monster", "frightened"],
    "tired": ["tired", "sleepy", "sleep", "yawn", "exhausted"],
    "hungry": ["hungry", "thirsty"],
    "shy": ["shy", "nervous", "worried"],
    "happy": ["happy", "good", "great", "fine", "glad", "yay", "fun", "love", "awesome", "wonderful"],
    "excited": ["excited", "wow", "yippee", "hooray", "cool", "super"],
    "proud": ["proud", "i did it", "i won"],
}
NEGATIVE = {"sad", "angry", "scared", "shy"}
LOW_ENERGY = {"tired", "hungry"}
POSITIVE = {"happy", "excited", "proud"}

LOW_CONFIDENCE = ["i can't", "i cant", "i cannot", "too hard", "it's hard", "its hard", "i'm bad", "im bad",
                  "i am bad", "i'm stupid", "im stupid", "i am stupid", "i don't know how", "dumb", "i give up"]
SAFETY = ["hit me", "hurts me", "hurt me", "hits me", "touch me", "touched me", "someone is hurting",
          "i am bleeding", "i'm bleeding", "i want to die", "kill myself", "alone at home", "home alone", "stranger"]
DISENGAGED = ["idk", "i don't know", "i dont know", "bored", "boring", "no", "nope", "nah", "don't want",
              "dont want", "stop", "quit", "whatever", "meh", "hmm", "hm", "ugh", "nothing", "blah",
              "i don't want", "no more", "enough"]
AFFIRM = {"yes", "yeah", "yep", "yup", "ok", "okay", "sure", "ready", "go", "play", "again", "more", "next",
          "start", "lets go", "let's go", "learn", "teach me", "i want to learn", "let's play", "lets play", "yes please"}
GREET = {"hi", "hello", "hey", "hiya", "good morning", "good afternoon", "good evening", "hello!"}
BYE = {"bye", "goodbye", "see you", "good night", "gotta go", "bye bye"}
THANKS = {"thanks", "thank you", "thank u"}
CHAT_Q = re.compile(r"\b(why|how come|who are you|what is your|what's your|where do you|do you|are you|can you|what do you|tell me|story|joke|song)\b")
NAME_RE = re.compile(r"\b(?:my name is|i am called|i'm called|call me)\s+([a-zA-Z]{2,15})\b", re.I)
REQUEST_JOKE = re.compile(r"\b(joke|funny|laugh)\b")
REQUEST_SONG = re.compile(r"\b(song|sing)\b")
REQUEST_STORY = re.compile(r"\bstory\b")
REQUEST_GAME = re.compile(r"\b(game|play)\b")


@dataclass
class ModeDecision:
    mode: str
    reason: str
    emotion: str = "neutral"
    signals: dict = field(default_factory=dict)


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9' ]+", " ", text.lower()).strip()


def _has(text: str, phrases) -> bool:
    padded = f" {text} "
    return any(f" {p} " in padded for p in phrases)


def detect_emotion(text: str) -> str:
    t = normalize(text)
    # check negative first so "not happy / i am sad" isn't read as happy
    for label in ("sad", "angry", "scared", "shy", "tired", "hungry", "proud", "excited", "happy"):
        if _has(t, EMOTIONS[label]):
            if label == "happy" and re.search(r"\b(not|no)\s+(happy|good|fine|great)\b", t):
                return "sad"
            return label
    return "neutral"


def detect(text: str, s: Session, idle: bool = False) -> ModeDecision:
    t = normalize(text)
    words = t.split()
    emotion = detect_emotion(text)
    signals = {
        "emotion": emotion,
        "words": len(words),
        "wrong_streak": s.wrong_streak,
        "lesson_streak": s.lesson_streak,
        "pending": bool(s.pending_item),
    }

    # 1. Safety and wellbeing always win.
    if _has(t, SAFETY):
        signals["safety"] = True
        return ModeDecision(SUPPORT, "safety_concern", emotion, signals)
    if emotion in NEGATIVE and not (s.pending_item and len(words) <= 1):
        return ModeDecision(SUPPORT, f"negative_emotion:{emotion}", emotion, signals)
    if _has(t, LOW_CONFIDENCE):
        signals["low_confidence"] = True
        return ModeDecision(SUPPORT, "low_confidence", emotion, signals)

    # 2. Idle ping from the client (child went quiet).
    if idle:
        return ModeDecision(ENGAGE, "idle", emotion, signals)

    # 3. Explicit requests for fun things => engage (child-led).
    if REQUEST_JOKE.search(t) or REQUEST_SONG.search(t) or REQUEST_STORY.search(t):
        return ModeDecision(ENGAGE, "asked_for_fun", emotion, signals)

    # 4. Disengagement (short non-answers, repeated failure, boredom).
    short_noanswer = len(words) <= 3 and _has(t, DISENGAGED)
    if short_noanswer and not (s.pending_item and t in {"no", "nope"} and _is_choice_answer(t, s)):
        return ModeDecision(ENGAGE, "disengaged", emotion, signals)
    if s.wrong_streak >= 3:
        return ModeDecision(ENGAGE, "repeated_difficulty", emotion, signals)

    # 5. Tired / hungry children: gentle conversation, not drilling.
    if emotion in LOW_ENERGY and not s.pending_item:
        return ModeDecision(CONVERSE, f"low_energy:{emotion}", emotion, signals)

    # 6. Open exercise => treat message as an attempt, unless clearly chatting.
    if s.pending_item:
        looks_like_chat = bool(CHAT_Q.search(t)) and len(words) > 3
        if not looks_like_chat:
            return ModeDecision(LEARN, "answering_exercise", emotion, signals)

    # 7. Child asks to start/continue learning.
    if t in AFFIRM or _has(t, AFFIRM):
        return ModeDecision(LEARN, "wants_to_learn", emotion, signals)

    # 8. Everything else is conversation.
    return ModeDecision(CONVERSE, "chat", emotion, signals)


def _is_choice_answer(t: str, s: Session) -> bool:
    from .curriculum import ITEMS_BY_ID
    item = ITEMS_BY_ID.get(s.pending_item or "")
    return bool(item and t in {o.lower() for o in item.options})


def extract_name(text: str):
    m = NAME_RE.search(text)
    return m.group(1).capitalize() if m else None


def intent_flags(text: str) -> dict:
    t = normalize(text)
    return {
        "greet": t in GREET or any(t.startswith(g + " ") for g in GREET),
        "bye": _has(t, BYE),
        "thanks": _has(t, THANKS),
        "joke": bool(REQUEST_JOKE.search(t)),
        "song": bool(REQUEST_SONG.search(t)),
        "story": bool(REQUEST_STORY.search(t)),
        "game": bool(REQUEST_GAME.search(t)),
        "name_q": "your name" in t,
        "question": bool(CHAT_Q.search(t)) or t.endswith("?") or text.strip().endswith("?"),
    }
