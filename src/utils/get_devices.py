# src/utils/get_devices.py
import sounddevice as sd

print("Available audio devices:\n")
for idx, device in enumerate(sd.query_devices()):
    print(f"[{idx}] {device['name']}")
