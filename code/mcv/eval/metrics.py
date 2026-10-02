"""Deterministic success checkers and aggregate metrics."""
from __future__ import annotations

import json
import re
import string

import numpy as np

_ART = re.compile(r"\b(a|an|the)\b")


def normalize(s: str) -> str:
    s = str(s).lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = _ART.sub(" ", s)
    return " ".join(s.split())


def check_qa(pred: str | None, gold: str) -> bool:
    """HotpotQA-style: normalized exact match, or the normalized gold occurs in a short normalized prediction
    (at most 2x gold tokens + 3). Pre-registered in PLAN.md."""
    if pred is None:
        return False
    p, g = normalize(pred), normalize(gold)
    if not g:
        return False
    if p == g:
        return True
    return f" {g} " in f" {p} " and len(p.split()) <= 2 * len(g.split()) + 3


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _value_ok(v, allowed: list) -> bool:
    for a in allowed:
        if a == "" or a is None:
            continue
        na, nv = _num(a), _num(v)
        if na is not None and nv is not None and abs(na - nv) < 1e-6:
            return True
        if isinstance(a, (list, dict)) or isinstance(v, (list, dict)):
            if json.dumps(a, sort_keys=True) == json.dumps(v, sort_keys=True):
                return True
            continue
        if normalize(a) == normalize(v):
            return True
    return False


def parse_call(pred: str | None) -> dict | None:
    """Extract the first JSON object {"name": ..., "arguments": {...}} from a model reply."""
    if not pred:
        return None
    for m in re.finditer(r"\{", pred):
        depth = 0
        for j in range(m.start(), len(pred)):
            depth += {"{": 1, "}": -1}.get(pred[j], 0)
            if depth == 0:
                try:
                    obj = json.loads(pred[m.start():j + 1])
                except json.JSONDecodeError:
                    break
                if isinstance(obj, dict) and "name" in obj:
                    args = obj.get("arguments", obj.get("parameters", {}))
                    return {"name": obj["name"], "arguments": args if isinstance(args, dict) else {}}
                break
    return None


def check_call(pred: str | None, gold: list) -> bool:
    """BFCL-style AST check (simplified): gold is [{func_name: {param: [allowed values]}}]. The call must name the
    gold function, give every parameter whose allowed list lacks "", use allowed values, and add no unknown params."""
    call = parse_call(pred)
    if call is None:
        return False
    for g in gold:
        (fname, params), = g.items()
        if call["name"] != fname:
            continue
        args = call["arguments"]
        if any(k not in params for k in args):
            continue
        ok = True
        for p, allowed in params.items():
            if p in args:
                ok &= _value_ok(args[p], allowed)
            else:
                ok &= ("" in allowed)
        if ok:
            return True
    return False


def check_exact(pred: str | None, gold: str) -> bool:
    return pred is not None and normalize(pred) == normalize(gold)


CHECKERS = {"qa": check_qa, "call": check_call, "exact": check_exact}


def success(checker: str, pred: str | None, gold) -> bool:
    return bool(CHECKERS[checker](pred, gold))


def aubc(budgets: list, success_rates: list) -> float:
    """Normalized area under the success-budget curve, trapezoid rule over log2(budget)."""
    x = np.log2(np.asarray(budgets, float))
    y = np.asarray(success_rates, float)
    if len(x) < 2:
        return float(y.mean())
    return float(np.trapezoid(y, x) / (x[-1] - x[0]))
