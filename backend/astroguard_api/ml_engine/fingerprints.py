import hashlib
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def dataset_fingerprint(paths):
    digest = hashlib.sha256()

    for path in paths:
        digest.update(str(path).encode())
        digest.update(sha256_file(path).encode())

    return digest.hexdigest()