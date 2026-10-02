"""Seeded adapters turning three task families into typed-block instances; dev/test split; TEST.lock.

Families
  tool    BFCL v3 simple + multiple (Apache-2.0): pick and fill one function call from a 30-tool catalog.
  facts   HotpotQA distractor validation (CC BY-SA 4.0): 10 native paragraphs + 10 from other questions.
  history synthetic multi-session user histories with attribute updates and a profile note that may be stale.
Gold answers come from the datasets' own labels or from the generator; never from an LLM.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

from mcv.ir.blocks import BlockType as T
from mcv.ir.blocks import ContextBlock as B
from mcv.ir.blocks import Instance

ROOT = Path(__file__).resolve().parents[3]
RAW, OUT = ROOT / "data/raw", ROOT / "data/processed"
SEED = 20261002
N_PER_FAMILY = 300
DEV_FRAC = 0.2
N_TOOLS, N_EXTRA_FACTS = 30, 10

INSTR = {
    "tool": "You are a function-calling assistant. Read the available tools and the user's request, then reply with "
            "exactly one JSON object of the form {\"name\": <tool name>, \"arguments\": {<parameter>: <value>}} "
            "calling the single most appropriate tool. Use parameter names exactly as in the tool definition and omit "
            "optional parameters you do not need. Output only the JSON object.",
    "facts": "Answer the question using the documents. Reply with a short answer phrase only (a name, date, number, "
             "or yes/no), on a final line of the form: ANSWER: <answer>",
    "history": "You are a personal assistant with access to past conversations with the user and possibly a profile "
               "note. Answer the question about the user. If information changed over time, the most recent "
               "statement wins. Reply on a final line of the form: ANSWER: <value>",
}


def first_sentences(text: str, n: int = 1) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n])


# ---------------------------------------------------------------- tool family (BFCL)
def _schema_text(fn: dict) -> str:
    return json.dumps({"name": fn["name"], "description": fn["description"], "parameters": fn["parameters"]},
                      ensure_ascii=False)


def _example_call(gt: dict) -> dict:
    (name, params), = gt.items()
    args = {}
    for p, allowed in params.items():
        vals = [a for a in allowed if a != ""]
        if vals and "" not in allowed:
            args[p] = vals[0]
    return {"name": name, "arguments": args}


def build_tool(rng: random.Random) -> list:
    items, answers = [], {}
    for f in ("BFCL_v3_simple.json", "BFCL_v3_multiple.json"):
        for line in (RAW / "bfcl" / f).read_text().splitlines():
            items.append(json.loads(line))
        for line in (RAW / "bfcl" / "possible_answer" / f).read_text().splitlines():
            a = json.loads(line)
            answers[a["id"]] = a["ground_truth"]
    items = [it for it in items if len(answers[it["id"]]) == 1]  # single expected call
    pool = {fn["name"]: fn for it in items for fn in it["function"]}
    rng.shuffle(items)
    out = []
    for k, it in enumerate(items[:N_PER_FAMILY]):
        own = {fn["name"] for fn in it["function"]}
        distract = rng.sample(sorted(set(pool) - own), N_TOOLS - len(own))
        catalog = list(it["function"]) + [pool[n] for n in distract]
        rng.shuffle(catalog)
        blocks = [B("instr", T.INSTRUCTIONS, {"full": INSTR["tool"]}),
                  B("goal", T.GOAL, {"full": "Request: " + it["question"][0][0]["content"]
                                            + "\nReply with only the JSON call, no explanation."})]
        for i, fn in enumerate(catalog):
            blocks.append(B(f"tool{i:02d}", T.TOOL_SCHEMA, {"full": _schema_text(fn),
                            "short": json.dumps({"name": fn["name"], "description": fn["description"]})},
                            source=fn["name"], meta={"gold": fn["name"] in {list(answers[it['id']][0])[0]}}))
        others = rng.sample([x for x in items if x["id"] != it["id"]], 3)
        for j, ex in enumerate(others):
            call = _example_call(answers[ex["id"]][0])
            blocks.append(B(f"ex{j}", T.EXAMPLE, {"full": f"Request: {ex['question'][0][0]['content']}\n"
                                                          f"Call: {json.dumps(call)}"}))
        out.append(Instance(f"tool-{k:04d}", "tool", blocks, answers[it["id"]], "call", meta={"src": it["id"]}))
    return out


# ---------------------------------------------------------------- facts family (HotpotQA distractor)
def build_facts(rng: random.Random) -> list:
    rows = [json.loads(l) for l in (RAW / "hotpot_distractor_validation.jsonl").read_text().splitlines()]
    rng.shuffle(rows)
    sel, rest = rows[:N_PER_FAMILY], rows[N_PER_FAMILY:]
    out = []
    for k, r in enumerate(sel):
        sup = set(r["supporting_facts"]["title"])
        paras = [(t, "".join(s), t in sup) for t, s in zip(r["context"]["title"], r["context"]["sentences"])]
        for o in rng.sample(rest, N_EXTRA_FACTS):
            t, s = o["context"]["title"][0], o["context"]["sentences"][0]
            paras.append((t, "".join(s), False))
        rng.shuffle(paras)
        blocks = [B("instr", T.INSTRUCTIONS, {"full": INSTR["facts"]}), B("goal", T.GOAL, {"full": "Question: " + r["question"]
                                                 + "\nReply with only one line: ANSWER: <short answer>. No explanation."})]
        for i, (t, txt, g) in enumerate(paras):
            full = f"{t}: {txt.strip()}"
            blocks.append(B(f"fact{i:02d}", T.FACT, {"full": full, "short": f"{t}: {first_sentences(txt, 1)}"},
                            source=t, meta={"gold": g}))
        for j, ex in enumerate(rng.sample(rest, 2)):
            blocks.append(B(f"ex{j}", T.EXAMPLE, {"full": f"Question: {ex['question']}\nANSWER: {ex['answer']}"}))
        out.append(Instance(f"facts-{k:04d}", "facts", blocks, r["answer"], "qa", meta={"src": r["id"], "type": r["type"]}))
    return out


# ---------------------------------------------------------------- history family (synthetic)
ATTRS = {
    "home city": ["Denver", "Austin", "Portland", "Raleigh", "Madison", "Tucson", "Boise", "Omaha", "Richmond", "Spokane"],
    "employer": ["Northwind Labs", "Bluefin Analytics", "Cedar Health", "Orbit Logistics", "Pine Street Bank",
                 "Kestrel Robotics", "Harbor Foods", "Summit Energy"],
    "dog's name": ["Biscuit", "Juniper", "Waffles", "Mochi", "Rocket", "Pepper", "Clover", "Ziggy"],
    "favorite cuisine": ["Ethiopian", "Peruvian", "Korean", "Lebanese", "Oaxacan", "Sichuan", "Basque", "Georgian"],
    "car": ["a blue Subaru Outback", "a gray Honda Civic", "a red Mazda CX-5", "a white Tesla Model 3",
            "a green Toyota Tacoma", "a black Ford Bronco"],
    "dentist": ["Dr. Alvarez", "Dr. Okafor", "Dr. Lindqvist", "Dr. Patel", "Dr. Moreau", "Dr. Nakamura"],
}
STATE = {"home city": "I live in {v}", "employer": "I work at {v}", "dog's name": "my dog is called {v}",
         "favorite cuisine": "my favorite food is {v}", "car": "I drive {v}", "dentist": "my dentist is {v}"}
CHAT = ["We talked about a weekend hiking plan and packing lists.", "The user asked for a pasta recipe and we adjusted it for six people.",
        "We brainstormed gift ideas for a coworker's farewell.", "The user wanted tips on fixing a squeaky door hinge.",
        "We compared two budgeting apps and their fees.", "The user asked about stretching routines after running.",
        "We drafted an email to a landlord about a leaking faucet.", "The user asked which houseplants tolerate low light.",
        "We planned a three-day itinerary for a museum trip.", "The user practiced Spanish phrases for ordering coffee.",
        "We reviewed a cover letter for a volunteer position.", "The user asked how to back up photos from a phone.",
        "We discussed whether to repaint the kitchen in a warmer shade and how many gallons it would take.",
        "The user wanted a beginner-friendly sourdough schedule that fits around a nine-to-five job.",
        "We went over the rules of a board game the user's family plays on holidays.",
        "The user asked for a summary of the differences between index funds and target-date funds.",
        "We wrote a short speech for a friend's birthday dinner with a couple of light jokes.",
        "The user wanted advice on keeping tomato plants healthy during a hot, dry week.",
        "We compared three podcast apps and how they handle offline downloads.",
        "The user asked how to politely decline an invitation to a neighborhood committee.",
        "We outlined a study plan for a certification exam over the next eight weeks.",
        "The user asked for ideas to keep a toddler busy on a long train ride.",
        "We discussed how to organize a cluttered garage with shelving and labeled bins.",
        "The user wanted a quick explanation of how heat pumps work in cold climates."]


def build_history(rng: random.Random) -> list:
    out = []
    for k in range(N_PER_FAMILY):
        n_sess = 24
        attrs = rng.sample(sorted(ATTRS), 4)
        target = attrs[0]
        values = {a: rng.sample(ATTRS[a], 3) for a in attrs}
        events = []  # (session, attr, value)
        for a in attrs:
            s0 = rng.randint(0, 8)
            events.append((s0, a, values[a][0]))
            if a == target or rng.random() < 0.5:
                events.append((rng.randint(s0 + 3, n_sess - 1), a, values[a][1]))
        sessions = []
        for s in range(n_sess):
            lines = rng.sample(CHAT, rng.randint(6, 8))
            for (es, a, v) in events:
                if es == s:
                    lines.insert(rng.randint(0, len(lines)), f'User: "By the way, {STATE[a].format(v=v)} now."' if any(
                        e2[0] < s and e2[1] == a for e2 in events) else f'User: "{STATE[a].format(v=v)}."')
            sessions.append(" ".join(lines))
        latest = max((e for e in events if e[1] == target), key=lambda e: e[0])
        first = min((e for e in events if e[1] == target), key=lambda e: e[0])
        stale = rng.random() < 0.5
        note_session = rng.randint(first[0], latest[0] - 1) if stale else rng.randint(latest[0], n_sess - 1)
        note_vals = {a: max((e for e in events if e[1] == a and e[0] <= note_session), key=lambda e: e[0],
                            default=(0, a, "unknown"))[2] for a in attrs}
        q = (f"Question: What is the user's current {target}?\n"
             "Reply with only one line: ANSWER: <value>. No explanation.")
        blocks = [B("instr", T.INSTRUCTIONS, {"full": INSTR["history"]}), B("goal", T.GOAL, {"full": q})]
        for s, txt in enumerate(sessions):
            blocks.append(B(f"turn{s:02d}", T.HISTORY_TURN, {"full": f"Session {s + 1}: {txt}",
                            "short": f"Session {s + 1}: {first_sentences(txt, 1)}"},
                            meta={"order": s, "gold": s == latest[0]}))
        note = "Profile note (written after session %d): " % (note_session + 1) + "; ".join(
            f"{a}: {v}" for a, v in note_vals.items()) + "."
        blocks.append(B("note", T.NOTE, {"full": note}, meta={"stale": stale}))
        blocks.append(B("ex0", T.EXAMPLE, {"full": "Session 2: User: \"I live in Fresno.\" ... Session 9: User: "
                                                    "\"By the way, I live in Reno now.\"\nQuestion: What is the user's "
                                                    "current home city?\nANSWER: Reno"}))
        out.append(Instance(f"history-{k:04d}", "history", blocks, latest[2], "qa",
                            meta={"stale_note": stale, "n_updates": sum(e[1] == target for e in events) - 1}))
    return out


def split(instances: list, rng: random.Random) -> None:
    idx = list(range(len(instances)))
    rng.shuffle(idx)
    n_dev = round(len(idx) * DEV_FRAC)
    for j, i in enumerate(idx):
        instances[i].split = "dev" if j < n_dev else "test"


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    info = {}
    allinst = []
    for fam, fn in (("tool", build_tool), ("facts", build_facts), ("history", build_history)):
        rng = random.Random(f"{SEED}-{fam}")
        inst = fn(rng)
        for x in inst:
            x.validate()
        split(inst, random.Random(f"{SEED}-{fam}-split"))
        allinst += inst
        info[fam] = {"n": len(inst), "dev": sum(x.split == "dev" for x in inst)}
    path = OUT / "instances.jsonl"
    path.write_text("".join(json.dumps(x.to_json(), sort_keys=True) + "\n" for x in allinst))
    test_ids = sorted(x.iid for x in allinst if x.split == "test")
    lock = {"instances_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "test_ids_sha256": hashlib.sha256("\n".join(test_ids).encode()).hexdigest(), "families": info}
    (OUT / "TEST.lock").write_text(json.dumps(lock, indent=1) + "\n")
    return lock


def load(split_name: str | None = None, family: str | None = None) -> list:
    out = []
    for line in (OUT / "instances.jsonl").read_text().splitlines():
        x = Instance.from_json(json.loads(line))
        if (split_name is None or x.split == split_name) and (family is None or x.family == family):
            out.append(x)
    return out


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
