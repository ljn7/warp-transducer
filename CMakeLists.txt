cmake_minimum_required(VERSION 3.18)

project(rnnt_release LANGUAGES CXX CUDA)

# Set global flags
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT APPLE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -O2")
    add_definitions(-DAPPLE)
endif()

# Include headers
include_directories(include)

# Find CUDA Toolkit
find_package(CUDAToolkit REQUIRED)
message(STATUS "CUDA toolkit found")

# Options
option(USE_NAIVE_KERNEL "use naive alpha-beta kernel" OFF)
option(DEBUG_TIME "output kernel time" OFF)
option(DEBUG_KERNEL "output alpha beta" OFF)
option(WITH_GPU "compile warp-rnnt with cuda." ON)
option(WITH_OMP "compile warp-rnnt with openmp." ON)

# Preprocessor flags
set(COMMON_DEFINITIONS "")
if(USE_NAIVE_KERNEL)
    list(APPEND COMMON_DEFINITIONS -DUSE_NAIVE_KERNEL)
endif()
if(DEBUG_TIME)
    list(APPEND COMMON_DEFINITIONS -DDEBUG_TIME)
endif()
if(DEBUG_KERNEL)
    list(APPEND COMMON_DEFINITIONS -DDEBUG_KERNEL)
endif()
if(NOT WITH_OMP)
    list(APPEND COMMON_DEFINITIONS -DRNNT_DISABLE_OMP)
endif()

# OpenMP
if(WITH_OMP)
    find_package(OpenMP)
    if(OpenMP_CXX_FOUND)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
    endif()
endif()

set(CMAKE_CUDA_ARCHITECTURES 86)

# --------------------
# Shared Library Target
# --------------------
if(WITH_GPU)
    message(STATUS "Building shared library with GPU support")

    add_library(warprnnt SHARED src/rnnt_entrypoint.cu)
    target_link_libraries(warprnnt PRIVATE CUDA::cudart CUDA::curand)
else()
    message(STATUS "Building shared library with no GPU support")

    add_library(warprnnt SHARED src/rnnt_entrypoint.cpp)
endif()

target_compile_features(warprnnt PRIVATE cxx_std_17)
target_compile_definitions(warprnnt PRIVATE ${COMMON_DEFINITIONS})
target_include_directories(warprnnt PRIVATE include)
set_target_properties(warprnnt PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON
    CUDA_STANDARD 17
    CUDA_STANDARD_REQUIRED ON
)
target_compile_options(warprnnt PRIVATE
    $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>
)

# --------------------
# Executables
# --------------------
add_executable(test_cpu tests/test_cpu.cpp tests/random.cpp)
target_link_libraries(test_cpu PRIVATE warprnnt)
target_compile_features(test_cpu PRIVATE cxx_std_17)

add_executable(test_time tests/test_time.cpp tests/random.cpp)
target_link_libraries(test_time PRIVATE warprnnt)
target_compile_features(test_time PRIVATE cxx_std_17)

if(WITH_GPU)
    add_executable(test_time_gpu tests/test_time.cu tests/random.cpp)
    target_link_libraries(test_time_gpu PRIVATE warprnnt CUDA::curand)
    target_compile_features(test_time_gpu PRIVATE cxx_std_17)
    set_target_properties(test_time_gpu PROPERTIES
        CUDA_SEPARABLE_COMPILATION ON
        CUDA_STANDARD 17
        CUDA_STANDARD_REQUIRED ON
    )
    target_compile_options(test_time_gpu PRIVATE
        $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>
    )

    add_executable(test_gpu tests/test_gpu.cu tests/random.cpp)
    target_link_libraries(test_gpu PRIVATE warprnnt CUDA::curand)
    target_compile_features(test_gpu PRIVATE cxx_std_17)
    set_target_properties(test_gpu PROPERTIES
        CUDA_SEPARABLE_COMPILATION ON
        CUDA_STANDARD 17
        CUDA_STANDARD_REQUIRED ON
    )
    target_compile_options(test_gpu PRIVATE
        $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>
    )
endif()

# --------------------
# Installation
# --------------------
install(TARGETS warprnnt
        RUNTIME DESTINATION bin
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)

install(FILES include/rnnt.h DESTINATION include)