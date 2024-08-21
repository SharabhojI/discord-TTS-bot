## Imports ##
import discord
from discord import app_commands
from discord.ext import commands
import gtts.lang
from gtts import gTTS
import os
from dotenv import load_dotenv
import re
from collections import deque
from datetime import timedelta
import asyncio
import subprocess
import traceback

load_dotenv() # load .env containing bot token
intents = discord.Intents.all() # set bot intents

client = commands.Bot(command_prefix='-', intents=intents)
user_preferences = {} # Dictionary to store user preferences
tts_queue = asyncio.Queue()
TTS_CHANNEL_ID = None  # Stores the ID of the channel designated for TTS
inactivity_timer = 600 # Timer for Auto-disconnect, default 10 mins
last_activity = {} # Track the last time there was bot activity across guilds
last_user = {} # Track the last user who sent a TTS message

## Event Handlers ##
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} Command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@client.event
async def on_message(message):
    if message.author == client.user or not message.guild:
        return
    if message.guild.voice_client and message.guild.voice_client.is_connected() and message.channel.id == TTS_CHANNEL_ID:
        await tts_from_message(message)
    await client.process_commands(message)

## Bot Slash Commands ##
@client.tree.command(
    name='join',
    description='Dom Bousta has summoned his herald...'
)
async def join(ctx: discord.Interaction):
    try:
        await ctx.response.defer(ephemeral=True)  # Defer the response to give more time for processing
        if ctx.user.voice:
            channel = ctx.user.voice.channel
            permissions = channel.permissions_for(ctx.guild.me)
            if not permissions.connect or not permissions.speak:
                await ctx.followup.send("I don't have permission to join or speak in this voice channel.", ephemeral=True)
                return
            await channel.connect()
            await ctx.followup.send(f"Joined {channel.name}. Messages sent to the designated TTS text channel will be read aloud.", ephemeral=True)
        else:
            await ctx.followup.send("You need to join a voice channel first!", ephemeral=True)
    except Exception as e:
        await ctx.followup.send(f"Error joining: {e}", ephemeral=True)

@client.tree.command(
    name='leave',
    description='Dom Bousta has dismissed his herald...'
)
async def leave(ctx: discord.Interaction):
    try:
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
            await ctx.response.send_message("Left the voice channel.", ephemeral=True)
        else:
            await ctx.response.send_message("I am not in a voice channel!", ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error leaving: {e}", ephemeral=True)

@client.tree.command(
    name='setchannel',
    description='Dom Bousta wishes to hold court in another Palace...'
)
async def set_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    global TTS_CHANNEL_ID
    try:
        TTS_CHANNEL_ID = channel.id
        await ctx.response.send_message(f"TTS channel set to {channel.name}.", ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error in setting TTS channel: {e}", ephemeral=True)

@client.tree.command(
    name='setinactivetimer',
    description='Dom Bousta chooses when his servants are to be dismissed...'
)
async def set_inactivity_timer(ctx: discord.Interaction, minutes: int):
    global inactivity_timer
    try:
        inactivity_timer = minutes * 60  # Convert minutes to seconds
        await ctx.response.send_message(f"Inactivity timer set to {minutes} minutes.", ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error setting inactivity timer: {e}", ephemeral=True)

@client.tree.command(
    name='setlang',
    description='Dom Bousta changes his court language...'
)
async def setlang(ctx: discord.Interaction, lang: str):
    try:
        user_preferences[ctx.user.id] = user_preferences.get(ctx.user.id, {})
        user_preferences[ctx.user.id]['lang'] = lang
        await ctx.response.send_message(f"Language set to {lang}", ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error in setting language: {e}", ephemeral=True)

@client.tree.command(
    name='setspeed',
    description='Dom Bousta grows weary of his heralds rate of speech...'
)
async def setspeed(ctx: discord.Interaction, speed: float):
    try:
        user_preferences[ctx.user.id] = user_preferences.get(ctx.user.id, {})
        user_preferences[ctx.user.id]['speed'] = speed
        await ctx.response.send_message(f"Speed set to {speed}x", ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error in setting speed: {e}", ephemeral=True)

@client.tree.command(
    name='setpitch',
    description='Dom Bousta dislikes his heralds manner of speech...'
)
async def setpitch(ctx: discord.Interaction, pitch: float):
    try:
        user_preferences[ctx.user.id] = user_preferences.get(ctx.user.id, {})
        user_preferences[ctx.user.id]['pitch'] = pitch
        await ctx.response.send_message(f"Pitch set to {pitch}", ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error in setting pitch: {e}", ephemeral=True)

@client.tree.command(
    name='listlang',
    description='Dom Bousta wishes to know the languages spoken in his court...'
)
async def listlang(ctx: discord.Interaction):
    try:
        lang_list = gtts.lang.tts_langs()
        await ctx.response.send_message("\n".join(f'{k}: {v}' for k,v in lang_list.items()),ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error listing languages: {e}", ephemeral=True)

@client.tree.command(
    name='clearqueue',
    description='Dom Bousta has had enough of his petitioners...'
)
async def clearqueue(ctx: discord.Interaction):
    try:
        while not tts_queue.empty():
            await tts_queue.get()
        await ctx.response.send_message("The TTS queue has been cleared.", ephemeral=True)
    except Exception as e:
        await ctx.response.send_message(f"Error clearing queue: {e}", ephemeral=True)

## Read from channel to TTS ##
async def tts_from_message(message):
    global last_user
    global last_activity
    try:
        if message.guild.voice_client:
            user_pref = user_preferences.get(message.author.id, {})
            lang = user_pref.get('lang', 'en')
            speed = user_pref.get('speed', 1.0)
            pitch = user_pref.get('pitch', 1.0)

            content = re.sub(r'http\S+', '', message.content)

            for user in message.mentions:
                content = content.replace(f'<@{user.id}>', user.display_name)

            if message.author.id != last_user.get(message.guild.id):
                content = f"{message.author.display_name} says {content}"
                last_user[message.guild.id] = message.author.id

            tts = gTTS(content, lang=lang, slow=speed < 1.0)
            file_path = f"tts_{message.author.id}_{message.id}.mp3"
            tts.save(file_path)
            last_activity[message.guild.id] = discord.utils.utcnow()

            if pitch != 1.0:
                pitch_file_path = f"tts_pitch_{message.author.id}_{message.id}.mp3"
                subprocess.run(["ffmpeg", '-i', file_path, '-filter:a', f"asetrate=44100*{pitch}", pitch_file_path])
                os.remove(file_path)
                file_path = pitch_file_path

            await tts_queue.put((message.guild.voice_client, file_path))
            if not hasattr(client, 'tts_task') or client.tts_task.done():
                client.tts_task = asyncio.create_task(process_tts_queue())
        else:
            await message.channel.send("I need to be in a voice channel first. Use /join to invite me.", ephemeral=True)
    except Exception as e:
        print(f"Error processing TTS: {e}")
        traceback.print_exc()

async def process_tts_queue():
    while True:
        voice_client, file_path = await tts_queue.get()
        try:
            if voice_client.is_connected() and os.path.exists(file_path):
                # Wait for any current playback to finish
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
                # Play the next message in the queue
                voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=file_path),
                                  after=lambda e: asyncio.run_coroutine_threadsafe(after_playing(file_path), client.loop))
                # Wait for this message to finish playing
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
            else:
                print(f"Voice client disconnected or file not found: {file_path}")
        except Exception as e:
            print(f"Error processing TTS file {file_path}: {e}")
        finally:
            if tts_queue.empty():
                return
            else:
                tts_queue.task_done()

async def after_playing(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

## Inactivity functions ##
async def cleanup_inactive_users():
    global user_preferences, last_user, last_activity
    current_time = discord.utils.utcnow()
    inactive_threshold = timedelta(days=30)  # Adjust as needed

    for guild_id in list(last_activity.keys()):
        if current_time - last_activity[guild_id] > inactive_threshold:
            del last_activity[guild_id]
            if guild_id in last_user:
                del last_user[guild_id]

    for user_id in list(user_preferences.keys()):
        if not client.get_user(user_id):  # User no longer in any mutual guilds
            del user_preferences[user_id]

async def check_inactivity():
    global last_activity
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            current_time = discord.utils.utcnow()
            for guild_id, time in list(last_activity.items()):
                if (current_time - time).total_seconds() > inactivity_timer:
                    voice_client = discord.utils.get(client.voice_clients, guild__id=guild_id)
                    if voice_client and voice_client.is_connected():
                        await voice_client.disconnect()
                        print(f"Disconnected from guild {guild_id} due to inactivity.")
                        del last_activity[guild_id]  # Remove the entry to avoid repeated checks
            if current_time.minute == 0: # cleanup users every hour
                await cleanup_inactive_users()
        except Exception as e:
            print(f"Error checking for inactivity: {e}")
        await asyncio.sleep(60)  # Check every minute

async def setup_hook():
    client.loop.create_task(check_inactivity())
client.setup_hook = setup_hook

## Run the bot with stored token ##
token = os.getenv('BOT_TOKEN')
client.run(token)
