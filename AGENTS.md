# Project decisions

## License placement

License placement belongs to packaging, not the generic CMake installation.
Do not install license files into `share/licenses`, `share/doc`, or other native
prefix locations from the project's CMake install rules, including when the
resolver is fetched with FetchContent.

Keep the project and bundled dependency licenses in binary packages:

- Python wheels use `wheel.license-files` for the project license and the
  wheel-only CMake rule guarded by `MRU_WHEEL AND SKBUILD` for the fetched
  resolver license in the wheel's `.dist-info/licenses` directory.
- Conda license placement belongs to the external feedstock recipe's metadata.

Preserve these packaging mechanisms when changing native install rules.

## Ownership and documentation

The project copyright attribution is **Generative Bionics S.R.L.** Preserve
third-party copyright and license notices unchanged.

Keep `README.md` short and aimed at users: conda/Pixi and PyPI/pip installation,
normal `import mujoco` usage, and two MJCF examples showing package URIs for
includes and meshes, using `gb-robot-models` for the mesh. Omit the Pixi exec and
uv/uvx one-liners at the user's request. Keep development, build, testing,
packaging, and contribution guidance here. Track ABI evidence and release decisions in `agent-docs/abi.md` and
update it whenever compatibility policy or validation changes. Agent-oriented
notes belong in `agent-docs/`; human-facing usage guides belong in `docs/`.

## ABI and release decisions

Read `agent-docs/abi.md` before changing MuJoCo dependencies, provider callbacks,
loader code, runtime guards, or compatibility claims.

- Build every provider against the MuJoCo **3.12.0** header baseline. Native and
  wheel binaries use the same runtime loader and provider implementation, without
  direct MuJoCo imports or a link to `libmujoco`. Select old provider symbols for
  runtime versions 3.12–3.15 and renamed symbols for 3.16+. Validate structs,
  signatures, imported functions, and platform loader dependencies together.
- Conda-forge needs **no `libmujoco` host dependency** or per-MuJoCo ABI migration
  for this provider. The external feedstock declares `libmujoco >=3.12` at run
  time. If a future ABI is incompatible, patch repodata to restrict affected
  builds and update/rebuild the provider as necessary. Repodata changes dependency
  metadata; it cannot repair a binary or an already installed environment.
- PyPI 0.1.0 builds with MuJoCo 3.12.0 and declares `mujoco>=3.12,<3.18`.
  Review/test each new MuJoCo version and publish a new plugin release with an
  updated upper bound. The previous split 0.1.0/0.2.0 symbol-family release plan
  is superseded: one binary supports both families.
- Resolve only an already-loaded **shared** MuJoCo runtime, including runtimes
  loaded locally by Python. Never load or bundle a second engine. Reject versions
  below 3.12 and missing required symbols before registering providers.
- The common runtime loader has no hardcoded upper version bound; distribution
  metadata controls it. Only 3.12–3.17 are reviewed. Successful symbol lookup does
  not prove an unknown future struct layout is safe. Do not claim unconditional
  ABI compatibility with all future MuJoCo versions.
- When extending PyPI compatibility, update `project.dependencies`, the matrix
  and upper-bound assertion in `scripts/test_wheel.py`, and the ABI record
  together. Keep the pinned 3.12.0 headers unless an ABI change requires otherwise.
- Build one wheel and test that exact artifact with every supported runtime
  release (currently 3.12.0 through 3.17.0) and the rejected 3.11.0 runtime.
  Also check the PyPI upper bound in metadata. Do not broaden a range merely
  because compilation succeeds.

## On a new MuJoCo release

1. Read the release notes and compare the new tagged `mjplugin.h` / `mujoco.h`
   with the reviewed versions in `agent-docs/abi.md`. Check `mjResource`,
   `mjpResourceProvider`, callback signatures, all five dynamically resolved
   functions, library names, and automatic plugin discovery. Record the evidence
   and decision there; unchanged structs alone are insufficient.
2. If the provider ABI still matches, retain the **3.12.0 header baseline** and
   existing runtime dispatch. Do not change `build-system.requires`, the CMake
   header archive/hash, or `MRU_WHEEL_MUJOCO_VERSION` merely to follow the newest
   engine. If it breaks, implement and validate the needed runtime adapter or
   restrict compatibility before claiming support.
3. Extend `project.dependencies` in `pyproject.toml` only after review. For a
   compatible 3.18 release, for example, use `mujoco>=3.12,<3.19`. Add the new
   available runtime to `scripts/test_wheel.py` and move its excluded upper-bound
   assertion to the next unreviewed minor. Retain supported older runtimes and
   the rejected lower-bound test. Review patch releases too; an unchanged minor
   constraint does not replace checking for regressions.
4. Run `pixi run -e wheel test-wheel`: build once with PEP 517 isolation and test
   that exact artifact against the complete supported runtime matrix. Run
   `pixi run test` and `pixi run -e source test-source` against the new engine when its
   conda packages are available; use targeted test environments rather than
   changing the minimum runtime requirement. Check dependency imports, autoload,
   package contents/licenses, and uninstall ownership. Require relevant Linux,
   macOS, and Windows CI results before claiming those platforms. Record actual
   results and any unexecuted checks in `agent-docs/abi.md`.
5. Keep the Pixi source package and external feedstock's runtime-only
   `libmujoco >=3.12` policy for compatible engines. No MuJoCo host dependency or
   routine ABI migration is needed. For an incompatible engine, arrange an
   external conda repodata patch restricting affected builds and update the
   provider as needed; metadata patches cannot fix installed binaries. Keep the
   feedstock recipe outside this repository.
6. Before publishing expanded PyPI compatibility, choose a new **plugin** release
   version and set it identically in `pyproject.toml` (`project.version`),
   `pixi.toml` (`package.version`), and `CMakeLists.txt` (`project(... VERSION)`).
   Run `python scripts/check_versions.py` with Python >=3.11; CI gates builds on
   this check. Refresh `pixi.lock` for changed source-package metadata/dependencies
   and rerun affected packaging checks. Publishing is a separate action; new
   metadata does not broaden the dependency range of existing PyPI releases.

## C++ formatting

Follow the [bipedal-locomotion-framework clang-format configuration](https://github.com/gbionics/bipedal-locomotion-framework/blob/master/.clang-format).
Apply it to the existing C++ sources and headers using a temporary configuration
outside the repository. Do not copy or add a `.clang-format` here. The current
code was formatted and checked with clang-format 18 against that configuration.

## Development

Use Pixi for general development. `pixi run build` configures and builds;
`pixi run install` installs into the active environment's native plugin directory;
`pixi run test` runs Python autoload/resource tests and native CTest checks.
Keep the CMake configure command directly in the Pixi task, with
`CMAKE_INSTALL_PREFIX` supplied through activation environment variables.
The native feature defaults to `$CONDA_PREFIX`, with a Windows target override
of `%CONDA_PREFIX%/Library`; keep platform-specific prefix choices in `pixi.toml`
rather than a Python configuration wrapper. All builds resolve their MuJoCo
symbols dynamically; inspect `src/mujoco_api.cc` when auditing dependencies.

The default environment uses conda-forge MuJoCo and the packaged
`libresolve-robotics-uri-cpp`; `pixi.lock` records the resolved versions. The wheel
environment supplies C++ development tools and the Python build/test frontends,
without installing MuJoCo or scikit-build-core. Wheel builds use PEP 517 isolation:
`pyproject.toml` declares scikit-build-core and the exact MuJoCo build baseline
(currently 3.12.0) under `build-system.requires`. Keep the runtime ABI interval
separate under `project.dependencies`. Do not use `--no-isolation` in normal
builds or duplicate the MuJoCo build dependency in the Pixi environment.

Standalone native CMake builds require C++17 and the `ResolveRoboticsURICpp`
CMake package, with no Python or installed MuJoCo build dependency. They fetch
pinned MuJoCo 3.12.0 sources for headers only; `SOURCE_SUBDIR include` selects the
real header directory without configuring/building an engine. This is separate
from the resolver, whose upstream CMake project must be configured normally.
Set `MRU_MUJOCO_INCLUDE_DIR` to an existing 3.12.0 include directory, or
`FETCHCONTENT_SOURCE_DIR_MUJOCO_HEADERS` to an unpacked source tree for offline
builds. Feedstocks can supply the pinned archive as an additional source.
Native integration tests additionally need installed shared MuJoCo and Python;
packaging builds can omit those tests:

```sh
cmake -S . -B build/native -DCMAKE_INSTALL_PREFIX=/your/prefix -DBUILD_TESTING=OFF
cmake --build build/native
cmake --install build/native
```

`MRU_PLUGIN_INSTALL_DIR` overrides `bin/mujoco_plugin`. On Windows, the Pixi
activation environment selects the environment's `Library` prefix. Set
`BUILD_TESTING=OFF` to omit all native integration-test dependencies. Native applications
without discovery must explicitly call MuJoCo's `mj_loadPluginLibrary` before
parsing models. Keep registered libraries loaded for process lifetime.
The temporary native discovery example lives in `tests/loader.h`, which is
exercised by the native tests and linked from `docs/use-from-cxx.md` for downstream
projects to copy. Do not install headers or export CMake helper targets/configs;
the package installs only the provider library. The discovery helper locates the
module containing a MuJoCo symbol, takes the parent of the module's directory,
and appends `bin/mujoco_plugin`. Do not validate module filenames, shared/static
linkage, or directory names, and do not add package-manager-specific path rules.
For directory discovery, a statically linked symbol uses its containing
executable/library module as usual; the URI provider itself requires a loaded
shared MuJoCo runtime. Keep the loader header free of explicit throws and nested `detail`
namespaces: discovery returns an empty path on failure, and the boolean
`loadDefaultMuJoCoPlugins()` returns false on discovery or filesystem failures.
Print an explanatory diagnostic to stderr before every false return from the
loading helper, including the directory and filesystem error when available.
Use filesystem error-code overloads. MuJoCo's void scanning API cannot report
individual library failures; do not imply that true guarantees registration.
Keep this helper native-only; Python wheels retain their existing autoload layout.
Only conda/Pixi installations with shared MuJoCo are supported for C++ use.
`docs/use-from-cxx.md` documents discovery and explicitly supplied directories.
Test discovery from an executable outside a moved prefix and from a symbol
linked into the executable without a shared MuJoCo dependency.

## Pixi source package

The root `pixi.toml` defines a source package using `pixi-build-cmake` and the
`pixi-build` preview feature. Keep its version aligned with CMake and PyPI.
The backend configures, builds, and installs using the existing CMake rules;
`BUILD_TESTING=OFF` keeps MuJoCo and Python out of build/host requirements.
The packaged resolver is a host dependency; `libmujoco >=3.12` is a run dependency
only. Build tools/compilers come from the backend, with CMake >=3.26 required.
Package license metadata uses `license` / `license-file`, without changing the
native CMake install rules. `LICENSES.txt` combines the project `LICENSE` and the
unchanged resolver v0.6.1 license for the package metadata. Keep these notices
aligned when updating either license or the resolver; the project's own `LICENSE`
stays separate. This source package is separate from the external
conda-forge feedstock; do not reintroduce a local conda recipe.

Consumers enable `workspace.preview = ["pixi-build"]` and use a path or Git
source dependency, for example:

```toml
[dependencies]
mujoco-robotics-uri = { path = "../mujoco-robotics-uri" }
# Alternatively, use git = "https://github.com/gbionics/mujoco-robotics-uri.git"
# and optionally rev = "<commit>" to pin the source.
```

`pixi run -e source test-source` installs the package from `{ path = "." }` into a
separate consumer environment and runs the existing resource/autoload tests.
Keep this environment free of the default development feature so a manual
`pixi run install` cannot mask a broken source package. CI runs that task on all
four native platforms: Linux x86-64/AArch64, macOS ARM64, and Windows x86-64. To create a local package artifact without uploading:

```sh
pixi publish --path . --target-dir build/pixi-package
```

CMake FetchContent needs network access for baseline headers unless sources are
provided locally. See the [Pixi CMake backend documentation](https://pixi.prefix.dev/latest/build/backends/pixi-build-cmake/)
for backend configuration. No engine or resolver is vendored into the source.

## Wheels and CI

Pixi supports `linux-64`, `linux-aarch64`, `osx-arm64`, and `win-64`. Keep all
four platforms resolved in `pixi.lock`. Linux AArch64 CI runs natively on
`ubuntu-24.04-arm`, including native CTest, source-package autoload tests, and
the complete wheel runtime matrix. Linux wheels use architecture-matched
`manylinux_2_28_x86_64` / `manylinux_2_28_aarch64` containers and auditwheel tags.
Keep wheel artifact names distinct (`wheels-linux-x86_64` and
`wheels-linux-aarch64`) so the publishing job can download all `wheels-*`.
Auditwheel/patchelf dependencies apply to both Linux platforms. Do not claim
AArch64 execution based only on lock resolution or workflow configuration.


```sh
pixi run -e wheel wheel
pixi run -e wheel test-wheel
pixi run -e wheel python -m build --sdist
```

Wheel builds fetch resolver v0.6.1 with CMake FetchContent using the readable
GitHub release archive URL and its SHA-256 pin. Configure the upstream CMake
project normally, including YCM; do not bypass it using a nonexistent
`SOURCE_SUBDIR` or a hand-built replacement interface target. Native builds use
the packaged resolver by default; `MRU_FETCH_RESOLVER=ON` opts into fetching.

Building a wheel needs network access unless FetchContent sources are available
locally; `-Ccmake.define.FETCHCONTENT_SOURCE_DIR_RESOLVE_ROBOTICS_URI_CPP=/path/to/resolver`
passes a checkout to `python -m build`. YCM may need its own local source override.
The wheel test uses clean virtual environments under `build/wheel-tests`, with
Python symlinks on POSIX to avoid copying interpreters into a small `/tmp`.
It installs dependencies from PyPI. `--skip-build` and repeated
`--mujoco-version VERSION` arguments support targeted investigation; run the
full default matrix for release evidence. `--wheel-dir wheelhouse` validates an
already-built artifact without rebuilding it; CI must test the exact wheel it
uploads.

Keep CI as ordinary isolated `python -m build` jobs. Use the locked Pixi
`wheel-build` environment on all platforms for Python, python-build, packaging,
pip, CMake, and Ninja. On Linux it also supplies auditwheel and patchelf. Install
it with
`prefix-dev/setup-pixi` and `locked: true`, and invoke commands with
`pixi run --locked -e wheel-build`. Do not bootstrap these tools with pip or
`actions/setup-python`. PEP 517 still installs the declared backend and baseline
MuJoCo into an isolated build environment; fresh runtime tests still install
upstream MuJoCo versions from PyPI.

Unlike the local `wheel` development environment, `wheel-build` has no compiler
activation. Linux retains the manylinux compiler for its ABI baseline. macOS
uses Apple Clang to avoid conda activation's library search paths selecting a
conda libc++; this is a runtime-linkage choice, not a requirement to use a
particular Clang distribution. For consistency, Windows also leaves compiler
setup to the runner: msvc-dev-cmd initializes MSVC, with the project's static CRT
setting and import checks. Avoid conda compiler activation in all wheel CI jobs;
this Windows choice is for consistency, not a separate portability requirement. Do not introduce conda C++ runtime
dependencies into PyPI wheels. There is no cibuildwheel or dependency-bundling
requirement for this plugin. Linux release builds run inside the manylinux_2_28
image and use auditwheel to validate/apply a compatible PyPI
tag. No libraries should be grafted into the wheel; the wheel-content checks
reject extra binaries. macOS builds set the deployment target explicitly.
Windows wheel builds link the MSVC C/C++ runtime statically, and CI uses dumpbin
to reject dependencies on MuJoCo or redistributable MSVC runtime DLLs. macOS and
Windows need no repair step. All platforms test the built wheel against the
MuJoCo ABI matrix and upload GitHub artifacts after validation.

Publishing a GitHub release triggers `.github/workflows/build.yml`, which rebuilds
and tests all four platform wheels and the native/source packages. The release
tag must be `v<plugin version>` (for example `v0.1.0`), checked by
`python scripts/check_versions.py --tag v0.1.0`. After all native and wheel jobs
pass, `publish-pypi` downloads those exact `wheels-*` artifacts and uploads them
to PyPI without rebuilding. Push, pull-request, and manual workflow runs only
build/test; they do not publish. This workflow publishes wheels only.

The publisher uses the GitHub environment `pypi`, its configured release-tag and
review rules, and job-scoped `id-token: write` permission. Configure PyPI Trusted
Publishing with owner `gbionics`, repository `mujoco-robotics-uri`, workflow
filename `build.yml`, and environment `pypi`. No PyPI API token or environment
secret is needed. Keep publishing separate from build jobs; only the publishing
job receives OIDC permission. Adding/changing the workflow does not itself
publish a release.

Conda recipes belong in the conda-forge feedstock, not this repository. Do not
add a local `recipe/` directory or recipe build commands here.

Do not publish, retag a local wheel as manylinux, or broaden platform claims on
the strength of configured workflows alone. Inspect packaged contents and shared
library dependencies. No `.pth` hooks, modifications to MuJoCo Python sources,
or explicit registration helpers may be prerequisites for the supported autoload
layouts. Pip-wheel and conda-forge plugin directories differ.

## Resource semantics

Delegate search policy to the resolver; do not reimplement its environment/path
precedence. `robot://` uses default resolver options, rejects parent traversal,
and has no configured default-package fallback. Preserve URI names so includes,
meshes, textures, compiler directories, and attached models remain URI-relative.
URDF path stripping can remove mesh URIs: use `strippath="false"` when necessary.

Read only regular files of at most `INT_MAX` bytes. Each open owns independent
binary data until close, including a valid pointer for empty files. Clean up
failed opens; never let exceptions cross C callbacks or library initialization.
Preserve existing scheme providers with a diagnostic rather than replacing them.
Leave ordinary paths and `file://` handling to MuJoCo. Without a modification
callback, reviewed MuJoCo versions treat resources as modified, avoiding stale
cache reuse; verify this again when changing the supported API range.

## User examples

The example mesh URI is
`package://gb_robot_models/meshes/sim_gene01_head.obj`, from
https://github.com/gbionics/gb-robot-models. Use a mesh example to avoid conflating
resource lookup with full URDF compilation and robot-specific constraints.
The README's installation commands assume package publication; until then,
validate the same XML with a locally installed wheel or native plugin and the
real `gb-robot-models` package. Do not claim a published package exists merely
because a local build passed.
