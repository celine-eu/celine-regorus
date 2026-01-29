from __future__ import annotations
import json, os, urllib.request
from typing import Optional, List

REGORUS_REPO = "microsoft/regorus"
API = "https://api.github.com"

def _req(url: str) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "celine-regorus-builder"}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    r = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_latest_github_tag(repo: str = REGORUS_REPO) -> Optional[str]:
    data = _req(f"{API}/repos/{repo}/releases/latest")
    return data.get("tag_name") if isinstance(data, dict) else None

def fetch_all_github_tags(repo: str = REGORUS_REPO) -> List[str]:
    out: List[str] = []
    page = 1
    while True:
        data = _req(f"{API}/repos/{repo}/tags?per_page=100&page={page}")
        if not isinstance(data, list) or not data:
            break
        for t in data:
            if isinstance(t, dict) and t.get("name"):
                out.append(str(t["name"]))
        page += 1
    return out
