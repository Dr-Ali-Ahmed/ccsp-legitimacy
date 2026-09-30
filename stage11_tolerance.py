"""Tolerance runs: deck slide 43's tau_v. Quiet batch = material fraction <= tau_v."""
import json, pathlib, sys, random, copy
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
from ccsp.replay import replay, State
ROOT = pathlib.Path(__file__).parent; RUN = ROOT / "runs" / "stage11"; RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl")
CB = json.load(open(ROOT / "data/corpus/codebook.json")); CB_FAM = copy.deepcopy(CB); CB_FAM["dimensions"] = {"mapping": CB["dimensions_families"]["mapping"]}
corpus = {r["id"]: r for r in map(json.loads, open(ROOT / "data/corpus/corpus.jsonl"))}
hold = {json.loads(l)["id"] for l in open(ROOT / "data/corpus/holdout_ids.jsonl")}
ab = {r["paper_id"]: r for r in map(json.loads, open(ROOT / "runs/stage7_abstract/records.jsonl"))}
ft = {r["paper_id"]: r for r in map(json.loads, open(ROOT / "runs/stage7_fulltext/records.jsonl"))}
def rec_for(pid):
    r = ft.get(pid) or ab.get(pid)
    if r: r = dict(r); r["year"] = corpus[pid]["year"]; r["title"] = corpus[pid]["title"]
    return r
dev = sorted([rec_for(p) for p, c in corpus.items() if c["year"] and c["year"] <= 2017 and p not in hold and rec_for(p)], key=lambda r: (r["year"], r["title"] or ""))
early = [r for r in dev if r["year"] <= 2010]
holdout_recs = [rec_for(p) for p in hold if rec_for(p) and corpus[p]["year"] <= 2017]
seeds = json.load(open(ROOT / "runs/stage1/seeds_resolved.json")); counter_ids = [s["id"] for s in seeds if s["year"] in (2011, 2014, 2015)]
VARIANTS = {"A_primary": dict(codebook=CB), "B_families": dict(codebook=CB_FAM), "C_confirmed": dict(codebook=CB, confirm_dimensions=True)}
rows = []
print(f"{'variant':12s} {'tau_v':>5s} {'main stop':>14s} {'freeze2010':>12s} {'orders stop':>11s} {'counter after freeze':>22s} {'holdout after main stop':>24s}")
for name, kw in VARIANTS.items():
    for tau_v in (0.0, 0.1, 0.2, 0.3):
        main = replay(dev, tau_v=tau_v, **kw); frz = replay(early, tau_v=tau_v, **kw)
        st = State(codebook=kw["codebook"], confirm_dimensions=kw.get("confirm_dimensions", False)); [st.absorb(r) for r in early]
        counter = [st.absorb(rec_for(p))["material"] for p in counter_ids if rec_for(p)]
        # holdout injected after the main stop (if any): does the sealed set reopen the construct?
        hold_mat = None
        if main["stop"]:
            st2 = State(codebook=kw["codebook"], confirm_dimensions=kw.get("confirm_dimensions", False))
            for r in dev[:main["stop"]["after_paper"]]: st2.absorb(r)
            hold_mat = sum(st2.absorb(r)["material"] for r in holdout_recs)
        orders = 0
        for seed in range(20):
            rng = random.Random(seed); shuf = early[:]; rng.shuffle(shuf); orders += bool(replay(shuf, tau_v=tau_v, stop_at_first=True, **kw)["stop"])
        row = {"variant": name, "tau_v": tau_v, "main_stop": main["stop"], "freeze_stop": frz["stop"], "orders_stopping": orders,
               "counter_material": counter, "holdout_material_after_stop": hold_mat, "n_holdout": len(holdout_recs)}
        rows.append(row)
        ms = f"{main['stop']['year']} b{main['stop']['batch']}" if main["stop"] else "never"; fs = f"{frz['stop']['year']} b{frz['stop']['batch']}" if frz["stop"] else "never"
        print(f"{name:12s} {tau_v:5.1f} {ms:>14s} {fs:>12s} {orders:>8d}/20 {str(counter):>22s} {str(hold_mat)+'/'+str(len(holdout_recs)) if hold_mat is not None else '-':>24s}")
json.dump(rows, open(RUN / "tolerance_summary.json", "w"), indent=1); audit.write("stage11_complete", rows=len(rows))
