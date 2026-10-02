"""Single-decision agent over Ollama /api/chat with a strict text protocol and a content-addressed response cache.

Each instance is one decision: the assembled context (rendered blocks, goal last) is sent as one user message and the
reply is parsed by the family's checker (JSON call for tools; ``ANSWER:`` line for facts/history). Identical prompts
(same model, seed and decoding options) are answered once and reused across policies; every reuse is logged.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
from pathlib import Path

import httpx

OLLAMA = "http://localhost:11434/api/chat"
NUM_CTX = 16384  # fixed for every call so Ollama never reloads the model between conditions
ANSWER = re.compile(r"ANSWER:\s*(.+)", re.I)


def options(seed: int) -> dict:
    return {"temperature": 0, "seed": seed, "num_ctx": NUM_CTX, "num_predict": 96}


def extract_answer(checker: str, text: str) -> str | None:
    if checker == "call":
        return text  # parsed by mcv.eval.metrics.parse_call
    found = ANSWER.findall(text or "")
    if found:
        return found[-1].strip().strip("*`\"' ")
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    return lines[-1] if lines else None


class Cache:
    """SQLite cache keyed by sha256(model, seed, options, prompt)."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path), check_same_thread=False)
        self.con.execute("CREATE TABLE IF NOT EXISTS r (k TEXT PRIMARY KEY, v TEXT)")
        self.lock = threading.Lock()

    @staticmethod
    def key(model: str, seed: int, prompt: str) -> str:
        return hashlib.sha256(json.dumps([model, seed, options(seed), prompt]).encode()).hexdigest()

    def get(self, k: str):
        with self.lock:
            row = self.con.execute("SELECT v FROM r WHERE k=?", (k,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, k: str, v: dict) -> None:
        with self.lock:
            self.con.execute("INSERT OR REPLACE INTO r VALUES (?,?)", (k, json.dumps(v)))
            self.con.commit()


def call(http: httpx.Client, model: str, seed: int, prompt: str, cache: Cache | None = None) -> dict:
    """Return {"text", "prompt_tokens", "completion_tokens", "seconds", "cached", "key"}."""
    k = Cache.key(model, seed, prompt)
    if cache is not None:
        hit = cache.get(k)
        if hit is not None:
            return {**hit, "cached": True, "key": k}
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "options": options(seed)}
    if model.startswith("qwen3"):
        body["think"] = False
    t0 = time.perf_counter()
    for attempt in range(3):
        try:
            r = http.post(OLLAMA, json=body, timeout=600)
            r.raise_for_status()
            break
        except httpx.HTTPError:
            if attempt == 2:
                raise
            time.sleep(5)
    d = r.json()
    out = {"text": d["message"].get("content", ""), "prompt_tokens": d.get("prompt_eval_count", 0),
           "completion_tokens": d.get("eval_count", 0), "seconds": time.perf_counter() - t0}
    if cache is not None:
        cache.put(k, out)
    return {**out, "cached": False, "key": k}
