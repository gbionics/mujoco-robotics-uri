// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#ifndef MUJOCO_ROBOTICS_URI_LOADER_H
#define MUJOCO_ROBOTICS_URI_LOADER_H

#include <cstdio>
#include <filesystem>
#include <string>
#include <system_error>
#include <vector>

#include <mujoco/mujoco.h>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace mujoco_robotics_uri
{
/// Return the MuJoCo symbol's module path, or an empty path on lookup failure.
inline std::filesystem::path loadedMuJoCoLibrary()
{
#ifdef _WIN32
    HMODULE module = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS
                                | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            reinterpret_cast<LPCWSTR>(&mj_version),
                            &module))
    {
        return {};
    }
    // The path length is not known in advance. GetModuleFileNameW returns the
    // buffer size when truncated, so grow it until the full path fits, including
    // paths beyond MAX_PATH, up to a 32,768-character buffer.
    std::vector<wchar_t> filename(512);
    for (;;)
    {
        const DWORD length
            = GetModuleFileNameW(module, filename.data(), static_cast<DWORD>(filename.size()));
        if (!length)
        {
            return {};
        }
        if (length < filename.size())
        {
            return std::filesystem::path(std::wstring(filename.data(), length));
        }
        if (filename.size() >= 32768)
        {
            return {};
        }
        filename.resize(filename.size() * 2);
    }
#else
    // Look past executable PLT entries for a definition; if none is exported,
    // use the linked symbol's address (including statically linked symbols).
    void* symbol = dlsym(RTLD_NEXT, "mj_version");
    if (!symbol)
    {
        symbol = reinterpret_cast<void*>(&mj_version);
    }
    Dl_info info{};
    if (!dladdr(symbol, &info) || !info.dli_fname)
    {
        return {};
    }
    return std::filesystem::path(info.dli_fname);
#endif
}

/// Locate bin/mujoco_plugin one level above the module's directory; empty on failure.
inline std::filesystem::path getMuJoCoPluginDirectory()
{
    // Keep the symbol linked even with a linker's --as-needed option.
    (void)mj_version();
    const auto module = loadedMuJoCoLibrary();
    if (module.empty())
    {
        return {};
    }
    std::error_code error;
    const auto directory
        = std::filesystem::absolute(module.parent_path().parent_path() / "bin" / "mujoco_plugin",
                                    error);
    // Remove redundant separators and . or .. components without filesystem access
    // or resolving symlinks, preserving the installation path reported by the loader.
    return error ? std::filesystem::path{} : directory.lexically_normal();
}

/// Scan the default plugin folder; false if discovery or directory access fails.
/// MuJoCo's void loading API does not report individual library failures.
inline bool loadDefaultMuJoCoPlugins()
{
    const auto directory = getMuJoCoPluginDirectory();
    std::error_code error;
    if (directory.empty())
    {
        std::fputs("mujoco-robotics-uri: cannot determine the default MuJoCo plugin directory\n",
                   stderr);
        return false;
    }
    if (!std::filesystem::is_directory(directory, error) || error)
    {
        std::fprintf(stderr,
                     "mujoco-robotics-uri: cannot access plugin directory '%s': %s\n",
                     directory.string().c_str(),
                     error ? error.message().c_str() : "not a directory");
        return false;
    }
    // Check directory access before delegating to MuJoCo's void scanning API.
    const std::filesystem::directory_iterator entries(directory, error);
    if (error)
    {
        std::fprintf(stderr,
                     "mujoco-robotics-uri: cannot read plugin directory '%s': %s\n",
                     directory.string().c_str(),
                     error.message().c_str());
        return false;
    }
    const auto path = directory.string();
    mj_loadAllPluginLibraries(path.c_str(), nullptr);
    return true;
}

} // namespace mujoco_robotics_uri
#endif
