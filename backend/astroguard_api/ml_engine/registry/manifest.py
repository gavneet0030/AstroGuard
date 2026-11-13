import json
from pathlib import Path


def write_manifest(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

    temporary.replace(path)


def read_manifest(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )