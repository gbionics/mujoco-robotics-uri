// SPDX-FileCopyrightText: 2026 Generative Bionics S.R.L.
// SPDX-License-Identifier: BSD-3-Clause
#include <cstdlib>

// A locally loaded runtime in an unrelated directory, deliberately lacking
// provider symbols. The real-runtime matrix covers successful registration.
extern "C" int mj_version()
{
    const char* version = std::getenv("MRU_TEST_RUNTIME_VERSION");
    return version ? std::atoi(version) : 3012000;
}

extern "C" const char* mj_versionString()
{
    return "test-runtime";
}
