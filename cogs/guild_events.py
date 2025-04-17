import discord
from discord.ext import commands
import yaml
import os

LANG_FILE_PATH = "data/guild_settings.yml"

def load_guild_settings():
    if not os.path.exists(LANG_FILE_PATH):
        return {}
    with open(LANG_FILE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_guild_settings(data):
    with open(LANG_FILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)

class GuildEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        settings = load_guild_settings()
        gid = str(guild.id)
        if gid not in settings:
            settings[gid] = "en"
            save_guild_settings(settings)
            print(f"✅ Joined: {guild.name} | 言語を en に設定")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        settings = load_guild_settings()
        gid = str(guild.id)
        if gid in settings:
            del settings[gid]
            save_guild_settings(settings)
            print(f"❌ Removed: {guild.name} | 設定削除")

async def setup(bot):
    await bot.add_cog(GuildEvents(bot))
