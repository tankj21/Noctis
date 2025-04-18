import discord
from discord import app_commands
from discord.ext import commands
import yaml
import os

LANG_FILE_PATH = "data/lang_guild_settings.yml"

def load_guild_settings():
    if not os.path.exists(LANG_FILE_PATH):
        return {}
    with open(LANG_FILE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
    
def save_guild_settings(data):
    with open(LANG_FILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)

class Language(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="language", description="set guild language")
    @app_commands.guilds(discord.Object(id=831385920145588244))
    @app_commands.describe(language="Choose language ex: ja , en")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_language(self, interaction: discord.Interaction, language: str):
        supported_languages = ["ja", "en"]
        if language not in supported_languages:
            await interaction.response.send_message(f"対応している言語は {', '.join(supported_languages)} のみです。", ephemeral=True)
            return

        settings = load_guild_settings()
        settings[str(interaction.guild.id)] = language
        save_guild_settings(settings)

        await interaction.response.send_message(f"✅ 言語が `{language}` に設定されました。")

async def setup(bot):
    await bot.add_cog(Language(bot))