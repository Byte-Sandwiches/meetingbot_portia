#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Configuration settings for the project, loaded from a .env file.
    """
    PORTIA_API_KEY = os.getenv('PORTIA_API_KEY')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
    ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')

    # Try to parse audio index to int if present, else None
    AUDIO_INPUT_INDEX = None
    try:
        val = os.getenv('AUDIO_INPUT_INDEX')
        if val is not None and val != "":
            # Accept quoted numbers too: strip quotes
            val = val.strip().strip('"').strip("'")
            AUDIO_INPUT_INDEX = int(val)
    except Exception:
        AUDIO_INPUT_INDEX = None

    GEMINI_MODEL = "gemini-1.5-flash"
    
    PORTIA_STORAGE_CLASS = "cloud"
    PORTIA_LOG_LEVEL = "INFO"
    
    BROWSER_TYPE = "chromium"
    BROWSER_HEADLESS = False
    BROWSER_PATH = "/usr/bin/chromium"  
    
    MEETING_CHECK_INTERVAL = 60
    TRANSCRIPT_CAPTURE_DELAY = 5
    
    @classmethod
    def validate(cls):
        """
        Validates that all required configuration keys are present.
        If you want to allow missing non-critical keys, remove them from the list.
        """
        required_keys = [
            'PORTIA_API_KEY',
            'GOOGLE_API_KEY',
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET',
            'ASSEMBLYAI_API_KEY'
            # AUDIO_INPUT_INDEX is optional if you want to disable transcription
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing required configuration: {', '.join(missing_keys)}")
        
        return True

# Validate on import so startup fails fast if critical keys are missing.
Config.validate()
