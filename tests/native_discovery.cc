// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#include "loader.h"
#include "mujoco_api.h"

#include <cstdio>
#include <filesystem>
#include <string>

int main(int argc, char** argv)
{
    try
    {
        if (argc < 2)
            return 1;
        const auto expected = std::filesystem::path(argv[1]);
        const auto actual = mujoco_robotics_uri::getMuJoCoPluginDirectory();
        if (actual != expected)
        {
            std::fprintf(stderr,
                         "Expected %s, found %s\n",
                         expected.string().c_str(),
                         actual.string().c_str());
            return 1;
        }
        if (argc > 2 && std::string(argv[2]) == "missing")
        {
            if (!mujoco_robotics_uri::loadDefaultMuJoCoPlugins())
                return 0;
            std::fputs("Expected false for a missing directory\n", stderr);
            return 1;
        }
        if (MRU_FIND_PROVIDER("robot://model.xml"))
        {
            std::fputs("Provider was registered before directory loading\n", stderr);
            return 1;
        }
        if (!mujoco_robotics_uri::loadDefaultMuJoCoPlugins())
            return 1;
        if (!MRU_FIND_PROVIDER("robot://model.xml"))
            return 1;
        char error[1024]{};
        mjModel* model = mj_loadXML("robot://model.xml", nullptr, error, sizeof(error));
        if (!model)
        {
            std::fprintf(stderr, "%s\n", error);
            return 1;
        }
        const bool valid = model->ngeom == 1;
        mj_deleteModel(model);
        return valid ? 0 : 1;
    } catch (const std::exception& error)
    {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
