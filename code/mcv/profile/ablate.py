"""Counterfactual ablation conditions for profiling (run on the dev split only).

For an instance with optional block types O (all present types except the mandatory goal/instructions):
  full              every block, full variants
  -T                all blocks of type T removed                       (T in O)
  -T1-T2            both types removed                                 (pairs from O)
  short:T           type T rendered with its "short" variant           (types that have one)
  -b                one block removed (leave-one-block-out, sampled)   (for the instance-level feature model)
  pad:-T            type T replaced by neutral filler of equal token length (length-neutral control, sensitivity)
Each condition is a selection {block_id: variant}; rendering is canonical (mcv.ir.render).
"""
from __future__ import annotations

import itertools
import random

from mcv.ir.blocks import MANDATORY_TYPES, BlockType, Instance

FILLER = "(This section intentionally contains no information.) "


def optional_types(inst: Instance) -> list:
    present = []
    for b in inst.blocks:
        if b.type not in MANDATORY_TYPES and b.type not in present:
            present.append(b.type)
    return present


def conditions(inst: Instance, n_lobo: int = 6, seed: int = 0, pad: bool = False) -> dict:
    """Return {condition_name: {block_id: variant}} for one instance."""
    full = {b.id: "full" for b in inst.blocks}
    out = {"full": dict(full)}
    O = optional_types(inst)
    for t in O:
        out[f"-{t.value}"] = {i: v for i, v in full.items() if inst.by_id()[i].type != t}
        if any("short" in b.variants for b in inst.of_type(t)):
            out[f"short:{t.value}"] = {i: ("short" if inst.by_id()[i].type == t and "short" in inst.by_id()[i].variants
                                           else v) for i, v in full.items()}
    for t1, t2 in itertools.combinations(O, 2):
        out[f"-{t1.value}-{t2.value}"] = {i: v for i, v in full.items() if inst.by_id()[i].type not in (t1, t2)}
    rng = random.Random(f"{inst.iid}-{seed}")
    optional_blocks = [b.id for b in inst.blocks if b.type not in MANDATORY_TYPES]
    for bid in rng.sample(optional_blocks, min(n_lobo, len(optional_blocks))):
        out[f"-b:{bid}"] = {i: v for i, v in full.items() if i != bid}
    if pad:
        for t in O:
            out[f"pad:-{t.value}"] = dict(full)  # rendered with padding by render_condition
    return out


def render_condition(inst: Instance, name: str, selection: dict, counter=None) -> str:
    """Render a condition; ``pad:-T`` replaces type T's blocks by filler of (approximately) equal token length."""
    from mcv.ir.blocks import ContextBlock
    from mcv.ir.render import render
    blocks = [b for b in inst.blocks if b.id in selection]
    if name.startswith("pad:-"):
        t = BlockType(name[5:])
        new = []
        for b in blocks:
            if b.type == t:
                n = counter.block_cost(b) if counter else len(b.text) // 4
                reps = max(1, n // max(1, (counter.count(FILLER) if counter else 12)))
                new.append(ContextBlock(b.id, b.type, {"full": (FILLER * reps).strip()}))
            else:
                new.append(b)
        blocks = new
    return render(blocks, selection, all_blocks=inst.blocks)
