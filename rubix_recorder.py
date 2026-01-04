#!/usr/bin/env python3
"""
Automated audio recorder for Rubix44
Records two channels while playing back a WAV file through Rubix44
"""

import argparse
import sys
import threading
import time
from datetime import datetime

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    def __init__(self, input_device=None, output_device=None, duration=3600, sample_rate=44100):
        """
        Initialize the audio recorder
        
        Args:
            input_device: Name or ID of the input device (None for auto-detect)
            output_device: Name or ID of the output device (None for auto-detect)
            duration: Recording duration in seconds (default: 3600 = 1 hour)
            sample_rate: Sample rate in Hz (default: 44100)
        """
        self.input_device = input_device
        self.output_device = output_device
        self.duration = duration
        self.sample_rate = sample_rate
        self.recording = None
        self.should_stop = False
        
    def find_device(self, search_term='rubix', device_type='input'):
        """
        Find device by name
        
        Args:
            search_term: String to search for in device name
            device_type: 'input', 'output', or 'both'
        """
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if search_term.lower() in device['name'].lower():
                # Check if device supports the required type
                if device_type == 'input' and device['max_input_channels'] > 0:
                    return i
                elif device_type == 'output' and device['max_output_channels'] > 0:
                    return i
                elif device_type == 'both':
                    if device['max_input_channels'] > 0 and device['max_output_channels'] > 0:
                        return i
        return None
    
    def stop_recording(self):
        """
        Signal that recording should be stopped
        """
        self.should_stop = True
    
    def record_with_playback(self, playback_file, output_prefix='recording'):
        """
        Record audio while playing back a file through Rubix44
        
        Args:
            playback_file: Path to WAV file to play during recording
            output_prefix: Prefix for output filenames
        """
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Load playback file
        try:
            playback_data, playback_sr = sf.read(playback_file)
            print(f"Loaded playback file: {playback_file}")
            print(f"Playback sample rate: {playback_sr} Hz")
            print(f"Playback channels: {playback_data.shape[1] if len(playback_data.shape) > 1 else 1}")
        except Exception as e:
            print(f"Error loading playback file: {e}")
            return False
        
        # Setup input device
        if self.input_device is None:
            input_id = self.find_device('rubix', 'input')
            if input_id is None:
                raise RuntimeError(
                    "Could not find Rubix44 input device!\n"
                    "Please ensure:\n"
                    "  1. Rubix44 is connected via USB\n"
                    "  2. Rubix44 is powered on\n"
                    "  3. Rubix44 drivers are installed (if needed)\n"
                    "Run with --list-devices to see available devices"
                )
        else:
            input_id = self.input_device
        
        # Setup output device
        if self.output_device is None:
            output_id = self.find_device('rubix', 'output')
            if output_id is None:
                raise RuntimeError(
                    "Could not find Rubix44 output device!\n"
                    "Please ensure:\n"
                    "  1. Rubix44 is connected via USB\n"
                    "  2. Rubix44 is powered on\n"
                    "  3. Rubix44 drivers are installed (if needed)\n"
                    "Run with --list-devices to see available devices"
                )
        else:
            output_id = self.output_device
        
        # Get device info
        input_device_info = sd.query_devices(input_id) if input_id else sd.query_devices(kind='input')
        output_device_info = sd.query_devices(output_id) if output_id else sd.query_devices(kind='output')
        
        print(f"\nRecording Configuration:")
        print(f"  Input Device: {input_device_info['name']}")
        print(f"  Output Device: {output_device_info['name']}")
        print(f"  Duration: {self.duration} seconds ({self.duration/60:.1f} minutes)")
        print(f"  Sample rate: {self.sample_rate} Hz")
        print(f"  Recording channels: 2")
        print(f"  Output prefix: {output_prefix}")
        print(f"  Timestamp: {timestamp}")
        
        # Ensure playback data is the right shape
        if len(playback_data.shape) == 1:
            # Mono file - convert to stereo
            playback_data = np.column_stack([playback_data, playback_data])
            print("  Note: Converted mono playback to stereo")
        
        # Resample playback if necessary
        if playback_sr != self.sample_rate:
            print(f"  Warning: Playback sample rate ({playback_sr}) doesn't match recording ({self.sample_rate})")
            print(f"           Consider converting your file to {self.sample_rate} Hz")
        
        # Start playback in a separate thread
        def play_audio():
            try:
                # Loop the playback if it's shorter than recording duration
                loops_needed = int(np.ceil(self.duration * playback_sr / len(playback_data)))
                if loops_needed > 1:
                    looped_data = np.tile(playback_data, (loops_needed, 1))
                    playback_length = int(self.duration * playback_sr)
                    sd.play(
                        looped_data[:playback_length], 
                        playback_sr,
                        device=output_id
                    )
                else:
                    sd.play(playback_data, playback_sr, device=output_id)
                print("  Playback started on Rubix44 outputs")
            except Exception as e:
                print(f"  Error starting playback: {e}")
        
        try:
            print("\nStarting recording and playback...")
            
            # Start playback
            playback_thread = threading.Thread(target=play_audio)
            playback_thread.start()
            
            # Small delay to ensure playback starts
            import time
            time.sleep(0.1)
            
            # Start recording
            self.recording = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=2,
                device=input_id
            )
            
            # Wait for recording to complete
            print("Recording in progress... Press Ctrl+C to stop early")
            # Check for stop signal periodically
            import time
            start_time = time.time()
            while not self.should_stop and (time.time() - start_time) < self.duration:
                time.sleep(0.1)  # Check every 100ms
                if sd.get_status()['active'] == 0:  # Recording finished naturally
                    break
            
            # If stop was requested, stop the recording
            if self.should_stop:
                print("\n\nRecording stopped by API request")
                sd.stop()
            else:
                sd.wait()  # Wait for natural completion
            
            print("Recording complete! Saving files...")
            
            # Save as stereo file
            stereo_filename = f"recordings/{output_prefix}_{timestamp}_stereo.wav"
            sf.write(stereo_filename, self.recording, self.sample_rate)
            print(f"✓ Saved: {stereo_filename}")
            
            # Save channels separately
            ch1_filename = f"recordings/{output_prefix}_{timestamp}_ch1.wav"
            ch2_filename = f"recordings/{output_prefix}_{timestamp}_ch2.wav"
            sf.write(ch1_filename, self.recording[:, 0], self.sample_rate)
            sf.write(ch2_filename, self.recording[:, 1], self.sample_rate)
            print(f"✓ Saved: {ch1_filename}")
            print(f"✓ Saved: {ch2_filename}")
            
            print("\n✓ All files saved successfully!")
            return True
            
        except KeyboardInterrupt:
            print("\n\nRecording interrupted by user")
            sd.stop()
            return False
        except Exception as e:
            print(f"\nError during recording: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Automated audio recorder for Rubix44'
    )
    parser.add_argument(
        'playback_file',
        help='WAV file to play during recording'
    )
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=3600,
        help='Recording duration in seconds (default: 3600 = 1 hour)'
    )
    parser.add_argument(
        '-r', '--rate',
        type=int,
        default=44100,
        help='Sample rate in Hz (default: 44100)'
    )
    parser.add_argument(
        '-o', '--output',
        default='recording',
        help='Output filename prefix (default: recording)'
    )
    parser.add_argument(
        '--input-device',
        help='Input device name or ID (default: auto-detect Rubix44)'
    )
    parser.add_argument(
        '--output-device',
        help='Output device name or ID (default: auto-detect Rubix44)'
    )
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List all available audio devices and exit'
    )
    
    args = parser.parse_args()
    
    # List devices if requested
    if args.list_devices:
        print("Available audio devices:")
        print("=" * 80)
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            print(f"\n[{i}] {device['name']}")
            print(f"    Inputs:  {device['max_input_channels']}")
            print(f"    Outputs: {device['max_output_channels']}")
            print(f"    Default SR: {device['default_samplerate']} Hz")
        return
    
    # Create recorder and start recording
    recorder = AudioRecorder(
        input_device=args.input_device,
        output_device=args.output_device,
        duration=args.duration,
        sample_rate=args.rate
    )
    
    recorder.record_with_playback(args.playback_file, args.output)

if __name__ == '__main__':
    main()
if __name__ == '__main__':
    main()
