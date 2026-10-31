"""Every model-load check starts a fresh interpreter; no registration helper."""
import os
import struct
import subprocess
import sys
import textwrap
import zlib

import pytest


@pytest.fixture
def resources(tmp_path):
    root = tmp_path / "share"
    model = root / "example" / "models"
    model.mkdir(parents=True)
    other = root / "other"
    other.mkdir()
    (model / "main.xml").write_text('<mujoco><include file="nested/one.xml"/></mujoco>')
    (model / "nested").mkdir()
    (model / "nested" / "one.xml").write_text('<mujoco><include file="two.xml"/></mujoco>')
    (model / "nested" / "two.xml").write_text('<mujoco><worldbody><geom size=".1"/></worldbody></mujoco>')
    (other / "part.xml").write_text('<mujoco><worldbody><geom size=".2"/></worldbody></mujoco>')
    (model / "cross.xml").write_text('<mujoco><include file="package://other/part.xml"/></mujoco>')
    (model / "empty.xml").touch()
    robots = root / "example" / "robots" / "testbot"
    robots.mkdir(parents=True)
    (robots / "robot.xml").write_text('<mujoco><worldbody><geom size=".3"/></worldbody></mujoco>')
    env = os.environ.copy()
    for key in ("AMENT_PREFIX_PATH", "GAZEBO_MODEL_PATH", "GZ_SIM_RESOURCE_PATH",
                "IGN_GAZEBO_RESOURCE_PATH", "ROS_PACKAGE_PATH", "SDF_PATH",
                "RRU_ADDITIONAL_PATHS", "ACTIVE_ROBOT_NAME", "YARP_ROBOT_NAME"):
        env.pop(key, None)
    env.update(RRU_ADDITIONAL_PATHS=str(root), ACTIVE_ROBOT_NAME="testbot")
    return tmp_path, root, model, env


def run(resources, code):
    tmp, _, _, env = resources
    result = subprocess.run([sys.executable, "-c", textwrap.dedent(code)],
                            cwd=tmp, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("scheme", ["package", "model"])
def test_autoload_and_nested_includes(resources, scheme):
    run(resources, f'''
        import mujoco
        m = mujoco.MjModel.from_xml_path("{scheme}://example/models/main.xml")
        assert m.ngeom == 1
    ''')


def test_cross_package_include(resources):
    run(resources, '''
        import mujoco
        assert mujoco.MjModel.from_xml_path("package://example/models/cross.xml").ngeom == 1
    ''')


def test_venv_nested_in_conda(resources):
    tmp, _, _, env = resources
    conda = tmp / "conda"
    venv = conda / "venv"
    for prefix, size in ((conda, ".2"), (venv, ".1")):
        package = prefix / "share" / "nested_env_example"
        package.mkdir(parents=True)
        (package / "shared.xml").write_text(
            f'<mujoco><worldbody><geom size="{size}"/></worldbody></mujoco>')
    (conda / "share" / "nested_env_example" / "conda_only.xml").write_text('<mujoco/>')
    env.pop("RRU_ADDITIONAL_PATHS")
    env.update(VIRTUAL_ENV=str(venv), CONDA_PREFIX=str(conda))
    run(resources, '''
        import mujoco
        model = mujoco.MjModel.from_xml_path("package://nested_env_example/shared.xml")
        assert model.geom_size[0, 0] == .1
        assert mujoco.MjModel.from_xml_path(
            "package://nested_env_example/conda_only.xml").ngeom == 0
    ''')


def test_robot_search_and_working_directory(resources):
    (resources[0] / "local.xml").write_text('<mujoco/>')
    run(resources, '''
        import mujoco
        assert mujoco.MjModel.from_xml_path("robot://robot.xml").ngeom == 1
        assert mujoco.MjModel.from_xml_path("robot://local.xml").ngeom == 0
        try:
            mujoco.MjModel.from_xml_path("robot://../local.xml")
        except ValueError:
            pass
        else:
            raise AssertionError("robot parent traversal accepted")
    ''')


def test_relative_mesh_texture_and_compiler_dirs(resources):
    model = resources[2]
    (model / "meshes").mkdir()
    (model / "textures").mkdir()
    (model / "meshes" / "part.obj").write_text(
        'v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 1 4 3\nf 2 3 4\n')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 2, 2, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(b'\x00' + b'\xff\x00\x00' * 2 + b'\x00' + b'\x00\xff\x00' * 2))
           + chunk(b'IEND', b''))
    (model / "textures" / "color.png").write_bytes(png)
    (model / "assets.xml").write_text('''<mujoco>
      <compiler meshdir="meshes" texturedir="textures"/>
      <asset><mesh name="part" file="part.obj"/>
        <texture name="color" type="2d" file="color.png"/>
        <material name="mat" texture="color"/></asset>
      <worldbody><geom type="mesh" mesh="part" material="mat"/></worldbody>
      </mujoco>''')
    run(resources, '''
        import mujoco
        m = mujoco.MjModel.from_xml_path("package://example/models/assets.xml")
        assert m.nmesh == 1 and m.ntex == 1
        m = mujoco.MjModel.from_xml_string('<mujoco><asset><mesh name="part" file="model://example/models/meshes/part.obj"/></asset><worldbody><geom type="mesh" mesh="part"/></worldbody></mujoco>')
        assert m.nmesh == 1
    ''')


def test_attached_model(resources):
    (resources[2] / "attached.xml").write_text('''<mujoco>
      <asset><model name="other" file="package://other/part.xml"/></asset>
      <worldbody><frame><attach model="other" prefix="other/"/></frame></worldbody>
      </mujoco>''')
    run(resources, '''
        import mujoco
        assert mujoco.MjModel.from_xml_path("package://example/models/attached.xml").ngeom == 1
    ''')


@pytest.mark.parametrize("path", ["missing.xml", "empty.xml", "nested"])
def test_invalid_resources(resources, path):
    run(resources, f'''
        import mujoco
        for _ in range(20):
            try:
                mujoco.MjModel.from_xml_path("package://example/models/{path}")
            except ValueError:
                pass
            else:
                raise AssertionError("invalid resource accepted")
    ''')


def test_repeated_concurrent_loads_and_changed_file(resources):
    run(resources, '''
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        import mujoco
        def load(_):
            return mujoco.MjModel.from_xml_path("package://example/models/main.xml").ngeom
        with ThreadPoolExecutor(max_workers=8) as pool:
            assert list(pool.map(load, range(64))) == [1] * 64
        path = Path("share/example/models/nested/two.xml")
        path.write_text('<mujoco><worldbody><geom size=".1"/><geom size=".2"/></worldbody></mujoco>')
        assert load(0) == 2
    ''')


def test_local_paths_unchanged(resources):
    (resources[2] / "local.xml").write_text('<mujoco><worldbody><geom size=".1"/></worldbody></mujoco>')
    run(resources, '''
        import mujoco
        assert mujoco.MjModel.from_xml_path("share/example/models/local.xml").ngeom == 1
    ''')
