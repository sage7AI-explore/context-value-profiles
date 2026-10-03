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


FAMS = [("facts", "Facts (HotpotQA)"), ("history", "History (synthetic)"), ("tool", "Tool (BFCL)")]
MAIN = "qwen3:4b-instruct"
B0_BUDGET = 1_000_000_000


def fig_curves() -> None:
    S = pd.read_csv(PROC / "success.csv")
    S = S[S.model == MAIN]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.3), sharey=True)
    for ax, (fam, title) in zip(axs, FAMS):
        d = S[S.family == fam]
        b0 = d[d.policy == "B0"]
        if len(b0):
            ax.axhline(b0.success.iloc[0], color=POLICY_COLOR["B0"], ls="--", lw=1, label=POLICY_NAME["B0"])
        for p in ["B1", "B3", "B5", "B4", "B2", "OURS-A", "OURS"]:
            g = d[(d.policy == p) & (d.budget < B0_BUDGET)].sort_values("budget")
            if not len(g):
                continue
            lw = 1.8 if p == "OURS" else 1.0
            ax.plot(g.budget, g.success, marker="o", ms=2.5, lw=lw, color=POLICY_COLOR[p], label=POLICY_NAME[p],
                    ls=":" if p == "OURS-A" else "-")
            if p in ("OURS", "B2"):
                ax.fill_between(g.budget, g.lo, g.hi, color=POLICY_COLOR[p], alpha=0.12, lw=0)
        ax.set_xscale("log", base=2)
        ax.set_xticks([1000, 2000, 4000, 8000], ["1k", "2k", "4k", "8k"])
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("token budget")
        ax.set_ylim(0, 1.03)
    axs[0].set_ylabel("task success")
    h, l = axs[2].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, -0.13))
    fig.tight_layout()
    fig.savefig(FIG / "fig2_success_budget.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_profiles() -> None:
    P = pd.read_csv(PROC / "profiles.csv")
    P = P[P.part.isin(["mcv", "interaction"])]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.1), gridspec_kw={"width_ratios": [2, 3, 2]})
    for ax, (fam, title) in zip(axs, FAMS):
        d = P[P.family == fam]
        keys = list(dict.fromkeys(d[d.part == "mcv"].key.tolist() + d[d.part == "interaction"].key.tolist()))
        x = np.arange(len(keys))
        for j, (m, c, lab) in enumerate([(MAIN, OK[3], "Qwen3-4B"), ("qwen3:8b", OK[0], "Qwen3-8B")]):
            g = d[d.model == m].set_index("key").reindex(keys)
            ax.bar(x + (j - 0.5) * 0.38, g.raw, 0.36, color=c, alpha=0.85, label=lab,
                   yerr=[np.clip(g.raw - g.lo, 0, None), np.clip(g.hi - g.raw, 0, None)], error_kw={"lw": 0.6, "capsize": 1.5})
        ax.axhline(0, color="#444", lw=0.6)
        ax.set_xticks(x, [("I(" + k.replace("|", ", ").replace("_", " ") + ")") if "|" in k else k.replace("_", " ")
                          for k in keys], rotation=20, ha="right", fontsize=6.5)
        ax.set_title(title, fontsize=8)
        ax.set_ylim(-1, 1.05)
    axs[0].set_ylabel("success drop when removed\n(MCV) / interaction")
    axs[0].legend(fontsize=6.5, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "fig3_profiles.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_transfer() -> None:
    T = pd.read_csv(PROC / "transfer.csv")
    conds = [("B2", OK[0], "B2 relevance"), ("OURS-T", OK[7], "MCV, 4B profile (transferred)"),
             ("OURS-native", OK[3], "MCV, 8B profile (native)")]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 1.9), sharey=True)
    for ax, (fam, title) in zip(axs, FAMS):
        d = T[T.family == fam]
        for j, (c, col, lab) in enumerate(conds):
            for k, b in enumerate([2000, 8000]):
                g = d[(d.cond == c) & (d.budget == b)]
                if not len(g):
                    continue
                r = g.iloc[0]
                ax.bar(k + (j - 1) * 0.27, r.success, 0.25, color=col, label=lab if k == 0 else None,
                       yerr=[[r.success - r.lo], [r.hi - r.success]], error_kw={"lw": 0.6, "capsize": 1.5})
        ax.set_xticks([0, 1], ["2k budget", "8k budget"])
        ax.set_title(title, fontsize=8)
        ax.set_ylim(0, 1.05)
    axs[0].set_ylabel("success (Qwen3-8B)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    fig.savefig(FIG / "fig4_transfer.pdf", bbox_inches="tight")
    plt.close(fig)


TYPE_COLOR = {"instructions": "#999999", "goal": "#555555", "tool_schema": OK[0], "fact": OK[2], "example": OK[1],
              "note": OK[4], "history_turn": OK[5], "skill_doc": OK[6]}


def fig_composition() -> None:
    C = pd.read_csv(PROC / "composition.csv")
    pols = ["B0", "B2", "B4", "OURS-A", "OURS"]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 1.9), sharey=False)
    for ax, (fam, title) in zip(axs, FAMS):
        d = C[(C.family == fam) & ((C.budget == 8000) | (C.policy == "B0"))]
        bottom = np.zeros(len(pols))
        for t, col in TYPE_COLOR.items():
            v = np.array([d[(d.policy == p) & (d.type == t)].tokens.sum() for p in pols])
            if v.sum() == 0:
                continue
            ax.barh(range(len(pols)), v, left=bottom, color=col, label=t.replace("_", " "), height=0.7)
            bottom += v
        ax.set_yticks(range(len(pols)), ["B0 full", "B2 rel.", "B4 cov.", "MCV add.", "MCV"] if fam == "facts" else [""] * 5)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("mean prompt tokens (8k budget)")
    hs, ls = {}, {}
    for ax in axs:
        for h, l in zip(*ax.get_legend_handles_labels()):
            hs.setdefault(l, h)
    fig.legend(list(hs.values()), list(hs.keys()), loc="lower center", ncol=8, fontsize=6.5, frameon=False,
               bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    fig.savefig(FIG / "fig5_composition.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_breakeven() -> None:
    C = pd.read_csv(PROC / "cost.csv")
    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    q = np.logspace(1, 5, 200)
    for (fam, title), col in zip(FAMS, [OK[2], OK[5], OK[0]]):
        r = C[C.family == fam].iloc[0]
        ax.plot(q, (q * r.tokens_saved_per_query - r.profiling_prompt_tokens) / 1e6, color=col, label=title)
        if np.isfinite(r.break_even_queries):
            ax.plot([r.break_even_queries], [0], "o", color=col, ms=3)
    ax.axhline(0, color="#444", lw=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("queries served after profiling")
    ax.set_ylabel("net prompt tokens saved (M)")
    ax.legend(fontsize=6.5, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig6_breakeven.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_sample_size() -> None:
    S = pd.read_csv(PROC / "profile_sample_size.csv")
    a = S.groupby("k").agg(mae=("mae", "mean"), lo=("mae", lambda x: np.percentile(x, 10)),
                           hi=("mae", lambda x: np.percentile(x, 90)), top=("top_type_all", "mean")).reset_index()
    fig, ax = plt.subplots(figsize=(3.4, 1.9))
    ax.plot(a.k, a.mae, "o-", color=OK[3], ms=3, label="mean abs. error of type MCVs")
    ax.fill_between(a.k, a.lo, a.hi, color=OK[3], alpha=0.15, lw=0)
    ax.set_xlabel("development instances used for profiling")
    ax.set_ylabel("abs. error vs. full profile", color=OK[3])
    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.plot(a.k, a.top, "s--", color=OK[0], ms=3)
    ax2.set_ylabel("top type correct (all families)", color=OK[0])
    ax2.set_ylim(0, 1.02)
    ax.set_xticks(a.k)
    fig.tight_layout()
    fig.savefig(FIG / "fig7_sample_size.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_frontier() -> None:
    S = pd.read_csv(PROC / "success.csv")
    S = S[S.model == MAIN]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.0), sharey=True)
    for ax, (fam, title) in zip(axs, FAMS):
        d = S[S.family == fam]
        for p in ["B0", "B1", "B3", "B5", "B4", "B2", "OURS"]:
            g = d[d.policy == p].sort_values("budget")
            ax.plot(g.prompt_tokens, g.success, marker="o" if p != "B0" else "*", ms=3 if p != "B0" else 7,
                    lw=1.6 if p == "OURS" else 0.9, color=POLICY_COLOR[p], label=POLICY_NAME[p])
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("mean prompt tokens sent")
        ax.set_ylim(0, 1.03)
    axs[0].set_ylabel("task success")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=7, fontsize=6.3, frameon=False, bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    fig.savefig(FIG / "fig8_frontier.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIG.mkdir(exist_ok=True)
    fig_architecture()
    for f in (fig_curves, fig_profiles, fig_transfer, fig_composition, fig_breakeven, fig_sample_size, fig_frontier):
        try:
            f()
        except Exception as e:  # noqa: BLE001 -- partial data while runs are in flight
            print(f.__name__, "skipped:", e)
    print(sorted(p.name for p in FIG.glob("*.pdf")))


if __name__ == "__main__":
    main()
