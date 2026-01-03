#!/usr/bin/env python3
"""
Test script to verify audio setup
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import sys

print("=" * 60)
print("Audio Recording Setup Test")
print("=" * 60)

# Check Python version
print(f"\nPython version: {sys.version}")

# Check package versions
print(f"\nsounddevice version: {sd.__version__}")
print(f"soundfile version: {sf.__version__}")
print(f"numpy version: {np.__version__}")

# List all audio devices
print("\n" + "=" * 60)
print("Available Audio Devices:")
print("=" * 60)
devices = sd.query_devices()
print(devices)

# Try to find Rubix44
print("\n" + "=" * 60)
print("Searching for Rubix44...")
print("=" * 60)
rubix_found = False
for i, device in enumerate(sd.query_devices()):
    if 'rubix' in device['name'].lower() or 'roland' in device['name'].lower():
        print(f"\n✓ Found: {device['name']}")
        print(f"  Device ID: {i}")
        print(f"  Input channels: {device['max_input_channels']}")
        print(f"  Output channels: {device['max_output_channels']}")
        print(f"  Default sample rate: {device['default_samplerate']}")
        rubix_found = True

if not rubix_found:
    print("\n✗ Rubix44 not found. Make sure it's connected and powered on.")
else:
    print("\n✓ Setup verified successfully!")

print("\n" + "=" * 60)

