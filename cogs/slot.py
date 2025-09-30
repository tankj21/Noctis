import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
from datetime import datetime
import logging

class SlotGroup(app_commands.Group):
    
    SYMBOLS = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']
    SYMBOL_WEIGHTS = [30, 25, 20, 15, 7, 3]
    JACKPOT_CONTRIBUTION = 0.05  # ベット額の5%がジャックポットに積み立て

    def __init__(self):
        super().__init__(name="slot", description="スロットマシン関連コマンド")
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                coins INTEGER DEFAULT 1000,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                biggest_win INTEGER DEFAULT 0,
                bankruptcy_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ジャックポット用テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jackpot (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                amount INTEGER DEFAULT 0,
                last_winner TEXT,
                last_win_amount INTEGER DEFAULT 0,
                last_win_date TIMESTAMP
            )
        ''')
        
        # 初期ジャックポット額を設定
        cursor.execute('INSERT OR IGNORE INTO jackpot (id, amount) VALUES (1, 10000)')
        
        conn.commit()
        conn.close()

    def get_jackpot(self):
        """現在のジャックポット額を取得"""
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT amount FROM jackpot WHERE id = 1')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def add_to_jackpot(self, amount):
        """ジャックポットに積み立て"""
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE jackpot SET amount = amount + ? WHERE id = 1', (amount,))
        conn.commit()
        conn.close()

    def win_jackpot(self, user_id, username):
        """ジャックポット獲得処理"""
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        
        # 現在のジャックポット額を取得
        cursor.execute('SELECT amount FROM jackpot WHERE id = 1')
        jackpot_amount = cursor.fetchone()[0]
        
        # ジャックポット情報を更新（最低額にリセット）
        cursor.execute('''
            UPDATE jackpot 
            SET amount = 10000,
                last_winner = ?,
                last_win_amount = ?,
                last_win_date = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (username, jackpot_amount))
        
        conn.commit()
        conn.close()
        return jackpot_amount

    def get_last_jackpot_winner(self):
        """最後のジャックポット勝者情報を取得"""
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT last_winner, last_win_amount, last_win_date 
            FROM jackpot 
            WHERE id = 1 AND last_winner IS NOT NULL
        ''')
        result = cursor.fetchone()
        conn.close()
        return result

    def get_user(self, user_id):
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (str(user_id),))
        user = cursor.fetchone()

        if not user:
            cursor.execute(
                'INSERT INTO users (user_id, coins) VALUES (?, 1000)', (str(user_id),)
            )
            conn.commit()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (str(user_id),))
            user = cursor.fetchone()

        conn.close()
        return {
            'user_id': user[0],
            'coins': user[1],
            'total_wins': user[2],
            'total_losses': user[3],
            'biggest_win': user[4],
            'bankruptcy_count': user[5] if len(user) > 5 else 0
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

    def get_ranking(self, limit=10):
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, coins, total_wins, total_losses 
            FROM users 
            ORDER BY coins DESC 
            LIMIT ?
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_bankruptcy_ranking(self, limit=10):
        """破産回数ランキングを取得"""
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, bankruptcy_count, coins
            FROM users 
            WHERE bankruptcy_count > 0
            ORDER BY bankruptcy_count DESC 
            LIMIT ?
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def weighted_random(self):
        return random.choices(self.SYMBOLS, weights=self.SYMBOL_WEIGHTS, k=1)[0]

    def spin_slot(self):
        return [self.weighted_random(), self.weighted_random(), self.weighted_random()]

    def calculate_win(self, result, bet):
        s1, s2, s3 = result
        
        # 3つ揃い
        if s1 == s2 == s3:
            if s1 == '7️⃣':
                return 'JACKPOT'  # ジャックポット当選
            elif s1 == '💎':
                return bet * 20
            else:
                return bet * 10
        
        # 2つ揃い
        if s1 == s2 or s2 == s3 or s1 == s3:
            return bet * 2
        
        return 0

    @app_commands.command(name="play", description="スロットを回します")
    @app_commands.describe(bet="ベットするコイン数（デフォルト: 10）")
    async def slot(self, interaction: discord.Interaction, bet: int = 10):
        """スロットを回す"""
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
                    f"コインが足りません！現在のコイン: {user['coins']}",
                    ephemeral=True
                )
            return
        
        # スロットを回す
        result = self.spin_slot()
        win = self.calculate_win(result, bet)
        
        # 負けた時だけジャックポットに積み立て
        if win == 0:
            jackpot_contribution = int(bet * self.JACKPOT_CONTRIBUTION)
            self.add_to_jackpot(jackpot_contribution)
        
        # ジャックポット判定
        is_jackpot = (win == 'JACKPOT')
        if is_jackpot:
            win = self.win_jackpot(user_id, interaction.user.name)
        
        new_coins = user['coins'] - bet + win
        
        # データベース更新
        self.update_user(user_id, new_coins, win > 0, win)
        
        # 結果を表示
        if is_jackpot:
            embed = discord.Embed(
                title='🎰💰 JACKPOT!!! 💰🎰',
                description=f"**[ {' | '.join(result)} ]**\n\n🎉🎉🎉 ジャックポット当選！！ 🎉🎉🎉",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            embed.add_field(name='ベット額', value=f'{bet} コイン', inline=True)
            embed.add_field(
                name='🏆 ジャックポット獲得',
                value=f'**{win:,} コイン**',
                inline=True
            )
            embed.add_field(name='現在のコイン', value=f'{new_coins:,} コイン', inline=True)
            embed.set_footer(text=f'🎊 おめでとうございます {interaction.user.name} さん！ 🎊')
        else:
            embed = discord.Embed(
                title='🎰 スロットマシン 🎰',
                description=f"**[ {' | '.join(result)} ]**",
                color=discord.Color.green() if win > 0 else discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name='ベット額', value=f'{bet} コイン', inline=True)
            embed.add_field(
                name='結果',
                value=f'🎉 {win} コイン獲得！' if win > 0 else '💔 ハズレ',
                inline=True
            )
            embed.add_field(name='現在のコイン', value=f'{new_coins} コイン', inline=True)
            embed.set_footer(text=f'{interaction.user.name} のスロット結果')
        
        # 現在のジャックポット額を表示
        current_jackpot = self.get_jackpot()
        embed.add_field(
            name='💎 現在のジャックポット',
            value=f'{current_jackpot:,} コイン',
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="jackpot", description="現在のジャックポット情報を表示します")
    async def jackpot_info(self, interaction: discord.Interaction):
        """ジャックポット情報を表示"""
        current_jackpot = self.get_jackpot()
        last_winner_info = self.get_last_jackpot_winner()
        
        embed = discord.Embed(
            title='💎 ジャックポット情報',
            description=f'7️⃣ 7️⃣ 7️⃣ を揃えてジャックポットを獲得しよう！',
            color=discord.Color.gold()
        )
        embed.add_field(
            name='現在のジャックポット額',
            value=f'**{current_jackpot:,} コイン**',
            inline=False
        )
        
        if last_winner_info:
            winner_name, win_amount, win_date = last_winner_info
            embed.add_field(
                name='🏆 最後の当選者',
                value=f'{winner_name}',
                inline=True
            )
            embed.add_field(
                name='獲得額',
                value=f'{win_amount:,} コイン',
                inline=True
            )
            embed.add_field(
                name='当選日時',
                value=win_date,
                inline=True
            )
        
        embed.add_field(
            name='📝 積み立てについて',
            value=f'負けた時のベット額の{int(self.JACKPOT_CONTRIBUTION*100)}%がジャックポットに積み立てられます',
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coins", description="所持コインと統計を確認します")
    async def coins(self, interaction: discord.Interaction):
        """所持コインと統計を確認"""
        user_id = interaction.user.id
        user = self.get_user(user_id)
        
        total_plays = user['total_wins'] + user['total_losses']
        win_rate = (user['total_wins'] / total_plays * 100) if total_plays > 0 else 0
        
        embed = discord.Embed(
            title='💰 あなたの統計',
            color=discord.Color.blue()
        )
        embed.add_field(name='所持コイン', value=f"{user['coins']:,} 🪙", inline=True)
        embed.add_field(name='勝利回数', value=f"{user['total_wins']}", inline=True)
        embed.add_field(name='敗北回数', value=f"{user['total_losses']}", inline=True)
        embed.add_field(name='最大勝利額', value=f"{user['biggest_win']:,} コイン", inline=True)
        embed.add_field(name='勝率', value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name='総プレイ回数', value=f"{total_plays}", inline=True)
        embed.add_field(name='💔 破産回数', value=f"{user['bankruptcy_count']}回", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ranking", description="コインランキングを表示します")
    async def ranking(self, interaction: discord.Interaction):
        """コインランキングを表示"""
        top_players = self.get_ranking(10)
        
        if not top_players:
            await interaction.response.send_message('まだプレイヤーがいません', ephemeral=True)
            return
        
        ranking_text = ''
        for i, (user_id, coins, wins, losses) in enumerate(top_players, 1):
            try:
                user = await interaction.client.fetch_user(int(user_id))
                username = user.name
            except:
                username = 'Unknown User'
            
            medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
            ranking_text += f'{medal} **{username}** - {coins:,} コイン\n'
        
        embed = discord.Embed(
            title='🏆 コイン ランキング TOP 10',
            description=ranking_text,
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="bankruptcy", description="破産回数ランキングを表示します")
    async def bankruptcy_ranking(self, interaction: discord.Interaction):
        """破産回数ランキングを表示"""
        top_bankrupts = self.get_bankruptcy_ranking(10)
        
        if not top_bankrupts:
            await interaction.response.send_message('まだ破産したプレイヤーがいません', ephemeral=True)
            return
        
        ranking_text = ''
        for i, (user_id, bankruptcy_count, coins) in enumerate(top_bankrupts, 1):
            try:
                user = await interaction.client.fetch_user(int(user_id))
                username = user.name
            except:
                username = 'Unknown User'
            
            medal = '💀' if i == 1 else '👻' if i == 2 else '☠️' if i == 3 else f'{i}.'
            ranking_text += f'{medal} **{username}** - {bankruptcy_count}回破産 (現在: {coins:,}コイン)\n'
        
        embed = discord.Embed(
            title='💔 破産回数ランキング TOP 10',
            description=ranking_text + '\n\n*破産は名誉の勲章！挑戦し続けた証です！*',
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="スロットボットの使い方を表示します")
    async def help_command(self, interaction: discord.Interaction):
        """ヘルプを表示"""
        embed = discord.Embed(
            title='🎰 スロットボット ヘルプ',
            description='スロットマシンで遊ぼう！',
            color=discord.Color.blue()
        )
        embed.add_field(
            name='/slot play [ベット額]',
            value='スロットを回します（デフォルト: 10コイン）',
            inline=False
        )
        embed.add_field(
            name='/slot jackpot',
            value='現在のジャックポット情報を表示します',
            inline=False
        )
        embed.add_field(
            name='/slot coins',
            value='所持コインと統計を確認します',
            inline=False
        )
        embed.add_field(
            name='/slot ranking',
            value='コインランキングを表示します',
            inline=False
        )
        embed.add_field(
            name='/slot bankruptcy',
            value='破産回数ランキングを表示します',
            inline=False
        )
        embed.add_field(
            name='/slot bonus',
            value='コインが0の時に500コインを受け取ります',
            inline=False
        )
        embed.add_field(
            name='/slot help',
            value='このヘルプを表示します',
            inline=False
        )
        embed.add_field(
            name='💰 配当表',
            value='```\n7️⃣ 7️⃣ 7️⃣  → 💎 JACKPOT 💎 (全額獲得!)\n💎 💎 💎  → 20倍 (ダイヤモンド!)\nその他3つ揃い → 10倍\n2つ揃い     → 2倍\n```',
            inline=False
        )
        embed.add_field(
            name='🎰 ジャックポットについて',
            value=f'負けた時のベット額の{int(self.JACKPOT_CONTRIBUTION*100)}%がジャックポットに積み立てられ、7️⃣が3つ揃うと全額獲得できます！',
            inline=False
        )
        embed.set_footer(text='初期コイン: 1000 | 初期ジャックポット: 10,000')
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bonus", description="コインが0の時に500コインを受け取ります")
    async def bonus(self, interaction: discord.Interaction):
        """ボーナスコインを受け取る"""
        user_id = interaction.user.id
        user = self.get_user(user_id)
        
        if user['coins'] > 0:
            await interaction.response.send_message(
                f'まだコインが残っています！（現在: {user["coins"]:,} コイン）\n\nボーナスはコインが0の時のみ受け取れます。',
                ephemeral=True
            )
            return
        
        # 500コインを付与し、破産回数をカウント
        bonus_amount = 500
        conn = sqlite3.connect('slot_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET coins = ?, 
                bankruptcy_count = bankruptcy_count + 1 
            WHERE user_id = ?
        ''', (bonus_amount, str(user_id)))
        conn.commit()
        conn.close()
        
        new_bankruptcy_count = user['bankruptcy_count'] + 1
        
        embed = discord.Embed(
            title='🎁 ボーナス獲得！',
            description=f'**{bonus_amount} コイン**を受け取りました！',
            color=discord.Color.green()
        )
        embed.add_field(
            name='💰 現在のコイン',
            value=f'{bonus_amount} コイン',
            inline=True
        )
        embed.add_field(
            name='💔 破産回数',
            value=f'{new_bankruptcy_count}回目',
            inline=True
        )
        embed.set_footer(text='諦めずに挑戦し続けよう！')
        
        await interaction.response.send_message(embed=embed)

class SlotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slot_group = SlotGroup()

    async def cog_load(self):
        # Cogがロードされる時にGroupを追加
        self.bot.tree.add_command(self.slot_group)
        logging.info(f"SlotGroup を追加しました (コマンド数: {len(self.slot_group.commands)})")
        for cmd in self.slot_group.commands:
            logging.info(f"  - {cmd.name}")

    async def cog_unload(self):
        # Cogがアンロードされる時にGroupを削除
        self.bot.tree.remove_command("slot")
        logging.info("SlotGroup を削除しました")

async def setup(bot):
    await bot.add_cog(SlotCog(bot))
    logging.info("SlotCog をセットアップしました")

# テスト用（後で削除）
if __name__ == "__main__":
    import asyncio
    group = SlotGroup()
    print(f"SlotGroup commands: {[cmd.name for cmd in group.commands]}")