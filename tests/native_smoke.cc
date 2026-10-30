// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#include "mujoco_api.h"
#include <climits>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>

#define CHECK(x)                                                            \
    do                                                                      \
    {                                                                       \
        if (!(x))                                                           \
        {                                                                   \
            std::fprintf(stderr, "check failed at %d: %s\n", __LINE__, #x); \
            return 1;                                                       \
        }                                                                   \
    } while (0)

int ConflictOpen(mjResource*)
{
    return 0;
}
int ConflictRead(mjResource*, const void**)
{
    return -1;
}
void ConflictClose(mjResource*)
{
}

int main(int argc, char** argv)
{
    CHECK(argc >= 2);
    const bool conflict = argc > 2 && std::string(argv[2]) == "conflict";
    if (conflict)
    {
        mjpResourceProvider provider;
        MRU_DEFAULT_PROVIDER(&provider);
        provider.prefix = "package";
        provider.open = ConflictOpen;
        provider.read = ConflictRead;
        provider.close = ConflictClose;
        CHECK(MRU_REGISTER_PROVIDER(&provider) > 0);
    }
    mj_loadPluginLibrary(argv[1]);
    mj_loadPluginLibrary(argv[1]); // Repeated library load must preserve providers.
    const auto* package = MRU_FIND_PROVIDER("package://example/file");
    CHECK(package);
    CHECK(MRU_FIND_PROVIDER("model://example/file"));
    const auto* robot = MRU_FIND_PROVIDER("robot://file");
    CHECK(robot);
    if (conflict)
    {
        CHECK(package->open == ConflictOpen);
        return 0;
    }
    const auto dir = std::filesystem::current_path() / "native-resource-test";
    std::filesystem::create_directories(dir);
    const auto file = dir / "bytes.bin";
    {
        std::ofstream out(file, std::ios::binary);
        out << "abc";
    }
    std::string uri = "robot://native-resource-test/bytes.bin";
    mjResource resource{};
    resource.name = uri.data();
    CHECK(robot->open(&resource));
    const void* buffer = nullptr;
    CHECK(robot->read(&resource, &buffer) == 3);
    CHECK(buffer && std::memcmp(buffer, "abc", 3) == 0);
    robot->close(&resource);
    CHECK(!resource.data);
    {
        std::ofstream out(file, std::ios::binary | std::ios::trunc);
    }
    CHECK(robot->open(&resource));
    CHECK(robot->read(&resource, &buffer) == 0 && buffer);
    robot->close(&resource);
    std::filesystem::remove(file);
    for (int i = 0; i < 1000; ++i)
    {
        CHECK(!robot->open(&resource));
        CHECK(!resource.data);
    }
    uri = "robot://native-resource-test";
    resource.name = uri.data();
    CHECK(!robot->open(&resource)); // Directories are not resources.
    // Sparse files exercise the size limit without allocating INT_MAX bytes.
    {
        std::ofstream out(file, std::ios::binary);
        out.put('x');
    }
    std::error_code ec;
    std::filesystem::resize_file(file, static_cast<std::uintmax_t>(INT_MAX) + 1, ec);
    if (!ec)
    {
        uri = "robot://native-resource-test/bytes.bin";
        resource.name = uri.data();
        CHECK(!robot->open(&resource));
        CHECK(!resource.data);
    }
    std::filesystem::remove_all(dir);
    return 0;
}
