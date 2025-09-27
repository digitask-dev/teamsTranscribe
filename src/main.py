import sys
import os
import json
import threading
import pyaudio
import numpy as np
from vosk import Model, KaldiRecognizer
from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from dotenv import load_dotenv
load_dotenv()

# Path to the Vosk model directory (set MODEL_PATH environment variable or use default)
MODEL_PATH = os.environ.get('MODEL_PATH', "./model/vosk-model-small-ja-0.22")

class OverlayWindow(QLabel):
    def __init__(self):
        super().__init__()

        # Setup the overlay window
        self.setWindowTitle("Live Transcription")
        self.setStyleSheet("font-size: 20px; color: white; background-color: rgba(0, 0, 0, 150);")
        self.setAlignment(Qt.AlignCenter)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.resize(800, 200)
        self.show()

    def update_text(self, text):
        if text.strip():  # Only update if text is not empty
            self.setText(text)


def transcribe_audio(overlay, use_system_audio=False):
    # Load the Vosk model
    if not os.path.exists(MODEL_PATH):
        print(f"Model path '{MODEL_PATH}' does not exist!")
        sys.exit(1)

    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)

    # Setup PyAudio
    p = pyaudio.PyAudio()
    
    if use_system_audio:
        # Try to find a WASAPI loopback device for system audio capture
        wasapi_devices = []
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            if "WASAPI" in dev_info.get('hostApi', 0) and "loopback" in dev_info.get('name', '').lower():
                wasapi_devices.append((i, dev_info))
        
        if wasapi_devices:
            device_index = wasapi_devices[0][0]
            print(f"Using system audio device: {wasapi_devices[0][1]['name']}")
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, 
                          input=True, frames_per_buffer=8000,
                          input_device_index=device_index)
        else:
            print("No WASAPI loopback device found. Falling back to microphone.")
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, 
                          input=True, frames_per_buffer=8000)
    else:
        # Use regular microphone input
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, 
                      input=True, frames_per_buffer=8000)

    print("Listening for speech...")

    try:
        while True:
            # Read data from the audio source
            data = stream.read(8000, exception_on_overflow=False)
            
            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()  # Get the transcription result
                transcription = json.loads(result).get("text", "")
                overlay.update_text(transcription)
            else:
                # Display interim results
                partial = recognizer.PartialResult()
                partial_text = json.loads(partial).get("partial", "")
                overlay.update_text(partial_text)
    except KeyboardInterrupt:
        print("Stopping transcription...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def transcribe_both_audio(overlay):
    # Load the Vosk model
    if not os.path.exists(MODEL_PATH):
        print(f"Model path '{MODEL_PATH}' does not exist!")
        sys.exit(1)

    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)

    # Setup PyAudio for both microphone and system audio
    p = pyaudio.PyAudio()
    
    # Find microphone device
    mic_stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, 
                      input=True, frames_per_buffer=8000)
    
    # Find system audio device (VB-CABLE or other loopback)
    system_stream = None
    loopback_devices = []
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        dev_name = dev_info.get('name', '').lower()
        # Check for various loopback device patterns
        if ('loopback' in dev_name or 
            'cable' in dev_name or 
            'vb-audio' in dev_name or
            'virtual' in dev_name):
            loopback_devices.append((i, dev_info))
    
    if loopback_devices:
        device_index = loopback_devices[0][0]
        print(f"Using system audio device: {loopback_devices[0][1]['name']}")
        system_stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, 
                             input=True, frames_per_buffer=8000,
                             input_device_index=device_index)
    else:
        print("No loopback device found. Using microphone only.")

    print("Listening for speech from both microphone and system audio...")
    print("Debug: Speaking into microphone should show transcription in overlay window")

    try:
        while True:
            # Read from microphone
            mic_data = mic_stream.read(8000, exception_on_overflow=False)
            
            # Read from system audio if available
            system_data = mic_data  # Default to mic data if no system audio
            if system_stream:
                try:
                    system_data = system_stream.read(8000, exception_on_overflow=False)
                except:
                    system_data = mic_data
            
            # Mix the audio streams
            mixed_data = mix_audio(mic_data, system_data)
            
            # Debug: Check if we're getting audio data
            audio_level = np.frombuffer(mixed_data, dtype=np.int16).std()
            if audio_level > 100:  # If audio level is above threshold
                print(f"Audio detected (level: {audio_level:.0f})")
            
            if recognizer.AcceptWaveform(mixed_data):
                result = recognizer.Result()  # Get the transcription result
                transcription = json.loads(result).get("text", "")
                print(f"Full result JSON: {result}")
                print(f"Full transcription: '{transcription}'")
                if transcription.strip():
                    overlay.update_text(transcription)
            else:
                # Display interim results
                partial = recognizer.PartialResult()
                partial_result = json.loads(partial)
                partial_text = partial_result.get("partial", "")
                print(f"Partial result JSON: {partial}")
                print(f"Partial: '{partial_text}'")
                if partial_text.strip():
                    overlay.update_text(partial_text)
    except KeyboardInterrupt:
        print("Stopping transcription...")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        if system_stream:
            system_stream.stop_stream()
            system_stream.close()
        p.terminate()


def mix_audio(data1, data2):
    """Mix two audio streams by averaging the samples"""
    
    # Convert bytes to numpy arrays
    arr1 = np.frombuffer(data1, dtype=np.int16)
    arr2 = np.frombuffer(data2, dtype=np.int16)
    
    # Ensure arrays are the same length
    min_len = min(len(arr1), len(arr2))
    arr1 = arr1[:min_len]
    arr2 = arr2[:min_len]
    
    # Mix by averaging
    mixed = ((arr1.astype(np.int32) + arr2.astype(np.int32)) / 2).astype(np.int16)
    
    return mixed.tobytes()


def list_audio_devices():
    """List all available audio devices for debugging"""
    p = pyaudio.PyAudio()
    print("\nAvailable audio devices:")
    print("-" * 50)
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        print(f"Device {i}: {dev_info['name']}")
        print(f"  Host API: {dev_info['hostApi']}")
        print(f"  Max Input Channels: {dev_info['maxInputChannels']}")
        print(f"  Max Output Channels: {dev_info['maxOutputChannels']}")
        print()
    p.terminate()

# Uncomment the line below to debug audio devices
# list_audio_devices()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Live audio transcription')
    parser.add_argument('--mic-only', action='store_true', 
                       help='Capture microphone audio only')
    parser.add_argument('--system-only', action='store_true', 
                       help='Capture system audio output only')
    args = parser.parse_args()
    
    # Set up the PyQt application
    app = QApplication(sys.argv)
    overlay = OverlayWindow()

    # Start the transcription process in a separate thread
    if args.mic_only:
        thread = threading.Thread(target=transcribe_audio, args=(overlay, False), daemon=True)
    elif args.system_only:
        thread = threading.Thread(target=transcribe_audio, args=(overlay, True), daemon=True)
    else:
        # Default: mixed audio from both sources
        thread = threading.Thread(target=transcribe_both_audio, args=(overlay,), daemon=True)
    
    thread.start()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
