#!/usr/bin/env python3


import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    
    PORTIA_API_KEY = os.getenv('PORTIA_API_KEY')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
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
        """Validate required configuration"""
        required_keys = [
            'PORTIA_API_KEY',
            'GOOGLE_API_KEY', 
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET'
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing required configuration: {', '.join(missing_keys)}")
        
        return True

Config.validate()