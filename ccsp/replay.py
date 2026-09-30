"""Steps 5 to 8: running state, materiality by comparison, indicators, and the
conjunctive stopping rule, replayed over the corpus in publication order.

PRE-REGISTERED SETTINGS (set 2026-10-01 before any replay was run; changed only
through the sensitivity sweep, which reports every variant):
  BATCH = 10           papers per batch (the deck's 10 to 20; we take the low end because
                       abstract records are thin and smaller batches expose movement)
  K = 3                consecutive quiet batches before a candidate stop (deck slide 43)
  TAU_SYN = 0.55       cosine similarity above which two items are the same item
                       (MiniLM scores paraphrases of a definition near 0.5, unrelated near 0.0)
  TAU_AC = 0.10        attribute change (1 - Jaccard) below which the batch is quiet on attributes
  TAU_NC = 0.25        network change below which the batch is quiet on relations
  MATERIAL = attribute added, dimension added, level changed, rival construct added
  NOMOLOGICAL (new antecedent or consequence) is flagged but NOT material by default
  (deck slide 41: a network can grow without the construct changing); the sweep runs a
  variant where it counts.
Embedding model pinned: sentence-transformers/all-MiniLM-L6-v2. Chao1 as in the POC.
"""
import json
import math
import numpy as np
from collections import Counter, defaultdict
from sentence_transformers import SentenceTransformer

BATCH, K, TAU_SYN, TAU_AC, TAU_NC = 10, 3, 0.55, 0.10, 0.25
_model = None
def embed(texts):
    global _model
    if _model is None: _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model.encode(list(texts), normalize_embeddings=True) if len(texts) else np.zeros((0, 384))


def chao1(counts):
    f1 = sum(1 for c in counts if c == 1); f2 = sum(1 for c in counts if c == 2); s = len(counts)
    est = s + (f1 * (f1 - 1)) / (2 * (f2 + 1)) if s else 0
    return {"observed": s, "estimated": round(est, 1), "coverage": round(s / est, 3) if est else None}


class Canon:
    """Canonical item store for one field: matches new phrasings to existing items by embedding."""
    def __init__(self, tau): self.tau, self.items, self.vecs, self.count = tau, [], np.zeros((0, 384)), []
    def match(self, text, vec):
        if len(self.items):
            sims = self.vecs @ vec; j = int(np.argmax(sims))
            if sims[j] >= self.tau: self.count[j] += 1; return j, float(sims[j]), False
        self.items.append(text); self.vecs = np.vstack([self.vecs, vec]); self.count.append(1)
        return len(self.items) - 1, 1.0, True
    def ids(self): return set(range(len(self.items)))


class State:
    FIELDS = ("essential_attributes", "dimensions", "antecedents", "consequences", "rival_constructs")
    def __init__(self, tau_syn=TAU_SYN, codebook=None, confirm_dimensions=False):
        self.canon = {f: Canon(tau_syn) for f in self.FIELDS}
        self.codebook = codebook or {}
        self.seen_ids = {f: Counter() for f in self.FIELDS}
        self.confirm_dimensions = confirm_dimensions
        self.levels = Counter(); self.definition = None; self.def_vec = None; self.n_papers = 0
    def snapshot(self):
        return {f: set(self.canon[f].ids()) for f in self.FIELDS} | {"level": self.modal_level()}
    def modal_level(self):
        return self.levels.most_common(1)[0][0] if self.levels else None
    def absorb(self, rec, material_nomological=False):
        """Compare one paper's record with the state (materiality by diff), then merge it in."""
        r = rec["record"]; changes = defaultdict(list); novelty = []
        for f in self.FIELDS:
            vals = [i["value"] for i in r[f]]
            cbm = self.codebook.get(f, {}).get("mapping", {})
            fallback = [v for v in vals if v.strip() not in cbm]      # not in the codebook: embed and match
            vecs = dict(zip(fallback, embed(fallback))) if fallback else {}
            for v in vals:
                key = v.strip()
                if key in cbm:
                    cid = cbm[key]
                    if cid is None: continue                        # discarded by the codebook
                    prev = self.seen_ids[f][cid]; self.seen_ids[f][cid] += 1; new = prev == 0
                    if new: self.canon[f].items.append(cid); self.canon[f].count.append(1)
                    else: self.canon[f].count[self.canon[f].items.index(cid)] += 1
                    if f == "dimensions" and self.confirm_dimensions:
                        if prev == 1: changes[f].append(cid)        # second sighting confirms it
                    elif new: changes[f].append(cid)
                    novelty.append(1.0 if new else 0.0)
                else:
                    j, sim, new = self.canon[f].match(v, vecs[v])
                    if new: changes[f].append(v)
                    novelty.append(1 - sim if not new else 1.0 if len(self.canon[f].items) > 1 else 0.0)
        lvl = r["level"]["value"]; level_changed = False
        if lvl and lvl != "not stated":
            # AMENDMENT 2026-10-01: material only if this level was never seen before
            if self.levels and lvl not in self.levels: level_changed = True
            self.levels[lvl] += 1
        d = r["definition"]["value"]; dd = None
        if d:
            v = embed([d])[0]
            if self.def_vec is not None: dd = float(1 - self.def_vec @ v)
            self.definition, self.def_vec = d, v
        material = bool(changes["essential_attributes"] or changes["dimensions"] or level_changed or changes["rival_constructs"])
        nomological = bool(changes["antecedents"] or changes["consequences"])
        if material_nomological and nomological: material = True
        cat = ("dimension/definition" if changes["essential_attributes"] or changes["dimensions"] else
               "boundary" if changes["rival_constructs"] else "level" if level_changed else
               "nomological" if nomological else "redundant/contextual")
        self.n_papers += 1
        return {"paper_id": rec["paper_id"], "source": rec["source"], "material": material, "category": cat,
                "changes": dict(changes), "level_changed": level_changed, "definition_drift": dd,
                "semantic_novelty": float(np.mean(novelty)) if novelty else 0.0, "disagrees_with_prior": bool(r["disagrees_with_prior"]["value"])}


def jaccard_change(before, after):
    u = before | after
    return 0.0 if not u else 1 - len(before & after) / len(u)


def replay(records, batch=BATCH, k=K, tau_syn=TAU_SYN, tau_ac=TAU_AC, tau_nc=TAU_NC, material_nomological=False, stop_at_first=False, codebook=None, confirm_dimensions=False, tau_v=0.0):
    """records: list of extraction records sorted by year. Returns per-batch log and the stop point."""
    st = State(tau_syn, codebook, confirm_dimensions); log = []; streak = 0; stop = None
    for b in range(0, len(records), batch):
        chunk = records[b:b + batch]; before = st.snapshot(); paper_log = []
        for rec in chunk: paper_log.append(st.absorb(rec, material_nomological))
        after = st.snapshot()
        ac = jaccard_change(before["essential_attributes"] | before["dimensions"], after["essential_attributes"] | after["dimensions"])
        nc = jaccard_change(before["antecedents"] | before["consequences"] | before["rival_constructs"],
                            after["antecedents"] | after["consequences"] | after["rival_constructs"])
        n_material = sum(p["material"] for p in paper_log)
        dd = [p["definition_drift"] for p in paper_log if p["definition_drift"] is not None]
        quiet = (n_material / max(len(chunk), 1) <= tau_v) and (ac < tau_ac) and (nc < tau_nc)
        streak = streak + 1 if quiet else 0
        entry = {"batch": b // batch + 1, "years": [chunk[0]["year"], chunk[-1]["year"]], "n": len(chunk),
                 "AC": round(ac, 3), "NC": round(nc, 3), "DD_mean": round(float(np.mean(dd)), 3) if dd else None,
                 "SN_mean": round(float(np.mean([p["semantic_novelty"] for p in paper_log])), 3),
                 "material": n_material, "material_ids": [p["paper_id"] for p in paper_log if p["material"]],
                 "quiet": quiet, "streak": streak,
                 "chao1_attributes": chao1(st.canon["essential_attributes"].count),
                 "state_size": {f: len(st.canon[f].items) for f in State.FIELDS}, "papers": paper_log}
        log.append(entry)
        if streak >= k and stop is None:
            stop = {"batch": entry["batch"], "after_paper": st.n_papers, "year": chunk[-1]["year"]}
            if stop_at_first: break
    return {"settings": {"batch": batch, "k": k, "tau_syn": tau_syn, "tau_ac": tau_ac, "tau_nc": tau_nc, "material_nomological": material_nomological, "confirm_dimensions": confirm_dimensions, "tau_v": tau_v},
            "n_records": len(records), "stop": stop, "batches": log, "final_state": {f: st.canon[f].items for f in State.FIELDS} | {"definition": st.definition, "levels": dict(st.levels)}}
