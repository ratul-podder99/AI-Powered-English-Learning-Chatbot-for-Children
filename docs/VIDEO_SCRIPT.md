# 2-Minute Video Script (English, ~250 words)

Record your screen with the live app open (Loom, OBS, or QuickTime). Target 1:45-1:55.
Show: live URL → a short demo → `docs/architecture.svg`.

---

**[0:00-0:15] Intro, show the live app**
"Hi, I'm [Your Name]. This is Ollie the Owl, an English-learning chatbot for children under seven. It's live at this URL, and I'll walk through the key design decisions."

**[0:15-0:50] Demo, show the chat**
"Ollie starts with a name, then teaches in three levels: words, phrases, and sentences. Watch: I answer 'cat'... correct, I get a star and the progress bar moves. A wrong answer gets a hint first, then the answer revealed, no pressure. Now I type 'I am sad'. Ollie stops the lesson, names the feeling, and offers a deep breath, a chat, or a game. When I say 'I'm bored', Ollie switches to a joke, and then invites me back. So it detects four modes: learn, converse, engage, and support."

**[0:50-1:20] Architecture, show diagram**
"Design decision one: a deterministic core. Mode detection, curriculum, and social-emotional content are rule-based Python in FastAPI, taking about one to three milliseconds, so latency is far under two seconds. Decision two: an optional LLM, Claude Haiku, only for open-ended questions, with a 1.3 second timeout and a rule-based fallback, so it can never break the latency budget. Context lives in a session profile: level, mastery per word, mood history, and the last word learned."

**[1:20-1:50] Trade-offs**
"Trade-offs: in-memory sessions mean zero setup and zero latency, but state resets on restart and we run one instance. The next step is Redis. Rule-based emotion detection is fast and explainable, but misses unusual phrasing, so safety and negative emotions always take priority. The frontend is a single static page with browser speech, deployed as one Docker container."

**[1:50-2:00] Close**
"Code, docs, and tests are in the repository. Thank you for watching!"
