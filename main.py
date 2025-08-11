import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import keyboard
import whisper
import time
import requests

print(sd.query_devices())

samplerate = 48000
duration = 10
device_id = 1
for rate in [8000, 11025, 16000, 22050, 32000, 44100, 48000]:
    try:
        sd.check_input_settings(device=device_id, samplerate=rate)
        print(f"✅ Funciona: {rate} Hz")
    except Exception as e:
        print(f"❌ {rate} Hz: {e}")

API_URL = "http://localhost:8000/ask"

print("Starting system... Loading Whisper model...")
model = whisper.load_model("base", device="cpu")
print("Model loaded. Press and hold [f9] to record.")

recording = False
audio = []

def send_transcription_to_api(transcription_text):
    payload = {
        "text": transcription_text, 
        "pre-prompt": "Atenção: responda com a menor quantidade de palavras possível. Não use emojis, não explique, apenas responda a pergunta com precisão e objetividade. Se não houver pergunta, diga 'Nada a responder'.",
        "model": "gemma3n:2b"
    }

    os.makedirs("logs", exist_ok=True)
    log_path = "logs/api_logs.txt"

    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        end_time = time.time()

        data = response.json()
        elapsed_time = end_time - start_time

        log_entry = (
            f"\n[LOG - {time.strftime('%Y-%m-%d %H:%M:%S')}]\n"
            f"Payload: {payload}\n"
            f"Response: {data}\n"
            f"Response time: {elapsed_time:.2f} seconds\n"
            f"{'-'*60}\n"
        )

        with open(log_path, "a") as log_file:
            log_file.write(log_entry)

        print("Payload sent to API:", payload)
        print("Response from API:", data)
        print(f"API response time: {elapsed_time:.2f} seconds")

    except Exception as e:
        error_entry = (
            f"\n[ERROR - {time.strftime('%Y-%m-%d %H:%M:%S')}]\n"
            f"Payload: {payload}\n"
            f"Error: {str(e)}\n"
            f"{'-'*60}\n"
        )

        with open(log_path, "a") as log_file:
            log_file.write(error_entry)

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
        while keyboard.is_pressed('f9'):
            sd.sleep(100)

    print("Recording stopped. Saving...")

    audio_np = np.concatenate(audio, axis=0)

    file_index = get_next_filename()
    audio_filename = f"recordings/audio_{file_index}.wav"
    transcript_filename = f"recordings/transcript_{file_index}.txt"

    wav.write(audio_filename, samplerate, audio_np)

    print("Transcribing with Whisper...")
    whisper_start = time.time()
    result = model.transcribe(audio_filename)
    whisper_end = time.time()

    transcription = result["text"]
    transcription_time = whisper_end - whisper_start
    print("Transcription:", transcription)
    print(f"Transcription time: {transcription_time:.2f} seconds")

    with open(transcript_filename, "w") as f:
        f.write("Transcription:\n")
        f.write(transcription + "\n\n")
        f.write(f"Transcription time: {transcription_time:.2f} seconds\n")

    send_transcription_to_api(transcription)


while True:
    if keyboard.is_pressed('f9') and not recording:
        print("\nRecording...")
        recording = True
        record()
        recording = False

    time.sleep(0.1)
