from __future__ import annotations
import json, urllib.request, urllib.error
from typing import Optional

def fetch_pypi_version(package: str) -> Optional[str]:
    url = f"https://pypi.org/pypi/{package}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "celine-regorus-builder"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
            return data.get("info", {}).get("version")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
