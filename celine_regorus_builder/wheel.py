from __future__ import annotations
import base64, csv, hashlib, shutil, tempfile, zipfile
from pathlib import Path

PKG_INIT = """
from __future__ import annotations

from . import regorus as _native  # the compiled extension

# Re-export the API you want at top-level
Engine = _native.Engine

__all__ = ["Engine"]
"""


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _record_row(path_in_wheel: str, data: bytes) -> list[str]:
    digest = hashlib.sha256(data).digest()
    return [path_in_wheel, f"sha256={_b64(digest)}", str(len(data))]


def inject_typing(wheel_path: Path, pyi_bytes: bytes) -> None:
    """Inject regorus/regorus.pyi and regorus/py.typed and rebuild RECORD."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        unpack = td / "u"
        unpack.mkdir()
        with zipfile.ZipFile(wheel_path, "r") as z:
            z.extractall(unpack)

        pkg = unpack / "regorus"
        if not pkg.exists():
            raise RuntimeError("Expected 'regorus/' package dir not found in wheel")

        (pkg / "regorus.pyi").write_bytes(pyi_bytes)
        (pkg / "py.typed").write_text("", encoding="utf-8")
        (pkg / "__init__.py").write_text(PKG_INIT, encoding="utf-8")

        dist_infos = list(unpack.glob("*.dist-info"))
        if len(dist_infos) != 1:
            raise RuntimeError(f"Expected 1 dist-info dir, found {dist_infos}")
        dist = dist_infos[0]
        record = dist / "RECORD"
        record_rel = record.relative_to(unpack).as_posix()

        rows: list[list[str]] = []
        for p in unpack.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(unpack).as_posix()
            if rel == record_rel:
                rows.append([rel, "", ""])
            else:
                rows.append(_record_row(rel, p.read_bytes()))

        with record.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        tmp = wheel_path.with_suffix(wheel_path.suffix + ".tmp")
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in unpack.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(unpack).as_posix())

        tmp.replace(wheel_path)
