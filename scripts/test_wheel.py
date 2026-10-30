"""Test one wheel across its ABI range in fresh, upstream-only environments."""
import argparse
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import venv
import zipfile

from packaging.requirements import Requirement

repo = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--skip-build", action="store_true")
parser.add_argument("--wheel-dir", type=Path,
                    help="Test an existing wheel from this directory without rebuilding it")
parser.add_argument("--mujoco-version", action="append", help="Override compatible runtime versions to test")
args = parser.parse_args()
project = tomllib.loads((repo / "pyproject.toml").read_text())["project"]
requirement = next(dep for dep in project["dependencies"] if dep.startswith("mujoco"))
# Test one artifact across both provider-symbol families.
versions = args.mujoco_version or ["3.12.0", "3.13.0", "3.14.0", "3.15.0", "3.16.0", "3.17.0"]
incompatible = ["3.11.0"]
# Future upper bounds are packaging policy, not a second native loading path.
assert not Requirement(requirement).specifier.contains("3.18.0")

if not all(Requirement(requirement).specifier.contains(version) for version in versions):
    parser.error("--mujoco-version must satisfy the release's declared dependency range")


def call(*command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


if not args.skip_build and args.wheel_dir is None:
    call(sys.executable, "-m", "build", "--wheel", cwd=repo)
wheel_dir = args.wheel_dir.resolve() if args.wheel_dir else repo / "dist"
wheel = max(wheel_dir.glob(f"mujoco_robotics_uri-{project['version']}-*.whl"),
            key=lambda p: p.stat().st_mtime_ns)
with zipfile.ZipFile(wheel) as archive:
    # Repair tools may add explicit directory entries; inspect payload files.
    names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
    libraries = [n for n in names if n.endswith((".so", ".dylib", ".dll"))]
    assert len(libraries) == 1 and libraries[0].startswith("mujoco/plugin/"), names
    assert "mujoco_robotics_uri" in libraries[0]
    assert all(n.startswith(("mujoco/plugin/", "mujoco_robotics_uri-")) for n in names), names
    metadata = archive.read(next(n for n in names if n.endswith("/METADATA"))).decode()
    requirements = [Requirement(line.removeprefix("Requires-Dist: "))
                    for line in metadata.splitlines() if line.startswith("Requires-Dist: ")]
    assert Requirement(requirement) in requirements, metadata
    record = archive.read(next(n for n in names if n.endswith("/RECORD"))).decode()
    assert libraries[0] in record
    resolver_license = next(n for n in names if n.endswith("/licenses/resolve-robotics-uri-cpp/LICENSE"))
    assert "Redistribution and use" in archive.read(resolver_license).decode()
    assert resolver_license in record
    # A versioned MuJoCo dependency would prevent cross-version autoload even
    # when the callback ABI matches. No runtime may be bundled or directly linked.
    if sys.platform.startswith("linux"):
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / Path(libraries[0]).name
            library.write_bytes(archive.read(libraries[0]))
            dynamic = subprocess.check_output(["readelf", "-d", str(library)], text=True)
            assert not any("NEEDED" in line and "mujoco" in line for line in dynamic.splitlines()), dynamic
    elif sys.platform == "darwin":
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / Path(libraries[0]).name
            library.write_bytes(archive.read(libraries[0]))
            linked = subprocess.check_output(["otool", "-L", str(library)], text=True)
            # The first two lines identify the file and its own install name.
            dependencies = [line.strip().split(" (", 1)[0] for line in linked.splitlines()[2:]]
            assert all(name.startswith(("/usr/lib/", "/System/Library/"))
                       for name in dependencies), linked
    elif sys.platform == "win32":
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / Path(libraries[0]).name
            library.write_bytes(archive.read(libraries[0]))
            imports = subprocess.check_output(["dumpbin", "/DEPENDENTS", str(library)], text=True)
            assert "mujoco.dll" not in imports.lower(), imports
            assert not re.search(r"\b(?:msvcp|vcruntime)\w*\.dll\b", imports, re.I), imports

# Keep substantial installed dependencies off small memory-backed /tmp mounts.
test_dir = repo / "build" / "wheel-tests"
test_dir.mkdir(parents=True, exist_ok=True)
snapshot = '''
import hashlib, json, pathlib, mujoco
root = pathlib.Path(mujoco.__file__).parent
print(json.dumps({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}))
'''
for version in [*versions, *incompatible]:
    supported = version in versions
    print(f"Testing the same wheel with MuJoCo {version} (supported={supported})", flush=True)
    with tempfile.TemporaryDirectory(prefix="mru-wheel-", dir=test_dir) as tmp:
        env = Path(tmp) / "venv"
        venv.create(env, with_pip=True, symlinks=os.name != "nt")
        python = str(env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
        call(python, "-m", "pip", "install", "--only-binary=:all:", f"mujoco=={version}", "pytest")

        def hashes():
            return json.loads(subprocess.check_output([python, "-c", snapshot], text=True))

        original = hashes()
        # Supported versions use ordinary dependency resolution. Incompatible
        # versions deliberately bypass metadata to exercise the native guard.
        flags = [] if supported else ["--no-deps"]
        call(python, "-m", "pip", "install", *flags, str(wheel))
        installed = hashes()
        assert all(installed[name] == digest for name, digest in original.items())
        assert len(set(installed) - set(original)) == 1
        if supported:
            # This suite compiles package://example/models/main.xml with nested
            # includes, plus URI-backed meshes/textures, in fresh interpreters.
            # Only normal `import mujoco` loads the installed wheel's provider.
            call(python, "-m", "pytest", str(repo / "tests"), "-v", cwd=tmp)
        else:
            guard = subprocess.run([python, "-c", '''
import ctypes, pathlib, mujoco
root = pathlib.Path(mujoco.__file__).parent
library = next(p for p in root.iterdir() if p.name.startswith(('libmujoco.', 'mujoco.dll')))
runtime = ctypes.CDLL(str(library))
lookup = getattr(runtime, 'mjp_findProvider', None) or runtime.mjp_getResourceProvider
lookup.argtypes = [ctypes.c_char_p]
lookup.restype = ctypes.c_void_p
for scheme in (b'package://', b'model://', b'robot://'):
    assert not lookup(scheme), scheme
'''], capture_output=True, text=True, cwd=tmp)
            assert guard.returncode == 0, guard.stdout + guard.stderr
            assert "incompatible MuJoCo runtime" in guard.stderr, guard.stderr
        call(python, "-m", "pip", "uninstall", "-y", "mujoco-robotics-uri")
        assert hashes() == original, "Uninstall changed MuJoCo-owned files"
print("Wheel ABI matrix, minimum-version guard, autoload, licenses, and uninstall ownership verified.")
