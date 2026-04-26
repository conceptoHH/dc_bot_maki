from discord.app_commands import command
import os
import sys # Make sure to import this at the top of your file or here
import asyncio
import yt_dlp
import discord
from discord.ext import commands
import dotenv
import logging

dotenv.load_dotenv()
disc_token = os.environ.get('DISCORD_TOKEN')
user = os.environ.get('GOOGLE_USER')
pasw = os.environ.get('GOOGLE_PASS')
if not disc_token:
    raise RuntimeError("No se encontro el .env")

ytdl_format_options = {
    'format': 'bestaudio[ext=webm]/bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': False,
    'no_warnings': False,
    'default_search': 'auto',
    'source_address': '0.0.0.0', # bind to ipv4 since ipv6 addresses cause issues sometimes
    'cookiesfrombrowser': ('firefox', '9dyqdr9b.default-release'), #Se añadio para que funcione con cookies y google no flaggee al bot
    'remote_components': ['ejs:github'], #para que el runtime pueda pasar los challenges
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class Music(commands.Cog):
    """
    TO_DO: 
        Skip_button
        Skip_cancion_seleccionada
        get_queue_list
    """

    def __init__(self,bot):
        self.bot = bot
        self.queues = {}

    @commands.command()
    async def join(self, ctx):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(ctx.author.voice.channel)
        if ctx.author.voice:
            await ctx.author.voice.channel.connect() 

    @commands.command()
    async def play(self, ctx, url):
        await self.ensure_voice(ctx)

        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []


        if ctx.voice_client.is_playing():
            self.queues[ctx.guild.id].append(url)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

            await ctx.channel.send(f"Added {data['title']} to the *queue*")
            return
        else:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            filename = data['url']
            print(f"Extracted URL starts with: {filename[:30]}...") # Let's see what we actually got

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M -multiple_requests 1',
                'options': '-vn'
            }

            # Try the high-quality Opus stream first
            try:
                audio_src = await discord.FFmpegOpusAudio.from_probe(filename, **ffmpeg_options)
                print("Playing via Native Opus!")
            # If the probe fails (because it's an m3u8 or mp4), fall back to standard PCM
            except Exception as e:
                print(f"Opus probe failed, falling back to PCM: {e}")
                audio_src = discord.FFmpegPCMAudio(filename)

            ctx.voice_client.play(audio_src, after=lambda e: self.play_next_sync(ctx, e))
    
    @commands.command()
    async def testsound(self, ctx):
        import shutil
        await self.ensure_voice(ctx)
        
        # 1. Dynamically find the TRUE absolute path to ffmpeg.exe
        ffmpeg_absolute_path = shutil.which('ffmpeg')
        
        if not ffmpeg_absolute_path:
            await ctx.send("❌ Python cannot resolve the absolute path to FFmpeg.")
            return
            
        await ctx.send(f"✅ Bypassing Windows alias. Using path: `{ffmpeg_absolute_path}`")

        try:
            # 2. Force discord.py to use the physical executable, not the PATH alias
            audio_src = discord.FFmpegPCMAudio('test.mp3', executable=ffmpeg_absolute_path)
            ctx.voice_client.play(audio_src)
            
        except Exception as e:
            await ctx.send(f"❌ Audio engine failed: {e}")

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        else:
            await ctx.channel.send('There is no song playing right now you dummy (*-.-)')
    
    @commands.command()
    async def skip(self,ctx):
        if len(self.queues[ctx.guild.id]) > 0 and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        else: 
            await ctx.channel.send('There is no more songs in the queue right now (o.O)')

    @commands.command()
    async def list(self,ctx):
        num = 1
        for t in self.queues[ctx.guild.id]:
            await ctx.channel.send(f'{num}.- {t}')
            num += 1

    async def play_next(self, ctx):
        if len(self.queues[ctx.guild.id]) > 0:
            next_url = self.queues[ctx.guild.id].pop(0)

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(next_url, download=False))
            filename = data['url']

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M -multiple_requests 1',
                'options': '-vn'
            }

            audio_src = await discord.FFmpegOpusAudio.from_probe(filename, **ffmpeg_options)

            ctx.voice_client.play(audio_src, after=lambda e: self.play_next_sync(ctx, e))
    
    def play_next_sync(self, ctx, error):
        if error:
            print(f'Player error {error}')

        fut = asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

        try:
            fut.result()
        except Exception as e:
            print(f'Error al añadir la cancion a la cola de reproduccion: {e}') 


    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send('You are not connected to a voice channel.')
                raise commands.CommandError('Author not connected to a voice channel.')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


bot = commands.Bot(
    command_prefix='!',
    description='Relative simple music bot',
    intents=intents
)

@bot.event
async def on_ready():
    # Tell the type checker that User is filled up at this point
    assert bot.user is not None

    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    print(f'Is Opus Audio loaded?: {discord.opus.is_loaded()}')
    print('------')

async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(f'{disc_token}')

asyncio.run(main())
