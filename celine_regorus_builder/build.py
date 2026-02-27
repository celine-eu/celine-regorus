from __future__ import annotations
import os, re, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from .versions import base, tag_to_version
from .wheel import inject_typing
from .stubgen_rust import generate_regorus_pyi_from_lib_rs

REGORUS_REPO = "microsoft/regorus"
PYPI_PACKAGE = "celine-regorus"

root_dir = Path(__file__).parent.parent
dist_readme = root_dir / "stubs" / "README.dist.md"

stub_dir = root_dir / "stubs"


def post_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def effective_version(
    upstream_version: str,
    force: bool,
    fixed_post_ts: Optional[str] = None,
    existing_pypi_version: Optional[str] = None,
) -> str:
    if not force:
        return upstream_version
    if fixed_post_ts:
        return f"{upstream_version}.post{fixed_post_ts}"
    if (
        existing_pypi_version
        and ".post" in existing_pypi_version
        and base(existing_pypi_version) == upstream_version
    ):
        print(f"[INFO] Reusing existing PyPI post-release version: {existing_pypi_version}")
        return existing_pypi_version
    ts = fixed_post_ts or post_ts()
    return f"{upstream_version}.post{ts}"


def update_pyproject_toml(
    path: Path,
    tag: str,
    force: bool,
    fixed_post_ts: Optional[str] = None,
    existing_pypi_version: Optional[str] = None,
) -> None:
    """Patch upstream bindings/python/pyproject.toml for celine-regorus packaging."""
    content = path.read_text(encoding="utf-8")
    version = tag_to_version(tag)

    if force:
        version = effective_version(
            version,
            force,
            fixed_post_ts=fixed_post_ts,
            existing_pypi_version=existing_pypi_version,
        )
        print(f"[INFO] Forced build, using version {version}")

    # name: regorus -> celine-regorus
    content = re.sub(
        r'(?m)^\s*name\s*=\s*"regorus"\s*$', f'name = "{PYPI_PACKAGE}"', content
    )

    # ensure version is pep440 and correct
    if re.search(r"(?m)^\s*version\s*=", content):
        content = re.sub(
            r'(?m)^\s*version\s*=\s*"[^"]*"\s*$', f'version = "{version}"', content
        )
    else:
        content = re.sub(
            r'(?m)^\s*name\s*=\s*"' + re.escape(PYPI_PACKAGE) + r'"\s*$',
            f'name = "{PYPI_PACKAGE}"\nversion = "{version}"',
            content,
            count=1,
        )

    # remove dynamic version if present
    content = re.sub(
        r"(?m)^\s*dynamic\s*=\s*\[(.*?)\]\s*$",
        lambda m: "dynamic = ["
        + ", ".join(
            [
                x
                for x in (i.strip() for i in m.group(1).split(","))
                if x.strip("\"' ") != "version"
            ]
        )
        + "]",
        content,
    )

    # ensure [tool.maturin] header is a proper line
    content = re.sub(r"(?m)^\[tool\.maturin\](?=\S)", "[tool.maturin]\n", content)

    # enforce module-name regorus (no hyphen)
    if re.search(r"(?m)^\[tool\.maturin\]\s*$", content):
        if re.search(r"(?m)^\s*module-name\s*=", content):
            content = re.sub(
                r'(?m)^\s*module-name\s*=\s*"[^"]*"\s*$',
                'module-name = "regorus"',
                content,
            )
        else:
            content = re.sub(
                r"(?m)^\[tool\.maturin\]\s*$",
                '[tool.maturin]\nmodule-name = "regorus"',
                content,
                count=1,
            )
    else:
        content = content.rstrip() + '\n\n[tool.maturin]\nmodule-name = "regorus"\n'

    if dist_readme.exists():
        content = content.replace("[project]", '[project]\nreadme = "README.md"')

    path.write_text(content, encoding="utf-8")
    print(f"[INFO] Updated upstream pyproject.toml for {PYPI_PACKAGE} v{version}")


def _get_pyi_bytes(tag: str, py_bindings: Path) -> bytes:
    stub_pyi = stub_dir / f"{tag}.pyi"
    if stub_pyi.exists():
        print(f"[INFO] Using stub from {stub_pyi}")
        return stub_pyi.read_bytes()
    lib_rs = py_bindings / "src" / "lib.rs"
    print(f"[WARNING] No stub found for {tag}, generating from {lib_rs}")
    if not lib_rs.exists():
        raise RuntimeError(f"Cannot find upstream lib.rs at {lib_rs}")
    return generate_regorus_pyi_from_lib_rs(lib_rs)


def clone_and_prepare(
    tag: str,
    prepare_dir: Path,
    force: bool = False,
    fixed_post_ts: Optional[str] = None,
    existing_pypi_version: Optional[str] = None,
) -> Path:
    """Clone upstream and patch pyproject.toml but don't run maturin.
    Returns the path to bindings/python so the caller (e.g. maturin-action) can build it."""
    repo_dir = prepare_dir / "regorus"
    print(f"[INFO] Cloning {REGORUS_REPO} at tag {tag}...")
    subprocess.run(
        [
            "git", "clone", "--depth", "1", "--branch", tag,
            f"https://github.com/{REGORUS_REPO}.git",
            str(repo_dir),
        ],
        check=True,
    )

    py_bindings = repo_dir / "bindings" / "python"
    if not py_bindings.exists():
        raise RuntimeError(f"Python bindings not found at {py_bindings}")

    pyproject = py_bindings / "pyproject.toml"
    if pyproject.exists():
        update_pyproject_toml(
            pyproject,
            tag,
            force,
            fixed_post_ts=fixed_post_ts,
            existing_pypi_version=existing_pypi_version,
        )

    if dist_readme.exists():
        shutil.copy(dist_readme, py_bindings / "README.md")

    print(f"[INFO] Source ready at: {py_bindings}")
    return py_bindings


def clone_and_build(
    tag: str,
    output_dir: Path,
    dry_run: bool = False,
    force: bool = False,
    rust_target: Optional[str] = None,
    fixed_post_ts: Optional[str] = None,
    existing_pypi_version: Optional[str] = None,
) -> Optional[Path]:
    if dry_run:
        print(f"[DRY-RUN] Would clone and build tag: {tag}")
        return None

    with tempfile.TemporaryDirectory() as tmp:
        py_bindings = clone_and_prepare(
            tag=tag,
            prepare_dir=Path(tmp),
            force=force,
            fixed_post_ts=fixed_post_ts,
            existing_pypi_version=existing_pypi_version,
        )

        print("[INFO] Building wheel with maturin...")
        maturin_cmd = ["maturin", "build", "--release"]
        if rust_target:
            maturin_cmd += ["--target", rust_target]
            print(f"[INFO] Cross-compiling for target: {rust_target}")
        subprocess.run(maturin_cmd, cwd=py_bindings, check=True)

        wheels_dir = py_bindings / "target" / "wheels"
        wheels = list(wheels_dir.glob("*.whl"))
        if not wheels:
            raise RuntimeError("No wheel files found after build")

        pyi_bytes = _get_pyi_bytes(tag, py_bindings)

        output_dir.mkdir(parents=True, exist_ok=True)
        for w in wheels:
            dest = output_dir / w.name
            shutil.copy2(w, dest)
            inject_typing(dest, pyi_bytes)
            print(f"[INFO] Built typed wheel: {dest.name}")

        return output_dir
