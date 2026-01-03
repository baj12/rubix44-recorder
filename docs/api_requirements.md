# Rubix Recorder API Requirements

## Overview
This document outlines the requirements for a RESTful API that will control the Rubix44 audio recorder from a Windows machine. The API will allow external programs (like the XOR continuous recording program) to control recording sessions programmatically.

## Target Platform
- Primary: Windows (older machines)
- Secondary: Cross-platform compatibility
- Python 3.10+
- Conda environment management

## Core Functionalities

### 1. Recording Control
- Start recording with playback
- Stop recording
- Pause/resume functionality
- Get recording status

### 2. Playback Management
- List available playback files
- Upload new playback files
- Delete playback files
- Preview playback files

### 3. Device Management
- List available audio devices
- Select input/output devices
- Check device connectivity
- Get device information

### 4. Recording Management
- List past recordings
- Retrieve recording metadata
- Download recording files
- Delete recordings

### 5. Configuration
- Set recording parameters (duration, sample rate, etc.)
- Get current configuration
- Save/load configurations

## API Endpoints

### Authentication
```
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET /api/v1/auth/status
```

### Device Management
```
GET /api/v1/devices
GET /api/v1/devices/rubix
POST /api/v1/devices/select
```

### Recording Control
```
POST /api/v1/recordings/start
POST /api/v1/recordings/stop
POST /api/v1/recordings/pause
POST /api/v1/recordings/resume
GET /api/v1/recordings/status
GET /api/v1/recordings/history
```

### Playback Files
```
GET /api/v1/playback-files
POST /api/v1/playback-files
DELETE /api/v1/playback-files/{id}
GET /api/v1/playback-files/{id}
```

### Recordings
```
GET /api/v1/recordings
GET /api/v1/recordings/{id}
DELETE /api/v1/recordings/{id}
GET /api/v1/recordings/{id}/download
```

### Configuration
```
GET /api/v1/config
PUT /api/v1/config
GET /api/v1/config/default
```

## Data Models

### Device
```json
{
  "id": "integer",
  "name": "string",
  "input_channels": "integer",
  "output_channels": "integer",
  "sample_rates": "array",
  "is_rubix": "boolean",
  "status": "string"
}
```

### RecordingSession
```json
{
  "id": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "duration": "integer",
  "status": "string",
  "playback_file": "string",
  "recordings": "array"
}
```

### RecordingFile
```json
{
  "id": "string",
  "filename": "string",
  "channel": "integer",
  "size": "integer",
  "duration": "integer",
  "sample_rate": "integer",
  "created_at": "datetime"
}
```

### Configuration
```json
{
  "default_duration": "integer",
  "sample_rate": "integer",
  "output_prefix": "string",
  "auto_detect_devices": "boolean"
}
```

## Security Requirements
- Token-based authentication
- HTTPS support
- Rate limiting
- Input validation
- CORS configuration

## Performance Requirements
- Low latency response times (< 100ms for control commands)
- Concurrent session handling
- Efficient file streaming for downloads
- Minimal resource usage on older hardware

## Integration Points
- XOR continuous recording program
- External monitoring systems
- Web-based control interface