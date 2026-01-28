#!/usr/bin/env python3
"""
Build script for celine-regorus.

This script:
1. Checks the latest released tag from the official regorus repository
2. Compares it with the latest version published on PyPI for celine-regorus
3. If a new version is available, clones the repo at that tag and builds the wheel
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError


REGORUS_REPO = "microsoft/regorus"
PYPI_PACKAGE = "celine-regorus"
GITHUB_API = "https://api.github.com"


def get_github_headers() -> dict:
    """Get headers for GitHub API requests."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_latest_github_tag() -> Optional[str]:
    """
    Fetch the latest release tag from the official regorus repository.

    Returns:
        The latest tag name (e.g., 'v0.2.0') or None if not found.
    """
    url = f"{GITHUB_API}/repos/{REGORUS_REPO}/releases/latest"
    req = Request(url, headers=get_github_headers())

    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            tag = data.get("tag_name")
            print(f"[INFO] Latest GitHub release tag: {tag}")
            return tag
    except HTTPError as e:
        if e.code == 404:
            print("[WARN] No releases found, trying tags...")
            return fetch_latest_github_tag_from_tags()
        raise


def fetch_latest_github_tag_from_tags() -> Optional[str]:
    """
    Fallback: fetch latest tag if no releases exist.

    Returns:
        The latest tag name or None if not found.
    """
    url = f"{GITHUB_API}/repos/{REGORUS_REPO}/tags?per_page=100"
    req = Request(url, headers=get_github_headers())

    with urlopen(req, timeout=30) as response:
        tags = json.loads(response.read().decode())

        if not tags:
            print("[ERROR] No tags found in repository")
            return None

        # Sort tags by semantic version (handles v0.0.0 and regorus-v0.0.0 formats)
        version_tags = []
        for tag in tags:
            name = tag["name"]
            match = re.match(r"(?:regorus-)?v?(\d+)\.(\d+)\.(\d+)", name)
            if match:
                version_tags.append(
                    (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                        name,
                    )
                )

        if version_tags:
            version_tags.sort(reverse=True)
            latest = version_tags[0][3]
            print(f"[INFO] Latest tag from tags list: {latest}")
            return latest

        # Fallback to first tag if no semver tags
        return tags[0]["name"]


def fetch_all_github_tags() -> list[str]:
    """
    Fetch all release tags from the official regorus repository.

    Returns:
        List of tag names sorted by semantic version (newest first).
    """
    url = f"{GITHUB_API}/repos/{REGORUS_REPO}/tags?per_page=100"
    req = Request(url, headers=get_github_headers())

    with urlopen(req, timeout=30) as response:
        tags = json.loads(response.read().decode())

        version_tags = []
        for tag in tags:
            name = tag["name"]
            match = re.match(r"(?:regorus-)?v?(\d+)\.(\d+)\.(\d+)", name)
            if match:
                version_tags.append(
                    (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                        name,
                    )
                )

        version_tags.sort(reverse=True)
        return [t[3] for t in version_tags]


def fetch_pypi_version() -> Optional[str]:
    """
    Fetch the latest version of celine-regorus from PyPI.

    Returns:
        The latest version string (e.g., '0.2.0') or None if not published.
    """
    url = f"https://pypi.org/pypi/{PYPI_PACKAGE}/json"

    try:
        with urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            version = data["info"]["version"]
            print(f"[INFO] Latest PyPI version: {version}")
            return version
    except HTTPError as e:
        if e.code == 404:
            print(f"[INFO] Package {PYPI_PACKAGE} not found on PyPI (first release)")
            return None
        raise


def tag_to_version(tag: str) -> str:
    """
    Convert a git tag to a version string.

    Args:
        tag: Git tag (e.g., 'v0.2.0' or 'regorus-v0.5.0')

    Returns:
        Version string (e.g., '0.2.0' or '0.5.0')
    """
    # Handle 'regorus-v0.5.0' format
    if tag.startswith("regorus-v"):
        return tag[len("regorus-v") :]
    # Handle 'regorus-0.5.0' format (without v)
    if tag.startswith("regorus-"):
        return tag[len("regorus-") :]
    # Handle 'v0.5.0' format
    return tag.lstrip("v")


def version_to_tuple(version: str) -> tuple[int, int, int]:
    """Convert version string to comparable tuple."""
    match = re.match(r"(?:regorus-)?v?(\d+)\.(\d+)\.(\d+)", version)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return (0, 0, 0)


def needs_build(github_tag: str, pypi_version: Optional[str]) -> bool:
    """
    Determine if a new build is needed.

    Args:
        github_tag: Latest tag from GitHub
        pypi_version: Latest version from PyPI (or None)

    Returns:
        True if a build is needed, False otherwise.
    """
    github_version = tag_to_version(github_tag)

    if pypi_version is None:
        print(f"[INFO] No PyPI release exists, will build {github_version}")
        return True

    github_tuple = version_to_tuple(github_version)
    pypi_tuple = version_to_tuple(pypi_version)

    if github_tuple > pypi_tuple:
        print(f"[INFO] New version available: {github_version} > {pypi_version}")
        return True

    print(f"[INFO] PyPI is up to date ({pypi_version} >= {github_version})")
    return False


def clone_and_build(
    tag: str, output_dir: Path, dry_run: bool = False
) -> Optional[Path]:
    """
    Clone the regorus repository at a specific tag and build the Python wheel.

    Args:
        tag: Git tag to checkout
        output_dir: Directory to place the built wheel
        dry_run: If True, don't actually build

    Returns:
        Path to the built wheel, or None if dry_run.
    """
    if dry_run:
        print(f"[DRY-RUN] Would clone and build tag: {tag}")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir) / "regorus"

        # Clone the repository at the specific tag
        print(f"[INFO] Cloning regorus at tag {tag}...")
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                tag,
                f"https://github.com/{REGORUS_REPO}.git",
                str(repo_dir),
            ],
            check=True,
        )

        # Navigate to Python bindings directory
        python_bindings = repo_dir / "bindings" / "python"
        if not python_bindings.exists():
            raise RuntimeError(f"Python bindings not found at {python_bindings}")

        # Update pyproject.toml to use our package name
        pyproject_path = python_bindings / "pyproject.toml"
        if pyproject_path.exists():
            update_pyproject_toml(pyproject_path, tag)

        # Build using maturin
        print("[INFO] Building wheel with maturin...")
        subprocess.run(
            ["maturin", "build", "--release"], cwd=python_bindings, check=True
        )

        # Find the built wheel
        wheels_dir = repo_dir / "bindings" / "python" / "target" / "wheels"
        wheels = list(wheels_dir.glob("*.whl"))

        if not wheels:
            raise RuntimeError("No wheel files found after build")

        # Copy wheel to output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        for wheel in wheels:
            dest = output_dir / wheel.name
            shutil.copy2(wheel, dest)
            print(f"[INFO] Built wheel: {dest}")

        return output_dir


def update_pyproject_toml(path: Path, tag: str):
    """
    Update pyproject.toml to use celine-regorus as the package name.

    Note: We keep module-name as 'regorus' to match the PyInit_regorus symbol
    in the compiled Rust library. Users will `pip install celine-regorus` but
    `import regorus`.

    Args:
        path: Path to pyproject.toml
        tag: Git tag for version
    """
    content = path.read_text()
    version = tag_to_version(tag)

    # Update package name (PyPI name can have hyphen)
    content = re.sub(r'name\s*=\s*"regorus"', f'name = "{PYPI_PACKAGE}"', content)

    # Add description if not present
    if "description" not in content:
        content = re.sub(
            rf'name\s*=\s*"{PYPI_PACKAGE}"',
            f'name = "{PYPI_PACKAGE}"\ndescription = "Python bindings for Regorus - a Rego interpreter (unofficial build)"',
            content,
        )

    content = content.replace(
        "[tool.maturin]",
        """

[tool.maturin]
module-name = "regorus"
""",
    )

    path.write_text(content)
    print(f"[INFO] Updated pyproject.toml for {PYPI_PACKAGE} v{version}")


def main():
    parser = argparse.ArgumentParser(
        description="Build celine-regorus from the latest regorus release"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if a new version is available, don't build",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force build even if PyPI is up to date"
    )
    parser.add_argument(
        "--tag", type=str, help="Build a specific tag instead of latest"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Directory to place built wheels (default: dist)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually build, just show what would be done",
    )
    parser.add_argument(
        "--list-tags", action="store_true", help="List all available tags and exit"
    )

    args = parser.parse_args()

    # List tags mode
    if args.list_tags:
        print("[INFO] Fetching all tags...")
        tags = fetch_all_github_tags()
        for tag in tags:
            print(f"  {tag}")
        return 0

    # Fetch versions
    github_tag = args.tag or fetch_latest_github_tag()
    if not github_tag:
        print("[ERROR] Could not determine latest tag")
        return 1

    pypi_version = fetch_pypi_version()

    # Check if build is needed
    should_build = args.force or needs_build(github_tag, pypi_version)

    if args.check_only:
        # Output for GitHub Actions
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"should_build={'true' if should_build else 'false'}\n")
                f.write(f"tag={github_tag}\n")
                f.write(f"version={tag_to_version(github_tag)}\n")
        return 0 if should_build else 0

    if not should_build:
        print("[INFO] No build needed")
        return 0

    # Build
    try:
        clone_and_build(github_tag, args.output_dir, dry_run=args.dry_run)
        print("[SUCCESS] Build completed")

        # Output for GitHub Actions
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"tag={github_tag}\n")
                f.write(f"version={tag_to_version(github_tag)}\n")

        return 0
    except Exception as e:
        print(f"[ERROR] Build failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
