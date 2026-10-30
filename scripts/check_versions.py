"""Check that all distributions use the same plugin release version (Python >=3.11)."""
import argparse
from pathlib import Path
import re
import sys
import tomllib


def check_versions(root: Path) -> str:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    # The release version is deliberately a literal in the top-level project().
    cmake = re.sub(r"#[^\n]*", "", cmake)
    match = re.search(
        r"\bproject\s*\(\s*mujoco_robotics_uri\s+VERSION\s+"
        r"([0-9]+(?:\.[0-9]+){0,3})(?=\s|\))",
        cmake,
        re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Cannot find a literal VERSION in CMakeLists.txt project()")
    versions = {
        "pyproject.toml [project].version": pyproject["project"]["version"],
        "pixi.toml [package].version": pixi["package"]["version"],
        "CMakeLists.txt project(VERSION)": match.group(1),
    }
    if len(set(versions.values())) != 1:
        details = "\n".join(f"  {location}: {version}" for location, version in versions.items())
        raise ValueError(f"Plugin release versions must match:\n{details}")
    return match.group(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Require the release tag to equal v<plugin version>")
    args = parser.parse_args()
    try:
        version = check_versions(Path(__file__).resolve().parents[1])
    except (OSError, KeyError, ValueError) as error:
        sys.exit(str(error))
    if args.tag is not None and args.tag != f"v{version}":
        sys.exit(f"Release tag {args.tag!r} must match plugin version: v{version}")
    print(f"Plugin release versions match: {version}")
