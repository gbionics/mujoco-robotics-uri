// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#include "mujoco_api.h"
#include <ResolveRoboticsURICpp.h>

#include <climits>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <vector>

namespace
{
struct ResourceData
{
    std::vector<char> bytes;
    char empty = 0; // A valid buffer address even for an empty file.
};

int Open(mjResource* resource) noexcept
{
    if (!resource || !resource->name)
        return 0;
    resource->data = nullptr;
    try
    {
        const auto resolved = ResolveRoboticsURICpp::resolveRoboticsURI(resource->name);
        if (!resolved)
            return 0;
        const auto path = std::filesystem::u8path(*resolved);
        if (!std::filesystem::is_regular_file(path))
            return 0;
        std::ifstream stream(path, std::ios::binary | std::ios::ate);
        if (!stream)
            return 0;
        const auto size = stream.tellg();
        if (size < 0 || size > INT_MAX)
            return 0;
        auto data = std::make_unique<ResourceData>();
        data->bytes.resize(static_cast<std::size_t>(size));
        stream.seekg(0);
        if (!stream || (size && !stream.read(data->bytes.data(), size)))
            return 0;
        resource->data = data.release();
        return 1;
    } catch (...)
    {
        return 0;
    }
}

int Read(mjResource* resource, const void** buffer) noexcept
{
    if (!buffer)
        return -1;
    *buffer = nullptr;
    if (!resource || !resource->data)
        return -1;
    const auto& data = *static_cast<ResourceData*>(resource->data);
    *buffer = data.bytes.empty() ? &data.empty : data.bytes.data();
    return static_cast<int>(data.bytes.size());
}

void Close(mjResource* resource) noexcept
{
    if (resource)
    {
        delete static_cast<ResourceData*>(resource->data);
        resource->data = nullptr;
    }
}

void Register(const char* scheme, const char* probe)
{
    if (const auto* existing = mru::api.find_provider(probe))
    {
        if (existing->open != Open || existing->read != Read || existing->close != Close)
        {
            std::fprintf(stderr,
                         "mujoco-robotics-uri: '%s' provider already registered; keeping existing "
                         "provider\n",
                         scheme);
        }
        return;
    }
    mjpResourceProvider provider;
    mru::api.default_provider(&provider);
    provider.prefix = scheme;
    provider.open = Open;
    provider.read = Read;
    provider.close = Close;
    // No modified callback: MuJoCo treats the resource as modified, avoiding stale cache reuse.
    if (mru::api.register_provider(&provider) < 1)
    {
        std::fprintf(stderr, "mujoco-robotics-uri: could not register '%s' provider\n", scheme);
    }
}
} // namespace

mjPLUGIN_LIB_INIT(mujoco_robotics_uri_init)
{
    try
    {
        if (!mru::api.Initialize())
            return;
        Register("package", "package://");
        Register("model", "model://");
        Register("robot", "robot://");
    } catch (...)
    {
        std::fputs("mujoco-robotics-uri: provider initialization failed\n", stderr);
    }
}
