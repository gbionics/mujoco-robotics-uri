# MuJoCo ABI compatibility policy

This document records the evidence and release decisions behind compatibility
claims. Source compatibility, provider ABI compatibility, platform binary
compatibility, and package-manager dependency constraints are separate concerns.
A matching struct layout alone does not establish binary compatibility.

## Resource-provider changes in MuJoCo >=3.12

Inspection of the tagged `mjplugin.h` and `mujoco.h` headers confirms that
`mjpResourceProvider` and its callback signatures are unchanged across these
releases. Only the resource-provider interface is covered by this finding;
other MuJoCo APIs and structs can change independently.

| MuJoCo release | Relevant change |
| --- | --- |
| 3.12.0 | Appended `const char* args` to `mjResource`, increasing its size while retaining the offsets of earlier fields. This is the earliest supported source version. |
| 3.13.0 | No resource-provider ABI change. |
| 3.14.0 | Added archive-provider registration and lookup using the existing provider interface. This was additive; this plugin does not use the archive functions. |
| 3.15.0 | No resource-provider ABI change. |
| 3.16.0 | Renamed exported provider functions and removed the old names. This breaks plugins that import the old symbols, despite unchanged provider structs. |
| 3.17.0 | No further resource-provider ABI change relative to 3.16. |

The functions used by this plugin are:

| MuJoCo 3.12–3.15 | MuJoCo >=3.16 |
| --- | --- |
| `mjp_defaultResourceProvider` | `mjp_defaultProvider` |
| `mjp_registerResourceProvider` | `mjp_registerProvider` |
| `mjp_getResourceProvider` | `mjp_findProvider` |

The plugin also uses the unchanged `mj_version` and `mj_versionString` functions.
The runtime loader selects the provider names using `mj_version()`. It always
compiles against 3.12.0 headers, whose resource layouts and relevant function
signatures match all six reviewed releases. Compile-time API aliases remain for
function-pointer declarations and native tests using their installed headers;
they do not select the symbols used by the provider at runtime.

Sources:

- [MuJoCo 3.12.0 release notes](https://github.com/google-deepmind/mujoco/releases/tag/3.12.0)
- [MuJoCo 3.14.0 release notes](https://github.com/google-deepmind/mujoco/releases/tag/3.14.0)
- [3.16 function-renaming commit](https://github.com/google-deepmind/mujoco/commit/2757493d9b3b83a86eb6c426fd7d6b59dfe8dfc5)
- Tagged provider headers: [3.12](https://github.com/google-deepmind/mujoco/blob/3.12.0/include/mujoco/mjplugin.h), [3.13](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mjplugin.h), [3.14](https://github.com/google-deepmind/mujoco/blob/3.14.0/include/mujoco/mjplugin.h), [3.15](https://github.com/google-deepmind/mujoco/blob/3.15.0/include/mujoco/mjplugin.h), [3.16](https://github.com/google-deepmind/mujoco/blob/3.16.0/include/mujoco/mjplugin.h), [3.17](https://github.com/google-deepmind/mujoco/blob/3.17.0/include/mujoco/mjplugin.h)
- Tagged exported API headers: [3.12](https://github.com/google-deepmind/mujoco/blob/3.12.0/include/mujoco/mujoco.h), [3.13](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mujoco.h), [3.14](https://github.com/google-deepmind/mujoco/blob/3.14.0/include/mujoco/mujoco.h), [3.15](https://github.com/google-deepmind/mujoco/blob/3.15.0/include/mujoco/mujoco.h), [3.16](https://github.com/google-deepmind/mujoco/blob/3.16.0/include/mujoco/mujoco.h), [3.17](https://github.com/google-deepmind/mujoco/blob/3.17.0/include/mujoco/mujoco.h)

## Common native and wheel binary

Both distributions compile against the **3.12.0 headers** and dynamically resolve
the same five functions. There is no direct link, SONAME dependency, Windows
import-library dependency, or unresolved import for MuJoCo. This avoids the
versioned SONAME/install-name constraint and permits the same binary to register
against either provider-symbol family.

On Linux, `dl_iterate_phdr` locates an already-loaded MuJoCo shared object. On
macOS, dyld's loaded-image list supplies its path. Both use
`dlopen(..., RTLD_NOLOAD)` and `dlsym`, including when Python loaded the engine
with local symbol visibility. Windows uses `GetModuleHandleW` and
`GetProcAddress` on `mujoco.dll`. The loader makes no assumptions about the
plugin's directory relative to the runtime and never loads a second engine.
The host must retain its shared runtime and registered plugin for process
lifetime; using multiple different MuJoCo runtimes in one process is unsupported.

Before registration, reject runtimes older than 3.12 and missing required symbols.
Choose the legacy names below 3.16 and the renamed names from 3.16 onward.
There is no runtime upper bound: **metadata controls the supported interval**.
The reviewed provider layouts cover 3.12–3.17 only. Dynamic function lookup does
not make an unknown future layout compatible; future ABI changes still need
review, dependency restrictions, and potentially code changes.

This decision supersedes the earlier exact-version native linking/migration
policy and the separate 0.1.0 / 0.2.0 PyPI releases for old/new symbol families.

### Build dependencies

Native builds fetch the pinned 3.12.0 source archive for headers only. Its real
`include` directory is selected with FetchContent `SOURCE_SUBDIR include`, so
MuJoCo's engine build is not configured. `MRU_MUJOCO_INCLUDE_DIR` accepts an
existing 3.12.0 include directory; `FETCHCONTENT_SOURCE_DIR_MUJOCO_HEADERS` accepts
an unpacked source tree. An external feedstock can supply this archive as an
additional source for offline builds. No MuJoCo headers are installed by this
project. The resolver still uses its normal upstream CMake project when fetched.

Wheel builds obtain those same baseline headers from the isolated
`mujoco==3.12.0` build dependency. The Pixi wheel environment contains tools only.
`BUILD_TESTING=OFF` allows native packaging without installed MuJoCo or Python;
when enabled, integration test executables use installed shared MuJoCo and Python.

## Conda-forge: runtime-only MuJoCo dependency

The external feedstock should omit `libmujoco` from host requirements and declare
**`libmujoco >=3.12`** in run requirements. No MuJoCo ABI migration or rebuild for
each engine release is required by this provider's current dynamic interface.
The CMake install remains `<prefix>/bin/mujoco_plugin`, configurable through
`MRU_PLUGIN_INSTALL_DIR` (`<environment>/Library/bin/mujoco_plugin` on Windows).
No conda recipe belongs in this repository.

The root Pixi source package uses `pixi-build-cmake` with the same CMake install
and runtime policy. Its sole explicit host dependency is the packaged resolver;
MuJoCo is fetched for baseline headers, not installed as a host dependency.
Consumers can use path/Git source dependencies. The separate `source` environment
installs this package rather than relying on a manual development install.

If a future engine breaks the resource ABI, use a repodata patch to restrict the
runtime requirement of affected builds. Then update the provider and rebuild as
needed. A repodata patch changes solver metadata; it cannot repair binary code
or retroactively change an installed environment. An unbounded requirement is a
packaging policy, not evidence of compatibility with unreviewed future engines.

### Native C++ directory-discovery helper

The temporary `tests/loader.h` example remains available for tests and downstream
copying; it is not installed or exported. It locates the module containing
`mj_version`, takes the parent of its directory, and appends `bin/mujoco_plugin`
for `mj_loadAllPluginLibraries`. Discovery itself accepts executable-contained
symbols without checking shared/static linkage or module names. The URI provider
requires an already-loaded shared runtime. C++ use is supported through the
conda/Pixi installation. See [C++ usage](../docs/use-from-cxx.md).

`loadDefaultMuJoCoPlugins()` returns false with a diagnostic for discovery or
directory-access failures. MuJoCo's void scanning API does not report per-library
success. Different layouts require an explicitly supplied directory.

## PyPI: bounded compatibility per release

| Plugin release | Header build baseline | Wheel `Requires-Dist` |
| --- | --- | --- |
| 0.1.0 | 3.12.0 | `mujoco>=3.12,<3.18` |

One artifact covers both symbol families. This source tree implements the policy;
publication is separate. PyPI has no conda-style repodata patch mechanism, so
review new MuJoCo releases and publish new plugin versions with updated ranges.
Keep the 3.12.0 header baseline while it describes the supported provider ABI;
a newer engine alone does not require changing it. If an ABI breaks, implement
an explicit adapter or narrow the new release's range.

The upper bound is enforced by dependency resolution, not a separate wheel-only
runtime guard. Manually bypassing dependencies can run the binary outside its
advertised range; successful symbol lookup alone is not an ABI validation.

Wheels install only their uniquely owned plugin under `mujoco/plugin/`, plus
metadata/licenses. They must not overwrite MuJoCo files, bundle an engine, or add
Python startup hooks. Conda-forge's loader layout is supported through its native
package; pip wheels need not autoload in that layout.

## Validation requirements

Build one wheel and test that exact artifact with MuJoCo **3.12.0, 3.13.0, 3.14.0,
3.15.0, 3.16.0, and 3.17.0** in fresh environments. Test automatic registration
using only `import mujoco`, resource semantics, file ownership, and uninstall.
Install with dependency checks bypassed on 3.11.0 to verify rejection before
registration. Check the `<3.18` wheel metadata rather than inventing an unreleased
runtime for an upper-bound rejection test.

Inspect native and wheel library dependencies for accidental MuJoCo imports.
Native loader failure tests use fresh processes with no runtime, an older fake
runtime, and a locally loaded fake runtime lacking provider symbols. Prove that
a native packaging build works with only headers in the tools-only environment.
Retain native callback/conflict and relocated-directory discovery tests.

CI uses ordinary isolated Python build jobs on Linux x86-64/AArch64, macOS
ARM64, and Windows x86-64. Linux AArch64 uses a native `ubuntu-24.04-arm`
runner and the architecture-matched manylinux_2_28 container, including the same
six-version runtime matrix and source/native tests as x86-64. The `wheel-build` Pixi environment locks Python, the build/test
frontends, CMake, and Ninja on all platforms, plus Linux auditwheel/patchelf.
For consistency Windows also uses this compiler-free environment and initializes
MSVC with msvc-dev-cmd. CI does not bootstrap Python or frontends with pip. Linux retains the manylinux
compiler; macOS avoids conda compiler activation's libc++ search paths. The
Windows wheel statically links its CRT; all platforms retain dependency checks.
PEP 517 backend/header isolation and fresh PyPI runtime test environments remain
enabled. Linux runs in a manylinux_2_28 container and uses auditwheel for
validation/tagging; macOS sets its deployment target to 11.0; Windows statically
links the MSVC runtime and checks DLL imports. No bundling or cibuildwheel is
needed. Pass the exact output artifact to
`scripts/test_wheel.py --wheel-dir wheelhouse` before uploading. Configured jobs
are not executed validation.

## Validation recorded on 2026-10-30

These checks ran on Linux x86-64 with Python 3.12.16:

| Artifact / configuration | Runtime | Result |
| --- | --- | --- |
| One isolated-build 0.1.0 wheel using 3.12.0 headers | PyPI MuJoCo 3.12.0, 3.13.0, 3.14.0, 3.15.0, 3.16.0, 3.17.0 | All 11 resource/autoload tests passed on each runtime: **66 tests** using the same artifact across both symbol families. |
| The same wheel installed with `--no-deps` | PyPI MuJoCo 3.11.0 | Minimum-version diagnostic verified; all three providers remained unregistered. |
| Native build using fetched 3.12.0 headers | conda-forge MuJoCo 3.16.0 | 11 Python tests and all five CTest checks passed, including callback/conflict, relocated-directory discovery, executable-contained-symbol discovery, and loader failures. |
| Native packaging build with `BUILD_TESTING=OFF`, fetched resolver and cached baseline header sources | Pixi tools environment without MuJoCo installed | Configure and build succeeded without a MuJoCo package/library build dependency. |
| Fresh-process loader failures | No runtime; locally loaded stub in another directory reporting 3.11, 3.12, or 3.16 and lacking provider functions | Expected diagnostics verified without crashes or loading another engine. |

Wheel checks verified metadata `mujoco>=3.12,<3.18`, license inclusion, RECORD
ownership, and preservation of MuJoCo-owned files through install/uninstall in
all seven environments. ELF inspection verified that both native builds and the
wheel have no `libmujoco` dependency; the native provider has no undefined
`mj_`/`mjp_` imports. The original header review found identical normalized
resource structs/callback declarations across 3.12.0–3.17.0. Changed C++ files
passed the upstream clang-format 18 configuration.

These results supersede compatibility claims from the former split-ABI
implementation. macOS/Windows CI, manylinux container builds, and feedstock
package builds have not been executed locally. No package publication or
compatibility with unreviewed future MuJoCo ABIs is implied.

Pixi source packaging was also validated locally on Linux: `pixi-build-cmake`
0.4.7 built the CMake install into a `.conda` artifact with one plugin binary
under `bin/mujoco_plugin`. Package metadata includes project/resolver license
notices and `libmujoco >=3.12` plus compiler runtime requirements. No MuJoCo host
package was needed. The independent source-consumer environment passed all 11
resource/autoload tests against conda-forge MuJoCo 3.16.0, including a `--locked`
run. The workflow with source-package tests passed actionlint; macOS and Windows
source builds remain CI checks rather than locally executed evidence.

The Pixi-managed CI frontend was validated with Python 3.12.16, python-build
1.6.1, packaging 26.3, and auditwheel 6.8.2. `wheel-build` installed from the
updated lock file without activating a compiler or installing MuJoCo/backend
packages. A local isolated build using this frontend and the existing development
compiler succeeded, producing a byte-identical plugin to the previously tested
wheel. Targeted runtime tests passed on 3.12.0 and 3.16.0 (22 tests), with 3.11.0
rejection and ownership checks also passing. Workflow lint passed. The manylinux
container and macOS/Windows builds remain to be executed in CI.

Linux AArch64 support was added to all four Pixi environments and resolved in the
lock file. PyPI metadata confirmed CPython 3.12 AArch64 wheels for MuJoCo
3.11.0–3.17.0, covering the baseline, supported matrix, and rejection test.
GitHub Actions now schedules native/source tests and manylinux_2_28 AArch64
wheel builds/tests on `ubuntu-24.04-arm`, with separate Linux artifact names.
Local x86-64 regression checks passed (11 Python tests and five CTest checks).
AArch64 execution is pending CI; lock resolution is not execution evidence.
