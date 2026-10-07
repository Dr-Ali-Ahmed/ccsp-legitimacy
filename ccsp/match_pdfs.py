"""Match downloaded PDFs (any filename) to corpus DOIs by reading the first pages:
DOI pattern first, then title similarity against the frozen corpus. Logs every match
with its confidence; low-confidence matches go to a review list."""
import json, pathlib, re, sys, difflib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from ccsp.pdf_text import pdf_to_text
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>)\]]+", re.I)
def norm(t): return re.sub(r"[^a-z0-9 ]+", " ", (t or "").lower()).strip()
def match_folder(folder, corpus_path, out_path):
    corpus = [json.loads(l) for l in open(corpus_path)]
    by_doi = {(r.get("doi") or "").replace("https://doi.org/", "").lower(): r for r in corpus if r.get("doi")}
    titles = [(norm(r["title"]), r) for r in corpus if r.get("title")]
    results = []
    for pdf in sorted(pathlib.Path(folder).glob("*.pdf")):
        t = pdf_to_text(pdf)["text"]; head = t[:6000]
        found = None; how = None; conf = 0.0
        for m in DOI_RE.findall(head):
            d = m.rstrip(".,;").lower()
            if d in by_doi: found, how, conf = by_doi[d], "doi on first page", 1.0; break
        if not found:
            h = norm(head)
            best = max(titles, key=lambda x: difflib.SequenceMatcher(None, x[0], h[:len(x[0]) + 400]).ratio() if x[0] and x[0] in h or True else 0)
            # exact title containment is strongest; else ratio
            for nt, r in titles:
                # short generic titles ("Legitimacy") are too easy to find by accident: send those to review
                if nt and len(nt) >= 25 and nt in h: found, how, conf = r, "title found on first page", 0.95; break
                if nt and len(nt) < 25 and nt in h and str(r.get("year")) in head: found, how, conf = r, "short title plus year on first page", 0.8; break
            if not found:
                best, score = None, 0
                for nt, r in titles:
                    sc = difflib.SequenceMatcher(None, nt, h[:3000]).find_longest_match(0, len(nt), 0, min(len(h), 3000)).size / max(len(nt), 1)
                    if sc > score: best, score = r, sc
                if best and score >= 0.6: found, how, conf = best, "title similarity", round(score, 2)
        results.append({"file": pdf.name, "doi": (found or {}).get("doi"), "title": (found or {}).get("title"), "year": (found or {}).get("year"),
                        "how": how, "confidence": conf, "chars": len(t.strip()), "needs_review": conf < 0.9})
    json.dump(results, open(out_path, "w"), indent=1, ensure_ascii=False)
    return results
if __name__ == "__main__":
    folder, corpus, out = sys.argv[1], sys.argv[2], sys.argv[3]
    res = match_folder(folder, corpus, out)
    print(f"{len(res)} PDFs: {sum(1 for r in res if r['doi'])} matched, {sum(1 for r in res if r['needs_review'])} need review")
