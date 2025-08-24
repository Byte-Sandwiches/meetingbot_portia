import pyaudio

def list_audio_devices():
    """
    Lists all available audio input devices and their supported sample rates.
    """
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("Available Audio Input Devices:")
    for i in range(0, numdevices):
        device_info = p.get_device_info_by_index(i)
        
        # Check if the device is an input device
        if device_info.get('maxInputChannels') > 0:
            print("-" * 30)
            print(f"Device Index: {i}")
            print(f"Device Name: {device_info.get('name')}")
            print(f"Max Input Channels: {device_info.get('maxInputChannels')}")
            
            # Check for supported sample rates, especially 16000 Hz
            is_16k_supported = False
            for rate in [8000, 11025, 16000, 22050, 44100, 48000]:
                try:
                    if p.is_format_supported(
                        rate,
                        input_device=i,
                        input_channels=device_info.get('maxInputChannels'),
                        input_format=pyaudio.paInt16
                    ):
                        print(f"  - Supports {rate} Hz")
                        if rate == 16000:
                            is_16k_supported = True
                except:
                    pass
            if not is_16k_supported:
                print("  - 16000 Hz not explicitly supported.")
                
    p.terminate()

if __name__ == '__main__':
    list_audio_devices()
