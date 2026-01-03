# Rubix Recorder API

A RESTful API server for controlling the Rubix44 audio recorder from a Windows machine, designed for integration with XOR continuous recording programs.

## Features

- RESTful API for controlling Rubix44 audio recording
- Cross-platform compatibility (Windows, Linux, Mac)
- Playback file management
- Recording session control
- Device detection and configuration
- Easy integration with external programs like XOR

## Prerequisites

- Python 3.10+
- Conda or Miniconda
- Rubix44 audio interface
- Playback WAV files

## Installation

### Using Conda (Recommended)

1. Clone or download this repository
2. Create the conda environment:
   ```bash
   conda env create -f environment.yml
   ```
3. Activate the environment:
   ```bash
   conda activate rubix-recorder-api
   ```

### Using Pip

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the API Server

#### On Windows:
```cmd
start_api_server.bat
```

#### On Linux/Mac:
```bash
./start_api_server.sh
```

#### Manual start:
```bash
python api_server.py
```

The server will start on `http://localhost:5000` by default.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/config` | GET/PUT | Get/update configuration |
| `/api/v1/devices` | GET | List audio devices |
| `/api/v1/devices/rubix` | GET | Find Rubix44 device |
| `/api/v1/playback-files` | GET | List playback files |
| `/api/v1/recordings/start` | POST | Start recording |
| `/api/v1/recordings/stop` | POST | Stop recording |
| `/api/v1/recordings/status` | GET | Get recording status |
| `/api/v1/recordings/history` | GET | Get recording history |

### Example: Starting a Recording

```bash
curl -X POST http://localhost:5000/api/v1/recordings/start \
  -H "Content-Type: application/json" \
  -d '{
    "playback_file": "playback_files/sample.wav",
    "duration": 3600,
    "output_prefix": "my_recording"
  }'
```

### Integration with XOR Program

Use the provided `xor_client.py` library for easy integration:

```python
from xor_client import create_recorder_client, start_xor_recording

# Create client
client = create_recorder_client("http://localhost:5000")

# Start recording
session_id = start_xor_recording(
    client, 
    "playback_files/sample.wav", 
    duration=3600
)
```

## Testing

Run the test suite to verify the API is working:

```bash
python test_api.py
```

## Directory Structure

- `playback_files/` - WAV files for playback during recording
- `recordings/` - Recorded audio files (auto-generated)
- `logs/` - Server log files (auto-generated)
- `config/` - Configuration files (auto-generated)

## Configuration

The server can be configured via `config/api_config.json` (auto-generated on first run):

```json
{
  "host": "0.0.0.0",
  "port": 5000,
  "debug": false,
  "default_duration": 3600,
  "sample_rate": 44100,
  "output_prefix": "api_recording",
  "playback_directory": "playback_files",
  "recordings_directory": "recordings"
}
```

## Troubleshooting

### Rubix44 Not Detected

1. Ensure the device is connected via USB
2. Check that the device is powered on
3. Verify drivers are installed (if required)
4. Run with `--list-devices` flag to see available devices

### Permission Issues on Windows

- Run the command prompt as Administrator
- Ensure antivirus software isn't blocking the application

## Development

### Adding New Playback Files

Place WAV files in the `playback_files/` directory. They will be automatically available through the API.

### Extending the API

Modify `api_server.py` to add new endpoints or functionality.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request