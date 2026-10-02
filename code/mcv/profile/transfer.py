"""Profile transfer between models: rank agreement of type-level values and interactions.

A profile measured on a small model is applied unchanged to a larger one (OURS-T). Fidelity is reported as Spearman's
rho between the two models' type MCVs (and interaction terms), alongside the task-success difference between
transferred and native profiles.
"""
from __future__ import annotations

from scipy.stats import spearmanr


def _vec(p: dict, part: str, keys: list) -> list:
    return [p.get(part, {}).get(k, {}).get("value", 0.0) for k in keys]


def fidelity(src: dict, dst: dict) -> dict:
    out = {}
    for part in ("mcv", "interaction"):
        keys = sorted(set(src.get(part, {})) & set(dst.get(part, {})))
        if len(keys) >= 3:
            rho, p = spearmanr(_vec(src, part, keys), _vec(dst, part, keys))
            out[part] = {"rho": float(rho), "p": float(p), "n": len(keys)}
        else:
            out[part] = {"rho": float("nan"), "p": float("nan"), "n": len(keys)}
    return out


def transfer(profile: dict) -> dict:
    """Identity transfer (values are on the success-probability scale and used as-is); kept explicit for clarity."""
    return {**profile, "transferred": True}
