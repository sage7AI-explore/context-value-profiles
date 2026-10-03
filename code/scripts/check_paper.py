"""Paper gate (run after the PDF builds). Fails on:
  1. hand-typed result numbers in paper/sections/*.tex  (numbers must come from \\macros in generated/numbers.tex
     or generated/*.tex tables). Allowed literals: listed in paper/allowed_literals.txt (one regex per line),
     e.g. section/figure counts, years in prose, model sizes like 8B, budget levels defined by the design.
  2. page count outside the target range (default 11-12 pages, incl. references and bio).
  3. undefined references/citations or overfull boxes > 5pt in paper/main.log.
  4. any \\num-like macro used in the text that is not defined in generated/numbers.tex.
Usage: uv run python scripts/check_paper.py [--min 11 --max 12]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "paper"


def strip_tex(s: str) -> str:
    s = re.sub(r"(?<!\\)%.*", "", s)                         # comments
    s = re.sub(r"\\(cite[a-z]*|ref|label|eqref|autoref|input|include|url|href|includegraphics|cmidrule\(lr\))(\[[^\]]*\])?\{[^}]*\}", "", s)
    s = re.sub(r"\\begin\{(equation|align)\*?\}.*?\\end\{\1\*?\}", "", s, flags=re.S)
    return s


def page_count(pdf: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except ImportError:
        return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=11)
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()
    problems = []
    allowed = [re.compile(x.strip()) for x in (P / "allowed_literals.txt").read_text().splitlines()
               if x.strip() and not x.startswith("#")] if (P / "allowed_literals.txt").exists() else []
    numtex = (P / "generated" / "numbers.tex").read_text() if (P / "generated" / "numbers.tex").exists() else ""
    defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", numtex))
    for f in sorted((P / "sections").glob("*.tex")):
        text = strip_tex(f.read_text())
        for m in re.finditer(r"(?<![A-Za-z\\{])\d+(?:\.\d+)?\s*(?:\\?%|x|×|ms|s\b|tokens|pp)?", text):
            tok = m.group(0).strip()
            if any(r.fullmatch(tok) or r.fullmatch(tok.split()[0]) for r in allowed):
                continue
            line = text[: m.start()].count("\n") + 1
            problems.append(f"literal number '{tok}' in {f.name}:{line} -- move it to generated/numbers.tex or allow it")
        for mac in re.findall(r"\\(R[A-Z][A-Za-z]+)", text):   # convention: result macros start with \R
            if mac not in defined:
                problems.append(f"undefined result macro \\{mac} in {f.name}")
    pdf = P / "main.pdf"
    if not pdf.exists():
        problems.append("paper/main.pdf missing")
    else:
        n = page_count(pdf)
        if not a.min <= n <= a.max:
            problems.append(f"page count {n} outside {a.min}-{a.max} (add depth from real results, never filler)")
    log = (P / "main.log").read_text(errors="ignore") if (P / "main.log").exists() else ""
    for pat in [r"undefined references", r"Citation `[^']+' .*undefined", r"Reference `[^']+' .*undefined"]:
        if re.search(pat, log):
            problems.append(f"LaTeX log: {pat}")
    for m in re.finditer(r"Overfull \\hbox \((\d+\.\d+)pt", log):
        if float(m.group(1)) > 5:
            problems.append(f"overfull hbox {m.group(1)}pt")
    (ROOT / "results" / "PAPER_CHECK.md").write_text("# Paper check\n\n" + ("\n".join(f"- {p}" for p in problems) or "PASS") + "\n")
    print("PASS" if not problems else f"FAIL ({len(problems)} problems; see results/PAPER_CHECK.md)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
