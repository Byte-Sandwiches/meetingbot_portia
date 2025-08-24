# MeetingBot: The AI Meeting Agent

MeetingBot is an intelligent agent that automates the lifecycle of a meeting, from finding a scheduled event to joining the call, transcribing the discussion, and generating a concise summary with actionable insights. It leverages the **Google Calendar API** for scheduling, **`pyaudio`** for audio capture, and the **Portia AI** platform for powerful AI-driven analysis.

---

### Features

* **Automated Meeting Joining**: Automatically checks your Google Calendar for upcoming meetings and opens them at the right time.
* **AI-Powered Insights**: Uses Portia AI to transcribe meeting audio and generates a comprehensive summary, action items, sentiment analysis, and keywords.
* **Local File Storage**: Saves transcribed audio (`.wav`) and the AI-generated analysis (`.txt`) to local files for easy access and record-keeping.
* **Customizable Workflow**: Supports different modes for monitoring, auto-joining, and transcription via command-line arguments.
* **Clear Console Feedback**: Provides simple, informative messages about task status (e.g., "Checking Google Calendar," "Task completed," "Task failed").

---

### Getting Started

#### Prerequisites

* **Python 3.x**
* **A microphone**
* **A Google account** with a calendar.
* **A Portia AI account and API key.**

#### Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/your-username/meetingbot-portia.git](https://github.com/your-username/meetingbot-portia.git)
    cd meetingbot-portia
    ```
2.  Create and activate a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

#### Configuration

1.  **Google Calendar API**: Follow the instructions to get your `credentials.json` file. Run `python src/setup_google_calendar_auth.py` to authenticate and generate the `token.pickle` file.
2.  **Portia AI API Key**: Create a file named `config/project_config.py`.
3.  **Fill in the configuration details**:
    ```python
    class Config:
        PORTIA_API_KEY = "YOUR_PORTIA_API_KEY"
        BROWSER_PATH = "/usr/bin/chromium"  # Update this to your browser's executable path
    ```

---

### Usage

To run the MeetingBot, execute the `main.py` script from the `src` directory with the desired flags.

* **One-Time Check**: Checks for meetings once and prompts for action.
    ```bash
    python src/main.py
    ```
* **Monitor Mode**: Continuously monitors your calendar for upcoming meetings every two minutes.
    ```bash
    python src/main.py --monitor
    ```
* **Auto-Open Mode**: Automatically opens meeting links without a prompt.
    ```bash
    python src/main.py --monitor --auto-open
    ```
* **With Transcription**: Records and sends meeting audio to Portia AI for transcription.
    ```bash
    python src/main.py --monitor --auto-open --transcribe
    ```
* **Test Mode**: Checks for meetings but does not join them.
    ```bash
    python src/main.py --test
    ```

### Project Structure

```
.
├── agents/
│   ├── meeting_agent.py          # Core logic for finding and joining meetings.
│   └── transcript_agent.py       # Handles audio recording and Portia AI integration.
├── config/
│   ├── project_config.py         # Stores project-specific configuration (API keys, paths).
│   └── setup_google_calendar_auth.py # Utility script for Google API authentication.
├── recordings/                   # Directory to store raw meeting audio files.
├── transcripts/                  # Directory to store AI-generated text analysis.
├── src/
│   └── main.py                   # The main entry point of the application.
├── .gitignore                    # Specifies files and folders to ignore in Git.
├── README.md                     # This file.
└── requirements.txt              # Project dependencies.
```

---

### Future Enhancements
* Add support for other meeting platforms (e.g., Zoom, Microsoft Teams).
* Integrate with project management tools to automatically create tasks from action items.
* Develop a graphical user interface or a simple web dashboard.
* Implement real-time streaming to Portia AI for live transcription.
* also an future enhancement
