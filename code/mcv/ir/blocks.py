"""Typed context-block IR.

A :class:`ContextBlock` is the unit that context-assembly policies select. Each block has a type, a payload in one or
more variants (``full`` and optionally ``short``), dependencies on other blocks, and token costs measured with the
target model's tokenizer (:class:`TokenCounter`).
"""
from __future__ import annotations

import enum
import functools
import hashlib
import json
from dataclasses import dataclass, field


class BlockType(str, enum.Enum):
    GOAL = "goal"
    INSTRUCTIONS = "instructions"
    TOOL_SCHEMA = "tool_schema"
    SKILL_DOC = "skill_doc"
    FACT = "fact"
    EXAMPLE = "example"
    HISTORY_TURN = "history_turn"
    NOTE = "note"


#: Types every policy must include; the task is undefined without them.
MANDATORY_TYPES = frozenset({BlockType.GOAL, BlockType.INSTRUCTIONS})


@dataclass(frozen=True)
class ContextBlock:
    """One unit of context.

    Attributes:
        id: unique within an instance.
        type: block type.
        variants: variant name -> text; ``"full"`` is required, ``"short"`` is an optional compressed variant.
        source: provenance (dataset id, turn index, ...).
        deps: ids of blocks that must be included whenever this block is included.
        group: optional grouping key (e.g., the fact a note summarizes).
        meta: per-block features (order index, gold flag for analysis only, ...). Policies must not read ``meta["gold"]``.
    """

    id: str
    type: BlockType
    variants: dict
    source: str = ""
    deps: tuple = ()
    group: str = ""
    meta: dict = field(default_factory=dict, hash=False, compare=False)

    def __post_init__(self) -> None:
        if "full" not in self.variants:
            raise ValueError(f"block {self.id}: 'full' variant required")

    @property
    def text(self) -> str:
        return self.variants["full"]

    def digest(self) -> str:
        blob = json.dumps({"id": self.id, "type": self.type.value, "variants": self.variants, "deps": list(self.deps)},
                          sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass
class Instance:
    """A task instance: typed blocks plus a deterministic success check."""

    iid: str
    family: str
    blocks: list
    gold: object
    checker: str
    split: str = "dev"
    meta: dict = field(default_factory=dict)

    def by_id(self) -> dict:
        return {b.id: b for b in self.blocks}

    def of_type(self, t: BlockType) -> list:
        return [b for b in self.blocks if b.type == t]

    def mandatory_ids(self) -> list:
        return [b.id for b in self.blocks if b.type in MANDATORY_TYPES]

    def goal_text(self) -> str:
        return " ".join(b.text for b in self.blocks if b.type == BlockType.GOAL)

    def validate(self) -> None:
        """Raise ValueError on duplicate ids, unknown dependencies or dependency cycles."""
        ids = [b.id for b in self.blocks]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.iid}: duplicate block ids")
        graph = {b.id: list(b.deps) for b in self.blocks}
        for b in self.blocks:
            for d in b.deps:
                if d not in graph:
                    raise ValueError(f"{self.iid}: block {b.id} depends on unknown block {d}")
        state: dict = {}

        def visit(n: str) -> None:
            if state.get(n) == 1:
                raise ValueError(f"{self.iid}: dependency cycle through {n}")
            if state.get(n) == 2:
                return
            state[n] = 1
            for m in graph[n]:
                visit(m)
            state[n] = 2

        for n in graph:
            visit(n)

    def to_json(self) -> dict:
        return {"iid": self.iid, "family": self.family, "gold": self.gold, "checker": self.checker,
                "split": self.split, "meta": self.meta,
                "blocks": [{"id": b.id, "type": b.type.value, "variants": b.variants, "source": b.source,
                            "deps": list(b.deps), "group": b.group, "meta": b.meta} for b in self.blocks]}

    @classmethod
    def from_json(cls, d: dict) -> "Instance":
        blocks = [ContextBlock(x["id"], BlockType(x["type"]), x["variants"], x.get("source", ""), tuple(x.get("deps", ())),
                               x.get("group", ""), x.get("meta", {})) for x in d["blocks"]]
        return cls(d["iid"], d["family"], blocks, d["gold"], d["checker"], d.get("split", "dev"), d.get("meta", {}))


class TokenCounter:
    """Counts tokens with the Hugging Face tokenizer matching an Ollama model (cached per text).

    Agreement with Ollama's own ``prompt_eval_count`` is checked on a sample during verification.
    """

    TOKENIZERS = {"qwen3:4b-instruct": "Qwen/Qwen3-8B", "qwen3:8b": "Qwen/Qwen3-8B",
                  "mistral-nemo:12b": "mistralai/Mistral-Nemo-Instruct-2407"}

    def __init__(self, model: str):
        if model not in self.TOKENIZERS:
            raise KeyError(f"no tokenizer mapping for {model}")
        self.model = model
        self._tok = None

    def _load(self):
        if self._tok is None:
            from transformers import AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(self.TOKENIZERS[self.model])
        return self._tok

    @functools.lru_cache(maxsize=500_000)
    def count(self, text: str) -> int:
        return len(self._load().encode(text, add_special_tokens=False))

    def block_cost(self, block: ContextBlock, variant: str = "full") -> int:
        from mcv.ir.render import render_block
        return self.count(render_block(block, variant))
