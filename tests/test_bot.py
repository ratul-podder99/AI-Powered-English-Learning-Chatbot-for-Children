import asyncio

import pytest

from app import engine, modes
from app.curriculum import ITEMS_BY_ID, LEVELS
from app.state import Session


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def say(s, text, **kw):
    return run(engine.handle(s, text, **kw))


def new():
    s = Session(id="test-session-1")
    run(engine.start(s))
    return s


# ---------------------------------------------------------------- mode detection
@pytest.mark.parametrize("text,mode", [
    ("I am sad", modes.SUPPORT),
    ("I'm scared of the monster", modes.SUPPORT),
    ("I can't do it", modes.SUPPORT),
    ("someone hits me", modes.SUPPORT),
    ("tell me a joke", modes.ENGAGE),
    ("I am bored", modes.ENGAGE),
    ("idk", modes.ENGAGE),
    ("hello", modes.CONVERSE),
    ("my name is Rafi", modes.CONVERSE),
    ("yes", modes.LEARN),
    ("let's play", modes.LEARN),
])
def test_mode_detection(text, mode):
    s = Session(id="x")
    assert modes.detect(text, s).mode == mode


def test_idle_triggers_engage():
    assert modes.detect("", Session(id="x"), idle=True).mode == modes.ENGAGE


def test_pending_exercise_means_learn():
    s = Session(id="x", pending_item="l1_cat")
    assert modes.detect("cat", s).mode == modes.LEARN


# ---------------------------------------------------------------- answer checking
@pytest.mark.parametrize("item,text,ok", [
    ("l1_cat", "cat", True), ("l1_cat", "Cat!", True), ("l1_cat", "it is a cat", True),
    ("l1_cat", "dog", False), ("l1_cat", "not cat", False),
    ("l2_count3", "3", True), ("l2_count3", "three", True), ("l2_count3", "four", False),
    ("l2_banana", "yelow", True), ("l2_banana", "green", False),
    ("l3_order", "This is a dog", True), ("l3_order", "dog is this", False),
    ("l3_name", "my name is Rafi", True),
    ("l3_in_box", "in", True), ("l3_in_box", "on", False),
])
def test_check_answer(item, text, ok):
    assert engine.check_answer(ITEMS_BY_ID[item], text) is ok


# ---------------------------------------------------------------- flows
def test_first_message_asks_name():
    s = Session(id="x")
    r = run(engine.start(s))
    assert "name" in r["reply"].lower() and r["mode"] == "converse"


def test_name_is_remembered_and_used():
    s = new()
    say(s, "my name is Rafi")
    assert s.name == "Rafi"
    r = say(s, "yes")
    assert r["mode"] == "learn"


def test_correct_answer_progresses_and_gives_star():
    s = new()
    say(s, "yes")
    first = s.pending_item
    r = say(s, ITEMS_BY_ID[first].answers[0])
    assert s.stars == 1 and s.correct_at_level == 1
    assert s.pending_item and s.pending_item != first
    assert r["mode"] == "learn"


def test_wrong_then_hint_then_reveal():
    s = new()
    say(s, "yes")
    first = s.pending_item
    r1 = say(s, "banana split")
    assert "Hint" in r1["reply"] and s.pending_item == first
    r2 = say(s, "zebra")
    assert ITEMS_BY_ID[first].answers[0] in r2["reply"]
    assert s.pending_item != first
    assert s.mastery[first] == 0


def test_not_every_turn_is_a_lesson_sel_checkin():
    s = new()
    say(s, "yes")
    modes_seen = []
    for _ in range(4):
        r = say(s, ITEMS_BY_ID[s.pending_item].answers[0]) if s.pending_item else say(s, "yes")
        modes_seen.append(r["mode"])
        if r["mode"] == "converse":
            break
    assert "converse" in modes_seen          # check-in happened after consecutive lesson turns
    assert s.awaiting_checkin
    r = say(s, "happy")                      # answer the feelings check-in
    assert r["mode"] == "converse" and "happy" in r["reply"].lower()


def test_level_up_after_mastery():
    s = new()
    say(s, "yes")
    ups = 0
    for _ in range(40):
        if s.level == 2:
            break
        if s.pending_item:
            say(s, ITEMS_BY_ID[s.pending_item].answers[0])
        else:
            say(s, "yes")
    assert s.level == 2
    assert s.recent_results == [] or len(s.recent_results) < 3


def test_level_down_when_struggling():
    s = new()
    s.level = 2
    s.recent_results = [0, 0, 0, 0, 0, 0]
    s.correct_at_level = 0
    assert engine._maybe_change_level(s) and s.level == 1


def test_sad_child_gets_support_not_lesson():
    s = new()
    say(s, "yes")
    r = say(s, "I am sad because I miss mom")
    assert r["mode"] == "support" and s.pending_item is None
    assert "learn" not in r["reply"].lower().split("\n")[0]
    r = say(s, "🌸 Deep breath")
    assert "breathe" in r["reply"].lower()


def test_safety_flag():
    s = new()
    r = say(s, "someone hurts me")
    assert r["safety_flag"] is True and "grown-up" in r["reply"]


def test_bored_child_gets_fun_then_returns_to_learning():
    s = new()
    say(s, "yes")
    r = say(s, "I am bored")
    assert r["mode"] == "engage" and s.pending_item is None
    r = say(s, "yes")
    assert r["mode"] == "learn"


def test_repeated_difficulty_triggers_break():
    s = new()
    say(s, "yes")
    modes_seen = []
    for _ in range(8):
        modes_seen.append(say(s, "zzzz qqqq")["mode"])
    assert "engage" in modes_seen


def test_context_aware_greeting_after_sadness():
    s = new()
    say(s, "I am sad")
    s.awaiting_choice = False
    r = say(s, "hello")
    assert "feeling" in r["reply"].lower() or "down" in r["reply"].lower()


def test_context_aware_greeting_recalls_last_word():
    s = new()
    say(s, "yes")
    say(s, ITEMS_BY_ID[s.pending_item].answers[0])
    s.mood_history = []
    s.pending_item = None
    r = say(s, "hello")
    assert s.last_word in r["reply"]


def test_empty_and_long_input_are_safe():
    s = new()
    assert say(s, "")["reply"]
    assert say(s, "a" * 5000)["reply"]
    assert say(s, "😀")["reply"]


def test_all_items_well_formed():
    for lv, items in LEVELS.items():
        assert len(items) >= 10
        for it in items:
            assert it.level == lv and it.answers and it.prompt and it.hint
            assert engine.check_answer(it, it.answers[0]) or it.id == "l3_name"


# ---------------------------------------------------------------- API + latency
def test_api_roundtrip_and_latency():
    import time
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.post("/api/chat", json={"start": True}).json()
    sid = r["session_id"]
    worst = 0.0
    for msg in ["my name is Mia", "yes", "cat", "dog", "hello", "I am sad", "bored", "yes"]:
        t0 = time.perf_counter()
        out = c.post("/api/chat", json={"session_id": sid, "message": msg}).json()
        worst = max(worst, time.perf_counter() - t0)
        assert out["reply"] and out["mode"] in {"learn", "converse", "engage", "support"}
    assert worst < 2.0
    assert c.get("/api/health").json()["status"] == "ok"
    assert c.get("/").status_code == 200
