# WarpRNNT PyTorch Binding

PyTorch bindings for the [WarpRNNT](https://github.com/ljn7/warp-transducer) library, providing efficient RNN-Transducer loss computation with GPU acceleration.

## Overview

This package provides high-performance PyTorch kernels for computing RNN-Transducer (RNN-T) loss, commonly used in sequence-to-sequence models for speech recognition and other applications. WarpRNNT offers significant speedups through optimized CUDA implementations.

## Prerequisites

- **PyTorch**: Install from [pytorch.org](https://pytorch.org/get-started/locally/)
- **GCC**: Version 4.9 or later (Linux)
- **CUDA Toolkit**: Required for GPU support (optional but recommended)
- **CMake**: Version 3.10 or later

## Installation

### Linux / macOS

#### Step 1: Build WarpRNNT

Clone and build the WarpRNNT library:

```bash
git clone https://github.com/HawkAaron/warp-transducer
cd warp-transducer
mkdir build && cd build
cmake ..
make
sudo make install  # Optional: installs system-wide
```

#### Step 2: Set Environment Variables

If you have a GPU and CUDA installed:

```bash
export CUDA_HOME="/usr/local/cuda"
```

If WarpRNNT is installed in a custom location, set:

```bash
export WARP_RNNT_PATH="/path/to/warprnnt/build"
```

*Note: By default, `WARP_RNNT_PATH` points to `../build` relative to the binding directory.*

#### Step 3: Install PyTorch Bindings

```bash
cd ../pytorch_binding
pip install .
```

#### macOS with Anaconda (Troubleshooting)

If you encounter a `dlopen` error on macOS using Anaconda:

```bash
cd ../pytorch_binding
python setup.py install
cd ../build
cp libwarprnnt.dylib ~/anaconda3/lib
```

Adjust the path for your specific Python installation.

---

### Windows

#### Prerequisites

Ensure the following are installed:

1. **CUDA Toolkit** — [Download here](https://developer.nvidia.com/cuda-downloads)
   - Add to `PATH` and set `CUDA_HOME`
   
   ```cmd
   set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4
   set PATH=%CUDA_HOME%\bin;%PATH%
   ```

2. **Visual Studio 2022** (or later)
   - Include "Desktop development with C++" during installation
   - Provides MSVC compiler and CMake integration

3. **CMake** — [Download here](https://cmake.org/download/)
   - Optionally install Ninja for faster builds

#### Build Instructions

1. Open **"x64 Native Tools Command Prompt for VS 2022"** from the Start Menu

2. Clone and build WarpRNNT:

   ```cmd
   git clone https://github.com/HawkAaron/warp-transducer
   cd warp-transducer
   mkdir build && cd build
   cmake ..
   cmake --build . --config Release
   ```

   *For custom CUDA locations:*
   ```cmd
   cmake -DCUDA_TOOLKIT_ROOT_DIR="C:\Path\To\CUDA" ..
   ```

3. Install PyTorch bindings:

   ```cmd
   cd ..\pytorch_binding
   pip install -e . --no-build-isolation
   ```

4. Copy the DLL:

   ```cmd
   copy ..\build\warprnnt.dll warprnnt_pytorch\
   ```

5. Verify installation:

   ```cmd
   python -c "import warprnnt_pytorch; print('WarpRNNT successfully imported!')"
   ```

---

## Quick Start

```python
import torch
from warprnnt_pytorch import RNNTLoss

# Initialize loss function
rnnt_loss = RNNTLoss()

# Prepare inputs
acts = torch.FloatTensor([[[
    [0.1, 0.6, 0.1, 0.1, 0.1],
    [0.1, 0.1, 0.6, 0.1, 0.1],
    [0.1, 0.1, 0.2, 0.8, 0.1]
], [
    [0.1, 0.6, 0.1, 0.1, 0.1],
    [0.1, 0.1, 0.2, 0.1, 0.1],
    [0.7, 0.1, 0.2, 0.1, 0.1]
]]])

labels = torch.IntTensor([[1, 2]])
act_length = torch.IntTensor([2])
label_length = torch.IntTensor([2])

# Optional: Move to GPU
use_cuda = torch.cuda.is_available()
if use_cuda:
    acts = acts.cuda()
    labels = labels.cuda()
    act_length = act_length.cuda()
    label_length = label_length.cuda()

# Compute loss
acts.requires_grad = True
loss = rnnt_loss(acts, labels, act_length, label_length)
loss.backward()

print(f"Loss: {loss.item()}")
```

---

## API Reference

### `RNNTLoss`

```python
RNNTLoss(size_average=True, blank_label=0)
```

**Parameters:**
- `size_average` (bool, optional): If `True`, normalizes the loss by batch size. Default: `True`
- `blank_label` (int, optional): Index of the blank label. Default: `0`

### `forward`

```python
forward(acts, labels, act_lens, label_lens)
```

**Parameters:**
- `acts` (Tensor): Network outputs of shape `[batch, seqLength, labelLength+1, outputDim]`
  - Contains log probabilities over the vocabulary for each time step
- `labels` (Tensor): Ground truth labels of shape `[batch, max_label_length]`
  - Zero-padded target sequences
- `act_lens` (Tensor): Actual sequence lengths of shape `[batch]`
  - Contains the valid length of each sequence in `acts`
- `label_lens` (Tensor): Actual label lengths of shape `[batch]`
  - Contains the valid length of each label sequence

**Returns:**
- Loss value (scalar Tensor)

---

## Troubleshooting

### Error: `cuda_runtime_api.h: No such file or directory`

This error indicates that CUDA headers cannot be found. Even if CUDA is installed (e.g., version 12.9), the compiler may not know where to look.

**Solution:**

If your CUDA installation is at `/usr/local/cuda-12.9`, set these environment variables:

```bash
export CUDA_HOME=/usr/local/cuda-12.9
export CFLAGS="-I$CUDA_HOME/targets/x86_64-linux/include"
export LDFLAGS="-L$CUDA_HOME/targets/x86_64-linux/lib"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"
```

Then reinstall:

```bash
pip install .
```

### Library Not Found Errors

If you see errors about missing `libwarprnnt.so` or `warprnnt.dll`:

**Linux/macOS:**
```bash
export LD_LIBRARY_PATH=/path/to/warprnnt/build:$LD_LIBRARY_PATH
```

**Windows:**
Ensure `warprnnt.dll` is copied to the `warprnnt_pytorch\` directory as shown in the installation steps.

### Import Errors

Verify your installation:

```bash
python -c "import warprnnt_pytorch; print(warprnnt_pytorch.__file__)"
```

If this fails, try reinstalling with verbose output:

```bash
pip install . -v
```

---

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests to the [WarpRNNT repository](https://github.com/ljn7/warp-transducer).

## License

This project follows the license of the parent WarpRNNT library. Please refer to the [main repository](https://github.com/ljn7/warp-transducer) for details.

## Acknowledgments

Built on top of the excellent [WarpRNNT](https://github.com/HawkAaron/warp-transducer) library by HawkAaron.

---

## Links

- **WarpRNNT Library**: https://github.com/ljn7/warp-transducer
- **PyTorch**: https://pytorch.org
- **CUDA Toolkit**: https://developer.nvidia.com/cuda-downloads
