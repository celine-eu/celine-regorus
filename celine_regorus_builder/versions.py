from __future__ import annotations
import re
from typing import Optional, Tuple

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")

def tag_to_version(tag: str) -> str:
    tag = tag.strip()
    m = _SEMVER.search(tag)
    if not m:
        raise ValueError(f"Cannot extract semver from tag: {tag}")
    return f"{int(m.group(1))}.{int(m.group(2))}.{int(m.group(3))}"

def parse_semver(s: str) -> Optional[Tuple[int,int,int]]:
    m = _SEMVER.search(s.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

def is_newer(github_tag: str, pypi_version: str) -> bool:
    gv = parse_semver(github_tag)
    pv = parse_semver(pypi_version)
    if gv is None:
        return False
    if pv is None:
        return True
    return gv > pv
