import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

class RoleGroup(app_commands.Group):
    # add コマンド
    @app_commands.command(name="add", description="新しいロールを作成します")
    @app_commands.describe(
        name="ロール名",
        color="ロールの色（例: red, blue, #FF5733）",
        permissions="付与する権限（カンマ区切り: send_messages, manage_channels など）"
    )
    async def add(self, interaction: discord.Interaction, name: str, color: str = "default", permissions: str = ""):
        guild = interaction.guild

        # 色の処理
        if color == "default":
            color = discord.Color.default()
        elif color.startswith("#"):
            color = discord.Color(int(color.lstrip('#'), 16))
        else:
            try:
                color = discord.Color[color.lower()]
            except KeyError:
                await interaction.response.send_message("⚠️ 無効な色コードです。", ephemeral=True)
                return

        # 権限の処理
        perms = discord.Permissions()
        if permissions:
            invalid_permissions = []
            for perm_name in permissions.replace(" ", "").split(","):
                if hasattr(perms, perm_name):
                    setattr(perms, perm_name, True)
                else:
                    invalid_permissions.append(perm_name)

            if invalid_permissions:
                # ページネーションのためのビュー作成
                class PaginationView(View):
                    def __init__(self, permissions, page=0):
                        super().__init__()
                        self.permissions = permissions
                        self.page = page

                    async def send_page(self, interaction):
                        # ページごとに無効な権限を表示
                        start = self.page * 10
                        end = start + 10
                        current_page_permissions = self.permissions[start:end]

                        embed = discord.Embed(
                            title="⚠️ 無効な権限",
                            description=f"以下の権限は無効です: `{', '.join(current_page_permissions)}`",
                            color=discord.Color.red()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)

                    @discord.ui.button(label="次へ", style=discord.ButtonStyle.primary)
                    async def next_page(self, button: Button, interaction: discord.Interaction):
                        if (self.page + 1) * 10 < len(self.permissions):
                            self.page += 1
                            await self.send_page(interaction)
                        else:
                            await interaction.response.send_message("これ以上のページはありません。", ephemeral=True)

                    @discord.ui.button(label="前へ", style=discord.ButtonStyle.primary)
                    async def previous_page(self, button: Button, interaction: discord.Interaction):
                        if self.page > 0:
                            self.page -= 1
                            await self.send_page(interaction)
                        else:
                            await interaction.response.send_message("これ以上のページはありません。", ephemeral=True)

                # 最初のページを表示
                pagination_view = PaginationView(invalid_permissions)
                await pagination_view.send_page(interaction)

        # ロール作成処理
        role = await guild.create_role(name=name, color=color, permissions=perms)
        
        await interaction.response.send_message(f"✅ ロール `{role.name}` が作成されました！", ephemeral=True)


    # delete コマンド
    @app_commands.command(name="delete", description="既存のロールを削除します")
    @app_commands.describe(name="削除するロール名")
    async def delete(self, interaction: discord.Interaction, name: str):
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=name)
        if role:
            await role.delete()
            await interaction.response.send_message(f"✅ ロール `{name}` が削除されました！", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ ロール `{name}` が見つかりませんでした。", ephemeral=True)

    # edit コマンド
    @app_commands.command(name="edit", description="既存のロールを編集します")
    @app_commands.describe(
        name="編集するロール名",
        new_name="新しいロール名",
        color="新しいロールの色（例: red, blue, #FF5733）",
        permissions="新しい権限（カンマ区切り: send_messages, manage_channels など）"
    )
    async def edit(self, interaction: discord.Interaction, name: str, new_name: str = None, color: str = None, permissions: str = None):
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=name)
        
        if role:
            # 名前の変更
            if new_name:
                await role.edit(name=new_name)
            
            # 色の変更
            if color:
                if color.startswith("#"):
                    color = discord.Color(int(color.lstrip('#'), 16))
                else:
                    try:
                        color = discord.Color[color.lower()]
                    except KeyError:
                        await interaction.response.send_message("⚠️ 無効な色コードです。", ephemeral=True)
                        return
                await role.edit(color=color)
            
            # 権限の変更
            if permissions:
                perms = discord.Permissions()
                invalid_permissions = []
                for perm_name in permissions.replace(" ", "").split(","):
                    if hasattr(perms, perm_name):
                        setattr(perms, perm_name, True)
                    else:
                        invalid_permissions.append(perm_name)

                if invalid_permissions:
                    class PaginationView(View):
                        def __init__(self, permissions, page=0):
                            super().__init__()
                            self.permissions = permissions
                            self.page = page

                        async def send_page(self, interaction):
                            start = self.page * 10
                            end = start + 10
                            current_page_permissions = self.permissions[start:end]

                            embed = discord.Embed(
                                title="⚠️ 無効な権限",
                                description=f"以下の権限は無効です: `{', '.join(current_page_permissions)}`",
                                color=discord.Color.red()
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)

                        @discord.ui.button(label="次へ", style=discord.ButtonStyle.primary)
                        async def next_page(self, button: Button, interaction: discord.Interaction):
                            if (self.page + 1) * 10 < len(self.permissions):
                                self.page += 1
                                await self.send_page(interaction)
                            else:
                                await interaction.response.send_message("これ以上のページはありません。", ephemeral=True)

                        @discord.ui.button(label="前へ", style=discord.ButtonStyle.primary)
                        async def previous_page(self, button: Button, interaction: discord.Interaction):
                            if self.page > 0:
                                self.page -= 1
                                await self.send_page(interaction)
                            else:
                                await interaction.response.send_message("これ以上のページはありません。", ephemeral=True)

                    pagination_view = PaginationView(invalid_permissions)
                    await pagination_view.send_page(interaction)

                await role.edit(permissions=perms)

            await interaction.response.send_message(f"✅ ロール `{role.name}` が編集されました！", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ ロール `{name}` が見つかりませんでした。", ephemeral=True)

class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_command(RoleGroup())

async def setup(bot):
    await bot.add_cog(RoleCog(bot))