import os
import sounddevice as sd
import numpy as np
import queue
import threading
import requests


class TranscriptAgent:
    def __init__(self, api_key=None, device_index=None):
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        self.device_index = int(device_index or os.getenv("AUDIO_INPUT_INDEX", 0))
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream = None

        # ✅ Try to get device info
        info = sd.query_devices(self.device_index, "input")
        default_rate = int(info["default_samplerate"])
        self.sample_rate = self._pick_valid_rate(default_rate)
        print(f"[Audio] Using device {self.device_index}: {info['name']} "
              f"(max_in={info['max_input_channels']}, rate={self.sample_rate})")

    def _pick_valid_rate(self, default_rate):
        """Test if default sample rate works, else fall back."""
        test_rates = [default_rate, 16000, 44100, 48000]
        for rate in test_rates:
            try:
                with sd.InputStream(samplerate=rate, device=self.device_index, channels=1):
                    return rate
            except Exception:
                continue
        raise RuntimeError("❌ Could not find a valid sample rate for this mic.")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"[Audio Warning] {status}")
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        if self.is_recording:
            return

        self.is_recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            device=self.device_index,
            callback=self._audio_callback
        )
        self.stream.start()
        print("🎤 Transcription started (Ctrl+C to stop).")

        # Start uploader thread
        threading.Thread(target=self._uploader, daemon=True).start()

    def stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        print("🛑 Transcription stopped.")

    def _downsample(self, audio, target_rate=16000):
        """Convert mic rate → target rate (if needed)."""
        if self.sample_rate == target_rate:
            return audio
        duration = len(audio) / self.sample_rate
        new_length = int(duration * target_rate)
        return np.interp(
            np.linspace(0, len(audio), new_length, endpoint=False),
            np.arange(len(audio)),
            audio
        ).astype(np.float32)

    def _uploader(self):
        """Continuously read mic data, downsample, and send to API"""
        while self.is_recording:
            try:
                audio_chunk = self.audio_queue.get(timeout=1)
                # Flatten array
                audio_chunk = audio_chunk.flatten()

                # ✅ Downsample if needed
                chunk_16k = self._downsample(audio_chunk, target_rate=16000)

                # 🔥 Send to Portia/AssemblyAI/etc (dummy example)
                self._send_to_transcriber(chunk_16k)

            except queue.Empty:
                continue

    def _send_to_transcriber(self, chunk):
        """Stub: Replace with your transcription API logic"""
        headers = {"authorization": self.api_key}
        print(f"[Uploader] Sending {len(chunk)} samples to API...")
        # Example:
        # requests.post("https://api.assemblyai.com/v2/stream",
        #               headers=headers, data=chunk.tobytes())
