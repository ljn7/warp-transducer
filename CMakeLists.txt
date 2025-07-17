if(APPLE)
    cmake_minimum_required(VERSION 3.4)
else()
    cmake_minimum_required(VERSION 3.5)
endif()

project(rnnt_release LANGUAGES CXX CUDA)

# ==== USER OPTIONS ====
option(WITH_GPU "Build with CUDA support" ON)
option(WITH_OMP "Build with OpenMP support" ON)
option(USE_NAIVE_KERNEL "Use naive alpha-beta kernel" OFF)
option(DEBUG_TIME "Output kernel time" OFF)
option(DEBUG_KERNEL "Output alpha beta debug" OFF)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT APPLE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -O2")
    add_definitions(-DAPPLE)
endif()

include_directories(include)

# ==== PREPROCESSOR FLAGS ====
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

if(WITH_OMP)
    find_package(OpenMP)
    if(OpenMP_CXX_FOUND)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
    endif()
endif()

# ==== SAFE CUDA VERSION DETECTION & ARCH SELECTION ====

# Try to detect CUDA version. Set major.minor or fallback to "0"
if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
    find_package(CUDAToolkit REQUIRED)
    set(CUDA_TOOLKIT_VERSION "${CUDAToolkit_VERSION}")
    if(NOT CUDA_TOOLKIT_VERSION OR "${CUDA_TOOLKIT_VERSION}" STREQUAL "")
        # CMake >= 3.18 but CUDAToolkit_VERSION not set? Fallback logic
        set(CUDA_TOOLKIT_VERSION "0.0")
    endif()
else()
    find_package(CUDA REQUIRED)
    if(DEFINED CUDA_VERSION AND NOT "${CUDA_VERSION}" STREQUAL "")
        set(CUDA_TOOLKIT_VERSION "${CUDA_VERSION}")
    else()
        set(CUDA_TOOLKIT_VERSION "0.0")
    endif()
endif()

# Split CUDA version into major/minor
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
    message(WARNING "Could not detect CUDA version. Defaulting to minimal arch set (52;60;70;75).")
elseif(CUDA_VERSION_MAJOR LESS 11)
    set(CUDA_ARCH_LIST "52;60;70;75")
elseif(CUDA_VERSION_MAJOR EQUAL 11)
    set(CUDA_ARCH_LIST "52;60;70;75;80;86")
elseif(CUDA_VERSION_MAJOR GREATER_EQUAL 12)
    set(CUDA_ARCH_LIST "52;60;70;75;80;86;89")
endif()

# Allow user override
if(DEFINED CMAKE_CUDA_ARCHITECTURES AND NOT "${CMAKE_CUDA_ARCHITECTURES}" STREQUAL "")
    set(CUDA_ARCH_LIST "${CMAKE_CUDA_ARCHITECTURES}")
endif()

if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
    set(CMAKE_CUDA_ARCHITECTURES "${CUDA_ARCH_LIST}" CACHE STRING "Target GPU architectures")
    message(STATUS "Auto-selected CUDA archs for CUDA ${CUDA_TOOLKIT_VERSION}: ${CMAKE_CUDA_ARCHITECTURES}")
else()
    string(REPLACE ";" " " CUDA_ARCH_FLAGS "${CUDA_ARCH_LIST}")
    set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} ")
    foreach(ARCH ${CUDA_ARCH_LIST})
        set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} -gencode arch=compute_${ARCH},code=sm_${ARCH}")
    endforeach()
    set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} --std=c++11")
    message(STATUS "Auto-selected CUDA NVCC_ARCH flags for CUDA ${CUDA_TOOLKIT_VERSION}: ${CUDA_NVCC_FLAGS}")
endif()

if(CUDA_TOOLKIT_VERSION AND CUDA_VERSION_MAJOR LESS 11)
    if(CUDA_ARCH_LIST MATCHES "80|86|89")
        message(WARNING "
Detected CUDA ${CUDA_TOOLKIT_VERSION}.
Some requested architectures (${CUDA_ARCH_LIST}) require CUDA >= 11 (Ampere/Ada).
Remove sm_80/86/89 or upgrade CUDA Toolkit if you see NVCC errors.
")
    endif()
endif()

# ==== Apple/Mac rpath ====
if(APPLE)
    execute_process(COMMAND uname -v OUTPUT_VARIABLE DARWIN_VERSION)
    string(REGEX MATCH "[0-9]+" DARWIN_VERSION "${DARWIN_VERSION}")
    message(STATUS "DARWIN_VERSION=${DARWIN_VERSION}")
    if(${DARWIN_VERSION} LESS 15)
        set(CMAKE_SKIP_RPATH TRUE)
    endif()
else()
    set(CMAKE_SKIP_RPATH TRUE)
endif()

# ==== Main library target ====
if(WITH_GPU)
    message(STATUS "Building shared library with GPU support")
    if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
        add_library(warprnnt SHARED src/rnnt_entrypoint.cu)
        target_link_libraries(warprnnt PRIVATE CUDA::cudart CUDA::curand)
    else()
        CUDA_ADD_LIBRARY(warprnnt SHARED src/rnnt_entrypoint.cu)
        if(NOT Torch_FOUND)
            TARGET_LINK_LIBRARIES(warprnnt ${CUDA_curand_LIBRARY})
        endif()
    endif()
else()
    message(STATUS "Building shared library with no GPU support")
    add_library(warprnnt SHARED src/rnnt_entrypoint.cpp)
endif()

target_compile_features(warprnnt PRIVATE cxx_std_17)
target_compile_definitions(warprnnt PRIVATE ${COMMON_DEFINITIONS})
target_include_directories(warprnnt PRIVATE include)
if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18" AND TARGET warprnnt)
    set_target_properties(warprnnt PROPERTIES
        CUDA_SEPARABLE_COMPILATION ON
        CUDA_STANDARD 17
        CUDA_STANDARD_REQUIRED ON
    )
    target_compile_options(warprnnt PRIVATE
        $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>
    )
endif()

# ==== Test executables ====
add_executable(test_cpu tests/test_cpu.cpp tests/random.cpp)
target_link_libraries(test_cpu PRIVATE warprnnt)
target_compile_features(test_cpu PRIVATE cxx_std_17)

add_executable(test_time tests/test_time.cpp tests/random.cpp)
target_link_libraries(test_time PRIVATE warprnnt)
target_compile_features(test_time PRIVATE cxx_std_17)

if(WITH_GPU)
    if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
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
    else()
        cuda_add_executable(test_time_gpu tests/test_time.cu tests/random.cpp )
        TARGET_LINK_LIBRARIES(test_time_gpu warprnnt ${CUDA_curand_LIBRARY})
        set_target_properties(test_time_gpu PROPERTIES COMPILE_FLAGS "${CMAKE_CXX_FLAGS} --std=c++11")

        cuda_add_executable(test_gpu tests/test_gpu.cu tests/random.cpp )
        TARGET_LINK_LIBRARIES(test_gpu warprnnt ${CUDA_curand_LIBRARY})
        set_target_properties(test_gpu PROPERTIES COMPILE_FLAGS "${CMAKE_CXX_FLAGS} --std=c++11")
    endif()
endif()

# ==== Install targets ====
install(TARGETS warprnnt
        RUNTIME DESTINATION bin
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)

install(FILES include/rnnt.h DESTINATION include)
