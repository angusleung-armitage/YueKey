#!/usr/bin/env python3
"""Fetch only checksum-pinned build inputs; never runs downloaded code."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch() -> None:
    manifest = json.loads((ROOT / "data/sources.lock.json").read_text())
    for name, source in manifest["sources"].items():
        target = ROOT / "build/sources" / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == source["sha256"]:
            continue
        request = urllib.request.Request(source["url"], headers={"User-Agent": "quick-hk/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != source["sha256"]:
            raise ValueError(f"Checksum mismatch: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)
        print(f"Fetched {name}")


if __name__ == "__main__":
    fetch()
