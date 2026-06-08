# tomodachi-tts-bot

A Discord TTS bot that uses [Talkmodachi](https://github.com/dylanpdx/talkmodachi) to make Miis from Tomodachi Life read your messages out loud in a voice channel.

[Invite bot to your server](https://discord.com/oauth2/authorize?client_id=1513048347655540746)

## Features

- Reads every message in the voice channel where the bot is connected to
- Six presets: Young Man, Young Woman, Adult Man, Adult Woman, Old Man, Old Woman
- Full control over pitch, speed, quality, tone, accent, and intonation
- Tone switching: switch intonation 1→2→3→4 on each message
- Voice randomizer: randomize the voice settings

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
| `/join` | Join your voice channel |
| `/leave` | Leave the voice channel |
| `/voice set` | Adjust any combination of pitch, speed, quality, tone, accent, intonation, language |
| `/voice preset` | Apply character preset |
| `/voice toneswitch` | Toggle intonation switching per message |
| `/voice randomize` | Randomize all voice settings |
| `/voice show` | Show your current settings |
| `/voice reset` | Reset to defaults |

## Supported languages

US English, EU English, Spanish, German, French, Italian, Japanese, Korean

## Notes

Voice settings are saved in `user_voices.json` next to the script. This file is excluded from the repo — if you're hosting on a platform with ephemeral storage, settings will reset on each redeploy unless you attach a persistent disk.

The bot depends on the public Talkmodachi instance at `talkmodachi.dylanpdx.io`. If that goes down, TTS won't work. You can self-host it by following the instructions in the [Talkmodachi repo](https://github.com/dylanpdx/talkmodachi) and changing `TTS_API_URL` in `bot.py`.

## Credits

[Talkmodachi](https://github.com/dylanpdx/talkmodachi) by dylanpdx.
