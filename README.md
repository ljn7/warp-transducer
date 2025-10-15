# Warp-Transducer

A high-performance parallel implementation of RNN Transducer loss computation (Graves 2013), optimized for both CPU and GPU.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## Overview

Warp-Transducer provides fast, memory-efficient implementations of the RNN-T loss function, commonly used in end-to-end speech recognition systems. The library is designed for seamless integration with deep learning frameworks and offers significant performance improvements over naive implementations.

### Key Features

- **Dual Backend Support**: Optimized implementations for both CPU (OpenMP) and GPU (CUDA)
- **Framework Agnostic**: C/C++ interface with bindings for PyTorch
- **Production Ready**: Battle-tested on Linux, Windows, and Android (Termux)

### Available Variants

- **Graves 2013 Joint Network** (this branch): Current implementation
- **Graves 2012 Add Network**: [Available here](https://github.com/HawkAaron/warp-transducer/tree/add_network)

## Performance Benchmarks

Benchmarked on GeForce GTX 1080 Ti:

### Small Vocabulary (A=28)

| Batch Size (N) | Time (ms) | Sequences/sec |
|----------------|-----------|---------------|
| 1              | 8.51      | 117.5         |
| 16             | 11.43     | 1,400         |
| 32             | 12.65     | 2,530         |
| 64             | 14.75     | 4,339         |
| 128            | 19.48     | 6,572         |

*T=150 (time steps), L=40 (label length), A=28 (alphabet size)*

### Large Vocabulary (A=5000)

| Batch Size (N) | Time (ms) | Sequences/sec |
|----------------|-----------|---------------|
| 1              | 4.79      | 208.8         |
| 16             | 24.44     | 655           |
| 32             | 41.38     | 773           |
| 64             | 80.44     | 796           |
| 128            | 51.46     | 2,487         |

*T=150 (time steps), L=20 (label length), A=5000 (alphabet size)*

## Installation

### Prerequisites

- **CMake** 3.10 or later
- **C++11** compatible compiler (GCC 4.9+, MSVC 2015+)
- **CUDA Toolkit** 9.0+ (optional, for GPU support)
- **OpenMP** (optional, for CPU parallelization)

### Building from Source

#### Linux / macOS

1. **Clone the repository:**

   ```bash
   git clone https://github.com/HawkAaron/warp-transducer
   cd warp-transducer
   ```

2. **Create build directory:**

   ```bash
   mkdir build
   cd build
   ```

3. **Configure with CMake:**

   ```bash
   cmake ..
   ```

   For custom CUDA installation:
   ```bash
   cmake -DCUDA_TOOLKIT_ROOT_DIR=/path/to/cuda ..
   ```

   Or using environment variable:
   ```bash
   export CUDA_HOME=/usr/local/cuda
   cmake -DCUDA_TOOLKIT_ROOT_DIR=$CUDA_HOME ..
   ```

4. **Build and install:**

   ```bash
   make
   sudo make install  # Optional: system-wide installation
   ```

#### Windows

**Prerequisites:**
- Visual Studio 2015 or later with "Desktop development with C++"
- CMake 3.10 or later
- CUDA Toolkit (for GPU support)

**Build Steps:**

1. **Open "x64 Native Tools Command Prompt for VS 2022"** from the Start Menu

2. **Clone the repository:**

   ```cmd
   git clone https://github.com/HawkAaron/warp-transducer
   cd warp-transducer
   ```

3. **Create build directory:**

   ```cmd
   mkdir build
   cd build
   ```

4. **Configure with CMake:**

   ```cmd
   cmake ..
   ```

   For custom CUDA installation:
   ```cmd
   cmake -DCUDA_TOOLKIT_ROOT_DIR="C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4" ..
   ```

   Or set environment variable first:
   ```cmd
   set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4
   cmake -DCUDA_TOOLKIT_ROOT_DIR="%CUDA_HOME%" ..
   ```

5. **Build:**

   ```cmd
   cmake --build . --config Release
   ```

   The library (`warprnnt.dll`) will be in the `build/Release` directory.

6. **Install (optional):**

   ```cmd
   cmake --install . --config Release
   ```

### Verifying GPU Support

After running `cmake`, verify CUDA was detected:

**Success message:**
```
-- cuda found TRUE
-- Building shared library with GPU support
```

**If you see "no GPU support" despite having CUDA:**

Linux/macOS:
```bash
rm CMakeCache.txt
cmake -DCUDA_TOOLKIT_ROOT_DIR=$CUDA_HOME ..
```

Windows:
```cmd
del CMakeCache.txt
cmake -DCUDA_TOOLKIT_ROOT_DIR="%CUDA_HOME%" ..
```

## Testing

### Running Tests

Ensure CUDA libraries are accessible:

**Linux:**
```bash
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
./test_gpu  # If built with CUDA support
./test_cpu  # Always available
```

**macOS:**
```bash
export DYLD_LIBRARY_PATH=/usr/local/cuda/lib:$DYLD_LIBRARY_PATH
./test_gpu
./test_cpu
```

**Windows:**
```cmd
set PATH=%CUDA_HOME%\bin;%PATH%
test_gpu.exe
test_cpu.exe
```

## API Usage

### C/C++ Interface

The main interface is defined in `include/rnnt.h`:

```c
#include <rnnt.h>

// Initialize options
rnntOptions options;
memset(&options, 0, sizeof(options));
options.loc = RNNT_GPU;  // or RNNT_CPU
options.num_threads = 4;  // for CPU execution
options.stream = stream;  // CUDA stream for GPU

// Compute loss
rnntStatus_t status = compute_rnnt_loss(
    acts,           // Network outputs
    grads,          // Gradient storage (optional)
    labels,         // Target labels
    label_lengths,  // Label lengths per sample
    input_lengths,  // Input sequence lengths per sample
    alphabet_size,  // Vocabulary size
    minibatch,      // Batch size
    costs,          // Output: loss per sample
    workspace,      // Workspace memory
    options
);
```

### Important Notes

- **No Internal Allocation**: The library requires pre-allocated workspace memory to avoid synchronization overhead
- **CPU Version**: For CPU execution, you must manually apply `log_softmax` to network outputs before calling the loss function
- **GPU Version**: Log-softmax is automatically applied on GPU

For framework-specific bindings, see:
- [PyTorch Binding](pytorch_binding/)

## Troubleshooting

### Error: `cuda_runtime_api.h: No such file or directory`

This error occurs when the compiler cannot locate CUDA headers.

**Linux/macOS Diagnosis:**
```bash
find /usr/local -name cuda_runtime_api.h 2>/dev/null
```

**Linux/macOS Solution:**

If CUDA is installed at `/usr/local/cuda-12.9`:

```bash
export CUDA_HOME=/usr/local/cuda-12.9
export CFLAGS="-I$CUDA_HOME/targets/x86_64-linux/include"
export LDFLAGS="-L$CUDA_HOME/targets/x86_64-linux/lib"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"
```

Then rebuild:
```bash
cd build
rm CMakeCache.txt
cmake -DCUDA_TOOLKIT_ROOT_DIR=$CUDA_HOME ..
make
```

**Windows Solution:**

Ensure CUDA_HOME is set correctly:

```cmd
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4
set PATH=%CUDA_HOME%\bin;%PATH%
set INCLUDE=%CUDA_HOME%\include;%INCLUDE%
set LIB=%CUDA_HOME%\lib\x64;%LIB%
```

Then rebuild:
```cmd
cd build
del CMakeCache.txt
cmake -DCUDA_TOOLKIT_ROOT_DIR="%CUDA_HOME%" ..
cmake --build . --config Release
```

### CMake Not Finding CUDA

**Symptoms:** CMake reports "cuda found TRUE" but "no GPU support"

**Solution:**

Linux/macOS:
1. Clear CMake cache: `rm CMakeCache.txt`
2. Verify CUDA installation: `nvcc --version`
3. Set explicit path: `cmake -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda ..`

Windows:
1. Clear CMake cache: `del CMakeCache.txt`
2. Verify CUDA installation: `nvcc --version`
3. Set explicit path: `cmake -DCUDA_TOOLKIT_ROOT_DIR="C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4" ..`

### Library Not Found at Runtime

**Linux:**
```bash
sudo ldconfig  # If you ran 'make install'
# OR
export LD_LIBRARY_PATH=/path/to/warp-transducer/build:$LD_LIBRARY_PATH
```

**macOS:**
```bash
export DYLD_LIBRARY_PATH=/path/to/warp-transducer/build:$DYLD_LIBRARY_PATH
```

**Windows:**

Add the DLL location to your PATH:
```cmd
set PATH=C:\path\to\warp-transducer\build\Release;%PATH%
```

Or copy `warprnnt.dll` to the same directory as your executable (warprnnt_pytorch). 

## Framework Bindings

### PyTorch

```bash
cd pytorch_binding
pip install .
```

See [pytorch_binding/README.md](pytorch_binding/) for detailed usage.

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting

## Citation

If you use Warp-Transducer in your research, please cite:

```bibtex
@article{graves2013sequence,
  title={Sequence transduction with recurrent neural networks},
  author={Graves, Alex},
  journal={arXiv preprint arXiv:1211.3711},
  year={2013}
}
```

## References

- [Sequence Transduction with Recurrent Neural Networks](https://arxiv.org/abs/1211.3711) - Graves (2013)
- [Speech Recognition with Deep Recurrent Neural Networks](https://arxiv.org/abs/1303.5778) - Graves et al. (2013)
- [Baidu warp-ctc](https://github.com/baidu-research/warp-ctc) - Inspiration for this project
- [Awni's Transducer Implementation](https://github.com/awni/transducer) - Reference implementation

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Acknowledgments

Special thanks to the contributors and the broader speech recognition research community.

---

**Questions?** Open an issue or check existing discussions.

**Need PyTorch bindings?** See [pytorch_binding/](pytorch_binding/)