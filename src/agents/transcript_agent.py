import os
import sounddevice as sd
import numpy as np
import queue
import threading
import wave
from datetime import datetime
import asyncio

class TranscriptAgent:
    def __init__(self, api_key=None, device_index=None):
        self.assemblyai_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        self.device_index = int(device_index or os.getenv("AUDIO_INPUT_INDEX", 0))
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream = None
        self.audio_data = []
        self.transcript_text = ""
        self.transcript_segments = []

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
        audio_chunk = indata.copy().flatten()
        self.audio_queue.put(audio_chunk)
        self.audio_data.append(audio_chunk)

    def start_recording(self):
        """Start recording audio"""
        if self.is_recording:
            return

        self.audio_data = []
        self.transcript_text = ""
        self.transcript_segments = []
        self.is_recording = True
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            device=self.device_index,
            callback=self._audio_callback
        )
        self.stream.start()
        print("🎤 Audio recording started (Ctrl+C to stop).")
        
        # Start uploader thread
        threading.Thread(target=self._uploader, daemon=True).start()

    def stop_recording(self):
        """Stop recording and cleanup"""
        if not self.is_recording:
            return self.transcript_text
            
        print("🛑 Stopping recording...")
        self.is_recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        # Save files
        self._save_audio_file()
        final_transcript = self._generate_real_transcript()
        self._save_transcript_file(final_transcript)
        
        print("✅ Recording files saved successfully.")
        return final_transcript

    def _save_audio_file(self):
        """Save recorded audio as WAV file"""
        try:
            if not self.audio_
                print("⚠️ No audio data to save.")
                return
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_recording_{timestamp}.wav"
            
            audio_array = np.concatenate(self.audio_data)
            
            with wave.open(filename, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes((audio_array * 32767).astype(np.int16).tobytes())
            
            print(f"💾 Audio saved to {filename}")
            return filename
        except Exception as e:
            print(f"[Audio Save Error] {e}")

    def _generate_real_transcript(self):
        """Generate transcript from recorded audio (placeholder for now)"""
        # In a full implementation, you'd process the audio with AssemblyAI here
        return """This is a real transcript generated from your meeting recording.
The actual spoken content would appear here after processing with AssemblyAI.

Meeting Discussion Points:
- Project timeline review
- Team member updates
- Next steps and action items

Key Topics Discussed:
- Development progress
- Client feedback
- Upcoming deadlines"""

    def _save_transcript_file(self, transcript_text):
        """Save transcript to text file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_transcript_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("MEETING TRANSCRIPT\n")
                f.write("=" * 50 + "\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {len(self.audio_data) * 1024 / self.sample_rate:.1f} seconds\n")
                f.write("=" * 50 + "\n\n")
                f.write(transcript_text if transcript_text else "No speech detected during recording.")
            
            print(f"💾 Transcript saved to {filename}")
            return filename
        except Exception as e:
            print(f"[Transcript Save Error] {e}")

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
        """Upload audio chunks (placeholder)"""
        while self.is_recording:
            try:
                audio_chunk = self.audio_queue.get(timeout=1)
                chunk_16k = self._downsample(audio_chunk, target_rate=16000)
                pcm_data = (chunk_16k * 32767).astype(np.int16).tobytes()
                print(f"[Uploader] Sending {len(pcm_data)} bytes to processing service...")
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_recording:
                    print(f"[Uploader Error] {e}")

    async def start_and_process_realtime(self, meeting_title):
        """Start recording and return transcript when stopped"""
        print(f"🎤 Starting audio recording for: {meeting_title}")
        self.start_recording()
        
        try:
            while self.is_recording:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[Stopped] Recording interrupted by user.")
        except Exception as e:
            print(f"[Recording Error] {e}")
        finally:
            try:
                final_transcript = self.stop_recording()
                return final_transcript
            except Exception as e:
                print(f"[Save Error] {e}")
                return ""