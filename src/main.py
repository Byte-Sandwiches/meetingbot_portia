#!/usr/bin/env python3
import argparse
import asyncio
import os
import signal
import sys
from agents.meeting_agent import MeetingBotAgent
from dotenv import load_dotenv

load_dotenv()

def banner():
    print("MeetingBot - Smart Calendar Meeting Manager")
    print("=============================================")

async def main():
    parser = argparse.ArgumentParser(description="MeetingBot runner")
    parser.add_argument("--monitor", action="store_true", help="Enable monitoring mode")
    parser.add_argument("--auto-open", action="store_true", help="Auto-open meetings without asking")
    parser.add_argument("--test", action="store_true", help="Detect meetings only, no join")
    parser.add_argument("--transcribe", action="store_true", help="Enable transcription")
    parser.add_argument("--device", type=int, help="Force audio input device index")
    args = parser.parse_args()

    banner()
    if args.monitor:
        print("Mode: MONITORING MODE (Auto-checks every 2 minutes)")
    else:
        print("Mode: MANUAL MODE")
    if args.transcribe:
        print("Option: Transcription enabled")
    if args.device is not None:
        print(f"[Audio] Using device index {args.device}")
        os.environ["AUDIO_DEVICE_INDEX"] = str(args.device)
    print()

    bot = MeetingBotAgent()
    try:
        await bot.run_workflow(
            monitor_mode=args.monitor,
            auto_open=args.auto_open,
            test_mode=args.test,
            transcribe=args.transcribe,
        )
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user.")

if __name__ == "__main__":
    # Graceful shutdown
    def shutdown(signum, frame):
        print("\n👋 Application stopped by user.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user.")
    except Exception as e:
        print(f"[Fatal Error] {e}")
        sys.exit(1)