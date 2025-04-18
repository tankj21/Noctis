import discord
from discord import app_commands
from discord.ext import commands
import yaml
import os

LANG_FILE_PATH = "data/guild_settings.yml"
LOCALE_FOLDER = "lang"

# --- 多言語設定 ---
def get_guild_language(guild_id: int) -> str:
    if not os.path.exists(LANG_FILE_PATH):
        return "en"
    with open(LANG_FILE_PATH, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}
    return settings.get(str(guild_id), "en")

def get_translation(guild_id: int):
    lang = get_guild_language(guild_id)
    path = os.path.join(LOCALE_FOLDER, f"{lang}.yml")
    if not os.path.exists(path):
        path = os.path.join(LOCALE_FOLDER, "en.yml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class Info(commands.GroupCog, name="info"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="server", description="サーバーの情報を表示します")
    async def server(self, interaction: discord.Interaction):
        translation = get_translation(interaction.guild.id)
        guild = interaction.guild

        embed = discord.Embed(
            title=translation["info"]["server_title"],
            description=translation["info"]["server_description"],
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.add_field(name=translation["info"]["guild_name"], value=guild.name, inline=True)
        embed.add_field(name=translation["info"]["guild_id"], value=str(guild.id), inline=True)
        embed.add_field(name=translation["info"]["member_count"], value=str(guild.member_count), inline=True)
        embed.add_field(name=translation["info"]["owner"], value=str(guild.owner), inline=True)
        embed.add_field(name=translation["info"]["created_at"], value=guild.created_at.strftime("%Y/%m/%d %H:%M"), inline=True)
        embed.add_field(name=translation["info"]["channel_count"], value=str(len(guild.channels)), inline=True)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="user", description="指定したユーザーの情報を表示します")
    @app_commands.describe(user="対象のユーザー")
    async def user(self, interaction: discord.Interaction, user: discord.User):
        translation = get_translation(interaction.guild.id)
        member = interaction.guild.get_member(user.id)

        embed = discord.Embed(
            title=translation["info"]["user_title"],
            description=translation["info"]["user_description"],
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name=translation["info"]["user_name"], value=user.name, inline=True)
        embed.add_field(name=translation["info"]["user_id"], value=str(user.id), inline=True)
        embed.add_field(name=translation["info"]["bot_flag"], value=str(user.bot), inline=True)
        embed.add_field(name=translation["info"]["created_at"], value=user.created_at.strftime("%Y/%m/%d %H:%M"), inline=True)

        if member:
            if member.joined_at:
                embed.add_field(name=translation["info"]["joined_at"], value=member.joined_at.strftime("%Y/%m/%d %H:%M"), inline=True)
            embed.add_field(name=translation["info"]["status"], value=str(member.status).title(), inline=True)

        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

# --- Cog 登録 ---
async def setup(bot):
    await bot.add_cog(Info(bot))
