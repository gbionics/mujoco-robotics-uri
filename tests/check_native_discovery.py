"""Exercise an external executable against a moved native MuJoCo installation."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

executable, provider, mujoco = map(lambda p: Path(p).resolve(), sys.argv[1:])
with tempfile.TemporaryDirectory(prefix="mru-relocation-") as tmp:
    # macOS's temporary directory may use the /var -> /private/var alias.
    root = Path(tmp).resolve()
    original = root / "original"
    library_dir = original / ("bin" if sys.platform == "win32" else "lib")
    library_dir.mkdir(parents=True)
    library = library_dir / mujoco.name
    shutil.copy2(mujoco, library)
    if sys.platform != "win32":
        # Preserve SONAME/install-name aliases as well as the actual runtime file.
        for alias in mujoco.parent.glob("libmujoco*"):
            if alias.name != mujoco.name and alias.is_file() and alias.resolve() == mujoco:
                shutil.copy2(alias, library_dir / alias.name)
    plugin_dir = original / "bin/mujoco_plugin"
    plugin_dir.mkdir(parents=True)
    shutil.copy2(provider, plugin_dir / provider.name)
    # Move the installation independently of the executable and working directory.
    relocated = root / "relocated"
    original.rename(relocated)
    library = relocated / library.relative_to(original)
    plugin_dir = relocated / "bin/mujoco_plugin"
    external = root / "unrelated executable directory"
    external.mkdir()
    application = external / executable.name
    shutil.copy2(executable, application)
    (external / "model.xml").write_text('<mujoco><worldbody><geom size=".1"/></worldbody></mujoco>')
    env = os.environ.copy()
    # Activation and executable location must not influence directory discovery.
    env["CONDA_PREFIX"] = str(root / "wrong environment")
    env["VIRTUAL_ENV"] = str(root / "wrong venv")
    if sys.platform == "win32":
        env["PATH"] = str(library.parent) + os.pathsep + env.get("PATH", "")
    elif sys.platform == "darwin":
        env["DYLD_LIBRARY_PATH"] = str(library.parent)
    else:
        # Override compiler-injected development RPATHs so the copied runtime,
        # not the original Pixi runtime with the same SONAME, is selected.
        env["LD_PRELOAD"] = str(library)
    subprocess.run([str(application), str(plugin_dir)], cwd=external, env=env, check=True)
    plugin_dir.rename(plugin_dir.with_name("plugins temporarily removed"))
    missing = subprocess.run([str(application), str(plugin_dir), "missing"],
                             cwd=external, env=env, check=True, capture_output=True, text=True)
    assert str(plugin_dir) in missing.stderr, missing.stderr
    print("Relocated library discovery, external executable, model loading, and missing-directory handling passed.")
