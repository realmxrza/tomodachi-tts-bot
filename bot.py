import asyncio
import json
import os
import random
import re
import tempfile

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TTS_API_URL = "https://talkmodachi.dylanpdx.io/tts"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_voices.json")

LANGUAGES: dict[str, str] = {
    "useng": "US English",
    "eueng": "EU English",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "jp": "Japanese",
    "kr": "Korean",
}

DEFAULT_VOICE: dict = {
    "pitch": 50,
    "speed": 50,
    "quality": 50,
    "tone": 50,
    "accent": 50,
    "intonation": 1,
    "lang": "useng",
}

PRESETS: dict[str, dict] = {
    "youngm": {"pitch": 60, "speed": 59, "quality": 72, "tone": 25, "accent": 25, "intonation": 1, "lang": "useng"},
    "youngf": {"pitch": 83, "speed": 65, "quality": 78, "tone": 25, "accent": 25, "intonation": 1, "lang": "useng"},
    "adultm": {"pitch": 33, "speed": 52, "quality": 39, "tone": 25, "accent": 25, "intonation": 1, "lang": "useng"},
    "adultf": {"pitch": 68, "speed": 39, "quality": 58, "tone": 25, "accent": 25, "intonation": 1, "lang": "useng"},
    "oldm":   {"pitch": 25, "speed": 29, "quality": 39, "tone": 15, "accent": 25, "intonation": 1, "lang": "useng"},
    "oldf":   {"pitch": 67, "speed": 18, "quality": 69, "tone": 12, "accent": 42, "intonation": 1, "lang": "useng"},
}

tts_channels: dict[int, int] = {}

audio_queues: dict[int, asyncio.Queue] = {}

queue_tasks: dict[int, asyncio.Task] = {}

tone_switch_index: dict[str, int] = {}

GIF_URL_RE = re.compile(
    r"https?://\S*?(?:tenor\.com|giphy\.com|\.gif(?:\?\S*)?)\S*",
    re.IGNORECASE,
)
CUSTOM_EMOJI_RE = re.compile(r"<a?:\w+:\d+>|:[A-Za-z0-9_]+:")
UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


SLANG_MAP: dict[str, str] = {
    "RN": "Right now",
    "BTW": "By the way",
    "AAF": "Always a friend",
    "AAK": "Asleep at keyboard",
    "AFK": "Away from keyboard",
    "BRB": "Be right back",
    "AAMOF": "As a matter of fact",
    "FAQ": "Frequently asked questions",
    "B2K": "Back to keyboard",
    "BTK": "Back to keyboard",
    "FACK": "Full acknowledge",
    "AKA": "Also known as",
    "FKA": "Formerly known as",
    "FYI": "For your information",
    "HF": "Have fun",
    "GL": "Good luck",
    "HTH": "Hope this helps",
    "IDK": "I don't know",
    "IOW": "In other words",
    "IMO": "In my opinion",
    "IMHO": "In my humble opinion",
    "NNTR": "No need to reply",
    "NRN": "No reply necessary",
    "TBC": "To be continued",
    "TIA": "Thanks in advance",
    "TGIF": "Thank God it's Friday",
    "TQ": "Thank you",
    "TY": "Thank you",
    "TQVM": "Thank you very much",
    "TYT": "Take your time",
    "TTYL": "Talk to you later",
    "L8R": "Later",
    "WFM": "Works for me",
    "WRT": "With regard to",
    "WTH": "What the hell",
    "WTF": "What the fuck",
    "YMMD": "You made my day",
    "ICYMI": "In case you missed it",
    "LMAO": "Laughing my ass off",
    "OMG": "Oh my God",
    "OMFG": "Oh my fucking God",
    "WOL": "Wake on LAN",
    "FPS": "Frames per second",
    "CPS": "Clicks per second",
    "DOS": "Disk operating system",
    "DDOS": "Distributed Denial of Service",
    "ILY": "I love you",
    "GTG": "Got to go",
    "BBL": "Be back later",
    "GN": "Goodnight",
    "GM": "Good morning",
    "TS": "This shit",
    "FR": "For real",
    "IDC": "I don't care",
    "LMK": "Let me know",
    "TBH": "To be honest",
    "SMH": "Shaking my head",
    "IG": "I guess",
    "IYKYK": "If you know, you know",
    "AF": "As fuck",
    "PLS": "Please",
    "IRL": "In real life",
    "JK": "Just kidding",
    "PPL": "People",
    "NGL": "Not gonna lie",
    "IKR": "I know right",
    "THX": "Thanks",
    "HBD": "Happy Birthday",
    "OMW": "On my way",
    "OTW": "On the way",
}

SLANG_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in SLANG_MAP) + r")\b",
    re.IGNORECASE,
)


def expand_slang(text: str) -> str:
    return SLANG_RE.sub(lambda m: SLANG_MAP[m.group(0).upper()], text)


def sanitize_for_tts(text: str) -> str:
    text = GIF_URL_RE.sub("", text)
    text = CUSTOM_EMOJI_RE.sub("", text)
    text = UNICODE_EMOJI_RE.sub("", text)
    text = expand_slang(text)
    return text.strip()


def load_voices() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_voices(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_user_voice(user_id: str, voices: dict) -> dict:
    return {**DEFAULT_VOICE, **voices.get(user_id, {})}


async def ensure_queue(guild_id: int) -> asyncio.Queue:
    if guild_id not in audio_queues:
        audio_queues[guild_id] = asyncio.Queue()
    return audio_queues[guild_id]


async def queue_worker(guild_id: int) -> None:
    queue = audio_queues[guild_id]
    loop = asyncio.get_event_loop()

    while True:
        item = await queue.get()

        if item is None:
            queue.task_done()
            break

        wav_path, voice_client = item

        if voice_client and voice_client.is_connected():
            done_event = asyncio.Event()

            def after_play(error):
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass
                loop.call_soon_threadsafe(done_event.set)

            try:
                source = discord.FFmpegPCMAudio(wav_path)
                voice_client.play(source, after=after_play)
                await done_event.wait()
            except Exception as exc:
                print(f"[TTS] Playback error in guild {guild_id}: {exc}")
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass
        else:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

        queue.task_done()


async def enqueue_tts(guild_id: int, voice_client: discord.VoiceClient, wav_path: str) -> None:
    queue = await ensure_queue(guild_id)
    await queue.put((wav_path, voice_client))

    task = queue_tasks.get(guild_id)
    if task is None or task.done():
        queue_tasks[guild_id] = asyncio.create_task(queue_worker(guild_id))


async def stop_queue(guild_id: int) -> None:
    if guild_id in audio_queues:
        await audio_queues[guild_id].put(None)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    await bot.tree.sync()
    print(f"[TTS Bot] Ready — logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> None:
    guild = member.guild
    voice_client: discord.VoiceClient | None = guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        return

    bot_channel = voice_client.channel
    if before.channel != bot_channel:
        return

    human_members = [m for m in bot_channel.members if not m.bot]
    if human_members:
        return

    tts_channels.pop(guild.id, None)
    if voice_client.is_playing():
        voice_client.stop()
    await stop_queue(guild.id)
    await voice_client.disconnect()


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    if tts_channels.get(guild_id) != message.channel.id:
        return

    voice_client: discord.VoiceClient | None = message.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        return

    text = sanitize_for_tts(message.clean_content)
    if not text:
        return

    voices = load_voices()
    uid = str(message.author.id)
    voice = get_user_voice(uid, voices)

    if voice.get("tone_switch"):
        idx = tone_switch_index.get(uid, 0)
        intonation = (idx % 4) + 1
        tone_switch_index[uid] = idx + 1
    else:
        intonation = voice["intonation"]

    params = {
        "text": text,
        "pitch": voice["pitch"],
        "speed": voice["speed"],
        "quality": voice["quality"],
        "tone": voice["tone"],
        "accent": voice["accent"],
        "intonation": intonation,
        "lang": voice["lang"],
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(TTS_API_URL, params=params) as resp:
                if resp.status != 200:
                    print(f"[TTS] API returned {resp.status} for guild {guild_id}")
                    return
                audio_data = await resp.read()
    except Exception as exc:
        print(f"[TTS] Request failed: {exc}")
        return

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        tmp.write(audio_data)
    finally:
        tmp.close()

    await enqueue_tts(guild_id, voice_client, tmp.name)


@bot.tree.command(name="join", description="Join your voice channel and enable TTS in this text channel")
async def cmd_join(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers.", ephemeral=True)
        return

    member = interaction.guild.get_member(interaction.user.id)
    if not member or not member.voice or not member.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel first.", ephemeral=True)
        return

    vc_channel = member.voice.channel

    existing_vc: discord.VoiceClient | None = interaction.guild.voice_client
    if existing_vc:
        await existing_vc.move_to(vc_channel)
    else:
        await vc_channel.connect()

    tts_channels[interaction.guild.id] = interaction.channel.id
    await interaction.response.send_message(f"Joined **{vc_channel.name}**")


@bot.tree.command(name="leave", description="Leave the voice channel and stop TTS")
async def cmd_leave(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers.", ephemeral=True)
        return

    voice_client: discord.VoiceClient | None = interaction.guild.voice_client
    if not voice_client:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
        return

    left_channel = voice_client.channel
    tts_channels.pop(interaction.guild.id, None)

    if voice_client.is_playing():
        voice_client.stop()

    await stop_queue(interaction.guild.id)
    await voice_client.disconnect()
    await interaction.response.send_message(f"Left **{left_channel.name}**")


voice_group = app_commands.Group(name="voice", description="Manage your personal TTS voice settings")


@voice_group.command(name="set", description="Customise your TTS voice (any parameter can be omitted)")
@app_commands.describe(
    lang="Language for TTS",
    pitch="Voice pitch 0–100 (default 50)",
    speed="Speech speed 0–100 (default 50)",
    quality="Voice quality 0–100 (default 50)",
    tone="Voice tone 0–100 (default 50)",
    accent="Accent strength 0–100 (default 50)",
    intonation="Intonation style 1–4 (default 1)",
)
@app_commands.choices(lang=[
    app_commands.Choice(name="US English", value="useng"),
    app_commands.Choice(name="EU English", value="eueng"),
    app_commands.Choice(name="Spanish", value="es"),
    app_commands.Choice(name="German", value="de"),
    app_commands.Choice(name="French", value="fr"),
    app_commands.Choice(name="Italian", value="it"),
    app_commands.Choice(name="Japanese", value="jp"),
    app_commands.Choice(name="Korean", value="kr"),
])
async def voice_set(
    interaction: discord.Interaction,
    lang: str | None = None,
    pitch: app_commands.Range[int, 0, 100] | None = None,
    speed: app_commands.Range[int, 0, 100] | None = None,
    quality: app_commands.Range[int, 0, 100] | None = None,
    tone: app_commands.Range[int, 0, 100] | None = None,
    accent: app_commands.Range[int, 0, 100] | None = None,
    intonation: app_commands.Range[int, 1, 4] | None = None,
) -> None:
    voices = load_voices()
    uid = str(interaction.user.id)
    current = get_user_voice(uid, voices)

    updates = {k: v for k, v in {
        "lang": lang, "pitch": pitch, "speed": speed,
        "quality": quality, "tone": tone,
        "accent": accent, "intonation": intonation,
    }.items() if v is not None}

    if not updates:
        await interaction.response.send_message(
            "Provide at least one parameter to change. See `/voice show` for current settings.",
            ephemeral=True,
        )
        return

    current.update(updates)
    voices[uid] = current
    save_voices(voices)

    lang_name = LANGUAGES.get(current["lang"], current["lang"])
    await interaction.response.send_message(
        f"**Voice updated!**\n"
        f"Language: **{lang_name}**\n"
        f"Pitch: **{current['pitch']}** | Speed: **{current['speed']}** | Quality: **{current['quality']}**\n"
        f"Tone: **{current['tone']}** | Accent: **{current['accent']}** | Intonation: **{current['intonation']}**",
        ephemeral=True,
    )


@voice_group.command(name="show", description="Show your current TTS voice settings")
async def voice_show(interaction: discord.Interaction) -> None:
    voices = load_voices()
    current = get_user_voice(str(interaction.user.id), voices)
    lang_name = LANGUAGES.get(current["lang"], current["lang"])

    await interaction.response.send_message(
        f"**Your voice settings:**\n"
        f"Language: **{lang_name}**\n"
        f"Pitch: **{current['pitch']}** | Speed: **{current['speed']}** | Quality: **{current['quality']}**\n"
        f"Tone: **{current['tone']}** | Accent: **{current['accent']}** | Intonation: **{current['intonation']}**",
        ephemeral=True,
    )


@voice_group.command(name="preset", description="Apply a Talkmodachi character voice preset")
@app_commands.describe(name="Choose a character type")
@app_commands.choices(name=[
    app_commands.Choice(name="Young Man",   value="youngm"),
    app_commands.Choice(name="Young Woman", value="youngf"),
    app_commands.Choice(name="Adult Man",   value="adultm"),
    app_commands.Choice(name="Adult Woman", value="adultf"),
    app_commands.Choice(name="Old Man",     value="oldm"),
    app_commands.Choice(name="Old Woman",   value="oldf"),
])
async def voice_preset(interaction: discord.Interaction, name: str) -> None:
    preset = PRESETS.get(name)
    if not preset:
        await interaction.response.send_message("Unknown preset.", ephemeral=True)
        return

    voices = load_voices()
    uid = str(interaction.user.id)
    current = get_user_voice(uid, voices)
    current.update(preset)
    voices[uid] = current
    save_voices(voices)

    preset_label = {
        "youngm": "Young Man", "youngf": "Young Woman",
        "adultm": "Adult Man", "adultf": "Adult Woman",
        "oldm":   "Old Man",   "oldf":   "Old Woman",
    }.get(name, name)
    lang_name = LANGUAGES.get(current["lang"], current["lang"])
    await interaction.response.send_message(
        f"**Preset applied: {preset_label}**\n"
        f"Language: **{lang_name}**\n"
        f"Pitch: **{current['pitch']}** | Speed: **{current['speed']}** | Quality: **{current['quality']}**\n"
        f"Tone: **{current['tone']}** | Accent: **{current['accent']}** | Intonation: **{current['intonation']}**",
        ephemeral=True,
    )


@voice_group.command(name="toneswitch", description="Toggle automatic intonation cycling (1→2→3→4→1…) per message")
async def voice_toneswitch(interaction: discord.Interaction) -> None:
    voices = load_voices()
    uid = str(interaction.user.id)
    current = get_user_voice(uid, voices)
    current["tone_switch"] = not current.get("tone_switch", False)
    tone_switch_index.pop(uid, None)
    voices[uid] = current
    save_voices(voices)
    state = "**enabled**" if current["tone_switch"] else "**disabled**"
    await interaction.response.send_message(f"Tone switching {state}.", ephemeral=True)


@voice_group.command(name="randomize", description="Randomize all your voice settings")
async def voice_randomize(interaction: discord.Interaction) -> None:
    voices = load_voices()
    uid = str(interaction.user.id)
    current = get_user_voice(uid, voices)
    current.update({
        "pitch":      random.randint(0, 100),
        "speed":      random.randint(0, 100),
        "quality":    random.randint(0, 100),
        "tone":       random.randint(0, 100),
        "accent":     random.randint(0, 100),
        "intonation": random.randint(1, 4),
        "lang":       random.choice(list(LANGUAGES.keys())),
    })
    voices[uid] = current
    save_voices(voices)
    lang_name = LANGUAGES.get(current["lang"], current["lang"])
    await interaction.response.send_message(
        f"**Voice randomized!**\n"
        f"Language: **{lang_name}**\n"
        f"Pitch: **{current['pitch']}** | Speed: **{current['speed']}** | Quality: **{current['quality']}**\n"
        f"Tone: **{current['tone']}** | Accent: **{current['accent']}** | Intonation: **{current['intonation']}**",
        ephemeral=True,
    )


@voice_group.command(name="reset", description="Reset your TTS voice settings to defaults")
async def voice_reset(interaction: discord.Interaction) -> None:
    voices = load_voices()
    voices[str(interaction.user.id)] = DEFAULT_VOICE.copy()
    save_voices(voices)
    await interaction.response.send_message("Voice settings reset to defaults.", ephemeral=True)


bot.tree.add_command(voice_group)

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN not set. Add it to your .env file.")
    bot.run(TOKEN)
