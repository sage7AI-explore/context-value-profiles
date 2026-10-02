import math

import numpy as np
import pytest

from mcv.compile import policies as P
from mcv.compile.knapsack import BudgetError, compile_plan, greedy
from mcv.eval.metrics import aubc, check_call, check_exact, check_qa, normalize, parse_call, success
from mcv.ir.blocks import BlockType as T
from mcv.ir.blocks import ContextBlock as B
from mcv.ir.blocks import Instance
from mcv.ir.render import render, render_block
from mcv.profile.ablate import conditions, optional_types, render_condition
from mcv.profile.estimate import estimate, lobo_targets
from mcv.profile.features import BlockValueModel, _bm25, block_features, words
from mcv.profile.transfer import fidelity, transfer


class FakeCounter:
    """Word-count tokenizer for offline tests (block_cost includes the rendered header)."""

    def count(self, text: str) -> int:
        return len(text.split())

    def block_cost(self, block, variant="full"):
        return self.count(render_block(block, variant))


def inst(deps=None):
    blocks = [B("instr", T.INSTRUCTIONS, {"full": "Answer briefly."}),
              B("goal", T.GOAL, {"full": "Question: Which river flows through Paris?"}),
              B("f0", T.FACT, {"full": "Paris: the Seine river flows through Paris " * 3, "short": "Paris: the Seine."}),
              B("f1", T.FACT, {"full": "Berlin: the Spree flows through Berlin " * 3}),
              B("ex0", T.EXAMPLE, {"full": "Question: x? ANSWER: y"}, deps=tuple(deps or ())),
              B("n0", T.NOTE, {"full": "note about rivers"}),
              B("h0", T.HISTORY_TURN, {"full": "Session 1: hello"}, meta={"order": 0}),
              B("h1", T.HISTORY_TURN, {"full": "Session 2: river talk Paris"}, meta={"order": 1})]
    return Instance("i1", "facts", blocks, "Seine", "qa")


# ---------------------------------------------------------------- IR
def test_validate_errors():
    x = inst()
    x.validate()
    bad = Instance("d", "f", [B("a", T.GOAL, {"full": "g"}), B("a", T.FACT, {"full": "f"})], "", "qa")
    with pytest.raises(ValueError):
        bad.validate()
    with pytest.raises(ValueError):
        Instance("u", "f", [B("a", T.GOAL, {"full": "g"}, deps=("zz",))], "", "qa").validate()
    cyc = Instance("c", "f", [B("a", T.FACT, {"full": "a"}, deps=("b",)), B("b", T.FACT, {"full": "b"}, deps=("a",))], "", "qa")
    with pytest.raises(ValueError):
        cyc.validate()
    with pytest.raises(ValueError):
        B("x", T.FACT, {"short": "no full"})


def test_roundtrip_and_helpers():
    x = inst()
    y = Instance.from_json(x.to_json())
    assert [b.id for b in y.blocks] == [b.id for b in x.blocks] and y.gold == "Seine"
    assert set(x.mandatory_ids()) == {"instr", "goal"} and "Paris" in x.goal_text()
    assert len(x.of_type(T.FACT)) == 2 and x.by_id()["f0"].type == T.FACT and len(x.blocks[2].digest()) == 16


def test_render_deterministic_and_ordered():
    x = inst()
    a = render(list(reversed(x.blocks)), all_blocks=x.blocks)
    b = render(x.blocks, all_blocks=x.blocks)
    assert a == b
    assert a.index("### Instructions") < a.index("### Document") < a.index("### Conversation") < a.index("### Task")
    assert a.index("Session 1") < a.index("Session 2")
    with pytest.raises(KeyError):
        render_block(x.blocks[0], "short")


# ---------------------------------------------------------------- metrics
def test_checkers():
    assert check_qa("The Seine", "Seine") and check_qa("ANSWER seine river", "Seine")
    assert not check_qa("It is definitely not related to anything Seine at all here ok", "Seine")
    assert not check_qa(None, "x") and not check_qa("x", "")
    assert normalize("The  U.S.A!") == "usa"
    gold = [{"f": {"a": [1], "b": ["x", ""], "c": [[1, 2]]}}]
    assert check_call('{"name": "f", "arguments": {"a": 1.0, "c": [1, 2]}}', gold)
    assert check_call('text {"name":"f","arguments":{"a":"1","b":"X","c":[1,2]}} tail', gold)
    assert not check_call('{"name": "f", "arguments": {"a": 2, "c": [1, 2]}}', gold)
    assert not check_call('{"name": "f", "arguments": {"c": [1, 2]}}', gold)          # missing required a
    assert not check_call('{"name": "f", "arguments": {"a": 1, "c": [1, 2], "z": 1}}', gold)  # unknown param
    assert not check_call('{"name": "g", "arguments": {}}', gold) and not check_call("no json", gold)
    assert parse_call('{"name": "f", "parameters": {"a": 1}}')["arguments"] == {"a": 1} and parse_call("{bad") is None
    assert check_exact(" Seine. ", "seine") and not check_exact(None, "x")
    assert success("qa", "Seine", "Seine")
    assert math.isclose(aubc([1000, 2000, 4000], [0.0, 0.5, 1.0]), 0.5)
    assert aubc([1000], [0.3]) == 0.3


# ---------------------------------------------------------------- compiler
def test_budget_below_mandatory_fails_loudly():
    x = inst()
    with pytest.raises(BudgetError):
        compile_plan(x, FakeCounter(), 3, {})
    with pytest.raises(BudgetError):
        greedy(x, FakeCounter(), 3, {})
    with pytest.raises(BudgetError):
        P.tiers(x, FakeCounter(), 3)


def test_compiler_respects_budget_variants_and_zero_values():
    x, c = inst(), FakeCounter()
    vals = {"f0": {"full": 1.0, "short": 0.8}, "f1": {"full": 0.0}, "h1": {"full": 0.2}}
    plan = compile_plan(x, c, 30, vals)
    assert plan.tokens <= 30 and {"instr", "goal"} <= set(plan.selection)
    assert "f1" not in plan.selection  # zero value never selected
    assert plan.selection.get("f0") == "short"  # full does not fit with the rest; short does
    assert plan.certificate["status"] == "OPTIMAL"
    big = compile_plan(x, c, 10_000, vals)
    assert big.selection["f0"] == "full"
    assert len([1 for b in big.selection if b == "f0"]) == 1


def test_dependencies_enforced():
    x, c = inst(deps=["n0"]), FakeCounter()
    plan = compile_plan(x, c, 10_000, {"ex0": {"full": 1.0}, "n0": {"full": -0.1}})
    assert "ex0" in plan.selection and "n0" in plan.selection
    nodep = compile_plan(x, c, 10_000, {"ex0": {"full": 1.0}, "n0": {"full": -0.1}}, use_deps=False)
    assert "n0" not in nodep.selection
    g = greedy(x, c, 10_000, {"ex0": {"full": 1.0}})
    assert "n0" in g.selection


def test_interactions_change_the_optimum():
    x, c = inst(), FakeCounter()
    vals = {"n0": {"full": 0.3}, "h1": {"full": 0.3}}
    assert {"n0", "h1"} <= set(compile_plan(x, c, 10_000, vals).selection)
    plan = compile_plan(x, c, 10_000, vals, {("note", "history_turn"): -0.5})
    assert not ({"n0", "h1"} <= set(plan.selection))


def test_timeout_fallback(monkeypatch):
    import mcv.compile.knapsack as K

    class Dead:
        def __init__(self):
            self.parameters = type("p", (), {})()

        def Solve(self, m):
            return K.cp_model.UNKNOWN

        def StatusName(self, st):
            return "UNKNOWN"

    monkeypatch.setattr(K.cp_model, "CpSolver", Dead)
    plan = compile_plan(inst(), FakeCounter(), 10_000, {"f0": {"full": 1.0}})
    assert plan.certificate["fallback"] and "f0" in plan.selection


# ---------------------------------------------------------------- policies
class FakeEmbedder:
    def embed(self, texts):
        vocab = sorted({w for t in texts for w in words(t)})
        a = np.array([[t.lower().count(w) for w in vocab] for t in texts], float) + 1e-6
        return a / np.linalg.norm(a, axis=1, keepdims=True)


def test_rule_policies():
    x, c = inst(), FakeCounter()
    ctx = {"embedder": FakeEmbedder()}
    assert P.full(x, c, 0).tokens == sum(c.block_cost(b) for b in x.blocks)
    t = P.truncate(x, c, 30)
    assert "h1" in t.selection and t.tokens <= 30
    tier = P.tiers(x, c, 45)
    assert "f0" in tier.selection
    rel = P.relevance(x, c, 40, ctx)
    assert "f0" in rel.selection and rel.tokens <= 40
    cov = P.coverage(x, c, 40, ctx)
    assert cov.tokens <= 40 and len(cov.selection) >= 3
    assert "Task" in P.prompt_for(x, rel)
    plan = P.Plan({"instr": "full", "goal": "full"}, 10, 0.0, {"prompt_override": "compressed text"})
    assert "### Context" in P.prompt_for(x, plan)


def test_ours_policy_with_profile():
    x, c = inst(), FakeCounter()
    prof = {"mcv": {"fact": {"value": 0.5}, "history_turn": {"value": 0.1}},
            "short": {"fact": {"value": 0.25}}, "interaction": {"note|history_turn": {"value": -0.2}}}
    vm = BlockValueModel()  # unfitted -> falls back to the type-MCV feature
    vals = P.mcv_values(x, c, prof, vm)
    assert vals["f0"]["full"] == 0.5 and math.isclose(vals["f0"]["short"], 0.25)
    plan = P.ours(x, c, 10_000, {"profile": prof, "value_model": vm})
    assert {"f0", "f1"} <= set(plan.selection)
    assert P.interactions(prof) == {("note", "history_turn"): -0.2}


# ---------------------------------------------------------------- profiling
def test_conditions_and_padding():
    x, c = inst(), FakeCounter()
    cond = conditions(x, n_lobo=2, pad=True)
    assert "full" in cond and "-fact" in cond and "short:fact" in cond and "-fact-example" in cond
    assert sum(k.startswith("-b:") for k in cond) == 2 and "pad:-fact" in cond
    assert T.GOAL not in optional_types(x)
    padded = render_condition(x, "pad:-fact", cond["pad:-fact"], c)
    assert "Seine" not in padded and "intentionally" in padded
    assert render_condition(x, "-fact", cond["-fact"]).count("### Document") == 0


def test_estimator_recovers_known_effects():
    recs = []
    for i in range(40):
        iid = f"i{i}"
        recs += [{"iid": iid, "condition": "full", "success": 1}, {"iid": iid, "condition": "-fact", "success": 0},
                 {"iid": iid, "condition": "-note", "success": 1}, {"iid": iid, "condition": "-fact-note", "success": 1},
                 {"iid": iid, "condition": "short:fact", "success": 1}, {"iid": iid, "condition": "-b:f0", "success": 0}]
    prof = estimate(recs)
    assert math.isclose(prof["mcv"]["fact"]["raw"], 1.0) and prof["mcv"]["fact"]["value"] < 1.0  # shrinkage
    assert math.isclose(prof["mcv"]["note"]["raw"], 0.0)
    # fact helps only when the (conflicting) note is present: I = 1 - 0 - 1 + 1 = 1
    assert math.isclose(prof["interaction"]["fact|note"]["raw"], 1.0)
    assert math.isclose(prof["short"]["fact"]["raw"], 1.0)
    assert lobo_targets(recs)[0]["delta"] == 1.0 and prof["base"] == 1.0


def test_features_and_value_model():
    x, c = inst(), FakeCounter()
    f = block_features(x, {"mcv": {"fact": {"value": 0.4}}}, c)
    assert set(f) == {b.id for b in x.blocks} and f["f0"][len(f["f0"]) - 4] > f["f1"][len(f["f1"]) - 4]
    assert _bm25(["seine"], [["seine"], ["spree"]])[0] > 0 and _bm25(["x"], []) == []
    vm = BlockValueModel().fit([f["f0"], f["f1"]] * 3, [1.0, 0.0] * 3)
    assert vm.fitted and vm.predict([f["f0"]])[0] > vm.predict([f["f1"]])[0]


def test_transfer_fidelity():
    a = {"mcv": {k: {"value": v} for k, v in zip("abcd", [0.1, 0.2, 0.3, 0.4])}, "interaction": {}}
    b = {"mcv": {k: {"value": v} for k, v in zip("abcd", [0.2, 0.3, 0.5, 0.9])}, "interaction": {}}
    fid = fidelity(a, b)
    assert math.isclose(fid["mcv"]["rho"], 1.0) and math.isnan(fid["interaction"]["rho"])
    assert transfer(a)["transferred"]


# ---------------------------------------------------------------- mocked I/O: embedder, LLMLingua-2, agent call/cache
class FakeResp:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeHTTP:
    def __init__(self):
        self.calls = 0

    def post(self, url, json, timeout):
        self.calls += 1
        if url.endswith("/api/embed"):
            return FakeResp({"embeddings": [[float(len(t) % 7) + 1, 1.0, float(i)] for i, t in enumerate(json["input"])]})
        return FakeResp({"message": {"content": "thinking...\nANSWER: Seine"}, "prompt_eval_count": 12, "eval_count": 3})


def test_embedder_cache(tmp_path):
    http = FakeHTTP()
    e = P.Embedder(tmp_path / "e.sqlite", http)
    a = e.embed(["alpha", "beta"])
    b = e.embed(["alpha", "beta"])
    assert np.allclose(a, b) and http.calls == 1 and np.allclose(np.linalg.norm(a, axis=1), 1)


def test_llmlingua_policy_mocked(monkeypatch):
    class Comp:
        def compress_prompt(self, text, target_token, force_tokens):
            return {"compressed_prompt": " ".join(text.split()[: max(1, target_token)])}
    monkeypatch.setitem(P._LINGUA, "c", Comp())
    x, c = inst(), FakeCounter()
    plan = P.llmlingua2(x, c, 30, None)
    assert plan.tokens <= 30 and plan.certificate["status"] == "LINGUA" and plan.certificate["prompt_override"]
    noop = P.llmlingua2(x, c, 10_000, None)
    assert noop.certificate["status"] == "LINGUA_NOOP"


def test_agent_call_and_cache(tmp_path):
    from mcv.agent.loop import Cache, call, extract_answer
    http = FakeHTTP()
    cache = Cache(tmp_path / "c.sqlite")
    r1 = call(http, "qwen3:8b", 0, "prompt", cache)
    r2 = call(http, "qwen3:8b", 0, "prompt", cache)
    assert not r1["cached"] and r2["cached"] and http.calls == 1 and r1["key"] == r2["key"]
    assert extract_answer("qa", r1["text"]) == "Seine" and extract_answer("qa", "no tag\nlast line") == "last line"
    assert extract_answer("call", "{}") == "{}" and extract_answer("qa", "") is None
