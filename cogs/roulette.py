import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
from datetime import datetime
import logging

class RouletteBetTypeSelect(discord.ui.Select):
    def __init__(self, view_ref):
        options = [
            discord.SelectOption(label="赤・黒 (2倍)", value="red_black", description="赤または黒の数字に賭けます", emoji="🔴"),
            discord.SelectOption(label="奇数・偶数 (2倍)", value="even_odd", description="奇数または偶数の数字に賭けます", emoji="🔢"),
            discord.SelectOption(label="ハイ・ロー (2倍)", value="high_low", description="前半(1-18)または後半(19-36)に賭けます", emoji="📈"),
            discord.SelectOption(label="ダズン (3倍)", value="dozen", description="1-12, 13-24, 25-36の12点グループに賭けます", emoji="📦"),
            discord.SelectOption(label="カラム (3倍)", value="column", description="1st, 2nd, 3rdのカラム(縦列)に賭けます", emoji="📊"),
            discord.SelectOption(label="ストレートアップ (36倍)", value="number", description="特定の数字(0-36)に1点賭けします", emoji="🎯"),
        ]
        super().__init__(placeholder="賭け方の種類を選択してください", min_values=1, max_values=1, options=options)
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        bet_type = self.values[0]
        await self.view_ref.show_target_options(interaction, bet_type)

class RouletteTargetButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, bet_type, target_val, view_ref):
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.bet_type = bet_type
        self.target_val = target_val
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        if self.custom_id == "input_number":
            modal = RouletteNumberModal(self.view_ref)
            await interaction.response.send_modal(modal)
        else:
            await self.view_ref.spin_wheel(interaction, self.bet_type, self.target_val)

class RouletteBackButton(discord.ui.Button):
    def __init__(self, style, label, view_ref):
        super().__init__(style=style, label=label, row=1)
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.show_bet_type_select(interaction)

class RouletteNumberModal(discord.ui.Modal, title="ストレートアップ（数字指定）"):
    number_input = discord.ui.TextInput(
        label="賭ける数字を入力してください (0 - 36)",
        placeholder="例: 7",
        min_length=1,
        max_length=2,
        required=True
    )
    
    def __init__(self, bet_view):
        super().__init__()
        self.bet_view = bet_view
        
    async def on_submit(self, interaction: discord.Interaction):
        val_str = self.number_input.value.strip()
        if not val_str.isdigit():
            await interaction.response.send_message("半角数字で 0 から 36 の数値を入力してください。", ephemeral=True)
            return
            
        val = int(val_str)
        if val < 0 or val > 36:
            await interaction.response.send_message("0 から 36 の範囲で入力してください。", ephemeral=True)
            return
            
        await self.bet_view.spin_wheel(interaction, "number", str(val))

class RouletteBetView(discord.ui.View):
    def __init__(self, user_id, bet_amount, group):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.group = group

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                'これはあなたのゲームではありません！',
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def show_bet_type_select(self, interaction: discord.Interaction):
        self.clear_items()
        self.add_item(RouletteBetTypeSelect(self))
        
        embed = discord.Embed(
            title="🎰 ルーレット 🎰",
            description=f"ベット額: **{self.bet_amount}** コイン\n\nどの種類の賭けを行いますか？セレクトメニューから選んでください。",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    def get_bet_type_name(self, bet_type):
        mapping = {
            "red_black": "赤・黒賭け (2倍)",
            "even_odd": "奇数・偶数賭け (2倍)",
            "high_low": "ハイ・ロー賭け (2倍)",
            "dozen": "ダズン賭け (3倍)",
            "column": "カラム賭け (3倍)",
            "number": "ストレートアップ (36倍)"
        }
        return mapping.get(bet_type, bet_type)

    def get_target_display(self, bet_type, target):
        if bet_type == "red_black":
            return "🔴 赤" if target == "red" else "⚫ 黒"
        elif bet_type == "even_odd":
            return "奇数" if target == "odd" else "偶数"
        elif bet_type == "high_low":
            return "前半 Low (1-18)" if target == "low" else "後半 High (19-36)"
        elif bet_type == "dozen":
            return f"{target} Dozen"
        elif bet_type == "column":
            return f"{target} Column"
        elif bet_type == "number":
            return f"数字指定 [{target}]"
        return target

    async def show_target_options(self, interaction: discord.Interaction, bet_type: str):
        self.clear_items()
        
        if bet_type == "red_black":
            self.add_item(RouletteTargetButton(label="🔴 赤 (Red)", style=discord.ButtonStyle.danger, custom_id="red", bet_type=bet_type, target_val="red", view_ref=self))
            self.add_item(RouletteTargetButton(label="⚫ 黒 (Black)", style=discord.ButtonStyle.secondary, custom_id="black", bet_type=bet_type, target_val="black", view_ref=self))
        elif bet_type == "even_odd":
            self.add_item(RouletteTargetButton(label="🔵 奇数 (Odd)", style=discord.ButtonStyle.primary, custom_id="odd", bet_type=bet_type, target_val="odd", view_ref=self))
            self.add_item(RouletteTargetButton(label="⚪ 偶数 (Even)", style=discord.ButtonStyle.secondary, custom_id="even", bet_type=bet_type, target_val="even", view_ref=self))
        elif bet_type == "high_low":
            self.add_item(RouletteTargetButton(label="🔽 前半 Low (1-18)", style=discord.ButtonStyle.primary, custom_id="low", bet_type=bet_type, target_val="low", view_ref=self))
            self.add_item(RouletteTargetButton(label="🔼 後半 High (19-36)", style=discord.ButtonStyle.secondary, custom_id="high", bet_type=bet_type, target_val="high", view_ref=self))
        elif bet_type == "dozen":
            self.add_item(RouletteTargetButton(label="📦 1st Dozen (1-12)", style=discord.ButtonStyle.primary, custom_id="1st", bet_type=bet_type, target_val="1st", view_ref=self))
            self.add_item(RouletteTargetButton(label="📦 2nd Dozen (13-24)", style=discord.ButtonStyle.primary, custom_id="2nd", bet_type=bet_type, target_val="2nd", view_ref=self))
            self.add_item(RouletteTargetButton(label="📦 3rd Dozen (25-36)", style=discord.ButtonStyle.primary, custom_id="3rd", bet_type=bet_type, target_val="3rd", view_ref=self))
        elif bet_type == "column":
            self.add_item(RouletteTargetButton(label="📊 1st Column", style=discord.ButtonStyle.primary, custom_id="1st_col", bet_type=bet_type, target_val="1st", view_ref=self))
            self.add_item(RouletteTargetButton(label="📊 2nd Column", style=discord.ButtonStyle.primary, custom_id="2nd_col", bet_type=bet_type, target_val="2nd", view_ref=self))
            self.add_item(RouletteTargetButton(label="📊 3rd Column", style=discord.ButtonStyle.primary, custom_id="3rd_col", bet_type=bet_type, target_val="3rd", view_ref=self))
        elif bet_type == "number":
            self.add_item(RouletteTargetButton(label="🎯 数字を入力する", style=discord.ButtonStyle.success, custom_id="input_number", bet_type=bet_type, target_val="", view_ref=self))
            
        self.add_item(RouletteBackButton(style=discord.ButtonStyle.secondary, label="🔙 戻る", view_ref=self))
        
        embed = discord.Embed(
            title="🎰 ルーレット - ベット対象の選択",
            description=f"賭け方: **{self.get_bet_type_name(bet_type)}**\nベット額: **{self.bet_amount}** コイン\n\n賭ける対象のボタンをクリックしてください。",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def spin_wheel(self, interaction: discord.Interaction, bet_type: str, target: str):
        # コイン残高チェック
        user = self.group.get_user(self.user_id)
        if user['coins'] < self.bet_amount:
            await interaction.response.send_message(
                f"コインが足りません！現在のコイン: {user['coins']:,}",
                ephemeral=True
            )
            return

        # アニメーション中のメッセージ表示 (Viewは非表示にして操作不可に)
        target_display = self.get_target_display(bet_type, target)
        embed = discord.Embed(
            title="🟢 ルーレット回転中...",
            description=f"賭け対象: **{target_display}**\nベット額: **{self.bet_amount}** コイン\n\nボールをホイールに投入しました！ホイールが回転しています...",
            color=discord.Color.light_grey()
        )
        await interaction.response.edit_message(embed=embed, view=None)

        import asyncio
        await asyncio.sleep(1.2)

        # 減速演出
        embed.title = "✨ ボールがポケットに落ちそうです..."
        sim_nums = [random.randint(0, 36) for _ in range(3)]
        sim_displays = []
        for sn in sim_nums:
            color = self.group.get_number_color(sn)
            emoji = "🔴" if color == "red" else "⚫" if color == "black" else "🟢"
            sim_displays.append(f"{emoji} {sn}")
        
        embed.description = f"賭け対象: **{target_display}**\nベット額: **{self.bet_amount}** コイン\n\nボールが跳ねています... " + " ... ".join(sim_displays) + " ..."
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed)

        await asyncio.sleep(1.2)

        # 最終結果
        rolled_num = random.randint(0, 36)
        color = self.group.get_number_color(rolled_num)
        color_emoji = "🔴" if color == "red" else "⚫" if color == "black" else "🟢"
        color_name_ja = "赤" if color == "red" else "黒" if color == "black" else "緑"

        # 出目の属性情報
        properties = []
        properties.append(color_name_ja)
        if rolled_num != 0:
            properties.append("奇数" if rolled_num % 2 != 0 else "偶数")
            properties.append("前半(1-18)" if rolled_num <= 18 else "後半(19-36)")
            
            # Dozen
            if rolled_num <= 12:
                properties.append("1stダズン")
            elif rolled_num <= 24:
                properties.append("2ndダズン")
            else:
                properties.append("3rdダズン")
                
            # Column
            if rolled_num % 3 == 1:
                properties.append("1stカラム")
            elif rolled_num % 3 == 2:
                properties.append("2ndカラム")
            else:
                properties.append("3rdカラム")
        else:
            properties.append("ゼロ")
            
        prop_str = " / ".join(properties)

        # 勝敗判定
        is_win = self.group.check_win(rolled_num, bet_type, target)

        # 倍率決定
        multiplier = 0
        if is_win:
            if bet_type in ["red_black", "even_odd", "high_low"]:
                multiplier = 2
            elif bet_type in ["dozen", "column"]:
                multiplier = 3
            elif bet_type == "number":
                multiplier = 36

        win_amount = self.bet_amount * multiplier
        new_coins = user['coins'] - self.bet_amount + win_amount

        # DB更新
        self.group.update_user(self.user_id, new_coins, is_win, win_amount)

        # 最終結果表示
        result_title = "🎉 勝利！" if is_win else "💔 敗北"
        result_color = discord.Color.green() if is_win else discord.Color.red()
        if color == "green":
            result_color = discord.Color.from_rgb(0, 128, 0)

        embed = discord.Embed(
            title=f"🎰 ルーレット結果: {color_emoji} {rolled_num} ({prop_str})",
            description=f"結果: **{result_title}**\n\n賭け対象: **{target_display}**\nベット額: **{self.bet_amount}** コイン",
            color=result_color,
            timestamp=datetime.now()
        )

        if is_win:
            profit = win_amount - self.bet_amount
            embed.add_field(name="獲得コイン", value=f"🎉 **{win_amount} コイン** (+{profit})", inline=True)
        else:
            embed.add_field(name="獲得コイン", value="0 コイン", inline=True)
            
        embed.add_field(name="現在のコイン", value=f"{new_coins:,} コイン", inline=True)
        embed.set_footer(text=f"{interaction.user.name} のルーレット結果")

        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed)

class RouletteGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="roulette", description="ルーレット関連コマンド")

    def get_number_color(self, num):
        if num == 0:
            return 'green'
        if (1 <= num <= 10) or (19 <= num <= 28):
            return 'red' if num % 2 != 0 else 'black'
        if (11 <= num <= 18) or (29 <= num <= 36):
            return 'black' if num % 2 != 0 else 'red'

    def check_win(self, rolled_num, bet_type, target):
        if rolled_num == 0:
            if bet_type == "number" and target == "0":
                return True
            return False

        if bet_type == "red_black":
            color = self.get_number_color(rolled_num)
            return color == target
        elif bet_type == "even_odd":
            is_even = (rolled_num % 2 == 0)
            if target == "even":
                return is_even
            else:
                return not is_even
        elif bet_type == "high_low":
            is_low = (1 <= rolled_num <= 18)
            if target == "low":
                return is_low
            else:
                return not is_low
        elif bet_type == "dozen":
            if target == "1st":
                return 1 <= rolled_num <= 12
            elif target == "2nd":
                return 13 <= rolled_num <= 24
            elif target == "3rd":
                return 25 <= rolled_num <= 36
        elif bet_type == "column":
            rem = rolled_num % 3
            if target == "1st":
                return rem == 1
            elif target == "2nd":
                return rem == 2
            elif target == "3rd":
                return rem == 0
        elif bet_type == "number":
            return str(rolled_num) == target

        return False

    def get_user(self, user_id):
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, coins, total_wins, total_losses, biggest_win, bankruptcy_count
            FROM users WHERE user_id = ?
        ''', (str(user_id),))
        user = cursor.fetchone()

        if not user:
            cursor.execute(
                'INSERT INTO users (user_id, coins) VALUES (?, 1000)', (str(user_id),)
            )
            conn.commit()
            cursor.execute('''
                SELECT user_id, coins, total_wins, total_losses, biggest_win, bankruptcy_count
                FROM users WHERE user_id = ?
            ''', (str(user_id),))
            user = cursor.fetchone()

        conn.close()
        return {
            'user_id': user[0],
            'coins': user[1],
            'total_wins': user[2],
            'total_losses': user[3],
            'biggest_win': user[4],
            'bankruptcy_count': int(user[5]) if user[5] is not None else 0
        }

    def update_user(self, user_id, coins, is_win, win_amount):
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET coins = ?,
                total_wins = total_wins + ?,
                total_losses = total_losses + ?,
                biggest_win = MAX(biggest_win, ?),
                last_played = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (coins, 1 if is_win else 0, 0 if is_win else 1, win_amount, str(user_id)))
        conn.commit()
        conn.close()

    @app_commands.command(name="play", description="ルーレットゲームをプレイします")
    @app_commands.describe(bet="ベットするコイン数（デフォルト: 10）")
    async def play(self, interaction: discord.Interaction, bet: int = 10):
        if bet < 1:
            await interaction.response.send_message('ベット額は1以上にしてください！', ephemeral=True)
            return
            
        user_id = interaction.user.id
        user = self.get_user(user_id)
        
        if user['coins'] < bet:
            if user['coins'] == 0:
                await interaction.response.send_message(
                    f"💔 コインが0になってしまいました！\n\n`/slot bonus` コマンドで500コインを受け取ることができます。",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"コインが足りません！現在のコイン: {user['coins']:,}",
                    ephemeral=True
                )
            return
            
        # ビューを初期化してセレクトメニューを追加
        view = RouletteBetView(user_id, bet, self)
        view.add_item(RouletteBetTypeSelect(view))
        
        embed = discord.Embed(
            title="🎰 ルーレット 🎰",
            description=f"ベット額: **{bet}** コイン\n\nどの種類の賭けを行いますか？セレクトメニューから選んでください。",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"所持コイン: {user['coins']:,} コイン")
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="rules", description="ルーレットのルールと配当を表示します")
    async def rules(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎰 ルーレット ルール説明",
            description="ディーラーがホイールを回し、投げ入れたボールが0〜36のどの数字に落ちるかを予想するゲームです。",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🔴⚫ 各数字の色について",
            value="`0` は緑（🟢）です。\nそれ以外の数字は赤（🔴）または黒（⚫）に分類されます。\n奇数/偶数、ハイ/ローの判定に `0` は含まれず、出目が `0` の場合はこれらの賭けは全てハズレとなります。",
            inline=False
        )
        embed.add_field(
            name="💰 賭け方と配当倍率",
            value=(
                "**1. 赤・黒 (2倍)**: 出目の色が赤か黒かを予想します。\n"
                "**2. 奇数・偶数 (2倍)**: 出目の数値が奇数か偶数かを予想します。\n"
                "**3. ハイ・ロー (2倍)**: 出目が前半 (1-18) か後半 (19-36) かを予想します。\n"
                "**4. ダズン (3倍)**: 出目が 1-12 (1st), 13-24 (2nd), 25-36 (3rd) のいずれかに属するかを予想します。\n"
                "**5. カラム (3倍)**: 出目の数値を3で割った余り (1st=余り1, 2nd=余り2, 3rd=余り0) に基づく3つの縦列のいずれかを予想します。\n"
                "**6. ストレートアップ (36倍)**: 0〜36の中から特定の1つの数字をピンポイントで予想します。"
            ),
            inline=False
        )
        embed.set_footer(text="所持コインはスロットやブラックジャックと共通です")
        await interaction.response.send_message(embed=embed)

class RouletteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roulette_group = RouletteGroup()

    async def cog_load(self):
        self.bot.tree.add_command(self.roulette_group)
        logging.info(f"RouletteGroup を追加しました (コマンド数: {len(self.roulette_group.commands)})")

    async def cog_unload(self):
        self.bot.tree.remove_command("roulette")
        logging.info("RouletteGroup を削除しました")

async def setup(bot):
    await bot.add_cog(RouletteCog(bot))
    logging.info("RouletteCog をセットアップしました")
