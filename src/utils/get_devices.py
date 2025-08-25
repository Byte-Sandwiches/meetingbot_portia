#!/usr/bin/env python3
import sounddevice as sd

print("Available audio input devices:")
print("=" * 50)
devices = sd.query_devices()
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"[{i}] {device['name']}")
        print(f"    Channels: {device['max_input_channels']}, Sample Rate: {int(device['default_samplerate'])}")
        print()

print("Current .env setting:")
print(f"AUDIO_INPUT_INDEX = 10")