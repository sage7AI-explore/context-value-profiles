"""Vector PDF figures from results/processed (Okabe-Ito palette, labeled axes, CIs as bars/bands)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROC, FIG = ROOT / "results/processed", ROOT / "figures"
OK = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "font.family": "DejaVu Sans"})
POLICY_COLOR = {"B0": "#777777", "B1": OK[5], "B2": OK[0], "B3": OK[6], "B4": OK[4], "B5": OK[1], "OURS-A": OK[2],
                "OURS": OK[3], "OURS-T": OK[7]}
POLICY_NAME = {"B0": "B0 full context", "B1": "B1 truncate oldest", "B2": "B2 relevance top-k", "B3": "B3 LLMLingua-2",
               "B4": "B4 coverage (PACMS-style)", "B5": "B5 tier rules", "OURS-A": "MCV additive", "OURS": "MCV + interactions",
               "OURS-T": "MCV transferred (4B)"}


def _box(ax, x, y, w, h, text, color, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.8", fc=color + "26", ec=color, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7, fontweight="bold" if bold else "normal")


def _arrow(ax, a, b, text=""):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9, color="#444", lw=0.9))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 1.3, text, ha="center", fontsize=6, color="#333")


def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(7.0, 2.6))
    ax.set_xlim(0, 100), ax.set_ylim(0, 38), ax.axis("off")
    ax.text(25, 36, "offline, once per (model, task family)", ha="center", fontsize=7, style="italic", color="#555")
    ax.text(77, 36, "online, per instance and budget", ha="center", fontsize=7, style="italic", color="#555")
    ax.plot([52, 52], [2, 35], color="#bbb", lw=0.8, ls="--")
    _box(ax, 0, 22, 16, 10, "Typed block IR\ngoal, tools, docs,\nexamples, history", OK[5])
    _box(ax, 19, 22, 14, 10, "Counterfactual\nablations\n(dev split)", OK[1])
    _box(ax, 36.5, 22, 14, 10, "MCV profile\ntype values +\ninteractions", OK[3], bold=True)
    _box(ax, 18.5, 4, 15, 10, "Leave-one-\nblock-out\ndeltas", OK[1])
    _box(ax, 36, 4, 15, 10, "Block-value\nmodel (ridge,\ncheap features)", OK[3])
    _box(ax, 54, 12, 18, 14, "MCV compiler\nCP-SAT knapsack\nbudget, deps,\nvariants, interactions", OK[2], bold=True)
    _box(ax, 75, 13, 11, 12, "Renderer\n(fixed\norder)", OK[0])
    _box(ax, 89, 13, 11, 12, "Agent\n(one\ndecision)", OK[4])
    _arrow(ax, (16, 27), (19, 27))
    _arrow(ax, (33, 27), (36.5, 27))
    _arrow(ax, (26, 22), (26, 14))
    _arrow(ax, (33, 9), (36.5, 9))
    _arrow(ax, (50.5, 27), (54, 22))
    _arrow(ax, (50.5, 9), (54, 16))
    _arrow(ax, (72, 19), (75, 19))
    _arrow(ax, (86, 19), (89, 19))
    ax.text(63, 5.5, "instance blocks + budget B", ha="center", fontsize=6, color="#333")
    _arrow(ax, (63, 7.5), (63, 12))
    fig.savefig(FIG / "fig1_architecture.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIG.mkdir(exist_ok=True)
    fig_architecture()
    print(sorted(p.name for p in FIG.glob("*.pdf")))


if __name__ == "__main__":
    main()
