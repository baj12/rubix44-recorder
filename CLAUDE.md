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

## API Server

The project includes a RESTful API server ([api_server.py](api_server.py)) for remote control of recording sessions.

### Running the API Server

```bash
# Activate environment
conda activate rubix-recorder-api

# Start the server
python api_server.py

# Server runs on http://0.0.0.0:5000 by default
```

### Key API Endpoints

#### Complete Status - `GET /api/v1/status`
Comprehensive endpoint that provides:
- **Rubix Connection Status**: Whether Rubix44 is connected, with input/output device details (ID, name, channels, sample rate)
- **Current Recording Session**: Full session details if recording is in progress
- **System Configuration**: Default settings for duration, sample rate, output paths

Example response when recording:
```json
{
  "timestamp": "2025-11-30T14:30:45.123456",
  "service": "Rubix Recorder API",
  "version": "1.0.0",
  "rubix": {
    "connected": true,
    "input_device": {
      "id": 2,
      "name": "Rubix44",
      "channels": 4,
      "sample_rate": 44100
    },
    "output_device": { ... }
  },
  "recording": {
    "id": "20251130_143045",
    "human_id": "swift-panda-2347",
    "status": "recording",
    "playback_file": "test.wav",
    "duration": 3600,
    "sample_rate": 44100,
    "channels": 2,
    "elapsed_seconds": 125.4,
    "progress_percent": 3.48,
    ...
  },
  "config": { ... }
}
```

#### Recording Management
- `POST /api/v1/recordings/start` - Start a new recording session
  - Accepts: `playback_file`, `duration`, `sample_rate`, `output_prefix`, `input_device`, `output_device`
  - Returns: Session info with unique `id` and human-readable `human_id`
- `POST /api/v1/recordings/stop` - Stop current recording
- `GET /api/v1/recordings/status` - Get current session status
- `GET /api/v1/recordings/history` - List past recordings
- `POST /api/v1/recordings/delete` - Delete a recording session
  - Accepts: `session_id` (technical ID like `20251130_143045`)
  - Deletes all associated files (stereo, ch1, ch2)
- `POST /api/v1/recordings/transfer` - Transfer recording to storage server
  - Accepts: `session_id`, `delete_after_transfer` (optional, default: false)
  - Transfers files using configured protocol (scp, rsync, http)
  - Optionally deletes local files after successful transfer

#### Device Information
- `GET /api/v1/devices` - List all audio devices
- `GET /api/v1/devices/rubix` - Find Rubix44 device specifically

#### Playback Files
- `GET /api/v1/playback-files` - List available playback files with metadata (duration, sample rate, channels)

#### Storage Server Management
- `GET /api/v1/storage/config` - Get storage server configuration
- `PUT /api/v1/storage/config` - Update storage server configuration
  - Accepts: `enabled`, `host`, `port`, `protocol`, `username`, `remote_path`, `auto_transfer`
  - Supported protocols: `scp`, `sftp`, `rsync`, `http`

### Human-Readable Session IDs

Each recording session gets two identifiers:
1. **Technical ID** (`id`): Timestamp-based like `20251130_143045`
2. **Human ID** (`human_id`): Memorable format like `swift-panda-2347`

The human ID makes it easier to reference and discuss specific recording sessions.

### Storage Server Configuration

The API supports automatic or manual transfer of recordings to a remote storage server. Configure via the `/api/v1/storage/config` endpoint:

```json
{
  "enabled": true,
  "host": "storage.example.com",
  "port": 22,
  "protocol": "scp",
  "username": "recorder",
  "remote_path": "/data/recordings",
  "auto_transfer": false
}
```

**Supported protocols:**
- `scp` - Secure copy (requires SSH keys or password-less auth)
- `rsync` - Rsync over SSH (efficient for multiple files)
- `http` - HTTP POST upload to a web server
- `sftp` - SFTP transfer (not yet implemented)

**Usage:**
- Set `auto_transfer: true` to automatically transfer recordings after completion
- Use `/api/v1/recordings/transfer` endpoint to manually transfer specific sessions
- Add `delete_after_transfer: true` to remove local files after successful transfer
