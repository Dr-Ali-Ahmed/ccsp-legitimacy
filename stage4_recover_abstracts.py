"""Recover missing abstracts for stage 2 'unsure' papers from Semantic Scholar
and Crossref, so they can be rescreened on the same terms as everything else.
Papers still without an abstract afterwards are excluded with a logged reason."""
import json, pathlib, sys, time, requests
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
ROOT = pathlib.Path(__file__).parent
RUN = ROOT / "runs" / "stage4"; RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl")
S = requests.Session(); S.headers["User-Agent"] = "ccsp-legitimacy (mailto:actuary.ali@gmail.com)"

def s2(doi, title):
    try:
        if doi:
            r = S.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi.replace('https://doi.org/','')}", params={"fields": "abstract"}, timeout=20)
            if r.ok and r.json().get("abstract"): return r.json()["abstract"], "semantic_scholar"
        r = S.get("https://api.semanticscholar.org/graph/v1/paper/search", params={"query": title, "limit": 1, "fields": "abstract,title"}, timeout=20)
        if r.ok and r.json().get("data"):
            d = r.json()["data"][0]
            if d.get("abstract") and (d.get("title") or "").lower()[:40] == (title or "").lower()[:40]:
                return d["abstract"], "semantic_scholar_title"
    except Exception: pass
    return None, None

def crossref(doi):
    if not doi: return None, None
    try:
        r = S.get(f"https://api.crossref.org/works/{doi.replace('https://doi.org/','')}", timeout=20)
        if r.ok:
            a = r.json()["message"].get("abstract")
            if a:
                import re; return re.sub(r"<[^>]+>", " ", a).strip(), "crossref"
    except Exception: pass
    return None, None

rows = [json.loads(l) for l in open(ROOT / "runs" / "stage2_final_decisions.jsonl")]
unsure = [r for r in rows if r["decision"] == "unsure"]
found = 0
for r in unsure:
    if r["abstract"]: r["abstract_source"] = "openalex"; continue
    a, src = s2(r["doi"], r["title"])
    if not a: a, src = crossref(r["doi"])
    if a: r["abstract"], r["abstract_source"] = a, src; found += 1
    else: r["abstract_source"] = None
    audit.write("abstract_recovery", id=r["id"], source=src, found=bool(a))
    time.sleep(1.1)
with open(RUN / "unsure_with_abstracts.jsonl", "w") as f:
    for r in unsure:
        if r["abstract"]: f.write(json.dumps(r, ensure_ascii=False) + "\n")
with open(RUN / "unsure_no_abstract_excluded.jsonl", "w") as f:
    for r in unsure:
        if not r["abstract"]:
            r["decision"], r["reason"] = "exclude", "no abstract available from OpenAlex, Semantic Scholar or Crossref; title alone not decisive"
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
summary = {"unsure": len(unsure), "had_abstract": sum(1 for r in unsure if r.get("abstract_source")=="openalex"),
           "recovered": found, "still_none": sum(1 for r in unsure if not r["abstract"])}
json.dump(summary, open(RUN / "summary.json", "w"), indent=1); audit.write("stage4_complete", **summary)
print(json.dumps(summary, indent=1))
