# Ollie the Owl 🦉 - English Learning Chatbot for Children (under 7)

A friendly chatbot that teaches English step by step (L1 → L2 → L3), notices how the child
is feeling, and switches between **learning, conversation, engagement and support** instead of
drilling non-stop. Responses are rule-driven and take **~1-3 ms of server time**, so end-to-end
latency stays far below the 2 s requirement. An optional LLM (Claude) is used *only* for open-ended chat,
behind a hard timeout.

- **Live URL:** `<paste your deployed URL here>`
- **Architecture diagram:** [`docs/architecture.svg`](docs/architecture.svg) (Mermaid version in [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md))
- **System design:** [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md)
- **Video script (2 min):** [`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md)

## Features vs. requirements

| Requirement | How it is met |
|---|---|
| Progressive learning L1/L2/L3 | 30 items (10 per level): words → phrases → sentences. Level up after 6 correct answers with ≥ 75% rolling accuracy; step back down if accuracy drops below 35%. Spaced review of weak words every 4th item. |
| Child mode detection | `app/modes.py` decides `learn / converse / engage / support` per message from emotion lexicon, safety phrases, boredom/idle signals, repeated failures, and whether an exercise is open. Every decision carries a `reason` (visible in `debug`). |
| Not teaching every turn | After 3 consecutive lesson turns the bot pauses for a feelings check-in. Bored children get a joke/rhyme/story. Sad/scared/angry children get support first. |
| SEL | Emotion naming, breathing ("smell the flower, blow the candle"), growth-mindset praise ("trying makes our brain grow", "I can't… YET"), curiosity prompts, polite phrases (hello / thank you), safety → "tell a trusted grown-up" (`safety_flag` returned for adult-side handling). |
| Context-aware | Per-session profile: name, level, mastery per item, mood history, last word learned, recent turns. Greeting recalls last mood or last word; item selection follows mastery. |
| Latency < 2 s | Deterministic core (~1-3 ms). LLM is optional, off the lesson path, capped at 1.3 s with fallback. `scripts/latency_check.py` verifies p95. |

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

Run the tests (44 tests: mode detection, answer matching, level logic, SEL flows, API + latency):

```bash
pytest
```

Check latency against any running instance (local or deployed):

```bash
python scripts/latency_check.py https://<your-url> 60
```

### Optional: enable the LLM for open-ended chat

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # without it the bot is fully rule-based
export LLM_MODEL=claude-haiku-5-5        # default
export LLM_TIMEOUT=1.3                   # seconds; on timeout we fall back to rules
```

## Deploy (Render, free tier, Docker)

1. Push this repo to GitHub.
2. In Render: **New → Blueprint** → select the repo (it reads `render.yaml`). Or **New → Web Service → Docker**.
3. (Optional) add `ANTHROPIC_API_KEY` in the service's Environment tab.
4. Wait for the build; the URL looks like `https://english-buddy-xxxx.onrender.com`.
5. Verify: open the URL, and `curl https://<url>/api/health` should return `{"status":"ok",...}`.

**Free-tier cold starts:** Render's free instances sleep after ~15 min idle, and the first request can
take 30-60 s. To keep the demo under 2 s, either ping `/api/health` every 5 minutes
(e.g. UptimeRobot, free) or choose a paid instance. Do this *before* the reviewer opens the link.

Any Docker host works the same way (Fly.io, Railway, Cloud Run): the container listens on `$PORT`
(default 8000). **Keep it at one worker/instance**, because sessions are held in memory.

## API

`POST /api/chat`

```json
{ "session_id": "optional-client-id", "message": "cat", "idle": false, "start": false }
```

Response (abridged):

```json
{
  "reply": "Great job, Mia! ⭐\nThis is a dog!\nCan you say: dog?",
  "mode": "learn", "level": 1, "level_name": "Words", "stars": 1,
  "progress": {"correct": 1, "target": 6},
  "quick_replies": ["dog"], "emoji": "🐶", "safety_flag": false,
  "debug": {"reason": "new_item", "detected_mode": "learn", "engine_ms": 0.4, "source": "rules"},
  "session_id": "..."
}
```

`GET /api/health` · `GET /api/session/{id}` (parent-facing progress: level, stars, mastery, mood history).

## Project layout

```
app/
  main.py        FastAPI app, timing middleware, endpoints
  engine.py      dialogue manager (learn / converse / engage / support turns)
  modes.py       mode + emotion detection
  curriculum.py  L1-L3 items, accepted answers, hints
  sel.py         SEL copy: praise, feelings, calming, jokes, rhymes
  state.py       Session model + in-memory TTL store
  llm.py         optional LLM with timeout + safety filter
static/index.html  child-friendly UI (TTS + voice input)
tests/             pytest suite
scripts/latency_check.py
docs/              architecture.svg, SYSTEM_DESIGN.md, VIDEO_SCRIPT.md
Dockerfile, render.yaml
```

## Known limitations

- Sessions are in memory (lost on restart, single instance). See "Scaling path" in the design doc.
- Mode detection is lexicon/rule based, so unusual phrasing can be missed. It is tuned to be conservative
  (safety and negative emotion always win).
- Voice features use the browser's Web Speech API (best in Chrome/Edge/Safari); the app works without them.
- Children's speech recognition is imperfect; answers tolerate small typos but not pronunciation scoring.
- No accounts or stored personal data beyond a first name the child volunteers; a real product would need
  parental consent flows (COPPA/GDPR-K).
