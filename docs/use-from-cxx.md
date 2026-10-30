# Using mujoco-robotics-uri from C++

## Load the native plugin directory

If you are using MuJoCo from C++, to load any plugin that `simulate`/`mujoco-simulate` uses automically, both the mujoco bundled ones and `mujoco-robotics-uri`, you need to pass **`<install_prefix>/bin/mujoco_plugin`** to [`mj_loadAllPluginLibraries`](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-loadallpluginlibraries) before
loading any models.

Doing that is not supported trivially on MuJoCo versions up to the 3.17.0 . `simulate`/`mujoco-simulate` does that using the location of the `simulate`/`mujoco-simulate` executable itself, but your executable may be placed in a different location, so a more robust method, as long as you are using a shared library version of mujoco, is to find the mujoco path, and reconstruct the **`<install_prefix>/bin/mujoco_plugin`**  path out of it, see for example:

[the loader example in `tests/loader.h`](../tests/loader.h). This is a temporary,
tested example you can copy into your downstream project; the package does not
install any headers or provide a C++ helper target.

After copying it, include `"loader.h"` and call
`mujoco_robotics_uri::loadDefaultMuJoCoPlugins()` before loading models. It
returns `false` and prints an error to stderr if discovery or directory access
fails. MuJoCo's directory-loading API does not report individual library failures.

The example requires C++17. In CMake, link your application to `mujoco::mujoco`
and `${CMAKE_DL_LIBS}`.

## Why the application must manually load plugins

Linking to MuJoCo alone does not make an arbitrary C++ application scan the
plugin directory. MuJoCo's Python package and the `simulate`/`mujoco-simulate` application each
implement their own discovery. This provider registers resource callbacks when
its library is loaded; it does not register an engine plugin, so engine-plugin
counts are not a reliable check. Validate loading by opening a model or asset
through a supported URI.

Related upstream discussions:

- [MuJoCo issue #554: Out-of-the-box use of bundled plugins from pure C/C++](https://github.com/google-deepmind/mujoco/issues/554)
  discusses the distinction between application-driven discovery and linking
  the MuJoCo library.
- [MuJoCo issue #3357: Allow running Simulate with plugin libraries from any folder](https://github.com/google-deepmind/mujoco/issues/3357)
  discusses `simulate`'s executable-relative plugin directory and requests a way
  to load plugins from additional locations. It concerns the application's
  discovery policy, rather than automatic discovery by every C++ consumer.
