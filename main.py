import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.members = True  # メンバー情報取得に必要

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # スラッシュコマンドの同期
        await self.tree.sync()

client = MyClient()

@client.tree.command(name="info", description="サーバー情報またはユーザー情報を取得します")
@app_commands.describe(target="server または DiscordのユーザーID")
async def info(interaction: discord.Interaction, target: str):
    # "server" の場合はギルド情報を返す
    if target.lower() == "server":
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("このコマンドはサーバー内でのみ使用できます。", ephemeral=True)
            return
        embed = discord.Embed(title="サーバー情報", color=discord.Color.blue())
        embed.add_field(name="サーバー名", value=guild.name, inline=False)
        embed.add_field(name="サーバーID", value=guild.id, inline=False)
        embed.add_field(name="メンバー数", value=guild.member_count, inline=False)
        await interaction.response.send_message(embed=embed)

    else:
        try:
            user_id = int(target)
            user = interaction.guild.get_member(user_id)
            if user is None:
                await interaction.response.send_message("指定されたIDのユーザーはこのサーバーに存在しません。", ephemeral=True)
                return
            embed = discord.Embed(title="ユーザー情報", color=discord.Color.green())
            embed.add_field(name="名前", value=f"{user.name}#{user.discriminator}", inline=False)
            embed.add_field(name="ユーザーID", value=user.id, inline=False)
            embed.add_field(name="ステータス", value=str(user.status), inline=False)
            await interaction.response.send_message(embed=embed)
        except ValueError:
            await interaction.response.send_message("引数には `server` または ユーザーのIDを指定してください。", ephemeral=True)

# Botを起動
TOKEN = "ODMxMzg0ODY5MjAwMDY4NjI5.GTJJIN.lWV0OMMIkYAiaCwyFVSp7wjrbFaGC7yOxEcNoI"
client.run(TOKEN)
