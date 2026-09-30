"""Run extraction. --tier abstract: every corpus paper from its abstract.
--tier fulltext: papers with a PDF in hand, from full text (for the comparison)."""
import argparse, json, pathlib, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
from ccsp.extract import Extractor
from ccsp.pdf_text import pdf_to_text
ROOT = pathlib.Path(__file__).parent
ap = argparse.ArgumentParser(); ap.add_argument("--tier", choices=["abstract", "fulltext"], required=True)
ap.add_argument("--window", default="all"); ap.add_argument("--limit", type=int, default=0); args = ap.parse_args()
RUN = ROOT / "runs" / f"stage7_{args.tier}"; RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl"); ex = Extractor(audit)
corpus = [json.loads(l) for l in open(ROOT / "data/corpus/corpus.jsonl")]
if args.window == "2017": corpus = [r for r in corpus if r["year"] and r["year"] <= 2017]
if args.tier == "abstract":
    items = [(r["id"], f"TITLE: {r['title']}\nYEAR: {r['year']}\nABSTRACT: {r['abstract']}", "abstract") for r in corpus if r["abstract"]]
else:
    have = json.load(open(ROOT / "data/corpus/zotero_readback.json"))["have"]
    items = []
    for r in corpus:
        d = (r.get("doi") or "").replace("https://doi.org/", "").lower()
        if d in have:
            t = pdf_to_text(have[d])
            if t["status"] == "ok": items.append((r["id"], f"TITLE: {r['title']}\nYEAR: {r['year']}\n\n{t['text']}", "fulltext"))
            else: audit.write("no_text_layer", paper_id=r["id"], path=have[d])
if args.limit: items = items[:args.limit]
done = {json.loads(l)["paper_id"] for l in open(RUN / "records.jsonl")} if (RUN / "records.jsonl").exists() else set()
items = [i for i in items if i[0] not in done]
print(f"{args.tier}: {len(items)} to extract ({len(done)} already done)")
def one(it):
    try: return ex.extract(*it)
    except Exception as e: audit.write("extraction_error", paper_id=it[0], error=f"{type(e).__name__}: {str(e)[:200]}"); return None
with ThreadPoolExecutor(max_workers=6) as pool, open(RUN / "records.jsonl", "a") as f:
    for rec in pool.map(one, items):
        if rec: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
recs = [json.loads(l) for l in open(RUN / "records.jsonl")]
cost = sum(r["usage"]["in"]*5 + r["usage"]["cache_read"]*0.5 + r["usage"]["out"]*25 for r in recs) / 1e6
print(json.dumps({"records": len(recs), "text_sufficient": sum(1 for r in recs if r["record"]["text_sufficient"]),
                  "with_definition": sum(1 for r in recs if r["record"]["definition"]["value"]),
                  "unverified_quotes_total": sum(len(r["unverified_quotes"]) for r in recs), "cost_usd": round(cost, 2)}, indent=1))
