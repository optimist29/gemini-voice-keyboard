import io
import wave
import threading
import sounddevice as sd
import numpy as np
import pyperclip
from pynput import keyboard
from google import genai
from google.genai import types
client = genai.Client()
is_recording = False
audio_frames = []
SYSTEM_INSTRUCTION = """
You are a real-time speech-to-text formatter.
1. Transcribe the user's speech accurately, but remove all vocal fillers ("um", "uh", "like", "you know").
2. Resolve any false starts or self-corrections naturally (e.g. "Tuesday, wait no, Wednesday" -> "Wednesday").
3. Automatically apply correct capitalization, punctuation, and paragraphs.
4. Output ONLY the resulting polished text. Do NOT add conversational replies or explanations.
"""
def record_callback(indata, frames, time, status):
    if is_recording:
        audio_frames.append(indata.copy())
def process_and_paste():
    global audio_frames
    if not audio_frames:
        return
    
    print("⏳ Polishing text with Gemini...")
    # Convert recorded PCM chunks to in-memory WAV
    audio_data = np.concatenate(audio_frames, axis=0)
    audio_frames = []
    
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(16000)
        wf.writeframes(audio_data.tobytes())
    wav_bytes = wav_io.getvalue()
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
                SYSTEM_INSTRUCTION
            ]
        )
        clean_text = response.text.strip()
        if clean_text:
            print(f"✅ Output: {clean_text}")
            pyperclip.copy(clean_text)
            kb = keyboard.Controller()
            # Command+V on macOS
            with kb.pressed(keyboard.Key.cmd):
                kb.tap('v')
    except Exception as e:
        print(f"❌ Error: {e}")
def on_press(key):
    global is_recording, audio_frames
    if key == keyboard.Key.f8 and not is_recording:
        is_recording = True
        audio_frames = []
        print("\n🎙️ [Recording... Speak naturally]")
def on_release(key):
    global is_recording
    if key == keyboard.Key.f8 and is_recording:
        is_recording = False
        print("🛑 [Processing & Pasting...]")
        threading.Thread(target=process_and_paste, daemon=True).start()
if __name__ == "__main__":
    print("✨ Gemini Voice Keyboard active.")
    print("👉 Hold [F8] (or Fn+F8) anywhere to dictate. Release to paste.")
    # Initialize background microphone listener
    with sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=record_callback):
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
