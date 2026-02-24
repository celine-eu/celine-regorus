from __future__ import annotations
import argparse, os
from pathlib import Path

from .build import PYPI_PACKAGE, clone_and_build
from .github import fetch_all_github_tags, fetch_latest_github_tag
from .pypi import fetch_pypi_version
from .versions import is_newer, tag_to_version


def needs_build(github_tag: str, pypi_version: str | None) -> bool:
    if not pypi_version:
        print("[INFO] PyPI has no version (project missing or empty) -> build needed")
        return True
    if is_newer(github_tag, pypi_version):
        print(f"[INFO] New version: GitHub {github_tag} > PyPI {pypi_version}")
        return True
    print(f"[INFO] PyPI up to date: {pypi_version}")
    return False


def _write_outputs(should_build: bool, tag: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"should_build={'true' if should_build else 'false'}\n")
        f.write(f"tag={tag}\n")
        f.write(f"version={tag_to_version(tag)}\n")


def main() -> int:
    p = argparse.ArgumentParser(
        description="Build celine-regorus from microsoft/regorus releases"
    )
    p.add_argument("--check-only", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--tag", type=str, help="Upstream tag to build (e.g. v0.5.0 or regorus-v0.5.0)")
    p.add_argument("--output-dir", type=Path, default=Path("dist"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--list-tags", action="store_true")
    p.add_argument("--rust-target", type=str, default=None,
                   help="Rust target triple to pass to maturin (e.g. aarch64-apple-darwin)")
    p.add_argument("--prepare-only", action="store_true",
                   help="Clone and patch upstream source but skip maturin build")
    p.add_argument("--prepare-dir", type=Path, default=Path("/tmp/regorus-src"),
                   help="Where to clone upstream when using --prepare-only")

    p.add_argument("--post-ts", type=str, default=None,
                help="Fixed post-release timestamp (YYYYmmddHHMMSS) to use across all platform builds")

    args = p.parse_args()

    if args.list_tags:
        for t in fetch_all_github_tags():
            print(t)
        return 0

    github_tag = args.tag or fetch_latest_github_tag()
    if not github_tag:
        print("[ERROR] Could not determine latest tag")
        return 1

    pypi_version = fetch_pypi_version(PYPI_PACKAGE)
    should_build = bool(args.force) or needs_build(github_tag, pypi_version)

    if args.check_only:
        _write_outputs(should_build, github_tag)
        return 0

    if args.prepare_only:
        from .build import clone_and_prepare
        bindings_path = clone_and_prepare(
            github_tag,
            args.prepare_dir,
            force=bool(args.force),
            fixed_post_ts=args.post_ts,
        )
        print(f"[INFO] Source prepared at: {bindings_path}")
        _write_outputs(True, github_tag)
        return 0

    if not should_build:
        print("[INFO] No build needed")
        return 0

    try:
        clone_and_build(
            github_tag,
            args.output_dir,
            dry_run=args.dry_run,
            force=bool(args.force),
            rust_target=args.rust_target,
            fixed_post_ts=args.post_ts,  # ← correct
        )
        print("[SUCCESS] Build completed")
        _write_outputs(True, github_tag)
        return 0
    except Exception as e:
        print(f"[ERROR] Build failed: {e}")
        return 1
