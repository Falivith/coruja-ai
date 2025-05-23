import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import keyboard
import whisper
import time
import requests

samplerate = 16000
duration = 10

API_URL = "http://localhost:8000/ask"

print("Starting system... Loading Whisper model...")
model = whisper.load_model("small", device="cpu")
print("Model loaded. Press and hold [space] to record.")

recording = False
audio = []

def send_transcription_to_api(transcription_text):
    payload = {
        "text": transcription_text, 
        "pre-prompt": "Be clear, serious, and answer fast: ", 
        "model": "qwen3:4b"
        }
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        print("Response from API:", data)
    except Exception as e:
        print("Failed to send transcription to API:", e)

os.makedirs("recordings", exist_ok=True)

def get_next_filename():
    existing = os.listdir("recordings")
    audio_files = [f for f in existing if f.endswith(".wav")]
    nums = []
    for f in audio_files:
        try:
            num = int(f.split("_")[1].split(".")[0])
            nums.append(num)
        except:
            continue
    next_num = max(nums) + 1 if nums else 1
    return next_num

def record():
    global audio
    audio = []

    def callback(indata, frames, time, status):
        audio.append(indata.copy())

    with sd.InputStream(callback=callback, samplerate=samplerate, channels=1):
        while keyboard.is_pressed('space'):
            sd.sleep(100)

    print("Recording stopped. Saving...")

    audio_np = np.concatenate(audio, axis=0)

    file_index = get_next_filename()
    audio_filename = f"recordings/audio_{file_index}.wav"
    transcript_filename = f"recordings/transcript_{file_index}.txt"

    wav.write(audio_filename, samplerate, audio_np)

    print("Transcribing with Whisper...")
    result = model.transcribe(audio_filename)
    transcription = result["text"]
    print("Transcription:", transcription)

    with open(transcript_filename, "w") as f:
        f.write(transcription)

    send_transcription_to_api(transcription)

while True:
    if keyboard.is_pressed('space') and not recording:
        print("\nRecording...")
        recording = True
        record()
        recording = False

    time.sleep(0.1)
