import os
import asyncio
import yt_dlp
import discord
from discord.ext import commands
import dotenv

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

dotenv.load_dotenv()
disc_token = os.environ.get('DISCORD_TOKEN')

if not disc_token:
    raise RuntimeError("No se encontro el .env")


class Music(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(ctx.author.voice.channel)
        if ctx.author.voice:
            await ctx.author.voice.channel.connect() 

    @commands.command()
    async def play(self, ctx, url):
        await self.ensure_voice(ctx)

        data = ytdl.extract_info(url, download=False)
        filename = data['url']

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        audio_src = discord.FFmpegPCMAudio(filename,before_options=ffmpeg_options['before_options'],options=ffmpeg_options['options'])

        ctx.voice_client.play(audio_src)
        

    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send('You are not connected to a voice channel.')
                raise commands.CommandError('Author not connected to a voice channel.')
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

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
