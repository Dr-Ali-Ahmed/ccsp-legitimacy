"""Coarser dimension codebook: group the 98 canonical dimensions into families (variant B)."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import anthropic
from litsearch.audit import AuditLog
from ccsp.extract import load_key
ROOT = pathlib.Path(__file__).parent; load_key(); client = anthropic.Anthropic(timeout=3600.0)
audit = AuditLog(ROOT / "runs/stage9/audit_log.jsonl")
cb = json.load(open(ROOT / "data/corpus/codebook.json"))
dims = cb["dimensions"]["canonical"]
listing = "\n".join(f"{i}: {c['label']}" for i, c in enumerate(dims))
SCHEMA = {"type": "json_schema", "schema": {"type": "object", "properties": {"families": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "label": {"type": "string"}, "members": {"type": "array", "items": {"type": "integer"}}}, "required": ["id", "label", "members"], "additionalProperties": False}}},
    "required": ["families"], "additionalProperties": False}}
prompt = f"""Below are {len(dims)} dimension labels for the construct organizational legitimacy, each already a cluster of phrasings. Group them into dimension FAMILIES: a family is one way of cutting the construct (for example, the pragmatic/moral/cognitive typology and its individual members belong to one family; internal/external is another; input/throughput/output another; propriety/validity another). Aim for the smallest number of families that keeps genuinely different typologies apart, likely 10 to 20. Every index appears exactly once.

{listing}"""
with client.messages.stream(model="claude-opus-5", max_tokens=32000, thinking={"type": "adaptive"}, output_config={"format": SCHEMA, "effort": "high"},
                            messages=[{"role": "user", "content": prompt}]) as st: resp = st.get_final_message()
out = json.loads(next(b.text for b in resp.content if b.type == "text"))
fam_of = {}
for f in out["families"]:
    for m in f["members"]:
        if 0 <= m < len(dims): fam_of[dims[m]["id"]] = f["id"]
mapping = {ph: (fam_of.get(cid) if cid else None) for ph, cid in cb["dimensions"]["mapping"].items()}
cb["dimensions_families"] = {"canonical": out["families"], "mapping": mapping, "family_of_dimension": fam_of}
json.dump(cb, open(ROOT / "data/corpus/codebook.json", "w"), indent=1, ensure_ascii=False)
audit.write("codebook_families", field="dimensions", canonical_in=len(dims), families=len(out["families"]))
print(f"{len(dims)} dimensions -> {len(out['families'])} families")
for f in out["families"]: print(f"  {f['id']:6s} {f['label'][:60]:60s} {len(f['members'])}")
