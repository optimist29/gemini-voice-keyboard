import asyncio
import threading
import sounddevice as sd
import pyperclip
from pynput import keyboard
from google import genai
from google.genai import types

# Initialize Gemini Client (reads GEMINI_API_KEY from environment)
client = genai.Client()
is_recording = False
final_transcripts = []

SYSTEM_INSTRUCTION = """
Convert user speech into clean, polished written text.
1. Remove all vocal fillers ("um", "uh", "like", "you know").
2. Resolve any false starts or self-corrections naturally (e.g. "Tuesday, wait no, Wednesday" -> "Wednesday").
3. Automatically apply correct capitalization, punctuation, and paragraphs.
4. Output ONLY the resulting polished text. Do NOT add conversational replies.
"""

async def run_voice_session():
    global is_recording, final_transcripts
    final_transcripts = []
    
    async with client.aio.live.connect(
        model="gemini-2.0-flash-exp",
        config=types.LiveConnectConfig(
            response_modalities=[types.LiveModality.TEXT],
            system_instruction=types.Content(parts=[types.Part.from_text(SYSTEM_INSTRUCTION)])
        )
    ) as session:
        loop = asyncio.get_running_loop()
        
        def callback(indata, frames, time_info, status):
            if is_recording:
                asyncio.run_coroutine_threadsafe(
                    session.send(input={"data": indata.tobytes(), "mime_type": "audio/pcm;rate=16000"}),
                    loop
                )
                
        with sd.InputStream(samplerate=16000, channels=1, dtype="int16", callback=callback, blocksize=1024):
            async for response in session.receive():
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.text:
                            final_transcripts.append(part.text)
                if not is_recording:
                    break

def paste_output():
    text = "".join(final_transcripts).strip()
    if text:
        pyperclip.copy(text)
        kb = keyboard.Controller()
        # On macOS use Key.cmd; on Windows/Linux use Key.ctrl
        with kb.pressed(keyboard.Key.cmd):
            kb.tap("v")

def on_press(key):
    global is_recording
    if key == keyboard.Key.f8 and not is_recording:
        is_recording = True
        print("\n🎙️ [Recording... Speak naturally]")
        threading.Thread(target=lambda: asyncio.run(run_voice_session()), daemon=True).start()

def on_release(key):
    global is_recording
    if key == keyboard.Key.f8 and is_recording:
        is_recording = False
        print("🛑 [Processing & Pasting...]")
        threading.Thread(target=paste_output, daemon=True).start()

if __name__ == "__main__":
    print("✨ Gemini Voice Keyboard active.")
    print("👉 Hold [F8] anywhere to dictate. Release to paste clean text.")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
