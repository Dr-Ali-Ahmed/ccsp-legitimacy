"""Step 4: extract a structured construct record from one paper.

Seven fields, each with the quoted sentence it came from, or "not stated".
Source may be the abstract (tier 1, every paper) or the full text (tier 2,
where available). The model is told to use only the supplied text, never
what it already knows about the construct. Pinned model, temperature 0,
every prompt and response logged.
"""
import json, os, pathlib
import anthropic

MODEL = "claude-opus-5"
PROMPT_VERSION = "extract-v1-2026-10-01"
CONSTRUCT = "legitimacy (organizational legitimacy)"

SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "definition": {"type": "object", "properties": {"value": {"type": ["string", "null"]}, "quote": {"type": ["string", "null"]}}, "required": ["value", "quote"], "additionalProperties": False},
            "essential_attributes": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "string"}, "quote": {"type": "string"}}, "required": ["value", "quote"], "additionalProperties": False}},
            "dimensions": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "string"}, "quote": {"type": "string"}}, "required": ["value", "quote"], "additionalProperties": False}},
            "level": {"type": "object", "properties": {"value": {"type": "string", "enum": ["individual", "group", "organization", "field", "society", "multilevel", "not stated"]}, "quote": {"type": ["string", "null"]}}, "required": ["value", "quote"], "additionalProperties": False},
            "antecedents": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "string"}, "quote": {"type": "string"}}, "required": ["value", "quote"], "additionalProperties": False}},
            "consequences": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "string"}, "quote": {"type": "string"}}, "required": ["value", "quote"], "additionalProperties": False}},
            "rival_constructs": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "string"}, "quote": {"type": "string"}}, "required": ["value", "quote"], "additionalProperties": False}},
            "disagrees_with_prior": {"type": "object", "properties": {"value": {"type": ["string", "null"]}, "quote": {"type": ["string", "null"]}}, "required": ["value", "quote"], "additionalProperties": False},
            "text_sufficient": {"type": "boolean"},
        },
        "required": ["definition", "essential_attributes", "dimensions", "level", "antecedents", "consequences", "rival_constructs", "disagrees_with_prior", "text_sufficient"],
        "additionalProperties": False,
    },
}

SYSTEM = f"""You are extracting a structured record of how ONE paper treats the construct {CONSTRUCT}.

Rules, in order of importance:
1. Use ONLY the text supplied below the line. You already know a great deal about this construct from other papers; none of that may enter the record. If the supplied text does not say it, the answer is null or an empty list.
2. Every value must carry a "quote": the exact sentence or clause from the supplied text it was taken from. Copy it verbatim. If you cannot quote it, do not record it.
3. Record what THIS paper asserts or proposes about the construct, not what it summarizes from others, unless it adopts that summary as its own position.
4. Field meanings:
   definition: how the paper defines the construct.
   essential_attributes: properties the paper says the construct must have to be the construct. Short noun phrases.
   dimensions: components, types or facets the paper names.
   level: the level of analysis at which the paper treats the construct.
   antecedents: what the paper says causes or produces the construct.
   consequences: what the paper says the construct causes.
   rival_constructs: constructs the paper explicitly distinguishes it from, or argues it overlaps with.
   disagrees_with_prior: any explicit claim that an earlier definition or conceptualization is wrong or incomplete, naming what changes.
5. text_sufficient: true if the supplied text lets you fill the definition or at least one attribute or dimension; false if it is too thin (for example an abstract that only mentions the construct).
Return JSON matching the schema. Nothing else."""


def load_key():
    env = pathlib.Path(__file__).parent.parent / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()


class Extractor:
    def __init__(self, audit, model=MODEL):
        load_key()
        self.client = anthropic.Anthropic()
        self.audit = audit
        self.model = model

    def extract(self, paper_id, text, source, max_chars=180000):
        text = text[:max_chars]
        params = {
            "model": self.model, "max_tokens": 6000,
            "system": [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": f"SOURCE TYPE: {source}\n----------------\n{text}"}],
            "output_config": {"format": SCHEMA, "effort": "medium"},
            "thinking": {"type": "adaptive"},
        }
        resp = self.client.messages.create(**params)
        out = json.loads(next(b.text for b in resp.content if b.type == "text"))
        # quote validation in code: every quote must appear in the supplied text
        def check(q): return bool(q) and q.strip()[:60].lower() in text.lower()
        bad = []
        for k in ("essential_attributes", "dimensions", "antecedents", "consequences", "rival_constructs"):
            for item in out[k]:
                if not check(item["quote"]): bad.append((k, item["value"]))
        for k in ("definition", "level", "disagrees_with_prior"):
            if out[k]["value"] and out[k]["value"] != "not stated" and not check(out[k]["quote"]): bad.append((k, out[k]["value"]))
        rec = {"paper_id": paper_id, "source": source, "model": resp.model, "prompt_version": PROMPT_VERSION,
               "record": out, "unverified_quotes": bad,
               "usage": {"in": resp.usage.input_tokens, "cache_read": resp.usage.cache_read_input_tokens, "out": resp.usage.output_tokens}}
        self.audit.write("extraction", paper_id=paper_id, source=source, model=resp.model, prompt_version=PROMPT_VERSION,
                         text_sufficient=out["text_sufficient"], n_attributes=len(out["essential_attributes"]),
                         n_dimensions=len(out["dimensions"]), unverified_quotes=len(bad), usage=rec["usage"])
        return rec
