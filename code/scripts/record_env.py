"""Write results/ENVIRONMENT.md: machine, tool versions, Python package versions, Ollama model tags + digests.
Models are read from experiments/models.json (["qwen3:8b", ...]). Run once at the start and again before the
final runs; commit both versions."""
import importlib.metadata as md
import json
import platform
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sh(c: str) -> str:
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()


def main() -> None:
    models = json.loads((ROOT / "experiments" / "models.json").read_text())
    try:
        tags = json.load(urllib.request.urlopen("http://localhost:11434/api/tags", timeout=10))["models"]
    except Exception:  # noqa: BLE001
        tags = []
    L = ["# Environment", "", "## Machine", "",
         f"- macOS: {sh('sw_vers -productVersion')} ({sh('sw_vers -buildVersion')})",
         f"- CPU: {sh('sysctl -n machdep.cpu.brand_string')}, arch {platform.machine()}",
         f"- RAM: {int(sh('sysctl -n hw.memsize') or 0) / 2**30:.0f} GiB",
         f"- Free disk (home): {(sh('df -h ~ | tail -1').split() + ['?'] * 4)[3]}", "", "## Tools", "",
         f"- Python: {platform.python_version()} ({sh('uv --version')})", f"- Ollama: {sh('ollama --version')}",
         f"- LaTeX: {sh('pdflatex --version | head -1') or sh('tectonic --version')}",
         f"- Docker: {sh('docker --version') or 'not installed'}", "", "## Python packages", ""]
    for d in sorted(md.distributions(), key=lambda d: d.metadata["Name"].lower()):
        L.append(f"- {d.metadata['Name']}=={d.version}")
    L += ["", "## Models (Ollama)", "", "| tag | family | params | quant | digest |", "|---|---|---|---|---|"]
    for m in models:
        t = next((x for x in tags if x["name"] == m), None)
        if t is None:
            L.append(f"| {m} | NOT INSTALLED | | | |")
            continue
        d = t["details"]
        L.append(f"| {m} | {d.get('family')} | {d.get('parameter_size')} | {d.get('quantization_level')} | sha256:{t['digest']} |")
    L += ["", "Decoding: temperature 0 and a fixed `seed` per run. Ollama/llama.cpp on Metal is not guaranteed to be",
          "bit-deterministic even with a fixed seed; variance across seeds is reported, never hidden."]
    (ROOT / "results" / "ENVIRONMENT.md").write_text("\n".join(L) + "\n")
    print("wrote results/ENVIRONMENT.md")


if __name__ == "__main__":
    main()
