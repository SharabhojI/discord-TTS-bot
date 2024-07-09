# Custom TTS Discord Bot

This is a custom Discord text-to-speech (TTS) bot designed and created for South American friends without microphones. It allows for users to set a specific channel for TTS, adjust language, speed, and pitch settings, while ensuring the bot remains active only when needed through an inactivity disconnect feature.

## Features

- **Text-to-Speech**: Reads aloud messages posted in a designated channel.
- **Multi-Language Support**: Supports multiple languages for TTS, adjustable per user.
- **Speed and Pitch Adjustment**: Users can customize the speed and pitch of the TTS voice.
- **Automatic Disconnection**: Automatically disconnects from voice channels after a period of inactivity to conserve resources.
- **Dynamic Configuration**: Server administrators can dynamically set the text channel used for TTS and adjust the inactivity timer.

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- `discord.py` library
- `gtts` library for Google Text-to-Speech
- `ffmpeg` installed and accessible in the system's PATH for audio processing

### Installing Dependencies

Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```
Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### Configuration
Bot Token: Ensure you have a Discord Bot Token from the Discord Developer Portal.

Environment Setup: Place your bot token in a `.env` file in the root directory of your project:
`BOT_TOKEN=your_discord_bot_token_here`

FFmpeg: Make sure FFmpeg is installed and properly configured in your system's PATH.

### Running the Bot
Execute the bot script using Python:
```bash
python3 bot.py
```

## Usage

### Commands
- **/join**: Join a voice channel and activate TTS in the designated channel.
- **/leave**: Leave the voice channel and stop TTS.
- **/setchannel [channel]**: Set the specific text channel for TTS.
- **/setinactivetimer [minutes]**: Set the inactivity timer for auto-disconnect.
- **/setlang [language]**: Set the preferred language for TTS.
- **/setspeed [speed]**: Set the speech speed for TTS.
- **/setpitch [pitch]**: Set the speech pitch for TTS.
- **/listlang**: List the available languages for gTTS.
- **/clearqueue**: Clear the current TTS queue.

### Setting Up the TTS Channel
To designate a channel for TTS, use the **/setchannel** command followed by the channel name.
