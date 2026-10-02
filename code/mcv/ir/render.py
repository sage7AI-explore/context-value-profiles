"""Deterministic rendering of a selected block set into a prompt.

Order policy (fixed): instructions, tool schemas, skill docs, examples, facts, notes, history turns (instance order,
i.e. chronological), goal last. Within a type, blocks keep instance order. Rendering is a pure function of
(selected blocks, variants), so identical selections produce byte-identical prompts.
"""
from __future__ import annotations

from mcv.ir.blocks import BlockType, ContextBlock

ORDER = [BlockType.INSTRUCTIONS, BlockType.TOOL_SCHEMA, BlockType.SKILL_DOC, BlockType.EXAMPLE, BlockType.FACT,
         BlockType.NOTE, BlockType.HISTORY_TURN, BlockType.GOAL]
HEADER = {BlockType.INSTRUCTIONS: "Instructions", BlockType.TOOL_SCHEMA: "Tool", BlockType.SKILL_DOC: "Guide",
          BlockType.EXAMPLE: "Example", BlockType.FACT: "Document", BlockType.NOTE: "Note",
          BlockType.HISTORY_TURN: "Conversation", BlockType.GOAL: "Task"}


def render_block(block: ContextBlock, variant: str = "full") -> str:
    text = block.variants.get(variant)
    if text is None:
        raise KeyError(f"block {block.id} has no variant {variant!r}")
    return f"### {HEADER[block.type]}\n{text.strip()}\n"


def render(selected: list, variants: dict | None = None, all_blocks: list | None = None) -> str:
    """Render ``selected`` blocks in canonical order; ``all_blocks`` fixes within-type order."""
    variants = variants or {}
    ref = {b.id: i for i, b in enumerate(all_blocks or selected)}
    chosen = sorted(selected, key=lambda b: (ORDER.index(b.type), ref.get(b.id, 0)))
    return "\n".join(render_block(b, variants.get(b.id, "full")) for b in chosen)
