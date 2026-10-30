# mujoco-robotics-uri

MuJoCo resource provider for `package://`, `model://`, and `robot://` URIs,
powered by [resolve-robotics-uri-cpp](https://github.com/gbionics/resolve-robotics-uri-cpp).

Install it, then use MuJoCo python bindings or `simulate`/`mujoco-simulate` normally. For C/C++ users of MuJoCo, see [`docs/use-from-cxx.md`](docs/use-from-cxx.md).

The package requires mujoco at least 3.12, if you need compatibility for an earlier version of mujoco, please [open an issue](https://github.com/gbionics/mujoco-robotics-uri/issues/new).

### Installation

#### conda-forge (C++ and Python)

Install it with pixi or conda:

```sh
pixi add mujoco-robotics-uri
```

or

```sh
conda create -n mrienv -c conda-forge mujoco-robotics-uri
```

To depend on the source with Pixi, add this to your `pixi.toml`:

```toml
[workspace]
preview = ["pixi-build"]

[dependencies]
mujoco-robotics-uri = { git = "https://github.com/gbionics/mujoco-robotics-uri.git" }
```

#### PyPI (Python only)

Install it with uv or pip:

```sh
uv add mujoco-robotics-uri
```

or

```sh
python -m pip install mujoco-robotics-uri
```

### Usage

Once you installed in the same environment in which `mujoco` is installed, you can use to resolve `package://`, `model://` or `robot://` URIs according, in any place were MuJoCo expects a file, for example:

```python
import mujoco
model = mujoco.MjModel.from_xml_path("package://my_robot/models/robot.xml")
```

or include an MJCF file from a package:

```xml
<mujoco>
  <include file="package://my_robot/models/world.xml"/>
</mujoco>
```

Load a mesh from `gb-robot-models`:

```xml
<mujoco>
  <asset>
    <mesh name="head" file="package://gb_robot_models/meshes/sim_gene01_head.obj"/>
  </asset>
  <worldbody>
    <geom type="mesh" mesh="head"/>
  </worldbody>
</mujoco>
```
