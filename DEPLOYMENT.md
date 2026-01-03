# Deployment and Usage Guide

## Deployment Options

### Option 1: Direct Installation (Recommended for Windows)

1. Install Anaconda or Miniconda
2. Create the conda environment:
   ```bash
   conda env create -f environment.yml
   ```
3. Activate the environment:
   ```bash
   conda activate rubix-recorder-api
   ```
4. Start the server:
   - On Windows: Double-click `start_api_server.bat` or run from command prompt
   - On Linux/Mac: Run `./start_api_server.sh`

### Option 2: Docker Deployment

1. Install Docker and Docker Compose
2. Build and start the containers:
   ```bash
   docker-compose up -d
   ```
3. Access the API at `http://localhost:5000`

### Option 3: Manual Docker Build

1. Build the Docker image:
   ```bash
   docker build -t rubix-recorder-api .
   ```
2. Run the container:
   ```bash
   docker run -p 5000:5000 -v $(pwd)/recordings:/app/recordings -v $(pwd)/playback_files:/app/playback_files rubix-recorder-api
   ```

## Usage Procedures

### Preparing Playback Files

1. Place WAV files in the `playback_files/` directory
2. Ensure files are in proper WAV format (44.1kHz recommended)
3. Files will be automatically available through the API

### Starting Recordings via API

Use any HTTP client to interact with the API:

```bash
# Start a recording session
curl -X POST http://localhost:5000/api/v1/recordings/start \
  -H "Content-Type: application/json" \
  -d '{
    "playback_file": "playback_files/sample.wav",
    "duration": 3600,
    "output_prefix": "session"
  }'

# Check recording status
curl http://localhost:5000/api/v1/recordings/status

# Stop recording (if needed)
curl -X POST http://localhost:5000/api/v1/recordings/stop
```

### Integration with XOR Continuous Recording Program

Use the provided `xor_client.py` library:

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

# Monitor progress
status = client.get_recording_status()
print(f"Status: {status.get('status')}")
```

## Configuration

### Server Configuration

Edit `config/api_config.json` to customize:

```json
{
  "host": "0.0.0.0",
  "port": 5000,
  "debug": false,
  "default_duration": 3600,
  "sample_rate": 44100,
  "output_prefix": "api_recording"
}
```

### Environment Variables

- `FLASK_ENV`: Set to "development" or "production"
- `FLASK_DEBUG`: Enable/disable debug mode

## Monitoring and Maintenance

### Log Files

Check logs in the `logs/` directory:
- `logs/api_server.log`: Main application logs
- System logs will be visible in the terminal/console

### Health Checks

Monitor the health endpoint:
```bash
curl http://localhost:5000/api/v1/health
```

### Backup Procedures

Regularly backup:
- `recordings/` directory (contains all recorded files)
- `config/` directory (contains configuration)

## Troubleshooting

### Common Issues

1. **Rubix44 Not Detected**
   - Ensure device is connected via USB
   - Check that device is powered on
   - Verify drivers are installed
   - Run with `--list-devices` flag

2. **Permission Errors**
   - Run as Administrator (Windows)
   - Check file/folder permissions (Linux/Mac)

3. **Port Already in Use**
   - Change port in configuration
   - Kill existing process using the port

4. **Playback File Not Found**
   - Verify file exists in `playback_files/` directory
   - Check file format (must be WAV)

### Recovery Procedures

1. **Restart Server**: Stop and restart the API server
2. **Reset Configuration**: Delete `config/api_config.json` to reset to defaults
3. **Clear Logs**: Delete log files in `logs/` directory if they become too large

## Updating the Application

### Git Updates

Pull the latest changes:
```bash
git pull origin main
```

Update dependencies:
```bash
conda env update -f environment.yml
```

### Docker Updates

Rebuild and restart containers:
```bash
docker-compose down
docker-compose up --build -d
```

## Security Considerations

### Network Security

- By default, the server binds to all interfaces (0.0.0.0)
- For production, bind to localhost (127.0.0.1) or internal network only
- Use a reverse proxy (nginx) for public deployments

### File Security

- Playback files should be validated before use
- Restrict write access to recordings directory
- Regularly audit file permissions

## Performance Optimization

### Hardware Recommendations

- CPU: Dual-core 2GHz+ processor
- RAM: 4GB minimum, 8GB recommended
- Storage: SSD preferred for recording storage
- Audio Interface: Rubix44 connected via USB 2.0+

### Resource Management

- Monitor disk space regularly
- Clean old recordings periodically
- Limit concurrent recording sessions