"""Measure end-to-end latency against a running server.

Usage: python scripts/latency_check.py https://your-app.onrender.com [N]
Prints p50 / p95 / max over N requests (default 40) and exits non-zero if p95 >= 2 s.
"""
import statistics
import sys
import time

import httpx

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
msgs = ["hello", "my name is Mia", "yes", "cat", "dog", "I am sad", "deep breath", "bored", "yes", "apple", "why is the sky blue?"]

with httpx.Client(timeout=10) as c:
    c.get(f"{base}/api/health")  # warm-up / wake free-tier dyno
    sid = c.post(f"{base}/api/chat", json={"start": True}).json()["session_id"]
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        r = c.post(f"{base}/api/chat", json={"session_id": sid, "message": msgs[i % len(msgs)]})
        r.raise_for_status()
        times.append((time.perf_counter() - t0) * 1000)

times.sort()
p50, p95 = statistics.median(times), times[int(len(times) * 0.95) - 1]
print(f"requests={n}  p50={p50:.0f} ms  p95={p95:.0f} ms  max={times[-1]:.0f} ms")
sys.exit(0 if p95 < 2000 else 1)
