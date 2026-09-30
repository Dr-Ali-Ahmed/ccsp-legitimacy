"""Codebook pass: cluster every attribute / dimension / rival-construct phrasing
seen in the corpus into canonical items, once, logged, human-editable.
This is the 'ID alignment' step (deck slide 40). AI proposes the codebook;
the mapping file is the artifact a person can correct."""
import json, pathlib, sys, os
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import anthropic
from litsearch.audit import AuditLog
from ccsp.extract import load_key
ROOT = pathlib.Path(__file__).parent; RUN = ROOT / "runs" / "stage9"; RUN.mkdir(parents=True, exist_ok=True)
audit = AuditLog(RUN / "audit_log.jsonl"); load_key(); client = anthropic.Anthropic(timeout=3600.0, max_retries=3)
OUT = ROOT / "data/corpus/codebook.json"

ab = [json.loads(l) for l in open(ROOT / "runs/stage7_abstract/records.jsonl")]
ft = [json.loads(l) for l in open(ROOT / "runs/stage7_fulltext/records.jsonl")]
recs = {r["paper_id"]: r for r in ab}; recs.update({r["paper_id"]: r for r in ft})

FIELD_GUIDE = {
 "essential_attributes": "Properties the construct must have to be the construct (e.g. 'perceived by an audience', 'conformity with norms', 'socially constructed'). Consequences, antecedents, and remarks about the term's usage are NOT attributes: put those under 'discard' with the reason.",
 "dimensions": "Named types, components or facets of the construct (e.g. pragmatic / moral / cognitive; regulative / normative; input vs output legitimacy). Merge the same type under different names.",
 "rival_constructs": "Other constructs the papers distinguish legitimacy from or relate it to (reputation, status, trust, power, justice...). Merge synonyms; keep genuinely different constructs apart.",
 "antecedents": "Things said to cause or produce legitimacy. Merge synonyms into one canonical cause each.",
 "consequences": "Things legitimacy is said to cause. Merge synonyms.",
}
SCHEMA = {"type": "json_schema", "schema": {"type": "object", "properties": {
    "canonical": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "string"}, "label": {"type": "string"}, "members": {"type": "array", "items": {"type": "integer"}}},
        "required": ["id", "label", "members"], "additionalProperties": False}},
    "discard": {"type": "array", "items": {"type": "object", "properties": {"index": {"type": "integer"}, "reason": {"type": "string"}},
        "required": ["index", "reason"], "additionalProperties": False}}},
    "required": ["canonical", "discard"], "additionalProperties": False}}

codebook = json.load(open(OUT)) if OUT.exists() else {}
for field, guide in FIELD_GUIDE.items():
    if field in codebook: print(f"{field}: already done, skipping"); continue
    phr = []
    for r in recs.values():
        for i in r["record"][field]: phr.append(i["value"])
    uniq = sorted(set(p.strip() for p in phr if p.strip()))
    listing = "\n".join(f"{i}: {p}" for i, p in enumerate(uniq))
    prompt = f"""You are building a codebook for the field '{field}' of a construct record about organizational legitimacy.
{guide}
Below are {len(uniq)} phrasings collected from {len(recs)} papers. Group phrasings that mean the same thing into one canonical item with a short label (3 to 8 words). Every index must appear exactly once, either in a canonical item's members or in discard. Do not invent items that no phrasing supports. Prefer fewer, well separated canonical items; split only where the papers clearly mean different things.

{listing}"""
    with client.messages.stream(model="claude-opus-5", max_tokens=64000, thinking={"type": "adaptive"},
        output_config={"format": SCHEMA, "effort": "high"}, messages=[{"role": "user", "content": prompt}]) as stream:
        resp = stream.get_final_message()
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if text is None:
        audit.write("codebook_failed", field=field, stop_reason=resp.stop_reason, blocks=[b.type for b in resp.content])
        print(f"{field}: no output, stop_reason={resp.stop_reason}"); continue
    out = json.loads(text)
    mapping = {}
    bad_idx = 0
    for c in out["canonical"]:
        for m in c["members"]:
            if 0 <= m < len(uniq): mapping[uniq[m]] = c["id"]
            else: bad_idx += 1
    for d in out["discard"]:
        if 0 <= d["index"] < len(uniq): mapping[uniq[d["index"]]] = None
        else: bad_idx += 1
    if bad_idx: audit.write("codebook_bad_indices", field=field, count=bad_idx)
    missing = [p for p in uniq if p not in mapping]
    codebook[field] = {"canonical": out["canonical"], "discard": out["discard"], "mapping": mapping, "phrasings": uniq, "unmapped": missing}
    audit.write("codebook", field=field, phrasings=len(uniq), canonical=len(out["canonical"]), discarded=len(out["discard"]), unmapped=len(missing),
                usage={"in": resp.usage.input_tokens, "out": resp.usage.output_tokens})
    print(f"{field:22s} {len(uniq):4d} phrasings -> {len(out['canonical']):3d} canonical, {len(out['discard'])} discarded, {len(missing)} unmapped")
    json.dump(codebook, open(OUT, "w"), indent=1, ensure_ascii=False)
print("\nattribute codebook:")
for c in codebook["essential_attributes"]["canonical"]: print(f"  {c['id']:6s} {c['label']:45s} ({len(c['members'])} phrasings)")
