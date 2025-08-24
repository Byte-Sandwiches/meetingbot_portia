#!/usr/bin/env python3

import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.meeting_agent import MeetingBotAgent

async def main():
    print("MeetingBot - Smart Calendar Meeting Manager")
    print("=" * 48)

    monitor_mode = "--monitor" in sys.argv or "-m" in sys.argv
    auto_open = "--auto-open" in sys.argv or "-a" in sys.argv
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    transcribe = "--transcribe" in sys.argv or "-x" in sys.argv

    if test_mode:
        print("Mode: TEST MODE (Checks meetings only, no actions)")
    elif monitor_mode:
        print("Mode: MONITORING MODE (Auto-checks every 2 minutes)")
        if auto_open:
            print("Option: Auto-opening enabled")
        if transcribe:
            print("Option: Transcription enabled via Portia AI")
    else:
        print("Mode: ONE-TIME MODE (Checks once and prompts for action)")

    if transcribe:
        print("Note: Transcription will be sent to Portia AI after joining")

    print()

    agent = MeetingBotAgent()
    await agent.run_workflow(
        monitor_mode=monitor_mode,
        auto_open=auto_open,
        test_mode=test_mode,
        transcribe=transcribe
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMeetingBot stopped by user.")
    except Exception as e:
        print(f"\nError: An unexpected error occurred. Error: {e}")