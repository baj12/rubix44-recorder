# Rubix Recorder API Documentation

## Overview

The Rubix Recorder API provides a RESTful interface for controlling audio recording sessions with a Rubix44 audio interface. The API allows external programs to start/stop recordings, manage playback files, and retrieve recording status and history.

## Base URL

All endpoints are prefixed with `/api/v1`:

```
http://localhost:5000/api/v1
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing token-based authentication.

## Error Handling

All errors are returned in JSON format with appropriate HTTP status codes:

```json
{
  "error": "Error message describing the issue"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

## API Endpoints

### Health Check

#### GET `/health`
Check if the API server is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-03T12:23:41.584Z",
  "service": "Rubix Recorder API"
}
```

### Configuration

#### GET `/config`
Retrieve current server configuration.

**Response:**
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

#### PUT `/config`
Update server configuration.

**Request Body:**
```json
{
  "port": 5001,
  "debug": true
}
```

**Response:**
```json
{
  "message": "Configuration updated",
  "config": {
    // Updated configuration
  }
}
```

### Device Management

#### GET `/devices`
List all available audio devices.

**Response:**
```json
[
  {
    "id": 0,
    "name": "Rubix44 USB Audio Interface",
    "input_channels": 18,
    "output_channels": 20,
    "sample_rate": 44100,
    "is_default_input": false,
    "is_default_output": false
  }
]
```

#### GET `/devices/rubix`
Find the Rubix44 device specifically.

**Response:**
```json
{
  "found": true,
  "input_device": 0,
  "output_device": 0,
  "input_device_info": {
    "id": 0,
    "name": "Rubix44 USB Audio Interface",
    "channels": 18,
    "sample_rate": 44100
  },
  "output_device_info": {
    "id": 0,
    "name": "Rubix44 USB Audio Interface",
    "channels": 20,
    "sample_rate": 44100
  }
}
```

### Playback Files

#### GET `/playback-files`
List all available playback files.

**Response:**
```json
[
  {
    "name": "sample.wav",
    "path": "playback_files/sample.wav",
    "size": 1024000,
    "modified": "2026-01-03T12:00:00.000Z"
  }
]
```

### Recording Control

#### POST `/recordings/start`
Start a new recording session.

**Request Body:**
```json
{
  "playback_file": "playback_files/sample.wav",
  "duration": 3600,
  "sample_rate": 44100,
  "output_prefix": "my_session"
}
```

**Response:**
```json
{
  "message": "Recording started",
  "session": {
    "id": "20260103_120000",
    "playback_file": "playback_files/sample.wav",
    "start_time": "2026-01-03T12:00:00.000Z",
    "end_time": null,
    "duration": 3600,
    "sample_rate": 44100,
    "output_prefix": "my_session",
    "status": "recording",
    "files": [],
    "error": null
  }
}
```

#### POST `/recordings/stop`
Stop the current recording session.

**Response:**
```json
{
  "message": "Recording stopped",
  "session": {
    "id": "20260103_120000",
    "playback_file": "playback_files/sample.wav",
    "start_time": "2026-01-03T12:00:00.000Z",
    "end_time": "2026-01-03T13:00:00.000Z",
    "duration": 3600,
    "sample_rate": 44100,
    "output_prefix": "my_session",
    "status": "completed",
    "files": [
      "recordings/my_session_2026-01-03_12-00-00_stereo.wav",
      "recordings/my_session_2026-01-03_12-00-00_ch1.wav",
      "recordings/my_session_2026-01-03_12-00-00_ch2.wav"
    ],
    "error": null
  }
}
```

#### GET `/recordings/status`
Get the status of the current recording session.

**Response:**
```json
{
  "id": "20260103_120000",
  "playback_file": "playback_files/sample.wav",
  "start_time": "2026-01-03T12:00:00.000Z",
  "end_time": null,
  "duration": 3600,
  "sample_rate": 44100,
  "output_prefix": "my_session",
  "status": "recording",
  "files": [],
  "error": null
}
```

#### GET `/recordings/history`
Get history of past recordings.

**Response:**
```json
[
  {
    "id": "my_session_2026-01-03_12-00-00",
    "prefix": "my_session",
    "timestamp": "2026-01-03_12-00-00",
    "files": [
      {
        "name": "my_session_2026-01-03_12-00-00_stereo.wav",
        "path": "recordings/my_session_2026-01-03_12-00-00_stereo.wav",
        "size": 1024000,
        "modified": "2026-01-03T13:00:00.000Z"
      }
    ]
  }
]
```

#### GET `/recordings/{filename}`
Download a recording file.

**Response:**
Binary file content with appropriate Content-Disposition header.

## Client Library Usage

For easy integration, use the provided Python client library:

```python
from xor_client import RubixRecorderClient

# Create client
client = RubixRecorderClient("http://localhost:5000")

# Start recording
result = client.start_recording(
    playback_file="playback_files/sample.wav",
    duration=3600
)

# Check status
status = client.get_recording_status()
print(f"Status: {status.get('status')}")
```

## Data Models

### Device
```json
{
  "id": "integer",
  "name": "string",
  "input_channels": "integer",
  "output_channels": "integer",
  "sample_rate": "integer",
  "is_default_input": "boolean",
  "is_default_output": "boolean"
}
```

### RecordingSession
```json
{
  "id": "string",
  "playback_file": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "duration": "integer",
  "sample_rate": "integer",
  "output_prefix": "string",
  "status": "string",
  "files": "array",
  "error": "string"
}
```

### Configuration
```json
{
  "host": "string",
  "port": "integer",
  "debug": "boolean",
  "default_duration": "integer",
  "sample_rate": "integer",
  "output_prefix": "string",
  "playback_directory": "string",
  "recordings_directory": "string"
}
```

## Rate Limiting

The API does not currently implement rate limiting. For production use, consider adding rate limiting middleware.

## Versioning

The API is currently at version 1 (`/api/v1`). Future versions will be accessible at `/api/v2`, etc.

## Changelog

### v1.0.0
- Initial release
- Basic recording functionality
- Device management
- Configuration management
- Playback file management