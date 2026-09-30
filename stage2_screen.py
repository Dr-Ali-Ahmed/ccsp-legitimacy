"""Stage 2: screen the candidate pool against declaration/inclusion_rule.md.

Reads runs/stage1/candidates.jsonl, screens every candidate with the Batch
API (include / exclude / unsure, each with a reason), writes
runs/stage2/screened.jsonl, and checks that every ground-truth seed came
through as include. Every decision is audit-logged.

  python3 stage2_screen.py --model claude-opus-5            # full run
  python3 stage2_screen.py --model claude-opus-5 --sample 200 --seed 7
"""

import argparse
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
from litsearch.screening import Screener

ROOT = pathlib.Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--model", default="claude-opus-5")
ap.add_argument("--sample", type=int, default=0, help="screen only a random sample of this size")
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--tag", default="")
ap.add_argument("--direct", action="store_true", help="single requests in parallel instead of the batch queue")
args = ap.parse_args()

RUN = ROOT / "runs" / ("stage2" + (f"_{args.tag}" if args.tag else ""))
RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl")

rule = (ROOT / "declaration" / "inclusion_rule.md").read_text()
declaration = {
    "claim": "Build the corpus of papers that do conceptual work on the construct "
             "of legitimacy in organizational research: papers that define, "
             "redefine, dimensionalize, bound, relevel, or review the concept itself, "
             "as opposed to papers that merely use legitimacy as a variable.",
    "criteria": rule,
}
audit.write("declaration", model=args.model, rule_sha=hash(rule) & 0xFFFFFFFF, sample=args.sample)

cands = [json.loads(l) for l in open(ROOT / "runs" / "stage1" / "candidates.jsonl")]
seeds = {c["id"] for c in cands if "seed" in c["sources"] and c.get("seed_role") == "ground_truth"}
if args.sample:
    rng = random.Random(args.seed)
    pool = [c for c in cands if c["id"] not in seeds]
    cands = [c for c in cands if c["id"] in seeds] + rng.sample(pool, args.sample)
print(f"screening {len(cands)} candidates with {args.model} (seeds always included: {len(seeds)})")

screener = Screener(declaration, audit, model=args.model, binary=False)
items = [(c, c.get("abstract")) for c in cands]
if args.direct:
    from concurrent.futures import ThreadPoolExecutor
    def one(item):
        rec, abs_ = item
        try:
            v, _ = screener.screen(rec, abs_)
        except Exception as e:
            v = {"decision": "error", "reason": f"{type(e).__name__}: {str(e)[:120]}"}
        return rec["id"], v
    with ThreadPoolExecutor(max_workers=8) as ex:
        verdicts = dict(ex.map(one, items))
else:
    verdicts = screener.screen_batch(items)

with open(RUN / "screened.jsonl", "w") as f:
    for c in cands:
        v = verdicts.get(c["id"], {"decision": "error", "reason": "no verdict returned"})
        c = dict(c); c["decision"] = v["decision"]; c["reason"] = v["reason"]
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

from collections import Counter
tally = Counter(verdicts[c["id"]]["decision"] for c in cands if c["id"] in verdicts)
missed_seeds = [c["title"] for c in cands if c["id"] in seeds and verdicts.get(c["id"], {}).get("decision") != "include"]
summary = {"screened": len(cands), "model": args.model, "tally": dict(tally),
           "seeds_not_included": missed_seeds}
json.dump(summary, open(RUN / "summary.json", "w"), indent=1)
audit.write("stage2_complete", **summary)
print(json.dumps(summary, indent=1))
if missed_seeds:
    print("\nSTOP: ground-truth seeds were not included. Rule or screener needs attention.")
