#!/usr/bin/env python3
"""
Client library for integrating with XOR continuous recording program
Provides simplified interface for controlling Rubix recorder via API
"""

import json
import time
from typing import Any, Dict, List, Optional

import requests


class RubixRecorderClient:
    """Client for interacting with Rubix Recorder API"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the client
        
        Args:
            base_url: Base URL of the Rubix Recorder API server
        """
        self.base_url = base_url.rstrip('/')
        self.api_prefix = "/api/v1"
        self.session = requests.Session()
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        return self.session.request(method, url, **kwargs)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the API server is healthy
        
        Returns:
            Health status dictionary
        """
        response = self._make_request("GET", "/health")
        response.raise_for_status()
        return response.json()
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration
        
        Returns:
            Configuration dictionary
        """
        response = self._make_request("GET", "/config")
        response.raise_for_status()
        return response.json()
    
    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update configuration
        
        Args:
            config: New configuration values
            
        Returns:
            Updated configuration
        """
        response = self._make_request("PUT", "/config", json=config)
        response.raise_for_status()
        return response.json()
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List all available audio devices
        
        Returns:
            List of device dictionaries
        """
        response = self._make_request("GET", "/devices")
        response.raise_for_status()
        return response.json()
    
    def find_rubix_device(self) -> Dict[str, Any]:
        """
        Find Rubix44 device
        
        Returns:
            Device information dictionary
        """
        response = self._make_request("GET", "/devices/rubix")
        response.raise_for_status()
        return response.json()
    
    def list_playback_files(self) -> List[Dict[str, Any]]:
        """
        List all available playback files
        
        Returns:
            List of playback file dictionaries
        """
        response = self._make_request("GET", "/playback-files")
        response.raise_for_status()
        return response.json()
    
    def start_recording(self, 
                       playback_file: str,
                       duration: Optional[int] = None,
                       sample_rate: Optional[int] = None,
                       output_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new recording session
        
        Args:
            playback_file: Path to playback file
            duration: Recording duration in seconds
            sample_rate: Sample rate in Hz
            output_prefix: Output filename prefix
            
        Returns:
            Session information dictionary
        """
        payload = {
            "playback_file": playback_file
        }
        
        if duration is not None:
            payload["duration"] = duration
        if sample_rate is not None:
            payload["sample_rate"] = sample_rate
        if output_prefix is not None:
            payload["output_prefix"] = output_prefix
            
        response = self._make_request("POST", "/recordings/start", json=payload)
        response.raise_for_status()
        return response.json()
    
    def stop_recording(self) -> Dict[str, Any]:
        """
        Stop current recording session
        
        Returns:
            Session information dictionary
        """
        response = self._make_request("POST", "/recordings/stop")
        response.raise_for_status()
        return response.json()
    
    def get_recording_status(self) -> Dict[str, Any]:
        """
        Get status of current recording session
        
        Returns:
            Status dictionary
        """
        response = self._make_request("GET", "/recordings/status")
        response.raise_for_status()
        return response.json()
    
    def get_recording_history(self) -> List[Dict[str, Any]]:
        """
        Get history of past recordings
        
        Returns:
            List of recording history dictionaries
        """
        response = self._make_request("GET", "/recordings/history")
        response.raise_for_status()
        return response.json()
    
    def download_recording(self, filename: str, save_path: str) -> bool:
        """
        Download a recording file
        
        Args:
            filename: Name of the file to download
            save_path: Local path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self._make_request("GET", f"/recordings/{filename}")
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False

# Convenience functions for XOR integration
def create_recorder_client(base_url: str = "http://localhost:5000") -> RubixRecorderClient:
    """
    Create a recorder client instance
    
    Args:
        base_url: Base URL of the API server
        
    Returns:
        RubixRecorderClient instance
    """
    return RubixRecorderClient(base_url)

def start_xor_recording(client: RubixRecorderClient, 
                       playback_file: str,
                       duration: int = 3600) -> Optional[str]:
    """
    Start a recording session for XOR integration
    
    Args:
        client: RubixRecorderClient instance
        playback_file: Path to playback file
        duration: Recording duration in seconds
        
    Returns:
        Session ID if successful, None otherwise
    """
    try:
        result = client.start_recording(
            playback_file=playback_file,
            duration=duration,
            output_prefix="xor_recording"
        )
        session = result.get("session", {})
        return session.get("id")
    except Exception as e:
        print(f"Error starting recording: {e}")
        return None

def wait_for_recording_completion(client: RubixRecorderClient, 
                                 session_id: str,
                                 timeout: int = 3600) -> bool:
    """
    Wait for a recording session to complete
    
    Args:
        client: RubixRecorderClient instance
        session_id: Session ID to monitor
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if completed successfully, False otherwise
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            status = client.get_recording_status()
            current_session = status.get("id")
            
            if current_session != session_id:
                print("Session ID mismatch")
                return False
                
            session_status = status.get("status")
            if session_status == "completed":
                return True
            elif session_status == "error":
                print(f"Recording error: {status.get('error')}")
                return False
            elif session_status == "idle":
                print("Recording session ended")
                return True
                
        except Exception as e:
            print(f"Error checking recording status: {e}")
            
        time.sleep(5)  # Check every 5 seconds
    
    print("Timeout waiting for recording completion")
    return False

def main():
    """Example usage"""
    # Create client
    client = create_recorder_client()
    
    # Check if server is running
    try:
        health = client.health_check()
        print(f"Server health: {health}")
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        return
    
    # List playback files
    try:
        files = client.list_playback_files()
        print(f"Available playback files: {len(files)}")
        for f in files:
            print(f"  - {f['name']}")
    except Exception as e:

if __name__ == "__main__":
    main()
