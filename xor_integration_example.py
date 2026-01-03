#!/usr/bin/env python3
"""
Example script demonstrating integration with XOR continuous recording program
"""

import os
import sys
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xor_client import (create_recorder_client, start_xor_recording,
                        wait_for_recording_completion)


def main():
    """Demonstrate XOR integration"""
    print("Rubix Recorder API - XOR Integration Example")
    print("=" * 50)
    
    # Create client
    client = create_recorder_client("http://localhost:5000")
    
    # Check if server is running
    try:
        health = client.health_check()
        print(f"✓ Server is running: {health['status']}")
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("Please start the API server first:")
        print("  On Windows: double-click start_api_server.bat")
        print("  On Linux/Mac: run ./start_api_server.sh")
        return
    
    # List available playback files
    try:
        files = client.list_playback_files()
        print(f"\nAvailable playback files ({len(files)}):")
        for i, f in enumerate(files):
            print(f"  {i+1}. {f['name']}")
    except Exception as e:
        print(f"Error listing playback files: {e}")
        return
    
    if not files:
        print("No playback files found. Please add WAV files to the playback_files/ directory.")
        return
    
    # Select a playback file
    selected_file = files[0]['name']  # Use the first file
    print(f"\nSelected playback file: {selected_file}")
    
    # Start recording session
    print("\nStarting recording session...")
    session_id = start_xor_recording(client, selected_file, duration=60)  # 1 minute for demo
    
    if not session_id:
        print("Failed to start recording session")
        return
    
    print(f"✓ Recording session started: {session_id}")
    
    # Monitor the recording
    print("\nMonitoring recording progress...")
    print("(Press Ctrl+C to stop early)")
    
    try:
        # Wait for completion or user interruption
        completed = wait_for_recording_completion(client, session_id, timeout=120)
        
        if completed:
            print("✓ Recording completed successfully")
        else:
            print("Recording did not complete successfully")
            
        # Show final status
        status = client.get_recording_status()
        print(f"\nFinal status: {status.get('status', 'unknown')}")
        
        if status.get('files'):
            print("Generated files:")
            for f in status['files']:
                if os.path.exists(f):
                    size = os.path.getsize(f)
                    print(f"  - {os.path.basename(f)} ({size} bytes)")
                    
    except KeyboardInterrupt:
        print("\n\nStopping recording early...")
        try:
            result = client.stop_recording()
            print("✓ Recording stopped")
        except Exception as e:

if __name__ == "__main__":
    main()
