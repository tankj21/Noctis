import discord
import os
import yaml
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.members = True  # メンバー情報取得に必要

def load_translations(lang_code):
    try:
        with open(f'lang/{lang_code}.yml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"エラー: 言語ファイル {lang_code}.yml が見つかりませんでした")
        return {}  # デフォルトで空の辞書を返す
    except yaml.YAMLError as e:
        print(f"YAMLエラー: {e}")
        return {}

class MyBot(commands.Bot):
    def __init__(self):
        # command_prefixは空で設定、これでスラッシュコマンドのみを使用
        super().__init__(command_prefix=None, intents=intents)  
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # スラッシュコマンドの同期
        await self.tree.sync()

bot = MyBot()

# Botを起動
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)