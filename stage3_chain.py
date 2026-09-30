"""Stage 3: second chaining round from the includes of stage 2.

Backward (what they cite) and forward (what cites them, prefiltered for a
concept signal) from every included paper, minus everything already in the
pool. Output: runs/stage3/new_candidates.jsonl, ready for screening.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
from litsearch.openalex import OpenAlex
from stage1_retrieve import slim, concept_signal   # reuse the same record shape and prefilter

ROOT = pathlib.Path(__file__).parent
RUN = ROOT / "runs" / "stage3"; RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl"); oa = OpenAlex(audit)

seen = {json.loads(l)["id"] for l in open(ROOT / "runs" / "stage2_final_decisions.jsonl")}
seen |= {json.loads(l)["id"] for l in open(ROOT / "runs" / "stage1" / "forward_prefiltered_out.jsonl")}
includes = [json.loads(l) for l in open(ROOT / "runs" / "stage2_final_decisions.jsonl")]
includes = [r for r in includes if r["decision"] == "include"]
# merge duplicate OpenAlex records of one paper by DOI
by_doi = {}
for r in includes:
    by_doi.setdefault(r["doi"] or r["id"], r)
includes = list(by_doi.values())
audit.write("stage3_start", includes=len(includes), already_seen=len(seen))
print(f"chaining from {len(includes)} unique includes; {len(seen)} ids already seen")

new = {}
def add(rec, src):
    if rec["id"] in seen: return
    if rec["id"] in new: new[rec["id"]]["sources"].append(src); return
    rec = dict(rec); rec["sources"] = [src]; new[rec["id"]] = rec

# backward
back = set()
for r in includes:
    w = oa.get_work(r["id"]); back.update(w.get("referenced_works", []))
back -= seen
print(f"backward: {len(back)} unseen referenced works")
for w in oa.get_works_batch(sorted(back)):
    add(slim(w), "backward2")

# forward, prefiltered, capped per paper with truncation logged
out = []
for r in includes:
    citers = oa.get_citers({"id": r["id"]}, max_records=5000)
    kept = 0
    for w in citers:
        rec = slim(w)
        if rec["id"] in seen or rec["id"] in new: continue
        if concept_signal(rec): add(rec, f"forward2:{r['year']}"); kept += 1
        else: out.append({"id": rec["id"], "title": rec["title"], "year": rec["year"], "cites": r["id"]})
    if kept: print(f"forward2 {r['year']} {(r['title'] or '')[:45]:45s} citers={len(citers):5d} kept={kept}")

for rec in new.values(): rec.pop("referenced_works", None)
with open(RUN / "new_candidates.jsonl", "w") as f:
    for rec in new.values(): f.write(json.dumps(rec, ensure_ascii=False) + "\n")
with open(RUN / "forward_prefiltered_out.jsonl", "w") as f:
    for rec in out: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
summary = {"unique_includes": len(includes), "new_candidates": len(new),
           "with_abstract": sum(1 for r in new.values() if r["abstract"]), "prefiltered_out": len(out)}
json.dump(summary, open(RUN / "summary.json", "w"), indent=1)
audit.write("stage3_complete", **summary); print(json.dumps(summary, indent=1))
