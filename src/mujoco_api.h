// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#ifndef MRU_MUJOCO_API_H_
#define MRU_MUJOCO_API_H_

#include <mujoco/mjplugin.h>
#include <mujoco/mujoco.h>

// Describe function pointers using the available headers. Runtime dispatch
// selects symbol names from mj_version(), independently of these aliases.
#if mjVERSION_HEADER < 3016000
#define MRU_DEFAULT_PROVIDER mjp_defaultResourceProvider
#define MRU_REGISTER_PROVIDER mjp_registerResourceProvider
#define MRU_FIND_PROVIDER mjp_getResourceProvider
#else
#define MRU_DEFAULT_PROVIDER mjp_defaultProvider
#define MRU_REGISTER_PROVIDER mjp_registerProvider
#define MRU_FIND_PROVIDER mjp_findProvider
#endif

namespace mru
{
struct MuJoCoApi
{
    decltype(&mj_version) version = nullptr;
    decltype(&mj_versionString) version_string = nullptr;
    decltype(&MRU_DEFAULT_PROVIDER) default_provider = nullptr;
    decltype(&MRU_REGISTER_PROVIDER) register_provider = nullptr;
    decltype(&MRU_FIND_PROVIDER) find_provider = nullptr;

    // Validate the runtime before resolving or calling provider functions.
    bool Initialize();
};
extern MuJoCoApi api;
} // namespace mru
#endif
