# tomodachi-tts-bot

A Discord TTS bot that uses [Talkmodachi](https://github.com/dylanpdx/talkmodachi) to make Miis from Tomodachi Life read your messages out loud in a voice channel.

Each user gets their own voice that persists across sessions. You can tune it manually or pick from the six character types straight out of the game.

## Features

- Reads every message in a designated text channel aloud while the bot is in a voice channel
- Per-user voice profiles saved to disk
- Six built-in presets matching Tomodachi Life's character types (Young Man, Young Woman, Adult Man, Adult Woman, Old Man, Old Woman)
- Full manual control over pitch, speed, quality, tone, accent, and intonation
- Tone switching — automatically cycles intonation 1→2→3→4 on each message for a more expressive delivery
- Voice randomizer
- Auto-disconnects when the last person leaves the voice channel

## Requirements

- Python 3.10+
- FFmpeg installed and on PATH
- A Discord bot token with the **Message Content** privileged intent enabled

## Setup

1. Clone the repo and install dependencies

```
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your bot token

```
DISCORD_TOKEN=your_token_here
```

3. Run it

```
python bot.py
```

## Commands

| Command | Description |
|---|---|
| `/join` | Join your voice channel and enable TTS in the current text channel |
| `/leave` | Leave the voice channel |
| `/voice set` | Adjust any combination of pitch, speed, quality, tone, accent, intonation, language |
| `/voice preset` | Apply a Tomodachi Life character preset |
| `/voice toneswitch` | Toggle automatic intonation cycling per message |
| `/voice randomize` | Randomize all voice settings |
| `/voice show` | Show your current settings |
| `/voice reset` | Reset to defaults |

## Supported languages

US English, EU English, Spanish, German, French, Italian, Japanese, Korean

## Notes

Voice settings are saved in `user_voices.json` next to the script. This file is excluded from the repo — if you're hosting on a platform with ephemeral storage, settings will reset on each redeploy unless you attach a persistent disk.

The bot depends on the public Talkmodachi instance at `talkmodachi.dylanpdx.io`. If that goes down, TTS won't work. You can self-host it by following the instructions in the [Talkmodachi repo](https://github.com/dylanpdx/talkmodachi) and changing `TTS_API_URL` in `bot.py`.

## Credits

TTS powered by [Talkmodachi](https://github.com/dylanpdx/talkmodachi) by dylanpdx.
