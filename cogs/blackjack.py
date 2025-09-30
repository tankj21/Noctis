import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
from datetime import datetime
import logging

class BlackjackGame:
    """ブラックジャックのゲーム状態を管理するクラス"""
    
    SUITS = ['♠️', '♥️', '♦️', '♣️']
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    def __init__(self, bet):
        self.bet = bet
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.is_finished = False
        self.result = None
        
    def create_deck(self):
        """デッキを作成してシャッフル"""
        deck = []
        for suit in self.SUITS:
            for rank in self.RANKS:
                deck.append(f"{rank}{suit}")
        random.shuffle(deck)
        return deck
    
    def deal_card(self):
        """カードを1枚引く"""
        return self.deck.pop()
    
    def calculate_hand_value(self, hand):
        """手札の合計値を計算（Aの処理含む）"""
        value = 0
        aces = 0
        
        for card in hand:
            # 絵文字は2文字分なので、最後の2文字を削除してランクを取得
            rank = card[:-2]
            
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11
            else:
                value += int(rank)
        
        # Aの値を調整（21を超える場合は1として扱う）
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def initial_deal(self):
        """初期カードを配る"""
        self.player_hand = [self.deal_card(), self.deal_card()]
        self.dealer_hand = [self.deal_card(), self.deal_card()]
        
        # プレイヤーがブラックジャックかチェック
        if self.calculate_hand_value(self.player_hand) == 21:
            self.is_finished = True
            if self.calculate_hand_value(self.dealer_hand) == 21:
                self.result = 'push'
            else:
                self.result = 'blackjack'
    
    def player_hit(self):
        """プレイヤーがヒット"""
        self.player_hand.append(self.deal_card())
        player_value = self.calculate_hand_value(self.player_hand)
        
        if player_value > 21:
            self.is_finished = True
            self.result = 'bust'
            return True
        elif player_value == 21:
            return True
        return False
    
    def dealer_play(self):
        """ディーラーのターン（17以上になるまで引く）"""
        while self.calculate_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deal_card())
        
        player_value = self.calculate_hand_value(self.player_hand)
        dealer_value = self.calculate_hand_value(self.dealer_hand)
        
        if dealer_value > 21:
            self.result = 'win'
        elif player_value > dealer_value:
            self.result = 'win'
        elif player_value < dealer_value:
            self.result = 'lose'
        else:
            self.result = 'push'
        
        self.is_finished = True
    
    def get_hand_display(self, hand, hide_first=False):
        """手札を表示用文字列に変換"""
        if hide_first:
            return f"🂠 {hand[1]}"
        return " ".join(hand)
    
    def calculate_winnings(self):
        """勝敗に応じた獲得コインを計算"""
        if self.result == 'blackjack':
            return int(self.bet * 2.5)  # ブラックジャックは2.5倍
        elif self.result == 'win':
            return self.bet * 2
        elif self.result == 'push':
            return self.bet
        else:
            return 0

class BlackjackButtons(discord.ui.View):
    """ブラックジャック用のボタン"""
    
    def __init__(self, user_id, blackjack_group):
        super().__init__(timeout=300)  # 5分でタイムアウト
        self.user_id = user_id
        self.blackjack_group = blackjack_group
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ボタンを押したのがゲームのプレイヤー本人かチェック"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                'これはあなたのゲームではありません！',
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label='🎴 Hit', style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Hitボタン"""
        await self.blackjack_group.process_hit(interaction, self.user_id)
    
    @discord.ui.button(label='✋ Stand', style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Standボタン"""
        await self.blackjack_group.process_stand(interaction, self.user_id)
    
    async def on_timeout(self):
        """タイムアウト時の処理"""
        # ボタンを無効化
        for item in self.children:
            item.disabled = True

class BlackjackGroup(app_commands.Group):
    
    def __init__(self):
        super().__init__(name="bj", description="ブラックジャック関連コマンド")
        self.active_games = {}  # user_id: BlackjackGame
    
    def get_user(self, user_id):
        """ユーザー情報を取得（スロットと同じDB）"""
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
            'bankruptcy_count': int(user[5]) if len(user) > 5 and user[5] is not None else 0
        }
    
    def update_user(self, user_id, coins, is_win, win_amount):
        """ユーザー情報を更新"""
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
    
    def create_game_embed(self, game, user_name, show_dealer=False):
        """ゲーム状態の埋め込みメッセージを作成"""
        player_value = game.calculate_hand_value(game.player_hand)
        
        if show_dealer or game.is_finished:
            dealer_display = game.get_hand_display(game.dealer_hand)
            dealer_value = game.calculate_hand_value(game.dealer_hand)
            dealer_info = f"{dealer_display} (合計: {dealer_value})"
        else:
            dealer_display = game.get_hand_display(game.dealer_hand, hide_first=True)
            dealer_info = f"{dealer_display} (合計: ?)"
        
        if game.is_finished:
            if game.result == 'blackjack':
                title = '🎉 ブラックジャック！'
                color = discord.Color.gold()
            elif game.result == 'win':
                title = '✨ 勝利！'
                color = discord.Color.green()
            elif game.result == 'lose':
                title = '💔 敗北'
                color = discord.Color.red()
            elif game.result == 'bust':
                title = '💥 バスト！'
                color = discord.Color.red()
            else:  # push
                title = '🤝 引き分け'
                color = discord.Color.blue()
        else:
            title = '🃏 ブラックジャック'
            color = discord.Color.blue()
        
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name=f'🎴 ディーラーの手札',
            value=dealer_info,
            inline=False
        )
        embed.add_field(
            name=f'🎴 {user_name}の手札',
            value=f"{game.get_hand_display(game.player_hand)} (合計: {player_value})",
            inline=False
        )
        embed.add_field(name='💰 ベット額', value=f'{game.bet} コイン', inline=True)
        
        if game.is_finished:
            winnings = game.calculate_winnings()
            profit = winnings - game.bet
            embed.add_field(
                name='獲得',
                value=f'{winnings} コイン ({"+" if profit >= 0 else ""}{profit})',
                inline=True
            )
        
        return embed
    
    async def process_hit(self, interaction: discord.Interaction, user_id: int):
        """Hit処理（ボタンとコマンド共通）"""
        if user_id not in self.active_games:
            await interaction.response.send_message(
                'ゲームが開始されていません。`/bj play` でゲームを開始してください。',
                ephemeral=True
            )
            return
        
        game = self.active_games[user_id]
        user = self.get_user(user_id)
        
        # カードを引く
        should_auto_stand = game.player_hit()
        
        embed = self.create_game_embed(game, interaction.user.name)
        
        if game.is_finished or should_auto_stand:
            if should_auto_stand and not game.is_finished:
                # 21になった場合は自動的にスタンド
                game.dealer_play()
                embed = self.create_game_embed(game, interaction.user.name, show_dealer=True)
            
            # ゲーム終了処理
            winnings = game.calculate_winnings()
            new_coins = user['coins'] - game.bet + winnings
            self.update_user(user_id, new_coins, game.result in ['win', 'blackjack'], winnings)
            embed.add_field(name='現在のコイン', value=f'{new_coins:,} コイン', inline=True)
            del self.active_games[user_id]
            
            # ボタンを無効化して更新
            view = BlackjackButtons(user_id, self)
            for item in view.children:
                item.disabled = True
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            # ゲーム継続
            view = BlackjackButtons(user_id, self)
            await interaction.response.edit_message(embed=embed, view=view)
    
    async def process_stand(self, interaction: discord.Interaction, user_id: int):
        """Stand処理（ボタンとコマンド共通）"""
        if user_id not in self.active_games:
            await interaction.response.send_message(
                'ゲームが開始されていません。`/bj play` でゲームを開始してください。',
                ephemeral=True
            )
            return
        
        game = self.active_games[user_id]
        user = self.get_user(user_id)
        
        # ディーラーのターン
        game.dealer_play()
        
        # 結果表示
        embed = self.create_game_embed(game, interaction.user.name, show_dealer=True)
        
        winnings = game.calculate_winnings()
        new_coins = user['coins'] - game.bet + winnings
        self.update_user(user_id, new_coins, game.result in ['win', 'blackjack'], winnings)
        embed.add_field(name='現在のコイン', value=f'{new_coins:,} コイン', inline=True)
        
        del self.active_games[user_id]
        
        # ボタンを無効化して更新
        view = BlackjackButtons(user_id, self)
        for item in view.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=view)
    
    @app_commands.command(name="play", description="ブラックジャックを開始します")
    @app_commands.describe(bet="ベットするコイン数（デフォルト: 10）")
    async def play(self, interaction: discord.Interaction, bet: int = 10):
        """ブラックジャックを開始"""
        user_id = interaction.user.id
        
        # 既にゲーム中かチェック
        if user_id in self.active_games:
            await interaction.response.send_message(
                '既にゲーム中です！先にゲームを終了してください。',
                ephemeral=True
            )
            return
        
        if bet < 1:
            await interaction.response.send_message('ベット額は1以上にしてください！', ephemeral=True)
            return
        
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
        
        # ゲーム開始
        game = BlackjackGame(bet)
        game.initial_deal()
        self.active_games[user_id] = game
        
        embed = self.create_game_embed(game, interaction.user.name)
        
        if game.is_finished:
            # ブラックジャックまたは両方21の場合
            winnings = game.calculate_winnings()
            new_coins = user['coins'] - bet + winnings
            self.update_user(user_id, new_coins, game.result != 'lose', winnings)
            embed.add_field(name='現在のコイン', value=f'{new_coins:,} コイン', inline=True)
            del self.active_games[user_id]
            await interaction.response.send_message(embed=embed)
        else:
            # ボタンを追加
            view = BlackjackButtons(user_id, self)
            await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="hit", description="カードを1枚引きます")
    async def hit(self, interaction: discord.Interaction):
        """ヒット（カードを引く）- コマンド版"""
        await self.process_hit(interaction, interaction.user.id)
    
    @app_commands.command(name="stand", description="スタンド（カードを引かずに勝負）")
    async def stand(self, interaction: discord.Interaction):
        """スタンド - コマンド版"""
        await self.process_stand(interaction, interaction.user.id)
    
    @app_commands.command(name="rules", description="ブラックジャックのルールを表示します")
    async def rules(self, interaction: discord.Interaction):
        """ルール説明"""
        embed = discord.Embed(
            title='🃏 ブラックジャック ルール',
            description='21を目指すカードゲーム！',
            color=discord.Color.blue()
        )
        embed.add_field(
            name='📋 基本ルール',
            value='手札の合計を21に近づけることを目指します。21を超えるとバスト（負け）です。',
            inline=False
        )
        embed.add_field(
            name='🎴 カードの価値',
            value='```\n数字カード: その数値\nJ, Q, K: 10点\nA: 1点または11点（有利な方）\n```',
            inline=False
        )
        embed.add_field(
            name='🎮 コマンド',
            value='`/bj play [ベット額]` - ゲーム開始\n`/bj hit` - カードを1枚引く\n`/bj stand` - これ以上引かずに勝負\n\n💡 ゲーム中はボタンでも操作できます！',
            inline=False
        )
        embed.add_field(
            name='💰 配当',
            value='```\nブラックジャック: 2.5倍\n通常勝利: 2倍\n引き分け: 返金\n敗北: 没収\n```',
            inline=False
        )
        embed.add_field(
            name='🎯 ディーラーのルール',
            value='ディーラーは17以上になるまでカードを引き続けます。',
            inline=False
        )
        embed.set_footer(text='💎 スロットと同じコインを使用します')
        
        await interaction.response.send_message(embed=embed)

class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bj_group = BlackjackGroup()

    async def cog_load(self):
        self.bot.tree.add_command(self.bj_group)
        logging.info(f"BlackjackGroup を追加しました (コマンド数: {len(self.bj_group.commands)})")
        for cmd in self.bj_group.commands:
            logging.info(f"  - {cmd.name}")

    async def cog_unload(self):
        self.bot.tree.remove_command("bj")
        logging.info("BlackjackGroup を削除しました")

async def setup(bot):
    await bot.add_cog(BlackjackCog(bot))
    logging.info("BlackjackCog をセットアップしました")