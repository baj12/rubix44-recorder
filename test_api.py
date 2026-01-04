#!/usr/bin/env python3
"""
Test script for Rubix Recorder API
Verifies that all API endpoints are functioning correctly
"""

import json
import os
import sys
import time

import requests
import pytest

# API server configuration
BASE_URL = "http://localhost:5000"
API_PREFIX = "/api/v1"


def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/health")
    except requests.exceptions.ConnectionError:
        pytest.skip("Could not connect to API server. Is it running?")
    except Exception as e:
        pytest.fail(f"Health check failed with error: {e}")

    assert response.status_code == 200, f"Health check returned {response.status_code}"
    print("✓ Health check passed")


def test_list_devices():
    """Test listing audio devices"""
    print("Testing device listing endpoint...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/devices")
    except Exception as e:
        pytest.fail(f"Device listing failed with error: {e}")

    assert response.status_code == 200, f"Device listing returned {response.status_code}"
    devices = response.json()
    assert isinstance(devices, list), "Devices response is not a list"
    print(f"✓ Found {len(devices)} audio devices")


def test_find_rubix():
    """Test finding Rubix device"""
    print("Testing Rubix device detection...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/devices/rubix")
    except Exception as e:
        pytest.fail(f"Rubix device detection failed with error: {e}")

    assert response.status_code == 200, f"Rubix detection returned {response.status_code}"
    result = response.json()
    if result.get("found"):
        print("✓ Rubix device found")
        if "input_device_info" in result:
            print(f"  Input device: {result['input_device_info']['name']}")
        if "output_device_info" in result:
            print(f"  Output device: {result['output_device_info']['name']}")
    else:
        print("⚠ Rubix device not found (make sure it's connected)")


def test_list_playback_files():
    """Test listing playback files"""
    print("Testing playback files listing...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/playback-files")
    except Exception as e:
        pytest.fail(f"Playback files listing failed with error: {e}")

    assert response.status_code == 200, f"Playback files returned {response.status_code}"
    files = response.json()
    assert isinstance(files, list), "Playback files response is not a list"
    print(f"✓ Found {len(files)} playback files")
    for file in files[:3]:
        print(f"  - {file.get('name')}")
    if len(files) > 3:
        print(f"  ... and {len(files) - 3} more")


def test_get_config():
    """Test getting configuration"""
    print("Testing configuration retrieval...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/config")
    except Exception as e:
        pytest.fail(f"Configuration retrieval failed with error: {e}")

    assert response.status_code == 200, f"Config retrieval returned {response.status_code}"
    config = response.json()
    assert isinstance(config, dict), "Config response is not a dict"
    print("✓ Configuration retrieved successfully")
    print(f"  Host: {config.get('host')}:{config.get('port')}")
    print(f"  Default duration: {config.get('default_duration')}s")


def test_get_recording_status():
    """Test getting recording status"""
    print("Testing recording status...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/recordings/status")
    except Exception as e:
        pytest.fail(f"Recording status check failed with error: {e}")

    assert response.status_code == 200, f"Recording status returned {response.status_code}"
    status = response.json()
    print(f"✓ Recording status: {status.get('status', 'unknown')}")


def test_get_recording_history():
    """Test getting recording history"""
    print("Testing recording history...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/recordings/history")
    except Exception as e:
        pytest.fail(f"Recording history retrieval failed with error: {e}")

    assert response.status_code == 200, f"Recording history returned {response.status_code}"
    history = response.json()
    assert isinstance(history, list), "Recording history is not a list"
    print(f"✓ Found {len(history)} past recordings")

def main():
    """Main test function"""
    print("=" * 60)
    print("Rubix Recorder API Test Suite")
    print("=" * 60)

    # Check if server is running
    try:
        test_health_check()
    except AssertionError:
        print("\nPlease start the API server before running tests:")
        print("  On Windows: run start_api_server.bat")
        print("  On Linux/Mac: run ./start_api_server.sh")
        return 1
    except Exception:
        print("\nPlease start the API server before running tests:")
        print("  On Windows: run start_api_server.bat")
        print("  On Linux/Mac: run ./start_api_server.sh")
        return 1

    print()

    # Run all tests
    tests = [
        test_get_config,
        test_list_devices,
        test_find_rubix,
        test_list_playback_files,
        test_get_recording_status,
        test_get_recording_history,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test {test.__name__} failed: {e}\n")
        except Exception as e:
            print(f"✗ Test {test.__name__} raised an exception: {e}\n")


    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

def test_get_config():
    """Test getting configuration"""
    print("Testing configuration retrieval...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/config")
    except Exception as e:
        pytest.fail(f"Configuration retrieval failed with error: {e}")

    assert response.status_code == 200, f"Config retrieval returned {response.status_code}"
    config = response.json()
    assert isinstance(config, dict), "Config response is not a dict"
    print("✓ Configuration retrieved successfully")
    print(f"  Host: {config.get('host')}:{config.get('port')}")
    print(f"  Default duration: {config.get('default_duration')}s")


def test_get_recording_status():
    """Test getting recording status"""
    print("Testing recording status...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/recordings/status")
    except Exception as e:
        pytest.fail(f"Recording status check failed with error: {e}")

    assert response.status_code == 200, f"Recording status returned {response.status_code}"
    status = response.json()
    print(f"✓ Recording status: {status.get('status', 'unknown')}")


def test_get_recording_history():
    """Test getting recording history"""
    print("Testing recording history...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/recordings/history")
    except Exception as e:
        pytest.fail(f"Recording history retrieval failed with error: {e}")

    assert response.status_code == 200, f"Recording history returned {response.status_code}"
    history = response.json()
    assert isinstance(history, list), "Recording history is not a list"
    print(f"✓ Found {len(history)} past recordings")

def main():
    """Main test function"""
    print("=" * 60)
    print("Rubix Recorder API Test Suite")
    print("=" * 60)
    
    # Check if server is running
    if not test_health_check():
        print("\nPlease start the API server before running tests:")
        print("  On Windows: run start_api_server.bat")
        print("  On Linux/Mac: run ./start_api_server.sh")
        return 1
    
    print()
    
    # Run all tests
    tests = [
        test_get_config,
        test_list_devices,
        test_find_rubix,
        test_list_playback_files,
        test_get_recording_status,
        test_get_recording_history
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}\n")
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())