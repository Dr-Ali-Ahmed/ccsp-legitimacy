"""Frozen corpus store.

Saves every retrieved work as JSON so the search can be re-run later
against the exact same body of literature, regardless of how the live
database changes afterward.
"""

import json
import pathlib


class Corpus:
    def __init__(self, directory, audit_log):
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.audit = audit_log

    def _path(self, work_id):
        return self.dir / (work_id.rsplit("/", 1)[-1] + ".json")

    def save(self, work, role):
        """Save a work with its role in the search (seed, reference, citer)."""
        path = self._path(work["id"])
        already = path.exists()
        record = {
            "role": role,
            "id": work["id"],
            "doi": work.get("doi"),
            "title": work.get("title"),
            "year": work.get("publication_year"),
            "venue": ((work.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "authors": [
                ((a.get("author") or {}).get("display_name"))
                for a in work.get("authorships", [])
                if (a.get("author") or {}).get("display_name")
            ],
            "cited_by_count": work.get("cited_by_count"),
            "abstract_inverted_index": work.get("abstract_inverted_index"),
            "referenced_works": work.get("referenced_works", []),
        }
        with open(path, "w") as f:
            json.dump(record, f, ensure_ascii=False)
        if not already:
            self.audit.write("work_frozen", id=work["id"], role=role)
        return record

    def count(self):
        return sum(1 for _ in self.dir.glob("*.json"))

    def load_all(self):
        works = []
        for path in sorted(self.dir.glob("*.json")):
            with open(path) as f:
                works.append(json.load(f))
        return works


def abstract_text(record):
    """Rebuild readable abstract text from OpenAlex's inverted index."""
    inv = record.get("abstract_inverted_index")
    if not inv:
        return None
    positions = {}
    for word, indexes in inv.items():
        for i in indexes:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))
