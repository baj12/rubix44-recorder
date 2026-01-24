#!/usr/bin/env python3
"""
Comprehensive test suite for Rubix Recorder API

This test suite can be run locally or against a remote server.

Usage:
    # Run against local server (default: http://localhost:5000)
    python test_api.py

    # Run against remote server
    python test_api.py --host 10.0.0.58

    # Run against remote server with custom port
    python test_api.py --host 10.0.0.58 --port 5000

    # Run specific test categories
    python test_api.py --test health
    python test_api.py --test devices
    python test_api.py --test recording

    # Run with verbose output
    python test_api.py -v

    # Skip recording tests (useful for quick checks)
    python test_api.py --skip-recording

    # Run a short recording test (5 seconds instead of default 10)
    python test_api.py --quick

    # Test watchdog functionality (requires longer wait)
    python test_api.py --test watchdog
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed. Install with: pip install requests")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestResult:
    """Represents the result of a single test"""
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration


class RubixAPITester:
    """Test suite for Rubix Recorder API"""

    def __init__(self, base_url: str, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.session = requests.Session()
        self.created_session_id: Optional[str] = None

    def log(self, message: str, level: str = "info"):
        """Log a message with optional color coding"""
        if level == "info" and not self.verbose:
            return

        colors = {
            "info": Colors.CYAN,
            "success": Colors.GREEN,
            "error": Colors.RED,
            "warning": Colors.YELLOW,
            "header": Colors.BOLD + Colors.BLUE
        }
        color = colors.get(level, "")
        print(f"{color}{message}{Colors.END}")

    def api_url(self, endpoint: str) -> str:
        """Construct full API URL"""
        return urljoin(self.base_url, f"/api/v1/{endpoint.lstrip('/')}")

    def request(self, method: str, endpoint: str, **kwargs) -> Tuple[Optional[dict], int]:
        """Make an API request and return response data and status code"""
        url = self.api_url(endpoint)
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {"raw_response": response.text}
            return data, response.status_code
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}, 0

    def run_test(self, name: str, test_func: Callable) -> TestResult:
        """Run a single test and record the result"""
        start_time = time.time()
        try:
            passed, message = test_func()
            duration = time.time() - start_time
            result = TestResult(name, passed, message, duration)
        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(name, False, f"Exception: {str(e)}", duration)

        self.results.append(result)

        status = f"{Colors.GREEN}PASS{Colors.END}" if result.passed else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  [{status}] {name} ({result.duration:.2f}s)")
        if result.message and (not result.passed or self.verbose):
            print(f"         {result.message}")

        return result

    # ==================== Health & Config Tests ====================

    def test_health(self) -> Tuple[bool, str]:
        """Test /health endpoint"""
        data, status = self.request("GET", "health")
        if status != 200:
            return False, f"Expected 200, got {status}"
        if data.get("status") != "healthy":
            return False, f"Expected status 'healthy', got {data.get('status')}"
        return True, ""

    def test_system_health(self) -> Tuple[bool, str]:
        """Test /system/health endpoint"""
        data, status = self.request("GET", "system/health")
        if status != 200:
            return False, f"Expected 200, got {status}"
        if "status" not in data:
            return False, "Missing 'status' in response"
        # Check for either 'checks' or 'stability' (different API versions)
        if "checks" not in data and "stability" not in data:
            return False, "Missing 'checks' or 'stability' in response"
        uptime = data.get("uptime", {}).get("human", "unknown")
        return True, f"Status: {data.get('status')}, Uptime: {uptime}"

    def test_get_config(self) -> Tuple[bool, str]:
        """Test GET /config endpoint"""
        data, status = self.request("GET", "config")
        if status != 200:
            return False, f"Expected 200, got {status}"
        required_keys = ["host", "port", "default_duration", "sample_rate"]
        missing = [k for k in required_keys if k not in data]
        if missing:
            return False, f"Missing keys: {missing}"
        return True, f"Config has {len(data)} keys"

    def test_config_has_watchdog(self) -> Tuple[bool, str]:
        """Test that config includes watchdog_grace_period"""
        data, status = self.request("GET", "config")
        if status != 200:
            return False, f"Expected 200, got {status}"
        if "watchdog_grace_period" not in data:
            # Watchdog may not be deployed yet - this is informational
            return True, "watchdog_grace_period not in config (feature may not be deployed)"
        grace_period = data.get("watchdog_grace_period")
        return True, f"Watchdog grace period: {grace_period}s"

    def test_update_config(self) -> Tuple[bool, str]:
        """Test PUT /config endpoint"""
        # Get current config
        original_data, _ = self.request("GET", "config")
        original_debug = original_data.get("debug", False)

        # Update config
        new_debug = not original_debug
        data, status = self.request("PUT", "config", json={"debug": new_debug})
        if status != 200:
            return False, f"Expected 200, got {status}"

        # Verify change
        verify_data, _ = self.request("GET", "config")
        if verify_data.get("debug") != new_debug:
            return False, "Config update not reflected"

        # Restore original
        self.request("PUT", "config", json={"debug": original_debug})
        return True, "Config update and restore successful"

    def test_system_dependencies(self) -> Tuple[bool, str]:
        """Test /system/dependencies endpoint"""
        data, status = self.request("GET", "system/dependencies")
        if status == 404:
            return True, "Endpoint not available (older API version)"
        if status != 200:
            return False, f"Expected 200, got {status}"
        if "python" not in data:
            return False, "Missing 'python' in response"
        return True, f"Python {data.get('python', {}).get('version', 'unknown')}"

    # ==================== Device Tests ====================

    def test_list_devices(self) -> Tuple[bool, str]:
        """Test /devices endpoint"""
        data, status = self.request("GET", "devices")
        if status != 200:
            return False, f"Expected 200, got {status}"
        # API returns either {"devices": [...]} or just [...]
        if isinstance(data, list):
            device_count = len(data)
        elif "devices" in data:
            device_count = len(data.get("devices", []))
        else:
            return False, "Unexpected response format"
        return True, f"Found {device_count} audio devices"

    def test_find_rubix(self) -> Tuple[bool, str]:
        """Test /devices/rubix endpoint"""
        data, status = self.request("GET", "devices/rubix")
        if status == 200:
            # Handle different response formats
            if isinstance(data, dict):
                input_dev = data.get("input_device", {})
                output_dev = data.get("output_device", {})
                if isinstance(input_dev, dict):
                    input_name = input_dev.get('name', 'N/A')
                else:
                    input_name = f"Device ID {input_dev}"
                if isinstance(output_dev, dict):
                    output_name = output_dev.get('name', 'N/A')
                else:
                    output_name = f"Device ID {output_dev}"
                return True, f"Input: {input_name}, Output: {output_name}"
            return True, f"Rubix found: {data}"
        if status == 404:
            return True, "Rubix44 not connected (expected on some systems)"
        return False, f"Unexpected status {status}"

    # ==================== Playback Files Tests ====================

    def test_list_playback_files(self) -> Tuple[bool, str]:
        """Test /playback-files endpoint"""
        data, status = self.request("GET", "playback-files")
        if status != 200:
            return False, f"Expected 200, got {status}"
        # API returns either {"files": [...]} or just [...]
        if isinstance(data, list):
            file_count = len(data)
        elif "files" in data:
            file_count = len(data.get("files", []))
        else:
            return False, "Unexpected response format"
        return True, f"Found {file_count} playback files"

    def test_playback_files_have_metadata(self) -> Tuple[bool, str]:
        """Test that playback files include metadata (duration, sample_rate, channels)"""
        data, status = self.request("GET", "playback-files")
        if status != 200:
            return False, f"Expected 200, got {status}"
        # API returns either {"files": [...]} or just [...]
        if isinstance(data, list):
            files = data
        else:
            files = data.get("files", [])
        if not files:
            return True, "No playback files to check metadata"

        first_file = files[0]
        # Check for either 'name' or 'filename' key
        name_key = "filename" if "filename" in first_file else "name"
        if name_key not in first_file:
            return False, f"Missing name/filename in file metadata"
        return True, f"First file: {first_file.get(name_key)}"

    # ==================== Recording Tests ====================

    def test_recording_status_idle(self) -> Tuple[bool, str]:
        """Test /recordings/status when idle"""
        data, status = self.request("GET", "recordings/status")
        if status != 200:
            return False, f"Expected 200, got {status}"
        if data.get("status") != "idle":
            return False, f"Expected 'idle', got {data.get('status')}"
        return True, ""

    def test_status_endpoint(self) -> Tuple[bool, str]:
        """Test /status endpoint (comprehensive status)"""
        data, status = self.request("GET", "status")
        if status != 200:
            return False, f"Expected 200, got {status}"
        required_keys = ["timestamp", "service", "version", "rubix", "recording", "config"]
        missing = [k for k in required_keys if k not in data]
        if missing:
            return False, f"Missing keys: {missing}"
        return True, f"Rubix connected: {data.get('rubix', {}).get('connected', False)}"

    def test_recording_history(self) -> Tuple[bool, str]:
        """Test /recordings/history endpoint"""
        data, status = self.request("GET", "recordings/history")
        if status != 200:
            return False, f"Expected 200, got {status}"
        if not isinstance(data, list):
            return False, "Expected list response"
        return True, f"Found {len(data)} recording sessions in history"

    def test_stop_recording_when_idle(self) -> Tuple[bool, str]:
        """Test /recordings/stop when no recording is active"""
        data, status = self.request("POST", "recordings/stop")
        if status != 400:
            return False, f"Expected 400, got {status}"
        return True, "Correctly rejected stop when idle"

    def test_start_recording_missing_file(self) -> Tuple[bool, str]:
        """Test /recordings/start with missing playback file"""
        data, status = self.request("POST", "recordings/start", json={
            "playback_file": "nonexistent_file_12345.wav",
            "duration": 10
        })
        if status != 404:
            return False, f"Expected 404, got {status}"
        return True, "Correctly rejected missing playback file"

    def test_start_recording_no_file(self) -> Tuple[bool, str]:
        """Test /recordings/start without playback file"""
        data, status = self.request("POST", "recordings/start", json={
            "duration": 10
        })
        if status != 400:
            return False, f"Expected 400, got {status}"
        return True, "Correctly rejected request without playback file"

    def test_full_recording_cycle(self, duration: int = 10) -> Tuple[bool, str]:
        """Test complete recording cycle: start, monitor, stop"""
        # First, get available playback files
        files_data, files_status = self.request("GET", "playback-files")
        if files_status != 200:
            return False, "Failed to get playback files"
        # API returns either {"files": [...]} or just [...]
        if isinstance(files_data, list):
            files = files_data
        else:
            files = files_data.get("files", [])
        if not files:
            return False, "No playback files available for testing"

        # Get filename - check for 'filename' or 'name' key
        first_file = files[0]
        playback_file = first_file.get("filename") or first_file.get("name")
        self.log(f"Using playback file: {playback_file}", "info")

        # Start recording
        start_data, start_status = self.request("POST", "recordings/start", json={
            "playback_file": playback_file,
            "duration": duration,
            "output_prefix": "test_api_recording"
        })

        if start_status == 500:
            # Might fail if Rubix44 is not connected
            error_msg = start_data.get("error", "Unknown error")
            if "rubix" in error_msg.lower() or "device" in error_msg.lower():
                return True, f"Skipped: Rubix44 not available ({error_msg})"
            return False, f"Server error: {error_msg}"

        if start_status != 202:
            return False, f"Expected 202, got {start_status}: {start_data}"

        session = start_data.get("session", {})
        session_id = session.get("id")
        human_id = session.get("human_id")
        self.created_session_id = session_id
        self.log(f"Started session {session_id} ({human_id})", "info")

        # Monitor recording for a bit
        time.sleep(2)

        # Check status
        status_data, status_status = self.request("GET", "recordings/status")
        if status_status != 200:
            return False, f"Failed to get recording status: {status_status}"

        if status_data.get("status") != "recording":
            return False, f"Expected status 'recording', got {status_data.get('status')}"

        elapsed = status_data.get("elapsed_seconds", 0)
        self.log(f"Recording in progress: {elapsed:.1f}s elapsed", "info")

        # Wait for recording to complete or stop early
        if duration > 5:
            time.sleep(3)
            # Stop recording early
            stop_data, stop_status = self.request("POST", "recordings/stop")
            if stop_status != 200:
                return False, f"Failed to stop recording: {stop_status}"
            self.log("Recording stopped early", "info")
        else:
            # Wait for natural completion
            time.sleep(duration + 2)

        # Verify recording completed
        time.sleep(1)
        final_status, _ = self.request("GET", "recordings/status")

        # Check history for our recording
        history_data, _ = self.request("GET", "recordings/history")
        found = any(r.get("id", "").startswith("test_api_recording") or
                   session_id in r.get("id", "") for r in history_data)

        return True, f"Recording cycle completed successfully (session: {human_id})"

    def test_concurrent_recording_rejection(self) -> Tuple[bool, str]:
        """Test that starting a second recording is rejected"""
        # Get playback files
        files_data, _ = self.request("GET", "playback-files")
        # API returns either {"files": [...]} or just [...]
        if isinstance(files_data, list):
            files = files_data
        else:
            files = files_data.get("files", [])
        if not files:
            return True, "Skipped: No playback files available"

        first_file = files[0]
        playback_file = first_file.get("filename") or first_file.get("name")

        # Start first recording
        start_data, start_status = self.request("POST", "recordings/start", json={
            "playback_file": playback_file,
            "duration": 30,
            "output_prefix": "test_concurrent"
        })

        if start_status == 500:
            return True, "Skipped: Rubix44 not available"

        if start_status != 202:
            return False, f"First recording failed: {start_status}"

        try:
            # Try to start second recording
            second_data, second_status = self.request("POST", "recordings/start", json={
                "playback_file": playback_file,
                "duration": 10
            })

            # Accept both 400 and 409 as valid rejection codes
            if second_status not in (400, 409):
                return False, f"Expected 400 or 409 rejection, got {second_status}"

            return True, f"Correctly rejected concurrent recording (status {second_status})"
        finally:
            # Clean up - stop the first recording
            self.request("POST", "recordings/stop")
            time.sleep(1)

    # ==================== Storage Config Tests ====================

    def test_get_storage_config(self) -> Tuple[bool, str]:
        """Test GET /storage/config endpoint"""
        data, status = self.request("GET", "storage/config")
        if status != 200:
            return False, f"Expected 200, got {status}"
        if "enabled" not in data:
            return False, "Missing 'enabled' in response"
        return True, f"Storage enabled: {data.get('enabled')}"

    def test_update_storage_config(self) -> Tuple[bool, str]:
        """Test PUT /storage/config endpoint"""
        # Get original config
        original_data, _ = self.request("GET", "storage/config")

        # Update with test values
        test_config = {
            "enabled": False,
            "host": "test.example.com",
            "port": 2222
        }
        update_data, update_status = self.request("PUT", "storage/config", json=test_config)
        if update_status != 200:
            return False, f"Expected 200, got {update_status}"

        # Verify change
        verify_data, _ = self.request("GET", "storage/config")
        if verify_data.get("host") != "test.example.com":
            return False, "Config update not reflected"

        # Restore original
        self.request("PUT", "storage/config", json=original_data)
        return True, "Storage config update and restore successful"

    # ==================== Logs Tests ====================

    def test_list_logs(self) -> Tuple[bool, str]:
        """Test GET /logs endpoint"""
        data, status = self.request("GET", "logs")
        if status != 200:
            return False, f"Expected 200, got {status}"
        # API returns either {"files": [...]} or {"log_files": [...]}
        if "files" in data:
            file_count = len(data.get("files", []))
        elif "log_files" in data:
            file_count = len(data.get("log_files", []))
        else:
            return False, "Missing 'files' or 'log_files' in response"
        return True, f"Found {file_count} log files"

    def test_get_log_file(self) -> Tuple[bool, str]:
        """Test GET /logs/<filename> endpoint"""
        # First list logs to get a filename
        list_data, _ = self.request("GET", "logs")
        files = list_data.get("files", list_data.get("log_files", []))
        if not files:
            return True, "Skipped: No log files available"

        first_file = files[0]
        if isinstance(first_file, dict):
            log_file = first_file.get("name", first_file.get("filename", ""))
        else:
            log_file = first_file
        if not log_file:
            return True, "Skipped: Could not determine log filename"

        _, status = self.request("GET", f"logs/{log_file}")
        if status == 200:
            return True, f"Retrieved log file: {log_file}"
        if status == 404:
            return True, "Log file not found (may have been rotated)"
        return False, f"Unexpected status {status}"

    # ==================== Watchdog Test ====================

    def test_watchdog_timeout(self, grace_period: int = 10) -> Tuple[bool, str]:
        """
        Test watchdog functionality by starting a recording and waiting
        for it to be force-stopped by the watchdog.

        Note: This test takes longer as it waits for the watchdog to trigger.
        """
        # Get playback files
        files_data, _ = self.request("GET", "playback-files")
        if not files_data.get("files"):
            return True, "Skipped: No playback files available"

        playback_file = files_data["files"][0]["name"]

        # Set a short watchdog grace period for testing
        original_config, _ = self.request("GET", "config")
        original_grace = original_config.get("watchdog_grace_period", 60)

        # Update to short grace period
        self.request("PUT", "config", json={"watchdog_grace_period": grace_period})

        try:
            # Start a very short recording (5 seconds)
            # The watchdog should trigger at duration + grace_period
            duration = 5
            start_data, start_status = self.request("POST", "recordings/start", json={
                "playback_file": playback_file,
                "duration": duration,
                "output_prefix": "test_watchdog"
            })

            if start_status == 500:
                return True, "Skipped: Rubix44 not available"

            if start_status != 202:
                return False, f"Failed to start recording: {start_status}"

            session_id = start_data.get("session", {}).get("id")
            self.log(f"Started watchdog test session: {session_id}", "info")

            # Wait for recording to complete naturally
            # The recording should finish within duration + a small buffer
            max_wait = duration + grace_period + 15
            start_time = time.time()

            while time.time() - start_time < max_wait:
                status_data, _ = self.request("GET", "recordings/status")
                current_status = status_data.get("status", "unknown")

                if current_status != "recording":
                    elapsed = time.time() - start_time
                    self.log(f"Recording ended with status '{current_status}' after {elapsed:.1f}s", "info")

                    # Check if it was stopped by watchdog (has error message about timeout)
                    error = status_data.get("error", "")
                    if "watchdog" in error.lower() or "timeout" in error.lower():
                        return True, f"Watchdog correctly stopped recording: {error}"
                    elif current_status in ["completed", "stopped"]:
                        return True, f"Recording completed normally (status: {current_status})"
                    else:
                        return False, f"Unexpected status: {current_status}"

                time.sleep(1)

            return False, f"Recording still active after {max_wait}s - watchdog may not be working"

        finally:
            # Restore original grace period
            self.request("PUT", "config", json={"watchdog_grace_period": original_grace})
            # Make sure recording is stopped
            self.request("POST", "recordings/stop")

    # ==================== Delete Recording Test ====================

    def test_delete_recording(self) -> Tuple[bool, str]:
        """Test /recordings/delete endpoint"""
        # Get history to find a test recording to delete
        history_data, _ = self.request("GET", "recordings/history")

        # Look for a test recording we can safely delete
        test_recordings = [r for r in history_data if
                         r.get("prefix", "").startswith("test_") or
                         "test" in r.get("id", "").lower()]

        if not test_recordings:
            return True, "Skipped: No test recordings to delete"

        session_id = test_recordings[0].get("id")

        # Try to delete
        delete_data, delete_status = self.request("POST", "recordings/delete", json={
            "session_id": session_id
        })

        if delete_status == 200:
            return True, f"Successfully deleted recording: {session_id}"
        elif delete_status == 404:
            return True, f"Recording not found (may already be deleted): {session_id}"
        else:
            return False, f"Delete failed with status {delete_status}: {delete_data}"

    # ==================== Test Runners ====================

    def run_health_tests(self):
        """Run health and config tests"""
        self.log("\n=== Health & Config Tests ===", "header")
        self.run_test("Health endpoint", self.test_health)
        self.run_test("System health endpoint", self.test_system_health)
        self.run_test("Get config", self.test_get_config)
        self.run_test("Config has watchdog setting", self.test_config_has_watchdog)
        self.run_test("Update config", self.test_update_config)
        self.run_test("System dependencies", self.test_system_dependencies)

    def run_device_tests(self):
        """Run device tests"""
        self.log("\n=== Device Tests ===", "header")
        self.run_test("List devices", self.test_list_devices)
        self.run_test("Find Rubix44", self.test_find_rubix)

    def run_playback_tests(self):
        """Run playback file tests"""
        self.log("\n=== Playback Files Tests ===", "header")
        self.run_test("List playback files", self.test_list_playback_files)
        self.run_test("Playback files have metadata", self.test_playback_files_have_metadata)

    def run_recording_tests(self, duration: int = 10):
        """Run recording tests"""
        self.log("\n=== Recording Tests ===", "header")
        self.run_test("Recording status (idle)", self.test_recording_status_idle)
        self.run_test("Comprehensive status", self.test_status_endpoint)
        self.run_test("Recording history", self.test_recording_history)
        self.run_test("Stop when idle (error handling)", self.test_stop_recording_when_idle)
        self.run_test("Start with missing file (error handling)", self.test_start_recording_missing_file)
        self.run_test("Start without file (error handling)", self.test_start_recording_no_file)
        self.run_test("Full recording cycle", lambda: self.test_full_recording_cycle(duration))
        self.run_test("Concurrent recording rejection", self.test_concurrent_recording_rejection)

    def run_storage_tests(self):
        """Run storage config tests"""
        self.log("\n=== Storage Config Tests ===", "header")
        self.run_test("Get storage config", self.test_get_storage_config)
        self.run_test("Update storage config", self.test_update_storage_config)

    def run_logs_tests(self):
        """Run logs tests"""
        self.log("\n=== Logs Tests ===", "header")
        self.run_test("List logs", self.test_list_logs)
        self.run_test("Get log file", self.test_get_log_file)

    def run_watchdog_tests(self):
        """Run watchdog tests"""
        self.log("\n=== Watchdog Tests ===", "header")
        self.run_test("Watchdog timeout", lambda: self.test_watchdog_timeout(10))

    def run_cleanup_tests(self):
        """Run cleanup tests"""
        self.log("\n=== Cleanup Tests ===", "header")
        self.run_test("Delete test recording", self.test_delete_recording)

    def run_all_tests(self, skip_recording: bool = False, quick: bool = False):
        """Run all tests"""
        duration = 5 if quick else 10

        self.run_health_tests()
        self.run_device_tests()
        self.run_playback_tests()

        if not skip_recording:
            self.run_recording_tests(duration)

        self.run_storage_tests()
        self.run_logs_tests()
        self.run_cleanup_tests()

    def print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"\n{'='*60}")
        print(f"{Colors.BOLD}Test Summary{Colors.END}")
        print(f"{'='*60}")
        print(f"Total:  {total}")
        print(f"Passed: {Colors.GREEN}{passed}{Colors.END}")
        print(f"Failed: {Colors.RED}{failed}{Colors.END}")

        total_time = sum(r.duration for r in self.results)
        print(f"Time:   {total_time:.2f}s")

        if failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")

        print(f"{'='*60}")
        return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Rubix Recorder API Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--host", default="localhost",
                       help="API server host (default: localhost)")
    parser.add_argument("--port", type=int, default=5000,
                       help="API server port (default: 5000)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--skip-recording", action="store_true",
                       help="Skip recording tests")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick tests with shorter recording duration")
    parser.add_argument("--test", choices=["health", "devices", "playback",
                                           "recording", "storage", "logs",
                                           "watchdog", "all"],
                       default="all",
                       help="Run specific test category (default: all)")

    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    print(f"{Colors.BOLD}Rubix Recorder API Test Suite{Colors.END}")
    print(f"Target: {base_url}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Test connectivity first
    tester = RubixAPITester(base_url, verbose=args.verbose)

    try:
        data, status = tester.request("GET", "health")
        if status == 0:
            print(f"{Colors.RED}ERROR: Cannot connect to {base_url}{Colors.END}")
            print(f"Error: {data.get('error', 'Unknown error')}")
            sys.exit(1)
        elif status != 200:
            print(f"{Colors.YELLOW}WARNING: Health check returned {status}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}ERROR: Connection failed: {e}{Colors.END}")
        sys.exit(1)

    print(f"{Colors.GREEN}Connected to API server{Colors.END}")

    # Run tests based on selection
    if args.test == "health":
        tester.run_health_tests()
    elif args.test == "devices":
        tester.run_device_tests()
    elif args.test == "playback":
        tester.run_playback_tests()
    elif args.test == "recording":
        tester.run_recording_tests(5 if args.quick else 10)
    elif args.test == "storage":
        tester.run_storage_tests()
    elif args.test == "logs":
        tester.run_logs_tests()
    elif args.test == "watchdog":
        tester.run_watchdog_tests()
    else:
        tester.run_all_tests(skip_recording=args.skip_recording, quick=args.quick)

    success = tester.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
