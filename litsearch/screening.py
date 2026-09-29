"""AI relevance screening.

The author declares the claim and inclusion criteria; the AI applies them to
each paper and returns include, exclude, or unsure, with a written reason.
Supports two paths: single calls (used for pilots and small sets) and the
Batch API (half price, used for large runs). Every decision is written to
the audit log with the model version, settings, and exact token counts.
"""

import json
import os
import pathlib
import time

import anthropic

DEFAULT_MODEL = "claude-opus-4-8"

DECISION_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["include", "exclude", "unsure"]},
            "reason": {"type": "string"},
        },
        "required": ["decision", "reason"],
        "additionalProperties": False,
    },
}


def load_api_key():
    """Read the key from the project .env. The .env deliberately overrides any
    ANTHROPIC_API_KEY inherited from the shell, because a stale key exported in
    a shell profile otherwise silently shadows the project's key."""
    env_path = pathlib.Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
    return os.environ["ANTHROPIC_API_KEY"]


BINARY_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["include", "exclude"]},
            "reason": {"type": "string"},
        },
        "required": ["decision", "reason"],
        "additionalProperties": False,
    },
}


class Screener:
    def __init__(self, declaration, audit_log, model=DEFAULT_MODEL, binary=False):
        load_api_key()
        self.client = anthropic.Anthropic()
        self.declaration = declaration
        self.audit = audit_log
        self.model = model
        self.binary = binary
        self.system_prompt = (
            "You are screening papers for a systematic literature search in "
            "management research. The author has declared the research claim and "
            "inclusion criteria below. Judge each paper you are given strictly "
            "against these criteria based on its title, venue, year, and abstract. "
            "Decide include, exclude, or unsure, and give a short reason that "
            "cites the specific criterion that drove your decision. Papers under "
            "different names for the same concept still count. If the abstract is "
            "missing and the title is not decisive, answer unsure.\n\n"
        )
        if self.binary:
            self.system_prompt = self.system_prompt.replace(
                "Decide include, exclude, or unsure",
                "Decide include or exclude; unsure is not permitted")
            self.system_prompt = self.system_prompt.replace(
                "If the abstract is missing and the title is not decisive, answer unsure.",
                "If the abstract is missing or does not state what the criteria require, "
                "lean exclude: only include a paper when the available text affirmatively "
                "supports the criteria.")
        self.system_prompt += (
            f"Research claim: {declaration['claim']}\n\n"
            f"Inclusion criteria (apply verbatim):\n{declaration['criteria']}"
        )

    def _params(self, record, abstract_text):
        paper_block = (
            f"Title: {record.get('title')}\n"
            f"Year: {record.get('year')}\n"
            f"Venue: {record.get('venue')}\n"
            f"Authors: {', '.join(record.get('authors', [])[:6])}\n"
            f"Abstract: {abstract_text or '(no abstract available)'}"
        )
        params = {
            "model": self.model,
            "max_tokens": 2000,
            "output_config": {"format": BINARY_SCHEMA if self.binary else DECISION_SCHEMA},
            "system": [{"type": "text", "text": self.system_prompt,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": paper_block}],
        }
        if self.model.startswith("claude-opus") or self.model.startswith("claude-fable"):
            params["thinking"] = {"type": "adaptive"}
            params["output_config"]["effort"] = "low"
        return params

    def screen(self, record, abstract_text):
        response = self.client.messages.create(**self._params(record, abstract_text))
        text = next(b.text for b in response.content if b.type == "text")
        verdict = json.loads(text)
        self.audit.write(
            "screening_decision",
            paper_id=record["id"],
            title=record.get("title"),
            decision=verdict["decision"],
            reason=verdict["reason"],
            model=response.model,
            path="single",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_tokens=response.usage.cache_read_input_tokens,
        )
        return verdict, response.usage

    def screen_batch(self, items, poll_seconds=20, chunk_size=1000):
        """items: list of (record, abstract_text). Returns {paper_id: verdict}.
        Uses the Batch API (half price). Splits large sets into chunks so no
        single request body gets huge, and retries submission on transient
        server errors. Blocks until all chunks complete."""
        verdicts = {}
        for start in range(0, len(items), chunk_size):
            chunk = items[start:start + chunk_size]
            verdicts.update(self._screen_one_batch(chunk, poll_seconds))
        return verdicts

    def _submit_with_retry(self, requests_payload, attempts=4):
        delay = 10
        for attempt in range(attempts):
            try:
                return self.client.messages.batches.create(requests=requests_payload)
            except anthropic.InternalServerError as exc:
                self.audit.write("batch_submit_retry", attempt=attempt + 1,
                                 error=str(exc)[:200])
                if attempt == attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 3

    def _screen_one_batch(self, items, poll_seconds=20):
        requests_payload = []
        by_custom_id = {}
        for i, (record, abstract) in enumerate(items):
            custom_id = f"p{i}_{record['id'].rsplit('/', 1)[-1]}"[:64]
            by_custom_id[custom_id] = record
            requests_payload.append({
                "custom_id": custom_id,
                "params": self._params(record, abstract),
            })
        batch = self._submit_with_retry(requests_payload)
        self.audit.write("screening_batch_submitted", batch_id=batch.id,
                         n_requests=len(requests_payload), model=self.model)
        while True:
            batch = self.client.messages.batches.retrieve(batch.id)
            if batch.processing_status == "ended":
                break
            time.sleep(poll_seconds)

        verdicts = {}
        totals = {"input": 0, "output": 0}
        for result in self.client.messages.batches.results(batch.id):
            record = by_custom_id[result.custom_id]
            if result.result.type != "succeeded":
                self.audit.write("screening_batch_item_failed",
                                 paper_id=record["id"],
                                 result_type=result.result.type)
                continue
            message = result.result.message
            text = next(b.text for b in message.content if b.type == "text")
            verdict = json.loads(text)
            verdicts[record["id"]] = verdict
            totals["input"] += message.usage.input_tokens
            totals["output"] += message.usage.output_tokens
            self.audit.write(
                "screening_decision",
                paper_id=record["id"],
                title=record.get("title"),
                decision=verdict["decision"],
                reason=verdict["reason"],
                model=message.model,
                path=f"batch:{batch.id}",
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens,
            )
        self.audit.write("screening_batch_finished", batch_id=batch.id,
                         succeeded=len(verdicts), **totals)
        return verdicts
