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
from agents.transcript_agent import TranscriptAgent


class MeetingBotAgent:
    """
    Orchestrates:
      - finds meetings in Google Calendar
      - opens Meet link
      - records + transcribes via TranscriptAgent
    """
    def __init__(self):
        self.browser_path = ProjectConfig.BROWSER_PATH
        self.transcript_agent = None

        # Initialize TranscriptAgent using env-driven selection (name > index)
        try:
            self.transcript_agent = TranscriptAgent()  # reads .env internally
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

    # ---------- record + transcribe ----------
    async def join_and_transcribe(self, meet_link: str, meeting_title: str):
        print(f"Joining + transcribing: {meeting_title}...")
        if not await self.open_meeting_in_browser(meet_link):
            return
        if self.transcript_agent is None:
            print("[Abort] TranscriptAgent not initialized.")
            return

        try:
            print("🎤 Transcription started (Ctrl+C to stop).")
            text = await self.transcript_agent.start_and_process_realtime(meeting_title)
            if text:
                print("✅ Transcription completed. Preview:")
                print(text[:400])
            else:
                print("⚠️ No text returned.")
        except KeyboardInterrupt:
            print("\n[Stopped] Transcription stopped by user.")
        except Exception as e:
            print(f"[Error] Transcription failed → {e}")

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
                            print(f"[Test Mode] Found: {meeting['title']}")
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
