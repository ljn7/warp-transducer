from packaging.version import Version
import os, platform, sys
from setuptools import setup, find_packages
from torch.utils.cpp_extension import BuildExtension, CppExtension, CUDAExtension
import torch

system = platform.system().lower()
is_windows = system == "windows"
is_macos = system == "darwin"
is_linux = system == "linux"

if Version(torch.__version__) >= Version("2.1.0"):
    cpp_standard = "c++17"
elif Version(torch.__version__) >= Version("1.5.0"):
    cpp_standard = "c++14"
else:
    cpp_standard = "c++11"

extra_compile_args = {"cxx": [], "nvcc": []}
extra_link_args = []

if is_windows:
    extra_compile_args["cxx"] += ["/std:c++17", "/MD", "/O2"]
else:
    extra_compile_args["cxx"] += [f"-std={cpp_standard}", "-fPIC"]

enable_gpu = torch.cuda.is_available() or "CUDA_HOME" in os.environ

if enable_gpu:
    extra_compile_args["cxx"] += ["/DWARPRNNT_ENABLE_GPU"] if is_windows else ["-DWARPRNNT_ENABLE_GPU"]
else:
    print("Torch has no CUDA support — building CPU-only version.")

warp_rnnt_path = os.environ.get("WARP_RNNT_PATH", os.path.realpath("../build"))
torch_lib_dir = os.path.join(os.path.dirname(torch.__file__), "lib")

if is_windows:
    lib_exts = [".lib", ".dll"]
elif is_macos:
    lib_exts = [".dylib"]
else:
    lib_exts = [".so"]

lib_name = None
for name in ["libwarprnnt", "warprnnt"]:
    for ext in lib_exts:
        if os.path.exists(os.path.join(warp_rnnt_path, name + ext)):
            lib_name = "warprnnt"
            break
    if lib_name:
        break

if not lib_name:
    print(f"Could not find warp-rnnt library in {warp_rnnt_path}")
    sys.exit(1)

libraries = []

libraries.append("warprnnt")

# Core PyTorch / c10 / python symbols next (order tuned for Windows linking)
# torch_python provides the Python bindings; c10 and torch_cpu are common deps
libraries += ["torch_python", "torch", "torch_cpu", "c10"]

if enable_gpu:
    # torch_cuda_libs = []
    # if os.path.isdir(torch_lib_dir):
    #     for f in os.listdir(torch_lib_dir):
    #         if f.startswith("torch_cuda") and (f.endswith(".lib") or f.endswith(".dll") or f.endswith(".so")):
    #             lib_base = os.path.splitext(f)[0]
    #             if lib_base not in torch_cuda_libs:
    #                 torch_cuda_libs.append(lib_base)
    # if "torch_cuda" in torch_cuda_libs:
    #     libraries.append("torch_cuda")
    # else:
    #     libraries += torch_cuda_libs

    # CUDA runtime (explicit on Windows)
    if is_windows:
        libraries.append("cudart")

# add sleef at the end (non-cuda math lib often used by torch)
libraries.append("sleef")

library_dirs = [os.path.realpath(warp_rnnt_path)]
if os.path.isdir(torch_lib_dir):
    library_dirs.append(torch_lib_dir)

if is_linux or is_macos:
    extra_link_args.append(f"-Wl,-rpath,{os.path.realpath(warp_rnnt_path)}")

define_macros = [("TORCH_API_INCLUDE_EXTENSION_H", None)]

include_dirs = [os.path.realpath("../include")]

print("\n===== Warp-RNNT Build Configuration =====")
print("System:", platform.system(), platform.release())
print("Torch version:", torch.__version__)
print("CUDA enabled:", enable_gpu)
print("Using C++ standard:", cpp_standard)
print("Warp-RNNT path:", warp_rnnt_path)
print("Torch lib dir:", torch_lib_dir)
print("Libraries to link (ordered):", libraries)
print("Library dirs:", library_dirs)
print("extra_compile_args:", extra_compile_args)
print("extra_link_args:", extra_link_args)
print("=========================================\n")

ext = CUDAExtension if enable_gpu and is_windows else CppExtension 
ext_modules = [
    ext(
        name="warprnnt_pytorch.warp_rnnt",
        sources=["src/binding.cpp"],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=libraries,
        define_macros=define_macros,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
]

setup(
    name="warprnnt_pytorch",
    version="0.2.0",
    description="PyTorch wrapper for RNN-Transducer",
    url="https://github.com/ljn7/warp-transducer",
    author="Mingkun Huang",
    author_email="mingkunhuang95@gmail.com",
    packages=find_packages(),
    install_requires=["packaging", "torch"],
    ext_modules=ext_modules,
    cmdclass={"build_ext": BuildExtension},
)
