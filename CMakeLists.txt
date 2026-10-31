cmake_minimum_required(VERSION 3.26)
project(mujoco_robotics_uri VERSION 0.1.1 LANGUAGES CXX)
include(GNUInstallDirs)
include(FetchContent)

option(MRU_WHEEL "Build for the upstream MuJoCo Python wheel layout" OFF)
option(MRU_FETCH_RESOLVER "Fetch the pinned resolver release" ${MRU_WHEEL})
set(MRU_PLUGIN_INSTALL_DIR "${CMAKE_INSTALL_BINDIR}/mujoco_plugin" CACHE PATH
    "Plugin destination relative to the installation prefix")

if(MRU_WHEEL)
  find_package(Python REQUIRED COMPONENTS Interpreter)
  execute_process(COMMAND "${Python_EXECUTABLE}" -c
    "import importlib.util; from pathlib import Path; print(Path(importlib.util.find_spec('mujoco').origin).parent.as_posix())"
    OUTPUT_VARIABLE _mujoco_dir OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
  set(MRU_WHEEL_MUJOCO_VERSION "3.12.0" CACHE STRING "MuJoCo headers for this wheel release")
  execute_process(COMMAND "${Python_EXECUTABLE}" -c
    "from importlib.metadata import version; print(version('mujoco'))"
    OUTPUT_VARIABLE _mujoco_version OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
  if(NOT _mujoco_version STREQUAL MRU_WHEEL_MUJOCO_VERSION)
    message(FATAL_ERROR "Wheel requires MuJoCo ${MRU_WHEEL_MUJOCO_VERSION} build headers; found ${_mujoco_version}")
  endif()
  # The 3.12 Windows wheel nests headers one mujoco directory deeper.
  find_path(MRU_MUJOCO_INCLUDE_DIR NAMES mujoco/mujoco.h
    PATHS "${_mujoco_dir}/include" "${_mujoco_dir}/include/mujoco"
    NO_DEFAULT_PATH NO_CACHE REQUIRED)
  set(MRU_PLUGIN_INSTALL_DIR "mujoco/plugin")
else()
  set(MRU_MUJOCO_INCLUDE_DIR "" CACHE PATH "MuJoCo 3.12.0 include directory (headers only)")
  if(NOT MRU_MUJOCO_INCLUDE_DIR)
    FetchContent_Declare(mujoco_headers
      URL https://github.com/google-deepmind/mujoco/archive/refs/tags/3.12.0.tar.gz
      URL_HASH SHA256=9faa979982c3e924e8aaff3b16983bba3a1ab19c81f4f73178ae9c2ea25e467d
      # Use only the existing include directory, without building another engine.
      SOURCE_SUBDIR include)
    FetchContent_MakeAvailable(mujoco_headers)
    set(MRU_MUJOCO_INCLUDE_DIR "${mujoco_headers_SOURCE_DIR}/include")
  endif()
endif()

if(MRU_FETCH_RESOLVER)
  FetchContent_Declare(resolve_robotics_uri_cpp
    URL https://github.com/gbionics/resolve-robotics-uri-cpp/archive/refs/tags/v0.6.2.tar.gz
    URL_HASH SHA256=ad2c5abeea06f859c05214311f99d0dcf80558c86d678081c8b3b33071c62591)
  FetchContent_MakeAvailable(resolve_robotics_uri_cpp)
  if(MRU_WHEEL AND SKBUILD)
    install(FILES "${resolve_robotics_uri_cpp_SOURCE_DIR}/LICENSE"
      DESTINATION "${SKBUILD_METADATA_DIR}/licenses/resolve-robotics-uri-cpp")
  endif()
else()
  find_package(ResolveRoboticsURICpp 0.6.2 CONFIG REQUIRED)
endif()

add_library(mujoco_robotics_uri SHARED src/provider.cc src/mujoco_api.cc)
target_compile_features(mujoco_robotics_uri PRIVATE cxx_std_17)
target_include_directories(mujoco_robotics_uri PRIVATE "${MRU_MUJOCO_INCLUDE_DIR}")
target_link_libraries(mujoco_robotics_uri PRIVATE
  ResolveRoboticsURICpp::ResolveRoboticsURICpp ${CMAKE_DL_LIBS})
set_target_properties(mujoco_robotics_uri PROPERTIES
  CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES
  INSTALL_REMOVE_ENVIRONMENT_RPATH YES)

if(MRU_WHEEL)
  if(MSVC)
    # Keep Windows wheels independent of redistributable C/C++ runtime DLLs.
    set_property(TARGET mujoco_robotics_uri PROPERTY MSVC_RUNTIME_LIBRARY
      "MultiThreaded$<$<CONFIG:Debug>:Debug>")
  endif()
endif()

install(TARGETS mujoco_robotics_uri
  LIBRARY DESTINATION "${MRU_PLUGIN_INSTALL_DIR}"
  RUNTIME DESTINATION "${MRU_PLUGIN_INSTALL_DIR}")

include(CTest)
if(BUILD_TESTING AND NOT MRU_WHEEL)
  # The plugin itself needs only baseline headers. These test executables need
  # a real engine and its headers to exercise MuJoCo's public native API.
  find_package(mujoco CONFIG REQUIRED)
  add_executable(native_smoke tests/native_smoke.cc)
  target_compile_features(native_smoke PRIVATE cxx_std_17)
  target_link_libraries(native_smoke PRIVATE mujoco::mujoco)
  target_include_directories(native_smoke PRIVATE src)
  add_test(NAME native_provider COMMAND native_smoke $<TARGET_FILE:mujoco_robotics_uri>)
endif()

if(BUILD_TESTING AND NOT MRU_WHEEL)
  add_test(NAME native_conflict COMMAND native_smoke $<TARGET_FILE:mujoco_robotics_uri> conflict)
endif()

if(BUILD_TESTING AND NOT MRU_WHEEL)
  add_executable(native_discovery tests/native_discovery.cc)
  target_compile_features(native_discovery PRIVATE cxx_std_17)
  target_link_libraries(native_discovery PRIVATE mujoco::mujoco ${CMAKE_DL_LIBS})
  target_include_directories(native_discovery PRIVATE src)
  # Exercise the PLT case too, rather than relying on the compiler's PIE default.
  if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_compile_options(native_discovery PRIVATE -fno-pie)
    target_link_options(native_discovery PRIVATE -no-pie)
  endif()
  find_package(Python REQUIRED COMPONENTS Interpreter)
  add_test(NAME native_relocated_discovery
    COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_native_discovery.py"
      $<TARGET_FILE:native_discovery> $<TARGET_FILE:mujoco_robotics_uri> $<TARGET_FILE:mujoco::mujoco>)
endif()

if(BUILD_TESTING AND NOT MRU_WHEEL AND UNIX)
  # Link a MuJoCo symbol into an executable without linking the shared runtime.
  add_executable(native_linked_module tests/native_linked_module.cc)
  target_compile_features(native_linked_module PRIVATE cxx_std_17)
  target_include_directories(native_linked_module PRIVATE
    $<TARGET_PROPERTY:mujoco::mujoco,INTERFACE_INCLUDE_DIRECTORIES>)
  target_link_libraries(native_linked_module PRIVATE ${CMAKE_DL_LIBS})
  add_test(NAME native_linked_module_discovery COMMAND native_linked_module)
endif()

if(BUILD_TESTING AND NOT MRU_WHEEL)
  add_library(runtime_without_providers SHARED tests/runtime_without_providers.cc)
  set_target_properties(runtime_without_providers PROPERTIES
    OUTPUT_NAME mujoco VERSION 3.12.0 WINDOWS_EXPORT_ALL_SYMBOLS ON
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/runtime-stub"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/runtime-stub")
  add_test(NAME runtime_loading_failures
    COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_runtime_loading.py"
      $<TARGET_FILE:mujoco_robotics_uri> $<TARGET_FILE:runtime_without_providers>)
endif()
