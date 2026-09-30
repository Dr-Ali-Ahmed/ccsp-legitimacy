"""Materiality-rule variants, side by side. Primary = pre-registered rule with the
new-level fix. B = dimension families. C = confirmed dimensions. Everything else fixed."""
import json, pathlib, sys, random, copy
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
from ccsp.replay import replay, State
ROOT = pathlib.Path(__file__).parent; RUN = ROOT / "runs" / "stage10"; RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl")
CB = json.load(open(ROOT / "data/corpus/codebook.json"))
CB_FAM = copy.deepcopy(CB); CB_FAM["dimensions"] = {"mapping": CB["dimensions_families"]["mapping"]}
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
seeds = json.load(open(ROOT / "runs/stage1/seeds_resolved.json")); counter_ids = [s["id"] for s in seeds if s["year"] in (2011, 2014, 2015)]
VARIANTS = {"A_primary": dict(codebook=CB), "B_families": dict(codebook=CB_FAM), "C_confirmed": dict(codebook=CB, confirm_dimensions=True),
            "BC_both": dict(codebook=CB_FAM, confirm_dimensions=True)}
results = {}
for name, kw in VARIANTS.items():
    main = replay(dev, **kw); frz = replay(early, **kw)
    st = State(codebook=kw["codebook"], confirm_dimensions=kw.get("confirm_dimensions", False)); [st.absorb(r) for r in early]
    counter = [st.absorb(rec_for(p)) for p in counter_ids if rec_for(p)]
    orders = []
    for seed in range(20):
        rng = random.Random(seed); shuf = early[:]; rng.shuffle(shuf); r = replay(shuf, stop_at_first=True, **kw); orders.append(r["stop"]["after_paper"] if r["stop"] else None)
    ks = {}
    for k in (2, 3, 4, 5):
        r = replay(early, k=k, stop_at_first=True, **kw); ks[k] = r["stop"]["year"] if r["stop"] else None
    results[name] = {"main_stop": main["stop"], "freeze_stop": frz["stop"], "freeze_stop_by_k": ks,
                     "material_per_batch_main": [b["material"] for b in main["batches"]], "quiet_batches_main": [b["batch"] for b in main["batches"] if b["quiet"]],
                     "counter": [{"year": corpus[c["paper_id"]]["year"], "material": c["material"], "category": c["category"]} for c in counter],
                     "orders_stop_after": orders}
    json.dump({"main": main, "freeze": frz}, open(RUN / f"replay_{name}.json", "w"), indent=1)
json.dump(results, open(RUN / "variants_summary.json", "w"), indent=1)
audit.write("stage10_complete", **{k: {"main_stop": v["main_stop"], "freeze_stop": v["freeze_stop"]} for k, v in results.items()})
print(f"dev={len(dev)} early={len(early)}\n")
print(f"{'variant':12s} {'main stop':>22s} {'freeze2010 stop':>22s} {'k=2/3/4/5 stop yr':>22s} {'material/batch (main)':>32s} {'counter 2011/2014':>18s} {'orders stopping':>15s}")
for n, v in results.items():
    ms = f"{v['main_stop']['year']} (b{v['main_stop']['batch']})" if v["main_stop"] else "never"
    fs = f"{v['freeze_stop']['year']} (b{v['freeze_stop']['batch']})" if v["freeze_stop"] else "never"
    ks = "/".join(str(x) if x else "-" for x in v["freeze_stop_by_k"].values())
    print(f"{n:12s} {ms:>22s} {fs:>22s} {ks:>22s} {str(v['material_per_batch_main']):>32s} {str([c['material'] for c in v['counter']]):>18s} {sum(1 for o in v['orders_stop_after'] if o):>15d}/20")
