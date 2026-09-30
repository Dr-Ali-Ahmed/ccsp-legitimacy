"""Second pass for missing PDFs: open-access copies via Semantic Scholar and
Unpaywall, and direct download for SSRN. Legal routes only. Logs every attempt."""
import json, pathlib, sys, time, requests
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
ROOT = pathlib.Path(__file__).parent; PDF = ROOT / "pdfs"; PDF.mkdir(exist_ok=True)
audit = AuditLog(ROOT / "runs" / "stage6_fetch_audit_log.jsonl")
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (ccsp-legitimacy research; mailto:actuary.ali@gmail.com)"
rb = json.load(open(ROOT / "data/corpus/zotero_readback.json"))
missing = rb["missing"] + rb["not_in_zotero"]
got = {}
def save(doi, url, src):
    r = S.get(url, timeout=60, allow_redirects=True)
    if r.ok and r.headers.get("content-type","").startswith("application/pdf") and len(r.content) > 20000:
        p = PDF / (doi.replace("/","_") + ".pdf"); p.write_bytes(r.content); got[doi] = {"path": str(p), "source": src}; return True
    return False
for doi in missing:
    ok, tried = False, []
    try:
        r = S.get(f"https://api.unpaywall.org/v2/{doi}", params={"email": "actuary.ali@gmail.com"}, timeout=20)
        if r.ok:
            loc = r.json().get("best_oa_location") or {}
            if loc.get("url_for_pdf"): tried.append("unpaywall"); ok = save(doi, loc["url_for_pdf"], "unpaywall")
    except Exception as e: tried.append(f"unpaywall:{type(e).__name__}")
    if not ok:
        try:
            r = S.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}", params={"fields": "openAccessPdf"}, timeout=20)
            u = (r.json().get("openAccessPdf") or {}).get("url") if r.ok else None
            if u: tried.append("semantic_scholar"); ok = save(doi, u, "semantic_scholar")
        except Exception as e: tried.append(f"s2:{type(e).__name__}")
    audit.write("open_fetch", doi=doi, obtained=ok, tried=tried, source=got.get(doi, {}).get("source"))
    time.sleep(1.1)
json.dump(got, open(ROOT / "data/corpus/open_fetch_results.json", "w"), indent=1)
print(f"tried {len(missing)}, obtained {len(got)}")
for d, v in got.items(): print(" ", d, v["source"])
