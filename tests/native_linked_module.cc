// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#include "loader.h"

#include <cstdio>
#include <filesystem>

// A symbol linked into the executable, without any MuJoCo shared library.
// Directory discovery must accept its containing module like any other module.
extern "C" int mj_version()
{
    return mjVERSION_HEADER;
}

int main(int argc, char** argv)
{
    if (argc != 1)
        return 1;
    try
    {
        const auto expected = (std::filesystem::absolute(argv[0]).parent_path().parent_path()
                               / "bin" / "mujoco_plugin")
                                  .lexically_normal();
        const auto actual = mujoco_robotics_uri::getMuJoCoPluginDirectory();
        if (actual != expected)
        {
            std::fprintf(stderr,
                         "Expected %s, found %s\n",
                         expected.string().c_str(),
                         actual.string().c_str());
            return 1;
        }
    } catch (const std::exception& error)
    {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
    return 0;
}
