"""Phase 1: fetch literature metadata from the arXiv API. Raw Atom XML saved to refs/raw/."""
import json, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "refs" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
API = "http://export.arxiv.org/api/query?"

ANCHORS = ["2606.20047","2609.00749","2609.37743","2510.04618","2607.25408","2609.34649","2310.03714","2605.26165","2411.15102","2507.13334","2607.22683","2609.13149","2608.21690","2406.12045","2409.00729","2403.12968","2307.03172","1809.09600","2108.00573","2410.10813"]
SEARCHES = {
    "context_selection_budget": 'all:context AND all:selection AND all:budget AND (all:LLM OR all:agent)',
    "prompt_compression_agents": 'all:"prompt compression" AND (all:agent OR all:tool)',
    "context_engineering": 'all:"context engineering"',
    "marginal_value_context": 'all:marginal AND all:value AND all:context AND all:LLM',
    "loo_context_attribution": 'all:"leave-one-out" AND all:context AND all:attribution',
    "knapsack_prompt": 'all:knapsack AND (all:prompt OR all:context) AND all:LLM',
    "token_budget_allocation": 'all:"token budget" AND all:allocation AND all:LLM',
    "context_rot": 'all:"context rot" OR all:"long context degradation"',
    "tool_schema_selection": 'all:tool AND all:schema AND (all:selection OR all:retrieval) AND all:LLM',
    "retrieval_budget": 'all:retrieval AND all:budget AND all:"retrieval-augmented"',
    "context_ablation_value": 'all:context AND all:ablation AND all:value AND all:agent',
    "shapley_context": 'all:Shapley AND (all:context OR all:prompt OR all:retrieval) AND all:LLM',
    "data_valuation_rag": 'all:"data valuation" AND (all:retrieval OR all:RAG OR all:context)',
}

def get(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode()
        except Exception as e:  # noqa: BLE001
            print("retry", attempt, e); time.sleep(5 * (attempt + 1))
    raise RuntimeError(url)

def parse(xml):
    out = []
    for e in ET.fromstring(xml).findall("a:entry", NS):
        idurl = e.findtext("a:id", default="", namespaces=NS)
        if "api/errors" in idurl:
            continue
        out.append({
            "arxiv_id": idurl.rsplit("/abs/", 1)[-1],
            "title": " ".join(e.findtext("a:title", "", NS).split()),
            "authors": [a.findtext("a:name", "", NS) for a in e.findall("a:author", NS)],
            "published": e.findtext("a:published", "", NS),
            "abstract": " ".join(e.findtext("a:summary", "", NS).split()),
            "doi": e.findtext("arxiv:doi", None, NS),
        })
    return out

def main():
    papers = {}
    xml = get(API + urllib.parse.urlencode({"id_list": ",".join(ANCHORS), "max_results": 50}))
    (RAW / "arxiv_anchors.xml").write_text(xml)
    for p in parse(xml):
        p["source"] = "anchor"; papers[p["arxiv_id"].split("v")[0]] = p
    for name, q in SEARCHES.items():
        time.sleep(3.5)
        xml = get(API + urllib.parse.urlencode({"search_query": q, "max_results": 15, "sortBy": "relevance"}))
        (RAW / f"arxiv_search_{name}.xml").write_text(xml)
        for p in parse(xml):
            k = p["arxiv_id"].rsplit("v", 1)[0]
            if k not in papers:
                p["source"] = f"search:{name}"; papers[k] = p
    (ROOT / "refs" / "candidates.json").write_text(json.dumps(papers, indent=1))
    print(len(papers), "candidates")
    missing = [a for a in ANCHORS if a not in papers]
    print("missing anchors:", missing)

if __name__ == "__main__":
    main()
