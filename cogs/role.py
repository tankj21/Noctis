import discord
from discord.ext import commands
from discord import app_commands

class RoleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="role", description="ロールの管理を行います")

    @app_commands.command(name="add", description="新しいロールを作成します")
    @app_commands.describe(
        name="ロール名",
        color="ロールの色（例: red, blue, #FF5733）",
        permissions="付与する権限（カンマ区切り: send_messages, manage_channels など）"
    )
    async def add(self, interaction: discord.Interaction, name: str, color: str = "default", permissions: str = ""):
        guild = interaction.guild

        # 色の変換
        if color.startswith("#"):  # カラーコードが渡された場合
            try:
                role_color = discord.Color(int(color[1:], 16))  # #を取り除いて16進数に変換
            except ValueError:
                await interaction.response.send_message(f"⚠️ 無効なカラーコード: `{color}`", ephemeral=True)
                return
        else:
            # 名前付きの色
            color_map = {
                "red": discord.Color.red(),
                "blue": discord.Color.blue(),
                "green": discord.Color.green(),
                "yellow": discord.Color.gold(),
                "purple": discord.Color.purple(),
                "default": discord.Color.default()
            }
            role_color = color_map.get(color.lower(), discord.Color.default())

        # 権限の変換
        perms = discord.Permissions()
        if permissions:
            for perm_name in permissions.replace(" ", "").split(","):
                if hasattr(perms, perm_name):
                    setattr(perms, perm_name, True)
                else:
                    await interaction.response.send_message(f"⚠️ 無効な権限: `{perm_name}`", ephemeral=True)
                    return

        # ロール作成
        try:
            role = await guild.create_role(name=name, colour=role_color, permissions=perms)
            await interaction.response.send_message(f"✅ ロール `{role.name}` を作成しました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Botにロール作成の権限がありません。", ephemeral=True)

    @app_commands.command(name="delete", description="既存のロールを削除します")
    @app_commands.describe(role="削除するロール")
    async def delete(self, interaction: discord.Interaction, role: discord.Role):
        try:
            await role.delete()
            await interaction.response.send_message(f"🗑️ ロール `{role.name}` を削除しました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Botにロール削除の権限がありません。", ephemeral=True)

    @app_commands.command(name="edit", description="既存のロールを編集します")
    @app_commands.describe(
        role="編集対象のロール",
        name="新しいロール名（任意）",
        color="新しいロールの色（任意、例: #FF5733）",
        permissions="更新する権限（カンマ区切り・空白でリセット）"
    )
    async def edit(self, interaction: discord.Interaction, role: discord.Role, name: str = None, color: str = None, permissions: str = None):
        updates = {}
        if name:
            updates["name"] = name

        if color:
            if color.startswith("#"):  # カラーコードが渡された場合
                try:
                    updates["colour"] = discord.Color(int(color[1:], 16))  # #を取り除いて16進数に変換
                except ValueError:
                    await interaction.response.send_message(f"⚠️ 無効なカラーコード: `{color}`", ephemeral=True)
                    return
            else:
                color_map = {
                    "red": discord.Color.red(),
                    "blue": discord.Color.blue(),
                    "green": discord.Color.green(),
                    "yellow": discord.Color.gold(),
                    "purple": discord.Color.purple(),
                    "default": discord.Color.default()
                }
                updates["colour"] = color_map.get(color.lower(), discord.Color.default())

        if permissions is not None:
            perms = discord.Permissions()
            if permissions.strip() != "":
                for perm_name in permissions.replace(" ", "").split(","):
                    if hasattr(perms, perm_name):
                        setattr(perms, perm_name, True)
                    else:
                        await interaction.response.send_message(f"⚠️ 無効な権限: `{perm_name}`", ephemeral=True)
                        return
            updates["permissions"] = perms

        try:
            await role.edit(**updates)
            await interaction.response.send_message(f"✏️ ロール `{role.name}` を更新しました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Botにロール編集の権限がありません。", ephemeral=True)


class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(RoleGroup())

async def setup(bot):
    await bot.add_cog(RoleCog(bot))
