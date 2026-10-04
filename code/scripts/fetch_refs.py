"""Build paper/references.bib ONLY from registry metadata (Crossref / DataCite / arXiv API).

Input:  refs/cite_plan.json   {"bibkey": {"doi": "10.xxxx/...", "arxiv": "2607.12345"}, ...}
        (give "doi" for published versions; give "arxiv" alone and the arXiv DataCite DOI 10.48550/arXiv.<id> is used)
Gate:   refs/abstracts/<bibkey>.txt must exist (the abstract you actually read, fetched from the API) -- no abstract,
        no citation. The file is written by `--fetch-abstracts`, then you must read it before citing.
Output: paper/references.bib, refs/raw/meta_<bibkey>.json, refs/cited.json

Usage:  uv run python scripts/fetch_refs.py --fetch-abstracts   # step 1: pull abstracts for every planned key
        uv run python scripts/fetch_refs.py                     # step 2: write the bib (after reading abstracts)
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "refs"
RAW = REFS / "raw"
ABS = REFS / "abstracts"
UA = {"User-Agent": "agentic-papers-refcheck/0.2 (research reproducibility; mailto:sangaraju1988@gmail.com)"}


def get(url: str, as_json: bool = True):
    req = urllib.request.Request(url, headers=UA)
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
                return json.loads(data) if as_json else data.decode()
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"failed: {url}")


def tex_escape(s: str) -> str:
    s = unicodedata.normalize("NFC", re.sub(r"\s+", " ", s)).strip()
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("$", r"\$")]:
        s = s.replace(a, b)
    # Registry titles sometimes carry TeX math ("$\\tau$-bench", which the escape above turns into "\\$τ\\$") or
    # decorative symbols ("♫ MuSiQue") that pdfLaTeX cannot typeset. Map them to plain TeX.
    s = s.replace(r"\$τ\$", r"$\tau$").replace("τ", r"$\tau$").replace("♫", "").strip()
    return s


def doi_for(entry: dict) -> str:
    if entry.get("doi"):
        return entry["doi"]
    if entry.get("arxiv"):
        return f"10.48550/arXiv.{entry['arxiv']}"
    raise ValueError(f"entry has neither doi nor arxiv: {entry}")


def meta_for(doi: str) -> dict:
    if doi.lower().startswith(("10.48550/", "10.5281/")):  # arXiv + Zenodo DOIs live at DataCite
        d = get(f"https://api.datacite.org/dois/{urllib.parse.quote(doi)}")["data"]["attributes"]
        authors = [(c.get("familyName") or c["name"].split(",")[0], c.get("givenName", "")) for c in d["creators"]]
        abstract = " ".join(x.get("description", "") for x in d.get("descriptions", []) if x.get("descriptionType") == "Abstract")
        return {"source": "datacite", "title": d["titles"][0]["title"], "authors": authors,
                "year": str(d["publicationYear"]), "venue": d.get("publisher") or "arXiv", "abstract": abstract, "raw": d}
    d = get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")["message"]
    authors = [(a.get("family", a.get("name", "")), a.get("given", "")) for a in d.get("author", [])]
    abstract = re.sub(r"<[^>]+>", " ", d.get("abstract", ""))
    return {"source": "crossref", "title": d["title"][0], "authors": authors, "type": d.get("type", ""),
            "year": str(d["issued"]["date-parts"][0][0]), "venue": (d.get("container-title") or [""])[0],
            "abstract": abstract, "raw": d}


def arxiv_abstract(aid: str) -> str:
    xml = get(f"https://export.arxiv.org/api/query?id_list={aid}", as_json=False)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    e = ET.fromstring(xml).find("a:entry", ns)
    return "" if e is None else re.sub(r"\s+", " ", e.findtext("a:summary", "", ns)).strip()


def main() -> int:
    plan = json.loads((REFS / "cite_plan.json").read_text())
    RAW.mkdir(parents=True, exist_ok=True)
    ABS.mkdir(parents=True, exist_ok=True)
    if "--fetch-abstracts" in sys.argv:
        for key, e in plan.items():
            if key.startswith("_"):
                continue
            m = meta_for(doi_for(e))
            text = m["abstract"] or (arxiv_abstract(e["arxiv"]) if e.get("arxiv") else "")
            (RAW / f"meta_{key}.json").write_text(json.dumps(m["raw"], indent=1))
            if text:
                (ABS / f"{key}.txt").write_text(f"TITLE: {m['title']}\nDOI: {doi_for(e)}\n\n{text}\n")
            print(("OK  " if text else "NO-ABSTRACT ") + key)
            time.sleep(0.5)
        print("Now READ every file in refs/abstracts/ before citing. Entries without an abstract cannot be cited.")
        return 0
    entries, index, missing = [], {}, []
    for key, e in plan.items():
        if key.startswith("_"):
            continue
        if not (ABS / f"{key}.txt").exists():
            missing.append(key)
            continue
        doi = doi_for(e)
        m = meta_for(doi)
        auth = " and ".join(f"{tex_escape(f)}, {tex_escape(g)}".rstrip(", ") for f, g in m["authors"]) or "{Anonymous}"
        if m["source"] == "crossref" and "proceedings" in m.get("type", ""):
            head, venue = "inproceedings", f"  booktitle = {{{tex_escape(m['venue'])}}},\n"
        elif m["source"] == "crossref":
            head, venue = "article", f"  journal = {{{tex_escape(m['venue'])}}},\n"
        else:
            aid = e.get("arxiv") or doi.split("arXiv.")[-1]
            head, venue = "misc", f"  howpublished = {{arXiv preprint arXiv:{aid}}},\n"
        entries.append(f"@{head}{{{key},\n  title = {{{{{tex_escape(m['title'])}}}}},\n  author = {{{auth}}},\n"
                       f"  year = {{{m['year']}}},\n{venue}  doi = {{{doi}}},\n}}\n")
        index[key] = {"doi": doi, "source": m["source"], "title": m["title"], "arxiv": e.get("arxiv")}
        time.sleep(0.3)
    if missing:
        print("REFUSING to cite (no abstract on file):", ", ".join(missing))
    (ROOT / "paper" / "references.bib").write_text(
        "% GENERATED by code/scripts/fetch_refs.py from Crossref/DataCite. Do not edit by hand.\n\n" + "\n".join(entries))
    (REFS / "cited.json").write_text(json.dumps(index, indent=1))
    print(len(entries), "bib entries written")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
