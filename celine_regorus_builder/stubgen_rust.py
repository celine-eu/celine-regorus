from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple


_PYMETHODS = re.compile(r"^\s*#\[\s*pymethods\s*\]\s*$")
_IMPL_ENGINE_START = re.compile(r"^\s*impl\s+Engine\s*\{\s*$")
_CFG_FEATURE = re.compile(r'^\s*#\[\s*cfg\s*\(\s*feature\s*=\s*"([^"]+)"\s*\)\s*\]\s*$')
_ATTR_NEW = re.compile(r"^\s*#\[\s*new\s*\]\s*$")

# Match `pub fn name(...) -> Ret {` AND `fn name(...) -> Ret {`
_FN_RE = re.compile(
    r"^\s*(?:pub\s+)?fn\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\((?P<args>[^)]*)\)\s*"
    r"(?:->\s*(?P<ret>.+?))?\s*"
    r"\{\s*$"
)


def _map_type(rt: str) -> str:
    t = (rt or "").strip().rstrip(";").strip()

    # Strip lifetimes like <'_>
    t = re.sub(r"<\s*'[^>]*\s*>", "", t)

    # Result<T> -> T
    m = re.match(r"Result<\s*([^>]+)\s*>", t)
    if m:
        t = m.group(1).strip()

    # PyResult<T> -> T
    m = re.match(r"PyResult<\s*([^>]+)\s*>", t)
    if m:
        t = m.group(1).strip()

    if t in {"()", ""}:
        return "None"
    if t == "Self":
        return "Engine"

    # Option<T> -> T | None
    m = re.match(r"Option<\s*([^>]+)\s*>", t)
    if m:
        return f"{_map_type(m.group(1))} | None"

    # Vec<T> -> list[T]
    m = re.match(r"Vec<\s*([^>]+)\s*>", t)
    if m:
        return f"list[{_map_type(m.group(1))}]"

    # primitives
    if t in {"String", "&str"}:
        return "str"
    if t == "bool":
        return "bool"
    if t in {"usize", "u64", "u32", "i64", "i32", "isize"}:
        return "int"
    if t in {"f64", "f32"}:
        return "float"

    # python interop
    if any(
        x in t
        for x in (
            "PyAny",
            "PyObject",
            "Bound",
            "Python",
            "PyDict",
            "PyList",
            "PyModule",
        )
    ):
        return "Any"

    return "Any"


def _parse_args(arg_str: str) -> List[Tuple[str, str]]:
    """
    Split args on commas not inside <>.
    Drop self/&self/&mut self and py: Python.
    """
    parts: List[str] = []
    cur = ""
    depth = 0
    for ch in arg_str:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            if cur.strip():
                parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())

    out: List[Tuple[str, str]] = []
    for p in parts:
        ps = p.strip()
        if ps in {"self", "&self", "&mut self"} or ps.endswith(" self"):
            continue
        if ":" not in ps:
            continue
        name, typ = [x.strip() for x in ps.split(":", 1)]
        if name == "py":
            continue
        out.append((name, _map_type(typ)))
    return out


def _brace_delta(line: str) -> int:
    # naive but fine for this file: count { and }
    return line.count("{") - line.count("}")


def generate_regorus_pyi_from_lib_rs(lib_rs: Path) -> bytes:
    lines = lib_rs.read_text(encoding="utf-8", errors="replace").splitlines()

    in_pymethods = False
    in_impl = False
    impl_depth = 0

    pending_new = False
    pending_feature: Optional[str] = None

    methods: List[Tuple[str, List[Tuple[str, str]], str, Optional[str]]] = []

    for line in lines:
        mfeat = _CFG_FEATURE.match(line)
        if mfeat:
            pending_feature = mfeat.group(1)
            continue

        if _ATTR_NEW.match(line):
            pending_new = True
            continue

        if _PYMETHODS.match(line):
            in_pymethods = True
            continue

        if in_pymethods and _IMPL_ENGINE_START.match(line):
            in_impl = True
            impl_depth = 1  # we just entered `impl Engine {`
            continue

        if in_impl:
            mfn = _FN_RE.match(line)
            if mfn:
                name = mfn.group("name")
                args = _parse_args(mfn.group("args") or "")
                ret = _map_type((mfn.group("ret") or "").strip())

                if pending_new or name == "new":
                    methods.append(("__init__", [], "None", pending_feature))
                else:
                    methods.append((name, args, ret, pending_feature))

                pending_new = False
                pending_feature = None

            # update brace depth *after* potential fn capture
            impl_depth += _brace_delta(line)

            # exit only when the impl block ends
            if impl_depth <= 0:
                in_impl = False
                in_pymethods = False
                pending_new = False
                pending_feature = None
                impl_depth = 0

    # de-dup __init__ if needed, stable sort with __init__ first
    seen = set()
    uniq: List[Tuple[str, List[Tuple[str, str]], str, Optional[str]]] = []
    for name, args, ret, feat in methods:
        key = (name, tuple(args), ret, feat)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((name, args, ret, feat))

    uniq.sort(key=lambda x: (0 if x[0] == "__init__" else 1, x[0]))

    out: List[str] = [
        "from __future__ import annotations",
        "from typing import Any",
        "",
        "__all__ = ['Engine']",
        "",
        "class Engine:",
        '    """Regorus engine."""',
        "",
    ]

    if not uniq:
        out.append("    ...")
    else:
        for name, args, ret, feat in uniq:
            if feat:
                out.append(f'    # Only present if compiled with Rust feature "{feat}"')
            if name == "__init__":
                out.append("    def __init__(self) -> None: ...")
                continue
            params = ["self"] + [f"{n}: {t}" for n, t in args]
            out.append(f"    def {name}({', '.join(params)}) -> {ret}: ...")

    out.append("")
    return ("\n".join(out)).encode("utf-8")
