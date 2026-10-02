"""Instance-level block value model.

Type-level MCV says how much a *kind* of block is worth; selecting among many blocks of one type (30 tool schemas,
20 documents, 24 sessions) needs instance-level signal. We fit a ridge regression, on dev leave-one-block-out deltas,
from cheap features to the block's marginal value. Features never use gold labels:
  type one-hot, type MCV (from the profile), lexical overlap with the goal (fraction of goal content words in the block),
  BM25 rank of the block within its type (normalized), log token length, recency (history order, normalized).
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
from sklearn.linear_model import Ridge

from mcv.ir.blocks import BlockType, Instance

TYPES = [t.value for t in BlockType]
STOP = set("a an the of in on to and or for is are was were be by with what which who when where how does do did "
           "it its this that as at from user user's current question request".split())


def words(s: str) -> list:
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]


def _bm25(query: list, docs: list, k1: float = 1.2, b: float = 0.75) -> list:
    N = len(docs)
    if N == 0:
        return []
    avg = sum(len(d) for d in docs) / N or 1.0
    df = Counter(w for d in docs for w in set(d))
    out = []
    for d in docs:
        tf = Counter(d)
        sc = 0.0
        for w in query:
            if w in tf:
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                sc += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg))
        out.append(sc)
    return out


def block_features(inst: Instance, profile: dict, counter) -> dict:
    """Return {block_id: feature vector (list)}."""
    q = words(inst.goal_text())
    qs = set(q)
    feats = {}
    by_type: dict = {}
    for b in inst.blocks:
        by_type.setdefault(b.type, []).append(b)
    for t, bs in by_type.items():
        scores = _bm25(q, [words(b.text) for b in bs])
        order = np.argsort(np.argsort(-np.asarray(scores))) if scores else []
        for j, b in enumerate(bs):
            w = set(words(b.text))
            overlap = len(qs & w) / max(1, len(qs))
            rank = float(order[j]) / max(1, len(bs) - 1) if len(bs) > 1 else 0.0
            recency = (b.meta.get("order", 0) / max(1, len(bs) - 1)) if t == BlockType.HISTORY_TURN else 0.0
            mcv = profile.get("mcv", {}).get(t.value, {}).get("value", 0.0)
            onehot = [1.0 if t.value == x else 0.0 for x in TYPES]
            feats[b.id] = onehot + [mcv, overlap, 1.0 - rank, math.log1p(counter.block_cost(b)) / 10, recency]
    return feats


class BlockValueModel:
    """Ridge regression from block features to leave-one-block-out delta."""

    def __init__(self, alpha: float = 1.0):
        self.m = Ridge(alpha=alpha)
        self.fitted = False

    def fit(self, X: list, y: list) -> "BlockValueModel":
        if len(X) >= 5:
            self.m.fit(np.asarray(X), np.asarray(y))
            self.fitted = True
        return self

    def predict(self, X: list) -> np.ndarray:
        X = np.asarray(X)
        if not self.fitted:
            return X[:, len(TYPES)]  # fall back to the type MCV feature
        return self.m.predict(X)
