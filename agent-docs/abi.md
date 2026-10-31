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
uses headers whose resource layouts and relevant function signatures match all
six reviewed releases: pinned 3.12.0 for wheels, installed 3.12–3.17 for native builds. Compile-time API aliases remain for
function-pointer declarations and native tests using their installed headers;
they do not select the symbols used by the provider at runtime.

Sources:

- [MuJoCo 3.12.0 release notes](https://github.com/google-deepmind/mujoco/releases/tag/3.12.0)
- [MuJoCo 3.14.0 release notes](https://github.com/google-deepmind/mujoco/releases/tag/3.14.0)
- [3.16 function-renaming commit](https://github.com/google-deepmind/mujoco/commit/2757493d9b3b83a86eb6c426fd7d6b59dfe8dfc5)
- Tagged provider headers: [3.12](https://github.com/google-deepmind/mujoco/blob/3.12.0/include/mujoco/mjplugin.h), [3.13](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mjplugin.h), [3.14](https://github.com/google-deepmind/mujoco/blob/3.14.0/include/mujoco/mjplugin.h), [3.15](https://github.com/google-deepmind/mujoco/blob/3.15.0/include/mujoco/mjplugin.h), [3.16](https://github.com/google-deepmind/mujoco/blob/3.16.0/include/mujoco/mjplugin.h), [3.17](https://github.com/google-deepmind/mujoco/blob/3.17.0/include/mujoco/mjplugin.h)
- Tagged exported API headers: [3.12](https://github.com/google-deepmind/mujoco/blob/3.12.0/include/mujoco/mujoco.h), [3.13](https://github.com/google-deepmind/mujoco/blob/3.13.0/include/mujoco/mujoco.h), [3.14](https://github.com/google-deepmind/mujoco/blob/3.14.0/include/mujoco/mujoco.h), [3.15](https://github.com/google-deepmind/mujoco/blob/3.15.0/include/mujoco/mujoco.h), [3.16](https://github.com/google-deepmind/mujoco/blob/3.16.0/include/mujoco/mujoco.h), [3.17](https://github.com/google-deepmind/mujoco/blob/3.17.0/include/mujoco/mujoco.h)

## Common native and wheel binary

Wheels compile against **3.12.0 headers**; native builds use installed, reviewed
**3.12–3.17 headers**. Both dynamically resolve the same five functions. There is no direct link, SONAME dependency, Windows
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

Native builds use `find_package(mujoco 3.12 CONFIG REQUIRED)` and take include
paths from `mujoco::mujoco` without linking the provider to that target. A
compile-time check rejects headers outside the reviewed 3.12–3.17 interval.
There is no MuJoCo header download or source-directory override. An installed
MuJoCo development package is required even with `BUILD_TESTING=OFF`; Python
and integration-test linkage are required only when tests are enabled.

Wheel builds retain their isolated `mujoco==3.12.0` build dependency and exact
baseline check. The Pixi wheel environment contains tools only. No MuJoCo
headers are installed by this project.

## Conda-forge: headers at build time, dynamic runtime dependency

The external feedstock now needs a reviewed `libmujoco >=3.12,<3.18` host
dependency for headers and should retain **`libmujoco >=3.12`** at runtime.
The recipe remains external and has not been updated here. Host-package run
exports must not inadvertently replace the intended dynamic runtime policy. No MuJoCo ABI migration or rebuild for
each engine release is required by this provider's current dynamic interface.
The CMake install remains `<prefix>/bin/mujoco_plugin`, configurable through
`MRU_PLUGIN_INSTALL_DIR` (`<environment>/Library/bin/mujoco_plugin` on Windows).
No conda recipe belongs in this repository.

The root Pixi source package uses `pixi-build-rattler-build` with the same CMake
install and runtime policy. `pixi-recipe.yaml` loads package metadata from
`pixi.toml` and declares the build, host, and run dependencies. Its host
dependencies include the packaged resolver and `libmujoco >=3.12,<3.18` for
installed headers. `requirements.ignore_run_exports.from_package: [libmujoco]`
keeps MuJoCo's narrow host run export out of the package, preserving the explicit
`libmujoco >=3.12` runtime requirement. Compiler runtime exports remain enabled.
This supersedes the temporary narrower metadata produced by `pixi-build-cmake`.
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
| 0.1.2 (prepared) | 3.12.0 | `mujoco>=3.12,<3.18` |

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
runtime, and a locally loaded fake runtime lacking provider symbols. Verify that
a native packaging build uses installed headers with tests disabled and has no
MuJoCo shared-library dependency.
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

The first GitHub Actions run executed Linux x86-64 and AArch64 native/source
checks successfully. It exposed test portability issues: repaired wheels contain
ZIP directory entries, macOS temporary paths can use the `/var` alias, and the
Windows native smoke target needs explicit C++17. These checks now inspect only
archive files, resolve the temporary test root, and request C++17 respectively.
The MuJoCo 3.12 Windows wheel also stores its headers under
`mujoco/include/mujoco/mujoco/`; CMake locates the actual include root from the
two published layouts instead of assuming the Unix layout.

The initial macOS ARM64 wheel job completed the full six-runtime matrix and
3.11 rejection checks successfully. Follow-up fixes were checked locally with
the native suite, a wheel repacked with explicit directory entries, and an
isolated wheel build; corrected Windows/manylinux jobs are being rerun in CI.

Windows native CI additionally exposed that activation environment values use
Windows variable expansion: the install-prefix override must be
`%CONDA_PREFIX%/Library`, not `$CONDA_PREFIX/Library`, which was left literal and
installed the plugin outside the environment. The CMake task remains direct and
continues reading `CMAKE_INSTALL_PREFIX` from the activation environment.

CI for commit 0f85ad8 passed the complete six-version wheel matrix on all four
platforms: Linux x86-64, Linux AArch64, macOS ARM64, and Windows x86-64. Native
and source-package checks passed on Linux x86-64/AArch64 and macOS; the Windows
native prefix correction is pending its follow-up CI run.


## Native header discovery change on 2026-10-31

At the user's request, native builds now discover installed MuJoCo headers via
`find_package` instead of fetching 3.12.0 sources. This supersedes the native
header-fetch and no-host-dependency decisions recorded above; historical test
results still describe the artifacts actually tested. Wheel builds retain the
pinned 3.12.0 baseline and existing runtime matrix. Runtime symbol dispatch and
the minimum runtime version are unchanged.

A fresh comparison of tagged `mjplugin.h` files for 3.12.0–3.17.0 found byte-identical
`mjResource`, `mjpResourceProvider`, and initialization macro sections across all
six releases. The macro emits a compiler/platform library constructor; it does
not resolve a MuJoCo initialization function.

Validation on Linux x86-64 with installed conda-forge MuJoCo 3.16.0 headers:
`pixi run --frozen test` passed 12 Python tests and all five CTest checks.
`pixi run --locked -e source test-source` rebuilt the source package with
`BUILD_TESTING=OFF` and passed all 12 consumer tests. Package output contained
only the provider binary plus metadata and licenses; linkage inspection showed
no MuJoCo dependency. The refreshed lock resolves all four platforms; native
builds on other platforms and a fresh wheel matrix were not executed for this
change. The wheel header acquisition and baseline check are unchanged.
The changed C++ source passed clang-format 18 using the temporary upstream
configuration.


## Pixi rattler-build backend change on 2026-10-31

At the user's request, the Pixi source package now uses `pixi-build-rattler-build`
and `pixi-recipe.yaml` to ignore only MuJoCo's host run export. This supersedes
the earlier decision to avoid a local source-package recipe; the conda-forge
feedstock recipe remains external. The recipe uses the existing CMake install
rules with tests disabled and installed MuJoCo headers, and preserves license
metadata through `LICENSES.txt`. Wheels and the runtime loader are unchanged.

Backend configuration follows the [Pixi documentation](https://pixi.prefix.dev/latest/build/backends/pixi-build-rattler-build/);
run-export filtering follows the [rattler-build recipe reference](https://rattler-build.prefix.dev/v0.64.1/reference/recipe_file/#ignore-run-exports).

Validation: `pixi lock` resolved Linux x86-64/AArch64, macOS ARM64, and Windows
x86-64. All four source-package lock entries contain only `libmujoco >=3.12`
for the engine, retaining their platform/compiler runtime requirements. Explicit
build variants preserve the previous Linux 2.28 sysroot, macOS 13.0 deployment
target, and Windows VS 2022 compiler choices.

On Linux x86-64, `pixi run --locked -e source test-source` built the new recipe
and all 12 consumer tests passed with conda-forge MuJoCo 3.16.0. Installed package
metadata confirms `libmujoco >=3.12` without the host's narrow run export. Its
sole payload is `bin/mujoco_plugin/libmujoco_robotics_uri.so`; packaged
`info/licenses/LICENSES.txt` exactly matches the repository's combined notices.
ELF dependencies contain only system/compiler runtime libraries, with no MuJoCo
link. `python3 scripts/check_versions.py` and `git diff --check` passed.
Other platform builds remain CI validation; wheels were not rebuilt for this
backend-only change.


## Plugin 0.1.2 preparation on 2026-10-31

CMake, PyPI, and Pixi now declare plugin version 0.1.2. The Pixi recipe reads
that version from `pixi.toml`; wheel baseline and supported runtime interval
are unchanged. `pixi lock` confirmed the lock remains current for the new
source metadata. `python3 scripts/check_versions.py --tag v0.1.2` passed.
The rebuilt 0.1.2 Linux source package passed all 12 consumer tests and its
installed metadata retains only `libmujoco >=3.12` for MuJoCo. The native 0.1.2
build passed 12 Python tests and all five CTest checks. A fresh wheel matrix
and other-platform builds remain CI checks. No release publication is implied.
