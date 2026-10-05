"""OpenAlex connector.

Wraps the OpenAlex REST API (free, no key required). Every request and
response summary is written to the audit log by the caller. Uses the
polite pool by sending a contact email with each request.
"""

import pathlib
import time
import requests

BASE = "https://api.openalex.org"
MAILTO = "aliahmed@lsu.edu"


def load_openalex_key():
    env_path = pathlib.Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("OPENALEX_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


class OpenAlex:
    def __init__(self, audit_log):
        self.audit = audit_log
        self.session = requests.Session()
        self.api_key = load_openalex_key()

    def _get(self, url, params=None):
        params = dict(params or {})
        params["mailto"] = MAILTO
        if self.api_key:
            params["api_key"] = self.api_key
        # Log the request without credentials or contact details: published
        # audit logs must never contain keys.
        self.audit.write("api_request", url=url,
                         params={k: v for k, v in params.items()
                                 if k not in ("mailto", "api_key")})
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        time.sleep(0.15)  # stay well under the 10 req/s polite-pool limit
        return response.json()

    def search_title(self, title):
        """Search works by title; returns the result list (caller logs the choice)."""
        # OpenAlex treats ? and * as wildcards and rejects them in stemmed search.
        query = title.replace("?", " ").replace("*", " ")
        data = self._get(f"{BASE}/works", {"search": query, "per-page": 5})
        results = data.get("results", [])
        self.audit.write(
            "search_results",
            query=title,
            count=data.get("meta", {}).get("count"),
            returned=[{"id": w["id"], "title": w.get("title"), "year": w.get("publication_year")} for w in results],
        )
        return results

    def get_work(self, work_id):
        """Fetch one work by OpenAlex ID or DOI URL."""
        # A DOI URL is passed through whole; OpenAlex accepts /works/https://doi.org/...
        short_id = work_id if work_id.startswith("https://doi.org/") else work_id.rsplit("/", 1)[-1]
        work = self._get(f"{BASE}/works/{short_id}")
        self.audit.write("work_retrieved", id=work["id"], title=work.get("title"), year=work.get("publication_year"))
        return work

    def get_references(self, work):
        """Return the OpenAlex IDs a work references (backward chaining)."""
        refs = work.get("referenced_works", [])
        self.audit.write("references_listed", id=work["id"], count=len(refs))
        return refs

    def get_citers(self, work, max_records=2000, until_year=None):
        """Return works that cite the given work (forward chaining).

        Paginates with a cursor. An optional publication-year ceiling
        restricts the walk (for validation runs that must match a
        review's search cutoff). If max_records stops the walk early,
        the truncation is logged so no cap is silent.
        """
        short_id = work["id"].rsplit("/", 1)[-1]
        filters = f"cites:{short_id}"
        if until_year is not None:
            filters += f",to_publication_date:{until_year}-12-31"
        citers = []
        cursor = "*"
        total = None
        while cursor and len(citers) < max_records:
            data = self._get(
                f"{BASE}/works",
                {"filter": filters, "per-page": 200, "cursor": cursor},
            )
            total = data.get("meta", {}).get("count")
            citers.extend(data.get("results", []))
            cursor = data.get("meta", {}).get("next_cursor")
        truncated = total is not None and len(citers) < total
        self.audit.write(
            "citers_retrieved",
            id=work["id"],
            total_citers=total,
            retrieved=len(citers),
            truncated=truncated,
        )
        return citers

    def get_works_batch(self, work_ids):
        """Fetch up to 50 works per request by ID list."""
        works = []
        for i in range(0, len(work_ids), 50):
            batch = work_ids[i : i + 50]
            short_ids = "|".join(w.rsplit("/", 1)[-1] for w in batch)
            data = self._get(f"{BASE}/works", {"filter": f"openalex_id:{short_ids}", "per-page": 50})
            works.extend(data.get("results", []))
        self.audit.write("batch_retrieved", requested=len(work_ids), received=len(works))
        return works
