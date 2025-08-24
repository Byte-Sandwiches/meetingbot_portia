#!/usr/bin/env python3

import asyncio
import os
import time
import threading
import requests
import json
from datetime import datetime
from config.project_config import Config as ProjectConfig
from typing import Dict, Any, Optional
import pyaudio
import wave

class TranscriptAgent:
    def __init__(self):
        self.is_recording = False
        self.audio_chunk_size = 1024
        self.sample_rate = 44100
        self.channels = 1
        self.format = pyaudio.paInt16
        self.audio_buffer = []
        self.transcript_file = None
        self.portia_api_key = ProjectConfig.PORTIA_API_KEY
        self.portia_base_url = "https://api.portia.ai"
        self.recording_start_time = None
        self.audio_instance = None
        self.stream = None

    def _parse_meeting_title_for_filename(self, title):
        sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        return sanitized_title.replace(" ", "_")

    async def start_recording(self):
        print("Starting audio recording...")
        self.is_recording = True
        self.audio_buffer = []
        self.recording_start_time = datetime.now()

        try:
            self.audio_instance = pyaudio.PyAudio()
            self.stream = self.audio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.audio_chunk_size
            )
            print("Task completed: Recording started successfully.")
            self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.recording_thread.start()
        except Exception as e:
            print(f"Task failed: Could not open microphone. Error: {e}")
            self.is_recording = False
            self.audio_instance.terminate()

    def _record_loop(self):
        try:
            while self.is_recording:
                data = self.stream.read(self.audio_chunk_size, exception_on_overflow=False)
                self.audio_buffer.append(data)
        except Exception as e:
            print(f"Task failed: Recording thread encountered an error. Error: {e}")
        finally:
            self._cleanup_stream()

    def _cleanup_stream(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        if self.audio_instance:
            try:
                self.audio_instance.terminate()
            except:
                pass

    async def stop_recording(self) -> Optional[str]:
        if not self.is_recording:
            return self.transcript_file

        print("Stopping audio recording...")
        self.is_recording = False
        await asyncio.sleep(0.5)

        if hasattr(self, 'recording_thread'):
            self.recording_thread.join(timeout=2)

        timestamp = int(time.time())
        filename = f"recordings/meeting_{timestamp}.wav"
        os.makedirs("recordings", exist_ok=True)

        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio_instance.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.audio_buffer))
            self.transcript_file = filename
            print(f"Task completed: Audio saved to {filename}")
            return filename
        except Exception as e:
            print(f"Task failed: Failed to save audio. Error: {e}")
            return None

    async def save_analysis_to_file(self, result: Dict[Any, Any], title: str) -> Optional[str]:
        print("Saving AI analysis to a local file...")
        try:
            filename = f"transcripts/{self._parse_meeting_title_for_filename(title)}_{int(time.time())}.txt"
            os.makedirs("transcripts", exist_ok=True)
            
            with open(filename, "w") as f:
                f.write("PORTIA AI ANALYSIS RESULT\n")
                f.write("="*60 + "\n\n")

                if "transcription" in result:
                    f.write("TRANSCRIPT:\n")
                    f.write(result["transcription"] + "\n\n")

                if "summary" in result:
                    f.write("SUMMARY:\n")
                    for point in result["summary"]:
                        f.write(f"- {point}\n")
                    f.write("\n")

                if "action_items" in result and result["action_items"]:
                    f.write("ACTION ITEMS:\n")
                    for item in result["action_items"]:
                        assignee = item.get("assignee", "Unassigned")
                        task = item.get("task", "No task")
                        due = item.get("due_date", "No due date")
                        f.write(f"- {task} -> @{assignee} (Due: {due})\n")
                    f.write("\n")

                if "keywords" in result:
                    f.write(f"KEYWORDS: {', '.join(result['keywords'])}\n\n")

                if "sentiment" in result:
                    f.write(f"SENTIMENT: {result['sentiment'].get('overall', 'N/A')} (Score: {result['sentiment'].get('score', 0):.2f})\n\n")

                f.write("="*60 + "\n")
            
            print(f"Task completed: Analysis saved to {filename}")
            return filename
        except Exception as e:
            print(f"Task failed: Could not save analysis to file. Error: {e}")
            return None

    async def send_to_portia(self, audio_path: str, meeting_title: str = "Untitled Meeting") -> Dict[Any, Any]:
        if not os.path.exists(audio_path):
            print(f"Task failed: Audio file not found at {audio_path}")
            return {"error": "file_not_found"}

        print(f"Sending audio file {audio_path} to Portia for analysis...")
        url = f"{self.portia_base_url}/api/v1/transcribe"
        headers = {"Authorization": f"Bearer {self.portia_api_key}"}
        
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data = {
                'title': meeting_title,
                'model': ProjectConfig.GEMINI_MODEL,
                'features': json.dumps([
                    "transcription",
                    "summary",
                    "action_items",
                    "sentiment",
                    "keywords"
                ])
            }

            try:
                response = requests.post(url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    print("Task completed: Successfully received AI insights from Portia.")
                    return response.json()
                else:
                    print(f"Task failed: Portia API Error [{response.status_code}] - {response.text}")
                    return {"error": response.text, "status_code": response.status_code}
            except requests.exceptions.RequestException as e:
                print(f"Task failed: Network error while connecting to Portia. Error: {e}")
                return {"error": "network_error"}
            except Exception as e:
                print(f"Task failed: An unexpected error occurred. Error: {e}")
                return {"error": "unknown"}

    async def process_meeting_transcript(self, meeting_title: str = "Untitled Meeting") -> Dict[Any, Any]:
        print("Starting meeting transcription process...")
        await self.start_recording()
        
        try:
            while self.is_recording:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Interrupt received. Finalizing recording...")
        finally:
            audio_file = await self.stop_recording()

        if not audio_file:
            print("Process failed: No audio file was generated.")
            return {}

        result = await self.send_to_portia(audio_file, meeting_title)

        if not result.get("error"):
            print("Process completed: AI analysis successful.")
            await self.save_analysis_to_file(result, meeting_title)
            self._pretty_print_result(result)
        else:
            print("Process failed: Could not get AI insights from Portia.")

        return result

    def _pretty_print_result(self, result: Dict):
        print("\n" + "="*60)
        print("PORTIA AI ANALYSIS RESULT")
        print("="*60)

        if "transcription" in result:
            print("TRANSCRIPT (First 3 lines):")
            lines = result["transcription"].split('\n')[:3]
            for line in lines:
                print(f"   - {line}")
            print("   ...")

        if "summary" in result:
            print("\nSUMMARY:")
            for point in result["summary"]:
                print(f"   - {point}")

        if "action_items" in result and result["action_items"]:
            print("\nACTION ITEMS:")
            for item in result["action_items"]:
                assignee = item.get("assignee", "Unassigned")
                task = item.get("task", "No task")
                due = item.get("due_date", "No due date")
                print(f"   - {task} -> @{assignee} (Due: {due})")

        if "keywords" in result:
            print(f"\nKEYWORDS: {', '.join(result['keywords'][:5])}")

        if "sentiment" in result:
            print(f"\nSENTIMENT: {result['sentiment'].get('overall', 'N/A')} (Score: {result['sentiment'].get('score', 0):.2f})")

        print("\nFull data available in JSON response.")
        print("="*60)

if __name__ == "__main__":
    async def test():
        agent = TranscriptAgent()
        print("Starting test recording. Speak for 5 seconds...")
        await agent.start_recording()
        await asyncio.sleep(5)
        await agent.stop_recording()
        print("Test recording saved.")

    asyncio.run(test())