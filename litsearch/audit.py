"""Append-only audit log for literature searches.

Every action in a search run is written as one JSON line: queries sent,
records received, and screening decisions with their reasons. The log is
never rewritten; re-running a step appends new events rather than
replacing old ones.

The writer itself refuses credentials: any value found in the project's
.env file is scrubbed from every event before it is written, so a
carelessly written connector cannot leak a key into a log that the
method encourages people to publish.
"""

import json
import datetime
import pathlib


def _load_secret_values():
    env_path = pathlib.Path(__file__).parent.parent / ".env"
    secrets = []
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                value = line.split("=", 1)[1].strip()
                if len(value) >= 8:
                    secrets.append(value)
    return secrets


class AuditLog:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secrets = _load_secret_values()

    def write(self, event_type, **payload):
        record = {
            "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": event_type,
            **payload,
        }
        line = json.dumps(record, ensure_ascii=False)
        for secret in self.secrets:
            if secret in line:
                line = line.replace(secret, "REDACTED")
        with open(self.path, "a") as f:
            f.write(line + "\n")
        return record

    def read_all(self):
        events = []
        with open(self.path) as f:
            for line in f:
                events.append(json.loads(line))
        return events
