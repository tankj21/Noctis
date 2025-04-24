import discord
from discord import app_commands
from discord.ext import commands
import time
import yaml
import os

# 言語ファイル読み込み関数
def load_translations(lang_code):
    try:
        with open(f'lang/{lang_code}.yml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except:
        return {}

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Botの応答速度を確認します")
    async def ping(self, interaction: discord.Interaction):
        lang = interaction.locale or "en-US"
        translations = load_translations(lang[:2])  # 例: "ja", "en"

        start = time.perf_counter()
        await interaction.response.defer(thinking=True)
        end = time.perf_counter()

        heartbeat = round(self.bot.latency * 1000)
        response_time = round((end - start) * 1000)

        embed = discord.Embed(
            title=translations.get("ping.title", "🏓 Pong!"),
            color=discord.Color.blurple()
        )
        embed.add_field(
            name=translations.get("ping.websocket_latency", "WebSocket Latency"),
            value=f"{heartbeat}ms"
        )
        embed.add_field(
            name=translations.get("ping.response_time", "Response Time"),
            value=f"{response_time}ms"
        )

        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
