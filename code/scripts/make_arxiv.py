"""Build a self-contained arXiv source package: dist/arxiv/ (flattened paths, figures, generated macros, .bbl) and
dist/context-that-pays-arxiv.tar.gz; compiles the package in a scratch copy to prove it builds; writes the plain-text
abstract (macros expanded) to dist/abstract.txt for the submission form."""
from __future__ import annotations

import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P, D = ROOT / "paper", ROOT / "dist"
OUT = D / "arxiv"


def macros() -> dict:
    out = {}
    for line in (P / "generated/numbers.tex").read_text().splitlines():
        m = re.match(r"\\newcommand\{\\(R[A-Za-z]+)\}\{(.*)\\xspace\}", line.split("  %")[0])
        if m:
            out[m.group(1)] = m.group(2)
    return out


def plain_abstract() -> str:
    s = (P / "sections/abstract.tex").read_text()
    s = "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("%"))
    M = macros()
    s = re.sub(r"\\(R[A-Za-z]+)(\{\})?", lambda m: M[m.group(1)], s)
    s = s.replace("{,}", ",").replace("\\%", "%").replace("--", "-").replace("$\\rho=", "rho = ").replace("$", "")
    return " ".join(s.split())


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "figures").mkdir(parents=True)
    for f in ("main.tex", "IEEEtran.cls", "accessstyle.sty", "main.bbl"):
        shutil.copy(P / f, OUT / f)
    shutil.copytree(P / "sections", OUT / "sections")
    shutil.copytree(P / "generated", OUT / "generated")
    used = set()
    for tex in (OUT / "sections").glob("*.tex"):
        s = tex.read_text()
        used |= set(re.findall(r"\.\./figures/([\w.-]+\.pdf)", s))
        tex.write_text(s.replace("../figures/", "figures/"))
    for f in used:
        shutil.copy(ROOT / "figures" / f, OUT / "figures" / f)
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "pkg"
        shutil.copytree(OUT, t)
        for _ in range(3):
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=t, capture_output=True)
        log = (t / "main.log").read_text(errors="ignore")
        assert (t / "main.pdf").exists(), "package does not compile"
        assert "There were undefined references" not in log and "Citation" not in log, "undefined references"
        shutil.copy(t / "main.pdf", D / "context-that-pays.pdf")
    tar = D / "context-that-pays-arxiv.tar.gz"
    with tarfile.open(tar, "w:gz") as tf:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                tf.add(f, arcname=str(f.relative_to(OUT)))
    ab = plain_abstract()
    (D / "abstract.txt").write_text(ab + "\n")
    print(f"package: {tar} ({tar.stat().st_size // 1024} KB), figures: {sorted(used)}, abstract: {len(ab)} chars")


if __name__ == "__main__":
    main()
