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

# API server configuration
BASE_URL = "http://localhost:5000"
API_PREFIX = "/api/v1"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/health")
        if response.status_code == 200:
            print("✓ Health check passed")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to API server. Is it running?")
        return False
    except Exception as e:
        print(f"✗ Health check failed with error: {e}")
        return False

def test_list_devices():
    """Test listing audio devices"""
    print("Testing device listing endpoint...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/devices")
        if response.status_code == 200:
            devices = response.json()
            print(f"✓ Found {len(devices)} audio devices")
            return True
        else:
            print(f"✗ Device listing failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Device listing failed with error: {e}")
        return False

def test_find_rubix():
    """Test finding Rubix device"""
    print("Testing Rubix device detection...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/devices/rubix")
        if response.status_code == 200:
            result = response.json()
            if result.get("found"):
                print("✓ Rubix device found")
                if "input_device_info" in result:
                    print(f"  Input device: {result['input_device_info']['name']}")
                if "output_device_info" in result:
                    print(f"  Output device: {result['output_device_info']['name']}")
            else:
                print("⚠ Rubix device not found (make sure it's connected)")
            return True
        else:
            print(f"✗ Rubix device detection failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Rubix device detection failed with error: {e}")
        return False

def test_list_playback_files():
    """Test listing playback files"""
    print("Testing playback files listing...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/playback-files")
        if response.status_code == 200:
            files = response.json()
            print(f"✓ Found {len(files)} playback files")
            for file in files[:3]:  # Show first 3 files
                print(f"  - {file['name']}")
            if len(files) > 3:
                print(f"  ... and {len(files) - 3} more")
            return True
        else:
            print(f"✗ Playback files listing failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Playback files listing failed with error: {e}")
        return False

def test_get_config():
    """Test getting configuration"""
    print("Testing configuration retrieval...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/config")
        if response.status_code == 200:
            config = response.json()
            print("✓ Configuration retrieved successfully")
            print(f"  Host: {config.get('host')}:{config.get('port')}")
            print(f"  Default duration: {config.get('default_duration')}s")
            return True
        else:
            print(f"✗ Configuration retrieval failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Configuration retrieval failed with error: {e}")
        return False

def test_get_recording_status():
    """Test getting recording status"""
    print("Testing recording status...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/recordings/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✓ Recording status: {status.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ Recording status check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Recording status check failed with error: {e}")
        return False

def test_get_recording_history():
    """Test getting recording history"""
    print("Testing recording history...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/recordings/history")
        if response.status_code == 200:
            history = response.json()
            print(f"✓ Found {len(history)} past recordings")
            return True
        else:
            print(f"✗ Recording history retrieval failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Recording history retrieval failed with error: {e}")
        return False

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