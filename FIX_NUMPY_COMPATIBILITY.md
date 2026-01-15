# Fix for "Illegal Instruction" Error on Windows

## Problem
The Windows machine has an Intel Core i7-3610QM CPU (Ivy Bridge, 2012) which supports AVX but NOT AVX2.
NumPy 2.2.6 requires AVX2 instructions, causing "illegal instruction" errors.

## Solution
Downgrade NumPy to version 1.26.4 (last version with good AVX-only support for Python 3.10)

## Steps to Fix (Run on Windows machine)

### Option 1: Quick Fix
```bash
# Activate the conda environment
conda activate rubix-recorder-api

# Downgrade numpy to version compatible with AVX (not AVX2)
pip install "numpy<2.0"

# Verify it works
python -c "import numpy; print(f'NumPy {numpy.__version__} loaded successfully')"

# Restart the API server
python api_server.py
```

### Option 2: Complete Reinstall
```bash
# Activate the conda environment
conda activate rubix-recorder-api

# Uninstall current numpy
pip uninstall -y numpy

# Install numpy 1.26.4 (last 1.x release, well-tested, AVX compatible)
pip install numpy==1.26.4

# Verify installation
python -c "import numpy; print(f'NumPy {numpy.__version__} loaded successfully')"
python -c "import scipy; print('SciPy OK')"
python -c "import sounddevice; print('Sounddevice OK')"
python -c "import soundfile; print('Soundfile OK')"

# Restart the API server
python api_server.py
```

### Option 3: Update environment.yml (Recommended for long-term)
Update the `environment.yml` file to pin NumPy version:

```yaml
name: rubix-recorder-api
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.10
  - scipy
  - pip
  - pip:
    - numpy==1.26.4  # Pin to 1.x for AVX compatibility (not AVX2)
    - flask==2.3.3
    - flask-cors==4.0.0
    - sounddevice>=0.4.6
    - soundfile>=0.12.1
    - python-dateutil>=2.8.2
```

Then recreate the environment:
```bash
conda env remove -n rubix-recorder-api
conda env create -f environment.yml
conda activate rubix-recorder-api
```

## Why This Happens

- **NumPy 2.0+** (released 2024) uses AVX2 instructions for performance
- **Your CPU** (Intel i7-3610QM, 2012) supports AVX but not AVX2
- **AVX2** was introduced with Intel Haswell CPUs in 2013
- **NumPy 1.26.x** works with AVX-only CPUs

## Verification

After downgrading, verify everything works:
```bash
# Test imports
python -c "import numpy; import scipy; import sounddevice; import soundfile; print('All modules OK')"

# Run the test suite
python test_api_changes.py
```

## Future Considerations

If you upgrade the Windows machine's CPU to anything from 2013 or later (Haswell, Broadwell, Skylake, etc.),
you can safely use NumPy 2.x again.

For now, NumPy 1.26.4 is:
- Stable and well-tested
- Fully compatible with your CPU
- Supports all features needed by this application
