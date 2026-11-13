cmake_minimum_required(VERSION 3.20)

project(AstroGuardNative
    VERSION 0.1.0
    DESCRIPTION "AstroGuard C++ telemetry processing core"
    LANGUAGES CXX
)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(astroguard_core STATIC
    src/telemetry.cpp
)

target_include_directories(astroguard_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(MSVC)
    target_compile_options(astroguard_core PRIVATE /W4 /WX /permissive-)
else()
    target_compile_options(astroguard_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

add_executable(astroguard_native
    src/main.cpp
)

target_link_libraries(astroguard_native PRIVATE astroguard_core)

if(BUILD_TESTING)
    add_executable(astroguard_native_tests
        tests/telemetry_tests.cpp
    )

    target_link_libraries(astroguard_native_tests PRIVATE astroguard_core)

    add_test(
        NAME astroguard_native_unit_tests
        COMMAND astroguard_native_tests
    )
endif()