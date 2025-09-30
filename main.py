import discord
import os
import yaml
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
import logging

intents = discord.Intents.default()
intents.members = True  # メンバー情報取得に必要
intents.message_content = True  # メッセージコンテンツ取得（必要に応じて）

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def load_translations(lang_code):
    try:
        with open(f'lang/{lang_code}.yml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"エラー: 言語ファイル {lang_code}.yml が見つかりませんでした")
        return {}  # デフォルトで空の辞書を返す
    except yaml.YAMLError as e:
        logging.error(f"YAMLエラー: {e}")
        return {}

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.initial_extensions = [
            "cogs.info",
            "cogs.guild_events",
            "cogs.language",
            "cogs.role",
            "cogs.ping",
            "cogs.slot",
            "cogs.blackjack",
        ]

    async def setup_hook(self):
        # 拡張機能の読み込み
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                logging.info(f"✅ {ext} を読み込みました")
            except Exception as e:
                logging.error(f"❌ {ext} の読み込みに失敗しました: {e}")
        
        # 登録されているコマンドを確認
        logging.info(f"📋 登録されているコマンド:")
        for command in self.tree.get_commands():
            logging.info(f"  - {command.name} ({type(command).__name__})")
            # グループの場合、サブコマンドも表示
            if hasattr(command, 'commands'):
                for subcmd in command.commands:
                    logging.info(f"    └─ {subcmd.name}")
        
        # コマンド同期
        try:
            # 特定のギルドに同期（テスト用・即座に反映）
            guild = discord.Object(id=831385920145588244)
            
            # ギルドのコマンドをクリアしてから同期
            self.tree.copy_global_to(guild=guild)
            synced_guild = await self.tree.sync(guild=guild)
            
            logging.info(f"✅ ギルド {guild.id} に {len(synced_guild)} 個のコマンドを同期しました")
            for cmd in synced_guild:
                logging.info(f"  - /{cmd.name}")
            
            # グローバルに同期（全サーバーで利用可能・反映に時間がかかる）
            synced_global = await self.tree.sync()
            logging.info(f"✅ グローバルに {len(synced_global)} 個のコマンドを同期しました")
            for cmd in synced_global:
                logging.info(f"  - /{cmd.name}")
        except Exception as e:
            logging.error(f"❌ コマンドの同期に失敗しました: {e}", exc_info=True)

    async def on_ready(self):
        logging.info(f"🤖 {self.user} でログインしました")
        logging.info(f"📊 {len(self.guilds)} サーバーに接続中")
        logging.info(f"🆔 Bot ID: {self.user.id}")

    async def on_command_error(self, ctx, error):
        """コマンドエラーハンドリング"""
        if isinstance(error, commands.CommandNotFound):
            return  # コマンドが見つからない場合は無視
        logging.error(f"コマンドエラー: {error}")

    async def on_error(self, event, *args, **kwargs):
        """一般的なエラーハンドリング"""
        logging.error(f"エラーが発生しました (イベント: {event})", exc_info=True)


# Botを起動
if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    
    if not TOKEN:
        logging.error("❌ DISCORD_TOKENが設定されていません！.envファイルを確認してください")
    else:
        bot = MyBot()
        try:
            bot.run(TOKEN)
        except KeyboardInterrupt:
            logging.info("⏹️ Botを停止しています...")
        except Exception as e:
            logging.error(f"❌ Botの起動に失敗しました: {e}")