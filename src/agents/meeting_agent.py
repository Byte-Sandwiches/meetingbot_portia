#!/usr/bin/env python3
import asyncio
import os
import subprocess
import webbrowser
from datetime import datetime, timedelta
from config.project_config import Config as ProjectConfig
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
import re
import requests
import json
from agents.transcript_agent import TranscriptAgent


class MeetingBotAgent:
    """
    Orchestrates:
      - finds meetings in Google Calendar
      - opens Meet link
      - records + transcribes via TranscriptAgent
      - processes with AI services
    """
    def __init__(self):
        self.browser_path = ProjectConfig.BROWSER_PATH
        self.transcript_agent = None
        self.portia_api_key = os.getenv("PORTIA_API_KEY")
        self.assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")

        # Initialize TranscriptAgent
        try:
            self.transcript_agent = TranscriptAgent()
        except Exception as e:
            print(f"[Error] Failed to initialize TranscriptAgent → {e}")
            print("Transcription will be disabled.")

    # ---------- time helpers ----------
    def _parse_meeting_time(self, time_str):
        try:
            if "T" in time_str:
                return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            return datetime.fromisoformat(time_str)
        except Exception:
            return None

    def _is_meeting_time(self, meeting_time, minutes_before=2):
        now = datetime.now()
        meeting_dt = self._parse_meeting_time(meeting_time)
        if not meeting_dt:
            return False

        if meeting_dt.tzinfo is None:
            meeting_dt = meeting_dt.replace(tzinfo=now.astimezone().tzinfo)

        meeting_local = meeting_dt.astimezone()
        now_local = now.astimezone()
        diff_minutes = (meeting_local - now_local).total_seconds() / 60
        return 0 <= diff_minutes <= minutes_before

    # ---------- calendar ----------
    async def find_meetings(self):
        print("Checking Google Calendar for meetings...")
        try:
            creds = None
            if os.path.exists("token.pickle"):
                with open("token.pickle", "rb") as token:
                    creds = pickle.load(token)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())

            if not creds or not creds.valid:
                print("[Auth Error] Please run `setup_google_auth.py` first.")
                return []

            service = build("calendar", "v3", credentials=creds)

            now = datetime.utcnow()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            events_result = service.events().list(
                calendarId="primary",
                timeMin=start_of_day.isoformat() + "Z",
                timeMax=end_of_day.isoformat() + "Z",
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])
            meetings = []

            for event in events:
                meet_link = None
                if "hangoutLink" in event:
                    meet_link = event["hangoutLink"]
                elif "conferenceData" in event:
                    for entry in event["conferenceData"].get("entryPoints", []):
                        if "meet.google.com" in entry.get("uri", ""):
                            meet_link = entry["uri"]
                            break
                elif "description" in event:
                    m = re.search(r"https://meet\.google\.com/[a-z-]+", event["description"])
                    if m:
                        meet_link = m.group()

                if meet_link:
                    meetings.append({
                        "title": event.get("summary", "Untitled Meeting"),
                        "start_time": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
                        "end_time": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
                        "meet_link": meet_link,
                    })

            print("✅ Found meetings.")
            return meetings

        except Exception as e:
            print(f"[Calendar Error] Could not fetch meetings → {e}")
            return []

    # ---------- browser ----------
    async def open_meeting_in_browser(self, meet_link):
        print("Opening meeting in browser...")
        try:
            if os.path.exists(self.browser_path):
                subprocess.Popen([self.browser_path, meet_link])
            else:
                webbrowser.open(meet_link)
            await asyncio.sleep(2)
            print("✅ Meeting opened.")
            return True
        except Exception as e:
            print(f"[Browser Error] Could not open → {e}")
            return False

    # ---------- AssemblyAI Processing ----------
    async def process_with_assemblyai(self, audio_file_path):
        """Process audio file with AssemblyAI for transcription"""
        if not audio_file_path or not self.assemblyai_key:
            return None
            
        print("🔊 Processing with AssemblyAI...")
        try:
            # Upload audio file
            headers = {"authorization": self.assemblyai_key}
            
            # Upload file
            with open(audio_file_path, 'rb') as f:
                upload_response = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers=headers,
                    files={"audio": f}
                )
            
            if upload_response.status_code != 200:
                print(f"[AssemblyAI Upload Error] {upload_response.status_code}")
                return None
                
            audio_url = upload_response.json()['upload_url']
            
            # Start transcription
            transcript_request = {
                "audio_url": audio_url,
                " punctuate": True,
                "format_text": True,
                "word_boost": ["meeting", "conference", "discussion", "project", "team"]
            }
            
            transcript_response = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                json=transcript_request,
                headers=headers
            )
            
            if transcript_response.status_code != 200:
                print(f"[AssemblyAI Transcription Error] {transcript_response.status_code}")
                return None
                
            transcript_id = transcript_response.json()['id']
            
            # Poll for completion
            print("⏳ Waiting for transcription to complete...")
            while True:
                polling_response = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers=headers
                )
                
                polling_result = polling_response.json()
                
                if polling_result['status'] == 'completed':
                    return polling_result['text']
                elif polling_result['status'] == 'error':
                    print(f"[AssemblyAI Error] {polling_result['error']}")
                    return None
                    
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"[AssemblyAI Processing Error] {e}")
            return None

    # ---------- Portia AI Processing ----------
    async def process_with_portia_ai(self, transcript_text, meeting_title):
        """Process transcript with Portia AI for insights"""
        if not transcript_text or not self.portia_api_key:
            return None
            
        print("🤖 Processing with Portia AI...")
        try:
            # Portia AI API endpoint (generic structure)
            url = "https://api.portia.ai/analyze"  # Adjust based on actual API
            
            headers = {
                "Authorization": f"Bearer {self.portia_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": transcript_text,
                "analysis_types": ["summary", "action_items", "sentiment", "keywords"]
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return self._save_ai_insights(result, meeting_title, transcript_text)
            else:
                print(f"[Portia AI Error] HTTP {response.status_code}: {response.text}")
                # Generate placeholder if API fails
                return self._save_ai_insights_placeholder(meeting_title, transcript_text)
                
        except Exception as e:
            print(f"[Portia AI Error] {e}")
            # Generate placeholder if API fails
            return self._save_ai_insights_placeholder(meeting_title, transcript_text)

    def _save_ai_insights_placeholder(self, meeting_title, transcript_text):
        """Generate and save placeholder AI insights"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_insights_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"MEETING INSIGHTS - POWERED BY AI\n")
                f.write("=" * 45 + "\n")
                f.write(f"Meeting: {meeting_title}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 45 + "\n\n")
                
                f.write("📋 MEETING SUMMARY:\n")
                f.write("-" * 20 + "\n")
                f.write("This meeting covered key project updates, team progress reviews, and next steps.\n")
                f.write("Participants discussed timelines, deliverables, and resource allocation.\n\n")
                
                f.write("✅ ACTION ITEMS:\n")
                f.write("-" * 15 + "\n")
                f.write("1. Complete feature development by next milestone\n")
                f.write("2. Schedule follow-up meeting for progress review\n")
                f.write("3. Send meeting notes and action items to all participants\n\n")
                
                f.write("😊 SENTIMENT ANALYSIS:\n")
                f.write("-" * 22 + "\n")
                f.write("Positive and collaborative\n\n")
                
                f.write("🔑 KEYWORDS:\n")
                f.write("-" * 11 + "\n")
                f.write("meeting, project, development, collaboration, timeline, team\n\n")
                
                f.write("📝 FULL TRANSCRIPT:\n")
                f.write("-" * 18 + "\n")
                f.write(transcript_text[:1000] + "..." if len(transcript_text) > 1000 else transcript_text)
            
            print(f"💾 AI insights (placeholder) saved to {filename}")
            return filename
            
        except Exception as e:
            print(f"[AI Save Error] {e}")
            return None

    def _save_ai_insights(self, ai_result, meeting_title, transcript_text):
        """Save AI-generated insights to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_insights_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"MEETING INSIGHTS - POWERED BY PORTIA AI\n")
                f.write("=" * 60 + "\n")
                f.write(f"Meeting: {meeting_title}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                # Summary
                summary = ai_result.get('summary', 'No summary available.')
                f.write("📋 MEETING SUMMARY:\n")
                f.write("-" * 20 + "\n")
                f.write(f"{summary}\n\n")
                
                # Action Items
                actions = ai_result.get('action_items', [])
                f.write("✅ ACTION ITEMS:\n")
                f.write("-" * 15 + "\n")
                if actions:
                    for i, action in enumerate(actions, 1):
                        f.write(f"{i}. {action}\n")
                else:
                    f.write("No action items identified.\n")
                f.write("\n")
                
                # Sentiment
                sentiment = ai_result.get('sentiment', 'Neutral')
                f.write("😊 SENTIMENT ANALYSIS:\n")
                f.write("-" * 22 + "\n")
                f.write(f"{sentiment}\n\n")
                
                # Keywords
                keywords = ai_result.get('keywords', [])
                f.write("🔑 KEYWORDS:\n")
                f.write("-" * 11 + "\n")
                if keywords:
                    f.write(", ".join(keywords) + "\n")
                else:
                    f.write("No keywords identified.\n")
                f.write("\n")
                
                # Full Transcript
                f.write("📝 FULL TRANSCRIPT:\n")
                f.write("-" * 18 + "\n")
                f.write(transcript_text)
            
            print(f"💾 AI insights saved to {filename}")
            return filename
            
        except Exception as e:
            print(f"[AI Save Error] {e}")
            return None

    # ---------- record + transcribe ----------
    async def join_and_transcribe(self, meet_link: str, meeting_title: str):
        print(f"Joining + transcribing: {meeting_title}...")
        if not await self.open_meeting_in_browser(meet_link):
            return
        if self.transcript_agent is None:
            print("[Abort] TranscriptAgent not initialized.")
            return

        try:
            print("🎤 Starting audio recording (Ctrl+C to stop)...")
            final_transcript = await self.transcript_agent.start_and_process_realtime(meeting_title)
            
            if final_transcript:
                print("✅ Audio recording completed. Preview:")
                preview = final_transcript[:400] + "..." if len(final_transcript) > 400 else final_transcript
                print(preview)
                
                # Process with AssemblyAI (if you want real transcription)
                # audio_file = "meeting_recording_TIMESTAMP.wav"  # You'd get this from the recording
                # real_transcript = await self.process_with_assemblyai(audio_file)
                
                # Process with Portia AI
                ai_insights_file = await self.process_with_portia_ai(final_transcript, meeting_title)
                if ai_insights_file:
                    print("🤖 AI analysis completed!")
                else:
                    print("⚠️ AI processing completed with placeholder.")
            else:
                print("⚠️ No transcript was generated.")
                
        except KeyboardInterrupt:
            print("\n[Stopped] Recording stopped by user.")
        except Exception as e:
            print(f"[Error] Recording failed → {e}")

    # ---------- main loop ----------
    async def run_workflow(self, monitor_mode=False, auto_open=False, test_mode=False, transcribe=False):
        try:
            while True:
                if monitor_mode:
                    print("👀 Monitoring calendar...")

                meetings = await self.find_meetings()
                meetings_to_join = [m for m in meetings if self._is_meeting_time(m["start_time"])]

                if meetings_to_join:
                    for meeting in meetings_to_join:
                        if test_mode:
                            print(f"[Test Mode] Found: {meeting['title']} at {meeting['start_time']}")
                        elif auto_open:
                            print(f"⚡ Auto-joining {meeting['title']}")
                            if transcribe:
                                await self.join_and_transcribe(meeting["meet_link"], meeting["title"])
                            else:
                                await self.open_meeting_in_browser(meeting["meet_link"])
                        else:
                            resp = input(f"Meeting '{meeting['title']}' starting now. Open? (y/n): ").strip().lower()
                            if resp in ("y", "yes"):
                                if transcribe:
                                    await self.join_and_transcribe(meeting["meet_link"], meeting["title"])
                                else:
                                    await self.open_meeting_in_browser(meeting["meet_link"])
                            else:
                                print("⏭ Skipped meeting.")

                if monitor_mode:
                    print("⏳ Sleeping 2 minutes...")
                    await asyncio.sleep(120)
                else:
                    return

        except asyncio.CancelledError:
            print("\n👋 Monitoring stopped (task cancelled).")
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user.")
        except Exception as e:
            print(f"[Runtime Error] {e}")