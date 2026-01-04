#!/usr/bin/env python3
"""
RESTful API Server for Rubix44 Audio Recorder
Provides HTTP endpoints to control recording sessions remotely.
"""

import json
import logging
import os
import sys
import threading
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
    "recordings_directory": "recordings"
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

# Ensure directories exist
os.makedirs(config["playback_directory"], exist_ok=True)
os.makedirs(config["recordings_directory"], exist_ok=True)

class RecordingSession:
    """Represents a recording session"""
    def __init__(self, playback_file, duration=None, sample_rate=None, output_prefix=None):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.playback_file = playback_file
        self.start_time = None
        self.end_time = None
        self.duration = duration or config["default_duration"]
        self.sample_rate = sample_rate or config["sample_rate"]
        self.output_prefix = output_prefix or config["output_prefix"]
        self.status = "initialized"  # initialized, recording, completed, error
        self.files = []
        self.error = None
        
    def to_dict(self):
        return {
            "id": self.id,
            "playback_file": self.playback_file,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "output_prefix": self.output_prefix,
            "status": self.status,
            "files": self.files,
            "error": self.error
        }

def start_recording_in_thread(session):
    """Start recording in a separate thread"""
    global current_recording_session
    
    with recording_lock:
        current_recording_session = session
        session.status = "recording"
        session.start_time = datetime.now()
        
    try:
        # Create recorder instance
        recorder = AudioRecorder(
            duration=session.duration,
            sample_rate=session.sample_rate
        )
        
        # Start recording with playback
        success = recorder.record_with_playback(
            session.playback_file,
            session.output_prefix
        )
        
        with recording_lock:
            if success:
                session.status = "completed"
                session.end_time = datetime.now()
                
                # Collect generated files
                timestamp = session.start_time.strftime("%Y-%m-%d_%H-%M-%S")
                base_path = f"{config['recordings_directory']}/{session.output_prefix}_{timestamp}"
                
                session.files = [
                    f"{base_path}_stereo.wav",
                    f"{base_path}_ch1.wav",
                    f"{base_path}_ch2.wav"
                ]
                
                # Verify files exist
                session.files = [f for f in session.files if os.path.exists(f)]
            else:
                session.status = "error"
                session.error = "Recording failed"
                
    except Exception as e:
        logger.error(f"Error during recording: {e}")
        with recording_lock:
            session.status = "error"
            session.error = str(e)
            session.end_time = datetime.now()
    finally:
        with recording_lock:
            current_recording_session = None

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
    """List all available playback files"""
    try:
        files = []
        playback_dir = config["playback_directory"]
        
        if os.path.exists(playback_dir):
            for filename in os.listdir(playback_dir):
                if filename.lower().endswith('.wav'):
                    filepath = os.path.join(playback_dir, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "name": filename,
                        "path": filepath,
                        "size": stat.st_size,
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
    
    # Check if already recording
    with recording_lock:
        if current_recording_session and current_recording_session.status == "recording":
            return jsonify({"error": "Recording already in progress"}), 400
    
    # Get parameters from request
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    playback_file = data.get('playback_file')
    if not playback_file:
        return jsonify({"error": "playback_file is required"}), 400
    
    # Verify playback file exists
    if not os.path.exists(playback_file):
        # Check in playback directory
        playback_path = os.path.join(config["playback_directory"], playback_file)
        if os.path.exists(playback_path):
            playback_file = playback_path
        else:
            return jsonify({"error": f"Playback file not found: {playback_file}"}), 404
    
    # Create recording session
    session = RecordingSession(
        playback_file=playback_file,
        duration=data.get('duration'),
        sample_rate=data.get('sample_rate'),
        output_prefix=data.get('output_prefix')
    )
    
    # Start recording in background thread
    recording_thread = threading.Thread(
        target=start_recording_in_thread,
        args=(session,),
        daemon=True
    )
    recording_thread.start()
    
    logger.info(f"Started recording session {session.id}")
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
        
        # For now, we'll just mark it as stopped
        # In a real implementation, we'd need to interrupt the recording
        current_recording_session.status = "stopped"
        current_recording_session.end_time = datetime.now()
        
        logger.info(f"Stopped recording session {current_recording_session.id}")
        return jsonify({
            "message": "Recording stopped",
            "session": current_recording_session.to_dict()
        })

@app.route('/api/v1/recordings/status', methods=['GET'])
def get_recording_status():
    """Get status of current recording session"""
    with recording_lock:
        if current_recording_session:
            return jsonify(current_recording_session.to_dict())
        else:
            return jsonify({"status": "idle", "message": "No active recording session"})

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
                        
                        recordings.append({
                            "id": f"{prefix}_{timestamp}",
                            "prefix": prefix,
                            "timestamp": timestamp,
                            "files": files
                        })
        
        return jsonify(recordings)
    except Exception as e:
        logger.error(f"Error getting recording history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/recordings/<path:filename>', methods=['GET'])
def download_recording(filename):
    """Download a recording file"""
    try:
        return send_from_directory(config["recordings_directory"], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({"error": "File not found"}), 404

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