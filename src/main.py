import sys
import os
import json
import threading
import pyaudio
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


def transcribe_audio(overlay):
    # Load the Vosk model
    if not os.path.exists(MODEL_PATH):
        print(f"Model path '{MODEL_PATH}' does not exist!")
        sys.exit(1)

    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)

    # Setup PyAudio for microphone input
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)

    print("Listening for speech...")

    try:
        while True:
            # Read data from the microphone
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


def main():
    # Set up the PyQt application
    app = QApplication(sys.argv)
    overlay = OverlayWindow()

    # Start the transcription process in a separate thread
    thread = threading.Thread(target=transcribe_audio, args=(overlay,), daemon=True)
    thread.start()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
