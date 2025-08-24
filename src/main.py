#!/usr/bin/env python3
import argparse
import asyncio
import os
import signal
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
    await bot.run_workflow(
        monitor_mode=args.monitor,
        auto_open=args.auto_open,
        test_mode=args.test,
        transcribe=args.transcribe,
    )

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Graceful shutdown on Ctrl+C
    def shutdown(sig, frame):
        print("\n👋 Monitoring stopped (cancelled by user).")
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.stop()

    signal.signal(signal.SIGINT, shutdown)

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
