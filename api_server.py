#!/usr/bin/env python3
"""
RESTful API Server for Rubix44 Audio Recorder
Provides HTTP endpoints to control recording sessions remotely.
"""

import json
import logging
import os
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Import Flask components
try:
    from flask import Flask, jsonify, request, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("Flask not found. Please install with: pip install flask flask-cors")
    sys.exit(1)

# Add the current directory to Python path to import rubix_recorder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rubix_recorder import AudioRecorder
except ImportError as e:
    print(f"Error importing rubix_recorder: {e}")
    print("Make sure rubix_recorder.py is in the same directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables for recording management
current_recording_session = None
recording_thread = None
recording_lock = threading.Lock()

# Configuration
CONFIG_FILE = 'config/api_config.json'
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": False,
    "default_duration": 3600,
    "sample_rate": 44100,
    "output_prefix": "api_recording",
    "playback_directory": "playback_files",
    "recordings_directory": "recordings",
    "storage_server": {
        "enabled": False,
        "host": "",
        "port": 22,
        "protocol": "scp",  # scp, sftp, rsync, http
        "username": "",
        "remote_path": "",
        "auto_transfer": False  # Automatically transfer after recording completes
    }
}

def load_config():
    """Load configuration from file or use defaults"""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.warning(f"Error loading config file: {e}")
    return config

def save_config(config):
    """Save configuration to file"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config file: {e}")
        return False


# Load configuration
config = load_config()

# Enable debug logging for remote debugging
if config.get("debug", False):
    logging.getLogger().setLevel(logging.DEBUG)

# Ensure directories exist
os.makedirs(config["playback_directory"], exist_ok=True)
os.makedirs(config["recordings_directory"], exist_ok=True)

# Word lists for human-readable identifiers
ADJECTIVES = [
    'swift', 'bright', 'calm', 'bold', 'clear', 'deep', 'eager', 'fair',
    'gentle', 'happy', 'keen', 'light', 'merry', 'noble', 'quick', 'warm',
    'wise', 'brave', 'cool', 'deft', 'fine', 'grand', 'jolly', 'kind',
    'lively', 'proud', 'sharp', 'smooth', 'sound', 'sweet', 'vital', 'wild'
]

NOUNS = [
    'panda', 'tiger', 'eagle', 'dolphin', 'falcon', 'phoenix', 'dragon', 'wolf',
    'bear', 'hawk', 'lynx', 'otter', 'raven', 'seal', 'swan', 'whale',
    'bison', 'crane', 'deer', 'fox', 'heron', 'jaguar', 'koala', 'lion',
    'moose', 'owl', 'panther', 'quail', 'robin', 'stork', 'turtle', 'viper'
]

def generate_human_readable_id():
    """Generate a human-readable identifier like 'swift-panda-2347'"""
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    number = random.randint(1000, 9999)
    return f"{adjective}-{noun}-{number}"

class RecordingSession:
    """Represents a recording session"""
    def __init__(self, playback_file, duration=None, sample_rate=None, output_prefix=None,
                 input_device=None, output_device=None):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.human_id = generate_human_readable_id()  # Human-readable unique identifier
        self.playback_file_path = playback_file  # Full path to the playback file
        self.playback_file = os.path.basename(playback_file)  # Just the filename for API responses
        self.start_time = None
        self.end_time = None
        self.duration = duration or config["default_duration"]
        self.sample_rate = sample_rate or config["sample_rate"]
        self.output_prefix = output_prefix or config["output_prefix"]
        self.input_device = input_device  # Device ID or name for input
        self.output_device = output_device  # Device ID or name for output
        self.status = "initialized"  # initialized, recording, completed, error, stopped
        self.files = []
        self.error = None
        self.recorder = None  # Reference to the AudioRecorder instance
        self.actual_duration = 0  # Actual recording duration in seconds
        self.channels = 2  # Number of recording channels
        
    def get_elapsed_seconds(self):
        """Calculate elapsed seconds since recording started"""
        if self.start_time and self.status == "recording":
            return (datetime.now() - self.start_time).total_seconds()
        return 0
        
    def to_dict(self):
        result = {
            "id": self.id,
            "human_id": self.human_id,
            "playback_file": self.playback_file,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "output_prefix": self.output_prefix,
            "input_device": self.input_device,
            "output_device": self.output_device,
            "status": self.status,
            "files": self.files,
            "error": self.error
        }

        # Add elapsed time if recording is in progress
        if self.status == "recording" and self.start_time:
            result["elapsed_seconds"] = self.get_elapsed_seconds()
            result["expected_duration"] = self.duration
            result["progress_percent"] = (self.get_elapsed_seconds() / self.duration * 100) if self.duration > 0 else 0

        return result

def start_recording_in_thread(session):
    """Start recording in a separate thread"""
    global current_recording_session
    
    logger.debug(f"Starting recording thread for session {session.id}")
    with recording_lock:
        current_recording_session = session
        session.status = "recording"
        session.start_time = datetime.now()
        logger.debug(f"Session {session.id} status set to recording at {session.start_time}")
        
    try:
        # Create recorder instance
        logger.debug(f"Creating AudioRecorder with duration={session.duration}, sample_rate={session.sample_rate}")
        recorder = AudioRecorder(
            input_device=session.input_device,
            output_device=session.output_device,
            duration=session.duration,
            sample_rate=session.sample_rate
        )
        
        # Store recorder reference in session
        session.recorder = recorder
        logger.debug(f"Stored recorder reference for session {session.id}")
        
        # Start recording with playback
        logger.debug(f"Calling record_with_playback with playback_file={session.playback_file_path}, output_prefix={session.output_prefix}")
        success = recorder.record_with_playback(
            session.playback_file_path,  # Use the full path
            session.output_prefix
        )
        logger.debug(f"record_with_playback returned success={success}")
        
        with recording_lock:
            if success or session.status == "stopped":  # Accept both completed and stopped
                if session.status != "stopped":
                    session.status = "completed"
                session.end_time = datetime.now()
                logger.debug(f"Session {session.id} completed at {session.end_time} with status {session.status}")
                
                # Calculate actual duration
                if session.start_time and session.end_time:
                    actual_duration = (session.end_time - session.start_time).total_seconds()
                else:
                    actual_duration = session.duration
                logger.debug(f"Actual recording duration: {actual_duration} seconds")
                
                # Collect generated files
                timestamp = session.start_time.strftime("%Y-%m-%d_%H-%M-%S")
                base_path = f"{config['recordings_directory']}/{session.output_prefix}_{timestamp}"
                logger.debug(f"Base path for recording files: {base_path}")
                
                session.files = [
                    f"{base_path}_stereo.wav",
                    f"{base_path}_ch1.wav",
                    f"{base_path}_ch2.wav"
                ]
                
                # Verify files exist and add metadata
                verified_files = []
                for file_path in session.files:
                    logger.debug(f"Checking if file exists: {file_path}")
                    if os.path.exists(file_path):
                        stat = os.stat(file_path)
                        verified_files.append({
                            "name": os.path.basename(file_path),
                            "path": file_path,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                        logger.debug(f"File exists and added to session: {file_path}")
                    else:
                        logger.warning(f"File does not exist: {file_path}")
                session.files = verified_files
                
                # Add duration to session for history
                session.actual_duration = actual_duration
                logger.debug(f"Session {session.id} files verified: {len(session.files)} files found")
            else:
                session.status = "error"
                session.error = "Recording failed"
                logger.error(f"Session {session.id} recording failed")
                
    except Exception as e:
        logger.error(f"Error during recording: {e}", exc_info=True)
        with recording_lock:
            session.status = "error"
            session.error = str(e)
            session.end_time = datetime.now()
    finally:
        with recording_lock:
            current_recording_session = None
            logger.debug(f"Recording thread for session {session.id} completed")

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Rubix Recorder API"
    })

@app.route('/api/v1/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(config)

@app.route('/api/v1/config', methods=['PUT'])
def update_config():
    """Update configuration"""
    global config
    new_config = request.get_json()
    
    if not new_config:
        return jsonify({"error": "No configuration provided"}), 400
    
    # Update config
    config.update(new_config)
    
    # Save to file
    if save_config(config):
        return jsonify({"message": "Configuration updated", "config": config})
    else:
        return jsonify({"error": "Failed to save configuration"}), 500

@app.route('/api/v1/devices', methods=['GET'])
def list_devices():
    """List all available audio devices"""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        device_list = []
        
        for i, device in enumerate(devices):
            device_list.append({
                "id": i,
                "name": device['name'],
                "input_channels": device['max_input_channels'],
                "output_channels": device['max_output_channels'],
                "sample_rate": device['default_samplerate'],
                "is_default_input": device['name'] == sd.query_hostapis(device['hostapi'])['default_input_device'],
                "is_default_output": device['name'] == sd.query_hostapis(device['hostapi'])['default_output_device']
            })
            
        return jsonify(device_list)
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/devices/rubix', methods=['GET'])
def find_rubix_device():
    """Find Rubix44 device"""
    try:
        recorder = AudioRecorder()
        input_id = recorder.find_device('rubix', 'input')
        output_id = recorder.find_device('rubix', 'output')
        
        result = {
            "found": input_id is not None or output_id is not None,
            "input_device": input_id,
            "output_device": output_id
        }
        
        if input_id is not None or output_id is not None:
            import sounddevice as sd
            if input_id is not None:
                input_device = sd.query_devices(input_id)
                result["input_device_info"] = {
                    "id": input_id,
                    "name": input_device['name'],
                    "channels": input_device['max_input_channels'],
                    "sample_rate": input_device['default_samplerate']
                }
            if output_id is not None:
                output_device = sd.query_devices(output_id)
                result["output_device_info"] = {
                    "id": output_id,
                    "name": output_device['name'],
                    "channels": output_device['max_output_channels'],
                    "sample_rate": output_device['default_samplerate']
                }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error finding Rubix device: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/playback-files', methods=['GET'])
def list_playback_files():
    """List all available playback files with metadata"""
    try:
        files = []
        playback_dir = config["playback_directory"]
        
        if os.path.exists(playback_dir):
            for filename in os.listdir(playback_dir):
                if filename.lower().endswith('.wav'):
                    filepath = os.path.join(playback_dir, filename)
                    stat = os.stat(filepath)
                    
                    # Try to get audio file metadata
                    duration_seconds = 0
                    sample_rate = config["sample_rate"]
                    channels = 2
                    format = "WAV"
                    
                    try:
                        import soundfile as sf
                        info = sf.info(filepath)
                        duration_seconds = info.duration
                        sample_rate = info.samplerate
                        channels = info.channels
                    except Exception:
                        # If we can't read the file, use defaults
                        pass
                    
                    files.append({
                        "filename": filename,
                        "path": filepath,
                        "size": stat.st_size,
                        "duration_seconds": duration_seconds,
                        "sample_rate": sample_rate,
                        "channels": channels,
                        "format": format,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return jsonify(files)
    except Exception as e:
        logger.error(f"Error listing playback files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/recordings/start', methods=['POST'])
def start_recording():
    """Start a new recording session"""
    global recording_thread
    
    logger.debug("Starting recording request processing")
    
    # Check if already recording
    with recording_lock:
        if current_recording_session and current_recording_session.status == "recording":
            logger.warning("Recording already in progress")
            return jsonify({"error": "Recording already in progress"}), 400
    
    # Get parameters from request
    data = request.get_json()
    logger.debug(f"Received data: {data}")
    
    if not data:
        logger.error("No data provided in request")
        return jsonify({"error": "No data provided"}), 400
    
    playback_file = data.get('playback_file')
    logger.debug(f"Requested playback file: {playback_file}")
    
    if not playback_file:
        logger.error("Playback file not provided")
        return jsonify({"error": "playback_file is required"}), 400
    
    # Verify playback file exists
    if not os.path.exists(playback_file):
        logger.debug(f"Playback file not found at {playback_file}, checking in playback directory")
        # Check in playback directory
        playback_path = os.path.join(config["playback_directory"], playback_file)
        if os.path.exists(playback_path):
            playback_file = playback_path
            logger.debug(f"Found playback file at {playback_file}")
        else:
            logger.error(f"Playback file not found: {playback_file}")
            return jsonify({"error": f"Playback file not found: {playback_file}"}), 404
    
    # Create recording session
    logger.debug(f"Creating recording session with playback file: {playback_file}")
    session = RecordingSession(
        playback_file=playback_file,  # Store the full path
        duration=data.get('duration'),
        sample_rate=data.get('sample_rate'),
        output_prefix=data.get('output_prefix'),
        input_device=data.get('input_device'),
        output_device=data.get('output_device')
    )
    logger.debug(f"Created session with ID: {session.id} (human ID: {session.human_id})")
    
    # Start recording in background thread
    logger.debug("Starting recording thread")
    recording_thread = threading.Thread(
        target=start_recording_in_thread,
        args=(session,),
        daemon=True
    )
    recording_thread.start()
    
    logger.info(f"Started recording session {session.id}")
    logger.debug(f"Session details: {session.to_dict()}")
    return jsonify({
        "message": "Recording started",
        "session": session.to_dict()
    }), 202

@app.route('/api/v1/recordings/stop', methods=['POST'])
def stop_recording():
    """Stop current recording session"""
    with recording_lock:
        if not current_recording_session or current_recording_session.status != "recording":
            return jsonify({"error": "No active recording session"}), 400
        
        # Signal the recorder to stop
        if current_recording_session.recorder:
            current_recording_session.recorder.stop_recording()
        
        # Mark as stopped and set end time
        current_recording_session.status = "stopped"
        current_recording_session.end_time = datetime.now()
        
        # Calculate actual duration
        if current_recording_session.start_time and current_recording_session.end_time:
            actual_duration = (current_recording_session.end_time - current_recording_session.start_time).total_seconds()
        else:
            actual_duration = 0
        
        # Prepare response with actual files
        files_response = []
        if current_recording_session.files:
            files_response = current_recording_session.files
        else:
            # Try to collect files even if recording was stopped early
            timestamp = current_recording_session.start_time.strftime("%Y-%m-%d_%H-%M-%S") if current_recording_session.start_time else ""
            if timestamp:
                base_path = f"{config['recordings_directory']}/{current_recording_session.output_prefix}_{timestamp}"
                for channel in ['_stereo.wav', '_ch1.wav', '_ch2.wav']:
                    file_path = base_path + channel
                    if os.path.exists(file_path):
                        stat = os.stat(file_path)
                        files_response.append({
                            "name": os.path.basename(file_path),
                            "path": file_path,
                            "size": stat.st_size
                        })
        
        logger.info(f"Stopped recording session {current_recording_session.id}")
        return jsonify({
            "success": True,
            "session_id": current_recording_session.id,
            "files": files_response,
            "duration_seconds": actual_duration
        })

@app.route('/api/v1/recordings/status', methods=['GET'])
def get_recording_status():
    """Get status of current recording session"""
    with recording_lock:
        if current_recording_session:
            return jsonify(current_recording_session.to_dict())
        else:
            return jsonify({"status": "idle", "message": "No active recording session"})

@app.route('/api/v1/status', methods=['GET'])
def get_complete_status():
    """Get complete system status including Rubix connection, recording state, and parameters"""
    try:
        import sounddevice as sd

        # Check Rubix connection
        recorder = AudioRecorder()
        rubix_input_id = recorder.find_device('rubix', 'input')
        rubix_output_id = recorder.find_device('rubix', 'output')

        rubix_status = {
            "connected": rubix_input_id is not None or rubix_output_id is not None,
            "input_device": None,
            "output_device": None
        }

        # Get detailed device information if Rubix is connected
        if rubix_input_id is not None:
            input_device = sd.query_devices(rubix_input_id)
            rubix_status["input_device"] = {
                "id": rubix_input_id,
                "name": input_device['name'],
                "channels": input_device['max_input_channels'],
                "sample_rate": input_device['default_samplerate']
            }

        if rubix_output_id is not None:
            output_device = sd.query_devices(rubix_output_id)
            rubix_status["output_device"] = {
                "id": rubix_output_id,
                "name": output_device['name'],
                "channels": output_device['max_output_channels'],
                "sample_rate": output_device['default_samplerate']
            }

        # Get current recording session status
        recording_status = None
        with recording_lock:
            if current_recording_session:
                recording_status = current_recording_session.to_dict()
            else:
                recording_status = {
                    "status": "idle",
                    "message": "No active recording session"
                }

        # Build complete status response
        status = {
            "timestamp": datetime.now().isoformat(),
            "service": "Rubix Recorder API",
            "version": "1.0.0",
            "rubix": rubix_status,
            "recording": recording_status,
            "config": {
                "default_duration": config["default_duration"],
                "sample_rate": config["sample_rate"],
                "output_prefix": config["output_prefix"],
                "playback_directory": config["playback_directory"],
                "recordings_directory": config["recordings_directory"]
            }
        }

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting complete status: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "service": "Rubix Recorder API"
        }), 500

@app.route('/api/v1/recordings/history', methods=['GET'])
def get_recording_history():
    """Get history of past recordings"""
    try:
        recordings = []
        recordings_dir = config["recordings_directory"]
        
        if os.path.exists(recordings_dir):
            # Look for stereo files as indicators of complete recordings
            for filename in sorted(os.listdir(recordings_dir), reverse=True):
                if filename.endswith('_stereo.wav'):
                    # Extract timestamp and prefix from filename
                    parts = filename.replace('_stereo.wav', '').split('_')
                    if len(parts) >= 3:
                        prefix = '_'.join(parts[:-2])
                        timestamp = parts[-2] + '_' + parts[-1]
                        
                        # Look for associated files
                        base_path = os.path.join(recordings_dir, f"{prefix}_{timestamp}")
                        files = []
                        for channel in ['_stereo.wav', '_ch1.wav', '_ch2.wav']:
                            file_path = base_path + channel
                            if os.path.exists(file_path):
                                stat = os.stat(file_path)
                                files.append({
                                    "name": os.path.basename(file_path),
                                    "path": file_path,
                                    "size": stat.st_size,
                                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                                })
                        
                        # Try to extract additional metadata from session info
                        # For now, we'll use default values and extract what we can
                        start_time_str = f"{timestamp.replace('_', 'T').replace('-', ':')}"
                        end_time_str = start_time_str  # We don't have actual end time
                        
                        # Try to get duration from file if possible
                        duration_seconds = 0
                        if files:
                            # Estimate duration from file size (rough approximation)
                            # For 16-bit stereo at 44.1kHz: ~176,400 bytes per second
                            stereo_file = next((f for f in files if 'stereo' in f['name']), None)
                            if stereo_file:
                                # Rough estimation: bytes / (2 channels * 2 bytes/sample * sample_rate)
                                estimated_duration = stereo_file['size'] / (2 * 2 * config["sample_rate"])
                                duration_seconds = max(0, estimated_duration)
                        
                        recordings.append({
                            "id": f"{prefix}_{timestamp}",
                            "prefix": prefix,
                            "timestamp": timestamp,
                            "start_time": start_time_str,
                            "end_time": end_time_str,
                            "duration_seconds": duration_seconds,
                            "playback_file": prefix,  # Use prefix as placeholder for playback file
                            "sample_rate": config["sample_rate"],
                            "files": files
                        })
        
        return jsonify(recordings)
    except Exception as e:
        logger.error(f"Error getting recording history: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/recordings/<path:filename>', methods=['GET'])
def download_recording(filename):
    """Download a recording file"""
    try:
        return send_from_directory(config["recordings_directory"], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({"error": "File not found"}), 404

@app.route('/api/v1/recordings/delete', methods=['POST'])
def delete_recording():
    """Delete a recording session (all associated files)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        session_id = data.get('session_id')
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        # Find files matching the session_id pattern
        recordings_dir = config["recordings_directory"]
        deleted_files = []
        not_found = []

        # Common patterns for session files
        patterns = [
            f"*{session_id}_stereo.wav",
            f"*{session_id}_ch1.wav",
            f"*{session_id}_ch2.wav"
        ]

        import glob
        for pattern in patterns:
            file_pattern = os.path.join(recordings_dir, pattern)
            matching_files = glob.glob(file_pattern)

            for file_path in matching_files:
                try:
                    os.remove(file_path)
                    deleted_files.append(os.path.basename(file_path))
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
                    not_found.append(os.path.basename(file_path))

        if not deleted_files and not not_found:
            return jsonify({"error": f"No files found for session_id: {session_id}"}), 404

        return jsonify({
            "success": True,
            "session_id": session_id,
            "deleted_files": deleted_files,
            "failed_files": not_found,
            "deleted_count": len(deleted_files)
        })

    except Exception as e:
        logger.error(f"Error deleting recording: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/recordings/transfer', methods=['POST'])
def transfer_recording():
    """Transfer a recording session to the configured storage server"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        session_id = data.get('session_id')
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        # Check if storage server is configured
        storage_config = config.get("storage_server", {})
        if not storage_config.get("enabled"):
            return jsonify({"error": "Storage server not configured or disabled"}), 400

        # Validate storage configuration
        required_fields = ["host", "username", "remote_path"]
        missing_fields = [field for field in required_fields if not storage_config.get(field)]
        if missing_fields:
            return jsonify({
                "error": f"Storage server configuration incomplete. Missing: {', '.join(missing_fields)}"
            }), 400

        # Find files matching the session_id
        recordings_dir = config["recordings_directory"]
        files_to_transfer = []

        import glob
        patterns = [
            f"*{session_id}_stereo.wav",
            f"*{session_id}_ch1.wav",
            f"*{session_id}_ch2.wav"
        ]

        for pattern in patterns:
            file_pattern = os.path.join(recordings_dir, pattern)
            matching_files = glob.glob(file_pattern)
            files_to_transfer.extend(matching_files)

        if not files_to_transfer:
            return jsonify({"error": f"No files found for session_id: {session_id}"}), 404

        # Transfer files based on protocol
        protocol = storage_config.get("protocol", "scp")
        transferred_files = []
        failed_files = []

        for file_path in files_to_transfer:
            filename = os.path.basename(file_path)
            try:
                if protocol in ["scp", "sftp"]:
                    # Use scp/sftp command
                    remote_file = f"{storage_config['remote_path']}/{filename}"
                    remote_host = f"{storage_config['username']}@{storage_config['host']}"

                    if protocol == "scp":
                        import subprocess
                        cmd = ["scp", "-P", str(storage_config.get('port', 22)), file_path, f"{remote_host}:{remote_file}"]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                        if result.returncode == 0:
                            transferred_files.append(filename)
                            logger.info(f"Transferred {filename} to {remote_host}:{remote_file}")
                        else:
                            failed_files.append({"file": filename, "error": result.stderr})
                            logger.error(f"Failed to transfer {filename}: {result.stderr}")

                    elif protocol == "sftp":
                        # SFTP implementation would go here
                        # For now, return not implemented
                        failed_files.append({"file": filename, "error": "SFTP not yet implemented"})

                elif protocol == "rsync":
                    # Rsync implementation
                    import subprocess
                    remote_host = f"{storage_config['username']}@{storage_config['host']}"
                    remote_path = f"{remote_host}:{storage_config['remote_path']}/"

                    cmd = ["rsync", "-avz", "-e", f"ssh -p {storage_config.get('port', 22)}", file_path, remote_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                    if result.returncode == 0:
                        transferred_files.append(filename)
                        logger.info(f"Transferred {filename} via rsync to {remote_path}")
                    else:
                        failed_files.append({"file": filename, "error": result.stderr})
                        logger.error(f"Failed to rsync {filename}: {result.stderr}")

                elif protocol == "http":
                    # HTTP POST upload
                    import requests
                    upload_url = f"http://{storage_config['host']}:{storage_config.get('port', 80)}{storage_config['remote_path']}"

                    with open(file_path, 'rb') as f:
                        files = {'file': (filename, f)}
                        response = requests.post(upload_url, files=files, timeout=300)

                        if response.status_code == 200:
                            transferred_files.append(filename)
                            logger.info(f"Uploaded {filename} to {upload_url}")
                        else:
                            failed_files.append({"file": filename, "error": f"HTTP {response.status_code}: {response.text}"})
                            logger.error(f"Failed to upload {filename}: HTTP {response.status_code}")
                else:
                    failed_files.append({"file": filename, "error": f"Unsupported protocol: {protocol}"})

            except Exception as e:
                failed_files.append({"file": filename, "error": str(e)})
                logger.error(f"Error transferring {filename}: {e}", exc_info=True)

        # Optionally delete local files after successful transfer
        delete_after_transfer = data.get('delete_after_transfer', False)
        deleted_files = []

        if delete_after_transfer and transferred_files:
            for file_path in files_to_transfer:
                filename = os.path.basename(file_path)
                if filename in transferred_files:
                    try:
                        os.remove(file_path)
                        deleted_files.append(filename)
                        logger.info(f"Deleted local file after transfer: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting {file_path} after transfer: {e}")

        return jsonify({
            "success": len(transferred_files) > 0,
            "session_id": session_id,
            "transferred_files": transferred_files,
            "failed_files": failed_files,
            "deleted_files": deleted_files,
            "transfer_count": len(transferred_files),
            "protocol": protocol,
            "destination": f"{storage_config['username']}@{storage_config['host']}:{storage_config['remote_path']}"
        })

    except Exception as e:
        logger.error(f"Error transferring recording: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/storage/config', methods=['GET'])
def get_storage_config():
    """Get storage server configuration (without sensitive data)"""
    storage_config = config.get("storage_server", {}).copy()
    # Don't expose password if it exists
    if "password" in storage_config:
        storage_config["password"] = "***"
    return jsonify(storage_config)

@app.route('/api/v1/storage/config', methods=['PUT'])
def update_storage_config():
    """Update storage server configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Update storage_server section in config
        if "storage_server" not in config:
            config["storage_server"] = {}

        config["storage_server"].update(data)

        # Save to file
        if save_config(config):
            # Return config without sensitive data
            safe_config = config["storage_server"].copy()
            if "password" in safe_config:
                safe_config["password"] = "***"

            return jsonify({
                "message": "Storage configuration updated",
                "storage_config": safe_config
            })
        else:
            return jsonify({"error": "Failed to save configuration"}), 500

    except Exception as e:
        logger.error(f"Error updating storage config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def main():
    """Main entry point"""
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs(config["playback_directory"], exist_ok=True)
    os.makedirs(config["recordings_directory"], exist_ok=True)
    
    logger.info("Starting Rubix Recorder API Server")
    logger.info(f"Listening on {config['host']}:{config['port']}")
    
    # Start Flask server
    app.run(
        host=config['host'],
        port=config['port'],
        debug=config['debug'],
        threaded=True
    )

if __name__ == '__main__':
    main()