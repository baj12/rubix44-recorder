#!/usr/bin/env python3
"""
Monitor a recording session in progress
Polls the status endpoint and displays progress
"""

import requests
import time
import sys
from datetime import datetime

BASE_URL = "http://10.0.0.58:5000/api/v1"

def monitor_recording(poll_interval=5):
    """Monitor current recording session"""
    print("Monitoring rubix44 server recording session...")
    print(f"Polling every {poll_interval} seconds")
    print("Press Ctrl+C to stop monitoring\n")

    last_progress = -1
    start_monitor_time = time.time()

    try:
        while True:
            try:
                # Get status
                response = requests.get(f"{BASE_URL}/status", timeout=10)

                if response.status_code != 200:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Status code {response.status_code}")
                    time.sleep(poll_interval)
                    continue

                data = response.json()
                recording = data.get("recording", {})
                status = recording.get("status", "unknown")

                if status == "recording":
                    human_id = recording.get("human_id", "N/A")
                    elapsed = recording.get("elapsed_seconds", 0)
                    duration = recording.get("duration", 0)
                    progress = recording.get("progress_percent", 0)
                    playback_file = recording.get("playback_file", "N/A")

                    # Only print when progress changes significantly
                    if abs(progress - last_progress) >= 1.0 or last_progress == -1:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Session: {human_id} | "
                              f"Playback: {playback_file} | "
                              f"Progress: {progress:.1f}% ({elapsed:.0f}/{duration}s)")
                        last_progress = progress

                    # Warn if approaching critical 150s mark
                    if 140 <= elapsed <= 160:
                        print(f"  ⚠ CRITICAL ZONE: {elapsed:.0f}s (watching for freeze at ~150s)")

                elif status == "idle":
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] No active recording")
                    print("Exiting monitor...")
                    break

                elif status in ["completed", "stopped"]:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Recording {status}!")
                    if recording.get("files"):
                        print(f"  Files: {len(recording['files'])} files saved")
                    print("Exiting monitor...")
                    break

                elif status == "error":
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Recording ERROR!")
                    print(f"  Error: {recording.get('error', 'Unknown error')}")
                    print("Exiting monitor...")
                    break

            except requests.exceptions.Timeout:
                monitor_elapsed = time.time() - start_monitor_time
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ REQUEST TIMEOUT after {monitor_elapsed:.0f}s monitoring "
                      f"(last progress: {last_progress:.1f}%)")
                print("  This likely indicates server freeze - server may have crashed")

            except requests.exceptions.ConnectionError:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ CONNECTION ERROR - server may be down")

            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")

def check_server_health():
    """Quick health check"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Server is healthy")
            return True
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot reach server: {e}")
        return False

if __name__ == "__main__":
    print("Rubix44 Recording Monitor")
    print("=" * 60)

    # Quick health check first
    if not check_server_health():
        print("\nServer appears to be down. Please check if api_server.py is running.")
        sys.exit(1)

    print()

    # Start monitoring
    poll_interval = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    monitor_recording(poll_interval)
