"""Stage 1: build the candidate pool for the legitimacy construct corpus.

Seeds (declaration/seeds.csv) -> resolve in OpenAlex -> backward chain (what
they cite) -> forward chain (what cites them, for seeds flagged yes) ->
keyword search -> one deduplicated candidate pool with abstracts.

No screening here. Every retrieval is audit-logged. Nothing is dropped
silently: forward citers that fail the concept-signal prefilter are kept in
a separate file so the prefilter itself can be audited.
"""

import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from litsearch.audit import AuditLog
from litsearch.openalex import OpenAlex, BASE
from litsearch.corpus import abstract_text

ROOT = pathlib.Path(__file__).parent
RUN = ROOT / "runs" / "stage1"
RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl")
oa = OpenAlex(audit)

CONCEPT_WORDS = ["defin", "conceptual", "construct", "dimension", "typolog",
                 "types of", "judgment", "judgement", "review", "distinguish",
                 "differ", "reputation", "status", "boundar", "what is",
                 "theoriz", "theoris", "multilevel", "multi-level",
                 "level of analysis", "perception", "process", "taking stock",
                 "meaning", "critique", "reconceptual", "clarif"]


def slim(w):
    return {
        "id": w["id"],
        "doi": w.get("doi"),
        "title": w.get("title") or w.get("display_name"),
        "year": w.get("publication_year"),
        "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
        "type": w.get("type"),
        "cited_by_count": w.get("cited_by_count"),
        "abstract": abstract_text(w),
        "referenced_works": w.get("referenced_works", []),
    }


def concept_signal(rec):
    t = (rec["title"] or "").lower()
    a = (rec["abstract"] or "").lower()
    if "legitima" in t:
        return True
    if "legitima" in a and any(k in a for k in CONCEPT_WORDS):
        return True
    return False


if __name__ == '__main__':
    # ---- 1. resolve seeds ------------------------------------------------------
    seeds = list(csv.DictReader(open(ROOT / "declaration" / "seeds.csv")))
    resolved = []
    for s in seeds:
        pick = None
        if s.get("doi"):
            pick = oa.get_work("https://doi.org/" + s["doi"])
            hits = [pick]
        else:
            hits = oa.search_title(s["title"])
        for h in ([] if pick else hits):
            if h.get("publication_year") == int(s["year"]):
                pick = h
                break
        if pick is None and hits:
            # fall back to the top hit within one year, and log that it is a fallback
            for h in hits:
                if abs((h.get("publication_year") or 0) - int(s["year"])) <= 1:
                    pick = h
                    break
        audit.write("seed_resolution", seed=s["title"], year=s["year"],
                    chosen=(pick or {}).get("id"), chosen_title=(pick or {}).get("title"),
                    chosen_year=(pick or {}).get("publication_year"),
                    exact_year=bool(pick and pick.get("publication_year") == int(s["year"])))
        if pick:
            full = oa.get_work(pick["id"])
            r = slim(full)
            r["seed_role"] = s["role"]
            r["forward_chain"] = s["forward_chain"] == "yes"
            resolved.append(r)
            print(f"seed  {s['year']}  {r['title'][:60]:60s}  {r['venue'] or '?'}  citers={r['cited_by_count']}")
        else:
            print(f"seed  {s['year']}  NOT RESOLVED: {s['title']}")

    json.dump(resolved, open(RUN / "seeds_resolved.json", "w"), indent=1)

    pool = {}
    def add(rec, source):
        if rec["id"] in pool:
            pool[rec["id"]]["sources"].append(source)
        else:
            rec = dict(rec)
            rec["sources"] = [source]
            pool[rec["id"]] = rec

    for r in resolved:
        add(r, "seed")

    # ---- 2. backward chaining ---------------------------------------------------
    back_ids = set()
    for r in resolved:
        back_ids.update(r["referenced_works"])
    back_ids -= set(pool)
    print(f"\nbackward: {len(back_ids)} unique referenced works to fetch")
    for w in oa.get_works_batch(sorted(back_ids)):
        add(slim(w), "backward")

    # ---- 3. forward chaining ----------------------------------------------------
    prefiltered_out = []
    for r in resolved:
        if not r["forward_chain"]:
            continue
        citers = oa.get_citers({"id": r["id"]}, max_records=20000)
        kept = 0
        for w in citers:
            rec = slim(w)
            if rec["id"] in pool:
                pool[rec["id"]]["sources"].append(f"forward:{r['year']}")
                continue
            if concept_signal(rec):
                add(rec, f"forward:{r['year']}")
                kept += 1
            else:
                prefiltered_out.append({"id": rec["id"], "title": rec["title"], "year": rec["year"],
                                        "cites_seed": r["id"]})
        print(f"forward  from {r['year']} {r['title'][:40]:40s}  citers={len(citers):6d}  kept={kept}")

    # ---- 4. keyword search ------------------------------------------------------
    kw_queries = [
        "legitimacy concept definition organizational",
        "organizational legitimacy theory conceptualization",
        "legitimacy judgments organizations",
        "legitimacy reputation status distinction",
        "legitimacy review organizational institutionalism",
    ]
    for q in kw_queries:
        cursor, n = "*", 0
        while cursor and n < 1000:
            data = oa._get(f"{BASE}/works", {"search": q, "filter": "from_publication_date:1975-01-01,type:article|book-chapter|review",
                                             "per-page": 200, "cursor": cursor})
            for w in data.get("results", []):
                rec = slim(w)
                if rec["id"] in pool:
                    pool[rec["id"]]["sources"].append("keyword")
                elif concept_signal(rec):
                    add(rec, "keyword")
                n += 1
            cursor = data.get("meta", {}).get("next_cursor")
        audit.write("keyword_search", query=q, scanned=n)
        print(f"keyword  '{q}'  scanned={n}")

    # ---- 5. save ----------------------------------------------------------------
    for rec in pool.values():
        rec.pop("referenced_works", None)
    with open(RUN / "candidates.jsonl", "w") as f:
        for rec in pool.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(RUN / "forward_prefiltered_out.jsonl", "w") as f:
        for rec in prefiltered_out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    from collections import Counter
    src = Counter(s.split(":")[0] for rec in pool.values() for s in set(rec["sources"]))
    with_abs = sum(1 for r in pool.values() if r["abstract"])
    summary = {"candidates": len(pool), "with_abstract": with_abs, "by_source": dict(src),
               "forward_prefiltered_out": len(prefiltered_out)}
    json.dump(summary, open(RUN / "summary.json", "w"), indent=1)
    audit.write("stage1_complete", **summary)
    print("\n", json.dumps(summary, indent=1))
