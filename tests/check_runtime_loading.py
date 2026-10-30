"""Exercise loader failures in fresh processes, without importing real MuJoCo."""
import os
from pathlib import Path
import subprocess
import sys

plugin, runtime = map(lambda arg: str(Path(arg).resolve()), sys.argv[1:])
for version, diagnostic in [
    (None, "no loaded MuJoCo shared runtime found"),
    (3011000, "incompatible MuJoCo runtime"),
    (3012000, "missing required provider symbols"),
    (3016000, "missing required provider symbols"),
]:
    code = "import ctypes, sys\n"
    if version is not None:
        code += "runtime = ctypes.CDLL(sys.argv[2], mode=ctypes.RTLD_LOCAL)\n"
    code += "plugin = ctypes.CDLL(sys.argv[1])\n"
    env = dict(os.environ, MRU_TEST_RUNTIME_VERSION=str(version))
    result = subprocess.run([sys.executable, "-c", code, plugin, runtime],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert diagnostic in result.stderr, result.stdout + result.stderr
