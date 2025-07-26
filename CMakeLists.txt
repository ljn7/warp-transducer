cmake_minimum_required(VERSION 3.10)
project(rnnt_release LANGUAGES CXX)

# ==== CUDA DETECTION ====
set(CUDA_FOUND FALSE)
set(CUDA_TOOLKIT_VERSION "0.0")

if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
    find_package(CUDAToolkit QUIET)
    
    if(CMAKE_VERSION VERSION_LESS "3.27")
        find_package(CUDA QUIET)
    endif()
    
    if(CUDAToolkit_FOUND OR CUDA_FOUND)
        set(CUDA_FOUND TRUE)
        if(CUDAToolkit_FOUND)
            set(CUDA_TOOLKIT_VERSION "${CUDAToolkit_VERSION}")
        elseif(DEFINED CUDA_VERSION AND NOT "${CUDA_VERSION}" STREQUAL "")
            set(CUDA_TOOLKIT_VERSION "${CUDA_VERSION}")
        endif()
    endif()
else()
    find_package(CUDA QUIET)
    if(CUDA_FOUND AND DEFINED CUDA_VERSION AND NOT "${CUDA_VERSION}" STREQUAL "")
        set(CUDA_TOOLKIT_VERSION "${CUDA_VERSION}")
    endif()
endif()

# ==== USER OPTIONS ====
option(WITH_GPU "Build with GPU (CUDA) support" ${CUDA_FOUND})
option(WITH_OMP "Build with OpenMP support" ON)
option(USE_NAIVE_KERNEL "Use naive alpha-beta kernel" OFF)
option(DEBUG_TIME "Output kernel time" OFF)
option(DEBUG_KERNEL "Output alpha beta debug" OFF)

# ==== GPU BUILD CONFIGURATION ====
if(WITH_GPU)
    if(NOT CUDA_FOUND)
        message(WARNING "WITH_GPU=ON was requested, but no compatible CUDA toolkit was found. Falling back to CPU-only build.")
        set(WITH_GPU OFF CACHE BOOL "Build with GPU (CUDA) support" FORCE)
        set(USE_CUDA FALSE)
    else()
        enable_language(CUDA)
        set(USE_CUDA TRUE)
        message(STATUS "Building with CUDA ${CUDA_TOOLKIT_VERSION} support")
    endif()
else()
    set(USE_CUDA FALSE)
    if(CUDA_FOUND)
        message(STATUS "CUDA ${CUDA_TOOLKIT_VERSION} detected but GPU support disabled (WITH_GPU=OFF)")
    else()
        message(STATUS "Building CPU-only version (no CUDA toolkit found)")
    endif()
endif()

# ==== OPENMP CONFIGURATION ====
if(WITH_OMP)
    find_package(OpenMP)
    if(OpenMP_CXX_FOUND)
        message(STATUS "OpenMP support enabled")
    else()
        message(WARNING "OpenMP requested but not found")
        set(WITH_OMP OFF)
    endif()
endif()

# ==== COMPILER SETTINGS ====
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Build type" FORCE)
endif()

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O0 -g")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")
endif()

if(APPLE)
    add_definitions(-DAPPLE)
    execute_process(COMMAND uname -v OUTPUT_VARIABLE DARWIN_VERSION)
    string(REGEX MATCH "[0-9]+" DARWIN_VERSION "${DARWIN_VERSION}")
    message(STATUS "Darwin version: ${DARWIN_VERSION}")
    if(${DARWIN_VERSION} LESS 15)
        set(CMAKE_SKIP_RPATH TRUE)
    endif()
else()
    set(CMAKE_SKIP_RPATH TRUE)
endif()

include_directories(include)

# ==== PREPROCESSOR DEFINITIONS ====
set(COMMON_DEFINITIONS "")

if(USE_CUDA)
    list(APPEND COMMON_DEFINITIONS -DWITH_CUDA=1)
else()
    list(APPEND COMMON_DEFINITIONS -DWITH_CUDA=0)
endif()

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

# ==== CUDA ARCHITECTURE SETUP ====
if(USE_CUDA)
    function(cuda_version_major VERSION OUTVAR)
        if(NOT "${VERSION}" STREQUAL "")
            string(REPLACE "." ";" TMP_LIST ${VERSION})
            list(GET TMP_LIST 0 MAJOR)
            set(${OUTVAR} "${MAJOR}" PARENT_SCOPE)
        else()
            set(${OUTVAR} "0" PARENT_SCOPE)
        endif()
    endfunction()

    function(cuda_version_minor VERSION OUTVAR)
        if(NOT "${VERSION}" STREQUAL "")
            string(REPLACE "." ";" TMP_LIST ${VERSION})
            list(LENGTH TMP_LIST TMP_LEN)
            if(TMP_LEN GREATER 1)
                list(GET TMP_LIST 1 MINOR)
            else()
                set(MINOR "0")
            endif()
            set(${OUTVAR} "${MINOR}" PARENT_SCOPE)
        else()
            set(${OUTVAR} "0" PARENT_SCOPE)
        endif()
    endfunction()

    cuda_version_major("${CUDA_TOOLKIT_VERSION}" CUDA_VERSION_MAJOR)
    cuda_version_minor("${CUDA_TOOLKIT_VERSION}" CUDA_VERSION_MINOR)

    set(CUDA_ARCH_LIST "")
    if(CUDA_TOOLKIT_VERSION STREQUAL "" OR CUDA_VERSION_MAJOR EQUAL 0)
        set(CUDA_ARCH_LIST "52;60;70;75")
        message(WARNING "Could not detect CUDA version. Using minimal architecture set: ${CUDA_ARCH_LIST}")
    elseif(CUDA_VERSION_MAJOR LESS 11)
        set(CUDA_ARCH_LIST "52;60;70;75")
    elseif(CUDA_VERSION_MAJOR EQUAL 11)
        set(CUDA_ARCH_LIST "52;60;70;75;80;86")
    elseif(CUDA_VERSION_MAJOR GREATER_EQUAL 12)
        set(CUDA_ARCH_LIST "52;60;70;75;80;86;89")
    endif()

    if(DEFINED CMAKE_CUDA_ARCHITECTURES AND NOT "${CMAKE_CUDA_ARCHITECTURES}" STREQUAL "")
        set(CUDA_ARCH_LIST "${CMAKE_CUDA_ARCHITECTURES}")
        message(STATUS "Using user-specified CUDA architectures: ${CUDA_ARCH_LIST}")
    else()
        message(STATUS "Auto-selected CUDA architectures for CUDA ${CUDA_TOOLKIT_VERSION}: ${CUDA_ARCH_LIST}")
        message(STATUS "To override, set -DCMAKE_CUDA_ARCHITECTURES=xx;yy;zz")
    endif()

    if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
        set(CMAKE_CUDA_ARCHITECTURES "${CUDA_ARCH_LIST}" CACHE STRING "Target GPU architectures")
    else()
        set(CUDA_NVCC_FLAGS "")
        foreach(ARCH ${CUDA_ARCH_LIST})
            set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} -gencode arch=compute_${ARCH},code=sm_${ARCH}")
        endforeach()
        message(STATUS "CUDA NVCC flags: ${CUDA_NVCC_FLAGS}")
    endif()

    if(CUDA_VERSION_MAJOR GREATER 0 AND CUDA_VERSION_MAJOR LESS 11)
        string(REGEX MATCH "8[0689]" AMPERE_ARCH "${CUDA_ARCH_LIST}")
        if(AMPERE_ARCH)
            message(WARNING 
                "Detected CUDA ${CUDA_TOOLKIT_VERSION} with Ampere/Ada architectures (${AMPERE_ARCH}) "
                "which require CUDA >= 11. Consider upgrading CUDA or removing sm_80/86/89 architectures.")
        endif()
    endif()
endif()

# ==== SOURCE FILE PREPARATION ====
set(RNNT_ENTRYPOINT_SRC src/rnnt_entrypoint.cu)
if(NOT USE_CUDA)
    configure_file(
        ${RNNT_ENTRYPOINT_SRC}
        ${CMAKE_CURRENT_BINARY_DIR}/rnnt_entrypoint_cpu.cpp
        COPYONLY
    )
    set(RNNT_ENTRYPOINT_SRC ${CMAKE_CURRENT_BINARY_DIR}/rnnt_entrypoint_cpu.cpp)
endif()

# ==== MAIN LIBRARY TARGET ====
add_library(warprnnt SHARED ${RNNT_ENTRYPOINT_SRC})

# Configure library properties
set_target_properties(warprnnt PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)

if(WIN32)
    set_target_properties(warprnnt PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

target_compile_definitions(warprnnt PRIVATE ${COMMON_DEFINITIONS})
target_include_directories(warprnnt PRIVATE include)

if(USE_CUDA)
    message(STATUS "Configuring library with GPU support")
    
    if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
        target_link_libraries(warprnnt PRIVATE CUDA::cudart CUDA::curand)
        set_target_properties(warprnnt PROPERTIES
            CUDA_SEPARABLE_COMPILATION ON
            CUDA_STANDARD 17
            CUDA_STANDARD_REQUIRED ON
        )
        target_compile_options(warprnnt PRIVATE
            $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>
        )
    else()
        cuda_add_library(warprnnt SHARED ${RNNT_ENTRYPOINT_SRC})
        if(NOT Torch_FOUND)
            target_link_libraries(warprnnt ${CUDA_curand_LIBRARY})
        endif()
    endif()
else()
    message(STATUS "Configuring library with CPU-only support")
endif()

if(WITH_OMP AND OpenMP_CXX_FOUND)
    target_link_libraries(warprnnt PRIVATE OpenMP::OpenMP_CXX)
endif()

# ==== TEST EXECUTABLES ====
add_executable(test_cpu tests/test_cpu.cpp tests/random.cpp)
target_link_libraries(test_cpu PRIVATE warprnnt)
target_compile_features(test_cpu PRIVATE cxx_std_17)

add_executable(test_time tests/test_time.cpp tests/random.cpp)
target_link_libraries(test_time PRIVATE warprnnt)
target_compile_features(test_time PRIVATE cxx_std_17)

if(USE_CUDA)
    if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
        add_executable(test_time_gpu tests/test_time.cu tests/random.cpp)
        target_link_libraries(test_time_gpu PRIVATE warprnnt CUDA::curand)
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
        set_target_properties(test_gpu PROPERTIES
            CUDA_SEPARABLE_COMPILATION ON
            CUDA_STANDARD 17
            CUDA_STANDARD_REQUIRED ON
        )
        target_compile_options(test_gpu PRIVATE
            $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>
        )
    else()
        cuda_add_executable(test_time_gpu tests/test_time.cu tests/random.cpp)
        target_link_libraries(test_time_gpu warprnnt ${CUDA_curand_LIBRARY})
        set_target_properties(test_time_gpu PROPERTIES 
            COMPILE_FLAGS "${CMAKE_CXX_FLAGS} --std=c++11"
        )

        cuda_add_executable(test_gpu tests/test_gpu.cu tests/random.cpp)
        target_link_libraries(test_gpu warprnnt ${CUDA_curand_LIBRARY})
        set_target_properties(test_gpu PROPERTIES 
            COMPILE_FLAGS "${CMAKE_CXX_FLAGS} --std=c++11"
        )
    endif()
endif()

# ==== INSTALL TARGETS ====
install(TARGETS warprnnt
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(FILES include/rnnt.h DESTINATION include)

# ==== BUILD SUMMARY ====
message(STATUS "")
message(STATUS "=== Build Configuration Summary ===")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "CUDA Available: ${CUDA_FOUND}")
if(CUDA_FOUND)
    message(STATUS "CUDA Version: ${CUDA_TOOLKIT_VERSION}")
endif()
message(STATUS "GPU Support: ${USE_CUDA}")
if(USE_CUDA)
    message(STATUS "CUDA Architectures: ${CMAKE_CUDA_ARCHITECTURES}")
endif()
message(STATUS "OpenMP Support: ${WITH_OMP}")
message(STATUS "Naive Kernel: ${USE_NAIVE_KERNEL}")
message(STATUS "Debug Time: ${DEBUG_TIME}")
message(STATUS "Debug Kernel: ${DEBUG_KERNEL}")
message(STATUS "=====================================")
message(STATUS "")