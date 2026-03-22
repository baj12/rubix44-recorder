#!/usr/bin/env python3
"""
Automated audio recorder for Rubix44
Records two channels while playing back a WAV file through Rubix44
"""

import argparse
import logging
import os
import queue
import sys
import threading
import time
from datetime import datetime

import numpy as np
import sounddevice as sd
import soundfile as sf

# Set up logging - use the rubix_recorder logger
# This will inherit api_server's configuration when used via the API
logger = logging.getLogger('rubix_recorder')


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
        Record audio while playing back a file through Rubix44.
        Uses streaming writes to disk to keep memory usage constant regardless
        of recording duration (avoids the ~1.27 GB allocation from sd.rec()).
        """
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
            self.input_device = input_id
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
            self.output_device = output_id
        else:
            output_id = self.output_device

        input_device_info = sd.query_devices(input_id)
        output_device_info = sd.query_devices(output_id)

        print(f"\nRecording Configuration:")
        print(f"  Input Device: {input_device_info['name']}")
        print(f"  Output Device: {output_device_info['name']}")
        print(f"  Duration: {self.duration} seconds ({self.duration/60:.1f} minutes)")
        print(f"  Sample rate: {self.sample_rate} Hz")
        print(f"  Recording channels: 2")
        print(f"  Output prefix: {output_prefix}")
        print(f"  Timestamp: {timestamp}")

        # Ensure playback data is stereo
        if len(playback_data.shape) == 1:
            playback_data = np.column_stack([playback_data, playback_data])
            print("  Note: Converted mono playback to stereo")

        # Resample playback to match recording sample rate.
        # Running input and output streams at different sample rates on the same
        # device is a known source of driver instability.
        if playback_sr != self.sample_rate:
            print(f"  Resampling playback from {playback_sr} Hz to {self.sample_rate} Hz...")
            try:
                from math import gcd
                from scipy.signal import resample_poly
                g = gcd(int(playback_sr), int(self.sample_rate))
                playback_data = resample_poly(
                    playback_data, int(self.sample_rate) // g, int(playback_sr) // g, axis=0
                )
                playback_sr = self.sample_rate
                print(f"  Resampled playback to {self.sample_rate} Hz")
            except Exception as e:
                print(f"  Warning: Could not resample playback ({e}). Proceeding with mismatched rates.")

        # Loop playback to cover the full recording duration
        playback_frames_needed = int(self.duration * playback_sr)
        if len(playback_data) < playback_frames_needed:
            loops_needed = int(np.ceil(playback_frames_needed / len(playback_data)))
            looped = np.tile(playback_data, (loops_needed, 1))
            playback_to_play = looped[:playback_frames_needed]
            print(f"  Looping playback {loops_needed}x to cover {self.duration}s")
        else:
            playback_to_play = playback_data[:playback_frames_needed]

        # Output file paths
        os.makedirs('recordings', exist_ok=True)
        stereo_filename = f"recordings/{output_prefix}_{timestamp}_stereo.wav"
        ch1_filename = f"recordings/{output_prefix}_{timestamp}_ch1.wav"
        ch2_filename = f"recordings/{output_prefix}_{timestamp}_ch2.wav"

        # Thread-safe queue: audio callback enqueues chunks; a writer thread drains
        # them to disk.  This keeps memory at ~one chunk (~350 KB at 4096 frames)
        # regardless of recording duration, avoiding the previous ~1.27 GB allocation.
        audio_queue = queue.Queue(maxsize=500)
        write_error = [None]
        total_frames_written = [0]

        def audio_callback(indata, frames, time_info, status):  # noqa: ARG001
            if status:
                logger.warning(f"Audio stream status: {status}")
            try:
                audio_queue.put_nowait(indata.copy())
            except queue.Full:
                logger.error("Audio queue full — dropping frames (disk write too slow?)")

        def writer_thread_fn():
            try:
                with (
                    sf.SoundFile(stereo_filename, mode='w', samplerate=self.sample_rate, channels=2) as stereo_f,
                    sf.SoundFile(ch1_filename, mode='w', samplerate=self.sample_rate, channels=1) as ch1_f,
                    sf.SoundFile(ch2_filename, mode='w', samplerate=self.sample_rate, channels=1) as ch2_f,
                ):
                    while True:
                        try:
                            data = audio_queue.get(timeout=2.0)
                            if data is None:  # sentinel: recording finished
                                break
                            stereo_f.write(data)
                            ch1_f.write(data[:, 0:1])
                            ch2_f.write(data[:, 1:2])
                            total_frames_written[0] += len(data)
                        except queue.Empty:
                            continue
            except Exception as e:
                write_error[0] = e
                logger.error(f"Writer thread error: {e}", exc_info=True)

        writer = threading.Thread(target=writer_thread_fn, daemon=True)

        def _stop_playback():
            try:
                sd.stop()
            except Exception as e:
                logger.warning(f"Error stopping playback: {e}")

        def _drain_writer():
            audio_queue.put(None)  # sentinel
            writer.join(timeout=60)

        try:
            print("\nStarting recording and playback...")
            writer.start()

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=2,
                device=input_id,
                callback=audio_callback,
                blocksize=4096,
            ):
                # Start playback (non-blocking; plays on the output device)
                sd.play(playback_to_play, playback_sr, device=output_id)
                print("Recording in progress... Press Ctrl+C to stop early")

                start_time = time.time()
                while not self.should_stop and (time.time() - start_time) < self.duration:
                    time.sleep(0.1)
            # Exiting the 'with' block stops and closes the InputStream.

            if self.should_stop:
                print("\n\nRecording stopped by API request")
            _stop_playback()
            _drain_writer()

            if write_error[0]:
                raise RuntimeError(f"Audio file write failed: {write_error[0]}")

            frames = total_frames_written[0]
            logger.info(f"Recording complete. Wrote {frames} frames ({frames / self.sample_rate:.1f}s) to 3 files.")
            print(f"Recording complete! Saved {frames / self.sample_rate:.1f}s of audio.")
            try:
                print(f"[OK] Saved: {stereo_filename}")
                print(f"[OK] Saved: {ch1_filename}")
                print(f"[OK] Saved: {ch2_filename}")
            except UnicodeEncodeError:
                print(f"Saved: {stereo_filename}, {ch1_filename}, {ch2_filename}")
            print("\n[OK] All files saved successfully!")
            return True

        except KeyboardInterrupt:
            print("\n\nRecording interrupted by user")
            _stop_playback()
            _drain_writer()
            return False
        except Exception as e:
            logger.error(f"Error during recording: {e}", exc_info=True)
            print(f"\nError during recording: {e}")
            import traceback
            traceback.print_exc()
            _stop_playback()
            _drain_writer()
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
