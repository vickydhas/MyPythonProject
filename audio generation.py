# python
import argparse
import pyttsx3
import sys
from pathlib import Path

def text_to_audio(text: str, out_path: str, rate: int | None = None, voice_index: int | None = None):
    """
    Convert text to audio and write to out_path.
    out_path extension typically should be .wav on some platforms.
    """
    engine = pyttsx3.init()
    if rate is not None:
        engine.setProperty("rate", rate)
    if voice_index is not None:
        voices = engine.getProperty("voices")
        if 0 <= voice_index < len(voices):
            engine.setProperty("voice", voices[voice_index].id)
    engine.save_to_file(text, out_path)
    engine.runAndWait()
    engine.stop()

def main():
    parser = argparse.ArgumentParser(description="Convert text to audio file (pyttsx3).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", "-t", help="Text to convert to audio.")
    group.add_argument("--infile", "-i", type=Path, help="Path to a text file to read input from.")
    parser.add_argument("--out", "-o", type=Path, required=True, help="Output audio file path (e.g. output.wav).")