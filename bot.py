"""ちるにゃん！の挨拶とボイスチャンネル入退室通知。"""

import asyncio
import logging
import os
import random
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands

from awake import awake

logger = logging.getLogger(__name__)
GREETINGS = ["さん、こんにちは〜だよ！", "さん、調子はどお？", "さん、猫は好きですか？",
             "さんにはあんまり返事したくないんだよね", "さん、大好き！", "さん、元気ですか？"]
STARTUP_GRACE_SECONDS = 5
NOTIFICATION_INTERVAL_SECONDS = 0.5


# 環境変数からサーバーと通知先のIDを読み込み、設定の不足や誤りを確認する。
def load_channels(environ):
    channels = {}
    for name in ("civ_union", "unreal19", "unreal"):
        guild = environ.get(name)
        channel = environ.get(f"{name}_vcstatus_channel")
        if not guild and not channel:
            continue
        try:
            guild_id, channel_id = int(guild or ""), int(channel or "")
            if guild_id <= 0 or channel_id <= 0:
                raise ValueError
        except ValueError:
            raise ValueError(f"{name} と {name}_vcstatus_channel に正の整数IDを設定してください") from None
        if guild_id in channels:
            raise ValueError(f"{name}: サーバーIDが重複しています")
        channels[guild_id] = channel_id
    if not channels:
        raise ValueError("通知先サーバーとチャンネルを1組以上設定してください")
    return channels


class ChiruBot(commands.Bot):
    # Botが受け取るイベント、コマンド、通知先と送信間隔の管理を準備する。
    def __init__(self, channels):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="~", help_command=None, intents=intents,
                         allowed_mentions=discord.AllowedMentions.none())
        self.inform_channels = dict(channels)
        self.ready_at = None
        self.notification_locks = {guild: asyncio.Lock() for guild in channels}
        self.last_notification = {}
        # 「~help」が呼ばれたら、ヘルプの送信処理へ渡す。
        @self.command(name="help")
        async def help_command(ctx):
            await self.send_help(ctx)

    # 接続準備が完了した時刻を記録し、ログとBotのプレイ中表示を更新する。
    async def on_ready(self):
        self.ready_at = time.monotonic()
        logger.info("Chiru-Nyan! is ready! user=%s discord.py=%s", self.user, discord.__version__)
        await self.change_presence(activity=discord.Game(name="Python"))

    # 接続が切れたら、入退室通知を抑制する状態に戻す。
    async def on_disconnect(self):
        self.ready_at = None

    # 接続が再開した時刻を記録し、直後5秒間の通知抑制を始める。
    async def on_resumed(self):
        self.ready_at = time.monotonic()

    # Botの使い方を埋め込みメッセージにして、コマンドが送られた場所へ返す。
    async def send_help(self, ctx):
        embed = discord.Embed(color=0x53BBD3, description="「にゃん！」でご挨拶するよ！\nボイスチャンネルの入退室もお知らせするよ。")
        embed.set_author(name="Chiru-Nyan! Help", icon_url=self.user.display_avatar.url)
        embed.set_footer(text=f"Childa BUNKYO {datetime.now(timezone.utc).year}")
        await ctx.send(embed=embed)

    # Bot以外の「にゃん！」に挨拶し、「~」で始まるコマンドも処理する。
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content == "にゃん！":
            await message.channel.send(message.author.name + random.choice(GREETINGS))
        await self.process_commands(message)

    # VCの入退室を判定し、設定されたチャンネルへ送信間隔を空けて通知する。
    async def on_voice_state_update(self, member, before, after):
        # 接続準備中と、接続・再接続直後5秒のイベントを抑制する。
        if self.ready_at is None or time.monotonic() - self.ready_at < STARTUP_GRACE_SECONDS:
            return
        if before.channel == after.channel:
            return
        # VC間の移動は通知対象外。
        if before.channel is not None and after.channel is not None:
            return
        channel_id = self.inform_channels.get(member.guild.id)
        if channel_id is None:
            return
        alert_channel = self.get_channel(channel_id)
        if (alert_channel is None or not hasattr(alert_channel, "send")
                or alert_channel.guild.id != member.guild.id):
            logger.warning("通知チャンネルが見つかりません: guild_id=%s channel_id=%s", member.guild.id, channel_id)
            return

        if before.channel is None:
            color = 0x00FF00
            description = f':inbox_tray: **{member.name}** が :loud_sound: `{after.channel.name}` にいるよ！みんなも参加、どう？'
        else:
            color = 0xFF0000
            description = f':outbox_tray: **{member.name}** が :loud_sound: `{before.channel.name}` から退出だ！おやすみなさいかな？'
        embed = discord.Embed(timestamp=datetime.now(timezone.utc), color=color, description=description)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)

        # 同じサーバーの送信を直列化し、前回の送信完了から0.5秒以上空ける。
        async with self.notification_locks[member.guild.id]:
            previous = self.last_notification.get(member.guild.id)
            if previous is not None:
                delay = NOTIFICATION_INTERVAL_SECONDS - (time.monotonic() - previous)
                if delay > 0:
                    await asyncio.sleep(delay)
            try:
                await alert_channel.send(embed=embed)
            except discord.HTTPException:
                logger.exception("入退室通知を送信できません: guild_id=%s", member.guild.id)
            finally:
                self.last_notification[member.guild.id] = time.monotonic()


# トークンと通知先を確認して、HTTPサーバーとDiscord Botを起動する。
def main():
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("MY_TOKEN", "").strip()
    if not token:
        raise ValueError("MY_TOKEN を設定してください")
    bot = ChiruBot(load_channels(os.environ))
    awake()
    bot.run(token)


if __name__ == "__main__":
    main()
