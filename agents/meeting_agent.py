#!/usr/bin/env python3

import asyncio
import os
import subprocess
import webbrowser
from datetime import datetime, timedelta
from config.project_config import Config as ProjectConfig
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pickle
import os.path
import re
from agents.transcript_agent import TranscriptAgent

class MeetingBotAgent:
    def __init__(self):
        self.browser_path = ProjectConfig.BROWSER_PATH
        self.transcript_agent = None

    def _parse_meeting_time(self, time_str):
        try:
            if 'T' in time_str:
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
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

        time_diff = meeting_local - now_local
        minutes_until_meeting = time_diff.total_seconds() / 60

        should_open = 0 <= minutes_until_meeting <= minutes_before
        return should_open

    def _get_meeting_status(self, meeting):
        meeting_time = self._parse_meeting_time(meeting['start_time'])
        if not meeting_time:
            return "unknown"

        now = datetime.now()
        if meeting_time.tzinfo:
            meeting_local = meeting_time.astimezone()
            now_local = now.astimezone()
        else:
            meeting_local = meeting_time
            now_local = now

        time_diff = meeting_local - now_local
        minutes_diff = time_diff.total_seconds() / 60

        if minutes_diff < -30:
            return "past"
        elif minutes_diff < 0:
            return "ongoing"
        elif minutes_diff <= 5:
            return "starting_soon"
        else:
            return "upcoming"

    async def find_meetings(self):
        print("Checking Google Calendar for meetings...")
        try:
            creds = None
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)

                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())

            if not creds or not creds.valid:
                print("Task failed: Authentication is not valid. Please run `setup_google_calendar_auth.py`.")
                return []

            service = build('calendar', 'v3', credentials=creds)

            now = datetime.utcnow()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            meetings = []

            for event in events:
                meet_link = None
                if 'hangoutLink' in event:
                    meet_link = event['hangoutLink']
                elif 'conferenceData' in event:
                    entry_points = event['conferenceData'].get('entryPoints', [])
                    for entry_point in entry_points:
                        if 'meet.google.com' in entry_point.get('uri', ''):
                            meet_link = entry_point['uri']
                            break
                elif 'description' in event:
                    description = event['description']
                    if 'meet.google.com' in description:
                        match = re.search(r'https://meet\.google\.com/[a-z-]+', description)
                        if match:
                            meet_link = match.group()

                if meet_link:
                    meeting = {
                        'title': event.get('summary', 'Untitled Meeting'),
                        'start_time': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                        'end_time': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                        'meet_link': meet_link
                    }
                    meetings.append(meeting)
            
            print("Task completed: Found meetings.")
            return meetings

        except (ImportError, Exception) as e:
            print(f"Task failed: Could not find meetings. Error: {e}")
            return []

    async def open_meeting_in_browser(self, meet_link):
        print("Attempting to open meeting in browser...")
        try:
            if os.path.exists(self.browser_path):
                subprocess.Popen([self.browser_path, meet_link])
            else:
                webbrowser.open(meet_link)

            await asyncio.sleep(2)
            print("Task completed: Meeting opened successfully.")
            return True

        except Exception as e:
            print(f"Task failed: Could not open browser. Error: {e}")
            return False

    async def join_and_transcribe(self, meet_link: str, meeting_title: str):
        print(f"Starting workflow to join and transcribe '{meeting_title}'...")
        success = await self.open_meeting_in_browser(meet_link)

        if not success:
            print("Workflow aborted: Failed to open meeting.")
            return

        try:
            self.transcript_agent = TranscriptAgent()
        except Exception as e:
            print(f"Workflow aborted: Could not initialize TranscriptAgent. Error: {e}")
            return

        try:
            print("Starting live transcription. Press Ctrl+C to stop recording.")
            result = await self.transcript_agent.process_meeting_transcript(meeting_title)
            print("Transcription workflow completed.")
        except KeyboardInterrupt:
            print("Transcription stopped by user.")
        except Exception as e:
            print(f"Transcription workflow failed. Error: {e}")

    async def run_workflow(self, monitor_mode=False, auto_open=False, test_mode=False, transcribe=False):
        while True:
            try:
                if monitor_mode:
                    print("Monitoring calendar for meetings...")

                meetings = await self.find_meetings()

                meetings_to_join = [m for m in meetings if self._is_meeting_time(m['start_time'])]
                
                if meetings_to_join:
                    for meeting in meetings_to_join:
                        if test_mode:
                            print(f"Test mode: Found meeting '{meeting['title']}' but not joining.")
                        elif auto_open:
                            print(f"Auto-opening meeting: '{meeting['title']}'...")
                            if transcribe:
                                await self.join_and_transcribe(meeting['meet_link'], meeting['title'])
                            else:
                                await self.open_meeting_in_browser(meeting['meet_link'])
                        else:
                            try:
                                response = input(f"Meeting '{meeting['title']}' is starting now. Open it? (y/n): ").lower().strip()
                                if response in ['y', 'yes']:
                                    if transcribe:
                                        await self.join_and_transcribe(meeting['meet_link'], meeting['title'])
                                    else:
                                        await self.open_meeting_in_browser(meeting['meet_link'])
                                else:
                                    print("Meeting not joined.")
                            except (EOFError, KeyboardInterrupt):
                                print("\nUser interrupt received. Exiting.")
                                return
                
                if monitor_mode:
                    print("No meetings found. Waiting 2 minutes before checking again.")
                    await asyncio.sleep(120)
                else:
                    return

            except KeyboardInterrupt:
                if monitor_mode:
                    print("\nMonitoring stopped by user.")
                    return
                else:
                    raise
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                if monitor_mode:
                    print("Waiting 2 minutes before checking again.")
                    await asyncio.sleep(120)
                else:
                    return

if __name__ == "__main__":
    async def main():
        agent = MeetingBotAgent()
        await agent.run_workflow()

    asyncio.run(main())