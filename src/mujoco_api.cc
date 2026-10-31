// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#include "mujoco_api.h"

#include <cstdio>
#include <cstring>
#include <string_view>

static_assert(mjVERSION_HEADER >= 3012000 && mjVERSION_HEADER < 3018000,
              "Build the provider against reviewed MuJoCo 3.12-3.17 headers");

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#else
#include <dlfcn.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#else
#include <link.h>
#endif
#endif

namespace
{
#ifdef _WIN32
HMODULE LoadedMuJoCo()
{
    return GetModuleHandleW(L"mujoco.dll");
}
template <typename Function> Function Symbol(HMODULE module, const char* name)
{
    return reinterpret_cast<Function>(GetProcAddress(module, name));
}
#else
void* OpenLoadedMuJoCo(const char* path) noexcept
{
    if (!path)
        return nullptr;
    const char* basename = std::strrchr(path, '/');
    const std::string_view name(basename ? basename + 1 : path);
#ifdef __APPLE__
    const bool runtime = name == "libmujoco.dylib"
                         || (name.rfind("libmujoco.", 0) == 0 && name.size() >= 6
                             && name.substr(name.size() - 6) == ".dylib");
#else
    const bool runtime = name == "libmujoco.so" || name.rfind("libmujoco.so.", 0) == 0;
#endif
    // Never introduce another runtime. Retain the handle for registered callbacks.
    return runtime ? dlopen(path, RTLD_LAZY | RTLD_NOLOAD) : nullptr;
}

void* LoadedMuJoCo()
{
#ifdef __APPLE__
    // Called during plugin initialization, while dyld serializes library loading.
    for (uint32_t i = 0; i < _dyld_image_count(); ++i)
    {
        if (void* module = OpenLoadedMuJoCo(_dyld_get_image_name(i)))
            return module;
    }
    return nullptr;
#else
    void* module = nullptr;
    dl_iterate_phdr(
        +[](dl_phdr_info* info, size_t, void* result) noexcept {
            void* candidate = OpenLoadedMuJoCo(info->dlpi_name);
            if (!candidate)
                return 0;
            *static_cast<void**>(result) = candidate;
            return 1;
        },
        &module);
    return module;
#endif
}
template <typename Function> Function Symbol(void* module, const char* name)
{
    return reinterpret_cast<Function>(dlsym(module, name));
}
#endif
} // namespace

namespace mru
{
MuJoCoApi api;

bool MuJoCoApi::Initialize()
{
    const auto module = LoadedMuJoCo();
    if (!module)
    {
        std::fputs("mujoco-robotics-uri: no loaded MuJoCo shared runtime found; providers "
                   "disabled\n",
                   stderr);
        return false;
    }
    version = Symbol<decltype(version)>(module, "mj_version");
    version_string = Symbol<decltype(version_string)>(module, "mj_versionString");
    if (!version || !version_string)
    {
        std::fputs("mujoco-robotics-uri: MuJoCo runtime is missing version symbols\n", stderr);
        return false;
    }
    const int runtime_version = version();
    if (runtime_version < 3012000)
    {
        std::fprintf(stderr,
                     "mujoco-robotics-uri: incompatible MuJoCo runtime %s; requires >=3.12; "
                     "providers disabled\n",
                     version_string());
        return false;
    }
    // Provider structs and these function signatures match in 3.12-3.17.
    // Packaging constraints handle future incompatible ABI changes.
    const bool legacy = runtime_version < 3016000;
    default_provider = Symbol<decltype(default_provider)>(module,
                                                          legacy ? "mjp_defaultResourceProvider"
                                                                 : "mjp_defaultProvider");
    register_provider = Symbol<decltype(register_provider)>(module,
                                                            legacy ? "mjp_registerResourceProvider"
                                                                   : "mjp_registerProvider");
    find_provider
        = Symbol<decltype(find_provider)>(module,
                                          legacy ? "mjp_getResourceProvider" : "mjp_findProvider");
    if (!default_provider || !register_provider || !find_provider)
    {
        std::fputs("mujoco-robotics-uri: MuJoCo runtime is missing required provider symbols; "
                   "providers disabled\n",
                   stderr);
        return false;
    }
    return true;
}
} // namespace mru
