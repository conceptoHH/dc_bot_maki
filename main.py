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

class QueueView(discord.ui.View):
    def __init__(self, music_cog, ctx):
        super().__init__(timeout=None)
        self.music_cog = music_cog
        self.ctx = ctx
        self.update_select()

    def update_select(self):
        self.clear_items()
        
        skip_btn = discord.ui.Button(label="Skip Current", style=discord.ButtonStyle.primary, custom_id="skip_current_btn")
        
        async def skip_current_callback(interaction: discord.Interaction):
            if self.ctx.voice_client and self.ctx.voice_client.is_playing():
                self.ctx.voice_client.stop()
                await interaction.response.send_message("Skipped current song!", ephemeral=False)
            else:
                await interaction.response.send_message("No song is playing right now.", ephemeral=True)
        skip_btn.callback = skip_current_callback
        self.add_item(skip_btn)
        
        queue = self.music_cog.queues.get(self.ctx.guild.id, [])
        if queue:
            options = []
            for i, item in enumerate(queue[:25]):
                title = item.get('title', item.get('url')) if isinstance(item, dict) else str(item)
                options.append(discord.SelectOption(label=f"{i+1}. {title[:90]}", value=str(i)))
            
            select = discord.ui.Select(placeholder="Select a song to remove", options=options, custom_id="skip_select_menu")
            
            async def skip_select_callback(interaction: discord.Interaction):
                idx = int(select.values[0])
                current_queue = self.music_cog.queues.get(self.ctx.guild.id, [])
                if 0 <= idx < len(current_queue):
                    removed = current_queue.pop(idx)
                    title = removed.get('title', removed.get('url')) if isinstance(removed, dict) else removed
                    await interaction.response.send_message(f"Removed '{title}' from queue.", ephemeral=False)
                    
                    self.update_select()
                    
                    embed = discord.Embed(title="🎶 Music Queue", color=discord.Color.blue())
                    description = ""
                    for j, item in enumerate(current_queue):
                        item_title = item.get('title', item.get('url')) if isinstance(item, dict) else str(item)
                        description += f"**{j+1}.** {item_title}\n"
                    if not description:
                        description = "The queue is currently empty."
                    embed.description = description
        
                    await interaction.message.edit(embed=embed, view=self)
                else:
                    await interaction.response.send_message("Invalid selection.", ephemeral=True)
            
            select.callback = skip_select_callback
            self.add_item(select)


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
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            self.queues[ctx.guild.id].append({'url': url, 'title': data.get('title', url)})

            await ctx.channel.send(f"Added {data['title']} to the *queue*")
            return
        else:
            await ctx.channel.send("Downloading song, please wait...")
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
            filename = ytdl.prepare_filename(data)
            print(f"Downloaded file to: {filename}")

            ffmpeg_options = {
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

            ctx.voice_client.play(audio_src, after=lambda e: self.play_next_sync(ctx, filename, e))
    
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
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.channel.send('Song paused (°.°) use -> !pause again to resume')
        elif ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.channel.send('Song resumed (* w *) enjoy!')
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
        queue = self.queues.get(ctx.guild.id, [])
        if not queue:
            await ctx.channel.send("The queue is currently empty.")
            return

        embed = discord.Embed(title="🎶 Music Queue", color=discord.Color.blue())
        description = ""
        for i, item in enumerate(queue):
            title = item.get('title', item.get('url')) if isinstance(item, dict) else str(item)
            description += f"**{i+1}.** {title}\n"
        
        embed.description = description
        
        view = QueueView(self, ctx)
        await ctx.channel.send(embed=embed, view=view)

    async def play_next(self, ctx):
        if len(self.queues[ctx.guild.id]) > 0:
            next_item = self.queues[ctx.guild.id].pop(0)
            if isinstance(next_item, dict):
                next_url = next_item['url']
                title = next_item.get('title', 'Unknown Title')
            else:
                next_url = next_item
                title = "Next Song"

            await ctx.channel.send(f"Downloading next song in queue: **{title}**...")
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(next_url, download=True))
            filename = ytdl.prepare_filename(data)

            ffmpeg_options = {
                'options': '-vn'
            }
            
            try:
                audio_src = await discord.FFmpegOpusAudio.from_probe(filename, **ffmpeg_options)
            except Exception as e:
                print(f"Opus probe failed, falling back to PCM: {e}")
                audio_src = discord.FFmpegPCMAudio(filename)

            ctx.voice_client.play(audio_src, after=lambda e: self.play_next_sync(ctx, filename, e))
    
    async def cleanup_file(self, filename):
        await asyncio.sleep(2)
        for i in range(5):
            try:
                if os.path.exists(filename):
                    os.remove(filename)
                    print(f"Deleted local file: {filename}")
                break
            except Exception as e:
                print(f"Failed to delete {filename}, retrying ({i+1}/5)... error: {e}")
                await asyncio.sleep(1)

    def play_next_sync(self, ctx, filename, error):
        if error:
            print(f'Player error {error}')

        asyncio.run_coroutine_threadsafe(self.cleanup_file(filename), self.bot.loop)

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


async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(f'{disc_token}')

asyncio.run(main())
