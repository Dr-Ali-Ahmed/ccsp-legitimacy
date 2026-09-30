"""Stage 5: freeze the corpus.

Dedupe includes by DOI and by normalized title. Apply the lean rule to the
remaining 'unsure' papers: full-text screen only if linked to >=2 included
papers, else exclude with a logged reason. Split at 2017 (extraction window
first). Seal a random 15% holdout from the <=2017 set. Hash everything.
Write the DOI list for Zotero.
"""
import csv, hashlib, json, pathlib, random, re, sys
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "data" / "corpus"; OUT.mkdir(parents=True, exist_ok=True)
audit = AuditLog(ROOT / "runs" / "stage5_freeze_audit_log.jsonl")

rows = [json.loads(l) for l in open(ROOT / "runs" / "all_decisions.jsonl")]
def norm(t): return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()[:70]

# ---- includes, deduped ----
inc = sorted([r for r in rows if r["decision"] == "include"], key=lambda r: (r["year"] or 9999, -(r["cited_by_count"] or 0)))
seen_doi, seen_title, uniq, dropped = set(), set(), [], []
for r in inc:
    d = (r["doi"] or "").lower(); t = (norm(r["title"]), r["year"])
    if (d and d in seen_doi) or t in seen_title:
        dropped.append({"id": r["id"], "title": r["title"], "year": r["year"], "doi": r["doi"]}); continue
    if d: seen_doi.add(d)
    seen_title.add(t); uniq.append(r)
audit.write("dedupe", includes=len(inc), unique=len(uniq), dropped=[x["title"] for x in dropped])

# ---- unsure: lean rule ----
inc_ids = {r["id"] for r in uniq}
uns = [r for r in rows if r["decision"] == "unsure"]
fulltext, excluded = [], []
for r in uns:
    links = sum(1 for s in set(r["sources"]) if s.startswith("forward") or s.startswith("backward"))
    if links >= 2: r["fulltext_reason"] = f"unsure after abstract screening; {links} citation links to the corpus"; fulltext.append(r)
    else:
        r["decision"], r["reason"] = "exclude", f"unsure after abstract screening and only {links} citation link(s) to the corpus; not sent to full text"
        excluded.append(r)
audit.write("unsure_rule", unsure=len(uns), to_fulltext=len(fulltext), excluded=len(excluded))

# ---- split and holdout ----
early = [r for r in uniq if r["year"] and r["year"] <= 2017]
late = [r for r in uniq if not r["year"] or r["year"] > 2017]
rng = random.Random(20260930)
hold_ids = set(r["id"] for r in rng.sample(early, round(0.15 * len(early))))
for r in uniq: r["holdout"] = r["id"] in hold_ids; r["window"] = "<=2017" if r in early else "2018+"

def write_jsonl(path, items):
    with open(path, "w") as f:
        for r in items: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return hashlib.sha256(open(path, "rb").read()).hexdigest()
h_corpus = write_jsonl(OUT / "corpus.jsonl", uniq)
h_hold = write_jsonl(OUT / "holdout_ids.jsonl", [{"id": i} for i in sorted(hold_ids)])
h_ft = write_jsonl(OUT / "unsure_fulltext_queue.jsonl", fulltext)
h_ex = write_jsonl(OUT / "unsure_excluded.jsonl", excluded)
write_jsonl(OUT / "dropped_duplicates.jsonl", dropped)

# ---- DOI list for Zotero: everything <=2017 plus the full-text queue ----
zot = [r for r in early] + fulltext
with open(OUT / "zotero_dois_2017.txt", "w") as f:
    for r in zot:
        if r["doi"]: f.write(r["doi"].replace("https://doi.org/", "") + "\n")
with open(OUT / "zotero_no_doi_2017.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "year", "title", "venue", "type"])
    for r in zot:
        if not r["doi"]: w.writerow([r["id"], r["year"], r["title"], r["venue"], r["type"]])
with open(OUT / "zotero_dois_2018plus.txt", "w") as f:
    for r in late:
        if r["doi"]: f.write(r["doi"].replace("https://doi.org/", "") + "\n")

summary = {"unique_includes": len(uniq), "duplicates_dropped": len(dropped),
           "window_2017": len(early), "window_2018plus": len(late), "holdout": len(hold_ids),
           "unsure_to_fulltext": len(fulltext), "unsure_excluded": len(excluded),
           "zotero_2017_with_doi": sum(1 for r in zot if r["doi"]), "zotero_2017_no_doi": sum(1 for r in zot if not r["doi"]),
           "sha256": {"corpus": h_corpus, "holdout": h_hold, "fulltext_queue": h_ft, "unsure_excluded": h_ex}}
json.dump(summary, open(OUT / "FREEZE.json", "w"), indent=1)
audit.write("corpus_frozen", **summary)
print(json.dumps(summary, indent=1))
print("\ndropped duplicates:"); [print(" ", d["year"], d["title"][:70]) for d in dropped]
