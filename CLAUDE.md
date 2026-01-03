# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rubix Recorder is a Python-based audio recording tool designed for the Rubix44 audio interface. It records two-channel audio while simultaneously playing back a WAV file through the Rubix44 outputs. The primary use case is capturing audio while playing test signals or reference tracks.

## Environment Setup

This project uses conda for environment management:

```bash
# Create and activate environment
conda env create -f environment.yml
conda activate audio-recorder

# Verify setup
python test_setup.py
```

The environment is named `audio-recorder` and includes:
- Python 3.10
- sounddevice (audio I/O)
- soundfile (WAV reading/writing)
- scipy and numpy (audio processing)

## Common Commands

### Running the Recorder

```bash
# Basic usage - record with playback
python rubix_recorder.py playback_files/your_file.wav

# Custom duration (default is 3600 seconds / 1 hour)
python rubix_recorder.py playback_files/your_file.wav --duration 60

# Custom sample rate (default is 44100 Hz)
python rubix_recorder.py playback_files/your_file.wav --rate 48000

# Custom output prefix (default is 'recording')
python rubix_recorder.py playback_files/your_file.wav --output mysession

# List available audio devices
python rubix_recorder.py --list-devices

# Quick recording using shell script
./quick_record.sh  # Edit script first to set parameters
```

### Manual device selection

If auto-detection fails:

```bash
python rubix_recorder.py playback_files/your_file.wav \
    --input-device 2 \
    --output-device 2
```

## Architecture

### Core Component: AudioRecorder Class

The `AudioRecorder` class in [rubix_recorder.py](rubix_recorder.py) handles all recording logic:

- **Device Detection**: `find_device()` automatically locates Rubix44 by searching device names for 'rubix'
- **Dual Audio Streams**: Uses threading to run playback and recording simultaneously
  - Playback runs in a separate thread via `threading.Thread`
  - Recording uses `sounddevice.rec()` on the main thread
  - 100ms delay ensures playback starts before recording begins
- **File Handling**: Outputs three files per session:
  - `*_stereo.wav` - combined stereo recording
  - `*_ch1.wav` - isolated channel 1
  - `*_ch2.wav` - isolated channel 2
- **Playback Looping**: If playback file is shorter than recording duration, it automatically tiles/loops the audio

### Audio Flow

1. User provides WAV file for playback and recording duration
2. Script auto-detects Rubix44 input and output devices
3. Playback thread starts, looping file if needed to match duration
4. Recording captures 2 channels from Rubix44 inputs
5. Both operations run concurrently until duration expires
6. Three WAV files saved to `recordings/` with timestamp

### Directory Structure

- `rubix_recorder.py` - Main recording script with AudioRecorder class
- `test_setup.py` - Environment verification and device detection test
- `quick_record.sh` - Convenience script for repeated recording sessions
- `playback_files/` - Store WAV files for playback here
- `recordings/` - Output directory for all recordings (created automatically)
- `logs/` - Log directory (currently unused)
- `environment.yml` - Conda environment specification

## Key Implementation Details

### Sample Rate Handling

The recorder does NOT automatically resample playback files. If playback sample rate differs from recording sample rate (default 44100 Hz), it prints a warning but continues. For best results, convert playback files to match the recording sample rate beforehand.

### Device Auto-Detection

Device detection searches for 'rubix' (case-insensitive) in device names. For input devices, it verifies `max_input_channels > 0`. For output devices, it checks `max_output_channels > 0`. If auto-detection fails, the script raises a RuntimeError with troubleshooting steps.

### Mono to Stereo Conversion

If the playback file is mono, it's automatically converted to stereo by duplicating the mono channel to both left and right channels.

### Recording Format

All recordings are saved as WAV files with:
- Sample rate: 44100 Hz (or user-specified via `--rate`)
- Bit depth: Determined by soundfile library (typically 16-bit or 24-bit)
- Channels: 2 (stereo)
- Filenames include timestamp: `YYYY-MM-DD_HH-MM-SS`
