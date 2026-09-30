"""Run the chronological replay, the 2010 freeze test, the counter batch, and the sensitivity sweep."""
import json, pathlib, sys, random
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
from ccsp.replay import replay, State, BATCH, K, TAU_SYN, TAU_AC, TAU_NC
ROOT = pathlib.Path(__file__).parent; import os
CB = json.load(open(ROOT / "data/corpus/codebook.json")) if os.environ.get("CCSP_CODEBOOK", "1") == "1" else None
RUN = ROOT / "runs" / ("stage8_codebook" if CB else "stage8"); RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl")

corpus = {r["id"]: r for r in map(json.loads, open(ROOT / "data/corpus/corpus.jsonl"))}
hold = {json.loads(l)["id"] for l in open(ROOT / "data/corpus/holdout_ids.jsonl")}
ab = {r["paper_id"]: r for r in map(json.loads, open(ROOT / "runs/stage7_abstract/records.jsonl"))}
ft = {r["paper_id"]: r for r in map(json.loads, open(ROOT / "runs/stage7_fulltext/records.jsonl"))}
def rec_for(pid):
    r = ft.get(pid) or ab.get(pid)
    if r: r = dict(r); r["year"] = corpus[pid]["year"]; r["title"] = corpus[pid]["title"]
    return r
# development set: <=2017 window, not holdout, has a record
dev = [rec_for(pid) for pid, c in corpus.items() if c["year"] and c["year"] <= 2017 and pid not in hold and rec_for(pid)]
dev.sort(key=lambda r: (r["year"], r["title"] or ""))
audit.write("replay_input", n=len(dev), fulltext=sum(1 for r in dev if r["source"] == "fulltext"), abstract=sum(1 for r in dev if r["source"] == "abstract"))
print(f"development set: {len(dev)} records ({sum(1 for r in dev if r['source']=='fulltext')} full text, {sum(1 for r in dev if r['source']=='abstract')} abstract)")

# 1. chronological replay on the full window
main = replay(dev, codebook=CB); json.dump(main, open(RUN / "replay_main.json", "w"), indent=1)
print("\nMAIN REPLAY stop:", main["stop"])
for b in main["batches"]:
    print(f"  batch {b['batch']:2d} {b['years'][0]}-{b['years'][1]} AC={b['AC']:.2f} NC={b['NC']:.2f} SN={b['SN_mean']:.2f} material={b['material']} quiet={b['quiet']} streak={b['streak']} attrs={b['state_size']['essential_attributes']}")

# 2. freeze at 2010
early = [r for r in dev if r["year"] <= 2010]
frz = replay(early, codebook=CB); json.dump(frz, open(RUN / "replay_freeze2010.json", "w"), indent=1)
print(f"\nFREEZE 2010: {len(early)} records; stop:", frz["stop"])

# 3. counter batch: the 2011 to 2015 anchors on top of the frozen state
seeds = json.load(open(ROOT / "runs/stage1/seeds_resolved.json"))
counter_ids = [s["id"] for s in seeds if s["year"] in (2011, 2014, 2015)]
st = State(codebook=CB); [st.absorb(r) for r in early]
counter = [st.absorb(rec_for(pid)) for pid in counter_ids if rec_for(pid)]
json.dump(counter, open(RUN / "counter_batch.json", "w"), indent=1)
print("COUNTER BATCH on frozen 2010 state:")
for c in counter: print(f"  {corpus[c['paper_id']]['year']} {corpus[c['paper_id']]['title'][:55]:55s} material={c['material']} cat={c['category']} changes={ {k: len(v) for k, v in c['changes'].items()} } level_changed={c['level_changed']}")

# 4. sensitivity sweep
sweep = []
for batch in (5, 10, 15):
    for k in (2, 3, 4, 5):
        for tau_syn in (0.45, 0.55, 0.65):
            for tau_ac in (0.05, 0.10, 0.20):
                for nom in (False, True):
                    r = replay(early, batch=batch, k=k, tau_syn=tau_syn, tau_ac=tau_ac, material_nomological=nom, stop_at_first=True, codebook=CB)
                    sweep.append({"batch": batch, "k": k, "tau_syn": tau_syn, "tau_ac": tau_ac, "nomological_material": nom,
                                  "stops_before_2011": r["stop"] is not None, "stop_year": r["stop"]["year"] if r["stop"] else None})
json.dump(sweep, open(RUN / "sweep_freeze2010.json", "w"), indent=1)
n_stop = sum(s["stops_before_2011"] for s in sweep)
print(f"\nSWEEP on the 2010 freeze: {n_stop} of {len(sweep)} settings stop before 2011")
# 5. order sensitivity at pre-registered settings
orders = []
for seed in range(20):
    rng = random.Random(seed); shuf = early[:]; rng.shuffle(shuf)
    r = replay(shuf, stop_at_first=True, codebook=CB); orders.append(r["stop"]["after_paper"] if r["stop"] else None)
print("ORDER SENSITIVITY (20 random orders, papers read before stop):", orders)
audit.write("stage8_complete", main_stop=main["stop"], freeze_stop=frz["stop"], sweep_stops=n_stop, sweep_n=len(sweep), order_stops=orders)
